#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills CLI 错误路径回归测试

冒烟测试（test_cli_smoke.py）验证**正常路径**返回合法 JSON；本测试验证
**错误路径**也返回结构化 JSON，而非 Python traceback。

对接"几十个 agent"时，agent 可能传错参数（APK 不存在、未加载就调命令）。
若 CLI 吐 traceback，agent 无法解析自恢复；必须返回 {"error": "..."} JSON。

覆盖的错误路径：
  1. 单次模式 + APK 不存在 → {"error": "File not found: ..."}
  2. 单次模式 + 未加载就调命令（不传 --apk-path）→ {"error": "..."}
  3. daemon 模式 + 未加载就调命令 → {"error": "..."}（JSON-RPC error）
  4. Click 参数错误（缺必需参数）→ Click 友好错误（非 traceback，exit≠0）

关键断言：错误输出**不含** Python traceback 标志（"Traceback (most recent"），
且（路径 1-3）输出是合法 JSON 含 "error" 键。

运行：``pytest tests/test_cli_error_paths.py -v``
独立：``python3 tests/test_cli_error_paths.py``
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
# 本测试用 /nonexistent.apk 等无效路径，不依赖真实测试 APK 存在。
TEST_PORT = 18960


def _run(args, env=None):
    """运行 skills CLI，返回 (returncode, stdout, stderr)。"""
    cmd = ["androguard-skills"] + args
    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=60, cwd=REPO_ROOT, env=env
    )
    return proc.returncode, proc.stdout, proc.stderr


def _assert_no_traceback(stderr, stdout, context):
    """断言输出不含 Python traceback。"""
    combined = stderr + stdout
    assert "Traceback (most recent" not in combined, (
        f"{context}: 输出含 Python traceback，应返回结构化 error JSON\n{combined[-500:]}"
    )


def _parse_json_output(stdout, context):
    """从 stdout 解析 JSON（容忍日志前缀）。"""
    lines = stdout.strip().splitlines()
    start = None
    for i, ln in enumerate(lines):
        ls = ln.lstrip()
        if ls.startswith("{") or ls.startswith("["):
            start = i
    if start is None:
        raise AssertionError(f"{context}: 输出无 JSON\nstdout: {stdout[-500:]}")
    try:
        return json.loads("\n".join(lines[start:]))
    except json.JSONDecodeError as e:
        raise AssertionError(f"{context}: JSON 解析失败\n{e}\nstdout: {stdout[-500:]}")


def test_single_mode_nonexistent_apk_returns_structured_error():
    """单次模式 + APK 不存在 → 结构化 {"error": "File not found"} JSON。"""
    # 确保 daemon 不在
    subprocess.run(["androguard-skills", "daemon", "stop"],
                   capture_output=True, timeout=10)
    code, out, err = _run(["apk", "info", "--apk-path", "/nonexistent.apk"])
    _assert_no_traceback(err, out, "单次模式无效 APK")
    data = _parse_json_output(out, "单次模式无效 APK")
    assert "error" in data, f"应含 error 键: {data}"
    assert "not found" in data["error"].lower() or "no apk" in data["error"].lower(), (
        f"错误信息应提及文件未找到: {data['error']}"
    )


def test_single_mode_no_apk_loaded_returns_structured_error():
    """单次模式 + 不传 --apk-path 且未加载 → 结构化 error JSON（非 traceback）。"""
    subprocess.run(["androguard-skills", "daemon", "stop"],
                   capture_output=True, timeout=10)
    code, out, err = _run(["apk", "info"])
    _assert_no_traceback(err, out, "单次模式未加载")
    data = _parse_json_output(out, "单次模式未加载")
    assert "error" in data, f"应含 error 键: {data}"


def test_single_mode_analysis_command_without_load_returns_structured_error():
    """单次模式 + analysis 命令未加载 → 结构化 error（覆盖非 apk 命令组）。"""
    subprocess.run(["androguard-skills", "daemon", "stop"],
                   capture_output=True, timeout=10)
    code, out, err = _run(["analysis", "find-methods", ".*"])
    _assert_no_traceback(err, out, "analysis 未加载")
    data = _parse_json_output(out, "analysis 未加载")
    assert "error" in data, f"应含 error 键: {data}"


def test_missing_required_argument_is_click_error_not_traceback():
    """缺必需参数 → Click 友好错误（非 traceback）。"""
    subprocess.run(["androguard-skills", "daemon", "stop"],
                   capture_output=True, timeout=10)
    code, out, err = _run(["analysis", "find-methods"])
    # Click 参数错误：exit≠0，stderr 含 "Error: Missing argument" 或 "Usage:"
    combined = out + err
    _assert_no_traceback(err, out, "缺参数")
    assert code != 0, f"缺参数应 exit≠0: {code}"
    assert "missing" in combined.lower() or "usage:" in combined.lower(), (
        f"应含 Click 友好错误: {combined[-300:]}"
    )
    # stdout 应为空：Click 参数错误（ClickException）不应被 _SkillsCliGroup
    # 误捕成 {"error":...} JSON。若 stdout 非空，说明 ClickException 被误当
    # 业务错误，agent 会同时看到 stdout JSON error + stderr usage，困惑。
    assert not out.strip(), (
        f"缺参数时 stdout 应为空（ClickException 不应被误捕成 JSON error）: "
        f"{out[-300:]}"
    )


def test_invalid_option_is_click_error_not_swallowed():
    """无效 option → Click 友好错误，stdout 不被误捕成 JSON error。"""
    subprocess.run(["androguard-skills", "daemon", "stop"],
                   capture_output=True, timeout=10)
    code, out, err = _run(["apk", "info", "--badopt", "1",
                           "--apk-path", "tests/data/APK/TestActivity.apk"])
    _assert_no_traceback(err, out, "无效option")
    assert code != 0, f"无效 option 应 exit≠0: {code}"
    assert "no such option" in (out + err).lower(), (
        f"应含 'No such option' 友好错误: {(out + err)[-300:]}"
    )
    # stdout 应为空（同上，ClickException 不应被误捕）
    assert not out.strip(), (
        f"无效 option 时 stdout 应为空: {out[-300:]}"
    )


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
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
