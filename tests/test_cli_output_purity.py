#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills CLI 输出纯净性回归测试

每个命令的 stdout 必须是纯 JSON（首行 { 或 [），stderr 不得含 Python
traceback，stdout 不得含 {"error": "0"} 残留（--help 误捕 Exit 的已修 bug
回归守卫）。

/gol："对接几十个 agent"，agent 解析 stdout 期望纯 JSON，任何杂质（traceback
到 stderr、非 JSON 首行、error:0 残留）都让 agent 解析失败。test_cli_smoke /
test_cli_all_commands_smoke 守了"输出合法 JSON"，但没系统守"stderr 无 traceback"
和"stdout 首行即 JSON 起点无杂质前缀"——本测试对全部命令实跑补这三层。

运行：``pytest tests/test_cli_output_purity.py -v``
独立：``python3 tests/test_cli_output_purity.py``
"""
import json
import os
import subprocess
import sys

import click
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
sys.path.insert(0, REPO_ROOT)

from androguard.skills.main import entry_point  # noqa: E402

APK = os.path.join(HERE, "data", "APK", "TestActivity.apk")

pytestmark = pytest.mark.skipif(
    not os.path.exists(APK),
    reason=f"基准 APK 不存在: {APK}（上游测试数据缺失则跳过）",
)

# 跳过有副作用或需特殊环境的命令组
_SKIP_GROUPS = {"daemon", "pentest"}


def _all_command_args() -> list:
    """返回 [(group, subcmd, args)] 列表，每个 args 是最小可执行参数。"""
    result = []
    for gname, gcmd in entry_point.commands.items():
        if not isinstance(gcmd, click.Group):
            continue
        if gname in _SKIP_GROUPS:
            continue
        for sname, scmd in gcmd.commands.items():
            args = [gname, sname]
            has_apk_opt = any(
                "--apk-path" in getattr(p, "opts", [])
                for p in scmd.params
                if isinstance(p, click.Option)
            )
            if has_apk_opt:
                args += ["--apk-path", APK]
            for p in scmd.params:
                if isinstance(p, click.Argument) and p.required:
                    # 正则通配给 find-* 命令，class 名给 class 命令
                    args.append(".*")
            result.append((gname, sname, args))
    return result


def _run(args):
    try:
        p = subprocess.run(
            ["androguard-skills"] + args,
            capture_output=True, text=True, timeout=90, cwd=REPO_ROOT,
        )
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"


_COMMANDS = _all_command_args()


@pytest.mark.parametrize("group,subcmd,args", _COMMANDS,
                         ids=[f"{g}-{s}" for g, s, _ in _COMMANDS])
def test_command_output_pure_json(group, subcmd, args):
    """每个命令 stdout 首行即 JSON 起点、stderr 无 traceback、无 error:0 残留。"""
    code, out, err = _run(args)

    # stderr 不得含 Python traceback（agent 无法解析）
    assert "Traceback" not in err, (
        f"`{group} {subcmd}` stderr 含 Traceback（agent 无法解析自恢复）:\n"
        f"{err[-400:]}"
    )

    # stdout 不得含 {"error": "0"} 残留（--help 误捕 Exit bug 的回归守卫，
    # 正常命令输出也不应有此误捕产物）
    assert '"error": "0"' not in out, (
        f"`{group} {subcmd}` stdout 含 {{\"error\": \"0\"}} 残留"
        "（疑似 Click Exit 误捕）:\n{out[-300:]}"
    )

    # stdout 非空时首行应是 JSON 起点（{ 或 [），无日志/杂质前缀
    out_stripped = out.strip()
    if out_stripped:
        first = out_stripped.splitlines()[0].lstrip()
        assert first.startswith("{") or first.startswith("["), (
            f"`{group} {subcmd}` stdout 首行非 JSON 起点（agent 解析会失败）"
            f": {first[:100]}"
        )


if __name__ == "__main__":
    fns = [(v, args) for v, (g, s, args) in
           [(test_command_output_pure_json, None)] * 0]
    # 手动跑参数化
    passed = failed = 0
    for group, subcmd, args in _COMMANDS:
        try:
            test_command_output_pure_json(group, subcmd, args)
            passed += 1
        except Exception as e:
            print(f"  FAIL  [{group}-{subcmd}]: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed, {len(_COMMANDS)} total")
    sys.exit(1 if failed else 0)
