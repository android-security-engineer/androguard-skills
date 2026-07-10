#!/usr/bin/env python3
"""根据 commands.json 生成 VitePress 命令文档页 + 各组 index 页。

每个命令一个 Markdown 文件：website/docs/commands/<group>/<cmd>.md
每组一个 index：website/docs/commands/<group>/index.md
顶层命令：website/docs/commands/<cmd>.md
"""
import json
import os
import re

# 路径基于本脚本位置，无论 cwd 在哪都能正确定位
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
ROOT = os.path.join(REPO_ROOT, "website", "docs", "commands")
DATA = os.path.join(SCRIPT_DIR, "commands.json")

# 组的中文标题 / 图标 / 简介
GROUP_META = {
    "daemon":     ("daemon · 进程管理", "⚙️", "管理 daemon 常驻进程：启动、停止、查看状态。daemon 缓存已加载的 APK/DEX/Analysis，跨命令复用，避免重复解析。"),
    "apk":        ("apk · APK 信息", "📦", "APK 维度的全部信息：基础元数据、签名（v1/v2/v3/v31）、四大组件、Manifest、文件、native 库、组件暴露面、攻击面、一键安全报告。共 56 个命令。"),
    "dex":        ("dex · DEX 信息", "🧩", "DEX 字节码与底层结构：类/方法/字段、反汇编、常量池表（string/type/proto/method/field_ids）、Encoded 表、注解、静态值。共 44 个命令。"),
    "analysis":   ("analysis · 静态分析", "🔍", "静态分析与安全审计：交叉引用、调用图、可达性、污点路径、19 域漏洞审计。共 69 个命令。"),
    "decompile":  ("decompile · 反编译", "🧠", "把 DEX 字节码反编译为可读形式：纯文本 Java 源码、结构化 AST、词法 token 流。共 6 个命令。"),
    "pentest":    ("pentest · 动态分析", "🧪", "基于 Frida 的动态分析：方法调用追踪、内存 DEX dump。需连接真机/模拟器。共 2 个命令。"),
    "resources":  ("resources · 资源解析", "🎨", "ARSC 资源表解析：包/locale/类型/配置变体、strings.xml、public.xml、ids.xml、资源 ID 双向查询。共 20 个命令。"),
    "visualize":  ("visualize · 可视化", "📊", "方法控制流图（CFG）导出：DOT、图片（PNG/JPG）、JSON 三种格式。共 3 个命令。"),
    "util":       ("util · 工具", "🔧", "工具命令：文件类型检测、AOSP 权限数据查询、类名/描述符格式转换。不依赖已加载 APK。共 5 个命令。"),
    "session":    ("session · 会话", "🗂️", "多 APK/DEX 关联分析：Session 创建、添加文件、跨 DEX 查类归属与字符串。共 8 个命令。"),
}


def slug(name):
    """命令名转文件名（连字符保留）。"""
    return name


def esc(text):
    """转义 help 文本里的 < > &，避免 VitePress 把 <application> 当 HTML 标签解析。"""
    if not text:
        return text
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fmt_param_row(p):
    """参数表格行。"""
    name = p["name"]
    if p["is_argument"]:
        name = f"`<{p['dest']}>`"
    else:
        name = f"`{name}`"
    typ = p["type"].replace("ParamType", "").lower() or "str"
    if p["choices"]:
        typ = "choice: " + " / ".join(f"`{c}`" for c in p["choices"])
    if p["is_flag"]:
        typ = "flag"
    req = "✅" if p["required"] else "—"
    default = "—" if p["default"] is None else f"`{p['default']}`"
    if p["is_flag"] and p["default"] is False:
        default = "`False`"
    help_t = esc(p["help"] or "")
    if p["multiple"]:
        help_t = "(可重复) " + help_t
    return f"| {name} | {typ} | {req} | {default} | {help_t} |"


def business_method(methods):
    """从 methods 列表里取真正的业务方法（去掉 load_apk 等辅助，去重）。"""
    seen = []
    for m in methods or []:
        if m in ("load_apk", "load_dex", "unload", "_get_skills", "_output_json"):
            continue
        if m not in seen:
            seen.append(m)
    return seen


def gen_command_page(group, cmd, is_top=False):
    name = cmd["name"]
    help_text = esc(cmd["help"] or "")
    methods = business_method(cmd.get("methods", []))
    params = cmd["params"]

    # 公共 --apk-path 单独说明
    has_apk_path = any(p["dest"] == "apk_path" for p in params)
    biz_params = [p for p in params if p["dest"] != "apk_path"]

    # 命令全名
    if is_top:
        full = f"androguard-skills {name}"
        title = name
    else:
        full = f"androguard-skills {group} {name}"
        title = f"{group} {name}"

    lines = []
    lines.append(f"# {title}\n")
    if help_text:
        lines.append(f"> {help_text}\n")

    # 用法
    lines.append("## 用法\n")
    lines.append("```bash")
    lines.append(full)
    lines.append("```\n")

    # 参数表
    lines.append("## 参数\n")
    if biz_params:
        lines.append("| 参数 | 类型 | 必填 | 默认 | 说明 |")
        lines.append("|------|------|------|------|------|")
        for p in biz_params:
            lines.append(fmt_param_row(p))
        lines.append("")
    else:
        lines.append("无业务参数。\n")

    if has_apk_path:
        lines.append("::: tip 公共参数 `--apk-path`\n")
        lines.append("支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。\n")
        lines.append(":::\n")

    # 说明
    lines.append("## 说明\n")
    desc = help_text or "见命令帮助。"
    lines.append(desc + "\n")

    # 对应 API
    if methods:
        lines.append("## 对应 API\n")
        for m in methods:
            lines.append(f"`skills.{m}(...)` — 详见 [Python API](../../guide/python-api)。")
        lines.append("")

    # 相关命令
    lines.append("## 相关\n")
    if is_top:
        lines.append("- [命令索引](./)")
    else:
        lines.append(f"- [{group} 命令组](./)")
        lines.append("- [命令索引](../)")
    lines.append("")

    return "\n".join(lines)


def gen_group_index(group, data):
    title, icon, desc = GROUP_META[group]
    cmds = data[group]["commands"]
    lines = []
    lines.append(f"# {icon} {title}\n")
    lines.append(f"> {desc}\n")
    lines.append(f"共 **{len(cmds)}** 个命令。\n")
    lines.append("## 命令列表\n")
    lines.append("| 命令 | 说明 |")
    lines.append("|------|------|")
    for c in cmds:
        lines.append(f"| [`{c['name']}`](./{slug(c['name'])}) | {esc(c['help'] or '')} |")
    lines.append("")
    lines.append("## 用法示例\n")
    lines.append("```bash")
    lines.append(f"androguard-skills {group} --help    # 查看本组所有命令")
    lines.append(f"androguard-skills {group} <子命令> --help")
    lines.append("```\n")
    lines.append("- [命令索引](../)")
    lines.append("")
    return "\n".join(lines)


def main():
    data = json.load(open(DATA, encoding="utf-8"))
    os.makedirs(ROOT, exist_ok=True)

    count = 0
    # 顶层命令
    for c in data["__top__"]["commands"]:
        path = os.path.join(ROOT, f"{slug(c['name'])}.md")
        # 已存在且手写过的（load/load-dex/unload）跳过覆盖
        if c["name"] in ("load", "load-dex", "unload") and os.path.exists(path):
            # 仍可补 methods；这里跳过，保持手写版
            continue
        open(path, "w", encoding="utf-8").write(gen_command_page(None, c, is_top=True))
        count += 1

    # 各组
    for group in GROUP_META:
        gdir = os.path.join(ROOT, group)
        os.makedirs(gdir, exist_ok=True)
        # index
        open(os.path.join(gdir, "index.md"), "w", encoding="utf-8").write(
            gen_group_index(group, data)
        )
        count += 1
        # 各命令
        for c in data[group]["commands"]:
            path = os.path.join(gdir, f"{slug(c['name'])}.md")
            open(path, "w", encoding="utf-8").write(gen_command_page(group, c))
            count += 1

    print(f"生成 {count} 个文件")


if __name__ == "__main__":
    main()
