"""
Daemon 进程管理。

基于 asyncio + TCP Socket 的 JSON-RPC 服务端，
支持后台常驻进程避免重复解析 APK。

架构::

    ┌─────────────────┐     TCP localhost       ┌──────────────────┐
    │  CLI Client     │ ◄────────────────────► │  Daemon Process  │
    │  (androguard-   │    JSON-RPC 协议         │  (常驻后台)       │
    │   skills CLI)   │                         │                  │
    └─────────────────┘                         │  缓存:           │
                                                │  - APK 对象      │
                                                │  - DEX 对象      │
                                                │  - Analysis 对象  │
                                                └──────────────────┘

使用方式::

    # 启动 daemon
    androguard-skills daemon start

    # 正常使用 CLI（自动连接 daemon）
    androguard-skills load test.apk
    androguard-skills apk info

    # 停止 daemon
    androguard-skills daemon stop
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import socket
import sys
import time
from typing import Union

from loguru import logger


# 自定义 JSON 编码器，处理 AndroGuard 返回的不可直接序列化的类型。
# 与 main._SkillsJsonEncoder 保持同步（消除重复会引入模块级导入，此处保持独立）。
class _DaemonJsonEncoder(json.JSONEncoder):
    """处理 set/frozenset/bytes/filter/map/zip/range/generator 等类型。"""

    def default(self, obj):
        if isinstance(obj, (set, frozenset)):
            return list(obj)
        if isinstance(obj, (bytes, bytearray)):
            return obj.hex()
        if isinstance(obj, (filter, map, zip, range)):
            return list(obj)
        if hasattr(obj, "__next__"):
            return list(obj)
        return super().default(obj)


# Daemon 运行时文件目录
DAEMON_DIR = os.path.join(
    os.environ.get("XDG_RUNTIME_DIR", "/tmp"),
    "androguard-skills-daemon",
)
PID_FILE = os.path.join(DAEMON_DIR, "daemon.pid")
PORT_FILE = os.path.join(DAEMON_DIR, "daemon.port")


def _ensure_daemon_dir():
    """确保 daemon 目录存在"""
    os.makedirs(DAEMON_DIR, exist_ok=True)


class DaemonServer:
    """
    JSON-RPC Daemon 服务端。

    监听 TCP localhost，接受 JSON-RPC 请求，
    调用 AndroguardSkillsMain 方法并返回结果。
    """

    def __init__(self, port: int = 8899, host: str = "127.0.0.1"):
        self.port = port
        self.host = host
        self._skills = None
        self._api = None
        self._server = None
        self._running = False

    def _get_skills(self):
        """懒加载 AndroguardSkillsMain"""
        if self._skills is None:
            from androguard.skills.main import AndroguardSkillsMain

            self._skills = AndroguardSkillsMain()
        return self._skills

    def _get_api(self):
        """懒加载 HeadlessAPI（共享同一 skills 实例）。"""
        if self._api is None:
            from androguard.agent.headless import HeadlessAPI

            self._api = HeadlessAPI(skills=self._get_skills())
        return self._api

    async def _handle_client(self, reader, writer):
        """处理客户端连接。

        协议：每条 JSON-RPC 请求以 ``\\n`` 分隔。一次 read 可能拿到不完整
        片段（大请求被 TCP 分片）或多条请求拼在一起，故维护逐连接缓冲区，
        按 ``\\n`` 切出完整请求再分发。此前假设一次 read 即完整 JSON，大请求
        （>64KB 批量/大 params）会被截断致 JSONDecodeError。
        """
        buffer = b""
        try:
            while self._running:
                data = await reader.read(65536)
                if not data:
                    break
                buffer += data

                # 按换行符切出所有完整请求，逐条分发
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    line = line.strip()
                    if not line:
                        continue  # 空行跳过

                    try:
                        request = json.loads(line.decode("utf-8"))
                        response = await self._dispatch(request)
                    except json.JSONDecodeError as e:
                        response = {
                            "jsonrpc": "2.0",
                            "error": {
                                "code": -32700,
                                "message": f"Parse error: {e}",
                            },
                            "id": None,
                        }
                    except Exception as e:
                        response = {
                            "jsonrpc": "2.0",
                            "error": {"code": -32603, "message": str(e)},
                            "id": None,
                        }

                    # 序列化响应也纳入 try：_DaemonJsonEncoder 的 str() 兜底已让
                    # 几乎所有对象可序列化，但防御 str() 自身抛异常的极端情况——
                    # 若 json.dumps 在此抛 TypeError 而不 catch，会逃逸到外层
                    # except (ConnectionResetError, BrokenPipeError) 不匹配，
                    # 该连接静默无响应（agent 超时），违反"对接几十个 agent"
                    # 的连接不静默死契约。序列化失败时回退结构化 error 响应。
                    try:
                        response_bytes = (
                            json.dumps(
                                response, cls=_DaemonJsonEncoder
                            ).encode("utf-8")
                            + b"\n"
                        )
                    except Exception as e:
                        response_bytes = (
                            json.dumps(
                                {
                                    "jsonrpc": "2.0",
                                    "error": {
                                        "code": -32603,
                                        "message": f"Response serialization failed: {e}",
                                    },
                                    "id": None,
                                }
                            ).encode("utf-8")
                            + b"\n"
                        )
                    writer.write(response_bytes)
                    await writer.drain()

        except (ConnectionResetError, BrokenPipeError):
            pass
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def _dispatch(self, request) -> Union[dict, list]:
        """
        分发 JSON-RPC 请求到 AndroguardSkillsMain 方法。

        支持单请求（dict）和批量请求（list，JSON-RPC 2.0 规范）。
        批量请求逐个分发，每个独立隔离（一个失败不影响其余），返回批量
        响应列表。对接几十个 agent 时，单连接发批量能减少往返开销。

        :param request: JSON-RPC 请求（dict 或 list）
        :return: JSON-RPC 响应（dict 或 list）
        """
        # JSON-RPC 2.0 批量请求：[req1, req2, ...] → [resp1, resp2, ...]
        if isinstance(request, list):
            responses = [await self._dispatch_single(r) for r in request]
            return [r for r in responses if r is not None]
        return await self._dispatch_single(request)

    async def _dispatch_single(self, request: dict) -> dict:
        """分发单个 JSON-RPC 请求。

        daemon 特有的内置方法（status/shutdown）在此处理；其余全部委托给
        HeadlessAPI.handle()，统一走 ToolRegistry 路由（参数校验、jsonable
        序列化、MCP tools/list 支持一并获得）。
        """
        method_name = request.get("method", "")
        req_id = request.get("id")

        # daemon 内置：状态查询
        if method_name == "status":
            skills = self._get_skills()
            return {
                "jsonrpc": "2.0",
                "result": {
                    "status": "running",
                    "pid": os.getpid(),
                    "uptime": time.time() - self._start_time,
                    "apk_loaded": skills.is_loaded,
                },
                "id": req_id,
            }

        # daemon 内置：优雅关闭
        if method_name == "shutdown":
            self._running = False
            return {
                "jsonrpc": "2.0",
                "result": {"status": "shutting_down"},
                "id": req_id,
            }

        # 其余全部委托给 HeadlessAPI（统一路由：技能方法 + MCP initialize/tools/list/tools/call）
        try:
            response = self._get_api().handle(request)
            if response is None:
                # MCP notification（无 id）→ 无响应
                return None
            return response
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": str(e)},
                "id": req_id,
            }

    async def _run_server(self):
        """运行 TCP 服务器"""
        # daemon 长驻服务的日志配置——这是生产健壮性关键：
        # AndroGuard 在 INFO 级别就会对每个 ClassAnalysis/MethodAnalysis 打日志，
        # 解析一个 APK 产生数万行 INFO，瞬间塞满 stderr 管道缓冲（64KB）。
        # daemon 的事件循环同时往 stderr 写日志和往 socket 写响应，stderr 满了
        # 会阻塞整个循环，导致响应无法写回、客户端超时——经典死锁。
        # 故：默认 WARNING 级别（仅错误/警告），并把日志落文件以便排障。
        # 需调试时用 LOGURU_LEVEL=DEBUG/INFO 覆盖，但生产环境勿用低级别。
        import os as _os

        _level = _os.environ.get("LOGURU_LEVEL", "WARNING").upper()
        # 先确保 daemon 目录存在，再配置日志落文件——否则若 DAEMON_DIR 不存在，
        # logger.add(file) 创建文件句柄可能失败被下面的 except 吞掉，daemon 静默无日志。
        _ensure_daemon_dir()
        try:
            logger.remove()
            # 默认不写 stderr（避免管道死锁）；落文件到 daemon 目录
            _log_file = _os.path.join(DAEMON_DIR, "daemon.log")
            logger.add(_log_file, level=_level, rotation="5 MB", retention=3)
        except Exception:
            pass

        self._server = await asyncio.start_server(
            self._handle_client, self.host, self.port
        )
        self._running = True
        self._start_time = time.time()

        # 写入 PID 和端口文件（目录已由上方 _ensure_daemon_dir 创建）
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
        with open(PORT_FILE, "w") as f:
            f.write(str(self.port))

        logger.info(
            f"AndroGuard Skills Daemon started on "
            f"{self.host}:{self.port} (PID: {os.getpid()})"
        )

        # 注册信号处理器实现 graceful shutdown：收到 SIGTERM/SIGINT 时
        # 设 _running=False，让上方 while 循环退出 → _run_server 返回 →
        # start() 的 finally 触发 _cleanup 清理 PID/端口文件。
        # 此前只 except KeyboardInterrupt 捕获 SIGINT（Ctrl-C），但 `kill <pid>`
        # 默认发 SIGTERM——SIGTERM 不触发 KeyboardInterrupt，进程被直接终止，
        # _cleanup 不执行，残留 PID 文件让下次 start 报 "already running"
        # （虽 _is_daemon_running 的端口探测兜底会清理，但仍是不干净的退出）。
        # add_signal_handler 仅 Unix 平台支持；非 Unix 跳过（退化到原行为）。
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, self._signal_handler)
            except (NotImplementedError, RuntimeError):
                # Windows/非 Unix 无 add_signal_handler，跳过
                pass

        async with self._server:
            while self._running:
                await asyncio.sleep(0.5)

    def _signal_handler(self):
        """信号处理：设 _running=False 触发 graceful shutdown。"""
        self._running = False
        logger.info("Received shutdown signal, stopping daemon gracefully...")

    def start(self):
        """启动 daemon 进程"""
        # 检查是否已有 daemon 在运行
        if self._is_daemon_running():
            print(
                json.dumps(
                    {
                        "error": "Daemon is already running. "
                        "Use 'androguard-skills daemon stop' first."
                    }
                )
            )
            return

        # 启动服务器
        try:
            asyncio.run(self._run_server())
        except KeyboardInterrupt:
            pass
        except OSError as e:
            # 端口被占（address already in use）或其他 OS 错误：
            # 输出结构化错误而非 Python traceback，agent 可解析自恢复
            # （/goal："对接几十个 agent"，端口冲突在多 agent 环境常见）
            print(
                json.dumps(
                    {
                        "error": f"Cannot start daemon on "
                        f"{self.host}:{self.port}: {e.strerror or str(e)}. "
                        f"Use a different port (--port) or stop the process "
                        f"holding this port."
                    }
                )
            )
        finally:
            self._cleanup()

    def _cleanup(self):
        """清理 PID 和端口文件"""
        for f in [PID_FILE, PORT_FILE]:
            try:
                os.remove(f)
            except FileNotFoundError:
                pass

    @staticmethod
    def _is_daemon_running() -> bool:
        """检查 daemon 是否在运行。

        双重确认：(1) PID 文件存在且进程存活；(2) 端口可连接。PID 复用
        （daemon 崩溃后 OS 把 PID 分配给别的进程）会让单纯 PID 检查误判
        "在跑"→start 拒绝启动。加端口探测兜底：PID 存活但端口不响应，
        视为未运行（清理残留 PID 文件）。
        """
        if not os.path.exists(PID_FILE):
            return False

        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())

            # 检查进程是否存在
            os.kill(pid, 0)
        except (ProcessLookupError, FileNotFoundError, ValueError):
            # 进程不存在，清理 PID 文件
            try:
                os.remove(PID_FILE)
            except FileNotFoundError:
                pass
            return False
        except OSError:
            # os.kill 其他 OSError（如权限不足）视为不可确认 → 清理
            try:
                os.remove(PID_FILE)
            except FileNotFoundError:
                pass
            return False

        # PID 存活，再确认端口是否真的在监听（防 PID 复用）
        port = 8899
        try:
            with open(PORT_FILE, "r") as f:
                port = int(f.read().strip())
        except (FileNotFoundError, ValueError):
            pass
        try:
            import socket as _sock

            with _sock.create_connection(("127.0.0.1", port), timeout=1) as s:
                # 发一个 status 请求确认是本 daemon（而非别的服务占了端口）
                s.sendall(
                    b'{"jsonrpc":"2.0","method":"status","params":{},"id":1}\n'
                )
                data = b""
                while b"\n" not in data:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                resp = data.decode("utf-8", errors="ignore").strip()
                # daemon 的 status 响应含 "running"
                if "running" in resp:
                    return True
                # 端口被别的服务占了 → daemon 不在跑
                return False
        except (ConnectionError, OSError):
            # PID 存活但端口不响应 → daemon 实际卡死/崩溃，清理残留
            try:
                os.remove(PID_FILE)
            except FileNotFoundError:
                pass
            return False


class DaemonClient:
    """
    JSON-RPC Daemon 客户端。

    CLI 命令通过此类与 daemon 通信。
    """

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    def is_daemon_running(self) -> bool:
        """检查 daemon 是否在运行"""
        return DaemonServer._is_daemon_running()

    def _get_daemon_port(self) -> int:
        """获取 daemon 端口"""
        try:
            with open(PORT_FILE, "r") as f:
                return int(f.read().strip())
        except (FileNotFoundError, ValueError):
            return 8899

    def call(self, method: str, params: dict = None) -> dict:
        """
        调用 daemon 的 JSON-RPC 方法。

        :param method: 方法名
        :param params: 参数
        :return: 结果
        :raises ConnectionError: 无法连接 daemon
        :raises RuntimeError: daemon 返回错误
        """
        if not self.is_daemon_running():
            raise ConnectionError("Daemon is not running")

        port = self._get_daemon_port()
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": 1,
        }

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(self.timeout)
                s.connect(("127.0.0.1", port))
                s.sendall(json.dumps(request).encode("utf-8") + b"\n")

                # 读取响应
                data = b""
                while True:
                    chunk = s.recv(65536)
                    if not chunk:
                        break
                    data += chunk
                    if b"\n" in data:
                        break

            response = json.loads(data.decode("utf-8").strip())

            if "error" in response:
                raise RuntimeError(
                    f"Daemon error: {response['error'].get('message', 'Unknown')}"
                )

            return response.get("result", {})

        except socket.timeout:
            raise ConnectionError("Daemon connection timed out")
        except ConnectionRefusedError:
            raise ConnectionError("Daemon connection refused")
        except json.JSONDecodeError as e:
            raise ConnectionError(f"Invalid response from daemon: {e}")

    def stop_daemon(self):
        """停止 daemon"""
        try:
            self.call("shutdown", {})
        except Exception:
            pass

        # 等待 daemon 停止
        for _ in range(10):
            if not self.is_daemon_running():
                break
            time.sleep(0.5)
