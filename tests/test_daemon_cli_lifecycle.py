#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills daemon CLI 生命周期回归测试

daemon start/stop/status 三个 CLI 命令的完整生命周期通过 subprocess 调真实
androguard-skills CLI 验证。此前无端到端测试（test_daemon_rpc 用 DaemonServer
API 直接启停，不走 CLI 命令路径）。

注意：daemon start 是阻塞的（asyncio.run 不返回），测试用 nohup 后台启。

运行：``pytest tests/test_daemon_cli_lifecycle.py -v``
"""
import json
import os
import subprocess
import sys
import time

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))

DEFAULT_PORT = 8899


def _cli(*args, timeout=30):
    """运行 androguard-skills CLI，返回 (code, stdout, stderr)。"""
    proc = subprocess.run(
        ["androguard-skills", *args],
        capture_output=True, text=True, timeout=timeout, cwd=REPO_ROOT,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _stop_daemon():
    _cli("daemon", "stop", timeout=10)
    time.sleep(0.5)


def test_daemon_status_not_running():
    """无 daemon 时 status 返回 not_running。"""
    _stop_daemon()
    code, out, _ = _cli("daemon", "status")
    assert code == 0
    data = json.loads(out)
    assert data["status"] == "not_running"


def test_daemon_full_lifecycle():
    """daemon start → status(running) → stop → status(not_running) 完整生命周期。"""
    _stop_daemon()
    try:
        # 后台启动 daemon（start 阻塞，用 nohup）
        with open("/tmp/androguard_daemon_start.log", "w") as log:
            proc = subprocess.Popen(
                ["androguard-skills", "daemon", "start"],
                stdout=log, stderr=log, cwd=REPO_ROOT,
            )
        # 等待启动
        deadline = time.time() + 15
        started = False
        while time.time() < deadline:
            code, out, _ = _cli("daemon", "status")
            if code == 0:
                try:
                    if json.loads(out)["status"] == "running":
                        started = True
                        break
                except Exception:
                    pass
            time.sleep(0.5)
        assert started, "daemon 未在 15s 内启动"

        # status 应含 pid/uptime
        code, out, _ = _cli("daemon", "status")
        data = json.loads(out)
        assert data["status"] == "running"
        assert "pid" in data
        assert "uptime" in data

        # load 一个 APK 验证 daemon 可用
        apk = os.path.join(HERE, "data", "APK", "TestActivity.apk")
        if os.path.exists(apk):
            code, out, _ = _cli("load", apk, timeout=60)
            assert code == 0
            ldata = json.loads(out)
            assert ldata.get("status") == "loaded"

        # stop
        code, out, _ = _cli("daemon", "stop")
        assert code == 0
        assert json.loads(out)["status"] == "stopped"

        # status 应 not_running
        time.sleep(1)
        code, out, _ = _cli("daemon", "status")
        assert json.loads(out)["status"] == "not_running"
    finally:
        _stop_daemon()
        # 确保后台 start 进程已结束
        try:
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=5)
        except Exception:
            pass


def test_daemon_stop_when_not_running():
    """无 daemon 时 stop 返回 not_running（不报错）。"""
    _stop_daemon()
    code, out, _ = _cli("daemon", "stop")
    assert code == 0
    assert json.loads(out)["status"] == "not_running"


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
    _stop_daemon()
    print(f"\n{passed} passed, {failed} failed, {len(fns)} total")
    sys.exit(1 if failed else 0)
