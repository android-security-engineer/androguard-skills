#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills 文档输出字段一致性回归测试

文档参数签名已由 test_docs_param_consistency.py 四层硬校验。但文档里的
**输出字段表**（形如 `| field | type | desc |`）描述的 JSON 输出字段名是否与
实跑一致未校验——agent 解析返回 JSON 时按文档字段名取值，字段名错了会取空
（/goal："对接几十个 agent"，字段漂移让 agent 静默取错值）。

本测试对若干关键命令实跑，提取真实输出顶层 keys，核对：
  1. 文档字段表里列的字段名必须在真实输出 keys 里（文档杜撰字段 → agent
     取空值）
  2. 真实输出里有但文档未列的字段仅信息性提示（不 fail，新增字段忘回填
     文档不一定是 bug）

字段表归属：参数表上方最近的 `## G S` 标题命令。文档里反引号包裹的字段名
在字段说明列的，提取为文档字段名。

代表性抽查（非全量——全量需每命令实跑耗时大，且很多命令输出依赖特定 APK
内容）。选输出结构稳定、agent 高频用的命令：apk info / dex header /
analysis class-exists / resources packages。

运行：``pytest tests/test_docs_output_fields.py -v``
独立：``python3 tests/test_docs_output_fields.py``
"""
import json
import os
import re
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
SKILLS_DIR = os.path.join(REPO_ROOT, "SKILLS")

# 测试 APK
_TEST_APK = os.path.join(HERE, "data", "APK", "TestActivity.apk")
_NEED_APK = pytest.mark.skipif(
    not os.path.exists(_TEST_APK), reason=f"测试 APK 不存在: {_TEST_APK}"
)


def _cli(*args, timeout=60):
    """运行 androguard-skills CLI，返回 (code, stdout, stderr)。"""
    proc = subprocess.run(
        ["androguard-skills", *args],
        capture_output=True, text=True, timeout=timeout, cwd=REPO_ROOT,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _cli_json(*args, timeout=60):
    """运行 CLI 并解析 JSON 输出，返回 dict 或 None。"""
    code, out, _ = _cli(*args, timeout=timeout)
    if code != 0:
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return None


# --------------------------------------------------------------------
# 文档字段表提取
# --------------------------------------------------------------------

_HEADING_CMD_RE = re.compile(
    r"^##\s+`?(apk|dex|analysis|resources|decompile|util|session|"
    r"visualize|pentest)\s+([a-z][a-z0-9-]*)"
)
# 命令示例行：androguard-skills G S ...
_CMD_EXAMPLE_RE = re.compile(
    r"androguard-skills\s+(apk|dex|analysis|resources|decompile|util|"
    r"session|visualize|pentest)\s+([a-z][a-z0-9-]*)"
)
# 字段说明表行：| `field_name` | type | desc |
_FIELD_TABLE_RE = re.compile(r"^\|\s*`([a-z_][a-z0-9_]*)`\s*\|")


def _doc_fields_for(group: str, subcmd: str) -> set:
    """从 SKILLS/*.md 提取指定命令文档字段表里的字段名集合。

    锚点用命令示例行（androguard-skills G S）或 `## G S` 标题——两者都
    标识命令段开始。收集锚点后到下一个锚点之间的字段表行里反引号包裹的
    字段名。两种锚点都试，覆盖不同文档风格。
    """
    target = (group, subcmd)
    fields = set()
    for fname in sorted(os.listdir(SKILLS_DIR)):
        if not fname.endswith(".md"):
            continue
        current = None
        with open(os.path.join(SKILLS_DIR, fname), "r", encoding="utf-8") as fh:
            for line in fh:
                # 命令示例行锚点
                em = _CMD_EXAMPLE_RE.search(line)
                if em:
                    current = (em.group(1), em.group(2))
                    continue
                # ## 标题锚点
                hm = _HEADING_CMD_RE.match(line)
                if hm:
                    current = (hm.group(1), hm.group(2))
                    continue
                if current != target:
                    continue
                fm = _FIELD_TABLE_RE.match(line)
                if fm:
                    fields.add(fm.group(1))
    return fields


# --------------------------------------------------------------------
# 测试
# --------------------------------------------------------------------


def _all_keys(obj, prefix="") -> set:
    """递归收集 dict 的所有层字段名（含嵌套），扁平化为集合。

    输出可能是嵌套结构（如 dex header 是 {"header": {...}}），文档字段表
    列的是叶子字段名，故需递归收集所有层 key 再比对。
    """
    keys = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.add(k)
            keys |= _all_keys(v)
    elif isinstance(obj, list):
        for item in obj:
            keys |= _all_keys(item)
    return keys


@_NEED_APK
def test_apk_info_fields_match():
    """apk info 文档字段表 vs 真实输出 keys。"""
    real = _cli_json("apk", "info", "--apk-path", _TEST_APK)
    assert real is not None and "package" in real, "apk info 输出异常"
    doc = _doc_fields_for("apk", "info")
    assert doc, "未在文档找到 apk info 字段表"
    real_keys = _all_keys(real)
    # 文档字段必须在真实输出里（含嵌套层）
    ghost = doc - real_keys
    # 真实输出里但文档未列的（信息性）
    undocumented = real_keys - doc
    assert not ghost, (
        f"apk info 文档字段表列了但真实输出没有的字段（agent 取空值）: "
        f"{sorted(ghost)}"
    )
    if undocumented:
        print(f"\n[信息] apk info 真实输出有但文档未列的字段: "
              f"{sorted(undocumented)}")


@_NEED_APK
def test_dex_header_fields_match():
    """dex header 文档字段表 vs 真实输出 keys（含嵌套）。"""
    real = _cli_json("dex", "header", "--apk-path", _TEST_APK)
    assert real is not None, "dex header 输出异常"
    doc = _doc_fields_for("dex", "header")
    if not doc:
        pytest.skip("dex header 无文档字段表")
    real_keys = _all_keys(real)
    ghost = doc - real_keys
    assert not ghost, (
        f"dex header 文档字段表列了但真实输出没有的字段: {sorted(ghost)}"
    )


@_NEED_APK
def test_resources_packages_fields_match():
    """resources packages 文档字段表 vs 真实输出 keys。"""
    real = _cli_json("resources", "packages", "--apk-path", _TEST_APK)
    assert real is not None, "resources packages 输出异常"
    doc = _doc_fields_for("resources", "packages")
    if not doc:
        pytest.skip("resources packages 无文档字段表")
    # 递归收集所有层 key（list/dict 都能处理）
    real_keys = _all_keys(real)
    ghost = doc - real_keys
    assert not ghost, (
        f"resources packages 文档字段表列了但真实输出没有的字段: "
        f"{sorted(ghost)}"
    )


def test_analysis_class_exists_output_structure():
    """analysis class-exists 输出结构核对（布尔字段 + class_name）。"""
    if not os.path.exists(_TEST_APK):
        pytest.skip("测试 APK 不存在")
    # 用一个确定存在的类
    real = _cli_json("analysis", "class-exists",
                     "Lcom/example/testactivity/MainActivity;",
                     "--apk-path", _TEST_APK, timeout=120)
    if real is None:
        # 类名可能不同，换个已知存在的
        real = _cli_json("analysis", "class-exists",
                         "Ltest/MainActivity;",
                         "--apk-path", _TEST_APK, timeout=120)
    assert real is not None, "analysis class-exists 输出异常"
    # class-exists 至少应有 exists 字段
    assert "exists" in real or "present" in real or "result" in real, (
        f"analysis class-exists 输出缺少 exists/present/result 字段: "
        f"{list(real.keys())}"
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
