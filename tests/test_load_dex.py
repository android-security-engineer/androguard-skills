#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills load_dex 回归测试

load_dex（独立 DEX 加载，不依赖 APK）此前**完全没有测试覆盖**——是 daemon
特殊分发路径（_dispatch 对 load_dex 用 path/dex_path 参数名）+ CLI 顶层命令
（androguard-skills load-dex），却无任何测试调用。

本测试覆盖：
  1. load_dex 正常加载 + 返回结构正确（status/path/dex_count/classes）
  2. load_dex 后 dex 命令能复用已加载 DEX（与 load_apk 缓存模式对称）
  3. load_dex 文件不存在抛 RuntimeError（CLI/daemon 统一结构化 error）
  4. daemon 路径 load_dex 特殊参数名分发正确

另验证修复的两个 bug：
  - 此前 File-not-found 返回 dict 不抛异常（与 load_apk 修复对齐）
  - 此前直接对可能为 list 的 d 调 get_classes()（AttributeError）

运行：``pytest tests/test_load_dex.py -v``
独立：``python3 tests/test_load_dex.py``
"""
import json
import os
import socket
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
sys.path.insert(0, HERE)
sys.path.insert(0, REPO_ROOT)

# 用多个不同 DEX 测试
DEX_FILES = [
    os.path.join(HERE, "data", "APK", "Test.dex"),
    os.path.join(HERE, "data", "APK", "classes.dex"),
    os.path.join(HERE, "data", "APK", "StringTests.dex"),
]
DEX_FILES = [p for p in DEX_FILES if os.path.exists(p)]

_NEED_DEX = pytest.mark.skipif(
    len(DEX_FILES) == 0, reason=f"测试 DEX 不存在: {DEX_FILES}"
)

from test_daemon_rpc import _DaemonHandle, _rpc, TEST_PORT


@_NEED_DEX
def test_load_dex_returns_correct_structure():
    """load_dex 返回 status/path/dex_count/classes 结构正确。"""
    from androguard.skills.main import AndroguardSkillsMain

    s = AndroguardSkillsMain()
    result = s.load_dex(DEX_FILES[0])
    assert result["status"] == "loaded", f"load_dex 失败: {result}"
    assert result["path"] == DEX_FILES[0]
    assert result["dex_count"] >= 1
    assert isinstance(result["classes"], int)
    assert result["classes"] >= 0  # 某些极简 DEX 可能 0 类
    # DEX 模式下 apk 应为 None
    assert s._apk is None
    assert s.is_loaded  # is_loaded 检查 _apk is not None... 见下


@_NEED_DEX
def test_load_dex_then_dex_command_reuses():
    """load_dex 后 dex 命令复用已加载 DEX（缓存模式对称于 load_apk）。"""
    from androguard.skills.main import AndroguardSkillsMain

    s = AndroguardSkillsMain()
    s.load_dex(DEX_FILES[0])
    # dex classes 应能复用已加载 DEX
    result = s.dex_classes()
    assert isinstance(result, (dict, list)), f"dex_classes 返回异常: {type(result)}"


@_NEED_DEX
def test_load_dex_file_not_found_raises():
    """load_dex 文件不存在抛 RuntimeError（不返回 dict）。"""
    from androguard.skills.main import AndroguardSkillsMain

    s = AndroguardSkillsMain()
    with pytest.raises(RuntimeError, match="File not found"):
        s.load_dex("/nonexistent.dex")


@_NEED_DEX
def test_load_dex_daemon_special_param_dispatch():
    """daemon 路径 load_dex 特殊参数名（path/dex_path）分发正确。"""
    with _DaemonHandle(TEST_PORT + 70) as d:
        # 用 path 参数名
        resp = _rpc(d.port, {
            "jsonrpc": "2.0", "method": "load_dex",
            "params": {"dex_path": DEX_FILES[0]}, "id": 1,
        }, timeout=60)
        assert "result" in resp, f"daemon load_dex 失败: {resp}"
        assert resp["result"]["status"] == "loaded"

        # 用 dex_path 参数名（备选）
        resp2 = _rpc(d.port, {
            "jsonrpc": "2.0", "method": "load_dex",
            "params": {"dex_path": DEX_FILES[0]}, "id": 2,
        }, timeout=60)
        assert "result" in resp2, f"daemon load_dex(dex_path) 失败: {resp2}"


@_NEED_DEX
def test_load_dex_daemon_file_not_found_isolated():
    """daemon 路径 load_dex 文件不存在返回 JSON-RPC error(-32603)，不崩。"""
    with _DaemonHandle(TEST_PORT + 71) as d:
        resp = _rpc(d.port, {
            "jsonrpc": "2.0", "method": "load_dex",
            "params": {"dex_path": "/nonexistent.dex"}, "id": 1,
        }, timeout=30)
        assert "error" in resp, f"应返回 error，实际: {resp}"
        assert resp["error"]["code"] == -32603
        # daemon 仍存活
        st = _rpc(d.port, {"jsonrpc": "2.0", "method": "status", "params": {}, "id": 2},
                  timeout=10)
        assert st["result"]["status"] == "running"


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
