#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills daemon 方法路由完整性回归测试

CLI 命令通过 _try_daemon_call("method_name", ...) 调 daemon，daemon 端
_dispatch 用 getattr(skills, method_name) 动态分发到 AndroguardSkillsMain
方法。若 CLI 写错 method 名（与类方法不匹配）或删了类方法，daemon 返回
method not found (-32601)，但单次 fallback 仍工作——test_cli_all_commands_smoke
（测单次模式）抓不到此 bug，agent 用 daemon 模式会失败
（/goal："对接几十个 agent"，daemon 是推荐模式，路由错=agent 不可用）。

本测试从 main.py 源码提取所有 _try_daemon_call("method") 的 method 名，
验证每个都在 AndroguardSkillsMain 有对应公开方法（daemon 可路由）。

运行：``pytest tests/test_daemon_method_routing.py -v``
独立：``python3 tests/test_daemon_method_routing.py``
"""
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
sys.path.insert(0, REPO_ROOT)

from androguard.skills.main import AndroguardSkillsMain  # noqa: E402

MAIN_PY = os.path.join(REPO_ROOT, "androguard", "skills", "main.py")

# 提取所有 _try_daemon_call("method_name", ...) 的 method 名
_METHOD_RE = re.compile(r'_try_daemon_call\(\s*"([a-z_]+)"')


def _daemon_methods_in_source():
    """从 main.py 源码提取所有 _try_daemon_call 的 method 名。"""
    with open(MAIN_PY, "r", encoding="utf-8") as f:
        src = f.read()
    return set(_METHOD_RE.findall(src))


def _class_public_methods():
    """AndroguardSkillsMain 的公开方法集合（不以 _ 开头）。"""
    return {
        m for m in dir(AndroguardSkillsMain)
        if not m.startswith("_") and callable(getattr(AndroguardSkillsMain, m))
    }


def test_all_daemon_methods_routable():
    """每个 _try_daemon_call 的 method 名必须在 AndroguardSkillsMain 有对应方法。"""
    daemon_methods = _daemon_methods_in_source()
    assert daemon_methods, "未从 main.py 提取到 _try_daemon_call method 名"

    cls_methods = _class_public_methods()
    assert cls_methods, "AndroguardSkillsMain 无公开方法——内省可能失效"

    missing = daemon_methods - cls_methods
    assert not missing, (
        f"{len(missing)} 个 daemon 路由的 method 在 AndroguardSkillsMain 缺失"
        f"（daemon 模式会返回 method not found）：\n"
        + "\n".join(f"  - {m}" for m in sorted(missing))
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
