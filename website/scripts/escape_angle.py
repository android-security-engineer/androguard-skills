#!/usr/bin/env python3
"""转义 Markdown 文件里代码块外的裸 < >，避免 VitePress 当 HTML 标签解析。

规则：逐行扫描，``` 围栏内不动；围栏外，把独立的 < > 替换为 &lt; &gt;。
但保留已转义的 &lt;/&gt;、HTML 注释 <!-- -->、以及行内代码 `...` 内的内容。
为简单稳妥，这里只转义围栏外、且不在反引号内的 < 和 >。
"""
import re
import sys


def escape_inline(line):
    """转义行内代码反引号之外的 < >。"""
    # 把 `...` 段暂存，保护其内容
    parts = re.split(r"(`[^`]*`)", line)
    for i, p in enumerate(parts):
        if i % 2 == 1:  # 反引号内
            continue
        p = p.replace("<", "&lt;").replace(">", "&gt;")
        parts[i] = p
    return "".join(parts)


def process(path):
    lines = open(path, encoding="utf-8").read().splitlines()
    out = []
    in_fence = False
    for ln in lines:
        stripped = ln.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            out.append(ln)
            continue
        if in_fence:
            out.append(ln)
            continue
        out.append(escape_inline(ln))
    open(path, "w", encoding="utf-8").write("\n".join(out) + "\n")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        process(p)
        print(f"处理 {p}")
