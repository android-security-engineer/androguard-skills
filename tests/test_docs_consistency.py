#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills 文档一致性回归测试

扫所有 SKILLS/*.md 文档里出现的 `androguard-skills <group> <subcmd>` 命令示例，
逐一核对该命令在 CLI `--help` 里真实存在。捕获：
  - 文档写了不存在的命令（笔误或命令改名后文档没跟）
  - 命令组归属错误（如把 analysis 命令写成 apk）

不影响运行时，但文档漂移会让照文档用命令的 agent（/goal："对接几十个
agent"）踩坑。本测试防漂移。

运行：``pytest tests/test_docs_consistency.py -v``
独立：``python3 tests/test_docs_consistency.py``
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
SKILLS_DIR = os.path.join(REPO_ROOT, "SKILLS")

# 命令组（顶层 group），从 entry_point 的 @xxx.command 装饰器统计得来。
# 这些是 `androguard-skills <group> --help` 能列出的子命令组。
GROUPS = {"apk", "dex", "analysis", "resources", "decompile", "util",
          "session", "visualize", "pentest"}


def _get_group_subcommands(group):
    """运行 `androguard-skills <group> --help`，解析子命令名列表。"""
    try:
        proc = subprocess.run(
            ["androguard-skills", group, "--help"],
            capture_output=True, text=True, timeout=30, cwd=REPO_ROOT,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None  # CLI 不可用
    # Click 的 --help 输出：子命令行格式为 "  name   Description"
    subs = set()
    for line in proc.stdout.splitlines():
        m = re.match(r"^  ([a-z][a-z0-9-]*)\s+", line)
        if m:
            subs.add(m.group(1))
    return subs


def _scan_doc_commands():
    """扫描 SKILLS/*.md，提取所有 `androguard-skills <group> <subcmd>` 示例。

    返回 [(doc_file, line_no, group, subcmd), ...]。
    """
    found = []
    pattern = re.compile(r"androguard-skills\s+(apk|dex|analysis|resources|"
                         r"decompile|util|session|visualize|pentest)\s+"
                         r"([a-z][a-z0-9-]*)")
    for fname in sorted(os.listdir(SKILLS_DIR)):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(SKILLS_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as fh:
            for i, line in enumerate(fh, 1):
                for m in pattern.finditer(line):
                    found.append((fname, i, m.group(1), m.group(2)))
    return found


def test_all_documented_commands_exist():
    """文档里每个命令示例都必须在 CLI --help 里真实存在。"""
    doc_cmds = _scan_doc_commands()
    assert doc_cmds, "未扫到任何命令示例——扫描正则可能失效"

    # 收集每个组的实际子命令
    actual = {}
    for g in GROUPS:
        subs = _get_group_subcommands(g)
        if subs is None:
            continue  # CLI 不可用时跳过（不 fail）
        actual[g] = subs

    if not actual:
        import pytest
        pytest.skip("androguard-skills CLI 不可用，无法核对")

    ghosts = []
    for fname, line, group, subcmd in doc_cmds:
        if group not in actual:
            continue  # 该组 help 拿不到，跳过
        if subcmd not in actual[group]:
            ghosts.append(f"{fname}:{line}  `androguard-skills {group} {subcmd}` "
                          f"不在 `{group} --help` 输出中")
    assert not ghosts, (
        f"发现 {len(ghosts)} 个文档里的命令在 CLI 中不存在（笔误/改名后文档没跟）：\n"
        + "\n".join(f"  - {g}" for g in ghosts[:30])
    )


def test_readme_index_covers_all_commands():
    """README 索引覆盖检查（宽松）。

    README 是入口索引，不必列全 218 命令（子 .md 有详细文档）。但若遗漏率
    过高（>50%），说明新增命令长期没回填索引，对 agent 不友好。阈值 50%。

    关键不变量由 test_all_documented_commands_exist 守：所有文档里写出的
    命令示例必须真实存在。本测试只防"索引长期不维护"的退化。
    """
    readme = os.path.join(SKILLS_DIR, "README.md")
    with open(readme, "r", encoding="utf-8") as fh:
        content = fh.read()
    indexed = set()
    for m in re.finditer(r"^\|\s*`(apk|dex|analysis|resources|decompile|util|"
                         r"session|visualize|pentest)\s+([a-z][a-z0-9-]*)`",
                         content, re.M):
        indexed.add((m.group(1), m.group(2)))

    actual_all = set()
    for g in GROUPS:
        subs = _get_group_subcommands(g)
        if subs:
            for s in subs:
                actual_all.add((g, s))

    if not actual_all:
        import pytest
        pytest.skip("CLI 不可用")

    missing = actual_all - indexed
    ratio = len(missing) / len(actual_all) if actual_all else 0
    if missing:
        print(f"\n[信息] README 索引遗漏 {len(missing)}/{len(actual_all)} 个命令 "
              f"({ratio:.0%})——这些命令应在子 .md 有详细文档，见 "
              f"test_all_documented_commands_exist 确保无笔误。前 20 个遗漏:")
        for g, s in sorted(missing)[:20]:
            print(f"  - {g} {s}")
    # 阈值 50%：超过则认为索引长期失修
    assert ratio < 0.50, f"README 索引遗漏 {ratio:.0%} 命令，索引长期失修"


def test_no_undocumented_commands():
    """每个命令至少在某份 .md 文档里被提及（防新增命令忘写文档）。

    判据：命令 `group subcmd` 或 `` `group subcmd` `` 在合并的全部 SKILLS/*.md
    中至少出现一次。这是文档覆盖的下限——agent 照文档用命令不会遇到"完全
    没文档"的命令。
    """
    # 合并所有 .md 内容
    all_docs = ""
    for fname in os.listdir(SKILLS_DIR):
        if fname.endswith(".md"):
            with open(os.path.join(SKILLS_DIR, fname), "r", encoding="utf-8") as fh:
                all_docs += fh.read()

    actual_all = set()
    for g in GROUPS:
        subs = _get_group_subcommands(g)
        if subs:
            for s in subs:
                actual_all.add((g, s))

    if not actual_all:
        import pytest
        pytest.skip("CLI 不可用")

    undocumented = []
    for g, s in sorted(actual_all):
        if f"{g} {s}" not in all_docs and f"`{g} {s}`" not in all_docs:
            undocumented.append(f"{g} {s}")
    assert not undocumented, (
        f"发现 {len(undocumented)} 个命令完全无文档提及（应至少在某 .md 出现）：\n"
        + "\n".join(f"  - {c}" for c in undocumented)
    )


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
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
