#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills Daemon JSON-RPC 批量请求回归测试

JSON-RPC 2.0 规范规定客户端可发批量请求（数组），服务端应返回批量响应。
对接几十个 agent 时，单连接发批量能减少 TCP 往返开销——这是真实能力。

此前 daemon 的 _dispatch 只处理 dict，传 list 会 TypeError。已修复为
_dispatch 检测 list 逐个分发到 _dispatch_single，每个独立隔离。

本测试验证：
  1. 批量请求返回批量响应（list），顺序与请求一致
  2. 批量内单个失败（未知方法）不影响其余，返回对应 error
  3. 批量响应 id 与请求 id 一一对应（无错乱）
  4. 单请求仍正常（向后兼容）

运行：``pytest tests/test_daemon_batch_rpc.py -v``
独立：``python3 tests/test_daemon_batch_rpc.py``
"""
import json
import os
import socket
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
sys.path.insert(0, HERE)

from test_daemon_rpc import _DaemonHandle, TEST_PORT

_SMALL_APK = os.path.join(HERE, "data", "APK", "TestActivity.apk")
_NEED_APK = pytest.mark.skipif(
    not os.path.exists(_SMALL_APK),
    reason=f"基准 APK 不存在: {_SMALL_APK}",
)


def _rpc_batch(port, batch, timeout=120):
    """发批量 JSON-RPC 请求，读一行响应。"""
    with socket.create_connection(("127.0.0.1", port), timeout=timeout) as s:
        s.sendall((json.dumps(batch) + "\n").encode("utf-8"))
        buf = b""
        while b"\n" not in buf:
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
    return json.loads(buf.split(b"\n", 1)[0].decode("utf-8"))


def test_batch_returns_list_in_order():
    """批量请求返回批量响应（list），顺序与请求一致。"""
    with _DaemonHandle(TEST_PORT + 60) as d:
        batch = [
            {"jsonrpc": "2.0", "method": "status", "params": {}, "id": 1},
            {"jsonrpc": "2.0", "method": "status", "params": {}, "id": 2},
            {"jsonrpc": "2.0", "method": "status", "params": {}, "id": 3},
        ]
        resp = _rpc_batch(d.port, batch)
        assert isinstance(resp, list), f"批量响应应为 list，实际 {type(resp)}"
        assert len(resp) == 3, f"响应数应=请求数 3，实际 {len(resp)}"
        # 顺序与 id 一致
        assert [r["id"] for r in resp] == [1, 2, 3]
        # 每个都有 result
        for r in resp:
            assert "result" in r, f"批量内元素缺 result: {r}"
            assert r["result"]["status"] == "running"


def test_batch_single_failure_does_not_affect_others():
    """批量内单个失败（未知方法）返回 error，不影响其余。"""
    with _DaemonHandle(TEST_PORT + 61) as d:
        batch = [
            {"jsonrpc": "2.0", "method": "status", "params": {}, "id": 1},
            {"jsonrpc": "2.0", "method": "this_does_not_exist", "params": {}, "id": 2},
            {"jsonrpc": "2.0", "method": "status", "params": {}, "id": 3},
        ]
        resp = _rpc_batch(d.port, batch)
        assert isinstance(resp, list) and len(resp) == 3
        # 第 1、3 成功
        assert "result" in resp[0] and resp[0]["id"] == 1
        assert "result" in resp[2] and resp[2]["id"] == 3
        # 第 2 失败但隔离
        assert "error" in resp[1], f"未知方法应返回 error: {resp[1]}"
        assert resp[1]["error"]["code"] == -32601
        assert resp[1]["id"] == 2


def test_batch_mixed_methods_no_id_mismatch():
    """批量混合方法（status + 需 APK 方法）：响应 id 无错乱。"""
    with _DaemonHandle(TEST_PORT + 62) as d:
        batch = [
            {"jsonrpc": "2.0", "method": "status", "params": {}, "id": "a"},
            {"jsonrpc": "2.0", "method": "apk_info", "params": {}, "id": "b"},
            {"jsonrpc": "2.0", "method": "status", "params": {}, "id": "c"},
        ]
        resp = _rpc_batch(d.port, batch)
        assert isinstance(resp, list) and len(resp) == 3
        # id 无错乱（支持字符串 id）
        ids = [r["id"] for r in resp]
        assert ids == ["a", "b", "c"], f"批量响应 id 错乱: {ids}"
        # apk_info 未加载 APK 时应返回 error 或 result（结构化即可，不崩）
        assert "result" in resp[1] or "error" in resp[1]


@_NEED_APK
def test_batch_with_load_then_query():
    """批量内先 load 再查询：同批内顺序执行，查询能命中已加载。"""
    with _DaemonHandle(TEST_PORT + 63) as d:
        batch = [
            {"jsonrpc": "2.0", "method": "load_apk",
             "params": {"apk_path": _SMALL_APK}, "id": 1},
            {"jsonrpc": "2.0", "method": "apk_info", "params": {}, "id": 2},
            {"jsonrpc": "2.0", "method": "status", "params": {}, "id": 3},
        ]
        resp = _rpc_batch(d.port, batch, timeout=120)
        assert isinstance(resp, list) and len(resp) == 3
        # load 成功
        assert "result" in resp[0], f"load 失败: {resp[0]}"
        # 同批内 apk_info 应命中已加载（顺序执行）
        assert "result" in resp[1], f"批量内 load 后 apk_info 应成功: {resp[1]}"
        # status 显示已加载
        assert resp[2]["result"]["apk_loaded"] is True


def test_single_request_still_works():
    """单请求（dict）向后兼容：仍返回 dict 而非 list。"""
    with _DaemonHandle(TEST_PORT + 64) as d:
        with socket.create_connection(("127.0.0.1", d.port), timeout=10) as s:
            s.sendall((json.dumps(
                {"jsonrpc": "2.0", "method": "status", "params": {}, "id": 1}
            ) + "\n").encode())
            buf = b""
            while b"\n" not in buf:
                chunk = s.recv(65536)
                if not chunk:
                    break
                buf += chunk
        resp = json.loads(buf.split(b"\n", 1)[0].decode("utf-8"))
        assert isinstance(resp, dict), f"单请求应返回 dict，实际 {type(resp)}"
        assert resp["id"] == 1
        assert resp["result"]["status"] == "running"


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
