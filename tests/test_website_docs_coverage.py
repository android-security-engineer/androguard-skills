#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills 文档站 docs/commands/ 渲染覆盖回归测试

gen_command_docs.py 读 commands.json 生成 docs/commands/<group>/<cmd>.md。
若 commands.json 新增了命令但没重新渲染，docs/commands/ 会缺该命令的文档
页——文档站侧边栏点不到，agent 查不到该命令文档（/goal："对接几十个 agent"）。

本测试校验覆盖性：commands.json 里每个命令在 docs/commands/<group>/
都有对应 .md 文件（非内容校验，因渲染输出可能随模板变）。

运行：``pytest tests/test_website_docs_coverage.py -v``
独立：``python3 tests/test_website_docs_coverage.py``
"""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
COMMANDS_JSON = os.path.join(REPO_ROOT, "website", "scripts", "commands.json")
DOCS_COMMANDS_DIR = os.path.join(REPO_ROOT, "website", "docs", "commands")


def test_every_command_has_doc_page():
    """commands.json 里每个命令在 docs/commands/<group>/ 都有 .md。"""
    if not os.path.exists(COMMANDS_JSON):
        pytest.skip("commands.json 不存在")
    if not os.path.exists(DOCS_COMMANDS_DIR):
        pytest.skip("docs/commands/ 不存在")

    with open(COMMANDS_JSON, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    missing = []
    for group, section in data.items():
        if not isinstance(section, dict):
            continue
        # __top__ 组的命令文档在 docs/commands/ 顶层（非子目录）
        if group == "__top__":
            group_dir = DOCS_COMMANDS_DIR
        else:
            group_dir = os.path.join(DOCS_COMMANDS_DIR, group)
        for cmd in section.get("commands", []):
            name = cmd.get("name")
            if not name:
                continue
            doc_file = os.path.join(group_dir, f"{name}.md")
            if not os.path.exists(doc_file):
                missing.append(f"{group}/{name}.md")

    assert not missing, (
        f"commands.json 里 {len(missing)} 个命令在 docs/commands/ 无对应"
        f" .md（需重新运行 gen_command_docs.py 渲染）：\n"
        + "\n".join(f"  - {m}" for m in missing[:30])
    )


def test_no_orphan_doc_pages():
    """docs/commands/<group>/ 里每个命令 .md 都在 commands.json 里（无孤儿）。

    捕获：命令从 commands.json 删除但 docs 里残留旧 .md（文档站显示已废弃命令）。
    index.md 不算命令文档，跳过。
    """
    if not os.path.exists(COMMANDS_JSON):
        pytest.skip("commands.json 不存在")
    if not os.path.exists(DOCS_COMMANDS_DIR):
        pytest.skip("docs/commands/ 不存在")

    with open(COMMANDS_JSON, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    # 收集 commands.json 里所有 (group, cmd) 对
    json_pairs = set()
    for group, section in data.items():
        if not isinstance(section, dict):
            continue
        for cmd in section.get("commands", []):
            name = cmd.get("name")
            if name:
                json_pairs.add((group, name))

    orphans = []
    # 顶层 .md 文件（docs/commands/*.md，非子目录）归 __top__ 组
    for fname in os.listdir(DOCS_COMMANDS_DIR):
        full = os.path.join(DOCS_COMMANDS_DIR, fname)
        if not os.path.isfile(full):
            continue
        if not fname.endswith(".md"):
            continue
        if fname == "index.md":
            continue
        cmd_name = fname[:-3]
        if ("__top__", cmd_name) not in json_pairs:
            orphans.append(f"(top)/{fname}")
    # 各组子目录
    for group_dir in os.listdir(DOCS_COMMANDS_DIR):
        full = os.path.join(DOCS_COMMANDS_DIR, group_dir)
        if not os.path.isdir(full):
            continue
        for fname in os.listdir(full):
            if not fname.endswith(".md"):
                continue
            if fname == "index.md":
                continue
            cmd_name = fname[:-3]  # 去 .md
            if (group_dir, cmd_name) not in json_pairs:
                orphans.append(f"{group_dir}/{fname}")

    assert not orphans, (
        f"docs/commands/ 里 {len(orphans)} 个 .md 不在 commands.json 里"
        f"（孤儿文档，命令已删除但文档残留）：\n"
        + "\n".join(f"  - {o}" for o in orphans[:30])
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
