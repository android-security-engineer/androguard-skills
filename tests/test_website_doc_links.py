#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills 文档站相对链接有效性回归测试

渲染命令文档（docs/commands/**/*.md）里引用了若干相对链接（如
`../../guide/python-api`、`./` 组索引、`../` 命令索引）。若链接目标不存在，
文档站导航断裂——agent 点"对应 API"或"相关"链接 404
（/goal："对接几十个 agent"，断链让 agent 迷路）。

本测试扫所有 docs/commands/ 下 .md 的 markdown 相对链接，校验目标文件存在。
仅校验相对链接（以 ./ 或 ../ 开头，或纯路径），不校验 http 外链。

VitePress 约定：链接 `./` 指向目录的 index.md，`../` 指向父目录 index.md，
`../../guide/foo` 指向 docs/guide/foo.md（.md 可省略）。

运行：``pytest tests/test_website_doc_links.py -v``
独立：``python3 tests/test_website_doc_links.py``
"""
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
DOCS_COMMANDS_DIR = os.path.join(REPO_ROOT, "website", "docs", "commands")
DOCS_DIR = os.path.join(REPO_ROOT, "website", "docs")

# markdown 链接：[text](url)  url 不以 http 开头
_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
_HTTP_RE = re.compile(r"^https?://")


def _resolve_link(link: str, src_file: str) -> str:
    """把相对链接解析为绝对文件路径（尝试 .md 后缀和 index.md）。

    VitePress：`./` → 目录/index.md，`../foo` → 父/foo.md，
    `../../guide/python-api` → docs/guide/python-api.md。
    """
    # 去掉锚点（#section）
    link = link.split("#")[0]
    if not link or _HTTP_RE.match(link):
        return ""  # 外链或纯锚点，跳过
    src_dir = os.path.dirname(src_file)
    # 相对解析
    target = os.path.normpath(os.path.join(src_dir, link))
    # 尝试多种形式
    candidates = []
    if link.endswith("/"):
        # 目录链接 → index.md
        candidates.append(os.path.join(target, "index.md"))
    else:
        candidates.append(target)  # 可能直接是 .md 文件
        candidates.append(target + ".md")  # 省略 .md
        candidates.append(os.path.join(target, "index.md"))  # 目录
    for c in candidates:
        if os.path.exists(c):
            return c
    return ""


def test_doc_relative_links_resolve():
    """docs/commands/ 下所有 .md 的相对链接目标必须存在。"""
    if not os.path.exists(DOCS_COMMANDS_DIR):
        pytest.skip("docs/commands/ 不存在")

    broken = _scan_broken_links(DOCS_COMMANDS_DIR)
    assert not broken, (
        f"发现 {len(broken)} 处 commands 文档相对链接断裂（目标 404）：\n"
        + "\n".join(f"  - {b}" for b in broken[:30])
    )


def test_all_docs_relative_links_resolve():
    """整个 docs/ 目录下所有 .md 的相对链接目标必须存在。

    覆盖 guide/modules/audit 等非命令文档的内部链接。
    """
    if not os.path.exists(DOCS_DIR):
        pytest.skip("docs/ 不存在")

    broken = _scan_broken_links(DOCS_DIR)
    assert not broken, (
        f"发现 {len(broken)} 处文档相对链接断裂（目标 404）：\n"
        + "\n".join(f"  - {b}" for b in broken[:40])
    )


def _scan_broken_links(scan_dir):
    """扫描目录下所有 .md 的断裂相对链接，返回 [描述, ...]。"""
    broken = []
    for root, _, files in os.walk(scan_dir):
        # 跳过 .vitepress 配置目录（非文档）
        if ".vitepress" in root:
            continue
        for fname in files:
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(root, fname)
            with open(fpath, "r", encoding="utf-8") as fh:
                content = fh.read()
            for m in _LINK_RE.finditer(content):
                link = m.group(1).strip()
                if not link or _HTTP_RE.match(link) or link.startswith("#"):
                    continue
                if not _resolve_link(link, fpath):
                    rel = os.path.relpath(fpath, REPO_ROOT)
                    broken.append(f"{rel}: 链接 `{link}` 目标不存在")
    return broken


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
