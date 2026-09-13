#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills 文档站 CLI 命令示例有效性回归测试

test_docs_consistency.py 扫 SKILLS/*.md 的命令示例核对存在性，但文档站
website/docs/ 下的 guide 文档（daemon-mode.md/jsonrpc-protocol.md 等）也
引用了 `androguard-skills G S` 命令示例——这些示例若写错命令名/组，agent
照用会失败（/goal："对接几十个 agent"）。

本测试只校验**完整 CLI 调用形式**（`androguard-skills G S ...`），不校验
裸 `G S`（modules 文档讲 Python API，`analysis api-usage-grouped` 是方法名
的连字符描述，非 CLI 命令，无法区分）。

运行：``pytest tests/test_website_doc_commands.py -v``
独立：``python3 tests/test_website_doc_commands.py``
"""
import os
import re
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
DOCS_DIR = os.path.join(REPO_ROOT, "website", "docs")

GROUPS = ["apk", "dex", "analysis", "resources", "decompile", "util",
          "session", "visualize", "pentest"]

# 只匹配完整 CLI 调用：androguard-skills G S （G 是命令组，S 是子命令）
# 不匹配 daemon 子命令（start/stop/status，已由 daemon_cmds 测试守）
_CMD_RE = re.compile(
    r"androguard-skills\s+(" + "|".join(GROUPS) + r")\s+([a-z][a-z0-9-]*)"
)


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


def test_website_doc_command_examples_exist():
    """文档站所有完整 CLI 命令示例（androguard-skills G S）必须真实存在。"""
    if not os.path.exists(DOCS_DIR):
        pytest.skip("website/docs/ 不存在")

    actual = _get_all_subcommands()
    if not actual:
        pytest.skip("androguard-skills CLI 不可用")

    ghosts = []
    for root, _, files in os.walk(DOCS_DIR):
        if ".vitepress" in root:
            continue
        for fname in files:
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(root, fname)
            with open(fpath, "r", encoding="utf-8") as fh:
                content = fh.read()
            rel = os.path.relpath(fpath, REPO_ROOT)
            for m in _CMD_RE.finditer(content):
                group, subcmd = m.group(1), m.group(2)
                if group in actual and subcmd not in actual[group]:
                    ghosts.append(
                        f"{rel}: `androguard-skills {group} {subcmd}` "
                        f"不在 `{group}` 组"
                    )

    assert not ghosts, (
        f"发现 {len(ghosts)} 处文档站 CLI 命令示例不存在：\n"
        + "\n".join(f"  - {g}" for g in ghosts[:30])
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
