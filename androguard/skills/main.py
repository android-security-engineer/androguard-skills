"""
AndroguardSkillsMain - AndroGuard Skills 核心类和 CLI 入口。

将 AndroGuard 所有核心能力封装为可程序化调用的接口，
支持 Daemon 模式和单次执行模式。
"""

from __future__ import annotations

import json
import os
import sys
from typing import Union

import click
from loguru import logger

from androguard.skills import (
    analysis_skills,
    apk_skills,
    decompiler_skills,
    dex_skills,
    pentest_skills,
    resource_skills,
    session_skills,
    util_skills,
    visualize_skills,
)


class AndroguardSkillsMain:
    """
    AndroGuard Skills - 将所有能力封装为可程序化调用的接口。

    所有方法返回 dict，适合 JSON 序列化输出。

    使用示例::

        skills = AndroguardSkillsMain()
        skills.load_apk("test.apk")
        info = skills.apk_info()
        print(json.dumps(info, indent=2))
    """

    def __init__(self):
        self._apk = None
        self._dex_list = []
        self._analysis = None
        self._loaded_path = None
        self._session = None

    @property
    def is_loaded(self) -> bool:
        """检查是否已加载 APK 或 DEX"""
        return self._apk is not None or bool(self._dex_list)

    @property
    def has_session(self) -> bool:
        """检查是否已创建 Session"""
        return self._session is not None

    def _ensure_loaded(self):
        """确保已加载 APK 或 DEX，否则抛异常"""
        if not self.is_loaded:
            raise RuntimeError(
                "No APK or DEX loaded. Call load_apk() or load_dex() first."
            )

    # ================================================================
    # 加载
    # ================================================================

    def load_apk(self, apk_path: str) -> dict:
        """
        加载 APK 文件。

        调用 AnalyzeAPK() 获取 APK、DEX、Analysis 三元组，
        并返回 APK 基本信息。

        :param apk_path: APK 文件路径
        :return: 加载结果和基本信息
        """
        from androguard.misc import AnalyzeAPK

        if not os.path.exists(apk_path):
            # 抛异常而非返回 dict：让 CLI 的 _SkillsCliGroup 统一捕获输出结构化
            # error，且错误信息精确（"File not found"），不会被后续 _ensure_loaded
            # 的"No APK loaded"掩盖。daemon 路径的 _dispatch 同样捕获此异常。
            raise RuntimeError(f"File not found: {apk_path}")

        try:
            a, d, dx = AnalyzeAPK(apk_path)
            # 释放上一轮解析对象：Analysis 持有海量 xref 跨引用图（ClassAnalysis
            # ↔ MethodAnalysis 互相引用成环），纯引用计数无法回收，daemon 长跑
            # 下连续 load 不同 APK 会导致内存膨胀。先显式断开旧引用再 gc.collect。
            self._apk = None
            self._dex_list = []
            self._analysis = None
            self._loaded_path = None
            import gc

            gc.collect()
            self._apk = a
            self._dex_list = d
            self._analysis = dx
            self._loaded_path = apk_path

            # 返回基本信息
            info = apk_skills.apk_info(self._apk)
            info["status"] = "loaded"
            info["path"] = apk_path
            return info
        except Exception as e:
            # 抛异常而非返回 dict：与 File not found 路径一致，让 CLI 的
            # _SkillsCliGroup 统一捕获输出结构化 error，daemon 路径的 _dispatch
            # try/except 同样捕获并返回 JSON-RPC error(-32603)。此前返回 dict
            # 会被当 result 原样回传，客户端无法区分成功与失败。
            raise RuntimeError(f"Failed to load APK: {str(e)}")

    def unload(self) -> dict:
        """卸载当前已加载的 APK，释放解析对象。

        daemon 长跑下连续 load 不同 APK，虽然 load_apk 会 gc 旧对象，但 glibc
        malloc 不归还 arena 给 OS（Python+glibc 已知行为，traced memory 回落
        而 RSS 不降）。对接几十个 agent 处理大 APK 后，agent 可显式 unload
        释放 Python 层引用 + gc，配合进程级 MALLOC_TRIM_THRESHOLD 让 RSS 回落。

        :return: 卸载结果
        """
        loaded_path = self._loaded_path
        self._apk = None
        self._dex_list = []
        self._analysis = None
        self._loaded_path = None
        self._session = None
        import gc

        gc.collect()
        # 尝试让 glibc 归还空闲 arena 给 OS（ctypes 调 malloc_trim）。
        # 降低 daemon 长跑 RSS 高位，daemon 进程内安全。
        try:
            import ctypes

            libc = ctypes.CDLL("libc.so.6")
            libc.malloc_trim(0)
        except Exception:
            pass  # 非 glibc 平台或无权限——gc 已回收 Python 层，可接受
        return {"status": "unloaded", "path": loaded_path}

    # ================================================================
    # APK 信息
    # ================================================================

    def apk_info(self) -> dict:
        """获取 APK 基本信息（包名、版本、SDK版本等）"""
        self._ensure_loaded()
        return apk_skills.apk_info(self._apk)

    def apk_permissions(self) -> dict:
        """获取 APK 权限信息（含保护级别详情）"""
        self._ensure_loaded()
        return apk_skills.apk_permissions(self._apk)

    def apk_activities(self) -> dict:
        """获取 APK Activity 列表（含 intent-filter）"""
        self._ensure_loaded()
        return apk_skills.apk_activities(self._apk)

    def apk_services(self) -> dict:
        """获取 APK Service 列表"""
        self._ensure_loaded()
        return apk_skills.apk_services(self._apk)

    def apk_receivers(self) -> dict:
        """获取 APK BroadcastReceiver 列表"""
        self._ensure_loaded()
        return apk_skills.apk_receivers(self._apk)

    def apk_providers(self) -> dict:
        """获取 APK ContentProvider 列表"""
        self._ensure_loaded()
        return apk_skills.apk_providers(self._apk)

    def apk_intent_filters(self, component: str) -> dict:
        """
        获取指定组件的 Intent Filter。

        :param component: 组件完整类名
        """
        self._ensure_loaded()
        return apk_skills.apk_intent_filters(self._apk, component)

    def apk_signature(self) -> dict:
        """获取 APK 签名信息（v1/v2/v3、证书指纹）"""
        self._ensure_loaded()
        return apk_skills.apk_signature(self._apk)

    def apk_files(self) -> dict:
        """获取 APK 文件列表（含类型、CRC）"""
        self._ensure_loaded()
        return apk_skills.apk_files(self._apk)

    def apk_manifest(self) -> dict:
        """获取 AndroidManifest.xml 内容"""
        self._ensure_loaded()
        return apk_skills.apk_manifest(self._apk)

    def apk_features(self) -> dict:
        """获取 APK uses-feature 列表"""
        self._ensure_loaded()
        return apk_skills.apk_features(self._apk)

    def apk_libraries(self) -> dict:
        """获取 APK uses-library 列表"""
        self._ensure_loaded()
        return apk_skills.apk_libraries(self._apk)

    def apk_icon(self, max_dpi: int = 65536) -> dict:
        """
        获取 APK 应用图标。

        :param max_dpi: 最大 DPI（默认 65536）
        """
        self._ensure_loaded()
        return apk_skills.apk_icon(self._apk, max_dpi)

    def apk_file(self, filename: str) -> dict:
        """
        提取 APK 中指定文件的内容。

        :param filename: 文件名
        """
        self._ensure_loaded()
        return apk_skills.apk_file(self._apk, filename)

    def apk_verify(self) -> dict:
        """验证 APK 完整性"""
        self._ensure_loaded()
        return apk_skills.apk_verify(self._apk)

    def apk_signing_block(self) -> dict:
        """获取 v2/v3 签名块详细信息"""
        self._ensure_loaded()
        return apk_skills.apk_signing_block(self._apk)

    def apk_manifest_attrs(
        self, tag_name: str, attribute: str, attribute_filter: dict = None
    ) -> dict:
        """
        批量提取 AndroidManifest.xml 中指定标签的属性值。

        :param tag_name: 标签名（如 uses-permission）
        :param attribute: 属性名（如 name）
        :param attribute_filter: 额外属性过滤条件
        """
        self._ensure_loaded()
        return apk_skills.apk_manifest_attrs(
            self._apk, tag_name, attribute, attribute_filter
        )

    def apk_manifest_attr(
        self, tag_name: str, attribute: str, attribute_filter: dict = None
    ) -> dict:
        """
        提取 AndroidManifest.xml 中单个标签的属性值。

        :param tag_name: 标签名
        :param attribute: 属性名
        :param attribute_filter: 额外属性过滤条件
        """
        self._ensure_loaded()
        return apk_skills.apk_manifest_attr(
            self._apk, tag_name, attribute, attribute_filter
        )

    def apk_certificate(self, filename: str = None) -> dict:
        """
        获取 APK 签名证书详情。

        :param filename: 签名文件名（如 META-INF/CERT.RSA）。None 时返回所有证书
        """
        self._ensure_loaded()
        return apk_skills.apk_certificate(self._apk, filename)

    def apk_verify_signature(self, filename: str = None) -> dict:
        """
        对 APK 签名做密码学验证（验证签名者信息是否匹配签名文件）。

        :param filename: 签名文件名。None 时验证所有签名文件
        """
        self._ensure_loaded()
        return apk_skills.apk_verify_signature(self._apk, filename)

    def apk_files_info(self) -> dict:
        """获取 APK 文件详细信息（名称/类型/CRC32）"""
        self._ensure_loaded()
        return apk_skills.apk_files_info(self._apk)

    def apk_dex_data(self, all_dex: bool = False) -> dict:
        """
        提取 DEX 二进制数据（base64）。

        :param all_dex: 是否提取所有 DEX（multidex）
        """
        self._ensure_loaded()
        return apk_skills.apk_dex_data(self._apk, all_dex)

    def apk_raw(self) -> dict:
        """提取整个 APK 原始字节（base64）"""
        self._ensure_loaded()
        return apk_skills.apk_raw(self._apk)

    def apk_manifest_tags(
        self, tag_name: str, attribute_filter: dict = None
    ) -> dict:
        """
        按属性过滤查找 manifest 标签。

        :param tag_name: 标签名
        :param attribute_filter: 属性过滤条件
        """
        self._ensure_loaded()
        return apk_skills.apk_manifest_tags(
            self._apk, tag_name, attribute_filter
        )

    # ================================================================
    # DEX 信息
    # ================================================================

    def dex_classes(self, filter_regex: str = None) -> dict:
        """
        获取 DEX 中的类列表。

        :param filter_regex: 类名过滤正则表达式（可选）
        """
        self._ensure_loaded()
        return dex_skills.dex_classes(self._dex_list, filter_regex)

    def dex_methods(self, class_name: str = None) -> dict:
        """
        获取 DEX 中的方法列表。

        :param class_name: 指定类名（可选，格式如 Lcom/example/MyClass;）
        """
        self._ensure_loaded()
        return dex_skills.dex_methods(self._dex_list, class_name)

    def dex_strings(self, filter_regex: str = None) -> dict:
        """
        获取 DEX 中的字符串。

        :param filter_regex: 字符串过滤正则表达式（可选）
        """
        self._ensure_loaded()
        return dex_skills.dex_strings(self._dex_list, filter_regex)

    def dex_strings_table(
        self, filter_regex: str = None, limit: int = None
    ) -> dict:
        """
        字符串常量池完整表（idx + 值 + 字节偏移 + UTF-16 长度）。

        :param filter_regex: 字符串过滤正则（可选）
        :param limit: 返回条目上限
        """
        self._ensure_loaded()
        return dex_skills.dex_strings_table(
            self._dex_list, filter_regex, limit
        )

    def dex_fields(self, class_name: str = None) -> dict:
        """
        获取 DEX 中的字段列表。

        :param class_name: 指定类名（可选）
        """
        self._ensure_loaded()
        return dex_skills.dex_fields(self._dex_list, class_name)

    def dex_header(self) -> dict:
        """获取 DEX 文件头信息"""
        self._ensure_loaded()
        if self._dex_list:
            return dex_skills.dex_header(self._dex_list[0])
        return {"error": "No DEX loaded"}

    def dex_class_names(self) -> dict:
        """快速获取 DEX 类名列表（不解析整个类）"""
        self._ensure_loaded()
        return dex_skills.dex_class_names(self._dex_list)

    def dex_hidden_api(self) -> dict:
        """获取 DEX 中的隐藏 API 列表"""
        self._ensure_loaded()
        if self._dex_list:
            return dex_skills.dex_hidden_api(self._dex_list[0])
        return {"error": "No DEX loaded"}

    def dex_disassemble(self, offset: int, size: int) -> dict:
        """
        反汇编 DEX 指定偏移处的字节码指令。

        :param offset: 起始偏移（必须是有效代码段偏移）
        :param size: 反汇编的字节大小
        """
        self._ensure_loaded()
        if self._dex_list:
            return dex_skills.dex_disassemble(self._dex_list[0], offset, size)
        return {"error": "No DEX loaded"}

    def dex_hierarchy(self) -> dict:
        """获取 DEX 类继承层级树"""
        self._ensure_loaded()
        return dex_skills.dex_hierarchy(self._dex_list)

    def dex_stats(self) -> dict:
        """获取 DEX 统计信息（各类计数、API 版本、格式）"""
        self._ensure_loaded()
        return dex_skills.dex_stats(self._dex_list)

    def dex_class(self, class_name: str) -> dict:
        """
        获取 DEX 中指定类的详细信息。

        :param class_name: 类名（格式如 Lcom/example/MyClass;）
        """
        self._ensure_loaded()
        return dex_skills.dex_class(self._dex_list, class_name)

    def dex_regex_strings(self, pattern: str) -> dict:
        """
        用正则高效搜索 DEX 字符串。

        :param pattern: 正则表达式
        """
        self._ensure_loaded()
        return dex_skills.dex_regex_strings(self._dex_list, pattern)

    def dex_debug_info(self, class_name: str = None) -> dict:
        """
        获取 DEX 调试信息。

        :param class_name: 指定类名（可选）
        """
        self._ensure_loaded()
        return dex_skills.dex_debug_info(self._dex_list, class_name)

    # ================================================================
    # 静态分析
    # ================================================================

    def analysis_xrefs_from(self, class_name: str) -> dict:
        """
        获取谁引用了指定类（XrefFrom）。

        :param class_name: 类名（格式如 Lcom/example/MyClass;）
        """
        self._ensure_loaded()
        return analysis_skills.analysis_xrefs_from(self._analysis, class_name)

    def analysis_xrefs_to(self, class_name: str) -> dict:
        """
        获取指定类引用了谁（XrefTo）。

        :param class_name: 类名
        """
        self._ensure_loaded()
        return analysis_skills.analysis_xrefs_to(self._analysis, class_name)

    def analysis_method_xrefs(self, class_name: str, method_name: str) -> dict:
        """
        获取指定方法的交叉引用。

        :param class_name: 类名
        :param method_name: 方法名
        """
        self._ensure_loaded()
        return analysis_skills.analysis_method_xrefs(
            self._analysis, class_name, method_name
        )

    def analysis_callgraph(self, output: str, fmt: str = "gml") -> dict:
        """
        生成调用图并导出。

        :param output: 输出文件路径
        :param fmt: 输出格式（gml, gexf, graphml, net）
        """
        self._ensure_loaded()
        return analysis_skills.analysis_callgraph(
            self._analysis, self._apk, output, fmt
        )

    def analysis_find_classes(self, pattern: str) -> dict:
        """
        按正则表达式搜索类。

        :param pattern: 类名正则表达式
        """
        self._ensure_loaded()
        return analysis_skills.analysis_find_classes(self._analysis, pattern)

    def analysis_find_methods(self, pattern: str) -> dict:
        """
        按正则表达式搜索方法。

        :param pattern: 方法名正则表达式
        """
        self._ensure_loaded()
        return analysis_skills.analysis_find_methods(self._analysis, pattern)

    def analysis_find_methods_advanced(
        self,
        classname: str = ".*",
        methodname: str = ".*",
        descriptor: str = ".*",
        accessflags: str = ".*",
        no_external: bool = False,
        limit: int = 500,
    ) -> dict:
        """多维正则方法搜索（类名×方法名×描述符×访问标志×排除外部，原生 find_methods）。"""
        self._ensure_loaded()
        return analysis_skills.analysis_find_methods_advanced(
            self._analysis,
            classname,
            methodname,
            descriptor,
            accessflags,
            no_external,
            limit,
        )

    def analysis_find_classes_advanced(
        self, name: str = ".*", no_external: bool = False, limit: int = 500
    ) -> dict:
        """多维正则类搜索（类名正则 + 排除外部类，原生 find_classes）。"""
        self._ensure_loaded()
        return analysis_skills.analysis_find_classes_advanced(
            self._analysis, name, no_external, limit
        )

    def analysis_find_strings(self, pattern: str) -> dict:
        """
        按正则表达式搜索字符串。

        :param pattern: 字符串正则表达式
        """
        self._ensure_loaded()
        return analysis_skills.analysis_find_strings(self._analysis, pattern)

    def analysis_permission_usage(self, permission: str) -> dict:
        """
        追踪指定权限的使用情况。

        :param permission: 权限名称
        """
        self._ensure_loaded()
        return analysis_skills.analysis_permission_usage(
            self._analysis, permission
        )

    def analysis_api_usage(
        self, limit: int = None, group_by_class: bool = False
    ) -> dict:
        """
        获取 Android API 使用情况（对应 api-usage CLI，支持按类分组）。

        :param limit: 返回数量限制（可选）
        :param group_by_class: 是否按 API 类分组统计
        """
        self._ensure_loaded()
        return analysis_skills.analysis_api_usage_grouped(
            self._analysis, limit, group_by_class
        )

    def analysis_internal_classes(self, filter_regex: str = None) -> dict:
        """
        获取应用内部类列表（非外部依赖）。

        :param filter_regex: 类名过滤正则（可选）
        """
        self._ensure_loaded()
        return analysis_skills.analysis_internal_classes(
            self._analysis, filter_regex
        )

    def analysis_external_classes(self, filter_regex: str = None) -> dict:
        """
        获取外部依赖类列表。

        :param filter_regex: 类名过滤正则（可选）
        """
        self._ensure_loaded()
        return analysis_skills.analysis_external_classes(
            self._analysis, filter_regex
        )

    def analysis_internal_methods(self, filter_regex: str = None) -> dict:
        """
        获取应用内部方法列表。

        :param filter_regex: 方法名过滤正则（可选）
        """
        self._ensure_loaded()
        return analysis_skills.analysis_internal_methods(
            self._analysis, filter_regex
        )

    def analysis_external_methods(self, filter_regex: str = None) -> dict:
        """
        获取外部方法列表。

        :param filter_regex: 方法名过滤正则（可选）
        """
        self._ensure_loaded()
        return analysis_skills.analysis_external_methods(
            self._analysis, filter_regex
        )

    def analysis_field_xrefs(self, class_name: str, field_name: str) -> dict:
        """
        获取指定字段的交叉引用。

        :param class_name: 类名
        :param field_name: 字段名
        """
        self._ensure_loaded()
        return analysis_skills.analysis_field_xrefs(
            self._analysis, class_name, field_name
        )

    def analysis_field_xrefs_detail(
        self, class_name: str, field_name: str
    ) -> dict:
        """
        获取字段读/写引用详情（含每处 offset，不去重）。

        :param class_name: 类名
        :param field_name: 字段名
        """
        self._ensure_loaded()
        return analysis_skills.analysis_field_xrefs_detail(
            self._analysis, class_name, field_name
        )

    def analysis_find_fields(self, pattern: str) -> dict:
        """
        按正则表达式搜索字段。

        :param pattern: 字段名正则表达式
        """
        self._ensure_loaded()
        return analysis_skills.analysis_find_fields(self._analysis, pattern)

    def analysis_permissions_map(self) -> dict:
        """获取完整的权限映射"""
        self._ensure_loaded()
        return analysis_skills.analysis_permissions_map(self._analysis)

    def analysis_class_exists(self, class_name: str) -> dict:
        """
        检查指定类是否存在（快速布尔判断）。

        :param class_name: 类名（格式如 Lcom/example/MyClass;）
        """
        self._ensure_loaded()
        return analysis_skills.analysis_class_exists(
            self._analysis, class_name
        )

    def analysis_method_analysis(
        self, class_name: str, method_name: str, descriptor: str
    ) -> dict:
        """
        按 class+method+descriptor 精确获取方法分析（含完整 xref）。

        :param class_name: 类名
        :param method_name: 方法名
        :param descriptor: 方法描述符（如 (Landroid/os/Bundle;)V）
        """
        self._ensure_loaded()
        return analysis_skills.analysis_method_analysis(
            self._analysis, class_name, method_name, descriptor
        )

    def analysis_strings_analysis(self, limit: int = None) -> dict:
        """
        获取全部字符串分析（含引用位置）。

        :param limit: 返回数量限制（可选）
        """
        self._ensure_loaded()
        return analysis_skills.analysis_strings_analysis(self._analysis, limit)

    def analysis_security_hotspots(self, limit: int = 50) -> dict:
        """
        APK 安全热点批量扫描（反射/加密/动态加载/命令执行/网络/native 等）。

        :param limit: 每类热点返回的调用位置上限
        """
        self._ensure_loaded()
        return analysis_skills.analysis_security_hotspots(
            self._analysis, limit
        )

    def apk_attack_surface(
        self,
        max_depth: int = 4,
        per_sink_limit: int = 10,
        max_nodes_per_component: int = 2000,
        include_safe: bool = False,
    ) -> dict:
        """
        攻击面聚合——交叉导出组件与其处理类前向可达的危险 sink。

        :param max_depth: 从组件类方法前向递归深度（默认 4）
        :param per_sink_limit: 每组件每类 sink 样本上限（默认 10）
        :param max_nodes_per_component: 单组件 BFS 节点上限（默认 2000）
        :param include_safe: 是否也分析非导出/受保护组件（默认 False）
        """
        self._ensure_loaded()
        return analysis_skills.apk_attack_surface(
            self._apk,
            self._analysis,
            max_depth,
            per_sink_limit,
            max_nodes_per_component,
            include_safe,
        )

    def analysis_native_methods(self, limit: int = 200) -> dict:
        """枚举所有 native 方法（JNI 边界）+ 声明类 + 调用方。"""
        self._ensure_loaded()
        return analysis_skills.analysis_native_methods(self._analysis, limit)

    def analysis_crypto_usage(self, per_type_limit: int = 100) -> dict:
        """加密 API 用法聚合 + 算法串还原 + 弱加密标记（ECB/DES/MD5/SHA1/RC4）。"""
        self._ensure_loaded()
        return analysis_skills.analysis_crypto_usage(
            self._analysis, per_type_limit
        )

    def analysis_reflection_targets(self, per_type_limit: int = 100) -> dict:
        """反射调用点 + 反射目标字符串还原（反混淆）。"""
        self._ensure_loaded()
        return analysis_skills.analysis_reflection_targets(
            self._analysis, per_type_limit
        )

    def analysis_url_endpoints(self, per_type_limit: int = 200) -> dict:
        """从字符串常量池提取 URL/host/IP 网络端点 + 引用方法。"""
        self._ensure_loaded()
        return analysis_skills.analysis_url_endpoints(
            self._analysis, per_type_limit
        )

    def analysis_taint_path(
        self,
        src_class: str,
        src_method: str,
        dst_class: str,
        dst_method: str,
        src_descriptor: str = None,
        dst_descriptor: str = None,
        max_depth: int = 8,
        max_nodes: int = 20000,
    ) -> dict:
        """源→汇调用路径搜索（前向 BFS + 父指针重建一条 source→sink 调用链）。"""
        self._ensure_loaded()
        return analysis_skills.analysis_taint_path(
            self._analysis,
            src_class,
            src_method,
            dst_class,
            dst_method,
            src_descriptor,
            dst_descriptor,
            max_depth,
            max_nodes,
        )

    def apk_deeplinks(self) -> dict:
        """深链接枚举（manifest intent-filter/data → scheme/host/path + 组件 + BROWSABLE）。"""
        self._ensure_loaded()
        return apk_skills.apk_deeplinks(self._apk)

    def analysis_webview_security(self, per_type_limit: int = 100) -> dict:
        """WebView 安全配置审计（addJavascriptInterface/文件访问/JS/调试等危险配置聚合 + findings）。"""
        self._ensure_loaded()
        return analysis_skills.analysis_webview_security(
            self._analysis, per_type_limit
        )

    def analysis_ssl_safety(self, per_type_limit: int = 100) -> dict:
        """SSL/TLS 校验绕过检测（不安全 TrustManager/HostnameVerifier + 已知绕过调用，MITM 审计）。"""
        self._ensure_loaded()
        return analysis_skills.analysis_ssl_safety(
            self._analysis, per_type_limit
        )

    def analysis_insecure_storage(self, per_type_limit: int = 100) -> dict:
        """不安全数据存储审计（外部存储/世界可读写模式/明文 SharedPreferences/DB，OWASP M9）。"""
        self._ensure_loaded()
        return analysis_skills.analysis_insecure_storage(
            self._analysis, per_type_limit
        )

    def analysis_sql_injection(self, per_type_limit: int = 100) -> dict:
        """SQL 注入面审计（rawQuery/execSQL/query 执行点枚举，OWASP M7）。"""
        self._ensure_loaded()
        return analysis_skills.analysis_sql_injection(
            self._analysis, per_type_limit
        )

    def analysis_pending_intent(self, per_type_limit: int = 100) -> dict:
        """PendingIntent 可变性审计（FLAG_IMMUTABLE 缺失 + Intent 重定向面）。"""
        self._ensure_loaded()
        return analysis_skills.analysis_pending_intent(
            self._analysis, per_type_limit
        )

    def analysis_privacy_sinks(self, per_type_limit: int = 100) -> dict:
        """隐私数据收集审计（设备标识/位置/联系人/账户/已装应用/剪贴板/录音摄像，OWASP M6）。"""
        self._ensure_loaded()
        return analysis_skills.analysis_privacy_sinks(
            self._analysis, per_type_limit
        )

    def analysis_telephony_sms(self, per_type_limit: int = 100) -> dict:
        """电话短信滥用审计（发/读短信、拨号、短信拦截、通话监听，扣费/拦截马特征）。"""
        self._ensure_loaded()
        return analysis_skills.analysis_telephony_sms(
            self._analysis, per_type_limit
        )

    def analysis_dynamic_code(self, per_type_limit: int = 100) -> dict:
        """动态代码加载审计（DexClassLoader/native 库/反射加载，脱壳/恶意 payload）。"""
        self._ensure_loaded()
        return analysis_skills.analysis_dynamic_code(
            self._analysis, per_type_limit
        )

    def analysis_persistence(self, per_type_limit: int = 100) -> dict:
        """持久化/后台驻留审计（设备管理员/无障碍/定时任务/前台服务/通知监听）。"""
        self._ensure_loaded()
        return analysis_skills.analysis_persistence(
            self._analysis, per_type_limit
        )

    def analysis_weak_random(self, per_type_limit: int = 100) -> dict:
        """不安全随机数审计（java.util.Random/Math.random/固定种子 vs SecureRandom，OWASP M10）。"""
        self._ensure_loaded()
        return analysis_skills.analysis_weak_random(
            self._analysis, per_type_limit
        )

    def analysis_broadcast_safety(self, per_type_limit: int = 100) -> dict:
        """广播收发安全审计（无权限广播/动态 receiver/粘性广播，组件间通信劫持面）。"""
        self._ensure_loaded()
        return analysis_skills.analysis_broadcast_safety(
            self._analysis, per_type_limit
        )

    def analysis_provider_safety(self, per_type_limit: int = 100) -> dict:
        """ContentProvider 安全审计（openFile 路径穿越/URI 权限授予/跨应用访问）。"""
        self._ensure_loaded()
        return analysis_skills.analysis_provider_safety(
            self._analysis, per_type_limit
        )

    def analysis_anti_analysis(self, per_type_limit: int = 100) -> dict:
        """反分析/加固对抗侦察（root/模拟器/调试器/Frida/Xposed 检测，字符串+API 双路）。"""
        self._ensure_loaded()
        return analysis_skills.analysis_anti_analysis(
            self._analysis, per_type_limit
        )

    def analysis_network_security(self, per_type_limit: int = 100) -> dict:
        """网络安全配置审计（明文 URL/证书固定/SSL 上下文/HTTP 客户端，通信安全总览）。"""
        self._ensure_loaded()
        return analysis_skills.analysis_network_security(
            self._analysis, per_type_limit
        )

    def analysis_obfuscation_metrics(self) -> dict:
        """混淆度量（类名长度分布/反射密度/字符串覆盖，量化混淆/加固程度）。"""
        self._ensure_loaded()
        return analysis_skills.analysis_obfuscation_metrics(self._analysis)

    def apk_security_report(self, per_type_limit: int = 20) -> dict:
        """一键全量安全报告（聚合全部专项审计 + 综合风险评分，漏洞审计套件闭环入口）。"""
        self._ensure_loaded()
        return analysis_skills.apk_security_report(
            self._apk, self._analysis, self._dex_list, per_type_limit
        )

    def analysis_class_fields_xref(
        self, class_name: str, xref_limit: int = 20
    ) -> dict:
        """类内所有字段的完整读写交叉引用（哪些方法读/写每个字段）。"""
        self._ensure_loaded()
        return analysis_skills.analysis_class_fields_xref(
            self._analysis, class_name, xref_limit
        )

    def analysis_hardcoded_secrets(self, limit: int = 100) -> dict:
        """扫描所有类 static-values 检测硬编码敏感字符串（密钥/令牌/URL/私钥）。"""
        self._ensure_loaded()
        return analysis_skills.analysis_hardcoded_secrets(
            self._analysis, self._dex_list, limit
        )

    def analysis_get_method(
        self, class_name: str, method_name: str, descriptor: str
    ) -> dict:
        """
        按 class+method+descriptor 获取底层 EncodedMethod 元数据。

        :param class_name: 类名
        :param method_name: 方法名
        :param descriptor: 方法描述符
        """
        self._ensure_loaded()
        return analysis_skills.analysis_get_method(
            self._analysis, class_name, method_name, descriptor
        )

    # ================================================================
    # 反编译
    # ================================================================

    def decompile_class(self, class_name: str) -> dict:
        """
        反编译指定类。

        :param class_name: 类名（格式如 Lcom/example/MyClass;）
        """
        self._ensure_loaded()
        return decompiler_skills.decompile_class(
            self._dex_list, self._analysis, class_name
        )

    def decompile_method(self, class_name: str, method_name: str) -> dict:
        """
        反编译指定方法。

        :param class_name: 类名
        :param method_name: 方法名
        """
        self._ensure_loaded()
        return decompiler_skills.decompile_method(
            self._dex_list, self._analysis, class_name, method_name
        )

    def decompile_method_ast(self, class_name: str, method_name: str) -> dict:
        """
        反编译方法并返回结构化 AST。

        :param class_name: 类名
        :param method_name: 方法名
        """
        self._ensure_loaded()
        return decompiler_skills.decompile_method_ast(
            self._dex_list, self._analysis, class_name, method_name
        )

    def decompile_method_tokens(
        self, class_name: str, method_name: str, limit: int = None
    ) -> dict:
        """
        反编译方法并返回 token 流。

        :param class_name: 类名
        :param method_name: 方法名
        :param limit: token 数量限制
        """
        self._ensure_loaded()
        return decompiler_skills.decompile_method_tokens(
            self._dex_list, self._analysis, class_name, method_name, limit
        )

    def decompile_class_ast(
        self,
        class_name: str,
        fields_limit: int = None,
        methods_limit: int = None,
    ) -> dict:
        """
        反编译类并返回类级结构化 AST（含所有方法和字段）。

        :param class_name: 类名
        :param fields_limit: 返回字段 AST 数量上限（None=全部）
        :param methods_limit: 返回方法 AST 数量上限（None=全部）
        """
        self._ensure_loaded()
        return decompiler_skills.decompile_class_ast(
            self._dex_list,
            self._analysis,
            class_name,
            fields_limit,
            methods_limit,
        )

    def decompile_class_tokens(
        self, class_name: str, limit: int = None
    ) -> dict:
        """
        反编译类并返回类级 token 流（结构化词法表示）。

        :param class_name: 类名
        :param limit: 返回顶层 token 数量上限（None=全部）
        """
        self._ensure_loaded()
        return decompiler_skills.decompile_class_tokens(
            self._dex_list,
            self._analysis,
            class_name,
            limit,
        )

    # ================================================================
    # 动态分析
    # ================================================================

    def pentest_trace(self, apk: str, modules: list) -> dict:
        """
        使用 Frida 追踪 APK 方法调用。

        :param apk: APK 文件路径
        :param modules: Frida 模块列表
        """
        return pentest_skills.pentest_trace(apk, modules)

    def pentest_dump(self, package: str, modules: list = None) -> dict:
        """
        内存 Dump 已安装应用的 DEX。

        :param package: 应用包名
        :param modules: Frida 模块列表（可选）
        """
        return pentest_skills.pentest_dump(package, modules)

    # ================================================================
    # 资源解析
    # ================================================================

    def _get_arsc(self):
        """获取 ARSCParser 对象"""
        self._ensure_loaded()
        arsc = self._apk.get_android_resources()
        if arsc is None:
            raise RuntimeError("No ARSC resources found in APK")
        return arsc

    def resource_packages(self) -> dict:
        """获取资源包名列表"""
        try:
            arsc = self._get_arsc()
            return resource_skills.resource_packages(arsc)
        except RuntimeError as e:
            return {"error": str(e)}

    def resource_locales(self, package: str) -> dict:
        """
        获取指定资源包支持的语言/地区列表。

        :param package: 资源包名
        """
        try:
            arsc = self._get_arsc()
            return resource_skills.resource_locales(arsc, package)
        except RuntimeError as e:
            return {"error": str(e)}

    def resource_types(self, package: str) -> dict:
        """
        获取指定资源包的资源类型列表。

        :param package: 资源包名
        """
        try:
            arsc = self._get_arsc()
            return resource_skills.resource_types(arsc, package)
        except RuntimeError as e:
            return {"error": str(e)}

    def resource_configs(self, resource_id: int) -> dict:
        """
        获取指定资源 ID 的所有配置。

        :param resource_id: 资源 ID（如 0x7f030000）
        """
        try:
            arsc = self._get_arsc()
            return resource_skills.resource_configs(arsc, resource_id)
        except RuntimeError as e:
            return {"error": str(e)}

    def resource_strings(self) -> dict:
        """获取所有解析后的字符串资源"""
        try:
            arsc = self._get_arsc()
            return resource_skills.resource_strings(arsc)
        except RuntimeError as e:
            return {"error": str(e)}

    def resource_bool(self, package: str, locale: str = "\x00\x00") -> dict:
        """
        获取布尔类型资源。

        :param package: 资源包名
        :param locale: 语言（可选，默认 "\x00\x00"）
        """
        try:
            arsc = self._get_arsc()
            return resource_skills.resource_bool(arsc, package, locale)
        except RuntimeError as e:
            return {"error": str(e)}

    def resource_color(self, package: str, locale: str = "\x00\x00") -> dict:
        """
        获取颜色类型资源。

        :param package: 资源包名
        :param locale: 语言（可选）
        """
        try:
            arsc = self._get_arsc()
            return resource_skills.resource_color(arsc, package, locale)
        except RuntimeError as e:
            return {"error": str(e)}

    def resource_dimen(self, package: str, locale: str = "\x00\x00") -> dict:
        """
        获取尺寸类型资源。

        :param package: 资源包名
        :param locale: 语言（可选）
        """
        try:
            arsc = self._get_arsc()
            return resource_skills.resource_dimen(arsc, package, locale)
        except RuntimeError as e:
            return {"error": str(e)}

    def resource_integer(self, package: str, locale: str = "\x00\x00") -> dict:
        """
        获取整数类型资源。

        :param package: 资源包名
        :param locale: 语言（可选）
        """
        try:
            arsc = self._get_arsc()
            return resource_skills.resource_integer(arsc, package, locale)
        except RuntimeError as e:
            return {"error": str(e)}

    def resource_id(
        self,
        package: str,
        resource_id: int = None,
        resource_type: str = None,
        key: str = None,
        locale: str = "\x00\x00",
    ) -> dict:
        """
        资源 ID 双向查询。

        :param package: 资源包名
        :param resource_id: 资源 ID（ID→名称查询）
        :param resource_type: 资源类型（名称→ID 查询）
        :param key: 资源键名
        :param locale: 语言（可选）
        """
        try:
            arsc = self._get_arsc()
            return resource_skills.resource_id(
                arsc, package, resource_id, resource_type, key, locale
            )
        except RuntimeError as e:
            return {"error": str(e)}

    # ================================================================
    # 可视化
    # ================================================================

    def _get_method_analysis(self, class_name: str, method_name: str):
        """获取 MethodAnalysis 对象"""
        self._ensure_loaded()
        class_analysis = self._analysis.get_class_analysis(class_name)
        if class_analysis is None:
            return None
        for ma in class_analysis.get_methods():
            if ma.name == method_name:
                return ma
        return None

    def visualize_method_dot(self, class_name: str, method_name: str) -> dict:
        """
        导出方法的控制流图为 DOT 格式。

        :param class_name: 类名
        :param method_name: 方法名
        """
        ma = self._get_method_analysis(class_name, method_name)
        if ma is None:
            return {
                "class": class_name,
                "method": method_name,
                "error": "Method not found",
            }
        return visualize_skills.visualize_method_dot(ma)

    def visualize_method_image(
        self, class_name: str, method_name: str, output: str, fmt: str = "png"
    ) -> dict:
        """
        导出方法的控制流图为图片。

        :param class_name: 类名
        :param method_name: 方法名
        :param output: 输出文件路径
        :param fmt: 输出格式（png, jpg）
        """
        ma = self._get_method_analysis(class_name, method_name)
        if ma is None:
            return {
                "class": class_name,
                "method": method_name,
                "error": "Method not found",
            }
        return visualize_skills.visualize_method_image(ma, output, fmt)

    def visualize_method_json(self, class_name: str, method_name: str) -> dict:
        """
        导出方法的控制流图为 JSON 格式。

        :param class_name: 类名
        :param method_name: 方法名
        """
        ma = self._get_method_analysis(class_name, method_name)
        if ma is None:
            return {
                "class": class_name,
                "method": method_name,
                "error": "Method not found",
            }
        return visualize_skills.visualize_method_json(ma)

    # ================================================================
    # 第四轮：APK 签名/证书/文件能力
    # ================================================================

    def apk_signing_versions(self) -> dict:
        """检测 APK 支持的签名方案（v1/v2/v3/v3.1）"""
        self._ensure_loaded()
        return apk_skills.apk_signing_versions(self._apk)

    def apk_certificates_scheme(self, scheme: str = "v3") -> dict:
        """
        按签名方案批量获取证书详情。

        :param scheme: 签名方案（v1/v2/v3/v31）
        """
        self._ensure_loaded()
        return apk_skills.apk_certificates_scheme(self._apk, scheme)

    def apk_certificates_der(self, scheme: str = "v3") -> dict:
        """
        按签名方案获取证书 DER 二进制（base64）。

        :param scheme: 签名方案（v2/v3/v31）
        """
        self._ensure_loaded()
        return apk_skills.apk_certificates_der(self._apk, scheme)

    def apk_public_keys(self, scheme: str = "v3") -> dict:
        """
        按签名方案获取签名公钥信息。

        :param scheme: 签名方案（v2/v3/v31）
        """
        self._ensure_loaded()
        return apk_skills.apk_public_keys(self._apk, scheme)

    def apk_signature_files(self) -> dict:
        """获取 APK 签名文件信息（文件名 + 原始签名数据 base64）"""
        self._ensure_loaded()
        return apk_skills.apk_signature_files(self._apk)

    def apk_files_crc32(self) -> dict:
        """获取 APK 中所有文件的 CRC32 校验值"""
        self._ensure_loaded()
        return apk_skills.apk_files_crc32(self._apk)

    # ================================================================
    # 第五轮：APK 指纹 / AXML 加固检测 / 工具能力
    # ================================================================

    def apk_fingerprint(self, scheme: str = "v3") -> dict:
        """
        计算签名公钥的 SHA-256 指纹。

        :param scheme: 签名方案（v2/v3/v31，用于取公钥）
        """
        self._ensure_loaded()
        return apk_skills.apk_fingerprint(self._apk, scheme)

    def apk_manifest_axml(self) -> dict:
        """
        分析 AndroidManifest.xml 的 AXML 结构（加固检测 / 根标签属性）。
        """
        self._ensure_loaded()
        return apk_skills.apk_manifest_axml(self._apk)

    def apk_axml(self, filename: str, pretty: bool = True) -> dict:
        """
        解析 APK 内任意二进制 AXML 文件为可读 XML。

        :param filename: APK 内文件路径（如 res/layout/main.xml）
        :param pretty: 是否美化输出
        """
        self._ensure_loaded()
        return apk_skills.apk_axml(self._apk, filename, pretty)

    # ================================================================
    # 第五轮：工具能力（androguard.util / androconf）
    # ================================================================

    def util_detect_file(self, filename: str) -> dict:
        """
        检测文件的 Android 类型（APK/DEX/ODEX/ELF 等）。

        :param filename: 文件路径
        """
        return util_skills.util_detect_file(filename)

    def util_detect_raw(self, data: bytes) -> dict:
        """
        检测原始字节的 Android 类型。

        :param data: 原始字节（base64 解码后）
        """
        return util_skills.util_detect_raw(data)

    def util_permissions(self, apilevel: int) -> dict:
        """
        加载指定 API level 的 AOSP 权限定义。

        :param apilevel: API level（如 35）
        """
        return util_skills.util_permissions(apilevel)

    def util_permission_mappings(self, apilevel: int) -> dict:
        """
        加载指定 API level 的方法签名 → 权限映射。

        :param apilevel: API level（如 23）
        """
        return util_skills.util_permission_mappings(apilevel)

    def util_available_api_levels(self) -> dict:
        """列出本地可用的权限数据 API level。"""
        return util_skills.util_available_api_levels()

    def util_format(self, value: str, to: str = "java") -> dict:
        """
        Dalvik/Java/Python 类名与描述符格式转换。

        :param value: 待转换的类名/描述符
        :param to: 目标格式（java/dalvik/python，默认 java）
        """
        return util_skills.util_format(value, to)

    # ================================================================
    # 第五轮：Session 会话能力（多 APK/DEX 关联分析）
    # ================================================================

    def session_analyze_apk(self, apk_path: str) -> dict:
        """
        用 Session 完整分析一个 APK（独立加载路径，与 load_apk 互不影响）。

        :param apk_path: APK 文件路径
        """
        return session_skills.session_analyze_apk(apk_path)

    def session_create(self) -> dict:
        """创建一个新的 Session 并持有（供后续 session 命令复用）。"""
        result = session_skills.session_create()
        try:
            from androguard.misc import Session

            self._session = Session()
            # 返回真实持有的 Session 的 is_open（此前 session_skills 内部
            # 创建的 Session 被丢弃，is_open 反映的是不相干实例）
            result["is_open"] = self._session.isOpen()
        except Exception as e:
            self._session = None
            result["error"] = str(e)
        return result

    def _ensure_session(self):
        """确保已创建 Session，否则抛异常。"""
        if self._session is None:
            raise RuntimeError(
                "No Session created. Call 'session create' first."
            )

    def session_add_apk(self, apk_path: str) -> dict:
        """向当前 Session 添加 APK（从文件读取字节）。"""
        self._ensure_session()
        import os

        if not os.path.exists(apk_path):
            raise RuntimeError(f"File not found: {apk_path}")
        with open(apk_path, "rb") as f:
            data = f.read()
        return session_skills.session_add_apk(self._session, apk_path, data)

    def session_add_dex(self, dex_path: str) -> dict:
        """向当前 Session 添加独立 DEX（从文件读取字节）。"""
        self._ensure_session()
        import os

        if not os.path.exists(dex_path):
            raise RuntimeError(f"File not found: {dex_path}")
        with open(dex_path, "rb") as f:
            data = f.read()
        return session_skills.session_add_dex(self._session, dex_path, data)

    def session_info(self) -> dict:
        """获取当前 Session 概要（APK/DEX 计数 + 字符串数）。"""
        self._ensure_session()
        return session_skills.session_info(self._session)

    def session_filename_by_class(self, class_name: str) -> dict:
        """查询类在 Session 中所属的文件名/摘要（多 APK/DEX 关联定位）。"""
        self._ensure_session()
        return session_skills.session_filename_by_class(
            self._session, class_name
        )

    def session_strings(self, limit: int = None) -> dict:
        """获取 Session 各 DEX 的字符串分析（跨文件字符串统计）。"""
        self._ensure_session()
        return session_skills.session_strings(self._session, limit)

    def session_classes(self, limit: int = None) -> dict:
        """获取 Session 中所有类（按 DEX 分组）。"""
        self._ensure_session()
        return session_skills.session_classes(self._session, limit)

    # ================================================================
    # 第六轮：APK 权限分类 / SDK 版本 / 设备特性
    # ================================================================

    def apk_declared_permissions(self) -> dict:
        """获取 APK 声明（自定义）的权限。"""
        self._ensure_loaded()
        return apk_skills.apk_declared_permissions(self._apk)

    def apk_requested_permissions(self) -> dict:
        """获取 APK 请求的权限分类（AOSP/第三方/隐含）。"""
        self._ensure_loaded()
        return apk_skills.apk_requested_permissions(self._apk)

    def apk_sdk_versions(self) -> dict:
        """获取 APK 的 SDK 版本信息（min/max/target/effective_target）。"""
        self._ensure_loaded()
        return apk_skills.apk_sdk_versions(self._apk)

    def apk_main_activities(self) -> dict:
        """获取 APK 的主 Activity（含别名 aliases）。"""
        self._ensure_loaded()
        return apk_skills.apk_main_activities(self._apk)

    def apk_device_features(self) -> dict:
        """获取 APK 的设备特性布尔标记（TV/Wearable/Leanback/Multidex）。"""
        self._ensure_loaded()
        return apk_skills.apk_device_features(self._apk)

    def apk_files_types(self) -> dict:
        """获取 APK 中所有文件的类型识别结果。"""
        self._ensure_loaded()
        return apk_skills.apk_files_types(self._apk)

    # ================================================================
    # 第七轮：APK 权限详情
    # ================================================================

    def apk_details_permissions(self) -> dict:
        """获取 APK 请求权限的详细信息（protection_level/label/description）。"""
        self._ensure_loaded()
        return apk_skills.apk_details_permissions(self._apk)

    # ================================================================
    # 第八轮：APK manifest 标签树 / 证书名规范化
    # ================================================================

    def apk_manifest_tree(self) -> dict:
        """获取 AndroidManifest.xml 的标签树统计（标签计数 + 属性概览）。"""
        self._ensure_loaded()
        return apk_skills.apk_manifest_tree(self._apk)

    def apk_find_tags_xml(
        self, xml_name: str, tag_name: str, filter_kwargs: dict = None
    ) -> dict:
        """
        从 APK 中指定 XML 文件查找标签。

        :param xml_name: APK 内的 XML 文件名
        :param tag_name: 标签名
        :param filter_kwargs: 属性过滤条件字典
        """
        self._ensure_loaded()
        return apk_skills.apk_find_tags_xml(
            self._apk, xml_name, tag_name, **(filter_kwargs or {})
        )

    def apk_cert_names(self, scheme: str = "v3", android: bool = True) -> dict:
        """
        获取签名证书主题/颁发者的规范化名称。

        :param scheme: 签名方案（v1/v2/v3/v31）
        :param android: 是否使用 Android 风格规范化
        """
        self._ensure_loaded()
        return apk_skills.apk_cert_names(self._apk, scheme, android)

    # ================================================================
    # 第九轮：APK 资源 ID 反解
    # ================================================================

    def apk_res_value(self, name: str) -> dict:
        """
        将资源 ID（如 @7F080001）解析为字面值。

        :param name: 资源 ID（如 @7F080001，无 @ 前缀自动补）
        """
        self._ensure_loaded()
        return apk_skills.apk_res_value(self._apk, name)

    # ================================================================
    # 第十轮：APK 元信息补充
    # ================================================================

    def apk_dex_names(self) -> dict:
        """获取 APK 内所有 DEX 文件名列表（multidex）。"""
        self._ensure_loaded()
        return apk_skills.apk_dex_names(self._apk)

    def apk_signature_names(self) -> dict:
        """获取所有签名文件名列表。"""
        self._ensure_loaded()
        return apk_skills.apk_signature_names(self._apk)

    def apk_app_name(self, locale: str = None) -> dict:
        """
        获取应用显示名。

        :param locale: 语言区域（如 zh、en）
        """
        self._ensure_loaded()
        return apk_skills.apk_app_name(self._apk, locale)

    def apk_valid(self) -> dict:
        """检查 APK 结构有效性。"""
        self._ensure_loaded()
        return apk_skills.apk_valid(self._apk)

    def apk_duplicate_signatures(self) -> dict:
        """检测是否存在重复签名 ID。"""
        self._ensure_loaded()
        return apk_skills.apk_duplicate_signatures(self._apk)

    def apk_security_overview(self) -> dict:
        """APK 安全概览（聚合签名/权限/组件/manifest 标志/加固等安全信号）。"""
        self._ensure_loaded()
        return apk_skills.apk_security_overview(self._apk)

    def apk_native_libraries(self, include_data: bool = False) -> dict:
        """APK 中的 native 库（lib/<abi>/*.so）列表，按 ABI 分组。"""
        self._ensure_loaded()
        return apk_skills.apk_native_libraries(self._apk, include_data)

    def apk_application_flags(self) -> dict:
        """Manifest <application> 安全属性审计（默认值推断 + 风险评级）。"""
        self._ensure_loaded()
        return apk_skills.apk_application_flags(self._apk)

    def apk_component_details(self) -> dict:
        """所有组件（Activity/Service/Receiver/Provider）的安全属性详情 + 暴露风险标记。"""
        self._ensure_loaded()
        return apk_skills.apk_component_details(self._apk)

    # ================================================================
    # 第四轮：DEX 底层 item/encoded 能力
    # ================================================================

    def dex_encoded_fields(
        self, class_name: str = None, limit: int = None
    ) -> dict:
        """
        获取 DEX 全部 EncodedField（底层字段表）。

        :param class_name: 限定某个类（可选）
        :param limit: 返回数量限制
        """
        self._ensure_loaded()
        return dex_skills.dex_encoded_fields(self._dex_list, class_name, limit)

    def dex_encoded_methods(
        self, class_name: str = None, limit: int = None
    ) -> dict:
        """
        获取 DEX 全部 EncodedMethod（底层方法表）。

        :param class_name: 限定某个类（可选）
        :param limit: 返回数量限制
        """
        self._ensure_loaded()
        return dex_skills.dex_encoded_methods(
            self._dex_list, class_name, limit
        )

    def dex_encoded_method(self, method_name: str) -> dict:
        """
        按方法名查找 EncodedMethod（跨类，返回所有同名方法）。

        :param method_name: 方法名
        """
        self._ensure_loaded()
        return dex_skills.dex_encoded_method(self._dex_list, method_name)

    def dex_encoded_method_descriptor(
        self, class_name: str, method_name: str, descriptor: str
    ) -> dict:
        """
        按 class+method+descriptor 精确查找 EncodedMethod。

        :param class_name: 类名
        :param method_name: 方法名
        :param descriptor: 方法描述符
        """
        self._ensure_loaded()
        return dex_skills.dex_encoded_method_descriptor(
            self._dex_list, class_name, method_name, descriptor
        )

    def dex_cm_lookup(self, idx: int, kind: str = "string") -> dict:
        """
        按 ID 查询 ClassManager 常量池表。

        :param idx: 常量池索引
        :param kind: 查询类型（string/method/field/type）
        """
        self._ensure_loaded()
        return dex_skills.dex_cm_lookup(self._dex_list, idx, kind)

    def dex_fields_id(self, limit: int = None) -> dict:
        """
        获取 DEX 字段索引表（FieldIdItem）。

        :param limit: 返回数量限制
        """
        self._ensure_loaded()
        return dex_skills.dex_fields_id(self._dex_list, limit)

    def dex_version(self) -> dict:
        """获取 DEX 版本号"""
        self._ensure_loaded()
        return dex_skills.dex_version(self._dex_list)

    # ================================================================
    # 第六轮：DEX 底层 item 表与计数
    # ================================================================

    def dex_items(self) -> dict:
        """获取 DEX 底层 item 表信息（header/codes/string_data/fields_id/methods_id/classes_def）。"""
        self._ensure_loaded()
        return dex_skills.dex_items(self._dex_list)

    def dex_lens(self) -> dict:
        """获取 DEX 各表长度（classes/methods/strings/fields/encoded_*）。"""
        self._ensure_loaded()
        return dex_skills.dex_lens(self._dex_list)

    def dex_class_manager(self) -> dict:
        """获取 DEX 的 ClassManager 概要信息。"""
        self._ensure_loaded()
        return dex_skills.dex_class_manager(self._dex_list)

    # ================================================================
    # 第七轮：DEX 按类 / 按 idx 的 encoded 查询
    # ================================================================

    def dex_encoded_fields_class(
        self, class_name: str, limit: int = None
    ) -> dict:
        """获取指定类的全部 EncodedField（按类过滤）。"""
        self._ensure_loaded()
        return dex_skills.dex_encoded_fields_class(
            self._dex_list, class_name, limit
        )

    def dex_encoded_methods_class(
        self, class_name: str, limit: int = None
    ) -> dict:
        """获取指定类的全部 EncodedMethod（按类过滤）。"""
        self._ensure_loaded()
        return dex_skills.dex_encoded_methods_class(
            self._dex_list, class_name, limit
        )

    def dex_encoded_method_by_idx(self, idx: int) -> dict:
        """按 DEX 方法索引获取 EncodedMethod。"""
        self._ensure_loaded()
        return dex_skills.dex_encoded_method_by_idx(self._dex_list, idx)

    def dex_encoded_field_by_name(self, name: str, limit: int = None) -> dict:
        """按字段名获取 EncodedField（跨类）。"""
        self._ensure_loaded()
        return dex_skills.dex_encoded_field_by_name(
            self._dex_list, name, limit
        )

    def dex_encoded_field_descriptor(
        self, class_name: str, field_name: str, descriptor: str
    ) -> dict:
        """
        按 class+field+descriptor 精确查 EncodedField。

        :param class_name: 类名
        :param field_name: 字段名
        :param descriptor: 字段描述符
        """
        self._ensure_loaded()
        return dex_skills.dex_encoded_field_descriptor(
            self._dex_list, class_name, field_name, descriptor
        )

    # ================================================================
    # 第十六轮：方法寄存器/指令信息
    # ================================================================

    def dex_method_info(self, class_name: str, method_name: str) -> dict:
        """
        获取方法的寄存器/参数映射等签名级元信息。

        :param class_name: 类名
        :param method_name: 方法名
        """
        self._ensure_loaded()
        return dex_skills.dex_method_info(
            self._dex_list, class_name, method_name
        )

    def dex_method_instructions(
        self, class_name: str, method_name: str, limit: int = None
    ) -> dict:
        """
        按方法反汇编所有 Dalvik 指令（指令流）。

        :param class_name: 类名
        :param method_name: 方法名
        :param limit: 返回指令数量上限
        """
        self._ensure_loaded()
        return dex_skills.dex_method_instructions(
            self._dex_list, class_name, method_name, limit
        )

    def dex_method_code(self, class_name: str, method_name: str) -> dict:
        """
        获取方法 DalvikCode 的底层信息（寄存器帧 + try/catch 异常表 + handlers）。

        :param class_name: 类名
        :param method_name: 方法名
        """
        self._ensure_loaded()
        return dex_skills.dex_method_code(
            self._dex_list, class_name, method_name
        )

    def dex_class_meta(self, class_name: str) -> dict:
        """
        获取 ClassDefItem 底层元信息（注解/源文件/接口/父类/各表偏移）。

        :param class_name: 类名
        """
        self._ensure_loaded()
        return dex_skills.dex_class_meta(self._dex_list, class_name)

    def dex_class_data(self, class_name: str, limit: int = None) -> dict:
        """
        获取类的 ClassDataItem 分类视图（direct/virtual 方法 + static/instance 字段）。

        :param class_name: 类名
        :param limit: 每类列表返回上限
        """
        self._ensure_loaded()
        return dex_skills.dex_class_data(self._dex_list, class_name, limit)

    def dex_field_init_value(self, class_name: str, field_name: str) -> dict:
        """
        获取字段的初始值（硬编码常量检测）。

        :param class_name: 类名
        :param field_name: 字段名
        """
        self._ensure_loaded()
        return dex_skills.dex_field_init_value(
            self._dex_list, class_name, field_name
        )

    def dex_method_instructions_idx(
        self, class_name: str, method_name: str, limit: int = None
    ) -> dict:
        """
        按方法反汇编所有指令，带字节偏移 idx。

        :param class_name: 类名
        :param method_name: 方法名
        :param limit: 返回指令数量上限
        """
        self._ensure_loaded()
        return dex_skills.dex_method_instructions_idx(
            self._dex_list, class_name, method_name, limit
        )

    def dex_proto_ids(self, limit: int = None) -> dict:
        """DEX 方法原型表（ProtoIdItem：shorty/return_type/parameters）。"""
        self._ensure_loaded()
        return dex_skills.dex_proto_ids(self._dex_list, limit)

    def dex_type_ids(self, limit: int = None) -> dict:
        """DEX 类型常量池表（type_ids：descriptor_idx → 类型描述符）。"""
        self._ensure_loaded()
        return dex_skills.dex_type_ids(self._dex_list, limit)

    def dex_annotations(
        self, class_name: str = None, limit: int = None
    ) -> dict:
        """DEX 注解目录（类/字段/方法/参数注解，含 visibility/type/elements）。"""
        self._ensure_loaded()
        return dex_skills.dex_annotations(self._dex_list, class_name, limit)

    def dex_static_values(self, class_name: str) -> dict:
        """类静态值数组（EncodedArray：所有 static 字段初始值，硬编码常量批量检测）。"""
        self._ensure_loaded()
        return dex_skills.dex_static_values(self._dex_list, class_name)

    # ================================================================
    # 第十轮：DEX 常量池按名查询 + 类内按名查方法
    # ================================================================

    def dex_method_id_by_name(self, name: str, limit: int = None) -> dict:
        """
        在常量池 method_ids 表按方法名搜索（含外部引用）。

        :param name: 方法名
        :param limit: 每 DEX 返回上限
        """
        self._ensure_loaded()
        return dex_skills.dex_method_id_by_name(self._dex_list, name, limit)

    def dex_method_ids(self, limit: int = None) -> dict:
        """
        常量池 method_ids 全量表（含外部引用，无 code_off）。

        :param limit: 每 DEX 返回上限
        """
        self._ensure_loaded()
        return dex_skills.dex_method_ids(self._dex_list, limit)

    def dex_field_id_by_name(self, name: str, limit: int = None) -> dict:
        """
        常量池 field_ids 表按字段名搜索（含外部引用）。

        :param name: 字段名
        :param limit: 每 DEX 返回上限
        """
        self._ensure_loaded()
        return dex_skills.dex_field_id_by_name(self._dex_list, name, limit)

    def dex_encoded_method_class_method(
        self, class_name: str, method_name: str
    ) -> dict:
        """
        类内按方法名查 EncodedMethod（无需 descriptor）。

        :param class_name: 类名
        :param method_name: 方法名
        """
        self._ensure_loaded()
        return dex_skills.dex_encoded_method_class_method(
            self._dex_list, class_name, method_name
        )

    # ================================================================
    # 第四轮：Analysis 字段/API 能力
    # ================================================================

    def analysis_find_fields_advanced(
        self,
        classname: str = ".*",
        fieldname: str = ".*",
        fieldtype: str = ".*",
        accessflags: str = ".*",
        limit: int = None,
        with_xrefs: bool = False,
    ) -> dict:
        """
        多维正则字段查找（原生 find_fields）。

        :param classname: 类名正则
        :param fieldname: 字段名正则
        :param fieldtype: 字段类型正则
        :param accessflags: 访问标志正则
        :param limit: 返回数量限制
        :param with_xrefs: 是否展开完整 xref 列表
        """
        self._ensure_loaded()
        return analysis_skills.analysis_find_fields_advanced(
            self._analysis,
            classname,
            fieldname,
            fieldtype,
            accessflags,
            limit,
            with_xrefs,
        )

    def analysis_field_analysis(
        self, class_name: str, field_name: str
    ) -> dict:
        """
        获取指定字段的完整分析（含 read/write xref 详情）。

        :param class_name: 类名
        :param field_name: 字段名
        """
        self._ensure_loaded()
        return analysis_skills.analysis_field_analysis(
            self._analysis, class_name, field_name
        )

    # ================================================================
    # 第五轮：Analysis 类/方法/字符串遗漏能力
    # ================================================================

    def analysis_class_hierarchy_info(self, class_name: str) -> dict:
        """
        获取类的继承信息（extends / implements）。

        :param class_name: 类名
        """
        self._ensure_loaded()
        return analysis_skills.analysis_class_hierarchy_info(
            self._analysis, class_name
        )

    def analysis_class_xref_new_instance(self, class_name: str) -> dict:
        """
        获取类的 new-instance 交叉引用（何处实例化此类）。

        :param class_name: 类名
        """
        self._ensure_loaded()
        return analysis_skills.analysis_class_xref_new_instance(
            self._analysis, class_name
        )

    def analysis_class_xref_const_class(self, class_name: str) -> dict:
        """
        获取类的 const-class 交叉引用（何处引用此类字面量）。

        :param class_name: 类名
        """
        self._ensure_loaded()
        return analysis_skills.analysis_class_xref_const_class(
            self._analysis, class_name
        )

    def analysis_class_detail(self, class_name: str) -> dict:
        """
        获取类的综合信息（方法数/继承/接口/xref 统计/vm_class 类型）。

        :param class_name: 类名
        """
        self._ensure_loaded()
        return analysis_skills.analysis_class_detail(
            self._analysis, class_name
        )

    def analysis_method_basic_blocks(
        self, class_name: str, method_name: str, descriptor: str
    ) -> dict:
        """
        获取方法的基本块（CFG 节点）列表。

        :param class_name: 类名
        :param method_name: 方法名
        :param descriptor: 描述符（如 ()V）
        """
        self._ensure_loaded()
        return analysis_skills.analysis_method_basic_blocks(
            self._analysis, class_name, method_name, descriptor
        )

    def analysis_method_exceptions(
        self, class_name: str, method_name: str, descriptor: str
    ) -> dict:
        """
        获取方法的 try/catch 异常处理表。

        :param class_name: 类名
        :param method_name: 方法名
        :param descriptor: 描述符（如 ()V）
        """
        self._ensure_loaded()
        return analysis_skills.analysis_method_exceptions(
            self._analysis, class_name, method_name, descriptor
        )

    def analysis_method_detail(
        self, class_name: str, method_name: str, descriptor: str
    ) -> dict:
        """
        获取方法的综合信息（full_name/access/长度/xref 统计/基本块数）。

        :param class_name: 类名
        :param method_name: 方法名
        :param descriptor: 描述符（如 ()V）
        """
        self._ensure_loaded()
        return analysis_skills.analysis_method_detail(
            self._analysis, class_name, method_name, descriptor
        )

    def analysis_method_api_info(
        self, class_name: str, method_name: str, descriptor: str
    ) -> dict:
        """
        查询方法的 API/权限标注属性（is_android_api/is_external/domain_flag/
        restriction_flag/apilist）。

        :param class_name: 类名
        :param method_name: 方法名
        :param descriptor: 描述符（如 ()V）
        """
        self._ensure_loaded()
        return analysis_skills.analysis_method_api_info(
            self._analysis, class_name, method_name, descriptor
        )

    def analysis_android_api_usage(
        self, limit: int = None, with_xrefs: bool = False
    ) -> dict:
        """
        批量列出 APK 使用的所有 Android 平台 API 方法。

        :param limit: 返回数量上限
        :param with_xrefs: 是否展开每个 API 的调用方
        """
        self._ensure_loaded()
        return analysis_skills.analysis_android_api_usage(
            self._analysis, limit, with_xrefs
        )

    def analysis_method_xrefs_detail(
        self, class_name: str, method_name: str, descriptor: str
    ) -> dict:
        """
        获取方法级 xref 完整引用列表（6 类：from/to/read/write/new_instance/const_class）。

        :param class_name: 类名
        :param method_name: 方法名
        :param descriptor: 描述符（如 (Landroid/os/Bundle;)V）
        """
        self._ensure_loaded()
        return analysis_skills.analysis_method_xrefs_detail(
            self._analysis, class_name, method_name, descriptor
        )

    def analysis_strings_overwritten(self) -> dict:
        """获取被覆盖的字符串（is_overwritten / get_orig_value）。"""
        self._ensure_loaded()
        return analysis_skills.analysis_strings_overwritten(self._analysis)

    def analysis_string_info(self, value: str, xref_limit: int = None) -> dict:
        """
        按精确字符串值查询单个字符串的完整分析详情（原始值/当前值/是否覆盖 + xref）。

        :param value: 字符串精确值
        :param xref_limit: xref_from 引用返回上限
        """
        self._ensure_loaded()
        return analysis_skills.analysis_string_info(
            self._analysis, value, xref_limit
        )

    def analysis_class_fields(
        self, class_name: str, limit: int = None
    ) -> dict:
        """
        列出指定类的全部字段及其交叉引用统计（类级字段视图）。

        :param class_name: 类名
        :param limit: 返回字段数量上限
        """
        self._ensure_loaded()
        return analysis_skills.analysis_class_fields(
            self._analysis, class_name, limit
        )

    # ================================================================
    # 第十七轮：方法全貌聚合
    # ================================================================

    def analysis_method_summary(
        self,
        class_name: str,
        method_name: str,
        descriptor: str = None,
        include_source: bool = True,
        xref_limit: int = 10,
    ) -> dict:
        """
        聚合方法的全部分析信息（元信息 + 6 类 xref 摘要 + 基本块/异常统计 + 反编译源码）。

        :param class_name: 类名
        :param method_name: 方法名
        :param descriptor: 方法描述符（可选，不传则取类内首个同名方法）
        :param include_source: 是否包含反编译源码
        :param xref_limit: 每类 xref 引用返回上限
        """
        self._ensure_loaded()
        return analysis_skills.analysis_method_summary(
            self._dex_list,
            self._analysis,
            class_name,
            method_name,
            descriptor,
            include_source,
            xref_limit,
        )

    def analysis_method_reachable(
        self,
        class_name: str,
        method_name: str,
        descriptor: str = None,
        max_depth: int = 3,
        include_external: bool = False,
        max_nodes: int = 5000,
    ) -> dict:
        """
        方法可达性分析——从指定方法递归展开 xref_to 到 max_depth 层。

        :param class_name: 起始类名
        :param method_name: 起始方法名
        :param descriptor: 方法描述符（可选）
        :param max_depth: 递归深度上限
        :param include_external: 是否递归外部方法
        :param max_nodes: 节点数上限
        """
        self._ensure_loaded()
        return analysis_skills.analysis_method_reachable(
            self._analysis,
            class_name,
            method_name,
            descriptor,
            max_depth,
            include_external,
            max_nodes,
        )

    def analysis_method_callers(
        self,
        class_name: str,
        method_name: str,
        descriptor: str = None,
        max_depth: int = 3,
        include_external: bool = False,
        max_nodes: int = 5000,
    ) -> dict:
        """
        方法反向可达性（调用方溯源）——从指定方法递归展开 xref_from 到 max_depth 层。

        与 method-reachable 方向相反：回答"哪些方法/入口最终会调用到此方法"，
        用于危险 sink 溯源、污点源定位、影响面评估、攻击路径反向构建。

        :param class_name: 目标类名
        :param method_name: 目标方法名
        :param descriptor: 方法描述符（可选）
        :param max_depth: 反向递归深度上限
        :param include_external: 是否递归外部方法
        :param max_nodes: 节点数上限
        """
        self._ensure_loaded()
        return analysis_skills.analysis_method_callers(
            self._analysis,
            class_name,
            method_name,
            descriptor,
            max_depth,
            include_external,
            max_nodes,
        )

    def analysis_method_block_instructions(
        self,
        class_name: str,
        method_name: str,
        descriptor: str = None,
        ins_limit_per_block: int = None,
    ) -> dict:
        """
        按基本块反汇编方法指令（CFG 节点级指令视图）。

        :param class_name: 类名
        :param method_name: 方法名
        :param descriptor: 方法描述符（可选）
        :param ins_limit_per_block: 每块指令上限
        """
        self._ensure_loaded()
        return analysis_skills.analysis_method_block_instructions(
            self._analysis,
            class_name,
            method_name,
            descriptor,
            ins_limit_per_block,
        )

    def analysis_method_switch_payloads(
        self,
        class_name: str,
        method_name: str,
        descriptor: str = None,
    ) -> dict:
        """
        解析方法的 switch 分支表（case→目标）与 fill-array-data 数组 payload。

        :param class_name: 类名
        :param method_name: 方法名
        :param descriptor: 方法描述符（可选）
        """
        self._ensure_loaded()
        return analysis_skills.analysis_method_switch_payloads(
            self._analysis,
            class_name,
            method_name,
            descriptor,
        )

    # ================================================================
    # 第六轮：调用图与 API 权限映射
    # ================================================================

    def analysis_call_graph(
        self, limit: int = None, external: bool = False
    ) -> dict:
        """
        获取完整调用图并序列化（节点 + 边）。

        :param limit: 返回边数量限制
        :param external: 是否包含外部方法节点
        """
        self._ensure_loaded()
        return analysis_skills.analysis_call_graph(
            self._analysis, limit, external
        )

    def analysis_call_graph_filtered(
        self,
        classname: str = None,
        methodname: str = None,
        descriptor: str = None,
        accessflags: str = None,
        no_isolated: bool = False,
        external: bool = False,
        limit: int = None,
    ) -> dict:
        """
        生成按类/方法/描述符/访问标志过滤的子调用图。

        :param classname: 类名正则
        :param methodname: 方法名正则
        :param descriptor: 描述符正则
        :param accessflags: 访问标志正则
        :param no_isolated: 移除孤立节点
        :param external: 是否包含外部方法节点
        :param limit: 返回边数量限制
        """
        self._ensure_loaded()
        return analysis_skills.analysis_call_graph_filtered(
            self._analysis,
            classname,
            methodname,
            descriptor,
            accessflags,
            no_isolated,
            external,
            limit,
        )

    def analysis_permissions(
        self, apilevel: int = None, limit: int = None
    ) -> dict:
        """
        基于 API level 的方法→权限映射分析（批量列出需权限的 API 调用）。

        :param apilevel: API level（None 用默认）
        :param limit: 返回数量限制
        """
        self._ensure_loaded()
        return analysis_skills.analysis_permissions(
            self._analysis, apilevel, limit
        )

    # ================================================================
    # 第四轮：ARSCParser 资源 XML 导出能力
    # ================================================================

    def resource_string_resources(
        self, package: str, locale: str = "\x00\x00", raw: bool = False
    ) -> dict:
        """
        获取指定包+语言的字符串资源（strings.xml）。

        :param package: 资源包名
        :param locale: 语言
        :param raw: 是否返回原始 XML 文本
        """
        try:
            arsc = self._get_arsc()
            return resource_skills.resource_string_resources(
                arsc, package, locale, raw
            )
        except RuntimeError as e:
            return {"error": str(e)}

    def resource_strings_all(self, raw: bool = False) -> dict:
        """
        获取所有包的字符串资源（全量 strings.xml）。

        :param raw: 是否返回原始 XML 文本
        """
        try:
            arsc = self._get_arsc()
            return resource_skills.resource_strings_all(arsc, raw)
        except RuntimeError as e:
            return {"error": str(e)}

    def resource_public(
        self, package: str, locale: str = "\x00\x00", raw: bool = False
    ) -> dict:
        """
        获取 public.xml（资源 type/name/id 完整映射）。

        :param package: 资源包名
        :param locale: 语言
        :param raw: 是否返回原始 XML 文本
        """
        try:
            arsc = self._get_arsc()
            return resource_skills.resource_public(arsc, package, locale, raw)
        except RuntimeError as e:
            return {"error": str(e)}

    def resource_id_resources(
        self, package: str, locale: str = "\x00\x00", raw: bool = False
    ) -> dict:
        """
        获取 ids.xml（id 类型资源列表）。

        :param package: 资源包名
        :param locale: 语言
        :param raw: 是否返回原始 XML 文本
        """
        try:
            arsc = self._get_arsc()
            return resource_skills.resource_id_resources(
                arsc, package, locale, raw
            )
        except RuntimeError as e:
            return {"error": str(e)}

    def resource_get_string(
        self, package: str, name: str, locale: str = "\x00\x00"
    ) -> dict:
        """
        按包名+键名+语言精确获取单个字符串资源值。

        :param package: 资源包名
        :param name: 字符串资源键名
        :param locale: 语言
        """
        try:
            arsc = self._get_arsc()
            return resource_skills.resource_get_string(
                arsc, package, name, locale
            )
        except RuntimeError as e:
            return {"error": str(e)}

    def resource_xml_name(self, resource_id: int, package: str = None) -> dict:
        """
        资源 ID → XML 名称（@pkg:type/name）。

        :param resource_id: 资源 ID（整型）
        :param package: 资源包名（可选）
        """
        try:
            arsc = self._get_arsc()
            return resource_skills.resource_xml_name(
                arsc, resource_id, package
            )
        except RuntimeError as e:
            return {"error": str(e)}

    def resource_res_configs(
        self, resource_id: int, fallback: bool = True
    ) -> dict:
        """
        按资源 ID 查配置变体（locale/密度，原始 entry 视图）。

        :param resource_id: 资源 ID（整型）
        :param fallback: 找不到精确配置时是否回退到默认配置
        """
        try:
            arsc = self._get_arsc()
            return resource_skills.resource_res_configs(
                arsc, resource_id, fallback
            )
        except RuntimeError as e:
            return {"error": str(e)}

    def resource_value(self, resource_id: int, package: str = None) -> dict:
        """
        按资源 ID 取类型化解析值。

        :param resource_id: 资源 ID（整型或十六进制/十进制字符串）
        :param package: 资源包名（可选）
        """
        try:
            arsc = self._get_arsc()
            return resource_skills.resource_value(arsc, resource_id, package)
        except RuntimeError as e:
            return {"error": str(e)}

    def resource_type_configs(
        self, package: str, resource_type: str = None
    ) -> dict:
        """
        资源类型的配置变体列表。

        :param package: 资源包名
        :param resource_type: 资源类型（可选，None 返回全部）
        """
        try:
            arsc = self._get_arsc()
            return resource_skills.resource_type_configs(
                arsc, package, resource_type
            )
        except RuntimeError as e:
            return {"error": str(e)}

    def resource_resolved_strings(self, locale: str = None) -> dict:
        """
        全量解析后字符串资源（pkg→locale→rid 三层结构）。

        :param locale: 语言过滤（可选）
        """
        try:
            arsc = self._get_arsc()
            return resource_skills.resource_resolved_strings(arsc, locale)
        except RuntimeError as e:
            return {"error": str(e)}

    # ================================================================
    # DEX 独立加载
    # ================================================================

    def load_dex(self, dex_path: str) -> dict:
        """
        直接加载 DEX 文件（不依赖 APK）。

        :param dex_path: DEX 文件路径
        :return: 加载结果
        """
        from androguard.misc import AnalyzeDex

        if not os.path.exists(dex_path):
            # 抛异常与 load_apk 一致：CLI _SkillsCliGroup 与 daemon _dispatch
            # 统一捕获输出结构化 error。
            raise RuntimeError(f"File not found: {dex_path}")

        try:
            _, d, dx = AnalyzeDex(dex_path)
            # AnalyzeDex 返回 (_, DEX_object, Analysis)
            # DEX_object 是单个 DEX，不是列表，需要包装为列表
            dex_list = [d] if not isinstance(d, list) else d
            # 释放旧解析对象 + gc（与 load_apk 一致，Analysis 持有 xref 引用环）
            self._apk = None
            self._dex_list = []
            self._analysis = None
            self._loaded_path = None
            self._session = None
            import gc

            gc.collect()
            self._dex_list = dex_list
            self._analysis = dx
            self._loaded_path = dex_path
            # DEX 模式下没有 APK
            self._apk = None

            # 取第一个 DEX 的类数（d 可能是 list，取首个；为空则 0）
            first_dex = dex_list[0] if dex_list else None
            class_count = (
                len(list(first_dex.get_classes()))
                if first_dex is not None
                else 0
            )

            return {
                "status": "loaded",
                "path": dex_path,
                "dex_count": len(self._dex_list),
                "classes": class_count,
            }
        except Exception as e:
            raise RuntimeError(f"Failed to load DEX: {str(e)}")


# ================================================================
# CLI 入口
# ================================================================

# 全局 skills 实例（单次执行模式使用）
_skills_instance = None


def _get_skills() -> AndroguardSkillsMain:
    """获取全局 skills 实例"""
    global _skills_instance
    if _skills_instance is None:
        _skills_instance = AndroguardSkillsMain()
    return _skills_instance


class _SkillsJsonEncoder(json.JSONEncoder):
    """自定义 JSON 编码器，处理 AndroGuard 返回的不可直接序列化的类型。

    AndroGuard 大量使用迭代器（filter/map/zip/range/generator）、集合（set/
    frozenset）、bytes 等。未处理的类型会导致 json.dumps TypeError 命令崩溃。
    """

    def default(self, obj):
        # 处理 set / frozenset（AndroGuard 权限集合等用 frozenset）
        if isinstance(obj, (set, frozenset)):
            return list(obj)
        # 处理 bytes / bytearray
        if isinstance(obj, (bytes, bytearray)):
            return obj.hex()
        # 处理 filter / map / zip / range
        if isinstance(obj, (filter, map, zip, range)):
            return list(obj)
        # 处理任意迭代器/generator（ hasattr __next__ 即迭代器）
        # 放最后：明确具名类型优先，通用迭代器兜底
        if hasattr(obj, "__next__"):
            return list(obj)
        return super().default(obj)


def _output_json(data: dict):
    """输出 JSON 到 stdout"""
    print(
        json.dumps(data, indent=2, ensure_ascii=False, cls=_SkillsJsonEncoder)
    )


def _parse_filter_pairs(pairs) -> dict:
    """
    将多个 "key=value" 字符串解析为字典。

    用于 manifest 属性过滤条件。
    """
    result = {}
    if not pairs:
        return result
    for pair in pairs:
        if "=" in pair:
            k, v = pair.split("=", 1)
            result[k.strip()] = v.strip()
    return result


def _try_daemon_call(method: str, params: dict = None) -> Union[dict, None]:
    """
    尝试通过 daemon 调用。

    :param method: JSON-RPC 方法名
    :param params: 参数
    :return: 响应结果 dict；daemon 不可用（未运行/连不上）返回 None 触发 fallback；
             daemon 在运行但方法执行报错时返回 {"error": ...} 不 fallback（直接输出给用户）。

    关键区分：daemon 在跑 + 方法报错（如未 load APK、APK 损坏）应直接返回结构化
    error，而非返回 None 触发 fallback——否则 fallback 单次执行会因同样原因再崩
    一次 traceback，且对 agent 来说 error 不是合法 JSON 无法自恢复。
    """
    from androguard.skills.daemon import DaemonClient

    # load_apk/load_dex 是慢命令（解析大 APK/DEX 可能耗时数十秒到数分钟），
    # 默认 30s timeout 会让正常的大 APK load 被误判超时→fallback 单次执行
    # （重新解析一遍，更慢且 daemon 那边仍在解析）。对这类命令用长 timeout。
    slow_methods = {
        "load_apk",
        "load_dex",
        "session_analyze_apk",
        "session_add_apk",
        "session_add_dex",
    }
    client_timeout = 600.0 if method in slow_methods else 30.0
    client = DaemonClient(timeout=client_timeout)
    if not client.is_daemon_running():
        return None  # daemon 未运行 → fallback 单次执行

    try:
        result = client.call(method, params or {})
        return result
    except (ConnectionError, OSError):
        # daemon 连不上（可能刚崩溃；socket.timeout/ConnectionRefusedError 均为 OSError 子类）→ fallback
        return None
    except RuntimeError as e:
        # daemon 在跑但方法报错（DaemonClient.call 对 JSON-RPC error 抛 RuntimeError）
        # → 返回结构化 error，不 fallback
        msg = str(e)
        if msg.startswith("Daemon error:"):
            msg = msg[len("Daemon error:") :].strip()
        return {"error": msg}


# 统一捕获 skills 执行异常，输出结构化 error JSON 而非 Python traceback。
# 单次 fallback 路径下，APK 无效/未加载等 RuntimeError 会被转成 {"error": "..."}
# JSON，agent 可解析自恢复。daemon 路径的 _dispatch 已自行捕获（返回 JSON-RPC
# error），不经过这里。Click 自身的参数错误（缺参数等）是 ClickException 子类，
# 交回 Click 处理，不被吞。
#
# 关键：click.exceptions.Exit（--help/--version/ctx.exit 触发）和 Abort（Ctrl-C
# 风格中断）都是 RuntimeError 的子类。若用宽泛的 `except RuntimeError`，
# 会把 Click 正常退出信号误当业务错误，在每个 `--help` 末尾吐出
# `{"error": "0"}`（str(Exit(0))=="0"），误导 agent 以为命令失败。故先
# re-raise Exit/Abort 交还 Click，只捕获我们自己 raise 的业务 RuntimeError。
class _SkillsCliGroup(click.Group):
    def invoke(self, ctx):
        try:
            return super().invoke(ctx)
        except (click.exceptions.Exit, click.exceptions.Abort):
            raise  # Click 自身退出信号，交还 Click 正常处理
        except (RuntimeError, TypeError) as e:
            # RuntimeError: 业务异常（load_apk 失败、_ensure_loaded 等）
            # TypeError: JSON 序列化失败（命令返回了 _SkillsJsonEncoder 无法
            # 处理的对象，如漏序列化的 lxml Element）。TypeError 不是
            # RuntimeError 子类，若不显式 catch 会逃逸吐 Python traceback，
            # agent 无法解析自恢复。转结构化 error 让 agent 可见失败原因。
            _output_json({"error": str(e)})
            ctx.exit(0)


@click.group(
    cls=_SkillsCliGroup, help="AndroGuard Skills - Android 逆向工程能力 CLI"
)
@click.version_option(version="4.1.4")
@click.option(
    "--verbose",
    "--debug",
    "verbosity",
    flag_value="verbose",
    help="Print more information",
)
def entry_point(verbosity):
    """AndroGuard Skills CLI 入口"""
    if verbosity is None:
        logger.remove()
        logger.add(sys.stderr, level="ERROR")
    else:
        logger.remove()
        logger.add(sys.stderr, level="INFO")


# ================================================================
# MCP stdio server 命令
# ================================================================


@entry_point.command(name="mcp")
@click.option(
    "--with-ui",
    is_flag=True,
    default=False,
    help="Also expose UI control tools (ui.snapshot, ui.action, etc.)",
)
def mcp_cmd(with_ui):
    """Run as an MCP stdio server (JSON-RPC line-framed on stdin/stdout).

    Suitable for use with Claude Desktop, Claude Code, and any MCP-compatible
    client. Each request is one JSON line; each response is one JSON line.

    Example Claude Code config (~/.claude/settings.json)::\n
        { "mcpServers": { "androguard": { "command": "androguard-skills", "args": ["mcp"] } } }
    """
    from androguard.agent.server import run_stdio

    run_stdio(include_ui=with_ui)


# ================================================================
# Daemon 命令
# ================================================================


@entry_point.group(help="Manage the daemon process")
def daemon():
    """Daemon 进程管理"""
    pass


@daemon.command(name="start")
@click.option(
    "--port", default=8899, help="TCP port for daemon (default: 8899)"
)
def daemon_start(port):
    """Start the daemon process"""
    from androguard.skills.daemon import DaemonServer

    server = DaemonServer(port=port)
    server.start()


@daemon.command(name="stop")
def daemon_stop():
    """Stop the daemon process"""
    from androguard.skills.daemon import DaemonClient

    client = DaemonClient()
    if client.is_daemon_running():
        client.stop_daemon()
        print(json.dumps({"status": "stopped"}))
    else:
        print(json.dumps({"status": "not_running"}))


@daemon.command(name="status")
def daemon_status():
    """Check daemon status"""
    from androguard.skills.daemon import DaemonClient

    client = DaemonClient()
    if client.is_daemon_running():
        info = client.call("status", {})
        _output_json(info or {"status": "running"})
    else:
        _output_json({"status": "not_running"})


# ================================================================
# Load 命令
# ================================================================


@entry_point.command(name="load")
@click.argument("apk_path", type=click.Path(exists=True))
def load_apk(apk_path):
    """Load an APK file for analysis"""
    # 先尝试 daemon
    result = _try_daemon_call("load_apk", {"apk_path": apk_path})
    if result is not None:
        _output_json(result)
        return

    # 降级为单次执行
    skills = _get_skills()
    result = skills.load_apk(apk_path)
    _output_json(result)


@entry_point.command(name="unload")
def unload_cmd():
    """Unload the current APK and release parsed objects (daemon mode).

    Releases the loaded APK's APK/DEX/Analysis objects, runs gc, and trims
    glibc malloc arenas so RSS falls back after processing large APKs.
    Use this when a daemon has finished analyzing one APK and will idle or
    switch contexts, to keep long-running memory bounded.
    """
    # 先尝试 daemon
    result = _try_daemon_call("unload")
    if result is not None:
        _output_json(result)
        return

    # 降级为单次执行（单次模式本就进程退出，unload 无实际效果但仍输出）
    skills = _get_skills()
    result = skills.unload()
    _output_json(result)


# ================================================================
# APK 命令组
# ================================================================


@entry_point.group(help="APK information commands")
def apk():
    """APK 信息命令组"""
    pass


@apk.command(name="info")
@click.option(
    "--apk-path",
    envvar="ANDROGUARD_APK_PATH",
    help="APK file path (or set ANDROGUARD_APK_PATH env var)",
)
def apk_info_cmd(apk_path):
    """Get APK basic information"""
    # 尝试 daemon
    result = _try_daemon_call("apk_info")
    if result is not None:
        _output_json(result)
        return

    # 降级为单次执行
    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.apk_info())


@apk.command(name="permissions")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_permissions_cmd(apk_path):
    """Get APK permissions"""
    result = _try_daemon_call("apk_permissions")
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.apk_permissions())


@apk.command(name="activities")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_activities_cmd(apk_path):
    """Get APK activities"""
    result = _try_daemon_call("apk_activities")
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.apk_activities())


@apk.command(name="services")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_services_cmd(apk_path):
    """Get APK services"""
    result = _try_daemon_call("apk_services")
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.apk_services())


@apk.command(name="receivers")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_receivers_cmd(apk_path):
    """Get APK broadcast receivers"""
    result = _try_daemon_call("apk_receivers")
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.apk_receivers())


@apk.command(name="providers")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_providers_cmd(apk_path):
    """Get APK content providers"""
    result = _try_daemon_call("apk_providers")
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.apk_providers())


@apk.command(name="intent-filters")
@click.argument("component")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_intent_filters_cmd(component, apk_path):
    """Get intent filters for a specific component"""
    result = _try_daemon_call("apk_intent_filters", {"component": component})
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.apk_intent_filters(component))


@apk.command(name="signature")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_signature_cmd(apk_path):
    """Get APK signature information"""
    result = _try_daemon_call("apk_signature")
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.apk_signature())


@apk.command(name="files")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_files_cmd(apk_path):
    """Get APK file listing"""
    result = _try_daemon_call("apk_files")
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.apk_files())


@apk.command(name="manifest")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_manifest_cmd(apk_path):
    """Get AndroidManifest.xml content"""
    result = _try_daemon_call("apk_manifest")
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.apk_manifest())


@apk.command(name="features")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_features_cmd(apk_path):
    """Get uses-feature list"""
    result = _try_daemon_call("apk_features")
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.apk_features())


@apk.command(name="libraries")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_libraries_cmd(apk_path):
    """Get uses-library list"""
    result = _try_daemon_call("apk_libraries")
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.apk_libraries())


@apk.command(name="icon")
@click.option(
    "--max-dpi",
    default=65536,
    type=int,
    help="Max DPI for icon selection (default: 65536)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_icon_cmd(max_dpi, apk_path):
    """Get app icon information"""
    result = _try_daemon_call("apk_icon", {"max_dpi": max_dpi})
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.apk_icon(max_dpi))


@apk.command(name="file")
@click.argument("filename")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_file_cmd(filename, apk_path):
    """Extract a file from APK (content returned as base64)"""
    result = _try_daemon_call("apk_file", {"filename": filename})
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.apk_file(filename))


@apk.command(name="verify")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_verify_cmd(apk_path):
    """Verify APK integrity and signature status"""
    result = _try_daemon_call("apk_verify")
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.apk_verify())


@apk.command(name="signing-block")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_signing_block_cmd(apk_path):
    """Get v2/v3 signing block details"""
    result = _try_daemon_call("apk_signing_block")
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.apk_signing_block())


@apk.command(name="manifest-attrs")
@click.option(
    "--tag",
    "tag_name",
    required=True,
    help="Manifest tag name (e.g. uses-permission)",
)
@click.option("--attribute", required=True, help="Attribute name (e.g. name)")
@click.option(
    "--filter",
    "filter_pairs",
    multiple=True,
    help="Attribute filter as key=value (can repeat)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_manifest_attrs_cmd(tag_name, attribute, filter_pairs, apk_path):
    """Batch extract attribute values from AndroidManifest tags"""
    attribute_filter = _parse_filter_pairs(filter_pairs)
    result = _try_daemon_call(
        "apk_manifest_attrs",
        {
            "tag_name": tag_name,
            "attribute": attribute,
            "attribute_filter": attribute_filter,
        },
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(
        skills.apk_manifest_attrs(tag_name, attribute, attribute_filter)
    )


@apk.command(name="manifest-attr")
@click.option("--tag", "tag_name", required=True, help="Manifest tag name")
@click.option("--attribute", required=True, help="Attribute name")
@click.option(
    "--filter",
    "filter_pairs",
    multiple=True,
    help="Attribute filter as key=value (can repeat)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_manifest_attr_cmd(tag_name, attribute, filter_pairs, apk_path):
    """Extract a single manifest attribute value (first match)"""
    attribute_filter = _parse_filter_pairs(filter_pairs)
    result = _try_daemon_call(
        "apk_manifest_attr",
        {
            "tag_name": tag_name,
            "attribute": attribute,
            "attribute_filter": attribute_filter,
        },
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(
        skills.apk_manifest_attr(tag_name, attribute, attribute_filter)
    )


@apk.command(name="certificate")
@click.option(
    "--filename",
    default=None,
    help="Signature file name (e.g. META-INF/CERT.RSA). If omitted, returns all certificates",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_certificate_cmd(filename, apk_path):
    """Get APK signing certificate details"""
    result = _try_daemon_call("apk_certificate", {"filename": filename})
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.apk_certificate(filename))


@apk.command(name="verify-signature")
@click.option(
    "--filename",
    default=None,
    help="Signature file name (e.g. META-INF/CERT.RSA). If omitted, verify all signature files",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_verify_signature_cmd(filename, apk_path):
    """Cryptographically verify APK signatures (signer info vs .SF file)"""
    result = _try_daemon_call("apk_verify_signature", {"filename": filename})
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.apk_verify_signature(filename))


@apk.command(name="files-info")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_files_info_cmd(apk_path):
    """Get detailed file information (name/type/CRC32)"""
    result = _try_daemon_call("apk_files_info")
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.apk_files_info())


@apk.command(name="dex-data")
@click.option(
    "--all-dex", is_flag=True, help="Extract all DEX files (multidex)"
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_dex_data_cmd(all_dex, apk_path):
    """Extract DEX binary data (base64 encoded)"""
    result = _try_daemon_call("apk_dex_data", {"all_dex": all_dex})
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.apk_dex_data(all_dex))


@apk.command(name="raw")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_raw_cmd(apk_path):
    """Extract the whole APK raw bytes (base64 encoded)"""
    result = _try_daemon_call("apk_raw")
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.apk_raw())


@apk.command(name="manifest-tags")
@click.option("--tag", "tag_name", required=True, help="Manifest tag name")
@click.option(
    "--filter",
    "filter_pairs",
    multiple=True,
    help="Attribute filter as key=value (can repeat)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_manifest_tags_cmd(tag_name, filter_pairs, apk_path):
    """Find manifest tags by attribute filter"""
    attribute_filter = _parse_filter_pairs(filter_pairs)
    result = _try_daemon_call(
        "apk_manifest_tags",
        {"tag_name": tag_name, "attribute_filter": attribute_filter},
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.apk_manifest_tags(tag_name, attribute_filter))


@apk.command(name="signing-versions")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_signing_versions_cmd(apk_path):
    """Detect APK signing schemes (v1/v2/v3/v3.1)"""
    result = _try_daemon_call("apk_signing_versions")
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.apk_signing_versions())


@apk.command(name="certificates-scheme")
@click.option(
    "--scheme",
    default="v3",
    type=click.Choice(["v1", "v2", "v3", "v31"]),
    help="Signing scheme",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_certificates_scheme_cmd(scheme, apk_path):
    """Get certificates by signing scheme (v1/v2/v3/v31)"""
    result = _try_daemon_call("apk_certificates_scheme", {"scheme": scheme})
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.apk_certificates_scheme(scheme))


@apk.command(name="certificates-der")
@click.option(
    "--scheme",
    default="v3",
    type=click.Choice(["v2", "v3", "v31"]),
    help="Signing scheme",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_certificates_der_cmd(scheme, apk_path):
    """Get certificate DER bytes (base64) by signing scheme"""
    result = _try_daemon_call("apk_certificates_der", {"scheme": scheme})
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.apk_certificates_der(scheme))


@apk.command(name="public-keys")
@click.option(
    "--scheme",
    default="v3",
    type=click.Choice(["v2", "v3", "v31"]),
    help="Signing scheme",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_public_keys_cmd(scheme, apk_path):
    """Get signing public keys by scheme"""
    result = _try_daemon_call("apk_public_keys", {"scheme": scheme})
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.apk_public_keys(scheme))


@apk.command(name="signature-files")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_signature_files_cmd(apk_path):
    """Get APK signature file info (name + raw signature base64)"""
    result = _try_daemon_call("apk_signature_files")
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.apk_signature_files())


@apk.command(name="files-crc32")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_files_crc32_cmd(apk_path):
    """Get CRC32 checksums of all APK files"""
    result = _try_daemon_call("apk_files_crc32")
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.apk_files_crc32())


@apk.command(name="fingerprint")
@click.option(
    "--scheme",
    default="v3",
    type=click.Choice(["v2", "v3", "v31"]),
    help="Signing scheme to read public keys from",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_fingerprint_cmd(scheme, apk_path):
    """Get SHA-256 fingerprints of signing public keys"""
    result = _try_daemon_call("apk_fingerprint", {"scheme": scheme})
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.apk_fingerprint(scheme))


@apk.command(name="manifest-axml")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_manifest_axml_cmd(apk_path):
    """Analyze AndroidManifest.xml AXML structure (packing detection / root tag attrs)"""
    result = _try_daemon_call("apk_manifest_axml")
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.apk_manifest_axml())


@apk.command(name="axml")
@click.argument("filename")
@click.option(
    "--no-pretty", is_flag=True, help="Disable pretty-printing (compact XML)"
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_axml_cmd(filename, no_pretty, apk_path):
    """Decode any binary AXML file in APK to readable XML (layouts/drawables/config)"""
    pretty = not no_pretty
    result = _try_daemon_call(
        "apk_axml", {"filename": filename, "pretty": pretty}
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.apk_axml(filename, pretty))


# ----------------------------------------------------------------
# 第六轮：APK 权限分类 / SDK 版本 / 设备特性
# ----------------------------------------------------------------


def _apk_loader(apk_path):
    """加载 APK 并返回 skills 实例（供无参/单参 apk 命令复用）"""
    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return None
        skills.load_apk(apk_path)
    return skills


@apk.command(name="declared-permissions")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_declared_permissions_cmd(apk_path):
    """Get permissions declared (custom <permission> tags) by the APK"""
    result = _try_daemon_call("apk_declared_permissions")
    if result is not None:
        _output_json(result)
        return
    skills = _apk_loader(apk_path)
    if skills is not None:
        _output_json(skills.apk_declared_permissions())


@apk.command(name="requested-permissions")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_requested_permissions_cmd(apk_path):
    """Get requested permissions grouped by source (AOSP/third-party/implied)"""
    result = _try_daemon_call("apk_requested_permissions")
    if result is not None:
        _output_json(result)
        return
    skills = _apk_loader(apk_path)
    if skills is not None:
        _output_json(skills.apk_requested_permissions())


@apk.command(name="sdk-versions")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_sdk_versions_cmd(apk_path):
    """Get SDK version info (min/max/target/effective_target)"""
    result = _try_daemon_call("apk_sdk_versions")
    if result is not None:
        _output_json(result)
        return
    skills = _apk_loader(apk_path)
    if skills is not None:
        _output_json(skills.apk_sdk_versions())


@apk.command(name="main-activities")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_main_activities_cmd(apk_path):
    """Get main activity (with aliases)"""
    result = _try_daemon_call("apk_main_activities")
    if result is not None:
        _output_json(result)
        return
    skills = _apk_loader(apk_path)
    if skills is not None:
        _output_json(skills.apk_main_activities())


@apk.command(name="device-features")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_device_features_cmd(apk_path):
    """Get device feature flags (TV/Wearable/Leanback/Multidex)"""
    result = _try_daemon_call("apk_device_features")
    if result is not None:
        _output_json(result)
        return
    skills = _apk_loader(apk_path)
    if skills is not None:
        _output_json(skills.apk_device_features())


@apk.command(name="files-types")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_files_types_cmd(apk_path):
    """Get MIME/file type of all APK entries"""
    result = _try_daemon_call("apk_files_types")
    if result is not None:
        _output_json(result)
        return
    skills = _apk_loader(apk_path)
    if skills is not None:
        _output_json(skills.apk_files_types())


@apk.command(name="details-permissions")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_details_permissions_cmd(apk_path):
    """Get requested permissions with details (protection_level/label/description)"""
    result = _try_daemon_call("apk_details_permissions")
    if result is not None:
        _output_json(result)
        return
    skills = _apk_loader(apk_path)
    if skills is not None:
        _output_json(skills.apk_details_permissions())


@apk.command(name="manifest-tree")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_manifest_tree_cmd(apk_path):
    """Get AndroidManifest.xml tag tree statistics (tag counts + attributes)"""
    result = _try_daemon_call("apk_manifest_tree")
    if result is not None:
        _output_json(result)
        return
    skills = _apk_loader(apk_path)
    if skills is not None:
        _output_json(skills.apk_manifest_tree())


@apk.command(name="find-tags-xml")
@click.argument("xml_name")
@click.argument("tag_name")
@click.option(
    "--filter",
    "filter_pairs",
    multiple=True,
    help="Attribute filter as key=value (repeatable)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_find_tags_xml_cmd(xml_name, tag_name, filter_pairs, apk_path):
    """Find tags in a specific XML file inside the APK"""
    kwargs = _parse_filter_pairs(filter_pairs)
    result = _try_daemon_call(
        "apk_find_tags_xml",
        {"xml_name": xml_name, "tag_name": tag_name, "filter_kwargs": kwargs},
    )
    if result is not None:
        _output_json(result)
        return
    skills = _apk_loader(apk_path)
    if skills is not None:
        _output_json(
            skills.apk_find_tags_xml(xml_name, tag_name, filter_kwargs=kwargs)
        )


@apk.command(name="cert-names")
@click.option(
    "--scheme",
    default="v3",
    type=click.Choice(["v1", "v2", "v3", "v31"]),
    help="Signing scheme",
)
@click.option(
    "--no-android", is_flag=True, help="Use non-Android canonicalization"
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_cert_names_cmd(scheme, no_android, apk_path):
    """Get canonical/normalized names of signing certificate subject and issuer"""
    result = _try_daemon_call(
        "apk_cert_names", {"scheme": scheme, "android": not no_android}
    )
    if result is not None:
        _output_json(result)
        return
    skills = _apk_loader(apk_path)
    if skills is not None:
        _output_json(skills.apk_cert_names(scheme, not no_android))


@apk.command(name="res-value")
@click.argument("name")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_res_value_cmd(name, apk_path):
    """Resolve a resource ID (e.g. @7F080001) to its literal value"""
    result = _try_daemon_call("apk_res_value", {"name": name})
    if result is not None:
        _output_json(result)
        return
    skills = _apk_loader(apk_path)
    if skills is not None:
        _output_json(skills.apk_res_value(name))


@apk.command(name="dex-names")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_dex_names_cmd(apk_path):
    """List all DEX file names in the APK (multidex aware)"""
    result = _try_daemon_call("apk_dex_names", {})
    if result is not None:
        _output_json(result)
        return
    skills = _apk_loader(apk_path)
    if skills is not None:
        _output_json(skills.apk_dex_names())


@apk.command(name="signature-names")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_signature_names_cmd(apk_path):
    """List all signature file names (e.g. CERT.RSA, CERT.SF)"""
    result = _try_daemon_call("apk_signature_names", {})
    if result is not None:
        _output_json(result)
        return
    skills = _apk_loader(apk_path)
    if skills is not None:
        _output_json(skills.apk_signature_names())


@apk.command(name="app-name")
@click.option(
    "--locale",
    default=None,
    help="Locale code (e.g. zh, en); default if omitted",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_app_name_cmd(locale, apk_path):
    """Get the app display name (resolved android:label)"""
    result = _try_daemon_call("apk_app_name", {"locale": locale})
    if result is not None:
        _output_json(result)
        return
    skills = _apk_loader(apk_path)
    if skills is not None:
        _output_json(skills.apk_app_name(locale))


@apk.command(name="valid")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_valid_cmd(apk_path):
    """Check if the APK is structurally valid"""
    result = _try_daemon_call("apk_valid", {})
    if result is not None:
        _output_json(result)
        return
    skills = _apk_loader(apk_path)
    if skills is not None:
        _output_json(skills.apk_valid())


@apk.command(name="duplicate-signatures")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_duplicate_signatures_cmd(apk_path):
    """Check for duplicate signature IDs (suspicious packing artifact)"""
    result = _try_daemon_call("apk_duplicate_signatures", {})
    if result is not None:
        _output_json(result)
        return
    skills = _apk_loader(apk_path)
    if skills is not None:
        _output_json(skills.apk_duplicate_signatures())


@apk.command(name="security-overview")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_security_overview_cmd(apk_path):
    """Security audit overview (signatures/permissions/components/manifest flags/packing)"""
    result = _try_daemon_call("apk_security_overview", {})
    if result is not None:
        _output_json(result)
        return
    skills = _apk_loader(apk_path)
    if skills is not None:
        _output_json(skills.apk_security_overview())


@apk.command(name="native-libraries")
@click.option(
    "--include-data",
    is_flag=True,
    help="Include base64-encoded .so data (large output)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_native_libraries_cmd(include_data, apk_path):
    """List native libraries (lib/<abi>/*.so) grouped by ABI"""
    result = _try_daemon_call(
        "apk_native_libraries", {"include_data": include_data}
    )
    if result is not None:
        _output_json(result)
        return
    skills = _apk_loader(apk_path)
    if skills is not None:
        _output_json(skills.apk_native_libraries(include_data))


@apk.command(name="application-flags")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_application_flags_cmd(apk_path):
    """Audit <application> security flags (debuggable/allowBackup/cleartext/etc) with default inference & risk rating"""
    result = _try_daemon_call("apk_application_flags", {})
    if result is not None:
        _output_json(result)
        return
    skills = _apk_loader(apk_path)
    if skills is not None:
        _output_json(skills.apk_application_flags())


@apk.command(name="component-details")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_component_details_cmd(apk_path):
    """List all components (Activity/Service/Receiver/Provider) with security attrs & exposure risk"""
    result = _try_daemon_call("apk_component_details", {})
    if result is not None:
        _output_json(result)
        return
    skills = _apk_loader(apk_path)
    if skills is not None:
        _output_json(skills.apk_component_details())


@apk.command(name="attack-surface")
@click.option(
    "--max-depth",
    default=4,
    type=int,
    help="Forward reachability depth from component methods (default 4)",
)
@click.option(
    "--per-sink-limit",
    default=10,
    type=int,
    help="Max call samples per sink category per component (default 10)",
)
@click.option(
    "--max-nodes",
    default=2000,
    type=int,
    help="BFS node cap per component (default 2000)",
)
@click.option(
    "--include-safe",
    is_flag=True,
    help="Also analyze non-exported/protected components (default: exposed only)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_attack_surface_cmd(
    max_depth, per_sink_limit, max_nodes, include_safe, apk_path
):
    """Attack surface: cross-reference exported components with forward-reachable dangerous sinks"""
    params = {
        "max_depth": max_depth,
        "per_sink_limit": per_sink_limit,
        "max_nodes_per_component": max_nodes,
        "include_safe": include_safe,
    }
    result = _try_daemon_call("apk_attack_surface", params)
    if result is not None:
        _output_json(result)
        return
    skills = _apk_loader(apk_path)
    if skills is not None:
        _output_json(
            skills.apk_attack_surface(
                max_depth,
                per_sink_limit,
                max_nodes,
                include_safe,
            )
        )


@apk.command(name="deeplinks")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_deeplinks_cmd(apk_path):
    """Enumerate deep links (intent-filter/data: scheme/host/path + component + BROWSABLE)"""
    result = _try_daemon_call("apk_deeplinks", {})
    if result is not None:
        _output_json(result)
        return
    skills = _apk_loader(apk_path)
    if skills is not None:
        _output_json(skills.apk_deeplinks())


@apk.command(name="security-report")
@click.option(
    "--limit",
    "per_type_limit",
    default=20,
    type=int,
    help="Max samples/findings per domain (default 20)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_security_report_cmd(per_type_limit, apk_path):
    """One-shot full security report: aggregate all audits + composite risk score (audit suite closure)"""
    result = _try_daemon_call(
        "apk_security_report", {"per_type_limit": per_type_limit}
    )
    if result is not None:
        _output_json(result)
        return
    skills = _apk_loader(apk_path)
    if skills is not None:
        _output_json(skills.apk_security_report(per_type_limit))


# ================================================================
# DEX 命令组
# ================================================================


@entry_point.group(help="DEX information commands")
def dex():
    """DEX 信息命令组"""
    pass


@dex.command(name="classes")
@click.option(
    "--filter",
    "filter_regex",
    default=None,
    help="Regex filter for class names",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_classes_cmd(filter_regex, apk_path):
    """List DEX classes"""
    result = _try_daemon_call("dex_classes", {"filter_regex": filter_regex})
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.dex_classes(filter_regex))


@dex.command(name="methods")
@click.option(
    "--class",
    "class_name",
    default=None,
    help="Filter by class name (e.g. Lcom/example/MyClass;)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_methods_cmd(class_name, apk_path):
    """List DEX methods"""
    result = _try_daemon_call("dex_methods", {"class_name": class_name})
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.dex_methods(class_name))


@dex.command(name="strings")
@click.option(
    "--filter", "filter_regex", default=None, help="Regex filter for strings"
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_strings_cmd(filter_regex, apk_path):
    """List DEX strings"""
    result = _try_daemon_call("dex_strings", {"filter_regex": filter_regex})
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.dex_strings(filter_regex))


@dex.command(name="strings-table")
@click.option(
    "--filter", "filter_regex", default=None, help="Regex filter for strings"
)
@click.option(
    "--limit", type=int, default=None, help="Max number of entries to return"
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_strings_table_cmd(filter_regex, limit, apk_path):
    """List string constant pool with idx/offset/utf16_size (binary location for patching)"""
    result = _try_daemon_call(
        "dex_strings_table", {"filter_regex": filter_regex, "limit": limit}
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.dex_strings_table(filter_regex, limit))


@dex.command(name="fields")
@click.option(
    "--class", "class_name", default=None, help="Filter by class name"
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_fields_cmd(class_name, apk_path):
    """List DEX fields"""
    result = _try_daemon_call("dex_fields", {"class_name": class_name})
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.dex_fields(class_name))


@dex.command(name="header")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_header_cmd(apk_path):
    """Get DEX file header information"""
    result = _try_daemon_call("dex_header")
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.dex_header())


@dex.command(name="class-names")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_class_names_cmd(apk_path):
    """Get quick class name list (without full class parsing)"""
    result = _try_daemon_call("dex_class_names")
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.dex_class_names())


@dex.command(name="hidden-api")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_hidden_api_cmd(apk_path):
    """Get hidden API list from DEX"""
    result = _try_daemon_call("dex_hidden_api")
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.dex_hidden_api())


@dex.command(name="disassemble")
@click.option(
    "--offset",
    required=True,
    type=int,
    help="Start offset (valid code segment offset, e.g. method code_off)",
)
@click.option(
    "--size", required=True, type=int, help="Number of bytes to disassemble"
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_disassemble_cmd(offset, size, apk_path):
    """Disassemble DEX bytecode at a given offset"""
    result = _try_daemon_call(
        "dex_disassemble", {"offset": offset, "size": size}
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.dex_disassemble(offset, size))


@dex.command(name="hierarchy")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_hierarchy_cmd(apk_path):
    """Get DEX class inheritance hierarchy tree"""
    result = _try_daemon_call("dex_hierarchy")
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.dex_hierarchy())


@dex.command(name="stats")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_stats_cmd(apk_path):
    """Get DEX statistics (counts, API version, format)"""
    result = _try_daemon_call("dex_stats")
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.dex_stats())


@dex.command(name="class")
@click.argument("class_name")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_class_cmd(class_name, apk_path):
    """Get detailed information for a specific DEX class"""
    result = _try_daemon_call("dex_class", {"class_name": class_name})
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.dex_class(class_name))


@dex.command(name="regex-strings")
@click.argument("pattern")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_regex_strings_cmd(pattern, apk_path):
    """Search DEX strings using regex (fast C-level implementation)"""
    result = _try_daemon_call("dex_regex_strings", {"pattern": pattern})
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.dex_regex_strings(pattern))


@dex.command(name="debug-info")
@click.option(
    "--class",
    "class_name",
    default=None,
    help="Class name to extract debug info for (optional)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_debug_info_cmd(class_name, apk_path):
    """Get DEX debug information"""
    result = _try_daemon_call("dex_debug_info", {"class_name": class_name})
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.dex_debug_info(class_name))


@dex.command(name="encoded-fields")
@click.option(
    "--class",
    "class_name",
    default=None,
    help="Filter by class name (optional)",
)
@click.option(
    "--limit", default=None, type=int, help="Limit number of results"
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_encoded_fields_cmd(class_name, limit, apk_path):
    """List all EncodedField (low-level field table)"""
    result = _try_daemon_call(
        "dex_encoded_fields", {"class_name": class_name, "limit": limit}
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.dex_encoded_fields(class_name, limit))


@dex.command(name="encoded-methods")
@click.option(
    "--class",
    "class_name",
    default=None,
    help="Filter by class name (optional)",
)
@click.option(
    "--limit", default=None, type=int, help="Limit number of results"
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_encoded_methods_cmd(class_name, limit, apk_path):
    """List all EncodedMethod (low-level method table)"""
    result = _try_daemon_call(
        "dex_encoded_methods", {"class_name": class_name, "limit": limit}
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.dex_encoded_methods(class_name, limit))


@dex.command(name="encoded-method")
@click.argument("method_name")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_encoded_method_cmd(method_name, apk_path):
    """Find EncodedMethod by method name (across all classes)"""
    result = _try_daemon_call(
        "dex_encoded_method", {"method_name": method_name}
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.dex_encoded_method(method_name))


@dex.command(name="encoded-method-descriptor")
@click.argument("class_name")
@click.argument("method_name")
@click.argument("descriptor")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_encoded_method_descriptor_cmd(
    class_name, method_name, descriptor, apk_path
):
    """Find EncodedMethod by class+method+descriptor (handles overloads)"""
    result = _try_daemon_call(
        "dex_encoded_method_descriptor",
        {
            "class_name": class_name,
            "method_name": method_name,
            "descriptor": descriptor,
        },
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(
        skills.dex_encoded_method_descriptor(
            class_name, method_name, descriptor
        )
    )


@dex.command(name="cm-lookup")
@click.argument("idx", type=int)
@click.option(
    "--kind",
    default="string",
    type=click.Choice(["string", "method", "field", "type"]),
    help="Constant pool kind",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_cm_lookup_cmd(idx, kind, apk_path):
    """Look up ClassManager constant pool entry by index"""
    result = _try_daemon_call("dex_cm_lookup", {"idx": idx, "kind": kind})
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.dex_cm_lookup(idx, kind))


@dex.command(name="fields-id")
@click.option(
    "--limit", default=None, type=int, help="Limit number of results"
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_fields_id_cmd(limit, apk_path):
    """Get DEX field index table (FieldIdItem)"""
    result = _try_daemon_call("dex_fields_id", {"limit": limit})
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.dex_fields_id(limit))


@dex.command(name="version")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_version_cmd(apk_path):
    """Get DEX version number"""
    result = _try_daemon_call("dex_version")
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.dex_version())


# ----------------------------------------------------------------
# 第六轮：DEX 底层 item 表与计数
# ----------------------------------------------------------------


def _dex_loader(apk_path):
    """加载 APK 并返回 skills 实例（供 dex 命令复用）"""
    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return None
        skills.load_apk(apk_path)
    return skills


@dex.command(name="items")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_items_cmd(apk_path):
    """Get low-level DEX item tables (header/codes/string_data/fields_id/methods_id/classes_def)"""
    result = _try_daemon_call("dex_items")
    if result is not None:
        _output_json(result)
        return
    skills = _dex_loader(apk_path)
    if skills is not None:
        _output_json(skills.dex_items())


@dex.command(name="lens")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_lens_cmd(apk_path):
    """Get DEX table lengths (classes/methods/strings/fields/encoded_*)"""
    result = _try_daemon_call("dex_lens")
    if result is not None:
        _output_json(result)
        return
    skills = _dex_loader(apk_path)
    if skills is not None:
        _output_json(skills.dex_lens())


@dex.command(name="class-manager")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_class_manager_cmd(apk_path):
    """Get DEX ClassManager summary (constant pool manager)"""
    result = _try_daemon_call("dex_class_manager")
    if result is not None:
        _output_json(result)
        return
    skills = _dex_loader(apk_path)
    if skills is not None:
        _output_json(skills.dex_class_manager())


# ----------------------------------------------------------------
# 第七轮：DEX 按类 / 按 idx 的 encoded 查询
# ----------------------------------------------------------------


@dex.command(name="encoded-fields-class")
@click.argument("class_name")
@click.option(
    "--limit", default=None, type=int, help="Max number of fields to return"
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_encoded_fields_class_cmd(class_name, limit, apk_path):
    """Get all EncodedField of a specific class (class field table)"""
    result = _try_daemon_call(
        "dex_encoded_fields_class", {"class_name": class_name, "limit": limit}
    )
    if result is not None:
        _output_json(result)
        return
    skills = _dex_loader(apk_path)
    if skills is not None:
        _output_json(skills.dex_encoded_fields_class(class_name, limit))


@dex.command(name="encoded-methods-class")
@click.argument("class_name")
@click.option(
    "--limit", default=None, type=int, help="Max number of methods to return"
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_encoded_methods_class_cmd(class_name, limit, apk_path):
    """Get all EncodedMethod of a specific class (class method table)"""
    result = _try_daemon_call(
        "dex_encoded_methods_class", {"class_name": class_name, "limit": limit}
    )
    if result is not None:
        _output_json(result)
        return
    skills = _dex_loader(apk_path)
    if skills is not None:
        _output_json(skills.dex_encoded_methods_class(class_name, limit))


@dex.command(name="encoded-method-by-idx")
@click.argument("idx", type=int)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_encoded_method_by_idx_cmd(idx, apk_path):
    """Get EncodedMethod by DEX method index"""
    result = _try_daemon_call("dex_encoded_method_by_idx", {"idx": idx})
    if result is not None:
        _output_json(result)
        return
    skills = _dex_loader(apk_path)
    if skills is not None:
        _output_json(skills.dex_encoded_method_by_idx(idx))


@dex.command(name="encoded-field-by-name")
@click.argument("name")
@click.option(
    "--limit", default=None, type=int, help="Max number of fields to return"
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_encoded_field_by_name_cmd(name, limit, apk_path):
    """Get EncodedField by field name (across all classes)"""
    result = _try_daemon_call(
        "dex_encoded_field_by_name", {"name": name, "limit": limit}
    )
    if result is not None:
        _output_json(result)
        return
    skills = _dex_loader(apk_path)
    if skills is not None:
        _output_json(skills.dex_encoded_field_by_name(name, limit))


@dex.command(name="encoded-field-descriptor")
@click.argument("class_name")
@click.argument("field_name")
@click.argument("descriptor")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_encoded_field_descriptor_cmd(
    class_name, field_name, descriptor, apk_path
):
    """Find EncodedField by class + field + descriptor (exact match)"""
    result = _try_daemon_call(
        "dex_encoded_field_descriptor",
        {
            "class_name": class_name,
            "field_name": field_name,
            "descriptor": descriptor,
        },
    )
    if result is not None:
        _output_json(result)
        return
    skills = _dex_loader(apk_path)
    if skills is not None:
        _output_json(
            skills.dex_encoded_field_descriptor(
                class_name, field_name, descriptor
            )
        )


@dex.command(name="method-info")
@click.argument("class_name")
@click.argument("method_name")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_method_info_cmd(class_name, method_name, apk_path):
    """Method signature-level info (registers/params mapping/locals/address)"""
    result = _try_daemon_call(
        "dex_method_info",
        {"class_name": class_name, "method_name": method_name},
    )
    if result is not None:
        _output_json(result)
        return
    skills = _dex_loader(apk_path)
    if skills is not None:
        _output_json(skills.dex_method_info(class_name, method_name))


@dex.command(name="method-instructions")
@click.argument("class_name")
@click.argument("method_name")
@click.option(
    "--limit",
    default=None,
    type=int,
    help="Max number of instructions to return",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_method_instructions_cmd(class_name, method_name, limit, apk_path):
    """Disassemble all Dalvik instructions of a method (instruction stream)"""
    result = _try_daemon_call(
        "dex_method_instructions",
        {"class_name": class_name, "method_name": method_name, "limit": limit},
    )
    if result is not None:
        _output_json(result)
        return
    skills = _dex_loader(apk_path)
    if skills is not None:
        _output_json(
            skills.dex_method_instructions(class_name, method_name, limit)
        )


@dex.command(name="method-code")
@click.argument("class_name")
@click.argument("method_name")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_method_code_cmd(class_name, method_name, apk_path):
    """Get method DalvikCode low-level info (register frame + try/catch + handlers)"""
    result = _try_daemon_call(
        "dex_method_code",
        {"class_name": class_name, "method_name": method_name},
    )
    if result is not None:
        _output_json(result)
        return
    skills = _dex_loader(apk_path)
    if skills is not None:
        _output_json(skills.dex_method_code(class_name, method_name))


@dex.command(name="class-meta")
@click.argument("class_name")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_class_meta_cmd(class_name, apk_path):
    """Get ClassDefItem low-level meta (annotations/source_file/interfaces/superclass/offsets)"""
    result = _try_daemon_call("dex_class_meta", {"class_name": class_name})
    if result is not None:
        _output_json(result)
        return
    skills = _dex_loader(apk_path)
    if skills is not None:
        _output_json(skills.dex_class_meta(class_name))


@dex.command(name="class-data")
@click.argument("class_name")
@click.option(
    "--limit",
    default=None,
    type=int,
    help="Max items per category (direct/virtual/static/instance)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_class_data_cmd(class_name, limit, apk_path):
    """Get ClassDataItem categorized view (direct/virtual methods + static/instance fields)"""
    result = _try_daemon_call(
        "dex_class_data", {"class_name": class_name, "limit": limit}
    )
    if result is not None:
        _output_json(result)
        return
    skills = _dex_loader(apk_path)
    if skills is not None:
        _output_json(skills.dex_class_data(class_name, limit))


@dex.command(name="field-init-value")
@click.argument("class_name")
@click.argument("field_name")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_field_init_value_cmd(class_name, field_name, apk_path):
    """Get field initial value (hardcoded constant detection)"""
    result = _try_daemon_call(
        "dex_field_init_value",
        {"class_name": class_name, "field_name": field_name},
    )
    if result is not None:
        _output_json(result)
        return
    skills = _dex_loader(apk_path)
    if skills is not None:
        _output_json(skills.dex_field_init_value(class_name, field_name))


@dex.command(name="method-instructions-idx")
@click.argument("class_name")
@click.argument("method_name")
@click.option(
    "--limit",
    default=None,
    type=int,
    help="Max number of instructions to return",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_method_instructions_idx_cmd(class_name, method_name, limit, apk_path):
    """Disassemble all instructions of a method with byte offset idx"""
    result = _try_daemon_call(
        "dex_method_instructions_idx",
        {"class_name": class_name, "method_name": method_name, "limit": limit},
    )
    if result is not None:
        _output_json(result)
        return
    skills = _dex_loader(apk_path)
    if skills is not None:
        _output_json(
            skills.dex_method_instructions_idx(class_name, method_name, limit)
        )


@dex.command(name="proto-ids")
@click.option(
    "--limit", default=None, type=int, help="Max number of protos to return"
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_proto_ids_cmd(limit, apk_path):
    """List DEX method prototype table (ProtoIdItem: shorty/return_type/parameters)"""
    result = _try_daemon_call("dex_proto_ids", {"limit": limit})
    if result is not None:
        _output_json(result)
        return
    skills = _dex_loader(apk_path)
    if skills is not None:
        _output_json(skills.dex_proto_ids(limit))


@dex.command(name="type-ids")
@click.option(
    "--limit", default=None, type=int, help="Max number of types to return"
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_type_ids_cmd(limit, apk_path):
    """List DEX type constant pool (type_ids: descriptor_idx -> type descriptor)"""
    result = _try_daemon_call("dex_type_ids", {"limit": limit})
    if result is not None:
        _output_json(result)
        return
    skills = _dex_loader(apk_path)
    if skills is not None:
        _output_json(skills.dex_type_ids(limit))


@dex.command(name="annotations")
@click.option(
    "--class",
    "class_name",
    default=None,
    help="Class name (Dalvik). Omit to scan all annotated classes",
)
@click.option(
    "--limit",
    default=None,
    type=int,
    help="Max classes to scan (when no --class)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_annotations_cmd(class_name, limit, apk_path):
    """List DEX annotation directory (class/field/method/parameter annotations)"""
    result = _try_daemon_call(
        "dex_annotations", {"class_name": class_name, "limit": limit}
    )
    if result is not None:
        _output_json(result)
        return
    skills = _dex_loader(apk_path)
    if skills is not None:
        _output_json(skills.dex_annotations(class_name, limit))


@dex.command(name="static-values")
@click.argument("class_name")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_static_values_cmd(class_name, apk_path):
    """Get class static values array (EncodedArray: all static field init values)"""
    result = _try_daemon_call("dex_static_values", {"class_name": class_name})
    if result is not None:
        _output_json(result)
        return
    skills = _dex_loader(apk_path)
    if skills is not None:
        _output_json(skills.dex_static_values(class_name))


@dex.command(name="method-id-by-name")
@click.argument("name")
@click.option("--limit", default=None, type=int, help="Max results per DEX")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_method_id_by_name_cmd(name, limit, apk_path):
    """Search method_ids constant-pool table by method name (includes external refs)"""
    result = _try_daemon_call(
        "dex_method_id_by_name", {"name": name, "limit": limit}
    )
    if result is not None:
        _output_json(result)
        return
    skills = _dex_loader(apk_path)
    if skills is not None:
        _output_json(skills.dex_method_id_by_name(name, limit))


@dex.command(name="method-ids")
@click.option("--limit", default=None, type=int, help="Max results per DEX")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_method_ids_cmd(limit, apk_path):
    """List all method_ids constant-pool entries (includes external refs, no code)"""
    result = _try_daemon_call("dex_method_ids", {"limit": limit})
    if result is not None:
        _output_json(result)
        return
    skills = _dex_loader(apk_path)
    if skills is not None:
        _output_json(skills.dex_method_ids(limit))


@dex.command(name="field-id-by-name")
@click.argument("name")
@click.option("--limit", default=None, type=int, help="Max results per DEX")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_field_id_by_name_cmd(name, limit, apk_path):
    """Search field_ids constant-pool table by field name (includes external refs)"""
    result = _try_daemon_call(
        "dex_field_id_by_name", {"name": name, "limit": limit}
    )
    if result is not None:
        _output_json(result)
        return
    skills = _dex_loader(apk_path)
    if skills is not None:
        _output_json(skills.dex_field_id_by_name(name, limit))


@dex.command(name="encoded-method-class-method")
@click.argument("class_name")
@click.argument("method_name")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def dex_encoded_method_class_method_cmd(class_name, method_name, apk_path):
    """Find EncodedMethod by class + method name (no descriptor needed)"""
    result = _try_daemon_call(
        "dex_encoded_method_class_method",
        {"class_name": class_name, "method_name": method_name},
    )
    if result is not None:
        _output_json(result)
        return
    skills = _dex_loader(apk_path)
    if skills is not None:
        _output_json(
            skills.dex_encoded_method_class_method(class_name, method_name)
        )


# ================================================================
# Analysis 命令组
# ================================================================


@entry_point.group(help="Static analysis commands")
def analysis():
    """静态分析命令组"""
    pass


@analysis.command(name="xrefs-from")
@click.argument("class_name")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_xrefs_from_cmd(class_name, apk_path):
    """Find what references this class (XrefFrom)"""
    result = _try_daemon_call(
        "analysis_xrefs_from", {"class_name": class_name}
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_xrefs_from(class_name))


@analysis.command(name="xrefs-to")
@click.argument("class_name")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_xrefs_to_cmd(class_name, apk_path):
    """Find what this class references (XrefTo)"""
    result = _try_daemon_call("analysis_xrefs_to", {"class_name": class_name})
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_xrefs_to(class_name))


@analysis.command(name="method-xrefs")
@click.argument("class_name")
@click.argument("method_name")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_method_xrefs_cmd(class_name, method_name, apk_path):
    """Find cross-references for a specific method"""
    result = _try_daemon_call(
        "analysis_method_xrefs",
        {"class_name": class_name, "method_name": method_name},
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_method_xrefs(class_name, method_name))


@analysis.command(name="callgraph")
@click.option("-o", "--output", required=True, help="Output file path")
@click.option(
    "-f",
    "--format",
    "fmt",
    type=click.Choice(["gml", "gexf", "graphml", "net"]),
    default="gml",
    help="Output format (default: gml)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_callgraph_cmd(output, fmt, apk_path):
    """Generate and export call graph"""
    result = _try_daemon_call(
        "analysis_callgraph", {"output": output, "fmt": fmt}
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_callgraph(output, fmt))


@analysis.command(name="find-classes")
@click.argument("pattern")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_find_classes_cmd(pattern, apk_path):
    """Search classes by regex pattern"""
    result = _try_daemon_call("analysis_find_classes", {"pattern": pattern})
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_find_classes(pattern))


@analysis.command(name="find-methods")
@click.argument("pattern")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_find_methods_cmd(pattern, apk_path):
    """Search methods by regex pattern"""
    result = _try_daemon_call("analysis_find_methods", {"pattern": pattern})
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_find_methods(pattern))


@analysis.command(name="find-strings")
@click.argument("pattern")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_find_strings_cmd(pattern, apk_path):
    """Search strings by regex pattern"""
    result = _try_daemon_call("analysis_find_strings", {"pattern": pattern})
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_find_strings(pattern))


@analysis.command(name="permission-usage")
@click.argument("permission")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_permission_usage_cmd(permission, apk_path):
    """Trace usage of a specific permission"""
    result = _try_daemon_call(
        "analysis_permission_usage", {"permission": permission}
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_permission_usage(permission))


@analysis.command(name="api-usage")
@click.option(
    "--limit", default=None, type=int, help="Limit number of results"
)
@click.option(
    "--group-by-class", is_flag=True, help="Group API usage by class"
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_api_usage_cmd(limit, group_by_class, apk_path):
    """Get Android API usage"""
    result = _try_daemon_call(
        "analysis_api_usage",
        {"limit": limit, "group_by_class": group_by_class},
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_api_usage(limit, group_by_class))


@analysis.command(name="internal-classes")
@click.option(
    "--filter",
    "filter_regex",
    default=None,
    help="Regex filter for class names",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_internal_classes_cmd(filter_regex, apk_path):
    """List internal (app) classes"""
    result = _try_daemon_call(
        "analysis_internal_classes", {"filter_regex": filter_regex}
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_internal_classes(filter_regex))


@analysis.command(name="external-classes")
@click.option(
    "--filter",
    "filter_regex",
    default=None,
    help="Regex filter for class names",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_external_classes_cmd(filter_regex, apk_path):
    """List external (dependency) classes"""
    result = _try_daemon_call(
        "analysis_external_classes", {"filter_regex": filter_regex}
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_external_classes(filter_regex))


@analysis.command(name="internal-methods")
@click.option(
    "--filter",
    "filter_regex",
    default=None,
    help="Regex filter for method names",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_internal_methods_cmd(filter_regex, apk_path):
    """List internal (app) methods"""
    result = _try_daemon_call(
        "analysis_internal_methods", {"filter_regex": filter_regex}
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_internal_methods(filter_regex))


@analysis.command(name="external-methods")
@click.option(
    "--filter",
    "filter_regex",
    default=None,
    help="Regex filter for method names",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_external_methods_cmd(filter_regex, apk_path):
    """List external (dependency) methods"""
    result = _try_daemon_call(
        "analysis_external_methods", {"filter_regex": filter_regex}
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_external_methods(filter_regex))


@analysis.command(name="field-xrefs")
@click.argument("class_name")
@click.argument("field_name")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_field_xrefs_cmd(class_name, field_name, apk_path):
    """Find cross-references for a specific field"""
    result = _try_daemon_call(
        "analysis_field_xrefs",
        {"class_name": class_name, "field_name": field_name},
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_field_xrefs(class_name, field_name))


@analysis.command(name="field-xrefs-detail")
@click.argument("class_name")
@click.argument("field_name")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_field_xrefs_detail_cmd(class_name, field_name, apk_path):
    """Get field read/write refs with per-access offset (not deduped)"""
    result = _try_daemon_call(
        "analysis_field_xrefs_detail",
        {"class_name": class_name, "field_name": field_name},
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_field_xrefs_detail(class_name, field_name))


@analysis.command(name="find-fields")
@click.argument("pattern")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_find_fields_cmd(pattern, apk_path):
    """Search fields by regex pattern"""
    result = _try_daemon_call("analysis_find_fields", {"pattern": pattern})
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_find_fields(pattern))


@analysis.command(name="permissions-map")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_permissions_map_cmd(apk_path):
    """Get complete permissions mapping from analysis"""
    result = _try_daemon_call("analysis_permissions_map")
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_permissions_map())


@analysis.command(name="class-exists")
@click.argument("class_name")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_class_exists_cmd(class_name, apk_path):
    """Check if a class exists in analysis (boolean)"""
    result = _try_daemon_call(
        "analysis_class_exists", {"class_name": class_name}
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_class_exists(class_name))


@analysis.command(name="method-analysis")
@click.argument("class_name")
@click.argument("method_name")
@click.argument("descriptor")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_method_analysis_cmd(
    class_name, method_name, descriptor, apk_path
):
    """Get method analysis by class+method+descriptor (with full xref)"""
    result = _try_daemon_call(
        "analysis_method_analysis",
        {
            "class_name": class_name,
            "method_name": method_name,
            "descriptor": descriptor,
        },
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(
        skills.analysis_method_analysis(class_name, method_name, descriptor)
    )


@analysis.command(name="strings-analysis")
@click.option(
    "--limit", default=None, type=int, help="Max number of strings to return"
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_strings_analysis_cmd(limit, apk_path):
    """Get all string analyses (with reference locations)"""
    result = _try_daemon_call("analysis_strings_analysis", {"limit": limit})
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_strings_analysis(limit))


@analysis.command(name="security-hotspots")
@click.option(
    "--limit",
    default=50,
    type=int,
    help="Max samples per hotspot category (default 50)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_security_hotspots_cmd(limit, apk_path):
    """Scan all methods for security-sensitive calls (reflection/crypto/exec/native/etc.)"""
    result = _try_daemon_call("analysis_security_hotspots", {"limit": limit})
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_security_hotspots(limit))


@analysis.command(name="hardcoded-secrets")
@click.option(
    "--limit",
    default=100,
    type=int,
    help="Max findings per category (default 100)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_hardcoded_secrets_cmd(limit, apk_path):
    """Scan static field values for hardcoded secrets (API keys/tokens/URLs/private keys)"""
    result = _try_daemon_call("analysis_hardcoded_secrets", {"limit": limit})
    if result is not None:
        _output_json(result)
        return
    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_hardcoded_secrets(limit))


@analysis.command(name="get-method")
@click.argument("class_name")
@click.argument("method_name")
@click.argument("descriptor")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_get_method_cmd(class_name, method_name, descriptor, apk_path):
    """Get underlying EncodedMethod metadata by class+method+descriptor"""
    result = _try_daemon_call(
        "analysis_get_method",
        {
            "class_name": class_name,
            "method_name": method_name,
            "descriptor": descriptor,
        },
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(
        skills.analysis_get_method(class_name, method_name, descriptor)
    )


@analysis.command(name="find-fields-advanced")
@click.option("--classname", default=".*", help="Regex for class name")
@click.option("--fieldname", default=".*", help="Regex for field name")
@click.option("--fieldtype", default=".*", help="Regex for field type")
@click.option(
    "--accessflags",
    default=".*",
    help="Regex for access flags (e.g. private|static)",
)
@click.option(
    "--limit", default=None, type=int, help="Limit number of results"
)
@click.option("--with-xrefs", is_flag=True, help="Include full xref lists")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_find_fields_advanced_cmd(
    classname, fieldname, fieldtype, accessflags, limit, with_xrefs, apk_path
):
    """Multi-dimensional regex field search (native find_fields)"""
    result = _try_daemon_call(
        "analysis_find_fields_advanced",
        {
            "classname": classname,
            "fieldname": fieldname,
            "fieldtype": fieldtype,
            "accessflags": accessflags,
            "limit": limit,
            "with_xrefs": with_xrefs,
        },
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(
        skills.analysis_find_fields_advanced(
            classname, fieldname, fieldtype, accessflags, limit, with_xrefs
        )
    )


@analysis.command(name="find-methods-advanced")
@click.option("--classname", default=".*", help="Regex for class name")
@click.option("--methodname", default=".*", help="Regex for method name")
@click.option(
    "--descriptor",
    default=".*",
    help="Regex for method descriptor (params + return type)",
)
@click.option(
    "--accessflags",
    default=".*",
    help="Regex for access flags (e.g. public.*static.*native)",
)
@click.option(
    "--no-external",
    is_flag=True,
    help="Exclude external (non-DEX-implemented) methods",
)
@click.option(
    "--limit", default=500, type=int, help="Max results (default 500)"
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_find_methods_advanced_cmd(
    classname,
    methodname,
    descriptor,
    accessflags,
    no_external,
    limit,
    apk_path,
):
    """Multi-dimensional regex method search: class x method x descriptor x accessflags (native find_methods)"""
    params = {
        "classname": classname,
        "methodname": methodname,
        "descriptor": descriptor,
        "accessflags": accessflags,
        "no_external": no_external,
        "limit": limit,
    }
    result = _try_daemon_call("analysis_find_methods_advanced", params)
    if result is not None:
        _output_json(result)
        return
    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(
        skills.analysis_find_methods_advanced(
            classname, methodname, descriptor, accessflags, no_external, limit
        )
    )


@analysis.command(name="find-classes-advanced")
@click.option("--name", default=".*", help="Regex for class name")
@click.option(
    "--no-external",
    is_flag=True,
    help="Exclude external (Android/third-party) classes",
)
@click.option(
    "--limit", default=500, type=int, help="Max results (default 500)"
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_find_classes_advanced_cmd(name, no_external, limit, apk_path):
    """Multi-dimensional regex class search: name regex + exclude-external (native find_classes)"""
    params = {"name": name, "no_external": no_external, "limit": limit}
    result = _try_daemon_call("analysis_find_classes_advanced", params)
    if result is not None:
        _output_json(result)
        return
    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(
        skills.analysis_find_classes_advanced(name, no_external, limit)
    )


@analysis.command(name="field-analysis")
@click.argument("class_name")
@click.argument("field_name")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_field_analysis_cmd(class_name, field_name, apk_path):
    """Get full field analysis (with read/write xref details)"""
    result = _try_daemon_call(
        "analysis_field_analysis",
        {"class_name": class_name, "field_name": field_name},
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_field_analysis(class_name, field_name))


# ----------------------------------------------------------------
# 第五轮：Analysis 类/方法/字符串遗漏能力
# ----------------------------------------------------------------


def _analysis_class_loader(class_name, apk_path):
    """加载 APK 并返回 skills 实例（供单参数类命令复用）"""
    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return None
        skills.load_apk(apk_path)
    return skills


@analysis.command(name="class-hierarchy-info")
@click.argument("class_name")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_class_hierarchy_info_cmd(class_name, apk_path):
    """Get class inheritance info (extends / implements)"""
    result = _try_daemon_call(
        "analysis_class_hierarchy_info", {"class_name": class_name}
    )
    if result is not None:
        _output_json(result)
        return
    skills = _analysis_class_loader(class_name, apk_path)
    if skills is not None:
        _output_json(skills.analysis_class_hierarchy_info(class_name))


@analysis.command(name="class-xref-new-instance")
@click.argument("class_name")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_class_xref_new_instance_cmd(class_name, apk_path):
    """Get new-instance xrefs of a class (where it is instantiated)"""
    result = _try_daemon_call(
        "analysis_class_xref_new_instance", {"class_name": class_name}
    )
    if result is not None:
        _output_json(result)
        return
    skills = _analysis_class_loader(class_name, apk_path)
    if skills is not None:
        _output_json(skills.analysis_class_xref_new_instance(class_name))


@analysis.command(name="class-xref-const-class")
@click.argument("class_name")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_class_xref_const_class_cmd(class_name, apk_path):
    """Get const-class xrefs of a class (where the class literal is referenced)"""
    result = _try_daemon_call(
        "analysis_class_xref_const_class", {"class_name": class_name}
    )
    if result is not None:
        _output_json(result)
        return
    skills = _analysis_class_loader(class_name, apk_path)
    if skills is not None:
        _output_json(skills.analysis_class_xref_const_class(class_name))


@analysis.command(name="class-detail")
@click.argument("class_name")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_class_detail_cmd(class_name, apk_path):
    """Get comprehensive class info (methods/inheritance/xref stats/vm_class type)"""
    result = _try_daemon_call(
        "analysis_class_detail", {"class_name": class_name}
    )
    if result is not None:
        _output_json(result)
        return
    skills = _analysis_class_loader(class_name, apk_path)
    if skills is not None:
        _output_json(skills.analysis_class_detail(class_name))


@analysis.command(name="method-basic-blocks")
@click.argument("class_name")
@click.argument("method_name")
@click.argument("descriptor")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_method_basic_blocks_cmd(
    class_name, method_name, descriptor, apk_path
):
    """Get basic blocks (CFG nodes) of a method"""
    result = _try_daemon_call(
        "analysis_method_basic_blocks",
        {
            "class_name": class_name,
            "method_name": method_name,
            "descriptor": descriptor,
        },
    )
    if result is not None:
        _output_json(result)
        return
    skills = _analysis_class_loader(class_name, apk_path)
    if skills is not None:
        _output_json(
            skills.analysis_method_basic_blocks(
                class_name, method_name, descriptor
            )
        )


@analysis.command(name="method-exceptions")
@click.argument("class_name")
@click.argument("method_name")
@click.argument("descriptor")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_method_exceptions_cmd(
    class_name, method_name, descriptor, apk_path
):
    """Get try/catch exception table for a method"""
    result = _try_daemon_call(
        "analysis_method_exceptions",
        {
            "class_name": class_name,
            "method_name": method_name,
            "descriptor": descriptor,
        },
    )
    if result is not None:
        _output_json(result)
        return
    skills = _analysis_class_loader(class_name, apk_path)
    if skills is not None:
        _output_json(
            skills.analysis_method_exceptions(
                class_name, method_name, descriptor
            )
        )


@analysis.command(name="method-detail")
@click.argument("class_name")
@click.argument("method_name")
@click.argument("descriptor")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_method_detail_cmd(class_name, method_name, descriptor, apk_path):
    """Get comprehensive method info (full_name/access/length/xref stats/bb count)"""
    result = _try_daemon_call(
        "analysis_method_detail",
        {
            "class_name": class_name,
            "method_name": method_name,
            "descriptor": descriptor,
        },
    )
    if result is not None:
        _output_json(result)
        return
    skills = _analysis_class_loader(class_name, apk_path)
    if skills is not None:
        _output_json(
            skills.analysis_method_detail(class_name, method_name, descriptor)
        )


@analysis.command(name="method-api-info")
@click.argument("class_name")
@click.argument("method_name")
@click.argument("descriptor")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_method_api_info_cmd(
    class_name, method_name, descriptor, apk_path
):
    """Get method API/permission annotation (is_android_api/domain_flag/restriction_flag/apilist)"""
    result = _try_daemon_call(
        "analysis_method_api_info",
        {
            "class_name": class_name,
            "method_name": method_name,
            "descriptor": descriptor,
        },
    )
    if result is not None:
        _output_json(result)
        return
    skills = _analysis_class_loader(class_name, apk_path)
    if skills is not None:
        _output_json(
            skills.analysis_method_api_info(
                class_name, method_name, descriptor
            )
        )


@analysis.command(name="android-api-usage")
@click.option(
    "--limit", default=None, type=int, help="Max number of APIs to return"
)
@click.option(
    "--with-xrefs",
    is_flag=True,
    default=False,
    help="Expand caller xrefs for each API",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_android_api_usage_cmd(limit, with_xrefs, apk_path):
    """List all Android platform APIs used by the APK (batch)"""
    result = _try_daemon_call(
        "analysis_android_api_usage",
        {"limit": limit, "with_xrefs": with_xrefs},
    )
    if result is not None:
        _output_json(result)
        return
    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_android_api_usage(limit, with_xrefs))


@analysis.command(name="method-xrefs-detail")
@click.argument("class_name")
@click.argument("method_name")
@click.argument("descriptor")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_method_xrefs_detail_cmd(
    class_name, method_name, descriptor, apk_path
):
    """Get full method-level xref lists (from/to/read/write/new_instance/const_class)"""
    result = _try_daemon_call(
        "analysis_method_xrefs_detail",
        {
            "class_name": class_name,
            "method_name": method_name,
            "descriptor": descriptor,
        },
    )
    if result is not None:
        _output_json(result)
        return
    skills = _analysis_class_loader(class_name, apk_path)
    if skills is not None:
        _output_json(
            skills.analysis_method_xrefs_detail(
                class_name, method_name, descriptor
            )
        )


@analysis.command(name="strings-overwritten")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_strings_overwritten_cmd(apk_path):
    """Get overwritten strings (is_overwritten / get_orig_value)"""
    result = _try_daemon_call("analysis_strings_overwritten")
    if result is not None:
        _output_json(result)
        return
    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_strings_overwritten())


@analysis.command(name="class-fields")
@click.argument("class_name")
@click.option(
    "--limit", default=None, type=int, help="Max number of fields to return"
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_class_fields_cmd(class_name, limit, apk_path):
    """List all fields of a class with xref read/write counts"""
    result = _try_daemon_call(
        "analysis_class_fields", {"class_name": class_name, "limit": limit}
    )
    if result is not None:
        _output_json(result)
        return
    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_class_fields(class_name, limit))


@analysis.command(name="class-fields-xref")
@click.argument("class_name")
@click.option(
    "--xref-limit",
    default=20,
    type=int,
    help="Max read/write refs to expand per field (default 20)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_class_fields_xref_cmd(class_name, xref_limit, apk_path):
    """List all fields of a class with full read/write xref sources (which methods)"""
    result = _try_daemon_call(
        "analysis_class_fields_xref",
        {"class_name": class_name, "xref_limit": xref_limit},
    )
    if result is not None:
        _output_json(result)
        return
    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_class_fields_xref(class_name, xref_limit))


@analysis.command(name="string-info")
@click.argument("value")
@click.option(
    "--xref-limit",
    default=None,
    type=int,
    help="Max number of xref_from refs to return",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_string_info_cmd(value, xref_limit, apk_path):
    """Get single string analysis (orig_value/current_value/is_overwritten + xrefs)"""
    result = _try_daemon_call(
        "analysis_string_info", {"value": value, "xref_limit": xref_limit}
    )
    if result is not None:
        _output_json(result)
        return
    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_string_info(value, xref_limit))


# ----------------------------------------------------------------
# 第十七轮：方法全貌聚合
# ----------------------------------------------------------------


@analysis.command(name="method-summary")
@click.argument("class_name")
@click.argument("method_name")
@click.option(
    "--descriptor",
    default=None,
    help="Method descriptor (optional; first match if omitted)",
)
@click.option(
    "--no-source", is_flag=True, help="Exclude decompiled Java source"
)
@click.option(
    "--xref-limit",
    default=10,
    type=int,
    help="Max refs per xref category (0 = all)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_method_summary_cmd(
    class_name, method_name, descriptor, no_source, xref_limit, apk_path
):
    """Aggregate method overview (info + 6 xref summaries + CFG/exception counts + source)"""
    params = {
        "class_name": class_name,
        "method_name": method_name,
        "descriptor": descriptor,
        "include_source": not no_source,
        "xref_limit": xref_limit if xref_limit != 0 else None,
    }
    result = _try_daemon_call("analysis_method_summary", params)
    if result is not None:
        _output_json(result)
        return
    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(
        skills.analysis_method_summary(
            class_name,
            method_name,
            descriptor,
            not no_source,
            xref_limit if xref_limit != 0 else None,
        )
    )


@analysis.command(name="method-reachable")
@click.argument("class_name")
@click.argument("method_name")
@click.option(
    "--descriptor",
    default=None,
    help="Method descriptor (optional; first match if omitted)",
)
@click.option(
    "--max-depth", default=3, type=int, help="Max recursion depth (default 3)"
)
@click.option(
    "--include-external",
    is_flag=True,
    help="Also recurse into external/API methods (may explode; use small depth)",
)
@click.option(
    "--max-nodes",
    default=5000,
    type=int,
    help="Node cap to prevent explosion (default 5000)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_method_reachable_cmd(
    class_name,
    method_name,
    descriptor,
    max_depth,
    include_external,
    max_nodes,
    apk_path,
):
    """Reachability analysis: methods reachable from a given method (recursive xref_to expansion)"""
    params = {
        "class_name": class_name,
        "method_name": method_name,
        "descriptor": descriptor,
        "max_depth": max_depth,
        "include_external": include_external,
        "max_nodes": max_nodes,
    }
    result = _try_daemon_call("analysis_method_reachable", params)
    if result is not None:
        _output_json(result)
        return
    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(
        skills.analysis_method_reachable(
            class_name,
            method_name,
            descriptor,
            max_depth,
            include_external,
            max_nodes,
        )
    )


@analysis.command(name="method-callers")
@click.argument("class_name")
@click.argument("method_name")
@click.option(
    "--descriptor",
    default=None,
    help="Method descriptor (optional; first match if omitted)",
)
@click.option(
    "--max-depth",
    default=3,
    type=int,
    help="Max reverse recursion depth (default 3)",
)
@click.option(
    "--include-external",
    is_flag=True,
    help="Also recurse into external/API methods (rarely useful upstream)",
)
@click.option(
    "--max-nodes",
    default=5000,
    type=int,
    help="Node cap to prevent explosion (default 5000)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_method_callers_cmd(
    class_name,
    method_name,
    descriptor,
    max_depth,
    include_external,
    max_nodes,
    apk_path,
):
    """Reverse reachability: callers that can reach a given method (recursive xref_from expansion)"""
    params = {
        "class_name": class_name,
        "method_name": method_name,
        "descriptor": descriptor,
        "max_depth": max_depth,
        "include_external": include_external,
        "max_nodes": max_nodes,
    }
    result = _try_daemon_call("analysis_method_callers", params)
    if result is not None:
        _output_json(result)
        return
    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(
        skills.analysis_method_callers(
            class_name,
            method_name,
            descriptor,
            max_depth,
            include_external,
            max_nodes,
        )
    )


@analysis.command(name="native-methods")
@click.option(
    "--limit",
    default=200,
    type=int,
    help="Max native methods to return (default 200)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_native_methods_cmd(limit, apk_path):
    """Enumerate all native (JNI) methods with declaring class and callers"""
    result = _try_daemon_call("analysis_native_methods", {"limit": limit})
    if result is not None:
        _output_json(result)
        return
    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_native_methods(limit))


@analysis.command(name="crypto-usage")
@click.option(
    "--limit",
    "per_type_limit",
    default=100,
    type=int,
    help="Max samples per category (default 100)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_crypto_usage_cmd(per_type_limit, apk_path):
    """Aggregate crypto API usage, resolve algorithm strings, flag weak crypto (ECB/DES/MD5/SHA1/RC4)"""
    result = _try_daemon_call(
        "analysis_crypto_usage", {"per_type_limit": per_type_limit}
    )
    if result is not None:
        _output_json(result)
        return
    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_crypto_usage(per_type_limit))


@analysis.command(name="reflection-targets")
@click.option(
    "--limit",
    "per_type_limit",
    default=100,
    type=int,
    help="Max samples per category (default 100)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_reflection_targets_cmd(per_type_limit, apk_path):
    """Resolve reflection call targets (Class.forName/getMethod string args) for deobfuscation"""
    result = _try_daemon_call(
        "analysis_reflection_targets", {"per_type_limit": per_type_limit}
    )
    if result is not None:
        _output_json(result)
        return
    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_reflection_targets(per_type_limit))


@analysis.command(name="url-endpoints")
@click.option(
    "--limit",
    "per_type_limit",
    default=200,
    type=int,
    help="Max samples per category (default 200)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_url_endpoints_cmd(per_type_limit, apk_path):
    """Extract URL/host/IP network endpoints from the string pool with referencing methods"""
    result = _try_daemon_call(
        "analysis_url_endpoints", {"per_type_limit": per_type_limit}
    )
    if result is not None:
        _output_json(result)
        return
    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_url_endpoints(per_type_limit))


@analysis.command(name="taint-path")
@click.argument("src_class")
@click.argument("src_method")
@click.argument("dst_class")
@click.argument("dst_method")
@click.option(
    "--src-descriptor",
    default=None,
    help="Source method descriptor (optional)",
)
@click.option(
    "--dst-descriptor", default=None, help="Sink method descriptor (optional)"
)
@click.option(
    "--max-depth", default=8, type=int, help="Max search depth (default 8)"
)
@click.option(
    "--max-nodes",
    default=20000,
    type=int,
    help="Max nodes visited (default 20000)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_taint_path_cmd(
    src_class,
    src_method,
    dst_class,
    dst_method,
    src_descriptor,
    dst_descriptor,
    max_depth,
    max_nodes,
    apk_path,
):
    """Find a forward call path from a source method to a sink method (source->sink chain)"""
    params = {
        "src_class": src_class,
        "src_method": src_method,
        "dst_class": dst_class,
        "dst_method": dst_method,
        "src_descriptor": src_descriptor,
        "dst_descriptor": dst_descriptor,
        "max_depth": max_depth,
        "max_nodes": max_nodes,
    }
    result = _try_daemon_call("analysis_taint_path", params)
    if result is not None:
        _output_json(result)
        return
    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(
        skills.analysis_taint_path(
            src_class,
            src_method,
            dst_class,
            dst_method,
            src_descriptor,
            dst_descriptor,
            max_depth,
            max_nodes,
        )
    )


@analysis.command(name="webview-security")
@click.option(
    "--limit",
    "per_type_limit",
    default=100,
    type=int,
    help="Max samples per category (default 100)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_webview_security_cmd(per_type_limit, apk_path):
    """Audit WebView security configuration (JS bridge/file access/JS/debug risky settings + findings)"""
    result = _try_daemon_call(
        "analysis_webview_security", {"per_type_limit": per_type_limit}
    )
    if result is not None:
        _output_json(result)
        return
    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_webview_security(per_type_limit))


@analysis.command(name="ssl-safety")
@click.option(
    "--limit",
    "per_type_limit",
    default=100,
    type=int,
    help="Max samples per category (default 100)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_ssl_safety_cmd(per_type_limit, apk_path):
    """Detect SSL/TLS validation bypass (insecure TrustManager/HostnameVerifier + bypass calls, MITM audit)"""
    result = _try_daemon_call(
        "analysis_ssl_safety", {"per_type_limit": per_type_limit}
    )
    if result is not None:
        _output_json(result)
        return
    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_ssl_safety(per_type_limit))


@analysis.command(name="insecure-storage")
@click.option(
    "--limit",
    "per_type_limit",
    default=100,
    type=int,
    help="Max samples per category (default 100)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_insecure_storage_cmd(per_type_limit, apk_path):
    """Audit insecure data storage (external storage/world-readable modes/plaintext prefs+db, OWASP M9)"""
    result = _try_daemon_call(
        "analysis_insecure_storage", {"per_type_limit": per_type_limit}
    )
    if result is not None:
        _output_json(result)
        return
    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_insecure_storage(per_type_limit))


@analysis.command(name="sql-injection")
@click.option(
    "--limit",
    "per_type_limit",
    default=100,
    type=int,
    help="Max samples per category (default 100)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_sql_injection_cmd(per_type_limit, apk_path):
    """Audit SQL injection surface (rawQuery/execSQL/query execution points, OWASP M7)"""
    result = _try_daemon_call(
        "analysis_sql_injection", {"per_type_limit": per_type_limit}
    )
    if result is not None:
        _output_json(result)
        return
    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_sql_injection(per_type_limit))


@analysis.command(name="pending-intent")
@click.option(
    "--limit",
    "per_type_limit",
    default=100,
    type=int,
    help="Max samples per category (default 100)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_pending_intent_cmd(per_type_limit, apk_path):
    """Audit PendingIntent mutability (missing FLAG_IMMUTABLE + Intent redirection surface)"""
    result = _try_daemon_call(
        "analysis_pending_intent", {"per_type_limit": per_type_limit}
    )
    if result is not None:
        _output_json(result)
        return
    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_pending_intent(per_type_limit))


def _analysis_audit_cli(method_name, per_type_limit, apk_path):
    """漏洞审计类 CLI 的共享执行体（daemon → fallback → per_type_limit 委托）。"""
    result = _try_daemon_call(method_name, {"per_type_limit": per_type_limit})
    if result is not None:
        _output_json(result)
        return
    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(getattr(skills, method_name)(per_type_limit))


@analysis.command(name="privacy-sinks")
@click.option(
    "--limit",
    "per_type_limit",
    default=100,
    type=int,
    help="Max samples per category (default 100)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_privacy_sinks_cmd(per_type_limit, apk_path):
    """Audit privacy data collection (device IDs/location/contacts/accounts/clipboard/camera-mic, OWASP M6)"""
    _analysis_audit_cli("analysis_privacy_sinks", per_type_limit, apk_path)


@analysis.command(name="telephony-sms")
@click.option(
    "--limit",
    "per_type_limit",
    default=100,
    type=int,
    help="Max samples per category (default 100)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_telephony_sms_cmd(per_type_limit, apk_path):
    """Audit telephony/SMS abuse (send/read SMS, dial, SMS interception, call monitoring)"""
    _analysis_audit_cli("analysis_telephony_sms", per_type_limit, apk_path)


@analysis.command(name="dynamic-code")
@click.option(
    "--limit",
    "per_type_limit",
    default=100,
    type=int,
    help="Max samples per category (default 100)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_dynamic_code_cmd(per_type_limit, apk_path):
    """Audit dynamic code loading (DexClassLoader/native libs/reflection, unpacking/malicious payload)"""
    _analysis_audit_cli("analysis_dynamic_code", per_type_limit, apk_path)


@analysis.command(name="persistence")
@click.option(
    "--limit",
    "per_type_limit",
    default=100,
    type=int,
    help="Max samples per category (default 100)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_persistence_cmd(per_type_limit, apk_path):
    """Audit persistence/background residency (device admin/accessibility/scheduled jobs/foreground service)"""
    _analysis_audit_cli("analysis_persistence", per_type_limit, apk_path)


@analysis.command(name="weak-random")
@click.option(
    "--limit",
    "per_type_limit",
    default=100,
    type=int,
    help="Max samples per category (default 100)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_weak_random_cmd(per_type_limit, apk_path):
    """Audit insecure randomness (java.util.Random/Math.random/fixed seed vs SecureRandom, OWASP M10)"""
    _analysis_audit_cli("analysis_weak_random", per_type_limit, apk_path)


@analysis.command(name="broadcast-safety")
@click.option(
    "--limit",
    "per_type_limit",
    default=100,
    type=int,
    help="Max samples per category (default 100)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_broadcast_safety_cmd(per_type_limit, apk_path):
    """Audit broadcast send/receive safety (unprotected broadcasts/dynamic receivers/sticky broadcasts)"""
    _analysis_audit_cli("analysis_broadcast_safety", per_type_limit, apk_path)


@analysis.command(name="provider-safety")
@click.option(
    "--limit",
    "per_type_limit",
    default=100,
    type=int,
    help="Max samples per category (default 100)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_provider_safety_cmd(per_type_limit, apk_path):
    """Audit ContentProvider safety (openFile path traversal/URI permission grants/cross-app access)"""
    _analysis_audit_cli("analysis_provider_safety", per_type_limit, apk_path)


@analysis.command(name="anti-analysis")
@click.option(
    "--limit",
    "per_type_limit",
    default=100,
    type=int,
    help="Max samples per category (default 100)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_anti_analysis_cmd(per_type_limit, apk_path):
    """Detect anti-analysis/hardening (root/emulator/debugger/Frida/Xposed detection, string+API dual scan)"""
    _analysis_audit_cli("analysis_anti_analysis", per_type_limit, apk_path)


@analysis.command(name="network-security")
@click.option(
    "--limit",
    "per_type_limit",
    default=100,
    type=int,
    help="Max samples per category (default 100)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_network_security_cmd(per_type_limit, apk_path):
    """Audit network security config (cleartext URLs/cert pinning/SSL context/HTTP clients)"""
    _analysis_audit_cli("analysis_network_security", per_type_limit, apk_path)


@analysis.command(name="obfuscation-metrics")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_obfuscation_metrics_cmd(apk_path):
    """Quantify obfuscation/hardening (class-name length distribution/reflection density/string coverage)"""
    result = _try_daemon_call("analysis_obfuscation_metrics", {})
    if result is not None:
        _output_json(result)
        return
    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_obfuscation_metrics())


@analysis.command(name="method-block-instructions")
@click.argument("class_name")
@click.argument("method_name")
@click.option(
    "--descriptor",
    default=None,
    help="Method descriptor (optional; first match if omitted)",
)
@click.option(
    "--ins-limit",
    default=None,
    type=int,
    help="Max instructions per block (0 = all)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_method_block_instructions_cmd(
    class_name, method_name, descriptor, ins_limit, apk_path
):
    """Disassemble method instructions organized by basic block (CFG node-level view)"""
    params = {
        "class_name": class_name,
        "method_name": method_name,
        "descriptor": descriptor,
        "ins_limit_per_block": ins_limit if ins_limit != 0 else None,
    }
    result = _try_daemon_call("analysis_method_block_instructions", params)
    if result is not None:
        _output_json(result)
        return
    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(
        skills.analysis_method_block_instructions(
            class_name,
            method_name,
            descriptor,
            ins_limit if ins_limit != 0 else None,
        )
    )


@analysis.command(name="method-switch-payloads")
@click.argument("class_name")
@click.argument("method_name")
@click.option(
    "--descriptor",
    default=None,
    help="Method descriptor (optional; first match if omitted)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_method_switch_payloads_cmd(
    class_name, method_name, descriptor, apk_path
):
    """Decode switch branch tables (case->target) and fill-array-data payloads in a method"""
    params = {
        "class_name": class_name,
        "method_name": method_name,
        "descriptor": descriptor,
    }
    result = _try_daemon_call("analysis_method_switch_payloads", params)
    if result is not None:
        _output_json(result)
        return
    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(
        skills.analysis_method_switch_payloads(
            class_name,
            method_name,
            descriptor,
        )
    )


# ----------------------------------------------------------------
# 第六轮：调用图与 API 权限映射
# ----------------------------------------------------------------


@analysis.command(name="call-graph")
@click.option(
    "--limit", default=None, type=int, help="Max number of edges to return"
)
@click.option(
    "--external", is_flag=True, help="Include external method nodes/edges"
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_call_graph_cmd(limit, external, apk_path):
    """Get the full call graph (nodes + edges)"""
    result = _try_daemon_call(
        "analysis_call_graph", {"limit": limit, "external": external}
    )
    if result is not None:
        _output_json(result)
        return
    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_call_graph(limit, external))


@analysis.command(name="call-graph-filtered")
@click.option(
    "--classname",
    default=None,
    help="Class name regex filter (e.g. Lcom/example/Foo;)",
)
@click.option("--methodname", default=None, help="Method name regex filter")
@click.option("--descriptor", default=None, help="Descriptor regex filter")
@click.option(
    "--accessflags",
    default=None,
    help="Access flags regex filter (e.g. public.*static)",
)
@click.option(
    "--no-isolated", is_flag=True, help="Remove isolated nodes (no edges)"
)
@click.option(
    "--external", is_flag=True, help="Include external method nodes/edges"
)
@click.option(
    "--limit", default=None, type=int, help="Max number of edges to return"
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_call_graph_filtered_cmd(
    classname,
    methodname,
    descriptor,
    accessflags,
    no_isolated,
    external,
    limit,
    apk_path,
):
    """Get a filtered sub call-graph (by class/method/descriptor/accessflags)"""
    result = _try_daemon_call(
        "analysis_call_graph_filtered",
        {
            "classname": classname,
            "methodname": methodname,
            "descriptor": descriptor,
            "accessflags": accessflags,
            "no_isolated": no_isolated,
            "external": external,
            "limit": limit,
        },
    )
    if result is not None:
        _output_json(result)
        return
    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(
        skills.analysis_call_graph_filtered(
            classname,
            methodname,
            descriptor,
            accessflags,
            no_isolated,
            external,
            limit,
        )
    )


@analysis.command(name="permissions")
@click.option(
    "--apilevel",
    default=None,
    help="API level for permission mapping (default: APK effective target)",
)
@click.option("--limit", default=None, type=int, help="Max number of results")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def analysis_permissions_cmd(apilevel, limit, apk_path):
    """List API methods that require permissions (batch, by API level)"""
    result = _try_daemon_call(
        "analysis_permissions", {"apilevel": apilevel, "limit": limit}
    )
    if result is not None:
        _output_json(result)
        return
    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.analysis_permissions(apilevel, limit))


# ================================================================
# Decompiler 命令组
# ================================================================


@entry_point.group(help="Decompilation commands")
def decompile():
    """反编译命令组"""
    pass


@decompile.command(name="class")
@click.argument("class_name")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def decompile_class_cmd(class_name, apk_path):
    """Decompile a specific class"""
    result = _try_daemon_call("decompile_class", {"class_name": class_name})
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.decompile_class(class_name))


@decompile.command(name="method")
@click.argument("class_name")
@click.argument("method_name")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def decompile_method_cmd(class_name, method_name, apk_path):
    """Decompile a specific method"""
    result = _try_daemon_call(
        "decompile_method",
        {"class_name": class_name, "method_name": method_name},
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.decompile_method(class_name, method_name))


@decompile.command(name="method-ast")
@click.argument("class_name")
@click.argument("method_name")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def decompile_method_ast_cmd(class_name, method_name, apk_path):
    """Decompile a method and return structured AST (triple/flags/ret/params/body)"""
    result = _try_daemon_call(
        "decompile_method_ast",
        {"class_name": class_name, "method_name": method_name},
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.decompile_method_ast(class_name, method_name))


@decompile.command(name="method-tokens")
@click.argument("class_name")
@click.argument("method_name")
@click.option(
    "--limit", default=None, type=int, help="Max number of tokens to return"
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def decompile_method_tokens_cmd(class_name, method_name, limit, apk_path):
    """Decompile a method and return token stream (type, value) pairs"""
    result = _try_daemon_call(
        "decompile_method_tokens",
        {"class_name": class_name, "method_name": method_name, "limit": limit},
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(
        skills.decompile_method_tokens(class_name, method_name, limit)
    )


@decompile.command(name="class-ast")
@click.argument("class_name")
@click.option(
    "--fields-limit",
    default=None,
    type=int,
    help="Max number of field ASTs to return (default: all)",
)
@click.option(
    "--methods-limit",
    default=None,
    type=int,
    help="Max number of method ASTs to return (default: all)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def decompile_class_ast_cmd(class_name, fields_limit, methods_limit, apk_path):
    """Decompile a class and return class-level AST (all methods + fields)"""
    result = _try_daemon_call(
        "decompile_class_ast",
        {
            "class_name": class_name,
            "fields_limit": fields_limit,
            "methods_limit": methods_limit,
        },
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(
        skills.decompile_class_ast(class_name, fields_limit, methods_limit)
    )


@decompile.command(name="class-tokens")
@click.argument("class_name")
@click.option(
    "--limit",
    default=None,
    type=int,
    help="Max number of top-level tokens to return (default: all)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def decompile_class_tokens_cmd(class_name, limit, apk_path):
    """Decompile a class and return class-level token stream (lexical tokens)"""
    result = _try_daemon_call(
        "decompile_class_tokens",
        {"class_name": class_name, "limit": limit},
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.decompile_class_tokens(class_name, limit))


# ================================================================
# Pentest 命令组
# ================================================================


@entry_point.group(help="Dynamic analysis / pentest commands")
def pentest():
    """动态分析命令组"""
    pass


@pentest.command(name="trace")
@click.argument("apk_path", type=click.Path(exists=True))
@click.option(
    "-m",
    "--module",
    "modules",
    multiple=True,
    help="Frida module to load (can be specified multiple times)",
)
def pentest_trace_cmd(apk_path, modules):
    """Trace APK using Frida"""
    skills = _get_skills()
    _output_json(skills.pentest_trace(apk_path, list(modules)))


@pentest.command(name="dump")
@click.argument("package_name")
@click.option(
    "-m",
    "--module",
    "modules",
    multiple=True,
    help="Frida module to load (can be specified multiple times)",
)
def pentest_dump_cmd(package_name, modules):
    """Dump DEX from running app"""
    skills = _get_skills()
    module_list = list(modules) if modules else None
    _output_json(skills.pentest_dump(package_name, module_list))


# ================================================================
# Resources 命令组
# ================================================================


@entry_point.group(help="Android resource parsing commands")
def resources():
    """资源解析命令组"""
    pass


@resources.command(name="packages")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def resources_packages_cmd(apk_path):
    """List resource packages"""
    result = _try_daemon_call("resource_packages")
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.resource_packages())


@resources.command(name="locales")
@click.argument("package_name")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def resources_locales_cmd(package_name, apk_path):
    """List supported locales for a resource package"""
    result = _try_daemon_call("resource_locales", {"package": package_name})
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.resource_locales(package_name))


@resources.command(name="types")
@click.argument("package_name")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def resources_types_cmd(package_name, apk_path):
    """List resource types for a resource package"""
    result = _try_daemon_call("resource_types", {"package": package_name})
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.resource_types(package_name))


@resources.command(name="configs")
@click.argument("resource_id", type=int)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def resources_configs_cmd(resource_id, apk_path):
    """Get all configurations for a resource ID"""
    result = _try_daemon_call("resource_configs", {"resource_id": resource_id})
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.resource_configs(resource_id))


@resources.command(name="strings")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def resources_strings_cmd(apk_path):
    """Get all resolved string resources"""
    result = _try_daemon_call("resource_strings")
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.resource_strings())


@resources.command(name="bool")
@click.argument("package_name")
@click.option(
    "--locale",
    default=None,
    help="Locale (e.g. zh, en). Default is the default locale",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def resources_bool_cmd(package_name, locale, apk_path):
    """Get boolean resources for a package"""
    loc = locale if locale else "\x00\x00"
    result = _try_daemon_call(
        "resource_bool", {"package": package_name, "locale": loc}
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.resource_bool(package_name, loc))


@resources.command(name="color")
@click.argument("package_name")
@click.option(
    "--locale",
    default=None,
    help="Locale (e.g. zh, en). Default is the default locale",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def resources_color_cmd(package_name, locale, apk_path):
    """Get color resources for a package"""
    loc = locale if locale else "\x00\x00"
    result = _try_daemon_call(
        "resource_color", {"package": package_name, "locale": loc}
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.resource_color(package_name, loc))


@resources.command(name="dimen")
@click.argument("package_name")
@click.option(
    "--locale",
    default=None,
    help="Locale (e.g. zh, en). Default is the default locale",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def resources_dimen_cmd(package_name, locale, apk_path):
    """Get dimension resources for a package"""
    loc = locale if locale else "\x00\x00"
    result = _try_daemon_call(
        "resource_dimen", {"package": package_name, "locale": loc}
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.resource_dimen(package_name, loc))


@resources.command(name="integer")
@click.argument("package_name")
@click.option(
    "--locale",
    default=None,
    help="Locale (e.g. zh, en). Default is the default locale",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def resources_integer_cmd(package_name, locale, apk_path):
    """Get integer resources for a package"""
    loc = locale if locale else "\x00\x00"
    result = _try_daemon_call(
        "resource_integer", {"package": package_name, "locale": loc}
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.resource_integer(package_name, loc))


@resources.command(name="id")
@click.argument("package_name")
@click.option(
    "--rid",
    "resource_id",
    default=None,
    type=int,
    help="Resource ID (decimal) for ID->name lookup",
)
@click.option(
    "--type",
    "resource_type",
    default=None,
    help="Resource type (string/color/layout) for name->ID lookup",
)
@click.option(
    "--key", default=None, help="Resource key name for name->ID lookup"
)
@click.option("--locale", default=None, help="Locale (optional)")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def resources_id_cmd(
    package_name, resource_id, resource_type, key, locale, apk_path
):
    """Bidirectional resource ID lookup (ID<->name)"""
    loc = locale if locale else "\x00\x00"
    result = _try_daemon_call(
        "resource_id",
        {
            "package": package_name,
            "resource_id": resource_id,
            "resource_type": resource_type,
            "key": key,
            "locale": loc,
        },
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(
        skills.resource_id(package_name, resource_id, resource_type, key, loc)
    )


@resources.command(name="string-resources")
@click.argument("package_name")
@click.option("--locale", default=None, help="Locale (optional, e.g. zh/en)")
@click.option(
    "--raw", is_flag=True, help="Return raw XML text instead of parsed list"
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def resources_string_resources_cmd(package_name, locale, raw, apk_path):
    """Get string resources (strings.xml) for a package+locale"""
    loc = locale if locale else "\x00\x00"
    result = _try_daemon_call(
        "resource_string_resources",
        {"package": package_name, "locale": loc, "raw": raw},
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.resource_string_resources(package_name, loc, raw))


@resources.command(name="strings-all")
@click.option(
    "--raw", is_flag=True, help="Return raw XML text instead of parsed list"
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def resources_strings_all_cmd(raw, apk_path):
    """Get all string resources (full strings.xml across packages)"""
    result = _try_daemon_call("resource_strings_all", {"raw": raw})
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.resource_strings_all(raw))


@resources.command(name="public")
@click.argument("package_name")
@click.option("--locale", default=None, help="Locale (optional)")
@click.option(
    "--raw", is_flag=True, help="Return raw XML text instead of parsed list"
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def resources_public_cmd(package_name, locale, raw, apk_path):
    """Get public.xml (full type/name/id resource mapping)"""
    loc = locale if locale else "\x00\x00"
    result = _try_daemon_call(
        "resource_public",
        {"package": package_name, "locale": loc, "raw": raw},
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.resource_public(package_name, loc, raw))


@resources.command(name="id-resources")
@click.argument("package_name")
@click.option("--locale", default=None, help="Locale (optional)")
@click.option(
    "--raw", is_flag=True, help="Return raw XML text instead of parsed list"
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def resources_id_resources_cmd(package_name, locale, raw, apk_path):
    """Get ids.xml (id-type resource list)"""
    loc = locale if locale else "\x00\x00"
    result = _try_daemon_call(
        "resource_id_resources",
        {"package": package_name, "locale": loc, "raw": raw},
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.resource_id_resources(package_name, loc, raw))


@resources.command(name="get-string")
@click.argument("package_name")
@click.argument("name")
@click.option("--locale", default=None, help="Locale (optional)")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def resources_get_string_cmd(package_name, name, locale, apk_path):
    """Get a single string resource value by package+key+locale"""
    loc = locale if locale else "\x00\x00"
    result = _try_daemon_call(
        "resource_get_string",
        {"package": package_name, "name": name, "locale": loc},
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.resource_get_string(package_name, name, loc))


@resources.command(name="xml-name")
@click.argument("resource_id")
@click.option("--package", default=None, help="Resource package (optional)")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def resources_xml_name_cmd(resource_id, package, apk_path):
    """Resolve a resource ID to its XML reference name (@pkg:type/name)"""
    rid = _parse_resource_id(resource_id)
    result = _try_daemon_call(
        "resource_xml_name", {"resource_id": rid, "package": package}
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.resource_xml_name(rid, package))


@resources.command(name="type-configs")
@click.argument("package_name")
@click.option(
    "--type",
    "resource_type",
    default=None,
    help="Resource type filter (e.g. string/layout); all if omitted",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def resources_type_configs_cmd(package_name, resource_type, apk_path):
    """List config variants for a resource type (all locales/densities)"""
    result = _try_daemon_call(
        "resource_type_configs",
        {"package": package_name, "resource_type": resource_type},
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.resource_type_configs(package_name, resource_type))


@resources.command(name="resolved-strings")
@click.option(
    "--locale", default=None, help="Locale filter (e.g. zh/en); all if omitted"
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def resources_resolved_strings_cmd(locale, apk_path):
    """Get all resolved string resources (package->locale->rid->value)"""
    result = _try_daemon_call("resource_resolved_strings", {"locale": locale})
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.resource_resolved_strings(locale))


@resources.command(name="res-configs")
@click.argument("resource_id")
@click.option(
    "--no-fallback",
    is_flag=True,
    help="Do not fall back to default config when exact match missing",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def resources_res_configs_cmd(resource_id, no_fallback, apk_path):
    """List config variants (locale/density, raw entry) for a specific resource ID"""
    rid = _parse_resource_id(resource_id)
    result = _try_daemon_call(
        "resource_res_configs",
        {"resource_id": rid, "fallback": not no_fallback},
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.resource_res_configs(rid, not no_fallback))


@resources.command(name="value")
@click.argument("resource_id")
@click.option(
    "--package", default=None, help="Resource package name (optional)"
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def resources_value_cmd(resource_id, package, apk_path):
    """Resolve a resource ID to its typed value (string/bool/color/dimen/integer/style/id)"""
    result = _try_daemon_call(
        "resource_value", {"resource_id": resource_id, "package": package}
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.resource_value(resource_id, package))


def _parse_resource_id(raw):
    """将资源 ID 字符串（0x7f020000 或十进制）解析为整型"""
    if raw is None:
        return None
    raw = str(raw).strip()
    try:
        return int(raw, 16) if raw.lower().startswith("0x") else int(raw)
    except ValueError:
        raise click.BadParameter(f"Invalid resource ID: {raw}")


# ================================================================
# Visualize 命令组
# ================================================================


@entry_point.group(help="Method visualization / CFG export commands")
def visualize():
    """可视化命令组"""
    pass


@visualize.command(name="method-dot")
@click.argument("class_name")
@click.argument("method_name")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def visualize_method_dot_cmd(class_name, method_name, apk_path):
    """Export method CFG as DOT format"""
    result = _try_daemon_call(
        "visualize_method_dot",
        {"class_name": class_name, "method_name": method_name},
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.visualize_method_dot(class_name, method_name))


@visualize.command(name="method-image")
@click.argument("class_name")
@click.argument("method_name")
@click.option("-o", "--output", required=True, help="Output image file path")
@click.option(
    "-f",
    "--format",
    "fmt",
    type=click.Choice(["png", "jpg"]),
    default="png",
    help="Image format (default: png)",
)
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def visualize_method_image_cmd(class_name, method_name, output, fmt, apk_path):
    """Export method CFG as image (PNG/JPG)"""
    result = _try_daemon_call(
        "visualize_method_image",
        {
            "class_name": class_name,
            "method_name": method_name,
            "output": output,
            "fmt": fmt,
        },
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(
        skills.visualize_method_image(class_name, method_name, output, fmt)
    )


@visualize.command(name="method-json")
@click.argument("class_name")
@click.argument("method_name")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def visualize_method_json_cmd(class_name, method_name, apk_path):
    """Export method CFG as JSON"""
    result = _try_daemon_call(
        "visualize_method_json",
        {"class_name": class_name, "method_name": method_name},
    )
    if result is not None:
        _output_json(result)
        return

    skills = _get_skills()
    if not skills.is_loaded:
        if not apk_path:
            _output_json(
                {
                    "error": "No APK loaded. Use 'load' command first or set --apk-path"
                }
            )
            return
        skills.load_apk(apk_path)
    _output_json(skills.visualize_method_json(class_name, method_name))


# ================================================================
# 工具能力命令组（androguard.util / androconf，不依赖已加载 APK）
# ================================================================


@entry_point.group(help="Utility commands (file detection, AOSP permissions)")
def util():
    """Utility commands"""


@util.command(name="detect")
@click.argument("filename", type=click.Path(exists=True))
def util_detect_cmd(filename):
    """Detect the Android file type (APK/DEX/ODEX/ELF) of a file"""
    result = _try_daemon_call("util_detect_file", {"filename": filename})
    if result is not None:
        _output_json(result)
        return
    _output_json(_get_skills().util_detect_file(filename))


@util.command(name="permissions")
@click.argument("apilevel")
def util_permissions_cmd(apilevel):
    """Load AOSP permission definitions for a given API level"""
    result = _try_daemon_call("util_permissions", {"apilevel": apilevel})
    if result is not None:
        _output_json(result)
        return
    _output_json(_get_skills().util_permissions(apilevel))


@util.command(name="permission-mappings")
@click.argument("apilevel")
def util_permission_mappings_cmd(apilevel):
    """Load method-signature -> permission mappings for a given API level"""
    result = _try_daemon_call(
        "util_permission_mappings", {"apilevel": apilevel}
    )
    if result is not None:
        _output_json(result)
        return
    _output_json(_get_skills().util_permission_mappings(apilevel))


@util.command(name="api-levels")
def util_api_levels_cmd():
    """List locally available API levels for permission data"""
    result = _try_daemon_call("util_available_api_levels")
    if result is not None:
        _output_json(result)
        return
    _output_json(_get_skills().util_available_api_levels())


@util.command(name="format")
@click.argument("value")
@click.option(
    "--to",
    default="java",
    type=click.Choice(["java", "dalvik", "python"]),
    help="Target format (java/dalvik/python, default java)",
)
def util_format_cmd(value, to):
    """Convert class name/descriptor between Dalvik/Java/Python formats"""
    result = _try_daemon_call("util_format", {"value": value, "to": to})
    if result is not None:
        _output_json(result)
        return
    _output_json(_get_skills().util_format(value, to))


# ================================================================
# Session 会话命令组（多 APK/DEX 关联分析）
# ================================================================


@entry_point.group(
    help="Session commands (multi-APK/DEX correlation analysis)"
)
def session():
    """Session commands"""


@session.command(name="analyze-apk")
@click.argument("apk_path", type=click.Path(exists=True))
def session_analyze_apk_cmd(apk_path):
    """Analyze an APK via a Session (independent loading path)"""
    result = _try_daemon_call("session_analyze_apk", {"apk_path": apk_path})
    if result is not None:
        _output_json(result)
        return
    _output_json(_get_skills().session_analyze_apk(apk_path))


@session.command(name="create")
def session_create_cmd():
    """Create a new Session (held for subsequent session commands; use daemon mode for cross-command persistence)"""
    result = _try_daemon_call("session_create", {})
    if result is not None:
        _output_json(result)
        return
    _output_json(_get_skills().session_create())


@session.command(name="add-apk")
@click.argument("apk_path", type=click.Path(exists=True))
def session_add_apk_cmd(apk_path):
    """Add an APK to the current Session (multi-file association analysis)"""
    result = _try_daemon_call("session_add_apk", {"apk_path": apk_path})
    if result is not None:
        _output_json(result)
        return
    skills = _get_skills()
    if not skills.has_session:
        _output_json(
            {
                "error": "No Session. Use 'session create' first (daemon mode recommended for persistence)"
            }
        )
        return
    _output_json(skills.session_add_apk(apk_path))


@session.command(name="add-dex")
@click.argument("dex_path", type=click.Path(exists=True))
def session_add_dex_cmd(dex_path):
    """Add a standalone DEX to the current Session"""
    result = _try_daemon_call("session_add_dex", {"dex_path": dex_path})
    if result is not None:
        _output_json(result)
        return
    skills = _get_skills()
    if not skills.has_session:
        _output_json(
            {
                "error": "No Session. Use 'session create' first (daemon mode recommended for persistence)"
            }
        )
        return
    _output_json(skills.session_add_dex(dex_path))


@session.command(name="info")
def session_info_cmd():
    """Get current Session overview (APK/DEX counts + string count)"""
    result = _try_daemon_call("session_info", {})
    if result is not None:
        _output_json(result)
        return
    skills = _get_skills()
    if not skills.has_session:
        _output_json({"error": "No Session. Use 'session create' first"})
        return
    _output_json(skills.session_info())


@session.command(name="filename-by-class")
@click.argument("class_name")
def session_filename_by_class_cmd(class_name):
    """Find which file/digest a class belongs to (multi-APK/DEX association)"""
    result = _try_daemon_call(
        "session_filename_by_class", {"class_name": class_name}
    )
    if result is not None:
        _output_json(result)
        return
    skills = _get_skills()
    if not skills.has_session:
        _output_json({"error": "No Session. Use 'session create' first"})
        return
    _output_json(skills.session_filename_by_class(class_name))


@session.command(name="strings")
@click.option("--limit", default=None, type=int, help="Max strings per DEX")
def session_strings_cmd(limit):
    """Get strings analysis across all DEXes in the Session"""
    result = _try_daemon_call("session_strings", {"limit": limit})
    if result is not None:
        _output_json(result)
        return
    skills = _get_skills()
    if not skills.has_session:
        _output_json({"error": "No Session. Use 'session create' first"})
        return
    _output_json(skills.session_strings(limit))


@session.command(name="classes")
@click.option(
    "--limit", default=None, type=int, help="Max DEX groups to return"
)
def session_classes_cmd(limit):
    """List all classes in the Session (grouped by DEX)"""
    result = _try_daemon_call("session_classes", {"limit": limit})
    if result is not None:
        _output_json(result)
        return
    skills = _get_skills()
    if not skills.has_session:
        _output_json({"error": "No Session. Use 'session create' first"})
        return
    _output_json(skills.session_classes(limit))


# ================================================================
# DEX 独立加载
# ================================================================


@entry_point.command(name="load-dex")
@click.argument("dex_path", type=click.Path(exists=True))
def load_dex_cmd(dex_path):
    """Load a standalone DEX file (without APK)"""
    skills = _get_skills()
    _output_json(skills.load_dex(dex_path))


if __name__ == "__main__":
    entry_point()
