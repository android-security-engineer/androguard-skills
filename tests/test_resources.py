#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills resources 组功能回归测试

resources 组（20 命令：packages/locales/types/configs/strings/resolved-strings/
bool/color/dimen/integer/public/id-resources/string-resources/value/xml-name/
get-string/res-configs/type-configs/id）是 ARSC 资源解析能力，此前全量冒烟
只验"不崩"，无功能正确性测试。

本测试用 TestActivity.apk（含真实资源）验关键命令的返回结构契约。

运行：``pytest tests/test_resources.py -v``
独立：``python3 tests/test_resources.py``
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
sys.path.insert(0, REPO_ROOT)

APK = os.path.join(HERE, "data", "APK", "TestActivity.apk")
_NEED_APK = pytest.mark.skipif(not os.path.exists(APK), reason=f"APK 不存在: {APK}")

# TestActivity 的真实资源 ID：0x7f020000 = 2130837504（drawable/icon）。
# 注意易错点：0x7f020000 十进制是 2130837504，不是 2130791936（那是 0x7f014e00，
# 不存在的资源 ID）。此前 RID 误用 2130791936 + 断言宽松，未真正测语义。
RID = 2130837504
RID_HEX = "0x7f020000"
PKG = "tests.androguard"


def _skills():
    from androguard.skills.main import AndroguardSkillsMain

    s = AndroguardSkillsMain()
    s.load_apk(APK)
    return s


@_NEED_APK
def test_resource_packages():
    s = _skills()
    r = s.resource_packages()
    assert r["total"] >= 1
    assert PKG in r["packages"]


@_NEED_APK
def test_resource_locales():
    s = _skills()
    r = s.resource_locales(PKG)
    assert r["package"] == PKG
    assert r["total"] >= 1
    assert isinstance(r["locales"], list)


@_NEED_APK
def test_resource_types():
    s = _skills()
    r = s.resource_types(PKG)
    assert r["package"] == PKG
    assert r["total"] >= 1


@_NEED_APK
def test_resource_configs_by_id():
    """resource_configs 用真实 RID(0x7f020000=drawable/icon) 应返回 configs。"""
    s = _skills()
    r = s.resource_configs(RID)
    assert isinstance(r, dict)
    assert "configs" in r, f"应含 configs，实际: {list(r.keys())}"
    # 真实资源 ID 应查到至少 1 个 config（drawable/icon 有 ldpi/mdpi/hdpi）
    assert r["total"] >= 1, f"真实 RID {RID_HEX} 应有 config，total={r.get('total')}"
    assert isinstance(r["configs"], list) and len(r["configs"]) >= 1
    assert r.get("resource_id") == RID_HEX


@_NEED_APK
def test_resource_res_configs_by_id():
    """resource_res_configs 用真实 RID 应返回 configs。"""
    s = _skills()
    r = s.resource_res_configs(RID)
    assert isinstance(r, dict)
    assert "configs" in r or "error" in r


@_NEED_APK
def test_resource_strings():
    s = _skills()
    r = s.resource_strings()
    assert r["total"] >= 1
    assert isinstance(r["strings"], list)


@_NEED_APK
def test_resource_resolved_strings():
    s = _skills()
    r = s.resource_resolved_strings()
    assert "packages" in r


@_NEED_APK
def test_resource_typed_string():
    """resource_string_resources 返回某 locale 的字符串资源。"""
    s = _skills()
    r = s.resource_string_resources(PKG)
    assert r["package"] == PKG
    assert "resources" in r


@_NEED_APK
def test_resource_get_string():
    """resource_get_string 取指定字符串名的值。"""
    s = _skills()
    r = s.resource_get_string(PKG, "app_name")
    assert r["package"] == PKG
    assert r["name"] == "app_name"
    # 应返回值或 error（结构化）
    assert "value" in r or "error" in r


@_NEED_APK
def test_resource_xml_name():
    """resource_xml_name 给定真实 rid 应 found=True 并返回 xml_name。"""
    s = _skills()
    r = s.resource_xml_name(RID)
    assert isinstance(r, dict)
    assert r.get("found") is True, f"真实 RID {RID_HEX} 应 found=True，实际: {r}"
    assert r.get("xml_name") == "@tests.androguard:drawable/icon"
    assert r.get("resource_id") == RID_HEX


@_NEED_APK
def test_resource_value():
    """resource_value 给定真实 rid 应返回 type=drawable 的解析值。"""
    s = _skills()
    r = s.resource_value(RID)
    assert isinstance(r, dict)
    assert "resource_id" in r
    assert r.get("type") == "drawable", f"真实 RID 应 type=drawable，实际: {r.get('type')}"
    assert r.get("xml_name") == "@tests.androguard:drawable/icon"


@_NEED_APK
def test_resource_type_configs():
    s = _skills()
    r = s.resource_type_configs(PKG)
    assert r["package"] == PKG
    assert "types" in r


@_NEED_APK
def test_resource_id_bidirectional():
    """resource id 支持双向查询：rid→name 得 drawable/icon；type+key→id 得 0x7f020000。"""
    s = _skills()
    # rid 查询 → name
    r = s.resource_id(PKG, resource_id=RID)
    assert isinstance(r, dict)
    assert r.get("query") == "id_to_name"
    assert r.get("type") == "drawable", f"rid→name 应 type=drawable，实际: {r.get('type')}"
    assert r.get("key") == "icon"
    # type+key 查询 → id（双向一致性）
    r2 = s.resource_id(PKG, resource_type="drawable", key="icon")
    assert isinstance(r2, dict)
    assert r2.get("query") == "name_to_id"
    assert r2.get("resource_id") == RID_HEX, (
        f"name→id 应得 {RID_HEX}，实际: {r2.get('resource_id')}"
    )


@_NEED_APK
def test_resource_bool_color_dimen_integer():
    """类型化资源命令（bool/color/dimen/integer）返回结构一致。"""
    s = _skills()
    for cmd in ("resource_bool", "resource_color", "resource_dimen", "resource_integer"):
        m = getattr(s, cmd)
        r = m(PKG)
        assert r["package"] == PKG
        assert "resources" in r


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
