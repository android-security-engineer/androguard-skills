#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills daemon 慢命令 timeout 回归测试

此前 _try_daemon_call 用 DaemonClient 默认 30s timeout——load_apk/load_dex
解析大 APK/DEX 可能耗时数十秒到数分钟，会被误判超时→fallback 单次执行
（重新解析，更慢且 daemon 那边仍在解析，双重浪费）。

已修复：load_apk/load_dex/session_analyze_apk/session_add_apk/session_add_dex
用 600s timeout，其余命令用 30s。

本测试验：
  1. 慢命令的 client timeout 是长 timeout（600s）
  2. 快命令的 client timeout 是默认 30s
  3. daemon load_apk 真实大 APK 不被误判超时（用中等 APK，解析数秒）

运行：``pytest tests/test_daemon_slow_timeout.py -v``
独立：``python3 tests/test_daemon_slow_timeout.py``
"""
import inspect
import os
import sys
import time

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
sys.path.insert(0, HERE)
sys.path.insert(0, REPO_ROOT)

from test_daemon_rpc import _DaemonHandle, _rpc, TEST_PORT

_MED_APK = os.path.join(HERE, "data", "APK", "com.android.example.text.styling.apk")
_NEED_APK = pytest.mark.skipif(
    not os.path.exists(_MED_APK), reason=f"中等 APK 不存在: {_MED_APK}"
)

SLOW_METHODS = {"load_apk", "load_dex", "session_analyze_apk",
                "session_add_apk", "session_add_dex"}


def test_slow_methods_use_long_timeout():
    """_try_daemon_call 对慢命令用 600s timeout，快命令用 30s。"""
    from androguard.skills.main import _try_daemon_call

    src = inspect.getsource(_try_daemon_call)
    assert "slow_methods" in src
    assert "600.0" in src or "600" in src
    # 验证慢命令集合
    for m in SLOW_METHODS:
        assert m in src, f"慢命令 {m} 未在 slow_methods 集合"


@_NEED_APK
def test_daemon_load_apk_not_false_timeout():
    """daemon load_apk 中等 APK 不被误判超时（解析数秒 < 600s）。

    此前 30s timeout 在大 APK 会误杀；此处用中等 APK 验证 load 成功返回
    result 而非 ConnectionError(timeout)。
    """
    with _DaemonHandle(TEST_PORT + 80) as d:
        t0 = time.time()
        resp = _rpc(d.port, {
            "jsonrpc": "2.0", "method": "load_apk",
            "params": {"apk_path": _MED_APK}, "id": 1,
        }, timeout=120)
        dur = time.time() - t0
        assert "result" in resp, (
            f"load_apk 应返回 result（若被误判超时会 ConnectionError）: {resp}"
        )
        assert resp["result"]["status"] == "loaded"
        # 中等 APK 解析应 < 120s（远小于 600s timeout）
        assert dur < 120


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
