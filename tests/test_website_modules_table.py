#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills 文档站 modules 表格 CLI 映射列有效性回归测试

website/docs/modules/*-skills.md 每个模块文档有一张「方法名 | 签名 | 说明 |
对应 CLI 命令」四列表，第四列声称该 Python API 方法对应的 CLI 命令。
若该列写错命令名/组（如把 `apk attack-surface` 写成 `analysis attack-surface`，
或把不存在的 `util detect-file` 当真实命令），agent 照表用会失败
（/goal："对接几十个 agent"，映射表是 agent 选命令的权威依据）。

本测试校验：每个 *-skills.md 表格第四列的 `` `G S` `` 必须是真实存在的
CLI 命令，或明确标注「无 CLI」。覆盖 8 个模块文档（apk/analysis/dex/
resources/decompile/util/session/visualize/pentest skills）。

运行：``pytest tests/test_website_modules_table.py -v``
独立：``python3 tests/test_website_modules_table.py``
"""
import os
import re
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
MODULES_DIR = os.path.join(REPO_ROOT, "website", "docs", "modules")

GROUPS = ["apk", "dex", "analysis", "resources", "decompile", "util",
          "session", "visualize", "pentest"]

# 表格行：| `method_name` | `(sig)` | 说明 | `G S` 或「无 CLI」 |
# 第四列在反引号内是 `G S`，或显式「无 CLI」文本
_ROW_RE = re.compile(
    r"^\|\s*`[a-z_][a-z0-9_]*`\s*\|"   # 第一列：方法名（反引号）
    r"[^|]*\|"                          # 第二列：签名
    r"[^|]*\|"                          # 第三列：说明
    r"\s*(.*?)\s*\|\s*$"                # 第四列：CLI 命令（捕获）
)
# 第四列里的 `G S` 形式（反引号包裹的「组 子命令」）
_CMD_IN_CELL_RE = re.compile(
    r"`(" + "|".join(GROUPS) + r")\s+([a-z][a-z0-9-]*)`"
)
# 「无 CLI」标记（中文/英文皆可）
_NO_CLI_RE = re.compile(r"无\s*CLI|no\s+CLI|—", re.IGNORECASE)


def _get_all_subcommands() -> dict:
    """返回 {group: set(subcmd)}。"""
    result = {}
    for g in GROUPS:
        try:
            proc = subprocess.run(
                ["androguard-skills", g, "--help"],
                capture_output=True, text=True, timeout=30, cwd=REPO_ROOT,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return {}
        subs = set()
        for line in proc.stdout.splitlines():
            m = re.match(r"^  ([a-z][a-z0-9-]*)\s+", line)
            if m:
                subs.add(m.group(1))
        result[g] = subs
    return result


def _module_files():
    """返回 8 个 *-skills.md 文件路径（排除 main/daemon/index）。"""
    if not os.path.exists(MODULES_DIR):
        return []
    result = []
    for fname in sorted(os.listdir(MODULES_DIR)):
        if fname.endswith("-skills.md"):
            result.append(os.path.join(MODULES_DIR, fname))
    return result


def test_modules_table_cli_mapping_valid():
    """modules 表格第四列的 `G S` 必须是真实 CLI 命令或标注「无 CLI」。"""
    if not os.path.exists(MODULES_DIR):
        pytest.skip("website/docs/modules/ 不存在")
    actual = _get_all_subcommands()
    if not actual:
        pytest.skip("androguard-skills CLI 不可用")

    bad = []
    for fpath in _module_files():
        rel = os.path.relpath(fpath, REPO_ROOT)
        with open(fpath, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
        # 跳过表头（前两行：| 方法名 ... | + |---|---|...）
        for lineno, line in enumerate(lines, 1):
            m = _ROW_RE.match(line)
            if not m:
                continue
            cell = m.group(1)
            # 第四列可能含多个 `G S`（罕见）或「无 CLI」文本
            cmds = _CMD_IN_CELL_RE.findall(cell)
            if cmds:
                # 有显式命令：每个都必须真实存在
                for group, subcmd in cmds:
                    if group in actual and subcmd not in actual[group]:
                        bad.append(
                            f"{rel}:{lineno}: 表格声称 `{group} {subcmd}` "
                            f"是 CLI 命令，但 `{group}` 组无此子命令"
                        )
            else:
                # 无 `G S`：必须显式标注「无 CLI」或破折号
                if not _NO_CLI_RE.search(cell):
                    # 可能是空单元格或其他，记录供人工核对
                    cell_clean = cell.strip().strip("|").strip()
                    if cell_clean and not _NO_CLI_RE.search(cell_clean):
                        bad.append(
                            f"{rel}:{lineno}: 表格第四列 `{cell_clean}` "
                            f"既非 `G S` 命令也非「无 CLI」标注"
                        )

    assert not bad, (
        f"modules 表格 CLI 映射列发现 {len(bad)} 处问题：\n"
        + "\n".join(f"  - {b}" for b in bad[:40])
    )


# 各 *-skills.md 文件 → 对应的 skills Python 模块（校验方法名列用）
_FILE_TO_MOD = {
    "apk-skills.md": "androguard.skills.apk_skills",
    "analysis-skills.md": "androguard.skills.analysis_skills",
    "dex-skills.md": "androguard.skills.dex_skills",
    "resource-skills.md": "androguard.skills.resource_skills",
    "decompiler-skills.md": "androguard.skills.decompiler_skills",
    "util-skills.md": "androguard.skills.util_skills",
    "session-skills.md": "androguard.skills.session_skills",
    "visualize-skills.md": "androguard.skills.visualize_skills",
    "pentest-skills.md": "androguard.skills.pentest_skills",
}
_METHOD_RE = re.compile(r"^\|\s*`([a-z_][a-z0-9_]*)`\s*\|", re.MULTILINE)


def test_modules_table_method_names_exist():
    """modules 表格第一列方法名必须在对应 skills 模块真实存在。

    若方法名写错（如漏后缀、拼错），agent 照表调
    ``skills.<method>(...)`` 会 AttributeError。
    """
    if not os.path.exists(MODULES_DIR):
        pytest.skip("website/docs/modules/ 不存在")

    import importlib
    bad = []
    for fname, modname in _FILE_TO_MOD.items():
        fpath = os.path.join(MODULES_DIR, fname)
        if not os.path.exists(fpath):
            continue
        try:
            mod = importlib.import_module(modname)
        except ImportError as e:
            pytest.fail(f"无法导入 {modname}（{fname} 校验前提）：{e}")
        with open(fpath, "r", encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                m = _METHOD_RE.match(line)
                if not m:
                    continue
                method = m.group(1)
                if not hasattr(mod, method):
                    bad.append(
                        f"{fname}:{lineno}: 表格方法名 `{method}` "
                        f"在 {modname} 不存在"
                    )
    assert not bad, (
        f"modules 表格方法名发现 {len(bad)} 处不存在于底层模块：\n"
        + "\n".join(f"  - {b}" for b in bad[:40])
    )


_COUNT_RE = re.compile(r"(\d+)\s*个公开(?:函数|方法)")


def test_modules_table_count_matches_reality():
    """modules 文档开头「共 N 个公开函数」声明必须与底层真实公开数 + 表格行数一致。

    若增删了 skills 方法但忘了改文档数字，agent 对能力规模认知会偏。
    dex/visualize/pentest 等句式多样（「共 N 个」「等 N 个」），正则宽松匹配。
    """
    if not os.path.exists(MODULES_DIR):
        pytest.skip("website/docs/modules/ 不存在")

    import importlib
    bad = []
    for fname, modname in _FILE_TO_MOD.items():
        fpath = os.path.join(MODULES_DIR, fname)
        if not os.path.exists(fpath):
            continue
        mod = importlib.import_module(modname)
        # 真实公开函数：不以 _ 开头、callable、定义在本模块
        real_public = [
            n for n in dir(mod)
            if not n.startswith("_")
            and callable(getattr(mod, n))
            and getattr(getattr(mod, n), "__module__", None) == modname
        ]
        with open(fpath, "r", encoding="utf-8") as fh:
            content = fh.read()
        # 文档声明的数字（取第一个匹配）
        m = _COUNT_RE.search(content)
        if not m:
            bad.append(
                f"{fname}: 未声明公开函数数（缺「N 个公开函数/方法」）"
            )
            continue
        doc_count = int(m.group(1))
        # 表格实际方法行数
        table_rows = len(_METHOD_RE.findall(content))
        if doc_count != len(real_public):
            bad.append(
                f"{fname}: 文档声称 {doc_count} 个，实际 {len(real_public)} 个"
            )
        if table_rows != len(real_public):
            bad.append(
                f"{fname}: 表格 {table_rows} 行，实际 {len(real_public)} 个"
            )
    assert not bad, (
        f"modules 文档公开函数数声明发现 {len(bad)} 处不符：\n"
        + "\n".join(f"  - {b}" for b in bad[:40])
    )


def test_every_cli_command_mapped_in_modules_table():
    """每个真实 CLI 命令必须在某 modules 表格里被映射（CLI→Python 反向覆盖）。

    若新增 CLI 命令但忘在 modules 表格加行，agent 查 modules 文档找不到
    该命令对应的 Python 方法（/goal："对接几十个 agent"，modules 表格是
    agent 从 CLI 命令反查底层 API 的权威映射）。
    """
    if not os.path.exists(MODULES_DIR):
        pytest.skip("website/docs/modules/ 不存在")
    actual = _get_all_subcommands()
    if not actual:
        pytest.skip("androguard-skills CLI 不可用")

    # 收集 modules 表格里所有 `G S` 映射
    table_cmds = set()
    for fname in os.listdir(MODULES_DIR):
        if not fname.endswith("-skills.md"):
            continue
        with open(os.path.join(MODULES_DIR, fname), "r", encoding="utf-8") as fh:
            for m in _CMD_IN_CELL_RE.finditer(fh.read()):
                table_cmds.add((m.group(1), m.group(2)))

    # 收集真实 CLI 命令
    real_cmds = set()
    for g, subs in actual.items():
        for s in subs:
            real_cmds.add((g, s))

    missing = real_cmds - table_cmds
    assert not missing, (
        f"{len(missing)} 个 CLI 命令在 modules 表格无映射（需补表格行）：\n"
        + "\n".join(f"  - `{g} {s}`" for g, s in sorted(missing)[:40])
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
