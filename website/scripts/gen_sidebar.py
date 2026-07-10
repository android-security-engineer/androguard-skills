#!/usr/bin/env python3
"""生成 VitePress 侧边栏 /commands/ 部分的 TS 片段，写到 stdout。"""
import json

d = json.load(open("website/scripts/commands.json", encoding="utf-8"))

GROUPS = ["daemon","apk","dex","analysis","decompile","pentest","resources","visualize","util","session"]
TITLES = {
    "daemon":"daemon · 进程管理","apk":"apk · APK 信息（56）","dex":"dex · DEX 信息（44）",
    "analysis":"analysis · 静态分析（69）","decompile":"decompile · 反编译（6）",
    "pentest":"pentest · 动态分析（2）","resources":"resources · 资源解析（20）",
    "visualize":"visualize · 可视化（3）","util":"util · 工具（5）","session":"session · 会话（8）",
}

out = []
for g in GROUPS:
    cmds = d[g]["commands"]
    out.append(f"        {{ text: '{TITLES[g]}', collapsed: true, items: [")
    out.append(f"          {{ text: '组概览', link: '/commands/{g}/' }},")
    for c in cmds:
        n = c["name"]
        out.append(f"          {{ text: '{n}', link: '/commands/{g}/{n}' }},")
    out.append("        ]},")
print("\n".join(out))
