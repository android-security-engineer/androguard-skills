#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills CLI ANDROGUARD_APK_PATH 环境变量回退回归测试

每个 apk/dex/analysis 命令的 --apk-path 选项配了 envvar="ANDROGUARD_APK_PATH"，
agent 可设环境变量避免每次传参（/goal："对接几十个 agent"，envvar 回退让
agent 调用更简洁）。但此回退行为此前无测试固化——若 envvar 配置被删或
回退逻辑失效，agent 设了环境变量命令仍报 "No APK loaded"。

本测试设环境变量后跑若干代表性命令，确认能正常加载 APK 并返回结果
（而非 "No APK loaded" error）。

运行：``pytest tests/test_envvar_apk_path.py -v``
独立：``python3 tests/test_envvar_apk_path.py``
"""
import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))

_TEST_APK = os.path.join(HERE, "data", "APK", "TestActivity.apk")
_NEED_APK = pytest.mark.skipif(
    not os.path.exists(_TEST_APK), reason=f"测试 APK 不存在: {_TEST_APK}"
)


def _cli_with_env(*args, env_extra, timeout=60):
    """运行 CLI，注入额外环境变量，返回 (code, stdout)。"""
    env = os.environ.copy()
    env.update(env_extra)
    proc = subprocess.run(
        ["androguard-skills", *args],
        capture_output=True, text=True, timeout=timeout,
        cwd=REPO_ROOT, env=env,
    )
    return proc.returncode, proc.stdout


@_NEED_APK
def test_envvar_apk_path_loads_apk_for_apk_info():
    """设 ANDROGUARD_APK_PATH 后 `apk info`（不传 --apk-path）能加载。"""
    code, out = _cli_with_env(
        "apk", "info", env_extra={"ANDROGUARD_APK_PATH": _TEST_APK}
    )
    assert code == 0, f"退出码 {code}: {out}"
    data = json.loads(out)
    assert "error" not in data, f"不应有 error（envvar 应让命令加载 APK）: {data}"
    assert "package" in data, f"应返回 APK 信息: {data}"


@_NEED_APK
def test_envvar_apk_path_loads_apk_for_dex_header():
    """设 ANDROGUARD_APK_PATH 后 `dex header`（不传 --apk-path）能加载。"""
    code, out = _cli_with_env(
        "dex", "header", env_extra={"ANDROGUARD_APK_PATH": _TEST_APK}
    )
    assert code == 0
    data = json.loads(out)
    assert "error" not in data, f"envvar 回退失效: {data}"
    assert "header" in data, f"应返回 DEX 头: {data}"


@_NEED_APK
def test_envvar_apk_path_loads_apk_for_analysis_class_exists():
    """设 ANDROGUARD_APK_PATH 后 `analysis class-exists` 能加载。"""
    code, out = _cli_with_env(
        "analysis", "class-exists", "Lcom/example/NonExistent;",
        env_extra={"ANDROGUARD_APK_PATH": _TEST_APK}, timeout=120,
    )
    assert code == 0
    data = json.loads(out)
    assert "error" not in data, f"envvar 回退失效: {data}"
    # 应有 exists/present/result 字段
    assert any(k in data for k in ("exists", "present", "result")), (
        f"应返回类存在性结果: {data}"
    )


@_NEED_APK
def test_explicit_apk_path_overrides_envvar():
    """显式 --apk-path 优先于环境变量（envvar 设错路径，--apk-path 正确）。"""
    code, out = _cli_with_env(
        "apk", "info", "--apk-path", _TEST_APK,
        env_extra={"ANDROGUARD_APK_PATH": "/nonexistent/wrong.apk"},
    )
    assert code == 0
    data = json.loads(out)
    assert "error" not in data, (
        f"显式 --apk-path 应优先于错误的 envvar: {data}"
    )
    assert "package" in data


@_NEED_APK
def test_no_envvar_no_arg_reports_error():
    """既无环境变量又无 --apk-path 时报结构化 error（不 traceback）。"""
    # 确保环境变量未设
    env = os.environ.copy()
    env.pop("ANDROGUARD_APK_PATH", None)
    proc = subprocess.run(
        ["androguard-skills", "apk", "info"],
        capture_output=True, text=True, timeout=30, cwd=REPO_ROOT, env=env,
    )
    assert proc.returncode == 0  # _SkillsCliGroup 捕获 RuntimeError 后 exit 0
    data = json.loads(proc.stdout)
    assert "error" in data
    assert "No APK loaded" in data["error"] or "apk-path" in data["error"].lower()


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
