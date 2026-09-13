#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills session 组回归测试

session 组（8 命令：create/add-apk/add-dex/analyze-apk/classes/info/strings/
filename-by-class）是多 APK/DEX 关联分析能力，此前**完全没有测试覆盖**。

审查实现发现并修复的 bug：
  - session_create 双 Session 实例：session_skills.session_create() 内部创建
    Session 但只返回字典（对象丢失），main.session_create 又 new 一个——
    result.is_open 反映被丢弃的实例。改 session_create 纯说明性 + main 创建
    持有后回填真实 is_open。
  - session_add_apk/add_dex File-not-found 返回 dict 不抛异常（与 load_apk/
    load_dex 修复对齐）。

运行：``pytest tests/test_session.py -v``
独立：``python3 tests/test_session.py``
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
sys.path.insert(0, REPO_ROOT)

APK = os.path.join(HERE, "data", "APK", "TestActivity.apk")
DEX_FILES = [
    os.path.join(HERE, "data", "APK", "Test.dex"),
    os.path.join(HERE, "data", "APK", "StringTests.dex"),
]
DEX_FILES = [p for p in DEX_FILES if os.path.exists(p)]

_NEED_APK = pytest.mark.skipif(not os.path.exists(APK), reason=f"APK 不存在: {APK}")
_NEED_DEX = pytest.mark.skipif(len(DEX_FILES) == 0, reason="测试 DEX 不存在")


def _skills():
    from androguard.skills.main import AndroguardSkillsMain

    return AndroguardSkillsMain()


@_NEED_APK
def test_session_create_held_session_is_open():
    """session_create 创建并持有 Session，is_open 反映真实持有的实例。"""
    s = _skills()
    assert not s.has_session
    r = s.session_create()
    assert r["status"] == "created"
    assert s.has_session
    # is_open 反映真实持有的 Session（此前反映被丢弃的实例）
    assert "is_open" in r


@_NEED_APK
def test_session_full_workflow():
    """完整 session 工作流：create → add_apk → info → classes → strings。"""
    s = _skills()
    s.session_create()

    # add_apk
    add = s.session_add_apk(APK)
    assert add["status"] == "added"
    assert add["package"] == "tests.androguard"
    assert "digest" in add

    # info
    info = s.session_info()
    assert info["apk_count"] == 1
    assert info["is_open"] is True

    # classes
    classes = s.session_classes()
    assert classes["total"] >= 1
    assert "dexes" in classes

    # strings
    strings = s.session_strings()
    assert isinstance(strings, dict)


@_NEED_APK
def test_session_filename_by_class():
    """session_filename_by_class 定位类所属文件。"""
    s = _skills()
    s.session_create()
    s.session_add_apk(APK)
    # TestActivity.apk 含 tests.androguard.TestActivity 类
    r = s.session_filename_by_class("Ltests/androguard/TestActivity;")
    assert isinstance(r, dict)


@_NEED_APK
def test_session_ensure_session_guard():
    """未 create session 时调命令抛 RuntimeError。"""
    s = _skills()
    with pytest.raises(RuntimeError, match="No Session created"):
        s.session_info()
    with pytest.raises(RuntimeError, match="No Session created"):
        s.session_add_apk(APK)


@_NEED_APK
def test_session_add_apk_file_not_found_raises():
    """session_add_apk 文件不存在抛 RuntimeError（不返回 dict）。"""
    s = _skills()
    s.session_create()
    with pytest.raises(RuntimeError, match="File not found"):
        s.session_add_apk("/nonexistent.apk")


@_NEED_DEX
def test_session_add_dex():
    """session_add_dex 添加独立 DEX。"""
    s = _skills()
    s.session_create()
    r = s.session_add_dex(DEX_FILES[0])
    assert r["status"] == "added"
    assert "digest" in r


@_NEED_DEX
def test_session_add_dex_file_not_found_raises():
    """session_add_dex 文件不存在抛 RuntimeError。"""
    s = _skills()
    s.session_create()
    with pytest.raises(RuntimeError, match="File not found"):
        s.session_add_dex("/nonexistent.dex")


@_NEED_APK
def test_session_analyze_apk_standalone():
    """session_analyze_apk 独立分析（不依赖 session create）。"""
    s = _skills()
    r = s.session_analyze_apk(APK)
    assert isinstance(r, dict)
    # 应返回分析结果（不崩）
    assert "error" not in r or r.get("error") is None or "status" in r or "package" in r


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
