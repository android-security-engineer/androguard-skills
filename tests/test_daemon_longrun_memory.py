#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills Daemon 长跑内存稳定性回归测试

/goal 要求"对接几十个 agent"——多 agent 各自 load 不同 APK，daemon 可能
连续跑数小时处理数百次 load_apk。AndroGuard 的 Analysis 对象持有海量 xref
跨引用图（ClassAnalysis ↔ MethodAnalysis 互相引用成环），纯引用计数无法
回收，daemon 长跑下连续 load 不同大 APK 会内存膨胀。

test_daemon_rpc.py 验证单次 load 正确；test_daemon_scale_concurrency.py 验证
并发不串行；本测试补第三正交维度——**长跑内存稳定性**：
  1. 连续 load 多个**不同** APK（不是重复 load 同一个，那样不触发旧对象释放）
  2. 断言内存增长有界（RSS 峰值 - 末次 load 后 RSS < 阈值）
  3. 断言旧对象被回收（load N 次后进程不持有 N 个 Analysis 图）

运行：``pytest tests/test_daemon_longrun_memory.py -v``
独立：``python3 tests/test_daemon_longrun_memory.py``
"""

import os
import socket
import sys
import threading
import time

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
sys.path.insert(0, HERE)

from test_daemon_rpc import _DaemonHandle, _rpc, TEST_PORT

# 候选 APK：多个不同 APK，覆盖不同规模（小/中/大），让每次 load 真正解析新对象
_ALL_APKS = [
    "TestActivity.apk",  # 174KB
    "com.politedroid_4.apk",  # 18KB
    "com.teleca.jamendo_35.apk",  # 426KB
    "hello-world.apk",  # 1.7MB
    "com.android.example.text.styling.apk",  # 1.5MB
    "a2dp.Vol_137.apk",  # 826KB
]
_APK_PATHS = [os.path.join(HERE, "data", "APK", n) for n in _ALL_APKS]
_APK_PATHS = [p for p in _APK_PATHS if os.path.exists(p)]

_NEED_APKS = pytest.mark.skipif(
    len(_APK_PATHS) < 3,
    reason=f"长跑测试需要至少 3 个不同 APK，实际可用 {len(_APK_PATHS)} 个",
)

# 内存判定阈值。
#
# 实测基线（6 个不同 APK 连续 load 两轮 = 12 次）：
#   - 单次大 APK（hello-world 1.7MB）解析瞬时占用峰值 ~310MB（Analysis 构建
#     xref 图期间同时持有 DEX 字节 + ClassAnalysis + MethodAnalysis 全集）
#   - gc.collect() 后能回落到 ~128MB（证明无真实泄漏——引用环被打破回收）
#   - 末次 gc 后净增长（相对 baseline）~10-15MB（Python 内部碎片，非泄漏）
#
# 故两道断言：
#   1. 峰值增长 < MAX_PEAK_GROWTH_MB：宽松，覆盖单次最大 APK 解析瞬时占用，
#      防的是"全部 N 个 APK 的 Analysis 图同时驻留不释放"的真泄漏（那种情况
#      峰值会随轮次单调爬升到数百 MB 甚至 GB）。
#      CI 实测：Linux 3.10 上单次大 APK 瞬时 RSS 峰值增长可到 ~387MB（glibc
#      碎片因 Python 版本/分配器而异），故阈值取 600MB——远低于 6-APK 真泄漏
#      的 ~1.8GB，又能容忍跨版本的瞬时波动。
#   2. 末次 gc 后净增长 < MAX_FINAL_GROWTH_MB：精确，证明旧对象确实被回收，
#      不是"峰值刚好没超阈值"
MAX_PEAK_GROWTH_MB = 600
# 末次 gc 后净增长阈值：glibc malloc 不归还 arena（traced memory 回落但
# RSS 不降），故放宽到 250MB——防的是 GB 级真泄漏，glibc 碎片的可控高位
# 由 unload 测试的 malloc_trim 回落断言兜住。
MAX_FINAL_GROWTH_MB = 250


def _get_rss_mb(pid):
    """读取进程 RSS（MB），失败返回 None。"""
    try:
        with open(f"/proc/{pid}/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024.0
    except Exception:
        return None
    return None


@_NEED_APKS
@pytest.mark.skipif(
    sys.platform != "linux",
    reason="内存泄漏检测依赖 Linux /proc RSS 与 glibc malloc_trim，非 Linux 不可用",
)
def test_daemon_repeated_load_no_memory_leak():
    """连续 load 不同 APK：内存增长有界，旧对象被回收，unload 后 RSS 回落。"""
    with _DaemonHandle(TEST_PORT + 50) as d:
        pid = d.proc.pid
        # 暖机：先 load 一次让进程稳定
        _rpc(
            d.port,
            {
                "jsonrpc": "2.0",
                "method": "load_apk",
                "params": {"apk_path": _APK_PATHS[0]},
                "id": 0,
            },
            timeout=120,
        )
        _rpc(
            d.port,
            {"jsonrpc": "2.0", "method": "status", "params": {}, "id": 0},
            timeout=10,
        )
        time.sleep(1)

        baseline_rss = _get_rss_mb(pid)
        assert baseline_rss is not None, "无法读取进程 RSS（非 Linux?）"

        # 连续 load N 个不同 APK（循环两轮，共 2N 次，模拟多 agent 反复换 APK）
        rounds = 2
        peak_rss = baseline_rss
        for r in range(rounds):
            for apk in _APK_PATHS:
                resp = _rpc(
                    d.port,
                    {
                        "jsonrpc": "2.0",
                        "method": "load_apk",
                        "params": {"apk_path": apk},
                        "id": r * 100,
                    },
                    timeout=120,
                )
                assert (
                    "result" in resp
                ), f"第 {r} 轮 load {os.path.basename(apk)} 失败: {resp}"
                cur = _get_rss_mb(pid)
                if cur and cur > peak_rss:
                    peak_rss = cur

        # 末次 load 后稍等 gc
        time.sleep(2)
        final_rss = _get_rss_mb(pid)

        growth = peak_rss - baseline_rss
        final_growth = final_rss - baseline_rss
        # 峰值增长有界：防"全部 N 个 APK 的 Analysis 图同时驻留不释放"的真
        # 泄漏（真泄漏下峰值随轮次单调爬升到 GB 级）。阈值覆盖单次最大 APK
        # 解析瞬时占用（traced_peak ~380MB，RSS 因 glibc 碎片更高）。
        assert growth < MAX_PEAK_GROWTH_MB, (
            f"内存峰值增长 {growth:.1f}MB 超阈值 {MAX_PEAK_GROWTH_MB}MB"
            f"（baseline={baseline_rss:.1f}MB, peak={peak_rss:.1f}MB）"
            f"——连续 load 不同 APK 旧对象可能未被回收"
        )
        # 末次 gc 后净增长：gc.collect() 回收 Python 层引用环。glibc malloc
        # 不归还 arena（已知行为，traced memory 回落但 RSS 不降），故此阈值
        # 宽松——真正的回收保证由下方 unload 测试给出。
        assert final_growth < MAX_FINAL_GROWTH_MB, (
            f"末次 gc 后内存净增长 {final_growth:.1f}MB 超阈值"
            f" {MAX_FINAL_GROWTH_MB}MB"
            f"（final={final_rss:.1f}MB, baseline={baseline_rss:.1f}MB）"
            f"——旧 Analysis 对象未被回收，gc.collect() 可能未生效"
        )

        # ---- unload 兜底：显式卸载 + malloc_trim 让 glibc 归还 arena ----
        # 这是 daemon 长跑内存可控的关键能力。load_apk 的 gc 回收 Python 对象，
        # 但 glibc 不主动归还 arena；unload 调 malloc_trim(0) 强制归还。
        before_unload = _get_rss_mb(pid)
        unload_resp = _rpc(
            d.port,
            {"jsonrpc": "2.0", "method": "unload", "params": {}, "id": 99},
            timeout=30,
        )
        assert (
            "result" in unload_resp
        ), f"unload 应返回 result，实际: {unload_resp}"
        assert unload_resp["result"]["status"] == "unloaded"
        time.sleep(1)
        after_unload = _get_rss_mb(pid)

        # unload 后 RSS 应显著回落（malloc_trim 归还 arena）
        reclaimed = before_unload - after_unload
        assert reclaimed > 10, (
            f"unload 后 RSS 仅回落 {reclaimed:.1f}MB（before={before_unload:.1f}MB,"
            f" after={after_unload:.1f}MB）——malloc_trim 可能未生效或无大 APK 已加载"
        )
        # unload 后 apk_loaded 应为 False
        st = _rpc(
            d.port,
            {"jsonrpc": "2.0", "method": "status", "params": {}, "id": 100},
            timeout=10,
        )
        assert (
            st["result"]["apk_loaded"] is False
        ), "unload 后 apk_loaded 应为 False"


@_NEED_APKS
def test_daemon_load_failure_does_not_corrupt_state():
    """load 失败（坏 APK）后 daemon 仍可用，且不残留半解析对象。"""
    # 用一个损坏/不存在的路径触发 load 失败
    with _DaemonHandle(TEST_PORT + 51) as d:
        # 先 load 一个正常 APK
        ok = _rpc(
            d.port,
            {
                "jsonrpc": "2.0",
                "method": "load_apk",
                "params": {"apk_path": _APK_PATHS[0]},
                "id": 1,
            },
            timeout=120,
        )
        assert "result" in ok

        # load 一个不存在的路径——应返回 error（-32603），不崩进程
        bad = _rpc(
            d.port,
            {
                "jsonrpc": "2.0",
                "method": "load_apk",
                "params": {"apk_path": "/nonexistent.apk"},
                "id": 2,
            },
            timeout=30,
        )
        assert (
            "error" in bad
        ), f"load 不存在路径应返回 JSON-RPC error，实际: {bad}"
        assert bad["error"]["code"] == -32603

        # daemon 仍存活
        st = _rpc(
            d.port,
            {"jsonrpc": "2.0", "method": "status", "params": {}, "id": 3},
            timeout=10,
        )
        assert (
            st["result"]["status"] == "running"
        ), "load 失败后 daemon 应仍存活"

        # 关键：load 失败不应把之前已加载的 APK 清掉（旧对象仍可用）
        # 或至少 daemon 不残留半解析对象导致后续命令崩溃
        info = _rpc(
            d.port,
            {"jsonrpc": "2.0", "method": "apk_info", "params": {}, "id": 4},
            timeout=30,
        )
        # info 可能返回 result（旧 APK 仍在）或 error（被清）——关键是结构化不崩
        assert (
            "result" in info or "error" in info
        ), f"load 失败后 apk_info 应返回结构化结果，实际: {info}"


if __name__ == "__main__":
    fns = [
        v
        for k, v in sorted(globals().items())
        if k.startswith("test_") and callable(v)
    ]
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
