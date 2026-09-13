#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills SKILLS README 索引分组准确性回归测试

test_docs_consistency.py::test_readme_index_covers_all_commands 只校验索引
覆盖率（<50% 遗漏才 fail），不校验**分组正确性**——README 索引表把命令按
组（apk/dex/analysis/...）分类列，若把 dex 命令列到 analysis 行，agent 按
索引找会找不到（/goal："对接几十个 agent"，索引分组错位让 agent 迷路）。

本测试扫 README 索引表每行 `| G S | ... |`，核对 (group, subcmd) 真实属于
该 group（subcmd 真在该 group 的子命令集合里）。捕获：
  - 命令列错组（如 `dex classes` 写成 `analysis classes`）
  - 子命令笔误（如 `apk permisions` 漏字母）

运行：``pytest tests/test_readme_index_grouping.py -v``
独立：``python3 tests/test_readme_index_grouping.py``
"""
import os
import re
import subprocess
import sys

import click
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
SKILLS_DIR = os.path.join(REPO_ROOT, "SKILLS")
sys.path.insert(0, REPO_ROOT)

from androguard.skills.main import entry_point  # noqa: E402


GROUPS = ["apk", "dex", "analysis", "resources", "decompile", "util",
          "session", "visualize", "pentest"]


def _group_subcommands(group) -> set:
    """该 group 的真实子命令名集合（Click 内省）。"""
    gc = entry_point.commands.get(group)
    if not isinstance(gc, click.Group):
        return set()
    return set(gc.commands.keys())


def _scan_index_entries():
    """扫 README 索引表，返回 [(line_no, group, subcmd), ...]。

    索引表行格式：| `G S` | 说明 | [doc.md](doc.md) |
    或带位置参数：| `G S <arg>` | 说明 | ... |
    """
    readme = os.path.join(SKILLS_DIR, "README.md")
    entries = []
    # 匹配 | `group subcmd` 或 | `group subcmd <...>
    pattern = re.compile(
        r"^\|\s*`(" + "|".join(GROUPS) + r")\s+([a-z][a-z0-9-]*)"
    )
    with open(readme, "r", encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            m = pattern.match(line)
            if m:
                entries.append((i, m.group(1), m.group(2)))
    return entries


def test_index_entries_in_correct_group():
    """索引表每行的 (group, subcmd) 必须真实属于该 group。"""
    entries = _scan_index_entries()
    assert entries, "未扫到索引表条目——扫描正则可能失效"

    # 每组的真实子命令
    real = {g: _group_subcommands(g) for g in GROUPS}

    misgrouped = []
    for line, group, subcmd in entries:
        if group not in real or not real[group]:
            continue
        if subcmd not in real[group]:
            misgrouped.append(
                f"README.md:{line} `androguard-skills {group} {subcmd}` "
                f"不在 `{group}` 组的子命令里"
            )
    assert not misgrouped, (
        f"发现 {len(misgrouped)} 处索引分组错误（命令列错组或笔误）：\n"
        + "\n".join(f"  - {m}" for m in misgrouped[:30])
    )


def test_index_entries_reference_existing_doc():
    """索引表每行引用的 .md 文档必须真实存在。

    捕获：索引指向不存在的文档（链接 404，agent 点不进去）。
    """
    readme = os.path.join(SKILLS_DIR, "README.md")
    pattern = re.compile(r"^\|\s*`[a-z]+\s+[a-z][a-z0-9-]*.*?\|\s*\[([^\]]+)\]\(([^)]+)\)")
    missing = []
    with open(readme, "r", encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            m = pattern.search(line)
            if not m:
                continue
            doc_link = m.group(2)
            # 只校验相对路径的 .md 链接
            if not doc_link.endswith(".md"):
                continue
            doc_path = os.path.join(SKILLS_DIR, doc_link)
            if not os.path.exists(doc_path):
                missing.append(f"README.md:{i} 引用 `{doc_link}` 不存在")
    assert not missing, (
        f"发现 {len(missing)} 处索引链接指向不存在的文档：\n"
        + "\n".join(f"  - {m}" for m in missing[:30])
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
