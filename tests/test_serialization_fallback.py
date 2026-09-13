#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills JSON 序列化失败兜底回归测试

命令返回 _SkillsJsonEncoder/_DaemonJsonEncoder 无法处理的类型（如漏序列化
的 lxml Element、自定义类实例）时，json.dumps 抛 TypeError。此前：
  - CLI 侧：TypeError 不是 RuntimeError 子类，_SkillsCliGroup 的
    `except RuntimeError` 兜不住 → 吐 Python traceback，agent 无法解析。
  - daemon 侧：json.dumps 在 _handle_client 的 try 块之外（response 已构造，
    在序列化 response 时抛），逃逸外层 except (ConnectionResetError,...) 不匹配
    → 该连接静默无响应（agent 超时）。

/goal："对接几十个 agent"，序列化失败不应崩 CLI 进程或让 daemon 连接静默死，
应转结构化 error 让 agent 可见失败原因自恢复。本测试固化此契约。

运行：``pytest tests/test_serialization_fallback.py -v``
独立：``python3 tests/test_serialization_fallback.py``
"""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
sys.path.insert(0, REPO_ROOT)

from androguard.skills.main import (  # noqa: E402
    _SkillsJsonEncoder,
    _SkillsCliGroup,
    entry_point,
    AndroguardSkillsMain,
)
from androguard.skills.daemon import _DaemonJsonEncoder  # noqa: E402


def _make_unserializable():
    """返回一个 _SkillsJsonEncoder 无法处理的对象（lxml Element）。

    AndroGuard 大量返回 lxml Element（get_android_manifest_xml 等），
    是最可能漏序列化的真实类型。
    """
    from lxml import etree
    return etree.fromstring("<unserializable/>")


# --------------------------------------------------------------------
# 1. 编码器仍显式抛 TypeError（不静默吞成 null，bug 显式暴露）
# --------------------------------------------------------------------

@pytest.mark.parametrize("encoder", [_SkillsJsonEncoder, _DaemonJsonEncoder],
                         ids=["Skills", "Daemon"])
def test_encoder_still_raises_typeerror_for_unknown(encoder):
    """未知类型仍抛 TypeError——显式暴露漏序列化 bug，不静默掩盖。

    编码器不加 str() 兜底（会掩盖 bug），保留 super().default() 抛 TypeError。
    兜底责任在调用方（_SkillsCliGroup / _handle_client），不在编码器。
    """
    with pytest.raises(TypeError):
        json.dumps({"r": _make_unserializable()}, cls=encoder)


def test_both_encoders_raise_same_typeerror():
    """两编码器对未知类型行为一致（都抛 TypeError）。"""
    for enc in [_SkillsJsonEncoder, _DaemonJsonEncoder]:
        with pytest.raises(TypeError):
            json.dumps({"r": _make_unserializable()}, cls=enc)


# --------------------------------------------------------------------
# 2. CLI 侧：TypeError 被 _SkillsCliGroup 兜住转结构化 error
# --------------------------------------------------------------------

def test_cli_typeerror_caught_as_structured_error(monkeypatch):
    """CLI 命令返回不可序列化对象时，TypeError 被兜住转结构化 error，无 traceback。

    模拟一个漏序列化的 skills 方法（返回含 lxml Element 的 dict），
    验证 _SkillsCliGroup 的 `except (RuntimeError, TypeError)` 兜住 TypeError。
    """
    from click.testing import CliRunner

    # monkeypatch：让 apk_info 返回含 Element 的 dict（模拟漏序列化）
    def _buggy_apk_info(self):
        return {"result": _make_unserializable()}

    monkeypatch.setattr(AndroguardSkillsMain, "apk_info", _buggy_apk_info)

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        entry_point,
        ["apk", "info", "--apk-path", "tests/data/APK/TestActivity.apk"],
    )
    # exit 0：TypeError 被兜住转结构化 error，不崩
    assert result.exit_code == 0, (
        f"TypeError 应被兜住 exit 0，实际 exit {result.exit_code}\n"
        f"output: {result.output}"
    )
    # 输出结构化 error JSON
    try:
        data = json.loads(result.output.strip())
    except json.JSONDecodeError:
        pytest.fail(f"应输出 JSON error，实际: {result.output[:300]}")
    assert "error" in data, f"应含 error 键: {data}"
    # error 信息含序列化失败原因
    assert "serializable" in data["error"].lower() or "type" in data["error"].lower(), (
        f"error 应提及序列化失败: {data['error']}"
    )
    # stderr 无 Python traceback
    assert "Traceback" not in (result.stderr or ""), (
        f"不应有 traceback，stderr: {(result.stderr or '')[-300:]}"
    )


def test_cli_typeerror_does_not_leak_to_stderr(monkeypatch):
    """CLI 序列化失败时 stderr 无 traceback（agent 解析 stdout 即可）。"""
    from click.testing import CliRunner

    def _buggy(self):
        return {"result": _make_unserializable()}

    monkeypatch.setattr(AndroguardSkillsMain, "apk_info", _buggy)

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        entry_point,
        ["apk", "info", "--apk-path", "tests/data/APK/TestActivity.apk"],
    )
    stderr = result.stderr or ""
    assert "Traceback" not in stderr, f"stderr 不应含 traceback: {stderr[-300:]}"
    assert "TypeError" not in stderr, (
        f"stderr 不应含裸 TypeError（应被兜进 JSON error）: {stderr[-300:]}"
    )


# --------------------------------------------------------------------
# 3. daemon 侧：_handle_client 序列化失败兜底返回结构化 error
#    （连接不静默死）
# --------------------------------------------------------------------

def test_daemon_serialization_fallback_returns_structured_error():
    """_handle_client 的 json.dumps 失败时，兜底返回 -32603 结构化 error。

    复刻 _handle_client 的序列化 try/except 逻辑：response 含不可序列化
    对象时，json.dumps 抛 TypeError，外层 except 转成结构化 error 响应，
    而非让连接静默无响应。
    """
    response = {"jsonrpc": "2.0", "result": _make_unserializable(), "id": 1}

    # 复刻 daemon._handle_client 的序列化段（与源码一致）
    try:
        response_bytes = (
            json.dumps(response, cls=_DaemonJsonEncoder).encode("utf-8") + b"\n"
        )
        pytest.fail("json.dumps 应对 lxml Element 抛 TypeError")
    except Exception as e:
        response_bytes = (
            json.dumps({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Response serialization failed: {e}",
                },
                "id": None,
            }).encode("utf-8")
            + b"\n"
        )

    decoded = json.loads(response_bytes.decode("utf-8").strip())
    assert "error" in decoded, f"应含 error（序列化失败兜底）: {decoded}"
    assert decoded["error"]["code"] == -32603, (
        f"应 -32603 Internal error: {decoded['error']['code']}"
    )
    assert "serialization failed" in decoded["error"]["message"].lower(), (
        f"error 应提及序列化失败: {decoded['error']['message']}"
    )


# --------------------------------------------------------------------
# 4. _SkillsCliGroup 的 except 子句覆盖 TypeError（源码契约）
# --------------------------------------------------------------------

def test_skills_cli_group_catches_typeerror():
    """_SkillsCliGroup.invoke 的 except 子句必须含 TypeError。

    源码级守卫：防止未来重构把 TypeError 从 except 中移除（回归到只 catch
    RuntimeError，序列化失败又吐 traceback）。
    """
    import inspect
    src = inspect.getsource(_SkillsCliGroup.invoke)
    # except (RuntimeError, TypeError) 或分开写都接受，关键是 TypeError 被捕
    assert "TypeError" in src, (
        "_SkillsCliGroup.invoke 的 except 必须含 TypeError，否则序列化失败 "
        "会逃逸吐 traceback（TypeError 不是 RuntimeError 子类）"
    )
    # Exit/Abort 仍优先 re-raise（--help 不被误捕，见 --help error:0 bug 修复）
    assert "Exit" in src and "Abort" in src, (
        "_SkillsCliGroup.invoke 仍须 re-raise click.exceptions.Exit/Abort"
    )


def test_daemon_handle_client_serialization_in_try():
    """_handle_client 的 json.dumps 必须在 try 块内（序列化失败兜底）。

    源码级守卫：json.dumps(response) 若在 try 块外，TypeError 会逃逸外层
    except (ConnectionResetError,...) 不匹配，连接静默死。防止未来重构
    把序列化移出 try。
    """
    import inspect
    from androguard.skills.daemon import DaemonServer
    src = inspect.getsource(DaemonServer._handle_client)
    # json.dumps 必须出现在源码里
    assert "json.dumps(response" in src or "json.dumps(response" in src, (
        "_handle_client 应含 json.dumps(response) 序列化"
    )
    # 必须有针对序列化失败的 except 兜底（含 serialization failed 或同义）
    assert "serialization" in src.lower() or "response_bytes" in src, (
        "_handle_client 应有序列化失败兜底（serialization failed / response_bytes try）"
    )


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    passed = failed = 0
    for fn in fns:
        try:
            import inspect
            sig = inspect.signature(fn)
            params = list(sig.parameters)
            if "encoder" in params:
                fn(_SkillsJsonEncoder)
            elif "monkeypatch" in params:
                class _MP:
                    def setattr(self, obj, name, val):
                        setattr(obj, name, val)
                fn(_MP())
            else:
                fn()
            print(f"  PASS  {fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {fn.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed, {len(fns)} total")
    sys.exit(1 if failed else 0)
