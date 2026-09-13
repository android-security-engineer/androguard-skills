#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills CLI 输出确定性回归测试

同一 APK 多次运行同一命令，输出应字节级一致（agent 对接几十个时，非确定
输出让 agent 无法稳定比对）。

## 为什么需要两组 APK

- ``TestActivity.apk``（轻量）：覆盖基础命令（apk info/permissions、dex classes、
  find-classes 等）。早期 ``dex classes`` 因 ``cls.get_source()`` 返回反编译源码
  （局部变量声明序非确定）导致不稳定——已移除 source 字段。本组守护该回归。
- ``app-prod-debug.apk``（2454 类，含真实交叉引用）：覆盖所有遍历 set 的命令
  （method-xrefs / xrefs-from/to / call-graph / 漏洞审计 / method-reachable /
  class-fields-xref 等）。这些命令在 TestActivity 上因 xref 为空集（迭代序
  不可见）而恒稳定，**只有在含真实多元素 set 的复杂 APK 上才会暴露非确定性**。
  本组正是为捕获 set 迭代序 / networkx 图序 / 反编译器序等非确定源而设。

## 已捕获并修复的非确定根因

- ``dex classes``/``dex class``：``get_source()`` 反编译源码非确定 → 移除 source 字段
- ``method-xrefs`` / ``xrefs-from`` / ``xrefs-to``：``get_xref_from/to()`` 返回 set，
  迭代序非确定 → 扁平化后排序
- ``method-summary`` 的 ``_summarize_refs``：set 迭代后先切片再排序 → 改为先排序再切片
- ``insecure-storage`` / ``sql-injection`` / ``pending-intent`` / ``webview-security``：
  同构漏洞审计骨架，``results[cat]`` 来自 set 迭代，切片前未排序 → 加 ``items.sort``
- ``_xref_semantic_audit`` 共享内核：同上，修此内核 8 个漏洞审计命令受益
- ``method-reachable``：BFS 遍历 ``get_xref_to()`` set，入队序非确定 → 每层排序 + 终排序
- ``call-graph`` / ``call-graph-filtered``：networkx 图节点/边序取决于 set 驱动的
  ``create_xref`` 构建，非确定 → 对 nodes/edges 排序
- ``class-fields-xref``：``get_fields()`` + ``get_xref_read/write()`` 均 set，
  ``_xref_list`` 切片前未排序 → 加排序 + ``fields_out`` 排序
- ``apk permissions``：``get_permissions()`` 等 list 来自 set，且
  ``get_details_permissions()`` 等 dict 的 key 插入序来自 set → list 排序 + dict 按 key 重建
- ``apk activities/services/receivers/providers``：``get_activities()`` 等 list 来自 set，
  ``get_intent_filters()`` 返回 dict key 亦来自 set → 同上
- ``apk manifest-attrs``：``get_all_attribute_value()`` 返回 filter/set → list 排序
- ``apk manifest-tags``：``find_tags()`` 列表序非确定 + lxml ``attrib`` 迭代序非确定 →
  列表排序 + attrs dict 按 key 重建

运行：``pytest tests/test_cli_output_determinism.py -v``
独立：``python3 tests/test_cli_output_determinism.py``
"""
import hashlib
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))

# 两组基准 APK：
# - APK_LIGHT：轻量，覆盖基础命令（早期 get_source 非确定回归在此守住）
# - APK_COMPLEX：复杂（2454 类 + 真实 xref），覆盖所有 set 迭代类命令
APK_LIGHT = os.path.join(HERE, "data", "APK", "TestActivity.apk")
APK_COMPLEX = os.path.join(HERE, "data", "APK", "app-prod-debug.apk")

# app-prod-debug 中含真实交叉引用的类（用于 method/field xref 类命令）
_COMPLEX_CLASS = "Landroid/support/v4/app/JobIntentService;"


def _run_n_times(args, n=3):
    """运行命令 n 次，返回 n 个输出的 md5 hash 列表。

    每次先 ``daemon stop``：避免 daemon 缓存让 ``--apk-path`` 被忽略，
    进而把"加载了不同 APK"误判为"非确定"。
    """
    hashes = []
    for _ in range(n):
        subprocess.run(["androguard-skills", "daemon", "stop"],
                       capture_output=True, timeout=10, cwd=REPO_ROOT)
        p = subprocess.run(
            ["androguard-skills"] + args,
            capture_output=True, text=True, timeout=180, cwd=REPO_ROOT,
        )
        hashes.append(hashlib.md5(p.stdout.encode("utf-8")).hexdigest())
    return hashes


# ---- 轻量组（TestActivity.apk）：基础命令 + 早期 get_source 回归守卫 ----
_LIGHT_COMMANDS = [
    (["apk", "info", "--apk-path", APK_LIGHT], "apk info"),
    (["apk", "permissions", "--apk-path", APK_LIGHT], "apk permissions"),
    (["apk", "signature", "--apk-path", APK_LIGHT], "apk signature"),
    (["dex", "classes", "--apk-path", APK_LIGHT],
     "dex classes（曾因 get_source 非确定，已移除 source 字段）"),
    (["dex", "header", "--apk-path", APK_LIGHT], "dex header"),
    (["analysis", "find-classes", ".*", "--apk-path", APK_LIGHT], "analysis find-classes"),
    (["analysis", "find-methods", ".*", "--apk-path", APK_LIGHT], "analysis find-methods"),
    (["analysis", "android-api-usage", "--apk-path", APK_LIGHT],
     "analysis android-api-usage"),
    (["resources", "packages", "--apk-path", APK_LIGHT], "resources packages"),
]

# ---- 复杂组（app-prod-debug.apk）：所有遍历 set / networkx / BFS 的命令 ----
# 这些命令在 TestActivity 上因 xref 为空集恒稳定，必须用含真实多元素 set 的复杂 APK
# 才能暴露非确定性。每条都对应一个已修复的非确定根因（见模块 docstring）。
_COMPLEX_COMMANDS = [
    # 单方法 xref（get_xref_from/to set 迭代）
    (["analysis", "method-xrefs", _COMPLEX_CLASS, "onCreate", "--apk-path", APK_COMPLEX],
     "method-xrefs（get_xref_from/to set 排序）"),
    (["analysis", "method-xrefs-detail", _COMPLEX_CLASS, "onCreate", "--apk-path", APK_COMPLEX],
     "method-xrefs-detail"),
    (["analysis", "method-summary", _COMPLEX_CLASS, "onCreate", "--no-source", "--apk-path", APK_COMPLEX],
     "method-summary --no-source（_summarize_refs 先排序再切片）"),
    # 类级 xref
    (["analysis", "xrefs-from", _COMPLEX_CLASS, "--apk-path", APK_COMPLEX],
     "xrefs-from（set 排序）"),
    (["analysis", "xrefs-to", _COMPLEX_CLASS, "--apk-path", APK_COMPLEX],
     "xrefs-to（set 排序）"),
    (["analysis", "class-fields-xref", _COMPLEX_CLASS, "--apk-path", APK_COMPLEX],
     "class-fields-xref（get_fields + get_xref_read/write set 排序）"),
    (["analysis", "class-xref-new-instance", _COMPLEX_CLASS, "--apk-path", APK_COMPLEX],
     "class-xref-new-instance"),
    (["analysis", "class-xref-const-class", _COMPLEX_CLASS, "--apk-path", APK_COMPLEX],
     "class-xref-const-class"),
    # 图遍历（networkx 节点/边序 + BFS set 入队序）
    (["analysis", "call-graph", "--apk-path", APK_COMPLEX],
     "call-graph（networkx nodes/edges 排序）"),
    (["analysis", "method-reachable", _COMPLEX_CLASS, "onCreate", "--max-depth", "2",
      "--apk-path", APK_COMPLEX],
     "method-reachable（BFS 每层 set 排序 + 终排序）"),
    # 全量漏洞审计（_xref_semantic_audit 内核 + 同构骨架 items.sort）
    (["analysis", "insecure-storage", "--apk-path", APK_COMPLEX],
     "insecure-storage（同构 items.sort）"),
    (["analysis", "sql-injection", "--apk-path", APK_COMPLEX],
     "sql-injection（同构 items.sort）"),
    (["analysis", "pending-intent", "--apk-path", APK_COMPLEX],
     "pending-intent（同构 items.sort）"),
    (["analysis", "webview-security", "--apk-path", APK_COMPLEX],
     "webview-security（同构 items.sort）"),
    (["analysis", "privacy-sinks", "--apk-path", APK_COMPLEX],
     "privacy-sinks（_xref_semantic_audit 内核）"),
    (["analysis", "security-hotspots", "--apk-path", APK_COMPLEX],
     "security-hotspots（_xref_semantic_audit 内核）"),
    (["analysis", "anti-analysis", "--apk-path", APK_COMPLEX],
     "anti-analysis（_xref_semantic_audit 内核）"),
    (["analysis", "ssl-safety", "--apk-path", APK_COMPLEX],
     "ssl-safety（_xref_semantic_audit 内核）"),
    # 聚合审计（get_methods set 迭代 + dict {k:samples} 按 key 重建）
    (["analysis", "crypto-usage", "--apk-path", APK_COMPLEX],
     "crypto-usage（usages/material dict 按 key 重建 + samples 排序）"),
    (["analysis", "reflection-targets", "--apk-path", APK_COMPLEX],
     "reflection-targets（categories dict 按 key 重建 + samples 排序）"),
    (["analysis", "url-endpoints", "--apk-path", APK_COMPLEX],
     "url-endpoints（origins 排序 + buckets 排序 + summary dict 按 key 重建）"),
    (["analysis", "anti-analysis", "--apk-path", APK_COMPLEX],
     "anti-analysis（字符串 xf 排序 + items 排序）"),
    # find-* 全量（get_classes/get_methods set 迭代）
    (["analysis", "find-classes", ".*", "--apk-path", APK_COMPLEX],
     "find-classes 全量（复杂 APK）"),
    (["analysis", "find-methods", ".*", "--apk-path", APK_COMPLEX],
     "find-methods 全量（复杂 APK）"),
    (["analysis", "find-fields", ".*", "--apk-path", APK_COMPLEX],
     "find-fields 全量（复杂 APK）"),
    (["analysis", "find-strings", "--apk-path", APK_COMPLEX],
     "find-strings（origins 排序）"),
    # dex/apk 复杂样本
    (["dex", "classes", "--apk-path", APK_COMPLEX], "dex classes（复杂 APK）"),
    (["apk", "info", "--apk-path", APK_COMPLEX], "apk info（复杂 APK）"),
    (["apk", "permissions", "--apk-path", APK_COMPLEX],
     "apk permissions（list 排序 + dict 按 key 重建）"),
    (["apk", "activities", "--apk-path", APK_COMPLEX],
     "apk activities（list 排序 + intent_filters dict 按 key 重建）"),
    (["apk", "services", "--apk-path", APK_COMPLEX],
     "apk services（list 排序 + intent_filters dict 按 key 重建）"),
    (["apk", "receivers", "--apk-path", APK_COMPLEX],
     "apk receivers（list 排序 + intent_filters dict 按 key 重建）"),
    (["apk", "providers", "--apk-path", APK_COMPLEX],
     "apk providers（list 排序 + intent_filters dict 按 key 重建）"),
    (["apk", "manifest-attrs", "--tag", "uses-permission", "--attribute", "name",
      "--apk-path", APK_COMPLEX],
     "apk manifest-attrs（get_all_attribute_value set 排序）"),
    (["apk", "manifest-tags", "--tag", "uses-permission", "--apk-path", APK_COMPLEX],
     "apk manifest-tags（find_tags 列表 + attrib dict 按 key 重建）"),
]


def _light_cases():
    """轻量组仅在 TestActivity.apk 存在时启用。"""
    if not os.path.exists(APK_LIGHT):
        return []
    return _LIGHT_COMMANDS


def _complex_cases():
    """复杂组仅在 app-prod-debug.apk 存在时启用。"""
    if not os.path.exists(APK_COMPLEX):
        return []
    return _COMPLEX_COMMANDS


@pytest.mark.parametrize("args,desc", _light_cases(),
                         ids=[d.split("（")[0] for _, d in _light_cases()])
def test_deterministic_light(args, desc):
    """轻量 APK：基础命令 3 次输出 hash 必须一致。"""
    hashes = _run_n_times(args, n=3)
    assert len(set(hashes)) == 1, (
        f"{desc} 输出非确定：3 次 hash 不一致 {hashes}。\n"
        f"可能原因：命令调用了反编译器/集合迭代等非确定操作。"
    )


@pytest.mark.parametrize("args,desc", _complex_cases(),
                         ids=[d.split("（")[0] for _, d in _complex_cases()])
def test_deterministic_complex(args, desc):
    """复杂 APK（含真实多元素 set）：遍历 set/networkx/BFS 的命令 3 次输出 hash
    必须一致。这组测试是捕获 set 迭代序非确定性的关键——空集 APK 测不出。"""
    hashes = _run_n_times(args, n=3)
    assert len(set(hashes)) == 1, (
        f"{desc} 输出非确定：3 次 hash 不一致 {hashes}。\n"
        f"可能原因：命令遍历 set（get_xref_from/to/get_fields 等）或 networkx 图\n"
        f"未对输出列表排序。agent 对接需要确定性输出以稳定比对。"
    )


if __name__ == "__main__":
    all_cases = _light_cases() + _complex_cases()
    passed = failed = 0
    for args, desc in all_cases:
        try:
            hashes = _run_n_times(args, n=3)
            assert len(set(hashes)) == 1
            print(f"  PASS  {desc}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {desc}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed, {len(all_cases)} total")
    sys.exit(1 if failed else 0)
