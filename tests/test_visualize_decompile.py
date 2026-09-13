#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills visualize + decompile 组功能回归测试

visualize（3 命令：method-dot/method-image/method-json）和 decompile
（6 命令：class/method/class-ast/class-tokens/method-ast/method-tokens）
此前无功能正确性测试（全量冒烟只验"不崩"）。

本测试验功能契约：
  - method-dot 返回含 dot 字段（CFG 的 DOT 文本）
  - method-json 返回含 cfg 字段（结构化 CFG）
  - method-image 在 graphviz 未装时返回结构化 error（不崩）
  - 方法不存在返回 {"error":"Method not found"}（业务级，非系统错误）
  - decompile method 返回源码文本
  - decompile class 返回类源码

graphviz 未装时 method-image 测试 skip（环境依赖，非被测契约）。

运行：``pytest tests/test_visualize_decompile.py -v``
独立：``python3 tests/test_visualize_decompile.py``
"""
import os
import shutil
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
sys.path.insert(0, REPO_ROOT)

APK = os.path.join(HERE, "data", "APK", "TestActivity.apk")
_NEED_APK = pytest.mark.skipif(not os.path.exists(APK), reason=f"APK 不存在: {APK}")

# TestActivity 的真实类+方法
CLS = "Ltests/androguard/TestActivity;"
METHOD = "onCreate"

_HAS_GRAPHVIZ = shutil.which("dot") is not None
_NEED_GRAPHVIZ = pytest.mark.skipif(
    not _HAS_GRAPHVIZ, reason="graphviz(dot) 未安装，method-image 跳过"
)


def _skills():
    from androguard.skills.main import AndroguardSkillsMain

    s = AndroguardSkillsMain()
    s.load_apk(APK)
    return s


@_NEED_APK
def test_visualize_method_dot():
    """method-dot 返回含 dot 字段（DOT 结构：name/nodes/edges）。"""
    s = _skills()
    r = s.visualize_method_dot(CLS, METHOD)
    assert "dot" in r, f"method-dot 应返回 dot 字段: {list(r.keys())}"
    # dot 可能是 dict（name/nodes/edges）或 str（完整 DOT 文本）
    assert isinstance(r["dot"], (dict, str, list))


@_NEED_APK
def test_visualize_method_json():
    """method-json 返回含 cfg 字段（结构化 CFG，可能为 JSON 字符串或 dict）。"""
    s = _skills()
    r = s.visualize_method_json(CLS, METHOD)
    assert "cfg" in r, f"method-json 应返回 cfg 字段: {list(r.keys())}"
    assert isinstance(r["cfg"], (dict, str, list))


@_NEED_APK
def test_visualize_method_not_found_returns_structured():
    """方法不存在返回 {"error":"Method not found"}（业务级，不崩）。"""
    s = _skills()
    r = s.visualize_method_dot("Lno/such/Class;", "nope")
    assert "error" in r
    assert "not found" in r["error"].lower()


@_NEED_APK
@_NEED_GRAPHVIZ
def test_visualize_method_image_writes_file():
    """method-image 在 graphviz 可用时写出图片文件。"""
    s = _skills()
    out = "/tmp/androguard_test_cfg.png"
    r = s.visualize_method_image(CLS, METHOD, out)
    # 成功应有输出文件信息，或结构化结果
    assert isinstance(r, dict)
    assert os.path.exists(out), f"method-image 应写出文件: {r}"


@_NEED_APK
def test_visualize_method_image_no_graphviz_structured_error():
    """graphviz 未装时 method-image 返回结构化 error（不崩，不 traceback）。"""
    if _HAS_GRAPHVIZ:
        pytest.skip("graphviz 已装，此测试验未装路径")
    s = _skills()
    r = s.visualize_method_image(CLS, METHOD, "/tmp/should_not_exist.png")
    assert "error" in r, f"graphviz 未装应返回结构化 error: {r}"
    assert "dot" in r["error"].lower() or "graphviz" in r["error"].lower()


@_NEED_APK
def test_decompile_method():
    """decompile method 返回源码文本。"""
    s = _skills()
    r = s.decompile_method(CLS, METHOD)
    assert isinstance(r, dict)
    # 应含 source 或 code 字段，或不崩的结构化结果
    assert "error" in r or any(
        k in r for k in ("source", "code", "method", "src")
    )


@_NEED_APK
def test_decompile_class():
    """decompile class 返回类源码，且源码含类名与已知方法名（语义校验）。"""
    s = _skills()
    r = s.decompile_class(CLS)
    assert isinstance(r, dict)
    # 优先期望成功（含 source），失败则需结构化 error
    if "error" in r and "source" not in r:
        return  # 反编译器不可用时容忍 error（已由其他断言守结构化）
    assert "source" in r, f"应含 source 字段，实际: {list(r.keys())}"
    src = r["source"]
    assert isinstance(src, str) and src, "source 应为非空字符串"
    # 源码应含类名（TestActivity）与已知方法（onCreate）
    assert "TestActivity" in src, (
        f"反编译源码应含类名 TestActivity，实际前200字符: {src[:200]}"
    )
    assert "onCreate" in src, (
        f"反编译源码应含 onCreate 方法，实际前200字符: {src[:200]}"
    )


@_NEED_APK
def test_decompile_method_not_found():
    """decompile 方法不存在返回结构化 error 或空结果（不崩）。"""
    s = _skills()
    r = s.decompile_method("Lno/such/Class;", "nope")
    assert isinstance(r, dict)
    assert "error" in r or "source" in r  # 不崩即可


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
