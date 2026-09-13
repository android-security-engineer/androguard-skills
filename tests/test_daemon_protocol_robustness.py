#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills daemon JSON-RPC 协议健壮性回归测试

test_daemon_rpc.py 守正常契约（status/分发/隔离/load 缓存），
test_daemon_batch_rpc.py 守批量请求，test_daemon_scale_concurrency.py 守
大 APK+并发。但协议层边缘情况——客户端连接但不发数据、发半截 JSON、
多条请求粘在一起、超长单行——未守。daemon 是长驻服务，有 bug 的 agent
或网络问题会发畸形请求，若 daemon 阻塞或崩溃会卡住整个事件循环，影响
所有 agent（/goal："对接几十个 agent"，单连接异常不应拖垮全局）。

本测试复用 test_daemon_rpc 的 _DaemonHandle 模式（独立复制避免收集耦合），
验证 _handle_client 的边缘处理：
  1. 连接建立后不发数据即关闭 → daemon 不崩，后续请求正常
  2. 发半截 JSON（无换行）后关闭 → daemon 不崩
  3. 多条请求粘在一个 send（无中间响应）→ 全部响应、顺序正确
  4. 超长单行（大 params，>64KB 跨 TCP 分片）→ 仍正确解析
  5. 空行/纯空白行 → 跳过不报错

运行：``pytest tests/test_daemon_protocol_robustness.py -v``
独立：``python3 tests/test_daemon_protocol_robustness.py``
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
TEST_PORT = 19499  # 与其他 daemon 测试错开


def _wait_port_ready(port, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except (ConnectionRefusedError, OSError):
            time.sleep(0.2)
    return False


class _DaemonHandle:
    def __init__(self, port):
        self.port = port
        self.proc = None

    def __enter__(self):
        self.proc = subprocess.Popen(
            [sys.executable, "-c",
             f"import sys; sys.path.insert(0, '{REPO_ROOT}'); "
             f"from androguard.skills.daemon import DaemonServer; "
             f"d = DaemonServer(port={self.port}); d.start()"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            cwd=REPO_ROOT,
        )
        if not _wait_port_ready(self.port):
            raise RuntimeError(f"daemon 未在端口 {self.port} 就绪")
        return self

    def __exit__(self, *exc):
        if self.proc and self.proc.poll() is None:
            try:
                self._rpc({"jsonrpc": "2.0", "method": "shutdown",
                           "params": {}, "id": 0})
            except Exception:
                pass
            try:
                self.proc.terminate()
                self.proc.wait(timeout=5)
            except Exception:
                self.proc.kill()

    def _rpc_raw(self, data_bytes, timeout=10):
        """发原始字节，读所有可用响应行。"""
        with socket.create_connection(("127.0.0.1", self.port),
                                       timeout=timeout) as s:
            s.sendall(data_bytes)
            s.shutdown(socket.SHUT_WR)
            buf = b""
            try:
                while True:
                    chunk = s.recv(65536)
                    if not chunk:
                        break
                    buf += chunk
            except socket.timeout:
                pass
            return buf

    def _rpc(self, req, timeout=10):
        """发一条 JSON-RPC，返回响应 dict。"""
        with socket.create_connection(("127.0.0.1", self.port),
                                       timeout=timeout) as s:
            s.sendall((json.dumps(req) + "\n").encode("utf-8"))
            buf = b""
            while b"\n" not in buf:
                chunk = s.recv(65536)
                if not chunk:
                    break
                buf += chunk
            return json.loads(buf.split(b"\n", 1)[0].decode("utf-8"))


@pytest.fixture(scope="module")
def daemon():
    with _DaemonHandle(TEST_PORT) as d:
        yield d


def test_connect_then_close_without_sending(daemon):
    """连接建立后不发任何数据即关闭 → daemon 不崩，后续正常。"""
    # 建连即关
    with socket.create_connection(("127.0.0.1", daemon.port), timeout=5):
        pass
    # daemon 仍应正常响应
    resp = daemon._rpc({"jsonrpc": "2.0", "method": "status",
                        "params": {}, "id": 1})
    assert resp.get("id") == 1
    assert "error" not in resp or "result" in resp


def test_partial_json_then_close(daemon):
    """发半截 JSON（无换行）后关闭 → daemon 不崩。"""
    daemon._rpc_raw(b'{"jsonrpc":"2.0","method":"status","params":{},')  # 无 } 无 \n
    # daemon 仍正常
    resp = daemon._rpc({"jsonrpc": "2.0", "method": "status",
                        "params": {}, "id": 2})
    assert resp.get("id") == 2


def test_pipelined_requests_in_one_send(daemon):
    """多条请求粘在一个 send（无中间读）→ 全部响应。"""
    reqs = [
        {"jsonrpc": "2.0", "method": "status", "params": {}, "id": i}
        for i in range(5)
    ]
    payload = "".join(json.dumps(r) + "\n" for r in reqs).encode("utf-8")
    buf = daemon._rpc_raw(payload, timeout=15)
    lines = [l for l in buf.split(b"\n") if l.strip()]
    assert len(lines) >= 5, f"应收到 5 条响应，实际 {len(lines)} 条"
    ids = []
    for line in lines[:5]:
        resp = json.loads(line.decode("utf-8"))
        ids.append(resp.get("id"))
    assert ids == [0, 1, 2, 3, 4], f"响应 id 顺序错: {ids}"


def test_empty_lines_skipped(daemon):
    """空行/纯空白行应被跳过，不产生响应也不报错。"""
    payload = b"\n\n   \n\t\n" + (
        json.dumps({"jsonrpc": "2.0", "method": "status",
                    "params": {}, "id": 7}) + "\n"
    ).encode("utf-8")
    buf = daemon._rpc_raw(payload, timeout=10)
    lines = [l for l in buf.split(b"\n") if l.strip()]
    assert len(lines) == 1, f"空行不应产生响应，实际 {len(lines)} 条非空行"
    resp = json.loads(lines[0].decode("utf-8"))
    assert resp.get("id") == 7


def test_oversized_single_line_across_fragments(daemon):
    """超长单行（>64KB，跨 TCP 分片）的合法 JSON 仍应正确解析。

    构造一个 params 里带大字符串的 status 请求，整体 >64KB。
    """
    # status 不接受 params，用 unknown method 但带大 params 测解析能力
    big = "x" * 70000  # 70KB，超过单次 read 的 65536
    req = {"jsonrpc": "2.0", "method": "nonexistent_method",
           "params": {"big": big}, "id": 99}
    payload = (json.dumps(req) + "\n").encode("utf-8")
    assert len(payload) > 65536, "测试前提：payload 应超过 64KB"
    buf = daemon._rpc_raw(payload, timeout=15)
    lines = [l for l in buf.split(b"\n") if l.strip()]
    assert lines, "超长请求应仍有响应"
    resp = json.loads(lines[0].decode("utf-8"))
    # 方法不存在应返回 error（-32601），证明完整解析了大请求
    assert resp.get("id") == 99
    assert "error" in resp
    assert resp["error"].get("code") == -32601, (
        f"超长请求应解析成功后报 method not found，实际: {resp.get('error')}"
    )


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    passed = failed = 0
    with _DaemonHandle(TEST_PORT) as d:
        # 手动注入 fixture（独立运行模式）
        class _Mod:
            pass
        for fn in fns:
            try:
                fn(d)
                print(f"  PASS  {fn.__name__}")
                passed += 1
            except Exception as e:
                print(f"  FAIL  {fn.__name__}: {e}")
                failed += 1
    print(f"\n{passed} passed, {failed} failed, {len(fns)} total")
    sys.exit(1 if failed else 0)
