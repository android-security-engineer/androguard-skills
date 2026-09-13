#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills daemon SIGTERM graceful shutdown 回归测试

此前 daemon 只 except KeyboardInterrupt 捕获 SIGINT，但 `kill <pid>` 默认发
SIGTERM——SIGTERM 不触发 KeyboardInterrupt，进程被直接终止，_cleanup 不执行，
残留 PID 文件让下次 start 报 "already running"（虽 _is_daemon_running 的端口
探测兜底会清理，但仍是不干净的退出）。

已修复：_run_server 注册 SIGTERM/SIGINT 信号处理器，收到信号时设
_running=False → 事件循环优雅退出 → start() finally 触发 _cleanup 清理
PID/端口文件。

本测试启真实 daemon，发 SIGTERM，确认：
  1. daemon 进程在 SIGTERM 后退出
  2. PID 文件被 _cleanup 清理（不存在）
  3. 端口文件被清理

运行：``pytest tests/test_daemon_sigterm.py -v``
独立：``python3 tests/test_daemon_sigterm.py``
"""
import json
import os
import signal
import subprocess
import sys
import time

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))

from androguard.skills.daemon import PID_FILE, PORT_FILE


def _cli(*args, timeout=30):
    proc = subprocess.run(
        ["androguard-skills", *args],
        capture_output=True, text=True, timeout=timeout, cwd=REPO_ROOT,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _cleanup_files():
    for f in (PID_FILE, PORT_FILE):
        try:
            os.remove(f)
        except FileNotFoundError:
            pass


def _wait_running(timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        code, out, _ = _cli("daemon", "status")
        if code == 0:
            try:
                if json.loads(out)["status"] == "running":
                    return True
            except Exception:
                pass
        time.sleep(0.5)
    return False


@pytest.mark.skipif(sys.platform == "win32",
                    reason="SIGTERM 信号处理仅 Unix")
def test_sigterm_cleans_pid_file():
    """SIGTERM 后 PID/端口文件被 _cleanup 清理。"""
    _cleanup_files()
    try:
        # 后台启动 daemon
        with open("/tmp/androguard_daemon_sigterm.log", "w") as log:
            proc = subprocess.Popen(
                ["androguard-skills", "daemon", "start"],
                stdout=log, stderr=log, cwd=REPO_ROOT,
            )
        assert _wait_running(15), "daemon 未在 15s 内启动"

        # 确认 PID 文件存在
        assert os.path.exists(PID_FILE), "PID 文件应在 daemon 运行时存在"
        with open(PID_FILE) as f:
            pid = int(f.read().strip())

        # 发 SIGTERM
        os.kill(pid, signal.SIGTERM)

        # 等待进程退出
        deadline = time.time() + 10
        exited = False
        while time.time() < deadline:
            if proc.poll() is not None:
                exited = True
                break
            time.sleep(0.3)
        assert exited, "daemon 进程应在 SIGTERM 后 10s 内退出"

        # 给 _cleanup 一点时间（finally 块）
        time.sleep(1)

        # PID 文件应被清理
        assert not os.path.exists(PID_FILE), (
            "SIGTERM 后 PID 文件应被 _cleanup 清理（graceful shutdown）"
        )
        assert not os.path.exists(PORT_FILE), (
            "SIGTERM 后 端口文件应被 _cleanup 清理"
        )
    finally:
        _cleanup_files()
        try:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)
        except Exception:
            pass


@pytest.mark.skipif(sys.platform == "win32",
                    reason="SIGTERM 信号处理仅 Unix")
def test_sigint_cleans_pid_file():
    """SIGINT（Ctrl-C）后 PID/端口文件也被清理。"""
    _cleanup_files()
    try:
        with open("/tmp/androguard_daemon_sigint.log", "w") as log:
            proc = subprocess.Popen(
                ["androguard-skills", "daemon", "start"],
                stdout=log, stderr=log, cwd=REPO_ROOT,
            )
        assert _wait_running(15)
        with open(PID_FILE) as f:
            pid = int(f.read().strip())

        os.kill(pid, signal.SIGINT)

        deadline = time.time() + 10
        exited = False
        while time.time() < deadline:
            if proc.poll() is not None:
                exited = True
                break
            time.sleep(0.3)
        assert exited, "daemon 进程应在 SIGINT 后 10s 内退出"
        time.sleep(1)
        assert not os.path.exists(PID_FILE), "SIGINT 后 PID 文件应被清理"
    finally:
        _cleanup_files()
        try:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)
        except Exception:
            pass


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
    _cleanup_files()
    print(f"\n{passed} passed, {failed} failed, {len(fns)} total")
    sys.exit(1 if failed else 0)
