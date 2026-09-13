#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills CLI --help 输出质量回归测试

test_cli_all_commands_smoke.py 跑了所有命令的功能，但没校验 --help 输出
本身。agent 找参数名时跑 `cmd --help`，若 help 漏列参数 → 参数不可见
（/goal："对接几十个 agent"，help 漂移让 agent 用不上隐藏参数）。

本测试对每个叶子命令跑 `--help`，校验：
  1. exit 0
  2. help 文本里出现该命令所有真实 option 的 CLI 形式（--foo-bar）
  3. help 文本里出现该命令所有位置参数（Argument）的名称

Click 的 --help 自动从参数定义生成，理论上不会漏，但若有自定义 group
或参数被条件性隐藏，help 会漏。本测试持续守这个不变量。

运行：``pytest tests/test_cli_help_quality.py -v``
独立：``python3 tests/test_cli_help_quality.py``
"""
import os
import subprocess
import sys

import click
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
sys.path.insert(0, REPO_ROOT)

from androguard.skills.main import entry_point  # noqa: E402


def _all_commands() -> list:
    """返回 [(group, subcmd, cmd_obj)] 叶子命令列表。"""
    result = []
    for group_name in entry_point.commands:
        group_cmd = entry_point.commands[group_name]
        if not isinstance(group_cmd, click.Group):
            continue
        for sub_name, sub_cmd in group_cmd.commands.items():
            result.append((group_name, sub_name, sub_cmd))
    return result


def _cli_help(group, subcmd):
    """运行 `androguard-skills G S --help`，返回 (code, stdout)。"""
    proc = subprocess.run(
        ["androguard-skills", group, subcmd, "--help"],
        capture_output=True, text=True, timeout=30, cwd=REPO_ROOT,
    )
    return proc.returncode, proc.stdout


def _option_cli_names(cmd) -> list:
    """命令所有 option 的 CLI 长形式名（--foo-bar）。"""
    names = []
    for p in cmd.params:
        if isinstance(p, click.Option):
            for o in p.opts:
                if o.startswith("--") and o != "--help":
                    names.append(o)
    return names


def _argument_names(cmd) -> list:
    """命令所有位置参数的 name（大写形式，Click help 里显示为大写）。

    Click Argument 的 name 是小写下划线形参名，但 --help 里显示为
    UPPER_SNAKE_CASE（如 class_name → CLASS_NAME）。校验用 name 的大写
    形式是否出现在 help 文本里。
    """
    names = []
    for p in cmd.params:
        if isinstance(p, click.Argument):
            # help 里显示为大写，下划线保留
            names.append(p.name.upper())
    return names


# 参数化：每个命令一个测试用例
_COMMANDS = _all_commands()


@pytest.mark.parametrize("group,subcmd,cmd", _COMMANDS,
                         ids=[f"{g}-{s}" for g, s, _ in _COMMANDS])
def test_help_exits_zero_and_lists_params(group, subcmd, cmd):
    """每个命令 --help 必须 exit 0 且列出所有真实参数。"""
    code, out = _cli_help(group, subcmd)
    assert code == 0, (
        f"`androguard-skills {group} {subcmd} --help` 退出码 {code}（应 0）"
    )
    assert out, f"`{group} {subcmd} --help` 无输出"

    # 所有 option 必须在 help 文本里
    missing_opts = []
    for opt in _option_cli_names(cmd):
        if opt not in out:
            missing_opts.append(opt)
    assert not missing_opts, (
        f"`{group} {subcmd} --help` 漏列 option: {missing_opts}"
    )

    # 所有位置参数名（大写形式）必须在 help 文本里
    missing_args = []
    for arg in _argument_names(cmd):
        if arg not in out:
            missing_args.append(arg)
    assert not missing_args, (
        f"`{group} {subcmd} --help` 漏列位置参数: {missing_args}"
    )

    # --help 输出不得含误导性 JSON error 块。
    # 回归守卫：_SkillsCliGroup.invoke 曾用宽泛 `except RuntimeError` 误捕
    # click.exceptions.Exit（--help 触发，Exit 是 RuntimeError 子类），导致每个
    # --help 末尾吐出 `{"error": "0"}`（str(Exit(0))=="0"），agent 跑 --help
    # 查参数时会误以为命令失败。修复后 Exit/Abort 应交还 Click，help 干净。
    assert '"error"' not in out, (
        f"`{group} {subcmd} --help` 输出含误导性 JSON error 块（疑似 Click "
        f"Exit 信号被误捕为业务错误）：\n{out[-400:]}"
    )


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    passed = failed = 0
    for fn in fns:
        try:
            # 参数化测试手动跑：遍历所有命令
            for group, subcmd, cmd in _COMMANDS:
                try:
                    fn(group, subcmd, cmd)
                    passed += 1
                except Exception as e:
                    print(f"  FAIL  {fn.__name__}[{group}-{subcmd}]: {e}")
                    failed += 1
            print(f"  PASS  {fn.__name__} ({len(_COMMANDS)} 命令)")
        except Exception as e:
            print(f"  FAIL  {fn.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
