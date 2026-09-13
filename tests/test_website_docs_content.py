#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills 文档站渲染文档内容一致性回归测试

test_website_docs_coverage.py 只校验渲染 .md 文件存在性，不校验内容——若
渲染模板 bug 或 commands.json 漂移，可能生成内容错配的 .md（标题/组/命令名
与文件名不符，或 API 方法名与 commands.json 的 methods 不符）。agent 照
错配文档用 skills API 会调错方法（/goal："对接几十个 agent"）。

本测试两层校验：
  1. 每个渲染 .md 的 `# 标题`（第一行）必须匹配 commands.json 里对应的
     `组 命令名`（标题=文件名对应的组+命令）。
  2. 渲染 .md 里 `skills.<method>(...)` 的 method 必须在该命令的
     commands.json methods 列表里（业务方法过滤后）。

运行：``pytest tests/test_website_docs_content.py -v``
独立：``python3 tests/test_website_docs_content.py``
"""
import json
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
COMMANDS_JSON = os.path.join(REPO_ROOT, "website", "scripts", "commands.json")
DOCS_COMMANDS_DIR = os.path.join(REPO_ROOT, "website", "docs", "commands")

# 业务方法过滤：与 gen_command_docs.py 的 business_method 一致
_AUX_METHODS = {"load_apk", "load_dex", "unload", "_get_skills",
                "_output_json", "_try_daemon_call"}


def _business_methods(methods):
    """过滤辅助方法，返回真正的业务方法集合（去重）。"""
    result = []
    seen = set()
    for m in methods or []:
        if m in _AUX_METHODS:
            continue
        if m not in seen:
            seen.add(m)
            result.append(m)
    return set(result)


def _load_commands_index():
    """返回 {(group, cmd_name): (doc_path, business_methods_set)}。"""
    with open(COMMANDS_JSON, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    index = {}
    for group, section in data.items():
        if not isinstance(section, dict):
            continue
        if group == "__top__":
            base = DOCS_COMMANDS_DIR
        else:
            base = os.path.join(DOCS_COMMANDS_DIR, group)
        for cmd in section.get("commands", []):
            name = cmd.get("name")
            if not name:
                continue
            doc_path = os.path.join(base, f"{name}.md")
            methods = _business_methods(cmd.get("methods", []))
            index[(group, name)] = (doc_path, methods)
    return index


def test_doc_title_matches_command():
    """每个渲染 .md 的 # 标题必须匹配 `组 命令名`。"""
    if not os.path.exists(COMMANDS_JSON):
        pytest.skip("commands.json 不存在")
    index = _load_commands_index()

    mismatches = []
    for (group, name), (doc_path, _) in index.items():
        if not os.path.exists(doc_path):
            continue  # 文件缺失已由 test_website_docs_coverage 守
        with open(doc_path, "r", encoding="utf-8") as fh:
            first_line = fh.readline().strip()
        expected = f"# {group} {name}" if group != "__top__" else f"# {name}"
        if first_line != expected:
            mismatches.append(
                f"{doc_path}: 标题 `{first_line}` 应为 `{expected}`"
            )
    assert not mismatches, (
        f"发现 {len(mismatches)} 处渲染文档标题与命令不符：\n"
        + "\n".join(f"  - {m}" for m in mismatches[:30])
    )


def test_doc_api_methods_in_commands_json():
    """渲染 .md 里 skills.<method> 必须在该命令的 methods 列表里。"""
    if not os.path.exists(COMMANDS_JSON):
        pytest.skip("commands.json 不存在")
    index = _load_commands_index()

    # skills.<method>(...) 模式
    api_re = re.compile(r"skills\.([a-z_][a-z0-9_]*)\(")
    mismatches = []
    for (group, name), (doc_path, business_methods) in index.items():
        if not os.path.exists(doc_path):
            continue
        with open(doc_path, "r", encoding="utf-8") as fh:
            content = fh.read()
        doc_methods = set(api_re.findall(content))
        # 文档里出现的每个业务方法必须在 commands.json 的业务方法集合里
        for m in doc_methods:
            if m in _AUX_METHODS:
                continue  # 辅助方法在文档里出现是正常的（如 load_apk 说明）
            if business_methods and m not in business_methods:
                mismatches.append(
                    f"{doc_path}: `skills.{m}(...)` 不在 {group} {name} 的 "
                    f"commands.json methods 里（业务方法: "
                    f"{sorted(business_methods) or '无'}）"
                )
    assert not mismatches, (
        f"发现 {len(mismatches)} 处渲染文档 API 方法与 commands.json 不符：\n"
        + "\n".join(f"  - {m}" for m in mismatches[:30])
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
