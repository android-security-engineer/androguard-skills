#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills 无效 APK 文件处理回归测试

test_cli_error_paths.py 守了"APK 文件不存在→结构化 error"，但"文件存在但
非有效 APK"（如文本文件改 .apk、损坏的 APK、截断的 ZIP）未守。agent 可能
传入损坏/伪造的 APK，CLI/daemon 应返回结构化 error 而非崩溃
（/goal："对接几十个 agent"，无效输入不应崩进程，agent 需可解析 error 自恢复）。

本测试用非 APK 文件（纯文本）和截断的 ZIP 验证：
  1. 单次模式：load 无效 APK → 结构化 error（exit 0，JSON）
  2. 单次模式：直接调查询命令传无效 --apk-path → 结构化 error
  3. daemon 模式：load 无效 APK → JSON-RPC error（不崩进程）

运行：``pytest tests/test_invalid_apk_handling.py -v``
独立：``python3 tests/test_invalid_apk_handling.py``
"""
import json
import os
import socket
import subprocess
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
TEST_PORT = 19606


def _cli(*args, timeout=60):
    proc = subprocess.run(
        ["androguard-skills", *args],
        capture_output=True, text=True, timeout=timeout, cwd=REPO_ROOT,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _make_invalid_apk(content=b"this is not a valid APK file"):
    """创建一个非 APK 文件，返回路径。"""
    fd, path = tempfile.mkstemp(suffix=".apk")
    os.write(fd, content)
    os.close(fd)
    return path


def test_single_mode_load_invalid_apk_returns_structured_error():
    """单次模式传非 APK 文件应返回结构化 error，不崩。"""
    fake = _make_invalid_apk()
    try:
        code, out, err = _cli("apk", "info", "--apk-path", fake, timeout=30)
    finally:
        os.unlink(fake)
    assert code == 0, (
        f"无效 APK 应 exit 0 输出结构化 error，实际 exit {code}, "
        f"stderr: {err[-300:]}"
    )
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        pytest.fail(f"应输出 JSON，实际: {out[:300]}")
    assert "error" in data, f"应含 error 键: {data}"
    assert "Traceback" not in err, f"不应有 traceback: {err[-300:]}"


def test_single_mode_truncated_zip_returns_structured_error():
    """截断的 ZIP（APK 是 ZIP 格式）应返回结构化 error。"""
    # PK 头但内容截断
    fake = _make_invalid_apk(b"PK\x03\x04" + b"\x00" * 10)
    try:
        code, out, err = _cli("apk", "info", "--apk-path", fake, timeout=30)
    finally:
        os.unlink(fake)
    assert code == 0, f"截断 ZIP 应 exit 0: {code}, stderr: {err[-200:]}"
    data = json.loads(out)
    assert "error" in data, f"应含 error: {data}"


def _wait_port_ready(port, timeout=15):
    import time
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except (ConnectionRefusedError, OSError):
            import time as _t
            _t.sleep(0.2)
    return False


def test_daemon_load_invalid_apk_isolated():
    """daemon 模式 load 无效 APK 应返回 JSON-RPC error，不崩进程。"""
    proc = subprocess.Popen(
        [sys.executable, "-c",
         f"import sys; sys.path.insert(0, '{REPO_ROOT}'); "
         f"from androguard.skills.daemon import DaemonServer; "
         f"d = DaemonServer(port={TEST_PORT}); d.start()"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=REPO_ROOT,
    )
    try:
        if not _wait_port_ready(TEST_PORT):
            pytest.fail("daemon 未就绪")
        fake = _make_invalid_apk()
        try:
            req = {"jsonrpc": "2.0", "method": "load_apk",
                   "params": {"apk_path": fake}, "id": 1}
            with socket.create_connection(("127.0.0.1", TEST_PORT),
                                           timeout=30) as s:
                s.sendall((json.dumps(req) + "\n").encode("utf-8"))
                buf = b""
                while b"\n" not in buf:
                    chunk = s.recv(65536)
                    if not chunk:
                        break
                    buf += chunk
            resp = json.loads(buf.split(b"\n", 1)[0].decode("utf-8"))
        finally:
            os.unlink(fake)
        # 应返回 error（不崩），且进程存活
        assert "error" in resp, (
            f"无效 APK load 应返回 error，实际: {resp}"
        )
        # 进程仍存活（status 正常）
        req2 = {"jsonrpc": "2.0", "method": "status", "params": {}, "id": 2}
        with socket.create_connection(("127.0.0.1", TEST_PORT),
                                       timeout=10) as s:
            s.sendall((json.dumps(req2) + "\n").encode("utf-8"))
            buf = b""
            while b"\n" not in buf:
                chunk = s.recv(65536)
                if not chunk:
                    break
                buf += chunk
        status = json.loads(buf.split(b"\n", 1)[0].decode("utf-8"))
        assert "result" in status, f"daemon 应在无效 load 后仍存活: {status}"
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


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
