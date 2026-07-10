#!/usr/bin/env python3
"""增强内省：从 click 命令树 + main.py 源码，提取每个命令调用的 skills 方法名。

在 introspect_commands.py 基础上，额外解析 main.py 源码，找到每个命令函数体里
调用的 skills.<method>(...) 或 _try_daemon_call("<method>", ...)，注入 method 字段。
输出 commands.json（覆盖）。
"""
import ast
import json
import re
import sys
import os

import click

from androguard.skills.main import entry_point

# 路径基于本脚本位置，无论 cwd 在哪都能正确定位
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
SRC_PATH = os.path.join(REPO_ROOT, "androguard", "skills", "main.py")


def param_info(p):
    names_long = [n for n in p.opts if n.startswith("--")]
    names_short = [n for n in p.opts if n.startswith("-") and not n.startswith("--")]
    display = (names_long + names_short + p.opts + [p.name])[0]
    return {
        "name": display,
        "dest": p.name,
        "type": type(p.type).__name__,
        "required": bool(p.required),
        "default": None if p.default is None else (
            p.default if not callable(p.default) else "<func>"
        ),
        "help": getattr(p, "help", None) or "",
        "is_flag": bool(getattr(p, "is_flag", False)),
        "multiple": bool(getattr(p, "multiple", False)),
        "nargs": getattr(p, "nargs", 1),
        "is_argument": isinstance(p, click.Argument),
        "choices": list(p.type.choices) if isinstance(p.type, click.Choice) else None,
    }


def extract_commands(group):
    cmds = []
    for name in sorted(group.commands.keys()):
        cmd = group.commands[name]
        if not isinstance(cmd, click.Command):
            continue
        cmds.append({
            "name": name,
            "help": (cmd.help or cmd.short_help or "").strip(),
            "params": [param_info(p) for p in cmd.params],
            "callback_name": cmd.callback.__name__ if cmd.callback else None,
        })
    return cmds


# ---- 从源码 AST 提取每个命令函数体里的 skills.<method>(...) 调用 ----
def find_skills_methods(src_path):
    """返回 {callback_func_name: [skills_method_name, ...]}"""
    src = open(src_path, encoding="utf-8").read()
    tree = ast.parse(src)
    mapping = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods = []
            for sub in ast.walk(node):
                # skills.foo(...) 或 self.skills.foo(...) —— Attribute 调用
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
                    attr = sub.func.attr
                    # 只收录看起来像 skills 方法的调用（排除 _get_skills/_output_json/_try_daemon_call 等辅助）
                    if attr.startswith("_"):
                        continue
                    # _try_daemon_call("method", ...) 里的字符串才是真正的 method
                    if attr == "try_daemon_call" or sub.func.attr.endswith("try_daemon_call"):
                        pass
                    # 收录 skills.<attr> 形式：func.value 是 Name(id=skills) 或 self.skills
                    val = sub.func.value
                    if isinstance(val, ast.Name) and val.id == "skills":
                        methods.append(attr)
                    elif isinstance(val, ast.Attribute) and val.attr == "skills":
                        methods.append(attr)
                # _try_daemon_call("xxx", ...)
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) \
                        and sub.func.id == "_try_daemon_call":
                    if sub.args and isinstance(sub.args[0], ast.Constant):
                        methods.append(sub.args[0].value)
            if methods:
                mapping[node.name] = methods
    return mapping


def main():
    with open(SRC_PATH, encoding="utf-8") as f:
        pass
    method_map = find_skills_methods(SRC_PATH)

    data = {}
    top_groups = []
    top_commands = []
    for name, cmd in entry_point.commands.items():
        if isinstance(cmd, click.Group):
            top_groups.append((name, cmd))
        elif isinstance(cmd, click.Command):
            top_commands.append((name, cmd))

    top = []
    for name, cmd in sorted(top_commands):
        cb = cmd.callback.__name__ if cmd.callback else None
        top.append({
            "name": name,
            "help": (cmd.help or cmd.short_help or "").strip(),
            "params": [param_info(p) for p in cmd.params],
            "callback_name": cb,
            "methods": method_map.get(cb, []),
        })
    data["__top__"] = {"title": "顶层命令", "help": entry_point.help, "commands": top}

    for name, grp in sorted(top_groups):
        cmds = extract_commands(grp)
        for c in cmds:
            c["methods"] = method_map.get(c["callback_name"], [])
        data[name] = {
            "title": name,
            "help": (grp.help or "").strip(),
            "commands": cmds,
        }

    json.dump(data, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
