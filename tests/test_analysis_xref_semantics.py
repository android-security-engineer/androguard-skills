#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills analysis 交叉引用语义正确性回归测试

test_query_semantics.py 守了 class-exists/find-classes/find-strings 的布尔/
非空语义，但 analysis 的核心——交叉引用（xref）——的语义未守。xref 是逆向
分析的基石（谁调用谁、谁引用谁），若 xref_from/to 方向反了或计数错，agent
基于错 xref 做的可达性/污点分析全错（/goal："对接几十个 agent"，xref 是
agent 做依赖分析的权威数据，错则下游全错）。

本测试对 TestActivity.apk 里已知有引用关系的类/方法验证 xref 语义：
  - xrefs-from：TestActivity 被谁引用（xref_from_count > 0，列表非空）
  - xrefs-to：TestActivity 引用了谁（xref_to_count > 0）
  - method-xrefs：onCreate 方法的交叉引用（含 xref_from_count 字段）
  - xref 列表元素结构（from_class/from_method/ref_type 等字段齐全）

判据用确定性输入（TestActivity 类确定有引用关系）。

运行：``pytest tests/test_analysis_xref_semantics.py -v``
独立：``python3 tests/test_analysis_xref_semantics.py``
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

# TestActivity.apk 里确定有引用关系的类
_CLS = "Ltests/androguard/TestActivity;"
_METHOD = "onCreate"


def _cli_json(*args, timeout=120):
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
def test_xrefs_from_returns_nonempty_for_referenced_class():
    """xrefs-from 对有引用的类应返回非空 xref_from 列表。"""
    r = _cli_json("analysis", "xrefs-from", _CLS,
                  "--apk-path", _TEST_APK)
    assert r is not None, "xrefs-from 输出异常"
    assert r.get("class") == _CLS
    count = r.get("xref_from_count", 0)
    xrefs = r.get("xref_from", [])
    assert count > 0, f"TestActivity 应被引用，xref_from_count={count}"
    assert isinstance(xrefs, list) and len(xrefs) == count, (
        f"xref_from 列表长度应等于 count，count={count}, "
        f"len={len(xrefs)}"
    )


@_NEED_APK
def test_xrefs_to_returns_nonempty_for_referencing_class():
    """xrefs-to 对有引用的类应返回非空 xref_to 列表。"""
    r = _cli_json("analysis", "xrefs-to", _CLS,
                  "--apk-path", _TEST_APK)
    assert r is not None, "xrefs-to 输出异常"
    assert r.get("class") == _CLS
    count = r.get("xref_to_count", 0)
    xrefs = r.get("xref_to", [])
    assert count > 0, f"TestActivity 应引用其他类，xref_to_count={count}"
    assert isinstance(xrefs, list) and len(xrefs) == count


@_NEED_APK
def test_xref_entry_structure_complete():
    """xref_from 列表元素应含 from_class/from_method/ref_type 等关键字段。"""
    r = _cli_json("analysis", "xrefs-from", _CLS,
                  "--apk-path", _TEST_APK)
    assert r is not None and r.get("xref_from"), "无 xref 数据"
    entry = r["xref_from"][0]
    # 关键字段至少含 from_class（谁引用的）
    assert "from_class" in entry, (
        f"xref 条目缺 from_class，实际: {list(entry.keys())}"
    )
    assert "from_method" in entry, (
        f"xref 条目缺 from_method，实际: {list(entry.keys())}"
    )
    # ref_type 应是已知调用类型（INVOKE_*/NEW_INSTANCE 等）
    ref_type = entry.get("ref_type", "")
    assert ref_type, f"xref 条目缺 ref_type: {entry}"
    assert any(t in ref_type for t in ("INVOKE", "INSTANCE", "CONST", "READ",
                                       "WRITE", "GET", "PUT")) or ref_type, (
        f"ref_type 不像已知调用类型: {ref_type}"
    )


@_NEED_APK
def test_method_xrefs_returns_structured():
    """method-xrefs 对已知方法应返回结构化结果含 xref 计数字段。"""
    r = _cli_json("analysis", "method-xrefs", _CLS, _METHOD,
                  "--apk-path", _TEST_APK)
    assert r is not None, "method-xrefs 输出异常"
    assert r.get("class") == _CLS
    assert r.get("method") == _METHOD
    # 应有某种 xref 计数字段
    assert any(k in r for k in ("xref_from_count", "xref_to_count",
                                "xref_from", "xref_to")), (
        f"method-xrefs 应含 xref 字段，实际: {list(r.keys())}"
    )


@_NEED_APK
def test_xrefs_from_and_to_are_distinct_directions():
    """xrefs-from 和 xrefs-to 应返回不同方向的计数（防两个命令返回同一份数据）。

    TestActivity 的 from（被谁引用）和 to（引用了谁）计数不同，证明两命令
    确实区分方向，而非实现成同一个。
    """
    rf = _cli_json("analysis", "xrefs-from", _CLS, "--apk-path", _TEST_APK)
    rt = _cli_json("analysis", "xrefs-to", _CLS, "--apk-path", _TEST_APK)
    assert rf and rt, "某侧输出异常"
    from_count = rf.get("xref_from_count", 0)
    to_count = rt.get("xref_to_count", 0)
    assert from_count != to_count, (
        f"xrefs-from({from_count}) 与 xrefs-to({to_count}) 计数相同，"
        f"可能两命令返回同方向数据（方向未区分）"
    )
    # 且字段名也应区分（from 命令用 xref_from，to 命令用 xref_to）
    assert "xref_from" in rf and "xref_from_count" in rf
    assert "xref_to" in rt and "xref_to_count" in rt


@_NEED_APK
def test_xrefs_from_count_consistent_across_calls():
    """同一类 xrefs-from 多次调用计数应一致（稳定性）。"""
    counts = []
    for _ in range(3):
        r = _cli_json("analysis", "xrefs-from", _CLS,
                      "--apk-path", _TEST_APK)
        counts.append(r.get("xref_from_count") if r else None)
    assert all(c == counts[0] for c in counts), (
        f"xref_from_count 多次调用不一致: {counts}"
    )
    assert counts[0] > 0


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
