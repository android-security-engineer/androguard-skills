#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills _is_daemon_running 端口探测 + PID 复用防护回归测试

此前 _is_daemon_running 只查 PID 文件 + os.kill(pid,0)——PID 复用（daemon
崩溃后 OS 把 PID 分配给别的进程）会误判"在跑"→start 拒绝启动。

已修复：双重确认 (1) PID 文件存在且进程存活；(2) 端口可连接且响应 status。
PID 存活但端口不响应（卡死/崩溃/PID 复用）→清理残留 PID 文件，返回 False。

运行：``pytest tests/test_daemon_running_check.py -v``
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
sys.path.insert(0, HERE)
sys.path.insert(0, REPO_ROOT)

from androguard.skills.daemon import DaemonServer, PID_FILE, PORT_FILE
from test_daemon_rpc import _DaemonHandle, TEST_PORT


def _cleanup_pid_files():
    for f in (PID_FILE, PORT_FILE):
        try:
            os.remove(f)
        except FileNotFoundError:
            pass


def test_no_pid_file_not_running():
    """无 PID 文件时判定未运行。"""
    _cleanup_pid_files()
    assert DaemonServer._is_daemon_running() is False


def test_stale_pid_file_cleaned():
    """残留 PID 文件（进程不存在）被清理，返回 False。"""
    _cleanup_pid_files()
    os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
    # 写一个极不可能存在的 PID（PID 空间上限附近）
    with open(PID_FILE, "w") as f:
        f.write("999999")
    assert DaemonServer._is_daemon_running() is False
    # PID 文件应被清理
    assert not os.path.exists(PID_FILE), "残留 PID 文件应被清理"


def test_invalid_pid_file_cleaned():
    """PID 文件内容非法（非数字）被清理。"""
    _cleanup_pid_files()
    os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
    with open(PID_FILE, "w") as f:
        f.write("not-a-number")
    assert DaemonServer._is_daemon_running() is False
    assert not os.path.exists(PID_FILE)


def test_running_daemon_detected():
    """真实运行的 daemon 被正确检测（端口响应 status）。"""
    _cleanup_pid_files()
    with _DaemonHandle(TEST_PORT + 90) as d:
        # daemon 已写 PID_FILE/PORT_FILE
        assert DaemonServer._is_daemon_running() is True


def test_pid_alive_but_port_dead_cleaned():
    """PID 存活但端口不响应（卡死/崩溃）→ 清理 PID 文件，返回 False。

    模拟：写当前进程的 PID（存活）但无 daemon 在 PORT_FILE 端口监听。
    """
    _cleanup_pid_files()
    os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
    # 写当前进程 PID（一定存活）
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))
    # 写一个无 daemon 监听的高位端口
    with open(PORT_FILE, "w") as f:
        f.write("39998")  # 极可能无服务
    assert DaemonServer._is_daemon_running() is False
    # PID 文件应被清理（端口不响应）
    assert not os.path.exists(PID_FILE), (
        "PID 存活但端口不响应时应清理 PID 文件（防 PID 复用误判）"
    )
    _cleanup_pid_files()


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
    _cleanup_pid_files()
    print(f"\n{passed} passed, {failed} failed, {len(fns)} total")
    sys.exit(1 if failed else 0)
