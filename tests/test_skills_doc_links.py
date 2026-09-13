#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills SKILLS 文档交叉引用有效性回归测试

test_website_doc_links.py 守 website/docs/ 的相对链接，但顶层 SKILLS/*.md
（agent 直接读的渐进式披露文档）的交叉引用无守卫——若删了某 .md 但其他
文档仍引用它（如「详见 [apk-signature](apk-signature.md)」），agent 跟随
链接 404（/goal："对接几十个 agent"，断链让 agent 迷路）。

本测试扫 SKILLS/*.md 的 markdown 相对链接，校验目标 .md 存在。仅校验相对
链接（非 http 外链）。SKILLS 链接通常是同目录 .md，省略 .md 也补全。

运行：``pytest tests/test_skills_doc_links.py -v``
独立：``python3 tests/test_skills_doc_links.py``
"""
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
SKILLS_DIR = os.path.join(REPO_ROOT, "SKILLS")

_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
_HTTP_RE = re.compile(r"^https?://")


def _resolve_link(link: str, src_file: str) -> bool:
    """相对链接解析为是否存在目标文件。"""
    link = link.split("#")[0]
    if not link or _HTTP_RE.match(link):
        return True  # 外链或纯锚点，跳过
    src_dir = os.path.dirname(src_file)
    target = os.path.normpath(os.path.join(src_dir, link))
    candidates = [target, target + ".md",
                  os.path.join(target, "index.md")]
    return any(os.path.exists(c) for c in candidates)


def test_skills_doc_relative_links_resolve():
    """SKILLS/*.md 的所有相对链接目标必须存在。"""
    if not os.path.exists(SKILLS_DIR):
        pytest.skip("SKILLS/ 不存在")

    broken = []
    for fname in sorted(os.listdir(SKILLS_DIR)):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(SKILLS_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as fh:
            content = fh.read()
        for m in _LINK_RE.finditer(content):
            link = m.group(1).strip()
            if not link or _HTTP_RE.match(link) or link.startswith("#"):
                continue
            if not _resolve_link(link, fpath):
                broken.append(f"{fname}: 链接 `{link}` 目标不存在")
    assert not broken, (
        f"SKILLS 文档发现 {len(broken)} 处相对链接断裂（目标 404）：\n"
        + "\n".join(f"  - {b}" for b in broken[:30])
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
