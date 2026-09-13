#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills 全量命令冒烟回归测试（参数化）

test_cli_smoke.py 只抽样 20 个命令；本测试对**全部 213 个顶层组命令**逐个
冒烟，断言每个命令满足以下之一：
  - exit 0 + 输出合法 JSON（正常路径）
  - exit 0 + 输出 {"error": ...}（结构化错误，如该命令需已加载 APK 但本测试
    未先 load——可接受，关键是结构化）
  - exit ≠0 + Click 友好错误（缺必需参数等，非 traceback）

**禁止**：Python traceback（"Traceback (most recent"）——这是 test_cli_error_paths
的契约延伸到全部命令。捕获任何命令在默认参数下崩溃。

因 213 命令各带不同参数，本测试用 `--apk-path` 做最大公约数尝试；需要额外
位置参数的命令会走 Click 错误分支（可接受）。

运行：``pytest tests/test_cli_all_commands_smoke.py -v``
（参数化会生成 213 个测试项，~3 分钟）
"""
import json
import os
import re
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
APK = os.path.join(HERE, "data", "APK", "TestActivity.apk")

GROUPS = ["apk", "dex", "analysis", "resources", "decompile", "util",
          "session", "visualize", "pentest"]

# 需要先 load APK 的命令在 daemon 模式下会报 "No APK loaded"——但本测试走单次
# 模式（确保 daemon 不在），用 --apk-path 触发单次 fallback load。


def _get_all_commands():
    """返回 [(group, subcmd), ...] 全部命令。CLI 不可用时返回空。"""
    cmds = []
    for g in GROUPS:
        try:
            proc = subprocess.run(
                ["androguard-skills", g, "--help"],
                capture_output=True, text=True, timeout=30, cwd=REPO_ROOT,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return []
        for line in proc.stdout.splitlines():
            m = re.match(r"^  ([a-z][a-z0-9-]*)\s+", line)
            if m:
                cmds.append((g, m.group(1)))
    return cmds


ALL_COMMANDS = _get_all_commands()

# 确保 daemon 不在（单次模式，--apk-path 才生效）
subprocess.run(["androguard-skills", "daemon", "stop"],
               capture_output=True, timeout=10, cwd=REPO_ROOT)


def _run_cmd(group, subcmd):
    """运行 `androguard-skills group subcmd --apk-path APK`，返回 (code, out, err)。"""
    cmd = ["androguard-skills", group, subcmd, "--apk-path", APK]
    # 某些命令的 --apk-path 可能叫别的或不存在，捕获 Click 错误即可
    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=90, cwd=REPO_ROOT,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _is_json(s):
    """尝试解析 JSON（容忍日志前缀行）。

    输出可能是单行或多行 pretty-printed JSON。策略：找到第一个以 { 或 [
    开头的行作为起点，从该行到末尾整体解析。
    """
    lines = s.strip().splitlines()
    start = None
    for i, ln in enumerate(lines):
        ls = ln.lstrip()
        if ls.startswith("{") or ls.startswith("["):
            start = i
            break  # 第一个 JSON 起点即可，不要遍历到嵌套行
    if start is None:
        return False, None
    try:
        return True, json.loads("\n".join(lines[start:]))
    except json.JSONDecodeError:
        return False, None


@pytest.mark.skipif(not ALL_COMMANDS, reason="androguard-skills CLI 不可用")
@pytest.mark.skipif(not os.path.exists(APK), reason=f"基准 APK 不存在: {APK}")
@pytest.mark.parametrize("group,subcmd", ALL_COMMANDS, ids=lambda x: f"{x[0]}-{x[1]}")
def test_command_does_not_crash(group, subcmd):
    """每个命令在默认 + --apk-path 下不得崩溃（无 traceback）。"""
    code, out, err = _run_cmd(group, subcmd)
    combined = out + err

    # 硬断言：绝无 Python traceback
    assert "Traceback (most recent" not in combined, (
        f"`{group} {subcmd}` 产生 Python traceback（应结构化错误）:\n{combined[-600:]}"
    )

    # 可接受的三种正常结果：
    # 1. exit 0 + JSON（含或不含 error 键）
    # 2. exit ≠0 + Click 友好错误（Usage/Error:）
    is_json, data = _is_json(out)
    if code == 0:
        assert is_json, (
            f"`{group} {subcmd}` exit 0 但输出非 JSON:\n{out[-400:]}"
        )
    else:
        # exit≠0：应是 Click 参数错误，含 Usage 或 Error 或 Missing
        click_err_keys = ["usage:", "error:", "missing", "invalid"]
        has_click_err = any(k in combined.lower() for k in click_err_keys)
        assert has_click_err, (
            f"`{group} {subcmd}` exit {code} 但无 Click 友好错误:\n{combined[-400:]}"
        )


if __name__ == "__main__":
    # 独立运行：逐个跑
    if not ALL_COMMANDS:
        print("CLI 不可用"); sys.exit(1)
    passed = failed = 0
    for g, s in ALL_COMMANDS:
        try:
            test_command_does_not_crash(g, s)
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {g} {s}: {str(e)[:120]}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {g} {s}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed, {len(ALL_COMMANDS)} total")
    sys.exit(1 if failed else 0)
