#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills 业务模块内部辅助函数单元测试

业务模块（apk_skills/dex_skills/analysis_skills/resource_skills）的公开
函数已通过 CLI 功能测试间接覆盖，但一批 _ 前缀的纯数据转换辅助函数无
单元级边缘用例固化。这些函数处理底层 AndroGuard 对象，边缘输入（None/
异常对象/空值）容易出错。本测试直接对辅助函数做边缘用例测试。

覆盖：
  - analysis_skills._normalize_descriptor：描述符归一化（去空格）
  - dex_skills._encode_value_to_python：EncodedValue 递归转 Python
  - dex_skills._item_info：DEX item 通用信息提取（duck-typing）
  - apk_skills._parse_certificate：asn1crypto 证书解析（用真实自签证书）

运行：``pytest tests/test_skills_helpers_unit.py -v``
独立：``python3 tests/test_skills_helpers_unit.py``
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
sys.path.insert(0, REPO_ROOT)

from androguard.skills.analysis_skills import _normalize_descriptor
from androguard.skills.dex_skills import _encode_value_to_python, _item_info
from androguard.skills.apk_skills import _parse_certificate


# --------------------------------------------------------------------
# _normalize_descriptor
# --------------------------------------------------------------------


class TestNormalizeDescriptor:
    def test_removes_spaces_inside_parens(self):
        d = "(Landroid/content/Context; Ljava/lang/String;)V"
        assert _normalize_descriptor(d) == (
            "(Landroid/content/Context;Ljava/lang/String;)V"
        )

    def test_no_spaces_unchanged(self):
        d = "(Ljava/lang/String;)V"
        assert _normalize_descriptor(d) == "(Ljava/lang/String;)V"

    def test_empty_string_returns_empty(self):
        assert _normalize_descriptor("") == ""

    def test_none_returns_none(self):
        assert _normalize_descriptor(None) is None

    def test_all_spaces_removed(self):
        assert _normalize_descriptor("  (  )  V  ") == "()V"

    def test_no_parens_descriptor(self):
        """无括号的字符串也去空格（函数不区分括号内外）。"""
        assert _normalize_descriptor("V") == "V"


# --------------------------------------------------------------------
# _encode_value_to_python
# --------------------------------------------------------------------


class _MockEncodedValue:
    """模拟 AndroGuard EncodedValue 的 duck-type mock。"""

    def __init__(self, value, raise_exc=None):
        self._value = value
        self._raise = raise_exc

    def get_value(self):
        if self._raise:
            raise self._raise
        return self._value


class TestEncodeValueToPython:
    def test_none_returns_none(self):
        assert _encode_value_to_python(None) is None

    def test_int_value(self):
        ev = _MockEncodedValue(42)
        assert _encode_value_to_python(ev) == 42

    def test_str_value(self):
        ev = _MockEncodedValue("hello")
        assert _encode_value_to_python(ev) == "hello"

    def test_bool_value(self):
        ev = _MockEncodedValue(True)
        assert _encode_value_to_python(ev) is True

    def test_float_value(self):
        ev = _MockEncodedValue(3.14)
        assert _encode_value_to_python(ev) == 3.14

    def test_bytes_value(self):
        ev = _MockEncodedValue(b"\x00\xff")
        result = _encode_value_to_python(ev)
        assert result == {"bytes_hex": "00ff"}

    def test_get_value_raises_returns_error_dict(self):
        ev = _MockEncodedValue(None, raise_exc=RuntimeError("boom"))
        result = _encode_value_to_python(ev)
        assert isinstance(result, dict)
        assert "encode_error" in result
        assert "boom" in result["encode_error"]

    def test_nested_encoded_value(self):
        """get_value 返回另一个带 get_value 的对象 → 递归。"""
        inner = _MockEncodedValue("nested")
        outer = _MockEncodedValue(inner)
        assert _encode_value_to_python(outer) == "nested"

    def test_list_of_encoded_values(self):
        """get_value 返回可迭代对象 → 逐项递归。"""
        items = [_MockEncodedValue(1), _MockEncodedValue(2)]
        ev = _MockEncodedValue(items)
        assert _encode_value_to_python(ev) == [1, 2]

    def test_list_of_plain_objects(self):
        """可迭代对象里无 get_value 的项 → str(it)。"""
        ev = _MockEncodedValue([1, 2, 3])
        assert _encode_value_to_python(ev) == ["1", "2", "3"]

    def test_bytes_truncated_to_200_hex_chars(self):
        """bytes_hex 截断到 200 字符。"""
        ev = _MockEncodedValue(b"\x00" * 200)
        result = _encode_value_to_python(ev)
        assert len(result["bytes_hex"]) == 200


# --------------------------------------------------------------------
# _item_info
# --------------------------------------------------------------------


class _MockItem:
    """模拟 DEX item 的 duck-type mock。"""

    def __init__(self, off=None, length=None, raw=None, raise_off=None):
        self._off = off
        self._length = length
        self._raw = raw
        self._raise_off = raise_off

    def get_off(self):
        if self._raise_off:
            raise self._raise_off
        return self._off

    def get_length(self):
        return self._length

    def get_raw(self):
        return self._raw


class TestItemInfo:
    def test_full_item(self):
        item = _MockItem(off=100, length=50, raw=b"\x00" * 50)
        info = _item_info(item)
        assert info["type"] == "_MockItem"
        assert info["off"] == 100
        assert info["length"] == 50
        assert info["raw_size"] == 50

    def test_minimal_item_no_raw(self):
        item = _MockItem(off=0, length=10)
        info = _item_info(item)
        assert info["off"] == 0
        assert info["length"] == 10
        assert "raw_size" not in info

    def test_item_with_only_type(self):
        """无任何 get_* 方法的对象 → 只返回 type。"""

        class Bare:
            pass

        info = _item_info(Bare())
        assert info == {"type": "Bare"}

    def test_get_off_raises(self):
        item = _MockItem(off=0, raise_off=RuntimeError("offset error"))
        info = _item_info(item)
        assert "error" in info["off"]
        assert "offset error" in info["off"]

    def test_get_raw_not_bytes(self):
        """get_raw 返回非 bytes → 不设 raw_size。"""
        item = _MockItem(off=0, length=1, raw="not bytes")
        info = _item_info(item)
        assert "raw_size" not in info


# --------------------------------------------------------------------
# _parse_certificate
# --------------------------------------------------------------------


def _make_self_signed_cert():
    """生成一个真实自签 X.509 证书用于测试 _parse_certificate。

    用 cryptography 库生成（AndroGuard 已依赖）。若不可用则 skip。
    """
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
        import datetime
    except ImportError:
        pytest.skip("cryptography 不可用")

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.COMMON_NAME, "TestCert"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(12345)
        .not_valid_before(datetime.datetime(2020, 1, 1))
        .not_valid_after(datetime.datetime(2030, 1, 1))
        .sign(key, hashes.SHA256())
    )
    # 转成 asn1crypto.x509.Certificate
    der = cert.public_bytes(serialization.Encoding.DER)
    try:
        from asn1crypto import x509 as asn1_x509
        return asn1_x509.Certificate.load(der)
    except ImportError:
        pytest.skip("asn1crypto 不可用")


class TestParseCertificate:
    def test_real_cert_parsed(self):
        cert = _make_self_signed_cert()
        info = _parse_certificate(cert)
        # 应有哈希字段
        assert "sha1" in info
        assert "sha256" in info
        assert "md5" in info
        assert "size" in info
        assert len(info["sha1"]) == 40  # sha1 hex
        assert len(info["sha256"]) == 64  # sha256 hex
        # 应有证书字段
        assert "issuer" in info
        assert "subject" in info
        assert "serial_number" in info
        assert info["serial_number"] == hex(12345)
        assert "valid_not_before" in info
        assert "valid_not_after" in info

    def test_invalid_cert_returns_error(self):
        """传入无法 dump 的对象 → 返回 {"error": ...}。"""

        class BadCert:
            def dump(self):
                raise RuntimeError("cannot dump")

        info = _parse_certificate(BadCert())
        assert "error" in info
        assert "cannot dump" in info["error"]


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
