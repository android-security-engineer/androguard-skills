#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills daemon 端口冲突优雅处理回归测试

daemon.start() 启动时若目标端口已被其他进程占用（多 agent 环境常见，
或前次 daemon 未正确退出），asyncio create_server 抛 OSError。
此前未 catch，daemon 进程崩溃吐 Python traceback，agent 无法解析自恢复
（/goal："对接几十个 agent"，端口冲突应输出结构化 error 而非 traceback）。

本测试先用 socket 占用端口，再启动 daemon 试图绑定同端口，验证：
  1. exit 0（不崩溃）
  2. stdout 输出结构化 JSON 含 "error" 键
  3. stderr 无 Python traceback

运行：``pytest tests/test_daemon_port_conflict.py -v``
独立：``python3 tests/test_daemon_port_conflict.py``
"""
import json
import os
import socket
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
TEST_PORT = 19603


def _occupy_port(port):
    """占用一个端口，返回保持的 socket（测试结束 close 释放）。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", port))
    s.listen(1)
    return s


def test_daemon_port_conflict_returns_structured_error():
    """端口被占时 daemon 应输出结构化 error，不崩不吐 traceback。"""
    holder = _occupy_port(TEST_PORT)
    try:
        proc = subprocess.run(
            [sys.executable, "-c",
             f"import sys; sys.path.insert(0, '{REPO_ROOT}'); "
             f"from androguard.skills.daemon import DaemonServer; "
             f"d = DaemonServer(port={TEST_PORT}); d.start()"],
            capture_output=True, text=True, timeout=10, cwd=REPO_ROOT,
        )
    finally:
        holder.close()

    # 1. exit 0（不崩溃）——结构化 error 走 stdout，非异常退出
    assert proc.returncode == 0, (
        f"端口冲突应 exit 0 输出结构化 error，实际 exit {proc.returncode}, "
        f"stderr: {proc.stderr[-300:]}"
    )
    # 2. stdout 是结构化 JSON 含 error 键
    try:
        data = json.loads(proc.stdout.strip())
    except json.JSONDecodeError:
        pytest.fail(
            f"端口冲突应输出 JSON，实际 stdout: {proc.stdout[:300]}"
        )
    assert "error" in data, f"JSON 应含 error 键: {data}"
    # error 应提到端口/地址相关
    err_msg = data["error"].lower()
    assert "port" in err_msg or "address" in err_msg or "bind" in err_msg, (
        f"error 应提及端口/地址: {data['error']}"
    )
    # 3. stderr 无 Python traceback
    assert "Traceback" not in proc.stderr, (
        f"不应有 traceback，stderr: {proc.stderr[-300:]}"
    )


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
