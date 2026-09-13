#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills daemon 与单次模式输出一致性回归测试

daemon 是加速层（端口 8899），语义上应对 agent 透明——同一命令在 daemon
模式和单次 fallback 模式应返回相同结果。但两条代码路径不同：
  - daemon: _dispatch 用 getattr(skills, method_name) 动态分发
  - 单次: CLI 命令函数 _try_daemon_call 失败后 fallback _get_skills()+load_apk
若两者对同一输入返回不同结果，agent 切换模式会困惑
（/goal："对接几十个 agent"，模式间漂移让 agent 无法稳定对接）。

本测试启动独立 daemon（高位端口），对若干输出稳定的命令比对两种模式的
核心字段。选标量/稳定字段（package/version/权限数等），避开顺序敏感的
列表逐字比对（Analysis 内部 dict 迭代序可能致列表元素顺序差异→假阳性）。

复用 test_daemon_rpc.py 的 _DaemonHandle/RPC 基础设施模式（独立复制，不
import 测试模块，避免 pytest 收集耦合）。

运行：``pytest tests/test_daemon_vs_cli_consistency.py -v``
独立：``python3 tests/test_daemon_vs_cli_consistency.py``
"""
import json
import os
import socket
import subprocess
import sys
import time

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
APK = os.path.join(HERE, "data", "APK", "TestActivity.apk")
_NEED_APK = pytest.mark.skipif(
    not os.path.exists(APK), reason=f"基准 APK 不存在: {APK}"
)

TEST_PORT = 19299  # 与 test_daemon_rpc 的 18999 错开


def _wait_port_ready(port, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except (ConnectionRefusedError, OSError):
            time.sleep(0.2)
    return False


class _DaemonHandle:
    def __init__(self, port):
        self.port = port
        self.proc = None

    def __enter__(self):
        self.proc = subprocess.Popen(
            [sys.executable, "-c",
             f"import sys; sys.path.insert(0, '{REPO_ROOT}'); "
             f"from androguard.skills.daemon import DaemonServer; "
             f"d = DaemonServer(port={self.port}); d.start()"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            cwd=REPO_ROOT,
        )
        if not _wait_port_ready(self.port):
            raise RuntimeError(f"daemon 未在端口 {self.port} 就绪")
        return self

    def __exit__(self, *exc):
        if self.proc and self.proc.poll() is None:
            try:
                self.call("shutdown", {})
            except Exception:
                pass
            try:
                self.proc.terminate()
                self.proc.wait(timeout=5)
            except Exception:
                self.proc.kill()

    def call(self, method, params=None, timeout=180):
        req = {"jsonrpc": "2.0", "method": method,
               "params": params or {}, "id": 1}
        with socket.create_connection(("127.0.0.1", self.port),
                                       timeout=timeout) as s:
            s.sendall((json.dumps(req) + "\n").encode("utf-8"))
            buf = b""
            while b"\n" not in buf:
                chunk = s.recv(65536)
                if not chunk:
                    break
                buf += chunk
            return json.loads(buf.split(b"\n", 1)[0].decode("utf-8"))


def _cli_json(*args, timeout=120):
    proc = subprocess.run(
        ["androguard-skills", *args],
        capture_output=True, text=True, timeout=timeout, cwd=REPO_ROOT,
    )
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def _daemon_call(port, method, params, timeout=180):
    """调 daemon 并提取 result（去掉 JSON-RPC 包装）。"""
    req = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    with socket.create_connection(("127.0.0.1", port), timeout=timeout) as s:
        s.sendall((json.dumps(req) + "\n").encode("utf-8"))
        buf = b""
        while b"\n" not in buf:
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
        resp = json.loads(buf.split(b"\n", 1)[0].decode("utf-8"))
    if "error" in resp:
        return None
    return resp.get("result")


# 比对的命令 + 各自的核心稳定字段（标量/计数，避开顺序敏感列表）
# daemon 已 load_apk，方法无需再传 apk_path（params 里只放业务参数）
_CMDS = [
    # (label, cli_args, daemon_method, daemon_params, stable_fields)
    ("apk info", ["apk", "info", "--apk-path", APK],
     "apk_info", {},
     ["package", "version_name", "version_code", "app_name"]),
    ("apk permissions", ["apk", "permissions", "--apk-path", APK],
     "apk_permissions", {},
     ["count:permissions", "count:declared_permissions"]),
    ("analysis class-exists (existing)",
     ["analysis", "class-exists", "LTestDefaultPackage;", "--apk-path", APK],
     "analysis_class_exists", {"class_name": "LTestDefaultPackage;"},
     ["exists", "class"]),
    ("analysis class-exists (nonexistent)",
     ["analysis", "class-exists", "Lcom/nonexistent/None;",
      "--apk-path", APK],
     "analysis_class_exists", {"class_name": "Lcom/nonexistent/None;"},
     ["exists"]),
    ("dex header", ["dex", "header", "--apk-path", APK],
     "dex_header", {},
     ["header.magic", "header.checksum", "header.file_size"]),
]


def _get_nested(d, path):
    """按点号路径取嵌套字段（如 header.magic）。

    支持 ``count:`` 前缀取列表长度（如 ``count:permissions`` →
    len(d['permissions'])），用于比对列表规模而非顺序（避免迭代序假阳性）。
    """
    if path.startswith("count:"):
        val = _get_nested(d, path[len("count:"):])
        return len(val) if isinstance(val, list) else None
    cur = d
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


@_NEED_APK
def test_daemon_and_cli_return_same_core_fields():
    """daemon 与单次模式对同一命令返回的核心字段值必须一致。"""
    with _DaemonHandle(TEST_PORT) as d:
        # daemon 先 load_apk
        load_resp = d.call("load_apk", {"apk_path": APK})
        assert "error" not in load_resp, (
            f"daemon load_apk 失败: {load_resp.get('error')}"
        )
        diffs = []
        for label, cli_args, method, params, fields in _CMDS:
            cli_out = _cli_json(*cli_args)
            dae_out = _daemon_call(d.port, method, params)
            if cli_out is None or dae_out is None:
                diffs.append(f"{label}: 某侧输出为 None（cli={cli_out is None}, "
                             f"daemon={dae_out is None})")
                continue
            for f in fields:
                cv = _get_nested(cli_out, f)
                dv = _get_nested(dae_out, f)
                if cv != dv:
                    diffs.append(
                        f"{label}: 字段 `{f}` 不一致 "
                        f"cli={cv!r} daemon={dv!r}"
                    )
        assert not diffs, (
            f"daemon 与单次模式输出不一致（{len(diffs)} 处）：\n"
            + "\n".join(f"  - {x}" for x in diffs)
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
