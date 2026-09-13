#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills SKILLS 文档参数签名一致性回归测试

test_docs_consistency.py 只校验命令名存在/不缺文档/索引不失修，但不校验
**参数签名**——文档可能写了 `--foo` 但命令真实参数是 `--bar`，agent 照文档
用会报 "no such option"（/goal："对接几十个 agent"，文档漂移直接让 agent
踩坑）。

本测试两层硬校验（无假阳性）：

1. **全局幽灵 option 检测**：文档里出现的每个 `--option` 必须在 CLI 至少一个
   命令的真实 option 里存在。文档写了 CLI 完全不认识的 `--option` 即 bug。

2. **位置参数误用检测**：文档里若把命令的**位置参数**当 `--option` 写
   （如 `dex cm-lookup --idx` 但 idx 实为位置参数），agent 照用会报
   "no such option"。Click 位置参数（Argument）的 name 不以 -- 开头，
   若文档里出现 `--<argname>` 且该 name 是某命令的 Argument name → 误用。

不做命令级段归属核对——多命令同段时参数归属无法可靠判定，假阳性高。
命令名存在性已由 test_docs_consistency 守。

运行：``pytest tests/test_docs_param_consistency.py -v``
独立：``python3 tests/test_docs_param_consistency.py``
"""
import os
import re
import sys
from collections import defaultdict

import click
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
SKILLS_DIR = os.path.join(REPO_ROOT, "SKILLS")
sys.path.insert(0, REPO_ROOT)

from androguard.skills.main import entry_point  # noqa: E402


# --------------------------------------------------------------------
# Click 内省
# --------------------------------------------------------------------


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


def _cli_option_names(cmd) -> set:
    """从 Click Command 提取所有 option 的 CLI 形式名（--foo-bar）。"""
    names = set()
    for p in cmd.params:
        if isinstance(p, click.Option):
            for o in p.opts:
                if o.startswith("--"):
                    names.add(o)
    return names


def _all_option_names() -> set:
    """所有命令所有 option 的 CLI 形式（--foo-bar）并集。"""
    known = set()
    for _, _, cmd in _all_commands():
        for p in cmd.params:
            if isinstance(p, click.Option):
                for o in p.opts:
                    if o.startswith("--"):
                        known.add(o)
    return known


def _all_argument_names() -> set:
    """所有命令所有位置参数（Argument）的 Python 形参名（下划线）并集。

    用于检测文档把位置参数当 --option 写的情况。
    """
    names = set()
    for _, _, cmd in _all_commands():
        for p in cmd.params:
            if isinstance(p, click.Argument):
                names.add(p.name)  # 形参名，如 "idx"
    return names


def _argument_name_to_option(name: str) -> str:
    """形参名（idx）→ 文档可能误写的 option 形式（--idx）。"""
    return "--" + name.replace("_", "-")


# --------------------------------------------------------------------
# 文档扫描
# --------------------------------------------------------------------


_OPTION_RE = re.compile(r"(?<![A-Za-z0-9-])--[a-z][a-z0-9-]*(?![A-Za-z0-9])")


def _scan_doc_options() -> dict:
    """扫所有 SKILLS/*.md，返回 {doc_file: set_of_option_strings}。"""
    found = defaultdict(set)
    for fname in sorted(os.listdir(SKILLS_DIR)):
        if not fname.endswith(".md"):
            continue
        with open(os.path.join(SKILLS_DIR, fname), "r", encoding="utf-8") as fh:
            for m in _OPTION_RE.finditer(fh.read()):
                found[fname].add(m.group(0))
    return found


# --------------------------------------------------------------------
# 测试
# --------------------------------------------------------------------


def test_no_ghost_options_in_docs():
    """文档里每个 --option 必须在 CLI 至少一个命令里真实存在。

    捕获：文档写了 CLI 完全不认识的参数（笔误如 --lmit、改名后文档没跟、
    或凭空杜撰的参数）。agent 照文档用会报 "no such option"。
    """
    known = _all_option_names()
    assert known, "Click 内省未拿到任何 option——内省可能失效"

    doc_options = _scan_doc_options()
    assert doc_options, "文档里未扫到任何 --option——扫描正则可能失效"

    ghosts = []
    for fname, opts in sorted(doc_options.items()):
        for opt in sorted(opts):
            if opt not in known:
                ghosts.append(f"{fname}: `{opt}` 不被任何 CLI 命令识别")
    assert not ghosts, (
        f"发现 {len(ghosts)} 个文档里的参数 CLI 不识别（笔误/改名/杜撰）：\n"
        + "\n".join(f"  - {g}" for g in ghosts[:40])
    )


def test_no_positional_argument_misused_as_option():
    """位置参数不得在文档里被当 --option 写。

    若 `idx` 是某命令的 Argument（位置参数），文档里出现 `--idx` 即误用——
    agent 照 `cmd --idx 5` 用会报 "no such option"，正确用法是 `cmd 5`。
    """
    arg_names = _all_argument_names()
    # 形参名 → 可能被误写的 --option 形式
    suspect_options = {
        _argument_name_to_option(n): n for n in arg_names
    }

    doc_options = _scan_doc_options()
    misused = []
    for fname, opts in sorted(doc_options.items()):
        for opt in sorted(opts):
            # 该 option 既不被任何命令识别为合法 option，
            # 又恰好是某命令位置参数的 --option 形式 → 位置参数误用
            if opt in suspect_options and opt not in _all_option_names():
                misused.append(
                    f"{fname}: `{opt}` 实为位置参数 "
                    f"`{suspect_options[opt]}`，不应写成 --option"
                )
    assert not misused, (
        f"发现 {len(misused)} 处位置参数被当 --option 写（agent 照用会报 "
        f"no such option）：\n"
        + "\n".join(f"  - {m}" for m in misused[:40])
    )


def test_known_options_have_docs_or_are_optional():
    """宽松信息性校验（不 fail）：CLI 真实参数不必都在文档里。

    但若某个非通用参数完全无文档提及，打印提示（这些可能是合理省略）。
    通用参数白名单见 _COMMON_OPTIONS。
    """
    _COMMON_OPTIONS = {"--apk-path", "--limit", "--per-type-limit",
                       "--per-sink-limit", "--max-depth", "--max-nodes",
                       "--locale", "--raw", "--package"}
    doc_options = _scan_doc_options()
    all_doc = set()
    for opts in doc_options.values():
        all_doc |= opts

    all_cmds = _all_commands()
    undocumented = set()
    for g, s, cmd in all_cmds:
        for p in cmd.params:
            if isinstance(p, click.Option):
                for o in p.opts:
                    if o.startswith("--") and o not in _COMMON_OPTIONS:
                        if o not in all_doc:
                            undocumented.add(f"{g} {s}: `{o}`")

    if undocumented:
        print(f"\n[信息] {len(undocumented)} 个非通用参数未在任何文档提及"
              f"（可能合理省略，仅提示）：")
        for u in sorted(undocumented)[:20]:
            print(f"  - {u}")


def test_command_example_line_options_match():
    """单行示例核对：每条 `androguard-skills G S --opt ...` 示例行上的
    `--option` 必须属于该命令的真实 option。

    单行归属无歧义（不像段范围会跨到下一个命令的参数描述），无假阳性。
    捕获：示例行里给 A 命令传了 B 命令才有的参数，agent 照用会报
    "no such option"。
    """
    all_cmds = _all_commands()
    # (group, subcmd) → 真实 option 集合
    real = {(g, s): _cli_option_names(cmd) for g, s, cmd in all_cmds}

    cmd_example_re = re.compile(
        r"androguard-skills\s+(apk|dex|analysis|resources|decompile|util|"
        r"session|visualize|pentest)\s+([a-z][a-z0-9-]*)"
    )

    mismatches = []
    for fname in sorted(os.listdir(SKILLS_DIR)):
        if not fname.endswith(".md"):
            continue
        with open(os.path.join(SKILLS_DIR, fname), "r", encoding="utf-8") as fh:
            for i, line in enumerate(fh, 1):
                m = cmd_example_re.search(line)
                if not m:
                    continue
                key = (m.group(1), m.group(2))
                if key not in real:
                    continue  # 命令不存在已由 test_docs_consistency 守
                real_opts = real[key]
                # 提取该行所有 --option
                for om in _OPTION_RE.finditer(line):
                    opt = om.group(0)
                    if opt not in real_opts:
                        mismatches.append(
                            f"{fname}:{i} `androguard-skills {key[0]} "
                            f"{key[1]}` 示例行含 `{opt}`，但该命令真实 "
                            f"option 为 {sorted(real_opts) or '(无)'}"
                        )

    assert not mismatches, (
        f"发现 {len(mismatches)} 处示例行参数与该命令真实参数不符：\n"
        + "\n".join(f"  - {m}" for m in mismatches[:40])
    )


# 命令标题：## `analysis crypto-usage [--limit]` 或 ## `apk deeplinks`
_HEADING_CMD_RE = re.compile(
    r"^##\s+`?(apk|dex|analysis|resources|decompile|util|session|"
    r"visualize|pentest)\s+([a-z][a-z0-9-]*)"
)
# 参数表行：| `--foo` | 说明 |  或  | --foo | 说明 |
_PARAM_TABLE_RE = re.compile(r"^\|\s*`?--[a-z][a-z0-9-]*`?\s*\|")


def test_param_table_options_match_heading_command():
    """参数表核对：文档里 `| --option | 说明 |` 表格行的 option 必须属于
    该参数表上方最近的 `## G S` 标题命令的真实参数。

    捕获：参数表里列了该命令不存在的参数（agent 照用报 no such option）。
    无 `## G S` 标题的文档（如 README.md 索引表）跳过——归属不明不校验。
    """
    all_cmds = _all_commands()
    real = {(g, s): _cli_option_names(cmd) for g, s, cmd in all_cmds}

    mismatches = []
    for fname in sorted(os.listdir(SKILLS_DIR)):
        if not fname.endswith(".md"):
            continue
        current_cmd = None  # (group, subcmd) 或 None
        with open(os.path.join(SKILLS_DIR, fname), "r", encoding="utf-8") as fh:
            for i, line in enumerate(fh, 1):
                # 更新当前命令（最近的 ## 标题）
                hm = _HEADING_CMD_RE.match(line)
                if hm:
                    current_cmd = (hm.group(1), hm.group(2))
                    continue
                # 参数表行
                if not _PARAM_TABLE_RE.match(line):
                    continue
                if current_cmd is None:
                    continue  # 无标题归属，跳过
                if current_cmd not in real:
                    continue  # 命令不存在已由别的测试守
                real_opts = real[current_cmd]
                for om in _OPTION_RE.finditer(line):
                    opt = om.group(0)
                    if opt not in real_opts:
                        mismatches.append(
                            f"{fname}:{i} `{current_cmd[0]} "
                            f"{current_cmd[1]}` 参数表含 `{opt}`，但该命令"
                            f"真实 option 为 {sorted(real_opts) or '(无)'}"
                        )

    assert not mismatches, (
        f"发现 {len(mismatches)} 处参数表参数与命令真实参数不符：\n"
        + "\n".join(f"  - {m}" for m in mismatches[:40])
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
