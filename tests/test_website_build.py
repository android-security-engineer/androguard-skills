#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills 文档站 VitePress 构建回归测试

website/docs/ 下的所有内容测试（commands.json 同步、渲染覆盖、链接有效、
modules 表格）都是静态校验，但没测 VitePress 能否成功 build。若文档引入
了 VitePress 不识别的语法（如错误的 frontmatter、非法的 include），静态
测试通过但 build 失败——文档站部署会断（/goal："对接几十个 agent"，文档站
是 agent 查命令的入口，build 失败=文档站不可用）。

本测试跑 `vitepress build docs`，验证 exit 0 + 生成 .vitepress/dist。
无 node 环境时 skip（不阻塞 Python 测试套件）。

运行：``pytest tests/test_website_build.py -v``
独立：``python3 tests/test_website_build.py``
"""

import os
import shutil
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
WEBSITE_DIR = os.path.join(REPO_ROOT, "website")
DIST_DIR = os.path.join(WEBSITE_DIR, "docs", ".vitepress", "dist")


def _has_node():
    """检查 node + vitepress 是否可用。

    只认本地真实安装的 vitepress（website/node_modules/.bin/vitepress）。
    不要用 ``shutil.which("npx")`` 兜底——CI 测试 job 未跑 ``npm install``，
    npx 虽存在但 vitepress 不在 node_modules，``npx vitepress`` 会联网解析失败
    报 "Cannot find package 'vitepress'"，而不是干净 skip。
    """
    if not shutil.which("node"):
        return False
    vp = os.path.join(WEBSITE_DIR, "node_modules", ".bin", "vitepress")
    return os.path.exists(vp)


def test_vitepress_build_succeeds():
    """VitePress build 必须成功（exit 0 + 生成 dist 目录）。"""
    if not _has_node():
        pytest.skip("node/vitepress 不可用，跳过 build 测试")
    if not os.path.exists(os.path.join(WEBSITE_DIR, "package.json")):
        pytest.skip("website/ 无 package.json")

    # 清理旧 dist（防误判）
    if os.path.exists(DIST_DIR):
        shutil.rmtree(DIST_DIR, ignore_errors=True)

    proc = subprocess.run(
        ["npx", "vitepress", "build", "docs"],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=WEBSITE_DIR,
    )
    assert proc.returncode == 0, (
        f"VitePress build 失败 (exit {proc.returncode}):\n"
        f"{proc.stderr[-1000:]}\n{proc.stdout[-500:]}"
    )
    # build 应生成 dist 目录
    assert os.path.exists(DIST_DIR), f"build 成功但未生成 dist: {DIST_DIR}"
    # dist 里应有 index.html（首页渲染产物）
    assert os.path.exists(
        os.path.join(DIST_DIR, "index.html")
    ), "dist 里无 index.html，首页未渲染"


if __name__ == "__main__":
    fns = [
        v
        for k, v in sorted(globals().items())
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
