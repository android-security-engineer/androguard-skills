#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills main.py 纯辅助函数单元测试

此前无测试固化的纯辅助函数：
  - _parse_filter_pairs: manifest 属性过滤 "key=value" 解析
  - _parse_resource_id:  资源 ID 字符串（0x7f020000 或十进制）→ 整型
  - _output_json:        结构化 JSON 输出（含 _SkillsJsonEncoder 调用链）
  - _apk_loader / _dex_loader / _analysis_class_loader: 加载器复用逻辑
    （未加载 + 无 path → 输出 error + 返回 None；已加载 → 直接复用）

这些函数此前靠 CLI 集成测试间接覆盖，但无单元级边缘用例固化。
Click multiple option 返回 tuple，故 _parse_filter_pairs 必须接受 tuple/list/None。

运行：``pytest tests/test_helpers_unit.py -v``
独立：``python3 tests/test_helpers_unit.py``
"""
import io
import json
import os
import sys
from contextlib import redirect_stdout
from unittest.mock import patch

import click
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
sys.path.insert(0, REPO_ROOT)

from androguard.skills.main import (
    _parse_filter_pairs,
    _parse_resource_id,
    _output_json,
    _apk_loader,
    _dex_loader,
    _analysis_class_loader,
    _get_skills,
    _SkillsJsonEncoder,
)


# --------------------------------------------------------------------
# _parse_filter_pairs
# --------------------------------------------------------------------


class TestParseFilterPairs:
    def test_none_returns_empty(self):
        assert _parse_filter_pairs(None) == {}

    def test_empty_tuple_returns_empty(self):
        assert _parse_filter_pairs(()) == {}

    def test_single_pair(self):
        assert _parse_filter_pairs(("name=foo",)) == {"name": "foo"}

    def test_multiple_pairs(self):
        result = _parse_filter_pairs(("name=foo", "type=bar"))
        assert result == {"name": "foo", "type": "bar"}

    def test_value_contains_equals_sign(self):
        """值中含 = 应按 split("=",1) 只切第一个。"""
        assert _parse_filter_pairs(("expr=a=b=c",)) == {"expr": "a=b=c"}

    def test_whitespace_stripped(self):
        """键值两端空白被 strip。"""
        result = _parse_filter_pairs(("  name  =  foo  ",))
        assert result == {"name": "foo"}

    def test_pair_without_equals_skipped(self):
        """无 = 的项被静默跳过（不抛异常）。"""
        result = _parse_filter_pairs(("name=foo", "invalid", "type=bar"))
        assert result == {"name": "foo", "type": "bar"}

    def test_list_input_accepted(self):
        """Click multiple 返回 tuple，但 list 也应可用。"""
        assert _parse_filter_pairs(["a=1", "b=2"]) == {"a": "1", "b": "2"}

    def test_empty_string_pair_skipped(self):
        """空字符串项被跳过（无 =）。"""
        result = _parse_filter_pairs(("", "name=foo"))
        assert result == {"name": "foo"}

    def test_empty_value_allowed(self):
        """key=（空值）仍写入字典。"""
        assert _parse_filter_pairs(("name=",)) == {"name": ""}

    def test_last_value_wins_on_duplicate_key(self):
        """重复键后者覆盖前者（字典语义）。"""
        result = _parse_filter_pairs(("name=foo", "name=bar"))
        assert result == {"name": "bar"}


# --------------------------------------------------------------------
# _parse_resource_id
# --------------------------------------------------------------------


class TestParseResourceId:
    def test_hex_with_0x_prefix(self):
        assert _parse_resource_id("0x7f020000") == 0x7F020000

    def test_hex_uppercase_0x_prefix(self):
        assert _parse_resource_id("0X7F020000") == 0x7F020000

    def test_decimal_string(self):
        assert _parse_resource_id("2130706432") == 2130706432

    def test_decimal_equals_hex_value(self):
        """0x7f020000 的十进制 == 2130837504（注意：非 2130706432，那是 0x7f014e00）。"""
        assert _parse_resource_id("0x7f020000") == 0x7F020000
        assert _parse_resource_id("0x7f020000") == _parse_resource_id("2130837504")
        assert _parse_resource_id("0x7f020000") != _parse_resource_id("2130706432")

    def test_integer_input(self):
        """整型输入直接转 int。"""
        assert _parse_resource_id(2130706432) == 2130706432

    def test_none_returns_none(self):
        assert _parse_resource_id(None) is None

    def test_whitespace_stripped(self):
        assert _parse_resource_id("  0x7f020000  ") == 0x7F020000

    def test_invalid_raises_bad_parameter(self):
        """非法值抛 click.BadParameter（CLI 友好错误）。"""
        with pytest.raises(click.BadParameter):
            _parse_resource_id("not-a-number")

    def test_invalid_hex_raises_bad_parameter(self):
        """0x 后跟非十六进制抛 BadParameter。"""
        with pytest.raises(click.BadParameter):
            _parse_resource_id("0xZZZZ")

    def test_empty_string_raises_bad_parameter(self):
        with pytest.raises(click.BadParameter):
            _parse_resource_id("")

    def test_small_hex_id(self):
        assert _parse_resource_id("0x1") == 1


# --------------------------------------------------------------------
# _output_json + _SkillsJsonEncoder 链路
# --------------------------------------------------------------------


class TestOutputJson:
    def test_simple_dict(self, capsys):
        _output_json({"status": "ok"})
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data == {"status": "ok"}

    def test_unicode_not_escaped(self, capsys):
        """ensure_ascii=False → 中文原样输出。"""
        _output_json({"msg": "测试"})
        out = capsys.readouterr().out
        assert "测试" in out
        assert json.loads(out) == {"msg": "测试"}

    def test_pretty_indented(self, capsys):
        """indent=2 → 多行输出。"""
        _output_json({"a": 1})
        out = capsys.readouterr().out
        assert '\n  "a"' in out

    def test_encoder_handles_set(self, capsys):
        _output_json({"perms": {"A", "B"}})
        out = capsys.readouterr().out
        data = json.loads(out)
        assert sorted(data["perms"]) == ["A", "B"]

    def test_encoder_handles_frozenset(self, capsys):
        _output_json({"perms": frozenset({"X", "Y"})})
        data = json.loads(capsys.readouterr().out)
        assert sorted(data["perms"]) == ["X", "Y"]

    def test_encoder_handles_bytes_as_hex(self, capsys):
        _output_json({"data": b"\x00\xff"})
        data = json.loads(capsys.readouterr().out)
        assert data["data"] == "00ff"

    def test_encoder_handles_generator(self, capsys):
        _output_json({"items": (x for x in range(3))})
        data = json.loads(capsys.readouterr().out)
        assert data["items"] == [0, 1, 2]

    def test_encoder_handles_filter(self, capsys):
        _output_json({"items": filter(lambda x: x > 1, [1, 2, 3])})
        data = json.loads(capsys.readouterr().out)
        assert data["items"] == [2, 3]

    def test_encoder_handles_map(self, capsys):
        _output_json({"items": map(lambda x: x * 2, [1, 2])})
        data = json.loads(capsys.readouterr().out)
        assert data["items"] == [2, 4]


# --------------------------------------------------------------------
# 加载器复用逻辑（_apk_loader / _dex_loader / _analysis_class_loader）
# 不实际加载 APK，只验证 "未加载 + 无 path → error + None" 路径与已加载复用。
# --------------------------------------------------------------------


class TestLoadersNoPathNoLoad:
    """三个加载器在未加载且无 path 时应输出 error JSON 并返回 None。"""

    def setup_method(self):
        # 重置全局单例，确保 is_loaded 为 False
        import androguard.skills.main as m
        m._skills_instance = None

    def test_apk_loader_no_path_no_load(self, capsys):
        result = _apk_loader(None)
        assert result is None
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "error" in data
        assert "No APK loaded" in data["error"]

    def test_apk_loader_empty_path_no_load(self, capsys):
        result = _apk_loader("")
        assert result is None

    def test_dex_loader_no_path_no_load(self, capsys):
        result = _dex_loader(None)
        assert result is None
        out = capsys.readouterr().out
        assert "error" in json.loads(out)

    def test_analysis_class_loader_no_path_no_load(self, capsys):
        result = _analysis_class_loader("Lsome/Class;", None)
        assert result is None
        out = capsys.readouterr().out
        assert "error" in json.loads(out)


class TestLoadersReuseWhenLoaded:
    """已加载时加载器应直接复用单例，不重新加载、不输出 error。"""

    def setup_method(self):
        import androguard.skills.main as m
        m._skills_instance = None

    def test_apk_loader_reuses_loaded_instance(self, capsys):
        skills = _get_skills()
        # 模拟已加载
        with patch.object(type(skills), "is_loaded", new=True):
            result = _apk_loader(None)
        assert result is skills
        assert capsys.readouterr().out == ""

    def test_apk_loader_reuses_even_with_path_when_loaded(self, capsys):
        """已加载时即使给了 path 也不重新加载（复用语义）。"""
        skills = _get_skills()
        with patch.object(type(skills), "is_loaded", new=True):
            with patch.object(skills, "load_apk") as mock_load:
                result = _apk_loader("/some/path.apk")
                mock_load.assert_not_called()
        assert result is skills

    def test_analysis_class_loader_reuses_when_loaded(self, capsys):
        skills = _get_skills()
        with patch.object(type(skills), "is_loaded", new=True):
            result = _analysis_class_loader("Lsome/Class;", None)
        assert result is skills
        assert capsys.readouterr().out == ""


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
