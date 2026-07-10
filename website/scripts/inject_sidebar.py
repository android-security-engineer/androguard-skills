#!/usr/bin/env python3
"""把 gen_sidebar.py 生成的片段注入 config.ts 的 /commands/ 侧边栏占位区。"""
import re

FRAG = open("website/scripts/sidebar_fragment.txt", encoding="utf-8").read()
CFG = open("website/docs/.vitepress/config.ts", encoding="utf-8").read()

# 替换 /commands/ sidebar 块里从 '// 各组：' 注释后到该块结束的部分
# 策略：定位 "/commands/': [" 到下一个 "      ]," 之间，替换组条目
pattern = r"(/commands/': \[\s*\{\s*text: '命令总览'[^}]*\},\s*\n)(.*?)(\n      \],)"
m = re.search(pattern, CFG, re.DOTALL)
if not m:
    # 退而求其次：直接替换占位注释之间的内容
    print("WARN: 精确匹配失败，尝试占位替换", file=__import__('sys').stderr)
    raise SystemExit(1)

new_block = m.group(1) + FRAG.rstrip() + m.group(3)
new_cfg = CFG[:m.start()] + new_block + CFG[m.end():]
open("website/docs/.vitepress/config.ts", "w", encoding="utf-8").write(new_cfg)
print("config.ts 已注入侧边栏条目")
