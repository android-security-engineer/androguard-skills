#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills JSON 编码器回归测试

_SkillsJsonEncoder（CLI）和 _DaemonJsonEncoder（daemon）处理 AndroGuard 返回
的不可直接序列化类型。此前未测试，且审查发现两个真实缺口：
  - frozenset 未处理（AndroGuard 权限集合用 frozenset）→ TypeError
  - generator 未处理（惰性迭代）→ TypeError

已修复：两个编码器现处理 set/frozenset/bytes/bytearray/filter/map/zip/range
+ 任意迭代器（hasattr __next__ 兜底）。

本测试验两个编码器对各类型的处理一致且正确，防回退。

运行：``pytest tests/test_json_encoder.py -v``
"""
import json
import os
import sys
from collections import OrderedDict

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
sys.path.insert(0, REPO_ROOT)

from androguard.skills.main import _SkillsJsonEncoder
from androguard.skills.daemon import _DaemonJsonEncoder

ENCODERS = [_SkillsJsonEncoder, _DaemonJsonEncoder]


def _gen():
    """生成器（generator）。"""
    yield 1
    yield 2
    yield 3


@pytest.mark.parametrize("encoder", ENCODERS, ids=["Skills", "Daemon"])
def test_set(encoder):
    assert json.loads(json.dumps({1, 2, 3}, cls=encoder)) == [1, 2, 3]


@pytest.mark.parametrize("encoder", ENCODERS, ids=["Skills", "Daemon"])
def test_frozenset(encoder):
    """frozenset 此前未处理（AndroGuard 权限集合）——防回退。"""
    r = json.loads(json.dumps(frozenset([1, 2, 3]), cls=encoder))
    assert sorted(r) == [1, 2, 3]


@pytest.mark.parametrize("encoder", ENCODERS, ids=["Skills", "Daemon"])
def test_bytes(encoder):
    assert json.loads(json.dumps(b"hello", cls=encoder)) == "68656c6c6f"


@pytest.mark.parametrize("encoder", ENCODERS, ids=["Skills", "Daemon"])
def test_bytearray(encoder):
    r = json.loads(json.dumps(bytearray(b"ab"), cls=encoder))
    assert r == "6162"


@pytest.mark.parametrize("encoder", ENCODERS, ids=["Skills", "Daemon"])
def test_filter_map_zip_range(encoder):
    assert json.loads(json.dumps(filter(lambda x: x > 1, [1, 2, 3]), cls=encoder)) == [2, 3]
    assert json.loads(json.dumps(map(lambda x: x * 2, [1, 2]), cls=encoder)) == [2, 4]
    assert json.loads(json.dumps(zip([1, 2], [3, 4]), cls=encoder)) == [[1, 3], [2, 4]]
    assert json.loads(json.dumps(range(3), cls=encoder)) == [0, 1, 2]


@pytest.mark.parametrize("encoder", ENCODERS, ids=["Skills", "Daemon"])
def test_generator(encoder):
    """generator 此前未处理——防回退。"""
    assert json.loads(json.dumps(_gen(), cls=encoder)) == [1, 2, 3]


@pytest.mark.parametrize("encoder", ENCODERS, ids=["Skills", "Daemon"])
def test_nested_complex(encoder):
    """嵌套复杂结构（dict 含 set/bytes/list）。"""
    data = {
        "perms": {"A", "B"},
        "frozen": frozenset([1, 2]),
        "raw": b"\x00\x01",
        "items": list(range(3)),
    }
    r = json.loads(json.dumps(data, cls=encoder))
    assert sorted(r["perms"]) == ["A", "B"]
    assert sorted(r["frozen"]) == [1, 2]
    assert r["raw"] == "0001"
    assert r["items"] == [0, 1, 2]


@pytest.mark.parametrize("encoder", ENCODERS, ids=["Skills", "Daemon"])
def test_ordereddict_works(encoder):
    """OrderedDict 应原生支持（dict 子类）。"""
    r = json.loads(json.dumps(OrderedDict([("a", 1), ("b", 2)]), cls=encoder))
    assert r == {"a": 1, "b": 2}


@pytest.mark.parametrize("encoder", ENCODERS, ids=["Skills", "Daemon"])
def test_unserializable_raises(encoder):
    """真正不可序列化的对象仍抛 TypeError（不能静默吞）。"""
    class Unknown:
        pass
    with pytest.raises(TypeError):
        json.dumps(Unknown(), cls=encoder)


def test_both_encoders_produce_identical_output():
    """_SkillsJsonEncoder 与 _DaemonJsonEncoder 对所有边缘类型输出必须一致。

    两编码器是独立复制实现（daemon 避免 main 的模块级 import），若改一个
    忘改另一个会漂移——daemon 与单次模式输出就不一致（/goal："对接几十个
    agent"，模式间漂移让 agent 无法稳定对接）。参数化测试隐式保证一致性
    （各自达预期），本测试显式断言两者输出完全相同，更强。
    """
    def _gen():
        yield 1
        yield 2

    # 用工厂列表（每次调用生成新对象），因 generator/filter 等消费后不可复用
    cases = [
        lambda: {1, 2, 3},
        lambda: frozenset([1, 2, 3]),
        lambda: b"hello",
        lambda: bytearray(b"ab"),
        lambda: filter(lambda x: x > 1, [1, 2, 3]),
        lambda: map(lambda x: x * 2, [1, 2]),
        lambda: zip([1, 2], [3, 4]),
        lambda: range(3),
        lambda: _gen(),
        lambda: {"perms": {"A", "B"}, "frozen": frozenset([1, 2]),
                 "raw": b"\x00\x01", "items": list(range(3))},
        lambda: OrderedDict([("a", 1), ("b", 2)]),
    ]
    for i, factory in enumerate(cases):
        # 每次新对象，避免消费型迭代器复用问题
        s = json.dumps(factory(), cls=_SkillsJsonEncoder)
        d = json.dumps(factory(), cls=_DaemonJsonEncoder)
        assert json.loads(s) == json.loads(d), (
            f"case {i} 两编码器输出不一致: Skills={s!r} Daemon={d!r}"
        )


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    passed = failed = 0
    for fn in fns:
        try:
            # 参数化手动展开
            for enc in ENCODERS:
                fn(enc)
            print(f"  PASS  {fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {fn.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed, {len(fns)} total")
    sys.exit(1 if failed else 0)
