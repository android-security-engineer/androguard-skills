#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills 文档站 commands.json 与 CLI 同步回归测试

文档站（website/）的命令文档由 introspect_commands.py 从 click 命令树
内省生成 commands.json，再由 gen_command_docs.py 渲染为 docs/commands/。
若 CLI 命令变了（新增/改名/改参数）但没重新内省，文档站会过时——agent
照文档站用命令会踩坑（/goal："对接几十个 agent"）。

本测试重新运行 introspect_commands.py 生成 commands.json，与磁盘上的
commands.json 比对，不一致即文档站过时（需重新跑内省脚本）。

运行：``pytest tests/test_website_commands_json_sync.py -v``
独立：``python3 tests/test_website_commands_json_sync.py``
"""
import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "website", "scripts")
COMMANDS_JSON = os.path.join(SCRIPTS_DIR, "commands.json")
INTROSPECT_SCRIPT = os.path.join(SCRIPTS_DIR, "introspect_commands.py")


def test_commands_json_in_sync_with_cli():
    """磁盘 commands.json 必须与重新内省的输出一致。"""
    if not os.path.exists(INTROSPECT_SCRIPT):
        pytest.skip("文档站 introspect 脚本不存在")
    if not os.path.exists(COMMANDS_JSON):
        pytest.skip("commands.json 不存在")

    # 重新内省生成 JSON（脚本输出到 stdout）
    proc = subprocess.run(
        [sys.executable, INTROSPECT_SCRIPT],
        capture_output=True, text=True, timeout=60, cwd=SCRIPTS_DIR,
    )
    assert proc.returncode == 0, (
        f"introspect_commands.py 运行失败（exit {proc.returncode}）:\n"
        f"{proc.stderr[:500]}"
    )

    fresh = json.loads(proc.stdout)
    with open(COMMANDS_JSON, "r", encoding="utf-8") as fh:
        on_disk = json.load(fh)

    # 比对（排序后序列化，避免 key 顺序差异）
    fresh_norm = json.dumps(fresh, sort_keys=True, ensure_ascii=False)
    disk_norm = json.dumps(on_disk, sort_keys=True, ensure_ascii=False)

    assert fresh_norm == disk_norm, (
        "commands.json 与当前 CLI 不一致——CLI 命令已变更但文档站未重新"
        "内省。请在 website/scripts/ 下运行：\n"
        f"  python3 introspect_commands.py > commands.json\n"
        "然后重新生成命令文档。"
    )


def test_commands_json_has_all_groups():
    """commands.json 覆盖所有顶层命令组。"""
    if not os.path.exists(COMMANDS_JSON):
        pytest.skip("commands.json 不存在")
    with open(COMMANDS_JSON, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    # commands.json 顶层 keys 应是命令组（apk/dex/analysis/...）
    expected_groups = {"apk", "dex", "analysis", "resources", "decompile",
                       "util", "session", "visualize", "pentest"}
    actual_groups = set(data.keys()) if isinstance(data, dict) else set()
    missing = expected_groups - actual_groups
    assert not missing, (
        f"commands.json 缺少命令组: {sorted(missing)}"
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
