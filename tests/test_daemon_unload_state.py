#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills daemon unload 后状态回归测试

test_daemon_longrun_memory.py 守 unload 的内存回落（malloc_trim 归还 arena），
test_cli_error_paths.py 守单次模式"未加载就调命令→结构化 error"。但 daemon
模式下 unload 后再调查询命令的行为未守——_ensure_loaded 抛 RuntimeError，
daemon._dispatch_single 应 catch 返回 JSON-RPC error(-32603) 而非崩溃
（/goal："对接几十个 agent"，daemon 长驻，unload 后任何命令都应优雅降级，
不能崩进程影响其他 agent）。

本测试验证：
  1. load_apk 后查询命令正常
  2. unload 后查询命令返回结构化 error（不崩，进程存活）
  3. reload 后查询命令恢复（unload 不留下腐化状态）

运行：``pytest tests/test_daemon_unload_state.py -v``
独立：``python3 tests/test_daemon_unload_state.py``
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
_NEED_APK = pytest.mark.skipif(
    not os.path.exists(APK), reason=f"基准 APK 不存在: {APK}"
)
TEST_PORT = 19599


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

    def call(self, method, params=None, timeout=120):
        req = {"jsonrpc": "2.0", "method": method,
               "params": params or {}, "id": 1}
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


@_NEED_APK
def test_unload_then_query_returns_structured_error():
    """unload 后调查询命令应返回 JSON-RPC error，不崩进程。"""
    with _DaemonHandle(TEST_PORT) as d:
        # 1. load + 查询正常
        load = d.call("load_apk", {"apk_path": APK})
        assert "error" not in load, f"load 失败: {load.get('error')}"
        info = d.call("apk_info", {})
        assert "result" in info, f"load 后 apk_info 应成功: {info}"

        # 2. unload
        unload = d.call("unload", {})
        assert "result" in unload, f"unload 失败: {unload}"

        # 3. unload 后查询应返回结构化 error（不崩）
        info2 = d.call("apk_info", {})
        assert "error" in info2, (
            f"unload 后 apk_info 应返回 error（未加载），实际: {info2}"
        )
        # error code 应是 -32603（方法执行异常）或含"loaded"提示
        err = info2["error"]
        assert isinstance(err, dict)
        assert "message" in err
        msg_lower = err.get("message", "").lower()
        assert "load" in msg_lower or err.get("code") == -32603, (
            f"error 应提示未加载: {err}"
        )

        # 4. 进程仍存活（status 正常响应）
        status = d.call("status", {})
        assert "result" in status, f"unload 后 daemon 应仍存活: {status}"


@_NEED_APK
def test_unload_then_reload_recovers():
    """unload 后重新 load 应恢复查询能力（unload 不留腐化状态）。"""
    with _DaemonHandle(TEST_PORT + 1) as d:
        # 初始 load
        d.call("load_apk", {"apk_path": APK})
        info1 = d.call("apk_info", {})
        assert "result" in info1
        pkg1 = info1["result"].get("package")

        # unload
        d.call("unload", {})

        # unload 后查询失败
        info_mid = d.call("apk_info", {})
        assert "error" in info_mid

        # reload 同一 APK
        reload_resp = d.call("load_apk", {"apk_path": APK})
        assert "error" not in reload_resp, (
            f"reload 失败: {reload_resp.get('error')}"
        )

        # 查询恢复，结果与首次一致
        info2 = d.call("apk_info", {})
        assert "result" in info2, f"reload 后查询应恢复: {info2}"
        pkg2 = info2["result"].get("package")
        assert pkg1 == pkg2, (
            f"reload 后 package 应与首次一致: {pkg1} vs {pkg2}"
        )


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
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
