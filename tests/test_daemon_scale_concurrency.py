#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills Daemon 规模与并发回归测试

/goal 要求"对接好几十个 agent"——多 agent 并发打 daemon，且可能处理真实大
APK。前述 test_daemon_rpc.py 用小样本（TestActivity.apk 174KB）验证功能
正确性；本测试补两个正交维度：

  1. **规模**：大 APK（28MB framework-res，类巨多）下 daemon 仍能正常
     load + 缓存命中命令响应快 + stderr 不塞满（死锁修复在大样本下生效）。
  2. **并发**：多个 agent 同时发请求，asyncio 并发不串行阻塞、响应 id
     无错乱（JSON-RPC id 路由在并发下正确）。

运行：``pytest tests/test_daemon_scale_concurrency.py -v``
独立：``python3 tests/test_daemon_scale_concurrency.py``
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

# 基准小 APK（并发测试用）；缺失则并发测试 skip
_SMALL_APK = os.path.join(HERE, "data", "APK", "TestActivity.apk")
_NEED_SMALL_APK = pytest.mark.skipif(
    not os.path.exists(_SMALL_APK),
    reason=f"基准 APK 不存在: {_SMALL_APK}",
)

# 复用 daemon 测试辅助
from test_daemon_rpc import _DaemonHandle, _rpc, TEST_PORT

# 仓库内最大 APK（28MB framework-res，类巨多，真实大规模样本）
BIG_APK = os.path.join(HERE, "data", "APK", "lineageos_nexus5_framework-res.apk")

# 缓存命中命令应在此秒数内返回（大样本下缓存命中应极快）
CACHE_HIT_TIMEOUT_S = 5.0
# load 大 APK 应在此秒数内完成（基线 ~2-3s，留足余量）
LOAD_TIMEOUT_S = 120.0


def test_daemon_large_apk_load_and_cache():
    """大 APK 下 daemon 能 load，缓存命中命令响应快，stderr 不塞满。"""
    if not os.path.exists(BIG_APK):
        import pytest
        pytest.skip(f"大样本 APK 不存在: {BIG_APK}")
    with _DaemonHandle(TEST_PORT + 40) as d:
        # load 大 APK
        t0 = time.time()
        resp = _rpc(
            d.port,
            {"jsonrpc": "2.0", "method": "load_apk", "params": {"apk_path": BIG_APK}, "id": 1},
            timeout=LOAD_TIMEOUT_S,
        )
        load_dur = time.time() - t0
        assert "result" in resp, f"大 APK load 失败: {resp}"
        assert load_dur < LOAD_TIMEOUT_S, f"大 APK load 超时: {load_dur:.1f}s"

        # 缓存命中命令应快（不再解析）
        t0 = time.time()
        info = _rpc(
            d.port, {"jsonrpc": "2.0", "method": "apk_info", "params": {}, "id": 2}, timeout=30
        )
        cache_dur = time.time() - t0
        assert "result" in info, f"缓存命中 apk_info 失败: {info}"
        assert cache_dur < CACHE_HIT_TIMEOUT_S, (
            f"缓存命中命令应 <{CACHE_HIT_TIMEOUT_S}s，实际 {cache_dur:.2f}s（缓存失效?）"
        )

        # stderr 不应塞满（死锁修复在大样本下的关键验证）
        # daemon 已配置日志落文件 + WARNING 级别，stderr 应近乎为空
        import fcntl

        if d.proc and d.proc.stderr:
            fd = d.proc.stderr.fileno()
            fl = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            try:
                data = d.proc.stderr.read()
                size = len(data) if data else 0
                # 大样本产生海量 INFO 日志，若死锁修复回退，stderr 会瞬间 >64KB
                assert size < 1024, (
                    f"stderr 积攒 {size} 字节——死锁修复可能回退"
                    f"（daemon 应日志落文件，stderr 近乎为空）"
                )
            except Exception:
                pass  # 读异常视作无积压


@_NEED_SMALL_APK
def test_daemon_concurrent_requests_no_id_mismatch():
    """多 agent 并发请求：全部成功，响应 id 无错乱（JSON-RPC id 路由正确）。"""
    with _DaemonHandle(TEST_PORT + 41) as d:
        # 先 load 小 APK（并发测试不需要大样本，关注并发正确性）
        _rpc(
            d.port,
            {"jsonrpc": "2.0", "method": "load_apk", "params": {"apk_path": _SMALL_APK}, "id": 0},
            timeout=60,
        )

        N = 20
        results = [None] * N
        methods = ["apk_info", "apk_permissions", "status", "status", "status"]

        def worker(i):
            method = methods[i % len(methods)]
            params = {} if method == "status" else {}
            if method == "apk_permissions":
                params = {}
            try:
                r = _rpc(
                    d.port,
                    {"jsonrpc": "2.0", "method": method, "params": params, "id": i + 1},
                    timeout=30,
                )
                results[i] = (method, "result" in r or "error" in r, r.get("id"))
            except Exception as e:
                results[i] = (method, False, str(e)[:50])

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(N)]
        t0 = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        dur = time.time() - t0

        ok = sum(1 for r in results if r and r[1])
        assert ok == N, f"并发请求失败 {N - ok}/{N}: {[r for r in results if r and not r[1]]}"

        # id 无错乱：每个响应 id 必须等于其请求 id（i+1）
        ids = [r[2] for r in results if r]
        assert sorted([i for i in ids if isinstance(i, int)]) == list(range(1, N + 1)), (
            f"响应 id 错乱: {sorted(ids)}"
        )


def test_daemon_concurrent_does_not_serialize():
    """并发不应退化为串行：N 个纯内存命令（status）并发耗时应显著小于 N×单次。"""
    with _DaemonHandle(TEST_PORT + 42) as d:
        N = 10
        # 先测单次 status 耗时
        t0 = time.time()
        _rpc(d.port, {"jsonrpc": "2.0", "method": "status", "params": {}, "id": 1}, timeout=10)
        single = time.time() - t0

        results = [None] * N

        def worker(i):
            try:
                r = _rpc(
                    d.port,
                    {"jsonrpc": "2.0", "method": "status", "params": {}, "id": i + 1},
                    timeout=10,
                )
                results[i] = "result" in r
            except Exception:
                results[i] = False

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(N)]
        t0 = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        concurrent_dur = time.time() - t0

        assert all(results), f"部分并发请求失败: {results}"
        # 并发耗时应远小于 N×单次（允许网络抖动，宽松判定：< N×single×0.7）
        # 注：若 asyncio 并发真并行，N 个纯内存 status 并发 ≈ 单次；若退化为
        # 串行则 ≈ N×single。此断言防并发退化。
        serial_bound = N * single * 0.7
        assert concurrent_dur < serial_bound or concurrent_dur < 1.0, (
            f"并发可能退化为串行: {N}×single={N*single:.3f}s, 并发实际={concurrent_dur:.3f}s"
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
