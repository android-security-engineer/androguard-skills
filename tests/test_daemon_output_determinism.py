#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills Daemon 模式输出确定性回归测试

`test_cli_output_determinism.py` 守护 CLI 单次执行模式的确定性。本测试守护
**daemon 模式**的确定性——agent 对接几十个时常用 daemon（避免重复解析 APK），
daemon 经 `getattr(skills, method)` 动态分发到 skills 方法，与 CLI 走同一
skills 实现，故确定性修复应对两条路径都生效。

本测试在独立高位端口启动 daemon 子进程，``load_apk`` 后对每个命令通过
JSON-RPC 调 3 次，断言结果（sort_keys 序列化后）hash 一致。

与 CLI 确定性测试的区别：
- CLI 测试每命令先 ``daemon stop`` 走单次执行路径
- 本测试常驻 daemon，走 JSON-RPC 分发路径，覆盖 daemon 缓存对象下的确定性

运行：``pytest tests/test_daemon_output_determinism.py -v``
"""
import hashlib
import json
import os
import socket
import subprocess
import sys
import time

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
APK = os.path.join(HERE, "data", "APK", "app-prod-debug.apk")

# 高位端口避免与默认 8899 或其他 daemon 测试冲突
PORT = 28991
STARTUP_TIMEOUT = 15

pytestmark = pytest.mark.skipif(
    not os.path.exists(APK),
    reason=f"复杂基准 APK 不存在: {APK}（确定性需含真实多元素 set 的复杂 APK）",
)

_COMPLEX_CLASS = "Landroid/support/v4/app/JobIntentService;"


def _wait_port_ready(port, timeout=STARTUP_TIMEOUT):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except (ConnectionRefusedError, OSError):
            time.sleep(0.2)
    return False


def _call(port, method, params=None):
    """单次 JSON-RPC 调用，返回 result 字段。"""
    req = (
        json.dumps({"jsonrpc": "2.0", "method": method, "params": params or {}, "id": 1}).encode()
        + b"\n"
    )
    s = socket.create_connection(("127.0.0.1", port), timeout=30)
    try:
        s.sendall(req)
        buf = b""
        while b"\n" not in buf:
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
    finally:
        s.close()
    return json.loads(buf.split(b"\n")[0]).get("result")


@pytest.fixture(scope="module")
def daemon():
    """启动一个 daemon 子进程（独立端口），加载 APK，模块结束后清理。"""
    proc = subprocess.Popen(
        [sys.executable, "-c",
         f"import sys; sys.path.insert(0, '{REPO_ROOT}'); "
         f"from androguard.skills.daemon import DaemonServer; "
         f"d = DaemonServer(port={PORT}); d.start()"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=REPO_ROOT,
    )
    try:
        if not _wait_port_ready(PORT):
            raise RuntimeError(f"daemon 未在端口 {PORT} 就绪")
        # 加载 APK（daemon 缓存解析对象）
        r = _call(PORT, "load_apk", {"apk_path": APK})
        assert r is not None and "error" not in (r or {}), f"load_apk 失败: {r}"
        # 等待解析完成（大 APK 的 create_xref 较慢）
        time.sleep(2)
        yield PORT
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


# 覆盖 CLI 确定性测试里所有本轮修复的命令（daemon 路径同源，应同样确定）
_COMMANDS = [
    ("apk_permissions", {}),
    ("apk_activities", {}),
    ("apk_services", {}),
    ("apk_receivers", {}),
    ("apk_providers", {}),
    ("apk_manifest_attrs", {"tag_name": "uses-permission", "attribute": "name"}),
    ("apk_manifest_tags", {"tag_name": "uses-permission"}),
    ("analysis_method_xrefs", {"class_name": _COMPLEX_CLASS, "method_name": "onCreate"}),
    ("analysis_insecure_storage", {}),
    ("analysis_sql_injection", {}),
    ("analysis_pending_intent", {}),
    ("analysis_webview_security", {}),
    ("analysis_call_graph", {}),
    ("analysis_method_reachable",
     {"class_name": _COMPLEX_CLASS, "method_name": "onCreate", "max_depth": 2}),
    ("analysis_class_fields_xref", {"class_name": _COMPLEX_CLASS}),
    ("analysis_crypto_usage", {}),
    ("analysis_reflection_targets", {}),
]


@pytest.mark.parametrize("method,params", _COMMANDS, ids=[m for m, _ in _COMMANDS])
def test_daemon_output_deterministic(daemon, method, params):
    """daemon 模式下同一命令调 3 次，结果 hash 必须一致。

    daemon 经 getattr 动态分发到 skills 实现，与 CLI 同源。本测试确认
    确定性修复对 daemon 路径也生效（agent 常用 daemon 避免重复解析）。
    """
    port = daemon
    hashes = set()
    for _ in range(3):
        r = _call(port, method, params)
        # sort_keys 序列化：dict key 顺序无关，只比对内容确定性
        # （list 顺序由 skills 层 sort 保证，此处检测 list 顺序也稳定）
        h = hashlib.md5(
            json.dumps(r, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        hashes.add(h)
    assert len(hashes) == 1, (
        f"daemon {method} 输出非确定：3 次 hash 不一致 {hashes}。\n"
        f"daemon 路径与 CLI 同源，若 CLI 确定但 daemon 非确定，可能是 daemon "
        f"缓存了跨调用可变状态。"
    )


if __name__ == "__main__":
    # 独立运行：手动启 daemon 跑全部
    proc = subprocess.Popen(
        [sys.executable, "-c",
         f"import sys; sys.path.insert(0, '{REPO_ROOT}'); "
         f"from androguard.skills.daemon import DaemonServer; "
         f"d = DaemonServer(port={PORT}); d.start()"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=REPO_ROOT,
    )
    passed = failed = 0
    try:
        if not _wait_port_ready(PORT):
            print(f"daemon 未就绪"); sys.exit(1)
        r = _call(PORT, "load_apk", {"apk_path": APK})
        time.sleep(2)
        for method, params in _COMMANDS:
            hashes = set()
            for _ in range(3):
                r = _call(PORT, method, params)
                hashes.add(hashlib.md5(
                    json.dumps(r, sort_keys=True, default=str).encode()).hexdigest())
            if len(hashes) == 1:
                print(f"  PASS  {method}"); passed += 1
            else:
                print(f"  FAIL  {method}: {hashes}"); failed += 1
    finally:
        proc.terminate(); proc.wait(timeout=10)
    print(f"\n{passed} passed, {failed} failed, {len(_COMMANDS)} total")
    sys.exit(1 if failed else 0)
