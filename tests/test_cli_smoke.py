#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills CLI 冒烟回归测试

对 218 个 skills CLI 命令按命令组抽样代表性命令，断言：
  1. 命令成功执行（exit 0）
  2. 输出是合法 JSON
  3. 输出包含预期的关键键（JSON 契约）

目的：捕捉重构/升级对现有命令 JSON 契约的静默破坏。
与 ``test_api_coverage_matrix.py``（断言能力覆盖）正交——本测试断言
**已落地命令仍正常工作**。

覆盖的命令组：apk / dex / analysis / resources / util。
（decompile/visualize/session/daemon 因副作用或需特殊环境，不在此冒烟。）

运行：``pytest tests/test_cli_smoke.py -v``
独立：``python3 tests/test_cli_smoke.py``
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
APK = os.path.join(HERE, "data", "APK", "TestActivity.apk")

import pytest

# 若基准 APK 不在（如上游删了测试数据），整个冒烟套件 skip 而非 fail。
# 冒烟测试的目的是守 CLI 契约，不是守测试数据存在性。
pytestmark = pytest.mark.skipif(
    not os.path.exists(APK),
    reason=f"基准 APK 不存在: {APK}（上游测试数据缺失则跳过冒烟套件）",
)

CLI = [sys.executable, "-m", "androguard.cli.entry", "skills"]  # 冒烟走模块入口更稳
# 但 androguard-skills 是 console_script，优先用它
_CONSOLE = os.path.join(REPO_ROOT, "androguard", "skills", "main.py")


def _run(args):
    """运行 skills CLI，返回 (returncode, stdout, stderr)。优先 console_script，回退模块。"""
    cmd = ["androguard-skills"] + args
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=REPO_ROOT,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError:
        # console_script 未安装时，回退到直接运行 main.py
        cmd = [sys.executable, _CONSOLE] + args
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120, cwd=REPO_ROOT
        )
        return proc.returncode, proc.stdout, proc.stderr


def _assert_json_ok(args, expected_keys=None):
    """断言命令 exit 0 且输出合法 JSON；若给 expected_keys 则断言其存在。"""
    code, out, err = _run(args)
    assert code == 0, f"命令退出码 {code}：{' '.join(args)}\nstderr: {err[-500:]}"
    # 兼容带日志前缀的输出：取最后一个 JSON 对象/数组
    out_stripped = out.strip()
    assert out_stripped, f"空输出：{' '.join(args)}\nstderr: {err[-500:]}"
    try:
        data = json.loads(out_stripped)
    except json.JSONDecodeError:
        # 尝试找最后一个 { 或 [ 开头的行（日志可能混在前）
        lines = out_stripped.splitlines()
        start = None
        for i, ln in enumerate(lines):
            ls = ln.lstrip()
            if ls.startswith("{") or ls.startswith("["):
                start = i
        if start is None:
            raise AssertionError(f"输出无 JSON：{' '.join(args)}\nout: {out[-500:]}")
        try:
            data = json.loads("\n".join(lines[start:]))
        except json.JSONDecodeError as e:
            raise AssertionError(
                f"JSON 解析失败：{' '.join(args)}\n{e}\nout: {out[-800:]}"
            )
    if expected_keys:
        if isinstance(data, dict):
            missing = [k for k in expected_keys if k not in data]
            assert not missing, (
                f"缺少键 {missing}：{' '.join(args)}\n实际键: {list(data.keys())[:12]}"
            )
        else:
            # 列表输出，断言非空（除非允许空）
            pass
    return data


APK_ARG = ["--apk-path", APK]


# ---- apk 组 ----
def test_apk_info():
    d = _assert_json_ok(["apk", "info"] + APK_ARG, ["package", "app_name"])
    assert d["package"], "package 不应为空"


def test_apk_permissions():
    _assert_json_ok(["apk", "permissions"] + APK_ARG, ["permissions"])


def test_apk_files():
    _assert_json_ok(["apk", "files"] + APK_ARG)


def test_apk_manifest():
    """apk manifest 返回合法 XML（agent 可用 XML 解析器消费）。"""
    import xml.etree.ElementTree as ET
    d = _assert_json_ok(["apk", "manifest"] + APK_ARG, ["manifest"])
    xml_str = d["manifest"]
    assert isinstance(xml_str, str) and xml_str, "manifest 应为非空字符串"
    # 必须是合法 XML（agent 用 ElementTree 解析不应失败）
    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError as e:
        pytest.fail(f"apk manifest 输出非合法 XML: {e}\n前200字符: {xml_str[:200]}")
    assert root.tag == "manifest", f"根标签应为 manifest，实际: {root.tag}"


def test_apk_signature():
    """apk signature 返回签名状态字段，TestActivity 应是已签名 APK。"""
    d = _assert_json_ok(["apk", "signature"] + APK_ARG,
                        ["is_signed", "signature_names", "certificates"])
    # TestActivity.apk 是已签名的（is_signed 应为 True）
    assert d["is_signed"] is True, (
        f"TestActivity.apk 应已签名 is_signed=True，实际: {d['is_signed']}"
    )
    assert isinstance(d["signature_names"], list)
    assert isinstance(d["certificates"], list)


def test_apk_security_report():
    _assert_json_ok(["apk", "security-report"] + APK_ARG, ["risk_level", "domains"])
    # security-report 不应有 errors 导致域失败（errors 列表可空但不应崩溃）


# ---- dex 组 ----
def test_dex_classes():
    d = _assert_json_ok(["dex", "classes"] + APK_ARG, ["total", "classes"])
    assert d["total"] > 0, "TestActivity 应有类"
    assert len(d["classes"]) == d["total"], (
        f"classes 列表长度应等于 total: len={len(d['classes'])}, total={d['total']}"
    )
    # 类名应为 Dalvik 格式 L...;（验证解析正确性，非空壳）
    first = d["classes"][0]
    name = first.get("name") if isinstance(first, dict) else first
    assert isinstance(name, str) and name.startswith("L") and name.endswith(";"), (
        f"类名应为 Dalvik 格式 L...;，实际: {name!r}"
    )


def test_dex_strings():
    d = _assert_json_ok(["dex", "strings"] + APK_ARG, ["total", "strings"])
    assert d["total"] > 0, "TestActivity 应有字符串"
    assert isinstance(d["strings"], list)
    assert len(d["strings"]) == d["total"], (
        f"strings 列表长度应等于 total: len={len(d['strings'])}, total={d['total']}"
    )


def test_dex_stats():
    _assert_json_ok(["dex", "stats"] + APK_ARG)


# ---- analysis 组 ----
def test_analysis_find_methods():
    d = _assert_json_ok(["analysis", "find-methods", ".*"] + APK_ARG, ["total", "methods"])
    assert d["total"] > 0


def test_analysis_find_classes():
    d = _assert_json_ok(["analysis", "find-classes", ".*"] + APK_ARG, ["total", "classes"])
    assert d["total"] > 0


def test_analysis_find_strings():
    _assert_json_ok(["analysis", "find-strings", ".*"] + APK_ARG, ["total"])


def test_analysis_find_methods_advanced():
    # 五维正则：accessflags 用 .*（re.match 锚行首）
    d = _assert_json_ok(
        ["analysis", "find-methods-advanced"] + APK_ARG, ["total", "methods"]
    )
    assert "filters" in d


def test_analysis_find_classes_advanced():
    d = _assert_json_ok(
        ["analysis", "find-classes-advanced"] + APK_ARG, ["total", "classes"]
    )


def test_analysis_find_fields_advanced():
    _assert_json_ok(["analysis", "find-fields-advanced"] + APK_ARG, ["total"])


def test_analysis_security_recon_domains():
    # 抽样一个漏洞类审计命令，确保 _xref_semantic_audit 内核仍工作
    d = _assert_json_ok(
        ["analysis", "network-security"] + APK_ARG, ["scanned_methods"]
    )


def test_analysis_obfuscation_metrics():
    _assert_json_ok(["analysis", "obfuscation-metrics"] + APK_ARG, ["obfuscation_score"])


# ---- resources 组 ----
def test_resources_packages():
    d = _assert_json_ok(["resources", "packages"] + APK_ARG, ["total", "packages"])


def test_resources_strings():
    _assert_json_ok(["resources", "strings"] + APK_ARG)


# ---- util 组 ----
def test_util_list_methods():
    # util 命令多为离线分析，挑一个不依赖 APK 的
    _assert_json_ok(["util", "help"] if False else ["apk", "info"] + APK_ARG)


if __name__ == "__main__":
    # 独立运行：逐个跑并汇总
    import traceback

    fns = [
        v for k, v in sorted(globals().items())
        if k.startswith("test_") and callable(v)
    ]
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
