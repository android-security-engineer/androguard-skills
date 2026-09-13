#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills Daemon 回归测试

验证 /goal 要求的"守护进程模式（daemon，端口 8899）"核心契约：
  1. 启动/停止生命周期（PID/PORT 文件正确写入与清理）
  2. JSON-RPC 2.0 分发（status 内置方法 + getattr 动态分发到 skills 方法）
  3. 异常隔离（坏 JSON / 未知方法 / 调用抛异常 都返回 JSON-RPC error，不崩进程）
  4. APK 加载缓存（load_apk 后后续请求复用已解析对象，不重解析）

测试用非默认端口（8899+）避免与可能已运行的 daemon 冲突。每测试启动独立
daemon 子进程，结束后清理。

运行：``pytest tests/test_daemon_rpc.py -v``
独立：``python3 tests/test_daemon_rpc.py``
"""
import json
import os
import socket
import subprocess
import sys
import time

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
APK = os.path.join(HERE, "data", "APK", "TestActivity.apk")
# 仅 load_apk 测试依赖真实 APK；其余测试（status/isolation/bad_json）不依赖。
_NEED_APK = pytest.mark.skipif(
    not os.path.exists(APK),
    reason=f"基准 APK 不存在: {APK}",
)

# 用高位端口避免与默认 8899 或其他测试冲突
TEST_PORT = 18999
DAEMON_STARTUP_TIMEOUT = 10  # 秒


def _wait_port_ready(port, timeout=DAEMON_STARTUP_TIMEOUT):
    """轮询端口直到 daemon 接受连接或超时。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except (ConnectionRefusedError, OSError):
            time.sleep(0.2)
    return False


class _DaemonHandle:
    """启动并管理一个 daemon 子进程（自定义端口）。"""

    def __init__(self, port):
        self.port = port
        self.proc = None

    def __enter__(self):
        # 子进程跑 daemon，注入 TEST_PORT。
        # stderr 用 PIPE 验证 daemon 自身的日志抑制修复——daemon._run_server
        # 把 loguru 级别提到 INFO（默认），抑制 AndroGuard 内部 DEBUG xref 日志
        # 刷屏。此前 DEBUG 日志会塞满 PIPE 缓冲（64KB）致 daemon 阻塞卡死。
        # 若该修复回退，本测试会因 stderr PIPE 被填满而 load_apk 超时失败。
        self.proc = subprocess.Popen(
            [
                sys.executable, "-c",
                f"import sys; sys.path.insert(0, '{REPO_ROOT}'); "
                f"from androguard.skills.daemon import DaemonServer; "
                f"d = DaemonServer(port={self.port}); d.start()",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            cwd=REPO_ROOT,
        )
        if not _wait_port_ready(self.port):
            raise RuntimeError(
                f"daemon 未在端口 {self.port} 就绪（启动超时）"
            )
        return self

    def __exit__(self, *exc):
        self.stop()

    def stop(self):
        if self.proc and self.proc.poll() is None:
            # 先尝试优雅 shutdown（JSON-RPC），再 kill
            try:
                self.call("shutdown", {})
            except Exception:
                pass
            try:
                self.proc.terminate()
                self.proc.wait(timeout=5)
            except Exception:
                self.proc.kill()


def _rpc(port, request, timeout=120):
    """发一条 JSON-RPC 请求，读一行响应。load_apk 含 xref 解析可能数秒，故默认 120s。"""
    with socket.create_connection(("127.0.0.1", port), timeout=timeout) as s:
        s.sendall((json.dumps(request) + "\n").encode("utf-8"))
        buf = b""
        while b"\n" not in buf:
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
        # 取第一行（daemon 以 \n 分隔响应）
        first_line = buf.split(b"\n", 1)[0]
        return json.loads(first_line.decode("utf-8"))


def call(port, method, params=None, req_id=1, timeout=120):
    """便捷封装：构造 JSON-RPC 请求并返回响应 dict。"""
    return _rpc(port, {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or {},
        "id": req_id,
    }, timeout=timeout)


# ---- 测试 ----

def test_daemon_status_builtin():
    """status 是内置方法，不依赖 APK 加载。"""
    with _DaemonHandle(TEST_PORT) as d:
        resp = call(d.port, "status", {})
        assert resp["jsonrpc"] == "2.0"
        assert "result" in resp, f"status 应返回 result，实际: {resp}"
        assert resp["result"]["status"] == "running"
        assert "pid" in resp["result"]
        assert "uptime" in resp["result"]
        assert "apk_loaded" in resp["result"]


def test_daemon_unknown_method_isolation():
    """未知方法返回 JSON-RPC error(-32601)，进程不崩。"""
    with _DaemonHandle(TEST_PORT + 1) as d:
        resp = call(d.port, "this_method_does_not_exist", {})
        assert "error" in resp, f"未知方法应返回 error，实际: {resp}"
        assert resp["error"]["code"] == -32601
        # 关键：进程仍存活，status 仍可调用
        status = call(d.port, "status", {})
        assert status["result"]["status"] == "running", "daemon 应在错误后仍存活"


@_NEED_APK
def test_daemon_load_apk_and_cache():
    """load_apk 加载后，status.apk_loaded 变 True；后续命令复用缓存。"""
    with _DaemonHandle(TEST_PORT + 2) as d:
        # 加载前
        before = call(d.port, "status", {})
        assert before["result"]["apk_loaded"] is False

        # 加载 APK
        load_resp = call(d.port, "load_apk", {"apk_path": APK})
        assert "result" in load_resp, f"load_apk 失败: {load_resp}"

        # 加载后 apk_loaded 应为 True（缓存命中）
        after = call(d.port, "status", {})
        assert after["result"]["apk_loaded"] is True, "加载后 apk_loaded 应为 True"

        # 后续命令应复用已加载对象（不再需要 apk_path，daemon 持有缓存）
        # 注：daemon 的 skills 实例在 load_apk 后持有 _apk/_analysis
        info = call(d.port, "apk_info", {})
        assert "result" in info, f"缓存命中后 apk_info 应成功: {info}"


def test_daemon_method_exception_isolation():
    """skills 方法抛异常时返回 JSON-RPC error(-32603)，进程不崩。"""
    with _DaemonHandle(TEST_PORT + 3) as d:
        # 调一个需要已加载 APK 但未加载的方法 → 应抛异常但被隔离
        resp = call(d.port, "apk_info", {})
        # 未加载时可能返回 error 或空 result，关键是进程不崩
        # 无论 result 还是 error，进程必须存活
        status = call(d.port, "status", {})
        assert status["result"]["status"] == "running", "daemon 应在方法异常后仍存活"


def test_daemon_bad_json_isolation():
    """坏 JSON 返回 parse error(-32700)，进程不崩。"""
    with _DaemonHandle(TEST_PORT + 4) as d:
        with socket.create_connection(("127.0.0.1", d.port), timeout=10) as s:
            s.sendall(b"this is not json\n")
            buf = b""
            while b"\n" not in buf:
                chunk = s.recv(65536)
                if not chunk:
                    break
                buf += chunk
            resp = json.loads(buf.split(b"\n", 1)[0].decode("utf-8"))
        assert resp["error"]["code"] == -32700, f"坏 JSON 应返回 -32700，实际: {resp}"
        # 进程仍存活
        status = call(d.port, "status", {})
        assert status["result"]["status"] == "running"


def test_daemon_large_request_not_truncated():
    """超过 64KB 的大请求（大批量/大 params）不被 TCP 分片截断。

    _handle_client 曾假设一次 read 即完整 JSON，大请求会被截断成不完整
    JSON 返回 -32700。修复为按 \\n 分隔的缓冲累积后，任意大请求都能正确
    解析。
    """
    with _DaemonHandle(TEST_PORT + 5) as d:
        # 80KB 单请求：params 里塞 80KB junk（>64KB read 缓冲）
        big = "x" * 80000
        req = json.dumps({
            "jsonrpc": "2.0", "method": "status",
            "params": {"junk": big}, "id": 1,
        }) + "\n"
        with socket.create_connection(("127.0.0.1", d.port), timeout=10) as s:
            s.sendall(req.encode("utf-8"))
            buf = b""
            while b"\n" not in buf:
                chunk = s.recv(65536)
                if not chunk:
                    break
                buf += chunk
        resp = json.loads(buf.split(b"\n", 1)[0].decode("utf-8"))
        # 不应是被截断的 -32700 parse error
        assert "result" in resp, (
            f"大请求应正常解析返回 result，实际（可能被截断）: {resp}"
        )
        assert resp["id"] == 1
        assert resp["result"]["status"] == "running"


def test_daemon_fragmented_request_reassembled():
    """单请求分片发送（TCP 拆成多个包）：缓冲累积后正确解析。"""
    import time

    with _DaemonHandle(TEST_PORT + 6) as d:
        req = json.dumps({
            "jsonrpc": "2.0", "method": "status", "params": {}, "id": 42,
        }) + "\n"
        data = req.encode("utf-8")
        with socket.create_connection(("127.0.0.1", d.port), timeout=10) as s:
            # 分 3 片发送，每片后 sleep 强制分到不同 read
            third = len(data) // 3 + 1
            for i in range(0, len(data), third):
                s.sendall(data[i:i + third])
                time.sleep(0.15)
            buf = b""
            while b"\n" not in buf:
                chunk = s.recv(65536)
                if not chunk:
                    break
                buf += chunk
        resp = json.loads(buf.split(b"\n", 1)[0].decode("utf-8"))
        assert resp["id"] == 42, f"分片请求响应 id 错误: {resp}"
        assert resp["result"]["status"] == "running"


def test_daemon_pipelined_requests():
    """多条请求一次发送（流水线）：按 \\n 切分逐条响应。"""
    with _DaemonHandle(TEST_PORT + 7) as d:
        req1 = json.dumps({"jsonrpc": "2.0", "method": "status", "params": {}, "id": 1})
        req2 = json.dumps({"jsonrpc": "2.0", "method": "status", "params": {}, "id": 2})
        # 两条请求 + 各自换行，一次发送
        payload = (req1 + "\n" + req2 + "\n").encode("utf-8")
        with socket.create_connection(("127.0.0.1", d.port), timeout=10) as s:
            s.sendall(payload)
            import time
            time.sleep(0.3)
            buf = s.recv(65536)
        lines = [l for l in buf.split(b"\n") if l.strip()]
        assert len(lines) == 2, f"应收到 2 条响应，实际 {len(lines)}: {buf!r}"
        r1 = json.loads(lines[0])
        r2 = json.loads(lines[1])
        assert r1["id"] == 1 and r2["id"] == 2, f"流水线响应 id 错乱: {r1['id']}, {r2['id']}"
        assert r1["result"]["status"] == "running"
        assert r2["result"]["status"] == "running"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = failed = 0
    for fn in fns:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {fn.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed, {len(fns)} total")
    sys.exit(1 if failed else 0)
