#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroguardSkills 能力覆盖矩阵测试（封顶证明，可复现）

本测试用 ``inspect.getmembers`` 内省穷举 AndroGuard 四大核心对象
（APK / DEX / Analysis / ARSCParser）的全部公开方法，逐一映射到 skills
源码，证明 skills 已封装（或合理排除）底层库的整个公开 API 表面。

判据：在合并后的 skills 源码中，以裸方法名做全词匹配 ``\\bname\\b``。
（早期版本用 ``\\.method\\(`` 匹配得 37 个假阳性——skills 通过
getattr 间接分派 / 可调用对象存 dict / 引用不带括号等方式调用方法，
并非都写成 ``.method()``。裸名全词匹配是正确的判据。）

未匹配项分两类：
  1. **内部构建器 / 变异器 / REPL 辅助**：被更高层已暴露命令消费，或超
     出只读逆向 recon 范围。登记在 ``REASONABLE_EXCLUSIONS`` 并附理由。
  2. **真实能力缺口**：应有对应 skills 封装而无。本测试断言其数为 0。

升级 AndroGuard 后重跑本测试：若新增公开方法导致缺口数 > 0，说明需要
新增对应 skills 封装——这是回归断言而非一次性检查。

运行：``pytest tests/test_api_coverage_matrix.py -v``
独立运行：``python3 tests/test_api_coverage_matrix.py``
"""
import inspect
import os
import re
import sys

# 允许独立运行（不依赖 pytest）。注意：本测试不在模块导入时调用
# logger.remove()——那会清空 loguru 全局 handler，污染同进程后续上游测试
# （如 test_apk.py::testAPKIntentFilters 依赖其收集期 add() 的 handler）。
# 本测试是纯静态内省，无需触碰日志配置。

# ---- 定位 skills 源码 ----
HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
SKILLS_DIR = os.path.join(REPO_ROOT, "androguard", "skills")


def _load_skills_source() -> str:
    """合并 skills 目录下所有 .py 源码为一个字符串。"""
    parts = []
    for fname in sorted(os.listdir(SKILLS_DIR)):
        if fname.endswith(".py"):
            with open(os.path.join(SKILLS_DIR, fname), "r", encoding="utf-8") as fh:
                parts.append(fh.read())
    return "\n".join(parts) + "\n"


# ---- 核心对象 ----
def _target_classes():
    from androguard.core.apk import APK
    from androguard.core.dex import DEX
    from androguard.core.analysis.analysis import Analysis
    from androguard.core.axml import ARSCParser
    return {"APK": APK, "DEX": DEX, "Analysis": Analysis, "ARSCParser": ARSCParser}


def _public_methods(cls) -> list:
    """枚举类的全部公开（非下划线开头）函数方法名。"""
    out = []
    for name, _fn in inspect.getmembers(cls, predicate=inspect.isfunction):
        if name.startswith("_"):
            continue
        out.append(name)
    return sorted(set(out))


# ---- 合理排除项（内部构建器 / 变异器 / REPL 辅助 / setter），逐条附理由 ----
# 这些方法被更高层已暴露的 skills 命令消费，或属于写操作/解析期接线，无独立
# 逆向调用价值。每项登记理由，便于升级时复核。
REASONABLE_EXCLUSIONS = {
    # --- 签名解析管线内部助手（被 apk signature / apk certificate 消费）---
    "APK.verify_signature": "签名验证管线内部：消费 asn1crypto.cms.SignerInfo 内部对象，由 apk signature 调用",
    "APK.find_certificate": "签名管线内部：从 cert bag 中定位 signer 引用的证书，由 apk signature 调用",
    "APK.get_hash_algorithm": "签名管线内部：从 SignerInfo 取哈希算法，由 apk signature 调用",
    "APK.parse_v2_v3_signature": "签名管线内部：解析 v2/v3 签名块，由 apk signature 初始化时调用",
    "APK.parse_signatures_or_digests": "签名管线内部：解析摘要字节，由 apk signature 调用",
    "APK.x509_ordered_name": "证书名格式化内部：x509.Name 排序，由 apk certificate 调用",
    "APK.read_uint32_le": "二进制读取原语：从 io_stream 读 uint32_le，解析期内部",
    # --- manifest 标签谓词（被 apk manifest-attrs / manifest-attr 消费）---
    "APK.get_value_from_tag": "manifest 谓词内部：取标签属性值，由 apk manifest-attrs 调用",
    "APK.is_tag_matched": "manifest 谓词内部：属性过滤匹配，由 apk manifest-attrs 调用",
    # --- 变异 / 重打包（写操作，超出只读 recon 范围）---
    "APK.new_zip": "重打包变异：创建新 zip（写操作），超出只读逆向 recon 范围",
    "DEX.fix_checksums": "DEX 变异：修补 checksum（写操作），超出只读 recon 范围",
    # --- 内部 setter（解析期接线）---
    "DEX.set_analysis": "内部 setter：注入 Analysis 引用，解析期接线",
    "DEX.set_decompiler": "内部 setter：注入反编译器，解析期接线",
    # --- REPL 便利 ---
    "Analysis.create_ipython_exports": "IPython REPL 实验性便利，非独立能力",
    # --- ARSC 内部助手 ---
    "ARSCParser.get_items": "资源解析内部：取包内 items，由 resources 系列命令消费",
    "ARSCParser.parse_id": "资源解析内部：解析 @[package:]DEADBEEF id，由 resources id 消费",
    # --- 平凡元信息 / REPL 打印 / 变异序列化 ---
    "APK.get_filename": "平凡元信息：返回 APK 文件路径，调用方经 --apk-path 已知，由 apk info 覆盖文件层",
    "APK.show": "REPL 打印便利：非结构化输出到 stdout，skills 全部返回 JSON，无对等必要",
    "DEX.show": "REPL 打印便利：非结构化输出到 stdout，skills 全部返回 JSON，无对等必要",
    "DEX.create_python_export": "REPL 实验性便利：把类/方法/字段名注入 Python 命名空间，非独立逆向能力",
    "DEX.save": "DEX 变异序列化：把含修改的 DEX 写回 bytes（写操作），超出只读 recon 范围",
    # --- 超集覆盖（能力已被更强 skills 命令完全包含）---
    "Analysis.find_strings": "已被 analysis_find_strings 超集覆盖：同为正则串搜索，额外附带 xref_from 引用位置",
}


def build_coverage_matrix():
    """构建覆盖矩阵。返回 (matrix, summary)。"""
    skills_src = _load_skills_source()
    targets = _target_classes()

    matrix = []  # [{obj, method, status, reason}]
    total = mapped = excluded = gaps = 0

    for tname in sorted(targets):
        cls = targets[tname]
        for m in _public_methods(cls):
            total += 1
            key = f"{tname}.{m}"
            if re.search(r"\b" + re.escape(m) + r"\b", skills_src):
                status = "mapped"
                reason = ""
                mapped += 1
            elif key in REASONABLE_EXCLUSIONS:
                status = "excluded"
                reason = REASONABLE_EXCLUSIONS[key]
                excluded += 1
            else:
                status = "gap"
                reason = ""
                gaps += 1
            matrix.append({"obj": tname, "method": m, "status": status, "reason": reason})

    summary = {
        "total_public_methods": total,
        "mapped": mapped,
        "excluded_reasonable": excluded,
        "gaps": gaps,
    }
    return matrix, summary


# ---- pytest 入口 ----
def test_api_coverage_matrix_has_no_real_gaps():
    """断言四大核心对象的公开 API 表面已 100% 映射，0 真实能力缺口。"""
    matrix, summary = build_coverage_matrix()
    gaps = [r for r in matrix if r["status"] == "gap"]
    assert not gaps, (
        f"发现 {len(gaps)} 个未覆盖且未登记排除的公开方法（真实能力缺口）：\n"
        + "\n".join(f"  - {g['obj']}.{g['method']}" for g in gaps)
        + "\n请为其新增 skills 封装，或在 REASONABLE_EXCLUSIONS 登记排除理由。"
    )
    # 同时断言合理排除项的理由都已填写（防止偷懒留空）
    for r in matrix:
        if r["status"] == "excluded":
            assert r["reason"], f"{r['obj']}.{r['method']} 被排除但未登记理由"


def test_coverage_matrix_summary_printable():
    """打印覆盖矩阵摘要（pytest -s 时可见），便于人工审计。"""
    matrix, summary = build_coverage_matrix()
    print("\n" + "=" * 60)
    print("AndroguardSkills 能力覆盖矩阵摘要")
    print("=" * 60)
    print(f"核心对象公开方法总数 : {summary['total_public_methods']}")
    print(f"  已映射到 skills   : {summary['mapped']}")
    print(f"  合理排除（登记理由）: {summary['excluded_reasonable']}")
    print(f"  真实能力缺口       : {summary['gaps']}")
    print("-" * 60)
    for r in matrix:
        if r["status"] == "excluded":
            print(f"  [排除] {r['obj']}.{r['method']} — {r['reason']}")
    print("=" * 60)
    assert summary["gaps"] == 0


# ---- skills 代码自身健康度：无死函数 ----
def _skills_module_functions():
    """收集各 skills 模块（非 main/daemon/__init__）的公开函数名。"""
    fns = {}
    for fname in sorted(os.listdir(SKILLS_DIR)):
        if fname.endswith(".py") and fname not in ("main.py", "daemon.py", "__init__.py"):
            src = open(os.path.join(SKILLS_DIR, fname)).read()
            mod = fname[:-3]
            fns[mod] = set(re.findall(r"^def (\w+)\(", src, re.M))
    return fns


def test_no_dead_skills_functions():
    """断言 skills 模块无死函数：每个公开函数应被至少一处引用（含动态分发）。

    防止重构后遗留无人调用的孤儿函数。判据：函数名在合并的全部 skills 源码中
    全词出现 ≥2 次（1 次是定义本身）。动态分发（daemon getattr / CLI _try_daemon_call
    用字符串方法名）也算引用——这些调用点用方法名字符串，会被全词匹配命中。

    DYNAMIC_DISPATCH_API 登记仅通过 daemon getattr 动态分发、无静态调用点的
    函数（客户端可用 {"method":"<name>"} 调用）。新增此类函数须在此登记并说明。
    """
    # 仅 daemon getattr 动态分发的 API（无静态调用点，但有 Python API 价值）
    DYNAMIC_DISPATCH_API = {
        "util_skills.util_calculate_fingerprint": "daemon 动态分发 API；apk_skills.apk_fingerprint 直接用原生 calculate_fingerprint 绕过此包装，但保留供 daemon 客户端按名调用",
        "util_skills.util_certificate_name_string": "daemon 动态分发 API；证书名在证书命令中已直接解析，但保留供 daemon 客户端按名调用",
    }
    skills_src = _load_skills_source()
    mods = _skills_module_functions()
    dead = []
    for mod, fns in mods.items():
        for fn in fns:
            if fn.startswith("_"):
                continue
            key = f"{mod}.{fn}"
            if key in DYNAMIC_DISPATCH_API:
                continue
            occurrences = len(re.findall(r"\b" + re.escape(fn) + r"\b", skills_src))
            if occurrences < 2:
                dead.append(f"{key} (引用 {occurrences})")
    assert not dead, (
        f"发现 {len(dead)} 个疑似死函数（定义但无任何调用点）：\n"
        + "\n".join(f"  - {d}" for d in dead)
        + "\n若为动态分发 API，在 DYNAMIC_DISPATCH_API 登记并说明；否则删除。"
    )


# ---- 独立运行入口 ----
if __name__ == "__main__":
    matrix, summary = build_coverage_matrix()
    test_coverage_matrix_summary_printable()
    # 也跑死函数检查
    test_no_dead_skills_functions()
    if summary["gaps"] == 0:
        print(f"\n✅ 封顶证明成立：{summary['total_public_methods']} 个公开方法，"
              f"{summary['mapped']} 已映射 + {summary['excluded_reasonable']} 合理排除，"
              f"0 真实能力缺口。")
        sys.exit(0)
    else:
        print(f"\n❌ 存在 {summary['gaps']} 个真实能力缺口：")
        for r in matrix:
            if r["status"] == "gap":
                print(f"   GAP: {r['obj']}.{r['method']}")
        sys.exit(1)
