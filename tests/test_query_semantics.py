#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills 查询命令语义正确性回归测试

现有测试多为冒烟（命令能跑、输出合法 JSON）或结构校验（有某字段）。
但查询命令的**语义正确性**——对存在/不存在的输入返回正确的布尔/结果——
未严格验证。若底层逻辑反了（如 is_class_present 调用错返回反值），冒烟
测试抓不到（输出仍是合法 JSON，只是值错），agent 照错值下结论会误判
（/goal："对接几十个 agent"，语义错比结构错更隐蔽危险）。

本测试对若干查询命令验证语义：
  - analysis class-exists：存在的类 → exists:true；不存在的 → exists:false
  - analysis find-classes：能匹配的模式 → 非空；不匹配的 → 空
  - dex class-exists 等价（如有）

判据用确定性输入（测试 APK 里已知存在/不存在的类名/模式），非随机。

运行：``pytest tests/test_query_semantics.py -v``
独立：``python3 tests/test_query_semantics.py``
"""
import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))

_TEST_APK = os.path.join(HERE, "data", "APK", "TestActivity.apk")
_NEED_APK = pytest.mark.skipif(
    not os.path.exists(_TEST_APK), reason=f"测试 APK 不存在: {_TEST_APK}"
)

# TestActivity.apk 里确定存在的类（从 dex classes 实测）
_EXISTING_CLASS = "LTestDefaultPackage;"
_NONEXISTENT_CLASS = "Lcom/nonexistent/NoSuchClass;"


def _cli_json(*args, timeout=120):
    """运行 CLI 并解析 JSON，返回 dict 或 None。"""
    proc = subprocess.run(
        ["androguard-skills", *args],
        capture_output=True, text=True, timeout=timeout, cwd=REPO_ROOT,
    )
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


@_NEED_APK
def test_class_exists_returns_true_for_existing_class():
    """analysis class-exists 对存在的类必须返回 exists=true。"""
    real = _cli_json("analysis", "class-exists", _EXISTING_CLASS,
                     "--apk-path", _TEST_APK)
    assert real is not None, "analysis class-exists 输出异常"
    # 必须有布尔字段且为 True
    bool_field = real.get("exists", real.get("present", real.get("result")))
    assert bool_field is True, (
        f"对存在的类 {_EXISTING_CLASS}，class-exists 应返回 true，"
        f"实际: {real}"
    )


@_NEED_APK
def test_class_exists_returns_false_for_nonexistent_class():
    """analysis class-exists 对不存在的类必须返回 exists=false。"""
    real = _cli_json("analysis", "class-exists", _NONEXISTENT_CLASS,
                     "--apk-path", _TEST_APK)
    assert real is not None, "analysis class-exists 输出异常"
    bool_field = real.get("exists", real.get("present", real.get("result")))
    assert bool_field is False, (
        f"对不存在的类 {_NONEXISTENT_CLASS}，class-exists 应返回 false，"
        f"实际: {real}"
    )


@_NEED_APK
def test_find_classes_matches_existing_pattern():
    """analysis find-classes 用匹配模式必须返回非空结果。"""
    # TestDefaultPackage 确定存在，正则应匹配
    real = _cli_json("analysis", "find-classes", "TestDefaultPackage",
                     "--apk-path", _TEST_APK)
    assert real is not None, "analysis find-classes 输出异常"
    # 结果应非空（total>0 或 classes 列表非空）
    total = real.get("total", 0)
    classes = real.get("classes", real.get("items", real.get("results", [])))
    assert total > 0 or (classes and len(classes) > 0), (
        f"用匹配模式 TestDefaultPackage，find-classes 应返回非空，"
        f"实际: total={total}, classes={classes}"
    )


@_NEED_APK
def test_find_classes_returns_empty_for_nonmatching_pattern():
    """analysis find-classes 用不匹配模式必须返回空结果。"""
    real = _cli_json("analysis", "find-classes",
                     "ZZZNoSuchPatternXYZ12345",
                     "--apk-path", _TEST_APK)
    assert real is not None, "analysis find-classes 输出异常"
    total = real.get("total", -1)
    classes = real.get("classes", real.get("items", real.get("results", [])))
    assert total == 0 or (classes is not None and len(classes) == 0), (
        f"用不匹配模式，find-classes 应返回空，"
        f"实际: total={total}, classes={classes}"
    )


@_NEED_APK
def test_find_strings_returns_empty_for_nonmatching_pattern():
    """analysis find-strings 用不匹配模式必须返回空结果。"""
    real = _cli_json("analysis", "find-strings",
                     "ZZZNoSuchStringPatternXYZ99999",
                     "--apk-path", _TEST_APK)
    assert real is not None, "analysis find-strings 输出异常"
    total = real.get("total", -1)
    assert total == 0, (
        f"用不匹配模式，find-strings 应返回 total=0，实际: total={total}"
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
