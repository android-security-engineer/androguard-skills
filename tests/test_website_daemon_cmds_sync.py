#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills 文档站 daemon_cmds.json 与 CLI 同步回归测试

daemon_cmds.json 是文档站对 daemon 命令组（start/stop/status）的内省输出，
含命令名/参数/line 号。它没有专用生成脚本（不像 commands.json 由
introspect_commands.py 生成），易随 main.py 变化漂移——daemon 命令改名/改参数
后 daemon_cmds.json 不跟，文档站会过时。

本测试不重新生成（无生成脚本），而是校验 daemon_cmds.json 里记录的命令名和
参数名与当前 CLI 真实 daemon 命令一致（line 号不校验，随源码必然漂移）。

运行：``pytest tests/test_website_daemon_cmds_sync.py -v``
独立：``python3 tests/test_website_daemon_cmds_sync.py``
"""
import json
import os
import sys

import click
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
sys.path.insert(0, REPO_ROOT)

from androguard.skills.main import entry_point  # noqa: E402

DAEMON_CMDS_JSON = os.path.join(
    REPO_ROOT, "website", "scripts", "daemon_cmds.json"
)


def _real_daemon_commands() -> dict:
    """从 click 树拿 daemon 组的真实命令名→参数名集合。"""
    daemon_group = entry_point.commands.get("daemon")
    if not isinstance(daemon_group, click.Group):
        return {}
    result = {}
    for name, cmd in daemon_group.commands.items():
        params = set()
        for p in cmd.params:
            if isinstance(p, click.Option):
                for o in p.opts:
                    if o.startswith("--"):
                        params.add(o)
        result[name] = params
    return result


def test_daemon_cmds_json_matches_cli():
    """daemon_cmds.json 里的命令名和参数名与 CLI 真实 daemon 命令一致。"""
    if not os.path.exists(DAEMON_CMDS_JSON):
        pytest.skip("daemon_cmds.json 不存在")

    with open(DAEMON_CMDS_JSON, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    # data 结构：{"daemon": {"commands": [{"name":..., "params":[...]}, ...]}}
    daemon_section = data.get("daemon", {})
    json_cmds = {}
    for cmd in daemon_section.get("commands", []):
        name = cmd.get("name")
        params = set()
        for p in cmd.get("params", []):
            pname = p.get("name")
            if pname and pname.startswith("--"):
                params.add(pname)
        if name:
            json_cmds[name] = params

    real = _real_daemon_commands()
    assert real, "CLI 无 daemon 命令组——内省可能失效"
    assert json_cmds, "daemon_cmds.json 无命令——解析可能失效"

    # 命令名集合一致
    assert set(json_cmds.keys()) == set(real.keys()), (
        f"daemon_cmds.json 命令名与 CLI 不符: "
        f"json={sorted(json_cmds.keys())} cli={sorted(real.keys())}"
    )

    # 每个命令的参数名集合一致
    for name in real:
        json_params = json_cmds[name]
        # 去掉 --help（CLI 内省不含，json 可能含）
        json_params = {p for p in json_params if p != "--help"}
        assert json_params == real[name], (
            f"daemon_cmds.json 里 daemon {name} 参数与 CLI 不符: "
            f"json={sorted(json_params)} cli={sorted(real[name])}"
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
