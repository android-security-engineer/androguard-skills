"""
静态分析能力封装。

将 androguard.core.analysis.analysis.Analysis 的方法封装为返回 dict 的函数，
便于 JSON 序列化和 CLI 输出。
"""

from __future__ import annotations

import re
from typing import Union

from loguru import logger


def _method_analysis_to_dict(ma) -> dict:
    """将 MethodAnalysis 对象转换为可序列化的字典"""
    return {
        "class": ma.class_name,
        "method": ma.name,
        "descriptor": ma.descriptor,
    }


def _normalize_descriptor(descriptor: str) -> str:
    """归一化方法描述符：去掉参数间的空格，便于容错匹配。

    AndroGuard 内部存储的 descriptor 参数间带空格（如
    ``(Landroid/content/Context; Ljava/lang/String;)V``），而用户/文档
    常传无空格版本（``(Landroid/content/Context;Ljava/lang/String;)V``）。
    ``get_method_analysis_by_name`` 做精确字符串匹配，空格差异会导致不命中。
    """
    if not descriptor:
        return descriptor
    # 只去掉参数列表内部（括号之间）的空格，保留返回类型后的空格语义无关
    return descriptor.replace(" ", "")


def _resolve_method_analysis(
    analysis_obj, class_name: str, method_name: str, descriptor: str
):
    """按 class+method+descriptor 查找 MethodAnalysis，descriptor 容错匹配。

    先用 get_method_analysis_by_name 精确查；不命中时遍历
    ClassAnalysis.get_methods() 按方法名 + 归一化 descriptor 匹配。
    """
    ma = analysis_obj.get_method_analysis_by_name(
        class_name, method_name, descriptor
    )
    if ma is not None:
        return ma
    # 精确不命中 → 按名 + 归一化 descriptor 容错查找
    target = _normalize_descriptor(descriptor)
    try:
        ca = analysis_obj.get_class_analysis(class_name)
    except Exception:
        ca = None
    if ca is not None:
        try:
            for m in ca.get_methods():
                try:
                    if (
                        m.name == method_name
                        and _normalize_descriptor(m.descriptor) == target
                    ):
                        return m
                except Exception:
                    continue
        except Exception:
            pass
    return None


def analysis_xrefs_from(analysis_obj, class_name: str) -> dict:
    """
    获取谁引用了指定类（XrefFrom）。

    :param analysis_obj: Analysis 对象
    :param class_name: 类名（格式如 Lcom/example/MyClass;）
    :return: 交叉引用信息
    """
    class_analysis = analysis_obj.get_class_analysis(class_name)
    if class_analysis is None:
        return {"class": class_name, "error": "Class not found in analysis"}

    xrefs = []
    # get_xref_from() 返回 defaultdict:
    # key = ClassAnalysis, value = set of (REF_TYPE, MethodAnalysis, offset)
    # defaultdict 外层迭代序在 3.7+ 确定（插入序），但 value 是 set，set 迭代
    # 序非确定（依赖哈希）——同一 class 下多条 method_refs 顺序每次不同，
    # 导致 xrefs 列表非确定（agent 对接需确定性）。扁平化后排序固定。
    for (
        ref_class_analysis,
        method_refs,
    ) in class_analysis.get_xref_from().items():
        for ref_type, ref_method, offset in method_refs:
            xrefs.append(
                {
                    "from_class": ref_class_analysis.name,
                    "from_method": ref_method.name,
                    "from_descriptor": ref_method.descriptor,
                    "ref_type": ref_type.name,
                    "offset": offset,
                }
            )
    xrefs.sort(
        key=lambda r: (
            r["from_class"],
            r["from_method"],
            r["from_descriptor"],
            r["offset"],
        )
    )

    return {
        "class": class_name,
        "xref_from_count": len(xrefs),
        "xref_from": xrefs,
    }


def analysis_xrefs_to(analysis_obj, class_name: str) -> dict:
    """
    获取指定类引用了谁（XrefTo）。

    :param analysis_obj: Analysis 对象
    :param class_name: 类名（格式如 Lcom/example/MyClass;）
    :return: 交叉引用信息
    """
    class_analysis = analysis_obj.get_class_analysis(class_name)
    if class_analysis is None:
        return {"class": class_name, "error": "Class not found in analysis"}

    xrefs = []
    # get_xref_to() 返回 defaultdict（同 xref_from，value 是 set 非确定），
    # 扁平化后排序固定顺序。
    for (
        ref_class_analysis,
        method_refs,
    ) in class_analysis.get_xref_to().items():
        for ref_type, ref_method, offset in method_refs:
            xrefs.append(
                {
                    "to_class": ref_class_analysis.name,
                    "to_method": ref_method.name,
                    "to_descriptor": ref_method.descriptor,
                    "ref_type": ref_type.name,
                    "offset": offset,
                }
            )
    xrefs.sort(
        key=lambda r: (
            r["to_class"],
            r["to_method"],
            r["to_descriptor"],
            r["offset"],
        )
    )

    return {"class": class_name, "xref_to_count": len(xrefs), "xref_to": xrefs}


def analysis_method_xrefs(
    analysis_obj, class_name: str, method_name: str
) -> dict:
    """
    获取指定方法的交叉引用。

    :param analysis_obj: Analysis 对象
    :param class_name: 类名
    :param method_name: 方法名
    :return: 方法交叉引用信息
    """
    # 通过 ClassAnalysis 查找方法，因为 get_method_analysis_by_name 需要 descriptor
    class_analysis = analysis_obj.get_class_analysis(class_name)
    if class_analysis is None:
        return {
            "class": class_name,
            "method": method_name,
            "error": "Class not found in analysis",
        }

    # 在类中查找匹配的方法
    method_analysis = None
    for ma in class_analysis.get_methods():
        if ma.name == method_name:
            method_analysis = ma
            break

    if method_analysis is None:
        return {
            "class": class_name,
            "method": method_name,
            "error": "Method not found in class",
        }

    result = {
        "class": class_name,
        "method": method_name,
        "descriptor": method_analysis.descriptor,
        "is_external": method_analysis.is_external(),
        "is_android_api": method_analysis.is_android_api(),
    }

    # XrefFrom - 谁调用了此方法
    # MethodAnalysis.get_xref_from() 返回 set of (ClassAnalysis, MethodAnalysis, offset)
    xref_from = []
    for (
        ref_class_analysis,
        ref_method,
        offset,
    ) in method_analysis.get_xref_from():
        xref_from.append(
            {
                "from_class": ref_class_analysis.name,
                "from_method": ref_method.name,
                "from_descriptor": ref_method.descriptor,
                "offset": offset,
            }
        )
    # get_xref_from() 返回 set，迭代顺序依赖哈希非确定（agent 对接需确定性比对）
    xref_from.sort(
        key=lambda r: (
            r["from_class"],
            r["from_method"],
            r["from_descriptor"],
            r["offset"],
        )
    )
    result["xref_from_count"] = len(xref_from)
    result["xref_from"] = xref_from

    # XrefTo - 此方法调用了谁
    # MethodAnalysis.get_xref_to() 返回 set of (ClassAnalysis, MethodAnalysis, offset)
    xref_to = []
    for (
        ref_class_analysis,
        ref_method,
        offset,
    ) in method_analysis.get_xref_to():
        xref_to.append(
            {
                "to_class": ref_class_analysis.name,
                "to_method": ref_method.name,
                "to_descriptor": ref_method.descriptor,
                "offset": offset,
            }
        )
    # 同 xref_from：set 迭代非确定，排序固定输出顺序
    xref_to.sort(
        key=lambda r: (
            r["to_class"],
            r["to_method"],
            r["to_descriptor"],
            r["offset"],
        )
    )
    result["xref_to_count"] = len(xref_to)
    result["xref_to"] = xref_to

    return result


def analysis_find_classes(analysis_obj, pattern: str) -> dict:
    """
    按正则表达式搜索类。

    :param analysis_obj: Analysis 对象
    :param pattern: 类名正则表达式
    :return: 匹配的类列表
    """
    regex = re.compile(pattern)
    classes = []
    for class_analysis in analysis_obj.get_classes():
        if regex.search(class_analysis.name):
            classes.append(
                {
                    "name": class_analysis.name,
                    "is_external": class_analysis.is_external(),
                    "is_android_api": class_analysis.is_android_api(),
                }
            )

    return {"pattern": pattern, "total": len(classes), "classes": classes}


def analysis_find_methods(analysis_obj, pattern: str) -> dict:
    """
    按正则表达式搜索方法。

    :param analysis_obj: Analysis 对象
    :param pattern: 方法名正则表达式
    :return: 匹配的方法列表
    """
    regex = re.compile(pattern)
    methods = []
    for class_analysis in analysis_obj.get_classes():
        for method_analysis in class_analysis.get_methods():
            if regex.search(method_analysis.name):
                methods.append(
                    {
                        "class": method_analysis.class_name,
                        "method": method_analysis.name,
                        "descriptor": method_analysis.descriptor,
                        "is_external": method_analysis.is_external(),
                    }
                )

    return {"pattern": pattern, "total": len(methods), "methods": methods}


def analysis_find_strings(analysis_obj, pattern: str) -> dict:
    """
    按正则表达式搜索字符串。

    :param analysis_obj: Analysis 对象
    :param pattern: 字符串正则表达式
    :return: 匹配的字符串及其使用位置
    """
    regex = re.compile(pattern)
    strings = []
    for string_analysis in analysis_obj.get_strings():
        value = string_analysis.get_value()
        if regex.search(value):
            string_info = {"value": value}

            # 获取字符串的引用位置
            # get_xref_from() 返回 set of (ClassAnalysis, MethodAnalysis)，
            # set 迭代顺序非确定（依赖哈希），导致 used_in 列表顺序每次不同
            # （agent 对接需确定性输出）。排序固定顺序。
            origins = []
            for (
                ref_class_analysis,
                ref_method,
            ) in string_analysis.get_xref_from():
                origins.append(
                    {
                        "class": ref_class_analysis.name,
                        "method": ref_method.name,
                    }
                )
            origins.sort(key=lambda r: (r["class"], r["method"]))
            string_info["used_in"] = origins
            string_info["used_in_count"] = len(origins)

            strings.append(string_info)

    return {"pattern": pattern, "total": len(strings), "strings": strings}


def analysis_callgraph(
    analysis_obj, apk_obj, output: str, fmt: str = "gml"
) -> dict:
    """
    生成调用图并导出为指定格式。

    :param analysis_obj: Analysis 对象
    :param apk_obj: APK 对象（用于获取入口点）
    :param output: 输出文件路径
    :param fmt: 输出格式（gml, gexf, graphml, net）
    :return: 调用图导出结果
    """
    import networkx as nx

    from androguard.core.bytecode import FormatClassToJava

    # 获取入口点
    entry_points = list(
        map(
            FormatClassToJava,
            apk_obj.get_activities()
            + apk_obj.get_providers()
            + apk_obj.get_services()
            + apk_obj.get_receivers(),
        )
    )

    callgraph = analysis_obj.get_call_graph(entry_points=entry_points)

    # 导出方法映射
    write_methods = {
        "gml": lambda g, p: nx.write_gml(g, p, stringizer=str),
        "gexf": nx.write_gexf,
        "graphml": nx.write_graphml,
        "net": nx.write_pajek,
    }

    fmt_lower = fmt.lower()
    if fmt_lower not in write_methods:
        return {
            "error": f"Unsupported format: {fmt}. "
            f"Supported: {', '.join(write_methods.keys())}"
        }

    try:
        write_methods[fmt_lower](callgraph, output)
        return {
            "output": output,
            "format": fmt_lower,
            "nodes": callgraph.number_of_nodes(),
            "edges": callgraph.number_of_edges(),
        }
    except Exception as e:
        return {"error": f"Failed to export callgraph: {str(e)}"}


def analysis_permission_usage(analysis_obj, permission: str) -> dict:
    """
    追踪指定权限的使用情况。

    :param analysis_obj: Analysis 对象
    :param permission: 权限名称
    :return: 权限使用信息
    """
    try:
        usages = list(analysis_obj.get_permission_usage(permission))
        result_usages = []
        for method_analysis in usages:
            result_usages.append(
                {
                    "class": method_analysis.class_name,
                    "method": method_analysis.name,
                    "descriptor": method_analysis.descriptor,
                }
            )
        return {
            "permission": permission,
            "usage_count": len(result_usages),
            "usages": result_usages,
        }
    except Exception as e:
        return {"permission": permission, "error": str(e)}


def analysis_internal_classes(analysis_obj, filter_regex: str = None) -> dict:
    """
    获取应用内部类列表（非外部依赖）。

    :param analysis_obj: Analysis 对象
    :param filter_regex: 类名过滤正则表达式（可选）
    :return: 内部类列表
    """
    pattern = re.compile(filter_regex) if filter_regex else None
    classes = []
    for class_analysis in analysis_obj.get_internal_classes():
        name = class_analysis.name
        if pattern and not pattern.search(name):
            continue
        classes.append(
            {
                "name": name,
                "is_android_api": class_analysis.is_android_api(),
            }
        )

    return {"total": len(classes), "classes": classes}


def analysis_external_classes(analysis_obj, filter_regex: str = None) -> dict:
    """
    获取外部依赖类列表。

    :param analysis_obj: Analysis 对象
    :param filter_regex: 类名过滤正则表达式（可选）
    :return: 外部类列表
    """
    pattern = re.compile(filter_regex) if filter_regex else None
    classes = []
    for class_analysis in analysis_obj.get_external_classes():
        name = class_analysis.name
        if pattern and not pattern.search(name):
            continue
        classes.append(
            {
                "name": name,
                "is_android_api": class_analysis.is_android_api(),
            }
        )

    return {"total": len(classes), "classes": classes}


def analysis_internal_methods(analysis_obj, filter_regex: str = None) -> dict:
    """
    获取应用内部方法列表。

    :param analysis_obj: Analysis 对象
    :param filter_regex: 方法名过滤正则表达式（可选）
    :return: 内部方法列表
    """
    pattern = re.compile(filter_regex) if filter_regex else None
    methods = []
    for method_analysis in analysis_obj.get_internal_methods():
        if pattern and not pattern.search(method_analysis.name):
            continue
        methods.append(
            {
                "class": method_analysis.class_name,
                "method": method_analysis.name,
                "descriptor": method_analysis.descriptor,
            }
        )

    return {"total": len(methods), "methods": methods}


def analysis_external_methods(analysis_obj, filter_regex: str = None) -> dict:
    """
    获取外部方法列表。

    :param analysis_obj: Analysis 对象
    :param filter_regex: 方法名过滤正则表达式（可选）
    :return: 外部方法列表
    """
    pattern = re.compile(filter_regex) if filter_regex else None
    methods = []
    for method_analysis in analysis_obj.get_external_methods():
        if pattern and not pattern.search(method_analysis.name):
            continue
        methods.append(
            {
                "class": method_analysis.class_name,
                "method": method_analysis.name,
                "descriptor": method_analysis.descriptor,
            }
        )

    return {"total": len(methods), "methods": methods}


def analysis_field_xrefs(
    analysis_obj, class_name: str, field_name: str
) -> dict:
    """
    获取指定字段的交叉引用。

    :param analysis_obj: Analysis 对象
    :param class_name: 类名
    :param field_name: 字段名
    :return: 字段交叉引用信息
    """
    # 通过 ClassAnalysis 查找字段
    class_analysis = analysis_obj.get_class_analysis(class_name)
    if class_analysis is None:
        return {
            "class": class_name,
            "field": field_name,
            "error": "Class not found",
        }

    # 查找字段分析 — get_field_analysis() 需要 EncodedField 对象，不是字段名字符串
    # 因此通过遍历 get_fields() 来匹配字段名
    field_analysis = None
    for fa in class_analysis.get_fields():
        if fa.name == field_name:
            field_analysis = fa
            break

    if field_analysis is None:
        return {
            "class": class_name,
            "field": field_name,
            "error": "Field not found in class",
        }

    # 获取底层字段对象
    field_obj = field_analysis.get_field()

    result = {
        "class": class_name,
        "field": field_name,
    }

    # 字段基本信息
    if field_obj is not None:
        result["descriptor"] = field_obj.get_descriptor()
        result["access_flags"] = field_obj.get_access_flags_string()

    # XrefRead - 谁读取了此字段
    # FieldAnalysis.get_xref_read() 返回 set of (ClassAnalysis, MethodAnalysis)
    xref_read = []
    for ref_class, ref_method in field_analysis.get_xref_read():
        xref_read.append(
            {
                "class": ref_class.name,
                "method": ref_method.name,
                "descriptor": ref_method.descriptor,
            }
        )
    result["xref_read_count"] = len(xref_read)
    result["xref_read"] = xref_read

    # XrefWrite - 谁写入/修改了此字段
    # FieldAnalysis.get_xref_write() 返回 set of (ClassAnalysis, MethodAnalysis)
    xref_write = []
    for ref_class, ref_method in field_analysis.get_xref_write():
        xref_write.append(
            {
                "class": ref_class.name,
                "method": ref_method.name,
                "descriptor": ref_method.descriptor,
            }
        )
    result["xref_write_count"] = len(xref_write)
    result["xref_write"] = xref_write

    return result


def analysis_field_xrefs_detail(
    analysis_obj, class_name: str, field_name: str
) -> dict:
    """
    获取字段读/写引用的完整列表（含每处引用的 offset，不去重）。

    与 analysis_field_xrefs（用 get_xref_read() 无 offset、set 去重）的区别：
    本命令用 get_xref_read(with_offset=True)/get_xref_write(with_offset=True)，
    返回 list of (ClassAnalysis, MethodAnalysis, offset)，每处引用一条（同一方法多处
    读/写会出现多条），适合精确定位字段被访问的指令位置。

    :param analysis_obj: Analysis 对象
    :param class_name: 类名
    :param field_name: 字段名
    :return: 字段读/写引用详情（含 offset）
    """
    class_analysis = analysis_obj.get_class_analysis(class_name)
    if class_analysis is None:
        return {
            "class": class_name,
            "field": field_name,
            "error": "Class not found",
        }

    field_analysis = None
    for fa in class_analysis.get_fields():
        if fa.name == field_name:
            field_analysis = fa
            break

    if field_analysis is None:
        return {
            "class": class_name,
            "field": field_name,
            "error": "Field not found in class",
        }

    field_obj = field_analysis.get_field()
    result = {"class": class_name, "field": field_name}
    if field_obj is not None:
        result["descriptor"] = field_obj.get_descriptor()
        result["access_flags"] = field_obj.get_access_flags_string()

    # XrefRead with offset - 每处读取一条（不去重）
    # get_xref_read(with_offset=True) 返回 list of (ClassAnalysis, MethodAnalysis, offset)
    xref_read = []
    try:
        for ref_class, ref_method, offset in field_analysis.get_xref_read(
            with_offset=True
        ):
            xref_read.append(
                {
                    "class": ref_class.name,
                    "method": ref_method.name,
                    "descriptor": ref_method.descriptor,
                    "offset": offset,
                }
            )
    except Exception:
        pass
    result["xref_read"] = {"count": len(xref_read), "refs": xref_read}

    # XrefWrite with offset - 每处写入一条（不去重）
    # get_xref_write(with_offset=True) 返回 list of (ClassAnalysis, MethodAnalysis, offset)
    xref_write = []
    try:
        for ref_class, ref_method, offset in field_analysis.get_xref_write(
            with_offset=True
        ):
            xref_write.append(
                {
                    "class": ref_class.name,
                    "method": ref_method.name,
                    "descriptor": ref_method.descriptor,
                    "offset": offset,
                }
            )
    except Exception:
        pass
    result["xref_write"] = {"count": len(xref_write), "refs": xref_write}

    return result


def analysis_find_fields(analysis_obj, pattern: str) -> dict:
    """
    按正则表达式搜索字段。

    :param analysis_obj: Analysis 对象
    :param pattern: 字段名正则表达式
    :return: 匹配的字段列表
    """
    regex = re.compile(pattern)
    fields = []
    for field_analysis in analysis_obj.get_fields():
        if regex.search(field_analysis.name):
            field_obj = field_analysis.get_field()
            field_info = {"name": field_analysis.name}
            if field_obj is not None:
                field_info["class"] = field_obj.get_class_name()
                field_info["descriptor"] = field_obj.get_descriptor()
                field_info["access_flags"] = (
                    field_obj.get_access_flags_string()
                )
            fields.append(field_info)

    return {"pattern": pattern, "total": len(fields), "fields": fields}


def analysis_permissions_map(analysis_obj) -> dict:
    """
    获取完整的权限映射。

    :param analysis_obj: Analysis 对象
    :return: 权限映射
    """
    try:
        perms = list(analysis_obj.get_permissions())
        perm_list = []
        for perm in perms:
            perm_list.append(str(perm))

        return {"total": len(perm_list), "permissions": perm_list}
    except Exception as e:
        return {"error": str(e)}


def analysis_class_exists(analysis_obj, class_name: str) -> dict:
    """
    检查指定类是否存在于分析中（快速布尔判断）。

    :param analysis_obj: Analysis 对象
    :param class_name: 类名（格式如 Lcom/example/MyClass;）
    :return: 存在性结果
    """
    try:
        exists = analysis_obj.is_class_present(class_name)
        return {"class": class_name, "exists": exists}
    except Exception as e:
        return {"class": class_name, "error": str(e)}


def analysis_method_analysis(
    analysis_obj, class_name: str, method_name: str, descriptor: str
) -> dict:
    """
    按 class+method+descriptor 精确获取方法分析（含完整 xref 信息）。

    :param analysis_obj: Analysis 对象
    :param class_name: 类名
    :param method_name: 方法名
    :param descriptor: 方法描述符（如 (Landroid/os/Bundle;)V）
    :return: 方法分析信息
    """
    try:
        ma = _resolve_method_analysis(
            analysis_obj, class_name, method_name, descriptor
        )
        if ma is None:
            return {
                "class": class_name,
                "method": method_name,
                "descriptor": descriptor,
                "error": "Method analysis not found",
            }

        result = {
            "class": ma.class_name,
            "method": ma.name,
            "descriptor": ma.descriptor,
            "is_external": ma.is_external(),
            "is_android_api": ma.is_android_api(),
        }

        # xref_from - 谁调用了此方法
        # MethodAnalysis.get_xref_from() 返回 set of (ClassAnalysis, MethodAnalysis, offset)
        xref_from = []
        for ref_class, ref_method, offset in ma.get_xref_from():
            xref_from.append(
                {
                    "from_class": ref_class.name,
                    "from_method": ref_method.name,
                    "from_descriptor": ref_method.descriptor,
                    "offset": offset,
                }
            )
        result["xref_from_count"] = len(xref_from)
        result["xref_from"] = xref_from

        # xref_to - 此方法调用了谁
        xref_to = []
        for ref_class, ref_method, offset in ma.get_xref_to():
            xref_to.append(
                {
                    "to_class": ref_class.name,
                    "to_method": ref_method.name,
                    "to_descriptor": ref_method.descriptor,
                    "offset": offset,
                }
            )
        result["xref_to_count"] = len(xref_to)
        result["xref_to"] = xref_to

        return result
    except Exception as e:
        return {
            "class": class_name,
            "method": method_name,
            "descriptor": descriptor,
            "error": str(e),
        }


def analysis_strings_analysis(analysis_obj, limit: int = None) -> dict:
    """
    获取全部字符串分析（含每个字符串的引用位置）。

    与 find-strings 不同，此命令返回所有字符串不过滤，
    可选 limit 限制返回数量。

    :param analysis_obj: Analysis 对象
    :param limit: 返回数量限制（可选）
    :return: 字符串分析列表
    """
    try:
        strings_map = analysis_obj.get_strings_analysis()
        strings = []
        for value, sa in strings_map.items():
            # get_xref_from() 返回 set of (ClassAnalysis, MethodAnalysis)
            origins = []
            for ref_class, ref_method in sa.get_xref_from():
                origins.append(
                    {
                        "class": ref_class.name,
                        "method": ref_method.name,
                        "descriptor": ref_method.descriptor,
                    }
                )
            strings.append(
                {
                    "value": value,
                    "used_in_count": len(origins),
                    "used_in": origins,
                }
            )
            if limit and len(strings) >= limit:
                break

        return {
            "total": len(strings),
            "all_strings_count": len(strings_map),
            "strings": strings,
        }
    except Exception as e:
        return {"error": str(e)}


def analysis_get_method(
    analysis_obj, class_name: str, method_name: str, descriptor: str
) -> dict:
    """
    按 class+method+descriptor 获取底层 EncodedMethod（含访问标志等元数据）。

    :param analysis_obj: Analysis 对象
    :param class_name: 类名
    :param method_name: 方法名
    :param descriptor: 方法描述符
    :return: EncodedMethod 元数据
    """
    try:
        em = analysis_obj.get_method_by_name(
            class_name, method_name, descriptor
        )
        if em is None:
            return {
                "class": class_name,
                "method": method_name,
                "descriptor": descriptor,
                "error": "Method not found",
            }

        result = {
            "class": class_name,
            "method": em.get_name(),
            "descriptor": em.get_descriptor(),
            "access_flags": em.get_access_flags_string(),
        }
        return result
    except Exception as e:
        return {
            "class": class_name,
            "method": method_name,
            "descriptor": descriptor,
            "error": str(e),
        }


def _field_analysis_info(field_analysis) -> dict:
    """将 FieldAnalysis 序列化为可读字典（含 xref 统计）"""
    field_obj = field_analysis.get_field()
    info = {"name": field_analysis.name}
    if field_obj is not None:
        info["class"] = field_obj.get_class_name()
        info["descriptor"] = field_obj.get_descriptor()
        info["access_flags"] = field_obj.get_access_flags_string()
    # xref 统计（不展开完整列表，避免输出过大）
    info["xref_read_count"] = len(field_analysis.get_xref_read())
    info["xref_write_count"] = len(field_analysis.get_xref_write())
    return info


def analysis_find_fields_advanced(
    analysis_obj,
    classname: str = ".*",
    fieldname: str = ".*",
    fieldtype: str = ".*",
    accessflags: str = ".*",
    limit: int = None,
    with_xrefs: bool = False,
) -> dict:
    """
    使用 Analysis 原生 find_fields 进行多维正则字段查找。

    :param analysis_obj: Analysis 对象
    :param classname: 类名正则
    :param fieldname: 字段名正则
    :param fieldtype: 字段类型正则
    :param accessflags: 访问标志正则（如 private|static）
    :param limit: 返回数量限制
    :param with_xrefs: 是否展开字段的完整 xref 列表
    :return: 匹配的字段列表
    """
    try:
        fields = []
        for fa in analysis_obj.find_fields(
            classname=classname,
            fieldname=fieldname,
            fieldtype=fieldtype,
            accessflags=accessflags,
        ):
            info = _field_analysis_info(fa)
            if with_xrefs:
                xref_read = []
                for ref_class, ref_method in fa.get_xref_read():
                    xref_read.append(
                        {
                            "class": ref_class.name,
                            "method": ref_method.name,
                            "descriptor": ref_method.descriptor,
                        }
                    )
                xref_write = []
                for ref_class, ref_method in fa.get_xref_write():
                    xref_write.append(
                        {
                            "class": ref_class.name,
                            "method": ref_method.name,
                            "descriptor": ref_method.descriptor,
                        }
                    )
                info["xref_read"] = xref_read
                info["xref_write"] = xref_write
            fields.append(info)
        total = len(fields)
        if limit:
            fields = fields[:limit]
        return {
            "filters": {
                "classname": classname,
                "fieldname": fieldname,
                "fieldtype": fieldtype,
                "accessflags": accessflags,
            },
            "total": total,
            "returned": len(fields),
            "fields": fields,
        }
    except Exception as e:
        return {"error": str(e)}


def analysis_field_analysis(
    analysis_obj, class_name: str, field_name: str
) -> dict:
    """
    获取指定字段的完整分析信息（含 read/write 交叉引用详情）。

    与 analysis_field_xrefs 类似，但通过原生 find_fields 精确匹配，
    并返回字段的访问标志和描述符。

    :param analysis_obj: Analysis 对象
    :param class_name: 类名
    :param field_name: 字段名
    :return: 字段分析信息
    """
    try:
        # 用 find_fields 精确匹配 classname + fieldname
        for fa in analysis_obj.find_fields(
            classname=re.escape(class_name),
            fieldname=re.escape(field_name),
        ):
            field_obj = fa.get_field()
            # find_fields 可能匹配到多个类的同名字段，确认类名匹配
            if (
                field_obj is not None
                and field_obj.get_class_name() != class_name
            ):
                continue
            result = {
                "class": class_name,
                "field": field_name,
            }
            if field_obj is not None:
                result["descriptor"] = field_obj.get_descriptor()
                result["access_flags"] = field_obj.get_access_flags_string()

            xref_read = []
            for ref_class, ref_method in fa.get_xref_read():
                xref_read.append(
                    {
                        "class": ref_class.name,
                        "method": ref_method.name,
                        "descriptor": ref_method.descriptor,
                    }
                )
            result["xref_read_count"] = len(xref_read)
            result["xref_read"] = xref_read

            xref_write = []
            for ref_class, ref_method in fa.get_xref_write():
                xref_write.append(
                    {
                        "class": ref_class.name,
                        "method": ref_method.name,
                        "descriptor": ref_method.descriptor,
                    }
                )
            result["xref_write_count"] = len(xref_write)
            result["xref_write"] = xref_write
            return result
        return {
            "class": class_name,
            "field": field_name,
            "error": "Field not found",
        }
    except Exception as e:
        return {"class": class_name, "field": field_name, "error": str(e)}


def analysis_api_usage_grouped(
    analysis_obj, limit: int = None, group_by_class: bool = False
) -> dict:
    """
    获取应用使用的 Android API（外部 API 方法），可选按类分组。

    与 analysis_android_api_usage（with_xrefs 展开调用方）的区别：本函数专注
    API 列表本身，支持 group_by_class 按类聚合统计，对应 api-usage CLI 命令。

    :param analysis_obj: Analysis 对象
    :param limit: 返回数量限制
    :param group_by_class: 是否按 API 类分组统计
    :return: API 使用列表
    """
    try:
        apis = []
        for ma in analysis_obj.get_android_api_usage():
            apis.append(
                {
                    "class": ma.class_name,
                    "method": ma.name,
                    "descriptor": ma.descriptor,
                    "is_external": ma.is_external(),
                }
            )
        total = len(apis)
        if group_by_class:
            groups = {}
            for api in apis:
                cls = api["class"]
                groups.setdefault(cls, []).append(
                    {
                        "method": api["method"],
                        "descriptor": api["descriptor"],
                    }
                )
            result = {
                "total": total,
                "class_count": len(groups),
                "classes": groups,
            }
            if limit:
                limited = dict(list(groups.items())[:limit])
                result["returned_classes"] = len(limited)
                result["classes"] = limited
            return result
        if limit:
            apis = apis[:limit]
        return {"total": total, "returned": len(apis), "apis": apis}
    except Exception as e:
        return {"error": str(e)}


# ================================================================
# 第五轮：ClassAnalysis / MethodAnalysis / StringAnalysis 遗漏方法
# ================================================================


def analysis_class_hierarchy_info(analysis_obj, class_name: str) -> dict:
    """
    获取类的继承关系（父类 + 实现的接口）。

    :param analysis_obj: Analysis 对象
    :param class_name: 类名
    :return: 继承关系信息
    """
    try:
        ca = analysis_obj.get_class_analysis(class_name)
        if ca is None:
            return {"class": class_name, "error": "Class not found"}
        result = {
            "class": class_name,
            "is_external": ca.is_external(),
            "is_android_api": ca.is_android_api(),
        }
        # extends / implements 是 property
        try:
            result["extends"] = ca.extends
        except Exception:
            pass
        try:
            result["implements"] = list(ca.implements)
        except Exception:
            pass
        return result
    except Exception as e:
        return {"class": class_name, "error": str(e)}


def analysis_class_xref_new_instance(analysis_obj, class_name: str) -> dict:
    """
    获取谁实例化了指定类（new-instance 交叉引用）。

    :param analysis_obj: Analysis 对象
    :param class_name: 类名
    :return: 实例化此类的方法列表
    """
    try:
        ca = analysis_obj.get_class_analysis(class_name)
        if ca is None:
            return {"class": class_name, "error": "Class not found"}
        # get_xref_new_instance 返回 list of (MethodAnalysis, offset)
        refs = []
        for ref_method, offset in ca.get_xref_new_instance():
            refs.append(
                {
                    "class": ref_method.class_name,
                    "method": ref_method.name,
                    "descriptor": ref_method.descriptor,
                    "offset": offset,
                }
            )
        return {
            "class": class_name,
            "total": len(refs),
            "xref_new_instance": refs,
        }
    except Exception as e:
        return {"class": class_name, "error": str(e)}


def analysis_class_xref_const_class(analysis_obj, class_name: str) -> dict:
    """
    获取谁引用了指定类的 Class 对象（const-class 交叉引用）。

    :param analysis_obj: Analysis 对象
    :param class_name: 类名
    :return: 引用此类 Class 对象的方法列表
    """
    try:
        ca = analysis_obj.get_class_analysis(class_name)
        if ca is None:
            return {"class": class_name, "error": "Class not found"}
        # get_xref_const_class 返回 list of (MethodAnalysis, offset)
        refs = []
        for ref_method, offset in ca.get_xref_const_class():
            refs.append(
                {
                    "class": ref_method.class_name,
                    "method": ref_method.name,
                    "descriptor": ref_method.descriptor,
                    "offset": offset,
                }
            )
        return {
            "class": class_name,
            "total": len(refs),
            "xref_const_class": refs,
        }
    except Exception as e:
        return {"class": class_name, "error": str(e)}


def analysis_class_detail(analysis_obj, class_name: str) -> dict:
    """
    获取类的综合分析信息（继承/接口/方法数/xref 统计/vm_class）。

    :param analysis_obj: Analysis 对象
    :param class_name: 类名
    :return: 类综合信息
    """
    try:
        ca = analysis_obj.get_class_analysis(class_name)
        if ca is None:
            return {"class": class_name, "error": "Class not found"}
        result = {
            "class": class_name,
            "is_external": ca.is_external(),
            "is_android_api": ca.is_android_api(),
            "nb_methods": ca.get_nb_methods(),
        }
        try:
            result["extends"] = ca.extends
        except Exception:
            pass
        try:
            result["implements"] = list(ca.implements)
        except Exception:
            pass
        # xref 统计
        try:
            result["xref_from_count"] = len(ca.get_xref_from())
        except Exception:
            pass
        try:
            result["xref_to_count"] = len(ca.get_xref_to())
        except Exception:
            pass
        try:
            result["xref_new_instance_count"] = len(ca.get_xref_new_instance())
        except Exception:
            pass
        try:
            result["xref_const_class_count"] = len(ca.get_xref_const_class())
        except Exception:
            pass
        # vm_class 类型
        try:
            vm_class = ca.get_vm_class()
            result["vm_class_type"] = type(vm_class).__name__
        except Exception:
            pass
        return result
    except Exception as e:
        return {"class": class_name, "error": str(e)}


def analysis_method_basic_blocks(
    analysis_obj, class_name: str, method_name: str, descriptor: str
) -> dict:
    """
    获取方法的基本块（BasicBlock）列表。

    :param analysis_obj: Analysis 对象
    :param class_name: 类名
    :param method_name: 方法名
    :param descriptor: 方法描述符
    :return: 基本块列表
    """
    try:
        ma = _resolve_method_analysis(
            analysis_obj, class_name, method_name, descriptor
        )
        if ma is None:
            return {
                "class": class_name,
                "method": method_name,
                "descriptor": descriptor,
                "error": "Method analysis not found",
            }
        bb_list = []
        for bb in ma.get_basic_blocks():
            bb_info = {
                "name": bb.get_name(),
                "start": bb.get_start(),
                "end": bb.get_end(),
                "nb_instructions": bb.get_nb_instructions(),
            }
            # 分析器注释（如检测到的 return/throw 模式标记）
            try:
                notes = bb.get_notes()
                if notes:
                    bb_info["notes"] = list(notes)
            except Exception:
                pass
            # 块的最后一条指令（终止指令，决定 CFG 后继方向）
            try:
                last = bb.get_last()
                if last is not None:
                    bb_info["last_instruction"] = {
                        "name": last.get_name(),
                        "output": last.get_output(),
                    }
            except Exception:
                pass
            # 后继基本块：list of (start, end, DEXBasicBlock)
            try:
                childs = []
                for child in bb.childs:
                    if isinstance(child, tuple) and len(child) >= 3:
                        target_bb = child[2]
                        childs.append(
                            {
                                "start": child[0],
                                "end": child[1],
                                "name": (
                                    target_bb.get_name()
                                    if hasattr(target_bb, "get_name")
                                    else str(target_bb)
                                ),
                            }
                        )
                    else:
                        childs.append(str(child))
                bb_info["childs"] = childs
            except Exception:
                pass
            # 前驱基本块：list of (start, end, DEXBasicBlock)
            try:
                fathers = []
                for father in bb.fathers:
                    if isinstance(father, tuple) and len(father) >= 3:
                        target_bb = father[2]
                        fathers.append(
                            {
                                "start": father[0],
                                "end": father[1],
                                "name": (
                                    target_bb.get_name()
                                    if hasattr(target_bb, "get_name")
                                    else str(target_bb)
                                ),
                            }
                        )
                    else:
                        fathers.append(str(father))
                bb_info["fathers"] = fathers
            except Exception:
                pass
            bb_list.append(bb_info)
        return {
            "class": class_name,
            "method": method_name,
            "descriptor": descriptor,
            "total": len(bb_list),
            "basic_blocks": bb_list,
        }
    except Exception as e:
        return {
            "class": class_name,
            "method": method_name,
            "descriptor": descriptor,
            "error": str(e),
        }


def analysis_method_exceptions(
    analysis_obj, class_name: str, method_name: str, descriptor: str
) -> dict:
    """
    获取方法的 try/catch 异常处理表。

    遍历方法所有基本块的 get_exception_analysis()，返回每个含异常处理的基本块
    及其 try 区间（start/end offset）和 catch 块列表（异常类名 + catch 基本块名）。
    用于逆向定位 try/catch 结构、异常流向分析。

    :param analysis_obj: Analysis 对象
    :param class_name: 类名
    :param method_name: 方法名
    :param descriptor: 方法描述符
    :return: 方法的异常处理表
    """
    try:
        ma = _resolve_method_analysis(
            analysis_obj, class_name, method_name, descriptor
        )
        if ma is None:
            return {
                "class": class_name,
                "method": method_name,
                "descriptor": descriptor,
                "error": "Method analysis not found",
            }
        exceptions = []
        for bb in ma.get_basic_blocks():
            try:
                ea = bb.get_exception_analysis()
            except Exception:
                continue
            if ea is None:
                continue
            try:
                data = ea.get()
            except Exception:
                continue
            if not isinstance(data, dict):
                continue
            handlers = []
            for item in data.get("list", []):
                if isinstance(item, dict):
                    handlers.append(
                        {
                            "exception_class": item.get("name"),
                            "idx": item.get("idx"),
                            "catch_block": item.get("basic_block"),
                        }
                    )
                else:
                    handlers.append({"raw": str(item)})
            exceptions.append(
                {
                    "basic_block": bb.get_name(),
                    "start": data.get("start"),
                    "end": data.get("end"),
                    "handlers": handlers,
                }
            )
        return {
            "class": ma.class_name,
            "method": ma.name,
            "descriptor": ma.descriptor,
            "full_name": ma.full_name,
            "total": len(exceptions),
            "exceptions": exceptions,
        }
    except Exception as e:
        return {
            "class": class_name,
            "method": method_name,
            "descriptor": descriptor,
            "error": str(e),
        }


def analysis_method_detail(
    analysis_obj, class_name: str, method_name: str, descriptor: str
) -> dict:
    """
    获取方法的综合分析信息（full_name/access/length/各类 xref 统计）。

    :param analysis_obj: Analysis 对象
    :param class_name: 类名
    :param method_name: 方法名
    :param descriptor: 方法描述符
    :return: 方法综合信息
    """
    try:
        ma = _resolve_method_analysis(
            analysis_obj, class_name, method_name, descriptor
        )
        if ma is None:
            return {
                "class": class_name,
                "method": method_name,
                "descriptor": descriptor,
                "error": "Method analysis not found",
            }
        result = {
            "class": ma.class_name,
            "method": ma.name,
            "descriptor": ma.descriptor,
            "full_name": ma.full_name,
            "access_flags": ma.get_access_flags_string(),
            "is_external": ma.is_external(),
            "is_android_api": ma.is_android_api(),
            "length": ma.get_length(),
        }
        # 各类 xref 统计
        try:
            result["xref_from_count"] = len(ma.get_xref_from())
        except Exception:
            pass
        try:
            result["xref_to_count"] = len(ma.get_xref_to())
        except Exception:
            pass
        try:
            result["xref_new_instance_count"] = len(ma.get_xref_new_instance())
        except Exception:
            pass
        try:
            result["xref_const_class_count"] = len(ma.get_xref_const_class())
        except Exception:
            pass
        try:
            result["xref_read_count"] = len(ma.get_xref_read())
        except Exception:
            pass
        try:
            result["xref_write_count"] = len(ma.get_xref_write())
        except Exception:
            pass
        # 基本块数
        try:
            result["basic_blocks_count"] = len(ma.get_basic_blocks())
        except Exception:
            pass
        return result
    except Exception as e:
        return {
            "class": class_name,
            "method": method_name,
            "descriptor": descriptor,
            "error": str(e),
        }


def analysis_method_xrefs_detail(
    analysis_obj, class_name: str, method_name: str, descriptor: str
) -> dict:
    """
    获取方法级 xref 的完整引用列表（6 类：from/to/read/write/new_instance/const_class）。

    与 analysis_method_detail（仅返回统计数）和 analysis_method_xrefs（仅 from/to，无 descriptor）
    的区别：本命令按 class+method+descriptor 精确查，返回每类 xref 的完整引用详情（含 offset），
    用于逆向追踪"某方法读写了哪些字段、new 了哪些类、调用了哪些方法、被谁调用"。

    :param analysis_obj: Analysis 对象
    :param class_name: 类名
    :param method_name: 方法名
    :param descriptor: 方法描述符（如 (Landroid/os/Bundle;)V）
    :return: 6 类 xref 的完整引用列表
    """
    try:
        ma = _resolve_method_analysis(
            analysis_obj, class_name, method_name, descriptor
        )
        if ma is None:
            return {
                "class": class_name,
                "method": method_name,
                "descriptor": descriptor,
                "error": "Method analysis not found",
            }

        result = {
            "class": ma.class_name,
            "method": ma.name,
            "descriptor": ma.descriptor,
            "full_name": ma.full_name,
        }

        # XrefFrom - 谁调用了此方法
        # get_xref_from() 返回 list of (ClassAnalysis, MethodAnalysis, offset)
        xref_from = []
        try:
            for ref_class, ref_method, offset in ma.get_xref_from():
                xref_from.append(
                    {
                        "class": ref_class.name,
                        "method": ref_method.name,
                        "descriptor": ref_method.descriptor,
                        "offset": offset,
                    }
                )
        except Exception:
            pass
        result["xref_from"] = {"count": len(xref_from), "refs": xref_from}

        # XrefTo - 此方法调用了谁
        # get_xref_to() 返回 list of (ClassAnalysis, MethodAnalysis, offset)
        xref_to = []
        try:
            for ref_class, ref_method, offset in ma.get_xref_to():
                xref_to.append(
                    {
                        "class": ref_class.name,
                        "method": ref_method.name,
                        "descriptor": ref_method.descriptor,
                        "offset": offset,
                    }
                )
        except Exception:
            pass
        result["xref_to"] = {"count": len(xref_to), "refs": xref_to}

        # XrefRead - 此方法读了哪些字段
        # get_xref_read() 返回 list of (ClassAnalysis, FieldAnalysis, offset)
        xref_read = []
        try:
            for ref_class, field_analysis, offset in ma.get_xref_read():
                xref_read.append(
                    {
                        "class": ref_class.name,
                        "field": field_analysis.name,
                        "offset": offset,
                    }
                )
        except Exception:
            pass
        result["xref_read"] = {"count": len(xref_read), "refs": xref_read}

        # XrefWrite - 此方法写了哪些字段
        # get_xref_write() 返回 list of (ClassAnalysis, FieldAnalysis, offset)
        xref_write = []
        try:
            for ref_class, field_analysis, offset in ma.get_xref_write():
                xref_write.append(
                    {
                        "class": ref_class.name,
                        "field": field_analysis.name,
                        "offset": offset,
                    }
                )
        except Exception:
            pass
        result["xref_write"] = {"count": len(xref_write), "refs": xref_write}

        # XrefNewInstance - 此方法 new 了哪些类
        # get_xref_new_instance() 返回 list of (ClassAnalysis, offset)
        xref_new = []
        try:
            for ref_class, offset in ma.get_xref_new_instance():
                xref_new.append(
                    {
                        "class": ref_class.name,
                        "offset": offset,
                    }
                )
        except Exception:
            pass
        result["xref_new_instance"] = {
            "count": len(xref_new),
            "refs": xref_new,
        }

        # XrefConstClass - 此方法引用了哪些类字面量（const-class 指令）
        # get_xref_const_class() 返回 list of (ClassAnalysis, offset)
        xref_const = []
        try:
            for ref_class, offset in ma.get_xref_const_class():
                xref_const.append(
                    {
                        "class": ref_class.name,
                        "offset": offset,
                    }
                )
        except Exception:
            pass
        result["xref_const_class"] = {
            "count": len(xref_const),
            "refs": xref_const,
        }

        return result
    except Exception as e:
        return {
            "class": class_name,
            "method": method_name,
            "descriptor": descriptor,
            "error": str(e),
        }


def analysis_strings_overwritten(analysis_obj) -> dict:
    """
    获取被覆盖的字符串（运行时被修改原值的字符串）。

    :param analysis_obj: Analysis 对象
    :return: 被覆盖字符串列表（含原值和当前值）
    """
    try:
        sa_dict = analysis_obj.get_strings_analysis()
        overwritten = []
        for value, sa in sa_dict.items():
            if sa.is_overwritten():
                overwritten.append(
                    {
                        "current_value": sa.get_value(),
                        "original_value": sa.get_orig_value(),
                    }
                )
        return {
            "total_strings": len(sa_dict),
            "overwritten_count": len(overwritten),
            "strings": overwritten,
        }
    except Exception as e:
        return {"error": str(e)}


# ================================================================
# 第六轮：调用图与 API 权限映射
# ================================================================


def analysis_call_graph(
    analysis_obj, limit: int = None, external: bool = False
) -> dict:
    """
    获取完整调用图（networkx DiGraph）并序列化。

    节点是方法（classname/methodname/descriptor/accessflags/external/entrypoint），
    边是调用关系。默认只返回内部方法的边（external=True 含外部方法）。

    :param analysis_obj: Analysis 对象
    :param limit: 返回边数量限制（调用图可能很大）
    :param external: 是否包含外部方法节点
    :return: 调用图节点和边
    """
    try:
        cg = analysis_obj.get_call_graph()
        nodes = []
        for n, data in cg.nodes(data=True):
            if not external and data.get("external"):
                continue
            nodes.append(
                {
                    "classname": data.get("classname"),
                    "methodname": data.get("methodname"),
                    "descriptor": data.get("descriptor"),
                    "accessflags": data.get("accessflags"),
                    "external": data.get("external", False),
                    "entrypoint": data.get("entrypoint", False),
                }
            )
        edges = []
        for u, v in cg.edges():
            u_data = cg.nodes[u]
            v_data = cg.nodes[v]
            if not external and (
                u_data.get("external") or v_data.get("external")
            ):
                continue
            edges.append(
                {
                    "from": {
                        "classname": u_data.get("classname"),
                        "methodname": u_data.get("methodname"),
                    },
                    "to": {
                        "classname": v_data.get("classname"),
                        "methodname": v_data.get("methodname"),
                    },
                }
            )
            if limit and len(edges) >= limit:
                break
        # networkx 图的 nodes/edges 迭代序取决于 create_xref 的 set 驱动构建，
        # 非确定 → 输出列表顺序每次不同。排序固定（agent 对接需确定性）。
        nodes.sort(
            key=lambda n: (
                n.get("classname") or "",
                n.get("methodname") or "",
                n.get("descriptor") or "",
            )
        )
        edges.sort(
            key=lambda e: (
                (
                    e["from"].get("classname") or "",
                    e["from"].get("methodname") or "",
                ),
                (
                    e["to"].get("classname") or "",
                    e["to"].get("methodname") or "",
                ),
            )
        )
        return {
            "total_nodes": cg.number_of_nodes(),
            "total_edges": cg.number_of_edges(),
            "returned_nodes": len(nodes),
            "returned_edges": len(edges),
            "nodes": nodes,
            "edges": edges,
        }
    except Exception as e:
        return {"error": str(e)}


def analysis_call_graph_filtered(
    analysis_obj,
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

    与 analysis_call_graph（全量图）的区别：本命令透传 get_call_graph 的过滤参数，
    生成只含匹配方法的子图，避免全图过大。例如 classname=Lcom/example/Foo;
    只保留 Foo 类方法的调用关系。

    :param analysis_obj: Analysis 对象
    :param classname: 类名正则（如 Lcom/example/Foo;，需转义 ;）
    :param methodname: 方法名正则
    :param descriptor: 描述符正则
    :param accessflags: 访问标志正则（如 public.*static）
    :param no_isolated: 移除孤立节点（无任何边的节点）
    :param external: 是否包含外部方法节点（默认只内部）
    :param limit: 返回边数量限制
    :return: 过滤后的调用图节点和边
    """
    import re

    try:
        kwargs = {}
        if classname:
            kwargs["classname"] = classname
        if methodname:
            kwargs["methodname"] = methodname
        if descriptor:
            kwargs["descriptor"] = descriptor
        if accessflags:
            kwargs["accessflags"] = accessflags
        if no_isolated:
            kwargs["no_isolated"] = True

        cg = analysis_obj.get_call_graph(**kwargs)
        nodes = []
        for n, data in cg.nodes(data=True):
            if not external and data.get("external"):
                continue
            nodes.append(
                {
                    "classname": data.get("classname"),
                    "methodname": data.get("methodname"),
                    "descriptor": data.get("descriptor"),
                    "accessflags": data.get("accessflags"),
                    "external": data.get("external", False),
                    "entrypoint": data.get("entrypoint", False),
                }
            )
        edges = []
        for u, v in cg.edges():
            u_data = cg.nodes[u]
            v_data = cg.nodes[v]
            if not external and (
                u_data.get("external") or v_data.get("external")
            ):
                continue
            edges.append(
                {
                    "from": {
                        "classname": u_data.get("classname"),
                        "methodname": u_data.get("methodname"),
                    },
                    "to": {
                        "classname": v_data.get("classname"),
                        "methodname": v_data.get("methodname"),
                    },
                }
            )
            if limit and len(edges) >= limit:
                break
        # 同 call-graph：networkx 节点/边迭代序非确定，排序固定输出
        nodes.sort(
            key=lambda n: (
                n.get("classname") or "",
                n.get("methodname") or "",
                n.get("descriptor") or "",
            )
        )
        edges.sort(
            key=lambda e: (
                (
                    e["from"].get("classname") or "",
                    e["from"].get("methodname") or "",
                ),
                (
                    e["to"].get("classname") or "",
                    e["to"].get("methodname") or "",
                ),
            )
        )
        return {
            "filter": {
                "classname": classname,
                "methodname": methodname,
                "descriptor": descriptor,
                "accessflags": accessflags,
                "no_isolated": no_isolated,
                "external": external,
            },
            "total_nodes": cg.number_of_nodes(),
            "total_edges": cg.number_of_edges(),
            "returned_nodes": len(nodes),
            "returned_edges": len(edges),
            "nodes": nodes,
            "edges": edges,
        }
    except Exception as e:
        return {"error": str(e)}


def analysis_permissions(
    analysis_obj, apilevel=None, limit: int = None
) -> dict:
    """
    基于 API level 的方法→权限映射分析（get_permissions）。

    返回调用到的需要权限的 API 方法及其所需权限列表。
    与 permission-usage（按单权限反查）不同，此命令批量列出所有需权限的 API 调用。

    :param analysis_obj: Analysis 对象
    :param apilevel: API level（None 用默认）
    :param limit: 返回数量限制
    :return: API 方法 → 权限列表
    """
    try:
        results = []
        for ma, perms in analysis_obj.get_permissions(apilevel):
            results.append(
                {
                    "method": {
                        "class_name": (
                            ma.get_class_name()
                            if hasattr(ma, "get_class_name")
                            else None
                        ),
                        "name": ma.name if hasattr(ma, "name") else None,
                        "descriptor": (
                            ma.descriptor
                            if hasattr(ma, "descriptor")
                            else None
                        ),
                        "is_external": (
                            ma.is_external()
                            if hasattr(ma, "is_external")
                            else None
                        ),
                    },
                    "permissions": list(perms),
                }
            )
        total = len(results)
        if limit:
            results = results[:limit]
        return {
            "apilevel": apilevel,
            "total": total,
            "returned": len(results),
            "results": results,
        }
    except Exception as e:
        return {"apilevel": apilevel, "error": str(e)}


# ================================================================
# 第十七轮：方法 API/权限标注查询
# ================================================================


def analysis_method_api_info(
    analysis_obj, class_name: str, method_name: str, descriptor: str
) -> dict:
    """
    查询方法的 API 与权限标注属性（is_android_api/is_external/domain_flag/
    restriction_flag/apilist）。

    与 analysis_method_detail（综合统计，含 xref 计数但不含权限标注）的区别：
    本命令聚焦权限审计维度——is_android_api 判断是否为 AOSP API、
    domain_flag/restriction_flag/apilist 是 AndroGuard 权限映射流程
    （Analysis.create_xref + PermissionAnalysis）填充的标注。
    常规加载下这些标注字段可能为 None（需先运行权限映射流程才有值），
    但 is_android_api/is_external 始终可用。

    :param analysis_obj: Analysis 对象
    :param class_name: 类名
    :param method_name: 方法名
    :param descriptor: 方法描述符（如 (Landroid/os/Bundle;)V）
    :return: 方法 API/权限标注属性
    """
    try:
        ma = _resolve_method_analysis(
            analysis_obj, class_name, method_name, descriptor
        )
        if ma is None:
            return {
                "class": class_name,
                "method": method_name,
                "descriptor": descriptor,
                "error": "Method analysis not found",
            }
        result = {
            "class": ma.class_name,
            "method": ma.name,
            "descriptor": ma.descriptor,
            "full_name": ma.full_name,
            "access_flags": ma.get_access_flags_string(),
            "is_external": ma.is_external(),
            "is_android_api": ma.is_android_api(),
        }
        # 权限标注属性（属性非方法，getattr 安全访问；可能为 None）
        for attr in ("domain_flag", "restriction_flag"):
            try:
                result[attr] = getattr(ma, attr, None)
            except Exception:
                result[attr] = None
        # apilist 可能是 list 或 None
        try:
            apilist = getattr(ma, "apilist", None)
            if apilist is None:
                result["apilist"] = None
            elif isinstance(apilist, (list, tuple, set)):
                result["apilist"] = [str(x) for x in apilist]
            else:
                result["apilist"] = str(apilist)
        except Exception:
            result["apilist"] = None
        # 代码长度（0 表示外部无实现体）
        try:
            result["length"] = ma.get_length()
        except Exception:
            pass
        return result
    except Exception as e:
        return {
            "class": class_name,
            "method": method_name,
            "descriptor": descriptor,
            "error": str(e),
        }


# ================================================================
# 第十七轮：方法全貌聚合
# ================================================================


def analysis_method_summary(
    dex_list,
    analysis_obj,
    class_name: str,
    method_name: str,
    descriptor: str = None,
    include_source: bool = True,
    xref_limit: int = 10,
) -> dict:
    """
    聚合方法的全部分析信息（一键出方法全貌）。

    单条命令聚合：方法元信息（access/length/is_external/is_android_api）+
    6 类 xref 统计与摘要引用 + 基本块数 + 异常处理块数 + 反编译 Java 源码。
    省去用户串调 method-detail / method-xrefs-detail / method-basic-blocks /
    method-exceptions / decompile method 五个命令。

    与各原子命令的区别：本命令是聚合视图，xref 引用默认限制前 xref_limit 条
    （原子命令返回全量），适合快速概览；需全量引用时用对应的 -detail 命令。

    :param dex_list: DEX 对象列表（反编译源码需要）
    :param analysis_obj: Analysis 对象
    :param class_name: 类名
    :param method_name: 方法名
    :param descriptor: 方法描述符（可选，传时精确匹配，不传则按类内首个同名方法）
    :param include_source: 是否包含反编译源码（默认 True）
    :param xref_limit: 每类 xref 引用返回上限（默认 10，None 返回全量）
    :return: 方法全貌聚合信息
    """
    try:
        # 1. 定位 MethodAnalysis（descriptor 可选）
        if descriptor:
            ma = _resolve_method_analysis(
                analysis_obj, class_name, method_name, descriptor
            )
        else:
            ma = None
            try:
                ca = analysis_obj.get_class_analysis(class_name)
            except Exception:
                ca = None
            if ca is not None:
                for m in ca.get_methods():
                    try:
                        if m.name == method_name:
                            ma = m
                            break
                    except Exception:
                        continue
        if ma is None:
            return {
                "class": class_name,
                "method": method_name,
                "descriptor": descriptor,
                "error": "Method analysis not found",
            }

        actual_descriptor = ma.descriptor

        # 2. 元信息
        summary = {
            "class": ma.class_name,
            "method": ma.name,
            "descriptor": actual_descriptor,
            "full_name": ma.full_name,
            "access_flags": ma.get_access_flags_string(),
            "is_external": ma.is_external(),
            "is_android_api": ma.is_android_api(),
        }
        try:
            summary["length"] = ma.get_length()
        except Exception:
            pass

        # 3. 6 类 xref 统计 + 摘要引用
        xref_stats = {}
        xref_sources = [
            (
                "xref_from",
                ma.get_xref_from,
                ("class", "method", "descriptor", "offset"),
            ),
            (
                "xref_to",
                ma.get_xref_to,
                ("class", "method", "descriptor", "offset"),
            ),
        ]
        for key, getter, fields in xref_sources:
            refs = []
            try:
                for ref_class, ref_method, offset in getter():
                    refs.append(
                        {
                            "class": ref_class.name,
                            "method": ref_method.name,
                            "descriptor": ref_method.descriptor,
                            "offset": offset,
                        }
                    )
            except Exception:
                pass
            xref_stats[key] = _summarize_refs(refs, xref_limit, fields)

        # read/write: (ClassAnalysis, FieldAnalysis, offset)
        for key, getter in [
            ("xref_read", ma.get_xref_read),
            ("xref_write", ma.get_xref_write),
        ]:
            refs = []
            try:
                for ref_class, field_analysis, offset in getter():
                    refs.append(
                        {
                            "class": ref_class.name,
                            "field": field_analysis.name,
                            "offset": offset,
                        }
                    )
            except Exception:
                pass
            xref_stats[key] = _summarize_refs(
                refs, xref_limit, ("class", "field", "offset")
            )

        # new_instance/const_class: (ClassAnalysis, offset)
        for key, getter in [
            ("xref_new_instance", ma.get_xref_new_instance),
            ("xref_const_class", ma.get_xref_const_class),
        ]:
            refs = []
            try:
                for ref_class, offset in getter():
                    refs.append(
                        {
                            "class": ref_class.name,
                            "offset": offset,
                        }
                    )
            except Exception:
                pass
            xref_stats[key] = _summarize_refs(
                refs, xref_limit, ("class", "offset")
            )
        summary["xrefs"] = xref_stats

        # 4. 基本块数 + 异常处理块数
        try:
            bbs = ma.get_basic_blocks()
            bb_count = len(bbs) if bbs else 0
            summary["basic_blocks_count"] = bb_count
            # 异常处理块数
            exc_count = 0
            for bb in bbs or []:
                try:
                    ea = bb.get_exception_analysis()
                    if ea is not None:
                        exc_count += 1
                except Exception:
                    continue
            summary["exception_blocks_count"] = exc_count
        except Exception:
            pass

        # 5. 反编译源码（可选）
        if include_source:
            try:
                from androguard.skills import decompiler_skills

                decomp = decompiler_skills.decompile_method(
                    dex_list, analysis_obj, class_name, method_name
                )
                if decomp.get("error"):
                    summary["source"] = ""
                    summary["source_error"] = decomp["error"]
                else:
                    summary["source"] = decomp.get("source", "")
            except Exception as e:
                summary["source"] = ""
                summary["source_error"] = (
                    f"Decompilation failed: {str(e)[:80]}"
                )
        return summary
    except Exception as e:
        return {
            "class": class_name,
            "method": method_name,
            "descriptor": descriptor,
            "error": str(e),
        }


def _summarize_refs(refs, limit, fields) -> dict:
    """将引用列表聚合成 {count, returned, refs} 摘要。

    先按 fields 排序固定顺序（xref getter 返回 set，迭代序非确定，会导致
    切片后的 refs 顺序每次不同 → agent 对接无法稳定比对），再按 limit 切片。
    """
    try:
        # 构造稳定排序键：用 fields 中存在的字段值组成 tuple
        refs = sorted(
            refs,
            key=lambda r: tuple(
                (r.get(f) if r.get(f) is not None else "") for f in fields
            ),
        )
    except Exception:
        pass
    total = len(refs)
    if limit is not None:
        sliced = refs[:limit]
    else:
        sliced = refs
    return {"count": total, "returned": len(sliced), "refs": sliced}


# ================================================================
# 第十八轮：Android API 使用聚合查询
# ================================================================


def analysis_android_api_usage(
    analysis_obj, limit: int = None, with_xrefs: bool = False
) -> dict:
    """
    批量列出 APK 使用的所有 Android 平台 API 方法。

    用 Analysis.get_android_api_usage() 返回所有被使用的 Android API
    MethodAnalysis（is_android_api=True 的外部方法），每项含
    class/method/descriptor。这是 method-api-info（单方法查询）的批量版，
    用于安全审计"这个 APK 调用了哪些系统 API"。

    :param analysis_obj: Analysis 对象
    :param limit: 返回数量上限（默认全部）
    :param with_xrefs: 是否展开每个 API 的调用方 xref（默认 False，仅列 API）
    :return: Android API 使用列表
    """
    try:
        # create_xref 幂等：确保交叉引用已建立（AnalyzeAPK 通常已自动调用）
        try:
            analysis_obj.create_xref()
        except Exception:
            pass
        apis = list(analysis_obj.get_android_api_usage())
        total = len(apis)
        sliced = apis[:limit] if limit else apis
        results = []
        for ma in sliced:
            item = {
                "class": ma.class_name,
                "method": ma.name,
                "descriptor": ma.descriptor,
                "full_name": ma.full_name,
            }
            if with_xrefs:
                # 调用方 xref：谁调用了这个 API
                try:
                    callers = []
                    for ref_class, ref_method, offset in ma.get_xref_from():
                        callers.append(
                            {
                                "from_class": ref_class.name,
                                "from_method": ref_method.name,
                                "from_descriptor": ref_method.descriptor,
                                "offset": offset,
                            }
                        )
                    item["callers_count"] = len(callers)
                    item["callers"] = callers
                except Exception:
                    pass
            results.append(item)
        return {
            "total": total,
            "returned": len(results),
            "apis": results,
        }
    except Exception as e:
        return {"error": str(e)}


def analysis_class_fields(
    analysis_obj, class_name: str, limit: int = None
) -> dict:
    """
    列出指定类的全部字段及其交叉引用统计（类级字段视图）。

    与 field-xrefs/field-xrefs-detail（单字段全 xref）和 find-fields（全局正则搜索）
    的区别：本命令遍历 ClassAnalysis.get_fields() 一次列出类内所有字段，每项含
    name/descriptor/access_flags + xref_read/xref_write **计数**（不带完整引用列表，
    避免输出过大），用于快速定位类内哪些字段被频繁读写（状态字段/配置字段/敏感字段）。

    :param analysis_obj: Analysis 对象
    :param class_name: 类名
    :param limit: 返回字段数量上限
    :return: 类内字段列表 + xref 计数
    """
    try:
        ca = analysis_obj.get_class_analysis(class_name)
        if ca is None:
            return {"class": class_name, "error": "Class not found"}
        fields = list(ca.get_fields())
        total = len(fields)
        sliced = fields[:limit] if limit else fields
        results = []
        for fa in sliced:
            item = {
                "name": fa.name,
            }
            field_obj = fa.get_field() if hasattr(fa, "get_field") else None
            if field_obj is not None:
                try:
                    item["descriptor"] = field_obj.get_descriptor()
                except Exception:
                    pass
                try:
                    item["access_flags"] = field_obj.get_access_flags_string()
                except Exception:
                    pass
            # xref 计数（with_offset=False 返回 list[(ClassAnalysis, MethodAnalysis)]）
            try:
                reads = fa.get_xref_read()
                item["xref_read_count"] = len(reads)
            except Exception:
                item["xref_read_count"] = 0
            try:
                writes = fa.get_xref_write()
                item["xref_write_count"] = len(writes)
            except Exception:
                item["xref_write_count"] = 0
            results.append(item)
        return {
            "class": class_name,
            "is_external": ca.is_external(),
            "fields_total": total,
            "returned": len(results),
            "fields": results,
        }
    except Exception as e:
        return {"class": class_name, "error": str(e)}


def analysis_string_info(
    analysis_obj, value: str, xref_limit: int = None
) -> dict:
    """
    按精确字符串值查询单个字符串的完整分析详情（原始值/当前值/是否覆盖 + 引用位置）。

    与 strings-overwritten（仅列出被覆盖字符串清单）和 find-strings（正则搜索 + 简要
    used_in）的区别：本命令按精确 value 取单个 StringAnalysis，返回 is_overwritten /
    orig_value / value 三者对照（混淆检测：运行时被覆写的字符串 orig_value 与 value
    不同），以及带 offset 的完整 xref_from 引用列表，用于追踪单个敏感字符串（密钥、
    URL、密文等）的全部使用位置。

    :param analysis_obj: Analysis 对象
    :param value: 字符串精确值（DEX 字符串池中的字面值）
    :param xref_limit: xref_from 引用返回上限（None=全部）
    :return: 字符串分析详情
    """
    try:
        sa_dict = analysis_obj.get_strings_analysis()
        sa = sa_dict.get(value)
        if sa is None:
            return {
                "value": value,
                "error": "String not found in DEX string pool",
            }
        result = {"value": value}
        try:
            result["is_overwritten"] = sa.is_overwritten()
        except Exception:
            result["is_overwritten"] = None
        try:
            result["orig_value"] = sa.get_orig_value()
        except Exception:
            pass
        # get_value() 是当前值（通常与 key 相同，但被覆写时可能不同）
        try:
            result["current_value"] = sa.get_value()
        except Exception:
            pass
        # xref_from with offset - 每处使用一条
        # get_xref_from(with_offset=True) 返回 list[(ClassAnalysis, MethodAnalysis)]
        # 注意：StringAnalysis 的 xref_from 带 offset 签名是
        # list[tuple[ClassAnalysis, MethodAnalysis]]（offset 在 add 时记录但 get 不一定返回）
        refs = []
        try:
            for ref_class, ref_method in sa.get_xref_from(with_offset=True):
                refs.append(
                    {
                        "class": ref_class.name,
                        "method": ref_method.name,
                        "descriptor": ref_method.descriptor,
                    }
                )
        except Exception:
            # 降级：不带 offset
            try:
                for ref_class, ref_method in sa.get_xref_from():
                    refs.append(
                        {
                            "class": ref_class.name,
                            "method": ref_method.name,
                            "descriptor": ref_method.descriptor,
                        }
                    )
            except Exception:
                pass
        total = len(refs)
        sliced = refs[:xref_limit] if xref_limit else refs
        result["xref_from"] = {
            "count": total,
            "returned": len(sliced),
            "refs": sliced,
        }
        return result
    except Exception as e:
        return {"value": value, "error": str(e)}


def analysis_security_hotspots(analysis_obj, limit: int = 50) -> dict:
    """
    APK 安全热点批量扫描（按危险调用模式扫描所有内部方法）。

    与 method-api-info（单方法 API 标注）和 android-api-usage（全量 Android API 列表）
    的区别：本命令按安全敏感的调用模式（反射/加密/动态加载/命令执行/网络/native 等）
    扫描所有内部方法的 xref_to，聚合每类热点的调用位置，一处输出便于快速定位需审计的代码。

    :param analysis_obj: Analysis 对象
    :param limit: 每类热点返回的调用位置上限（默认 50）
    :return: 安全热点聚合
    """
    import re

    # 危险调用模式（类名/方法签名正则）
    patterns = {
        "reflection": re.compile(
            r"Ljava/lang/reflect/|Ljava/lang/Class;->forName|"
            r"Ljava/lang/Class;->newInstance|Ljava/lang/reflect/Method;->invoke"
        ),
        "crypto": re.compile(
            r"Ljavax/crypto/|Ljava/security/|Landroid/util/Base64;|"
            r"Ljavax/crypto/Cipher;|Ljava/security/MessageDigest;"
        ),
        "dynamic_load": re.compile(
            r"Ldalvik/system/DexClassLoader|Ljava/net/URLClassLoader|"
            r"Ljava/lang/ClassLoader;->loadClass|Ldalvik/system/PathClassLoader"
        ),
        "command_exec": re.compile(
            r"Ljava/lang/Runtime;->exec|Ljava/lang/ProcessBuilder;|"
            r"Ljava/lang/Runtime;->getRuntime"
        ),
        "network": re.compile(
            r"Ljava/net/Socket;|Ljava/net/URL;|Ljava/net/HttpURLConnection|"
            r"Lorg/apache/http/|Lokhttp/|Ljava/net/InetAddress"
        ),
        "file_io": re.compile(
            r"Ljava/io/File;|Ljava/io/FileInputStream|Ljava/io/FileOutputStream|"
            r"Ljava/io/RandomAccessFile;|Ljava/io/FileWriter;|Ljava/io/FileReader;"
        ),
        "intent": re.compile(
            r"Landroid/content/Intent;->|startActivity|startService|"
            r"sendBroadcast|startActivityForResult"
        ),
        "telephony": re.compile(
            r"Landroid/telephony/SmsManager;|Landroid/telephony/TelephonyManager;|"
            r"Landroid/telephony/PhoneNumberUtils;"
        ),
        "content_provider": re.compile(
            r"Landroid/content/ContentResolver;->|getContentResolver|"
            r"Landroid/database/Cursor;"
        ),
    }

    try:
        hotspots = {k: [] for k in patterns}
        native_methods = []
        scanned = 0

        for ma in analysis_obj.get_methods():
            if ma.is_external():
                continue
            scanned += 1
            from_sig = f"{ma.class_name}->{ma.name}{ma.descriptor}"

            # native 方法检测
            try:
                em = ma.get_method()
                flags = em.get_access_flags_string()
                if flags and "native" in flags:
                    native_methods.append(
                        {
                            "class": ma.class_name,
                            "method": ma.name,
                            "descriptor": ma.descriptor,
                        }
                    )
            except Exception:
                pass

            # xref_to 扫描危险调用
            try:
                for ref_class, ref_method, off in ma.get_xref_to():
                    full = f"{ref_class.name}->{ref_method.name}{ref_method.descriptor}"
                    for cat, pat in patterns.items():
                        if pat.search(full):
                            hotspots[cat].append(
                                {
                                    "from": from_sig,
                                    "calls": full,
                                    "offset": off,
                                }
                            )
                            break  # 一个调用只归一类
            except Exception:
                pass

        # 截断 + 统计
        # hotspots/native_methods 来自 get_xref_to() 的 set 迭代（非确定）+
        # get_methods() 迭代，排序固定 samples/native_methods 顺序，让输出
        # 确定（agent 对接需确定性）。
        result_categories = {}
        for cat, items in hotspots.items():
            items.sort(key=lambda it: (it["from"], it["calls"], it["offset"]))
            result_categories[cat] = {
                "count": len(items),
                "samples": items[:limit] if limit else items,
            }
        native_methods.sort(
            key=lambda m: (m["class"], m["method"], m["descriptor"])
        )

        return {
            "scanned_methods": scanned,
            "native_methods_count": len(native_methods),
            "native_methods": (
                native_methods[:limit] if limit else native_methods
            ),
            "categories": result_categories,
        }
    except Exception as e:
        return {"error": str(e)}


def analysis_class_fields_xref(
    analysis_obj, class_name: str, xref_limit: int = 20
) -> dict:
    """
    获取类内所有字段的**完整读写交叉引用**（哪些方法读/写了每个字段）。

    与 class-fields（仅 xref 计数）和 field-xrefs-detail（单字段全 xref）的区别：
    本命令遍历类内所有字段并展开完整读写来源列表（class + method + descriptor），
    一次性给出类级字段数据流——哪些方法读取、哪些方法写入每个字段。用于追踪
    敏感字段（密钥/令牌/配置）的赋值点和消费点、状态字段的生命周期分析。

    :param analysis_obj: Analysis 对象
    :param class_name: 类名
    :param xref_limit: 每个字段的读写引用展开上限（默认 20）
    :return: 类内字段完整 xref
    """
    try:
        ca = analysis_obj.get_class_analysis(class_name)
        if ca is None:
            return {"class": class_name, "error": "Class not found"}

        def _xref_list(xref_iter):
            """将 FieldAnalysis xref [(ClassAnalysis, MethodAnalysis)] 序列化。"""
            out = []
            try:
                items = list(xref_iter)
            except Exception:
                return out
            for entry in items:
                try:
                    if isinstance(entry, tuple) and len(entry) >= 2:
                        ref_ca, ref_ma = entry[0], entry[1]
                        item = {}
                        try:
                            item["class"] = ref_ca.name
                        except Exception:
                            pass
                        try:
                            item["method"] = ref_ma.name
                        except Exception:
                            pass
                        try:
                            item["descriptor"] = ref_ma.descriptor
                        except Exception:
                            pass
                        try:
                            item["access_flags"] = (
                                ref_ma.get_access_flags_string()
                            )
                        except Exception:
                            pass
                        out.append(item)
                    else:
                        out.append(str(entry))
                except Exception:
                    continue
                if xref_limit and len(out) >= xref_limit:
                    break
            # get_xref_read/write 返回 set，迭代序非确定 → 切片前排序固定输出
            out.sort(
                key=lambda r: (
                    r.get("class", "") if isinstance(r, dict) else str(r),
                    r.get("method", "") if isinstance(r, dict) else "",
                    r.get("descriptor", "") if isinstance(r, dict) else "",
                )
            )
            return out

        fields_out = []
        for fa in ca.get_fields():
            item = {"name": fa.name}
            field_obj = fa.get_field() if hasattr(fa, "get_field") else None
            if field_obj is not None:
                try:
                    item["descriptor"] = field_obj.get_descriptor()
                except Exception:
                    pass
                try:
                    item["access_flags"] = field_obj.get_access_flags_string()
                except Exception:
                    pass
            try:
                reads = fa.get_xref_read()
                item["xref_read_count"] = len(reads)
                item["xref_read"] = _xref_list(reads)
            except Exception as e:
                item["xref_read_error"] = str(e)[:60]
            try:
                writes = fa.get_xref_write()
                item["xref_write_count"] = len(writes)
                item["xref_write"] = _xref_list(writes)
            except Exception as e:
                item["xref_write_error"] = str(e)[:60]
            fields_out.append(item)
        # get_fields() 可能返回 set，字段序非确定 → 排序固定输出
        fields_out.sort(
            key=lambda it: (it.get("name", ""), it.get("descriptor", ""))
        )
        return {
            "class": class_name,
            "is_external": ca.is_external(),
            "fields_total": len(fields_out),
            "xref_limit": xref_limit,
            "fields": fields_out,
        }
    except Exception as e:
        return {"class": class_name, "error": str(e)}


def analysis_hardcoded_secrets(
    analysis_obj, dex_list, limit: int = 100
) -> dict:
    """
    扫描所有类的静态值数组（EncodedArray），检测硬编码敏感字符串。

    与 dex regex-strings（全量字符串正则搜索）和 security-hotspots（方法级调用模式）
    的区别：本命令只扫 static final 字段的初始值（开发者主动硬编码的常量），按敏感
    模式分类（api_key/secret/token/url/private_key/jwt 等），跨所有类聚合。用于检测
    硬编码的 API 密钥、令牌、后端 URL、私钥等敏感凭证——这些是常见的安全漏洞。

    :param analysis_obj: Analysis 对象（未直接用，保留接口一致）
    :param dex_list: DEX 对象列表
    :param limit: 每类敏感项返回上限
    :return: 硬编码敏感项分类
    """
    try:
        import re

        from androguard.core.dex import EncodedArrayItem

        # 敏感模式：值或字段名匹配
        value_patterns = {
            "private_key": re.compile(
                r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"
            ),
            "jwt": re.compile(
                r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"
            ),
            "url": re.compile(r"https?://[^\s\"'<>]+"),
            "google_api_key": re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
            "aws_key": re.compile(r"AKIA[0-9A-Z]{16}"),
            "base64_long": re.compile(r"^[A-Za-z0-9+/]{40,}={0,2}$"),
        }
        # 字段名敏感模式
        name_patterns = {
            "api_key_field": re.compile(
                r"(?i)(api[_-]?key|secret|token|password|passwd|pwd|auth|credential)"
            ),
        }

        categories = {
            k: []
            for k in list(value_patterns.keys()) + list(name_patterns.keys())
        }
        scanned_classes = 0
        scanned_values = 0

        for dex_obj in dex_list:
            cm = dex_obj.get_class_manager()
            raw = getattr(dex_obj, "raw", None)
            if raw is None:
                continue
            for cls in dex_obj.get_classes():
                try:
                    off = cls.get_static_values_off()
                except Exception:
                    off = 0
                if not off:
                    continue
                scanned_classes += 1
                try:
                    raw.seek(off)
                    arr = EncodedArrayItem(raw, cm).get_value()
                    evs = arr.get_values()
                except Exception:
                    continue
                # 字段名
                names = []
                try:
                    cd = cls.get_class_data()
                    if cd is not None:
                        names = [f.get_name() for f in cd.get_static_fields()]
                except Exception:
                    pass
                cname = None
                try:
                    cname = cls.get_name()
                except Exception:
                    pass
                for i, ev in enumerate(evs):
                    scanned_values += 1
                    try:
                        v = ev.get_value()
                    except Exception:
                        v = None
                    if not isinstance(v, str) or not v:
                        continue
                    fname = names[i] if i < len(names) else ""
                    matched = False
                    # 值匹配
                    for cat, pat in value_patterns.items():
                        if pat.search(v):
                            categories[cat].append(
                                {
                                    "class": cname,
                                    "field": fname,
                                    "value": v[:200],
                                    "value_len": len(v),
                                }
                            )
                            matched = True
                            break
                    if matched:
                        continue
                    # 字段名匹配（值是字符串）
                    if fname:
                        for cat, pat in name_patterns.items():
                            if pat.search(fname):
                                categories[cat].append(
                                    {
                                        "class": cname,
                                        "field": fname,
                                        "value": v[:200],
                                        "value_len": len(v),
                                    }
                                )
                                break

        # 截断
        for cat in categories:
            if limit and len(categories[cat]) > limit:
                categories[cat] = categories[cat][:limit]

        return {
            "scanned_classes": scanned_classes,
            "scanned_static_values": scanned_values,
            "counts": {k: len(v) for k, v in categories.items()},
            "categories": categories,
        }
    except Exception as e:
        return {"error": str(e)}


# ================================================================
# 第二十九轮：方法可达性分析（调用链展开）
# ================================================================


def analysis_method_reachable(
    analysis_obj,
    class_name: str,
    method_name: str,
    descriptor: str = None,
    max_depth: int = 3,
    include_external: bool = False,
    max_nodes: int = 5000,
) -> dict:
    """
    方法可达性分析——从指定方法出发，递归展开 xref_to（被调用方）到
    max_depth 层，返回可达方法子图（含层级）。

    与 analysis call-graph（全量 networkx 调用图，无方向性溯源）的区别：
    本命令从单一方法出发做**有向可达性**——回答"这个方法能触达哪些方法"。
    用于：
      - 调用链追溯（某方法的影响范围 / 污点传播路径）
      - 危险 API 追踪（从敏感入口出发，看能否触达 sink）
      - 死代码检测的反向（入口可达性）

    默认只递归内部方法（is_external()==False），避免外部 API 调用链爆炸。
    可设 include_external=True 包含外部方法（但深度应小）。

    :param analysis_obj: Analysis 对象
    :param class_name: 起始方法类名
    :param method_name: 起始方法名
    :param descriptor: 方法描述符（可选，类内重载时需指定）
    :param max_depth: 递归深度上限（默认 3）
    :param include_external: 是否递归外部方法（默认 False）
    :param max_nodes: 节点数上限（防爆，默认 5000）
    :return: 可达方法子图
    """
    try:
        analysis_obj.create_xref()
    except Exception:
        pass

    # 定位起始方法
    try:
        if descriptor:
            ma = analysis_obj.get_method_analysis_by_name(
                class_name, method_name, descriptor
            )
        else:
            # 类内按名查（取第一个）
            ca = analysis_obj.get_class_analysis(class_name)
            if ca is None:
                return {"error": f"Class not found: {class_name}"}
            ma = None
            for m in ca.get_methods():
                if m.name == method_name:
                    ma = m
                    break
            if ma is None:
                return {
                    "error": f"Method not found: {class_name}->{method_name}"
                }
    except Exception as e:
        return {"error": str(e)}

    if ma is None:
        return {
            "error": f"Method not found: {class_name}->{method_name}({descriptor})"
        }

    def _key(m):
        return f"{m.get_class_name()}->{m.name}{m.descriptor}"

    def _node(m, depth):
        return {
            "class": m.get_class_name(),
            "method": m.name,
            "descriptor": m.descriptor,
            "full_name": m.full_name,
            "is_external": m.is_external(),
            "depth": depth,
        }

    visited = set()
    nodes = []
    edges = []
    queue = [(ma, 0)]
    start_key = _key(ma)
    visited.add(start_key)

    while queue:
        cur, depth = queue.pop(0)
        nodes.append(_node(cur, depth))
        if len(nodes) >= max_nodes:
            break
        if depth >= max_depth:
            continue
        try:
            xref_to = cur.get_xref_to()
        except Exception:
            continue
        # get_xref_to() 返回 set，迭代序非确定 → 入队顺序非确定 → BFS 遍历序
        # 非确定 → nodes/edges 列表顺序每次不同。按 key 排序固定遍历顺序。
        neighbors = sorted(
            xref_to, key=lambda t: f"{t[0].name}->{t[1].name}{t[1].descriptor}"
        )
        for _ca, nxt, _off in neighbors:
            k = _key(nxt)
            if k == start_key:
                edges.append({"from": _key(cur), "to": k, "depth": depth})
                continue
            edges.append({"from": _key(cur), "to": k, "depth": depth})
            if k in visited:
                continue
            # 递归条件：内部方法始终递归；外部方法按 include_external
            if nxt.is_external() and not include_external:
                continue
            visited.add(k)
            queue.append((nxt, depth + 1))

    # 统计
    internal_count = sum(1 for n in nodes if not n["is_external"])
    external_count = sum(1 for n in nodes if n["is_external"])
    max_depth_reached = max((n["depth"] for n in nodes), default=0)

    # BFS 节点序虽已按层排序入队，但同层多入口仍可能因上层 set 顺序残留差异；
    # 对 nodes/edges 做最终稳定排序，保证输出确定（agent 对接需确定性比对）。
    nodes.sort(
        key=lambda n: (n["depth"], n["class"], n["method"], n["descriptor"])
    )
    edges.sort(key=lambda e: (e["depth"], e["from"], e["to"]))

    return {
        "start": {
            "class": class_name,
            "method": method_name,
            "descriptor": descriptor,
            "full_name": ma.full_name,
        },
        "max_depth": max_depth,
        "include_external": include_external,
        "truncated": len(nodes) >= max_nodes,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "internal_count": internal_count,
        "external_count": external_count,
        "max_depth_reached": max_depth_reached,
        "nodes": nodes,
        "edges": edges,
    }


# ================================================================
# 第三十轮：按基本块反汇编（CFG 节点级指令视图）
# ================================================================


def analysis_method_block_instructions(
    analysis_obj,
    class_name: str,
    method_name: str,
    descriptor: str = None,
    ins_limit_per_block: int = None,
) -> dict:
    """
    按基本块反汇编方法指令——每个 BasicBlock 的完整指令流（CFG 节点级视图）。

    与 analysis method-basic-blocks（块元信息：名/范围/nb/last/childs，不含块内指令）
    和 analysis method-instructions（整方法指令流，无块边界）的区别：本命令按
    CFG 基本块组织指令，每块含其全部指令 + 后继/前继块名。用于：
      - 控制流敏感分析（按分支块定位指令，而非平铺指令流）
      - 反调试/混淆检测（异常处理块、死块、特殊跳转块的指令）
      - 路径分析（沿 childs 追踪某执行路径的指令）

    :param analysis_obj: Analysis 对象
    :param class_name: 类名
    :param method_name: 方法名
    :param descriptor: 方法描述符（可选）
    :param ins_limit_per_block: 每块返回指令上限（默认全部）
    :return: 按块组织的指令列表
    """
    ma = _resolve_method_analysis(
        analysis_obj, class_name, method_name, descriptor
    )
    if ma is None:
        return {
            "class": class_name,
            "method": method_name,
            "descriptor": descriptor,
            "error": "Method analysis not found",
        }

    try:
        bbs = list(ma.get_basic_blocks().get())
    except Exception as e:
        return {
            "class": class_name,
            "method": method_name,
            "descriptor": descriptor,
            "error": f"get_basic_blocks failed: {str(e)[:80]}",
        }

    def _ser_instruction(ins):
        item = {"name": ins.get_name(), "output": ins.get_output()}
        try:
            item["op_value"] = ins.get_op_value()
        except Exception:
            pass
        try:
            item["hex"] = ins.get_hex()
        except Exception:
            pass
        try:
            item["length"] = ins.get_length()
        except Exception:
            pass
        return item

    def _bb_name_list(relations):
        # relations: list of (start, end, DEXBasicBlock)
        names = []
        for r in relations:
            try:
                if isinstance(r, tuple) and len(r) >= 3:
                    bb = r[2]
                    names.append(
                        {
                            "start": r[0],
                            "end": r[1],
                            "name": (
                                bb.get_name()
                                if hasattr(bb, "get_name")
                                else str(bb)
                            ),
                        }
                    )
                else:
                    names.append(str(r))
            except Exception:
                names.append(str(r))
        return names

    blocks = []
    total_ins = 0
    for bb in bbs:
        try:
            ins_list = list(bb.get_instructions())
        except Exception:
            ins_list = []
        total_ins += len(ins_list)
        sliced = (
            ins_list[:ins_limit_per_block] if ins_limit_per_block else ins_list
        )
        block = {
            "name": bb.get_name(),
            "start": bb.get_start(),
            "end": bb.get_end(),
            "nb_instructions": bb.get_nb_instructions(),
            "instructions": [_ser_instruction(i) for i in sliced],
            "truncated": (
                ins_limit_per_block is not None
                and len(ins_list) > ins_limit_per_block
            ),
        }
        # 后继/前驱
        try:
            block["next"] = _bb_name_list(bb.get_next())
        except Exception:
            pass
        try:
            block["prev"] = _bb_name_list(bb.get_prev())
        except Exception:
            pass
        # 异常分析
        try:
            ea = bb.get_exception_analysis()
            if ea is not None:
                block["exception"] = str(ea)
        except Exception:
            pass
        blocks.append(block)

    return {
        "class": class_name,
        "method": method_name,
        "descriptor": descriptor,
        "full_name": ma.full_name,
        "block_count": len(blocks),
        "total_instructions": total_ins,
        "blocks": blocks,
    }


def analysis_method_switch_payloads(
    analysis_obj,
    class_name: str,
    method_name: str,
    descriptor: str = None,
) -> dict:
    """
    解析方法的 switch 分支表与 fill-array-data 数组 payload。

    packed-switch / sparse-switch 指令引用一个 payload 伪指令表（case 值 → 分支
    目标偏移），fill-array-data 指令引用一个数组初始化数据 payload。这些 payload
    在常规反汇编（method-instructions / method-block-instructions）中仅以原始
    hex 呈现，case→目标映射与数组内容不可读。本命令逐基本块提取并结构化解码：

      - packed-switch-payload / sparse-switch-payload → keys[] + targets[] 配对为
        cases: [{key, target}]（target 为相对 code unit 偏移，单位 16-bit 字）
      - fill-array-data-payload → 数组原始字节（hex）+ 长度

    用途：
      - 控制流完整性：还原 switch 的每个 case 值及其跳转目标（否则只见 switch 指令）
      - 逆向 switch 语义：case 键值常是状态码/opcode/消息类型，直接决定分支逻辑
      - 常量数组提取：fill-array-data 常用于硬编码密钥/查找表/字节数组初始化

    :param analysis_obj: Analysis 对象
    :param class_name: 类名
    :param method_name: 方法名
    :param descriptor: 方法描述符（可选，重载时指定）
    :return: switch/array payload 结构化解码结果
    """
    from androguard.core.dex import FillArrayData, PackedSwitch, SparseSwitch

    ma = _resolve_method_analysis(
        analysis_obj, class_name, method_name, descriptor
    )
    if ma is None:
        return {
            "class": class_name,
            "method": method_name,
            "descriptor": descriptor,
            "error": "Method analysis not found",
        }

    try:
        bbs = list(ma.get_basic_blocks().get())
    except Exception as e:
        return {
            "class": class_name,
            "method": method_name,
            "descriptor": descriptor,
            "error": f"get_basic_blocks failed: {str(e)[:80]}",
        }

    switches = []
    array_data = []
    branch_sites = []  # switch/fill 分支指令位置（引用 payload）

    for bb in bbs:
        try:
            ins_list = list(bb.get_instructions())
        except Exception:
            continue
        bb_name = bb.get_name()
        for ins in ins_list:
            name = ins.get_name()
            # 分支指令（引用 payload 的一侧）
            if name in ("packed-switch", "sparse-switch", "fill-array-data"):
                site = {"block": bb_name, "instruction": name}
                try:
                    site["output"] = ins.get_output()
                except Exception:
                    pass
                try:
                    site["op_value"] = ins.get_op_value()
                except Exception:
                    pass
                branch_sites.append(site)
                continue
            # payload 伪指令（解码表 / 数组）
            if isinstance(ins, (PackedSwitch, SparseSwitch)):
                try:
                    keys = list(ins.get_keys())
                except Exception:
                    keys = []
                try:
                    targets = list(ins.get_targets())
                except Exception:
                    targets = []
                cases = [
                    {"key": keys[i], "target": targets[i]}
                    for i in range(min(len(keys), len(targets)))
                ]
                entry = {
                    "block": bb_name,
                    "type": (
                        "packed-switch"
                        if isinstance(ins, PackedSwitch)
                        else "sparse-switch"
                    ),
                    "name": name,
                    "case_count": len(cases),
                    "cases": cases,
                }
                try:
                    entry["length"] = ins.get_length()
                except Exception:
                    pass
                switches.append(entry)
            elif isinstance(ins, FillArrayData):
                try:
                    data = ins.get_data()
                except Exception:
                    data = b""
                entry = {
                    "block": bb_name,
                    "name": name,
                    "data_length": len(data),
                    "data_hex": data.hex(),
                }
                try:
                    entry["length"] = ins.get_length()
                except Exception:
                    pass
                array_data.append(entry)

    return {
        "class": class_name,
        "method": method_name,
        "descriptor": descriptor,
        "full_name": ma.full_name,
        "switch_count": len(switches),
        "array_data_count": len(array_data),
        "branch_site_count": len(branch_sites),
        "switches": switches,
        "array_data": array_data,
        "branch_sites": branch_sites,
    }


def analysis_method_callers(
    analysis_obj,
    class_name: str,
    method_name: str,
    descriptor: str = None,
    max_depth: int = 3,
    include_external: bool = False,
    max_nodes: int = 5000,
) -> dict:
    """
    方法反向可达性（调用方溯源）——从指定方法出发，递归展开 xref_from
    （调用方）到 max_depth 层，返回能触达此方法的调用方子图（含层级）。

    与 analysis method-reachable（正向：此方法能触达谁）**方向相反**：本命令
    做反向溯源——回答"哪些方法/入口最终会调用到此方法"。用于：
      - 危险 sink 溯源：某敏感 API（如 exec/loadLibrary/Cipher）被哪些入口触达
      - 污点源定位：从 sink 反推到用户可控入口（导出组件生命周期方法）
      - 影响面评估：修改/hook 某方法会影响哪些上层调用方
      - 攻击路径构建：sink → ... → 导出入口 的完整反向链

    depth=0 是目标方法本身，depth=1 是直接调用者，depth=N 是 N 跳外的调用者。
    默认只递归内部方法（is_external()==False）；include_external 通常无意义
    （外部方法无实现体、无 xref_from 上溯），保留参数对称性。

    :param analysis_obj: Analysis 对象
    :param class_name: 目标方法类名
    :param method_name: 目标方法名
    :param descriptor: 方法描述符（可选，类内重载时需指定）
    :param max_depth: 反向递归深度上限（默认 3）
    :param include_external: 是否递归外部方法（默认 False）
    :param max_nodes: 节点数上限（防爆，默认 5000）
    :return: 调用方子图（反向可达）
    """
    try:
        analysis_obj.create_xref()
    except Exception:
        pass

    # 定位目标方法
    try:
        if descriptor:
            ma = analysis_obj.get_method_analysis_by_name(
                class_name, method_name, descriptor
            )
        else:
            ca = analysis_obj.get_class_analysis(class_name)
            if ca is None:
                return {"error": f"Class not found: {class_name}"}
            ma = None
            for m in ca.get_methods():
                if m.name == method_name:
                    ma = m
                    break
            if ma is None:
                return {
                    "error": f"Method not found: {class_name}->{method_name}"
                }
    except Exception as e:
        return {"error": str(e)}

    if ma is None:
        return {
            "error": f"Method not found: {class_name}->{method_name}({descriptor})"
        }

    def _key(m):
        return f"{m.get_class_name()}->{m.name}{m.descriptor}"

    def _node(m, depth):
        return {
            "class": m.get_class_name(),
            "method": m.name,
            "descriptor": m.descriptor,
            "full_name": m.full_name,
            "is_external": m.is_external(),
            "depth": depth,
        }

    visited = set()
    nodes = []
    edges = []
    entry_points = []  # 链源头：被完整展开却无内部调用方的节点
    truncated_frontier = (
        []
    )  # 因 max_depth 未继续上溯的边界节点（可能还有更上层调用方）
    queue = [(ma, 0)]
    start_key = _key(ma)
    visited.add(start_key)

    while queue:
        cur, depth = queue.pop(0)
        cur_node = _node(cur, depth)
        nodes.append(cur_node)
        if len(nodes) >= max_nodes:
            break
        if depth >= max_depth:
            # 到达深度上限，未展开其调用方 → 记为截断边界（非目标本身）
            if depth > 0:
                truncated_frontier.append(cur_node)
            continue
        try:
            xref_from = cur.get_xref_from()
        except Exception:
            xref_from = []
        # 统计本节点的内部调用方数量（判定是否为链源头）
        internal_callers = 0
        for _ca, caller, _off in xref_from:
            k = _key(caller)
            # 边方向：caller → cur（真实调用方向）
            edges.append({"from": k, "to": _key(cur), "depth": depth})
            if not caller.is_external():
                internal_callers += 1
            if k == start_key or k in visited:
                continue
            if caller.is_external() and not include_external:
                continue
            visited.add(k)
            queue.append((caller, depth + 1))
        # 被完整展开（depth<max_depth）但无内部调用方 → 反向调用链的真正源头
        # （典型：框架回调的生命周期方法、Thread.run、静态初始化等入口）
        if depth > 0 and internal_callers == 0:
            entry_points.append(cur_node)

    internal_count = sum(1 for n in nodes if not n["is_external"])
    external_count = sum(1 for n in nodes if n["is_external"])
    max_depth_reached = max((n["depth"] for n in nodes), default=0)

    return {
        "target": {
            "class": class_name,
            "method": method_name,
            "descriptor": descriptor,
            "full_name": ma.full_name,
        },
        "max_depth": max_depth,
        "include_external": include_external,
        "truncated": len(nodes) >= max_nodes,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "internal_count": internal_count,
        "external_count": external_count,
        "max_depth_reached": max_depth_reached,
        "entry_point_count": len(entry_points),
        "entry_points": entry_points,
        "frontier_count": len(truncated_frontier),
        "frontier": truncated_frontier,
        "nodes": nodes,
        "edges": edges,
    }


def apk_attack_surface(
    apk_obj,
    analysis_obj,
    max_depth: int = 4,
    per_sink_limit: int = 10,
    max_nodes_per_component: int = 2000,
    include_safe: bool = False,
) -> dict:
    """
    攻击面聚合分析——交叉引用 **导出组件** 与其处理类 **前向可达的危险 sink**。

    这是一个跨对象的聚合分析：把 manifest 层的暴露面（导出且无权限保护的
    Activity/Service/Receiver/Provider）与字节码层的危险能力（反射/命令执行/
    动态加载/加密/网络/文件/native 等 sink）连接起来，回答安全审计的核心问题：
    **"外部可直接触发的入口，能到达哪些危险操作？"**

    对每个导出组件：
      1. 定位其处理类（dotted name → Dalvik 描述符）
      2. 从该类所有方法出发，前向 BFS（xref_to）到 max_depth 层
      3. 沿途收集匹配危险 sink 模式的外部调用，按类别聚合
      4. 标记该组件的可达 sink 类别（reachable_sink_categories）

    与 security-hotspots（全局 sink 扫描，不区分入口）、component-details
    （仅 manifest 属性）、method-reachable（单方法正向可达）的区别：本命令
    **只从外部可达的入口出发**做可达性，直接产出"入口→危险能力"的攻击面地图，
    是组件劫持 / 越权 / 污点分析的起点。

    :param apk_obj: androguard APK 对象（取导出组件）
    :param analysis_obj: Analysis 对象（做前向可达）
    :param max_depth: 从组件类方法前向递归深度（默认 4）
    :param per_sink_limit: 每个组件每类 sink 的调用样本上限（默认 10）
    :param max_nodes_per_component: 单组件 BFS 节点上限（防爆，默认 2000）
    :param include_safe: 是否也分析非导出/受保护组件（默认 False，只看暴露面）
    :return: 攻击面聚合报告
    """
    import re

    try:
        analysis_obj.create_xref()
    except Exception:
        pass

    # sink 模式（与 security-hotspots 一致，便于交叉对照）
    sink_patterns = {
        "reflection": re.compile(
            r"Ljava/lang/reflect/|Ljava/lang/Class;->forName|"
            r"Ljava/lang/Class;->newInstance|Ljava/lang/reflect/Method;->invoke"
        ),
        "command_exec": re.compile(
            r"Ljava/lang/Runtime;->exec|Ljava/lang/ProcessBuilder;|"
            r"Ljava/lang/Runtime;->getRuntime"
        ),
        "dynamic_load": re.compile(
            r"Ldalvik/system/DexClassLoader|Ljava/net/URLClassLoader|"
            r"Ljava/lang/ClassLoader;->loadClass|Ldalvik/system/PathClassLoader|"
            r"Ljava/lang/System;->load|Ljava/lang/Runtime;->load"
        ),
        "crypto": re.compile(
            r"Ljavax/crypto/|Ljava/security/|Ljavax/crypto/Cipher;|"
            r"Ljava/security/MessageDigest;"
        ),
        "network": re.compile(
            r"Ljava/net/Socket;|Ljava/net/URL;|Ljava/net/HttpURLConnection|"
            r"Lorg/apache/http/|Ljava/net/InetAddress|Ljavax/net/ssl/"
        ),
        "file_io": re.compile(
            r"Ljava/io/File;|Ljava/io/FileInputStream|Ljava/io/FileOutputStream|"
            r"Ljava/io/RandomAccessFile;|Ljava/io/FileWriter;|Ljava/io/FileReader;"
        ),
        "webview": re.compile(
            r"Landroid/webkit/WebView;->loadUrl|Landroid/webkit/WebView;->addJavascriptInterface|"
            r"Landroid/webkit/WebSettings;->setJavaScriptEnabled|Landroid/webkit/WebView;->evaluateJavascript"
        ),
        "sql": re.compile(
            r"Landroid/database/sqlite/SQLiteDatabase;->rawQuery|"
            r"Landroid/database/sqlite/SQLiteDatabase;->execSQL|"
            r"Landroid/database/sqlite/SQLiteDatabase;->query"
        ),
        "intent_redirect": re.compile(
            r"getIntent|getParcelableExtra|getStringExtra|getSerializableExtra|"
            r"getData\b|startActivity|startService|sendBroadcast"
        ),
        "content_provider": re.compile(
            r"Landroid/content/ContentResolver;->|getContentResolver|"
            r"Landroid/database/Cursor;"
        ),
    }

    package = None
    try:
        package = apk_obj.get_package()
    except Exception:
        pass

    def _to_descriptor(name):
        """dotted 组件名 → Dalvik 描述符 Lx/y/Z;"""
        if not name:
            return None
        n = name
        if n.startswith("."):
            n = (package or "") + n
        elif "." not in n and package:
            # 单段类名，相对于包
            n = package + "." + n
        n = n.replace(".", "/")
        return "L" + n + ";"

    def _has_intent_filter(tag, name):
        try:
            return bool(apk_obj.get_intent_filters(tag, name))
        except Exception:
            return False

    def _attr(tag, attr, name):
        try:
            return apk_obj.get_attribute_value(tag, attr, name=name)
        except Exception:
            return None

    def _infer_exported(tag, name):
        explicit = _attr(tag, "exported", name)
        if explicit is not None:
            return str(explicit).lower() == "true", explicit
        return _has_intent_filter(tag, name), None

    def _scan_component(tag, name):
        """对单个组件类做前向可达 sink 扫描。"""
        desc = _to_descriptor(name)
        ca = None
        try:
            ca = analysis_obj.get_class_analysis(desc)
        except Exception:
            ca = None
        if ca is None:
            return {
                "class_descriptor": desc,
                "class_resolved": False,
                "note": "handler class not found in DEX (framework/absent/obfuscated)",
                "reachable_sink_categories": [],
                "sinks": {},
            }

        # 前向 BFS：从组件类所有内部方法出发
        visited = set()
        queue = []
        for m in ca.get_methods():
            try:
                if m.is_external():
                    continue
            except Exception:
                pass
            k = f"{m.get_class_name()}->{m.name}{m.descriptor}"
            if k not in visited:
                visited.add(k)
                queue.append((m, 0))

        sinks = {c: [] for c in sink_patterns}
        sink_counts = {c: 0 for c in sink_patterns}
        node_budget = max_nodes_per_component
        while queue and node_budget > 0:
            cur, depth = queue.pop(0)
            node_budget -= 1
            from_sig = f"{cur.get_class_name()}->{cur.name}{cur.descriptor}"
            try:
                xrefs = cur.get_xref_to()
            except Exception:
                xrefs = []
            for ref_class, ref_method, off in xrefs:
                try:
                    full = f"{ref_class.name}->{ref_method.name}{ref_method.descriptor}"
                except Exception:
                    continue
                # sink 匹配（外部调用为主，但也扫内部命中）
                for cat, pat in sink_patterns.items():
                    if pat.search(full):
                        sink_counts[cat] += 1
                        if len(sinks[cat]) < per_sink_limit:
                            sinks[cat].append(
                                {
                                    "from": from_sig,
                                    "calls": full,
                                    "offset": off,
                                    "depth": depth,
                                }
                            )
                        break
                # 继续展开内部被调方
                if depth < max_depth:
                    try:
                        if ref_method.is_external():
                            continue
                    except Exception:
                        continue
                    rk = f"{ref_method.get_class_name()}->{ref_method.name}{ref_method.descriptor}"
                    if rk not in visited:
                        visited.add(rk)
                        queue.append((ref_method, depth + 1))

        reachable = [c for c in sink_patterns if sink_counts[c] > 0]
        out_sinks = {
            c: {"count": sink_counts[c], "samples": sinks[c]}
            for c in reachable
        }
        return {
            "class_descriptor": desc,
            "class_resolved": True,
            "methods_explored": len(visited),
            "budget_exhausted": node_budget <= 0,
            "reachable_sink_categories": reachable,
            "sink_category_count": len(reachable),
            "sinks": out_sinks,
        }

    tag_getters = [
        ("activity", "activities", lambda: apk_obj.get_activities()),
        (
            "activity-alias",
            "activity_aliases",
            lambda: apk_obj.get_activity_aliases(),
        ),
        ("service", "services", lambda: apk_obj.get_services()),
        ("receiver", "receivers", lambda: apk_obj.get_receivers()),
        ("provider", "providers", lambda: apk_obj.get_providers()),
    ]

    components = []
    exposed_count = 0
    analyzed_count = 0
    for tag, _label, getter in tag_getters:
        try:
            names = list(getter())
        except Exception:
            names = []
        for name in names:
            exported_eff, exported_explicit = _infer_exported(tag, name)
            permission = _attr(tag, "permission", name)
            # provider 读写权限也算保护
            protected = bool(permission)
            if tag == "provider":
                rp = _attr("provider", "readPermission", name)
                wp = _attr("provider", "writePermission", name)
                protected = protected or bool(rp) or bool(wp)
            is_exposed = exported_eff and not protected
            if is_exposed:
                exposed_count += 1
            if not is_exposed and not include_safe:
                continue
            analyzed_count += 1
            entry = {
                "type": tag,
                "name": name,
                "exported": exported_eff,
                "exported_explicit": exported_explicit,
                "permission": permission,
                "exposed": is_exposed,
            }
            entry.update(_scan_component(tag, name))
            components.append(entry)

    # 全局聚合：哪些 sink 类别在攻击面上出现
    surface_categories = {}
    for c in components:
        for cat in c.get("reachable_sink_categories", []):
            surface_categories.setdefault(cat, 0)
            surface_categories[cat] += 1

    # 高危组件：暴露 + 可达 command_exec/dynamic_load/reflection/webview 任一
    critical_cats = {
        "command_exec",
        "dynamic_load",
        "reflection",
        "webview",
        "sql",
    }
    critical = [
        {
            "type": c["type"],
            "name": c["name"],
            "critical_sinks": [
                x
                for x in c.get("reachable_sink_categories", [])
                if x in critical_cats
            ],
        }
        for c in components
        if c.get("exposed")
        and any(
            x in critical_cats for x in c.get("reachable_sink_categories", [])
        )
    ]

    return {
        "package": package,
        "max_depth": max_depth,
        "include_safe": include_safe,
        "exposed_component_count": exposed_count,
        "analyzed_component_count": analyzed_count,
        "surface_sink_categories": surface_categories,
        "critical_component_count": len(critical),
        "critical_components": critical,
        "components": components,
    }


# ================================================================
# 第三十二轮：分析型/聚合型能力批量封装
# ================================================================


def _iter_method_invoke_args(ma):
    """
    遍历方法指令，产出 (invoke_target_full, [解析出的字符串参数], approx_offset)。

    通过跟踪 `const-string` 写入的寄存器，把随后调用点用到的寄存器解析回字符串
    常量——用于还原 Cipher.getInstance("AES/ECB/...")、Class.forName("com.x.Y")
    等调用的实参。启发式：寄存器→字符串映射跨基本块保留（不做精确数据流），
    对"const-string 紧邻 invoke"的常见模式（如加密/反射）足够可靠。

    :param ma: MethodAnalysis
    :yield: (target_descriptor, string_args, block_start_offset)
    """
    reg_str = {}
    try:
        blocks = list(ma.get_basic_blocks().get())
    except Exception:
        return
    for bb in blocks:
        try:
            start = bb.get_start()
        except Exception:
            start = 0
        try:
            instructions = list(bb.get_instructions())
        except Exception:
            continue
        for ins in instructions:
            try:
                name = ins.get_name()
                out = ins.get_output() or ""
            except Exception:
                continue
            if name.startswith("const-string"):
                parts = out.split(",", 1)
                if len(parts) == 2:
                    reg = parts[0].strip()
                    val = parts[1].strip()
                    if len(val) >= 2 and val[0] == '"' and val[-1] == '"':
                        val = val[1:-1]
                    reg_str[reg] = val
            elif name.startswith("invoke"):
                segs = [p.strip() for p in out.split(",")]
                if not segs:
                    continue
                target = segs[-1]
                regs = segs[:-1]
                args = [reg_str[r] for r in regs if r in reg_str]
                yield target, args, start


def analysis_native_methods(analysis_obj, limit: int = 200) -> dict:
    """
    枚举所有 native 方法（JNI 边界）——声明类 + 方法签名 + 调用方。

    与 security-hotspots（native 只是其中一类，藏在聚合结果里）的区别：本命令
    **专门**枚举 JNI 边界，独立列出每个 native 方法及其内部调用方，用于快速定位
    需要配合 .so 逆向的原生代码入口、评估哪些 Java 逻辑下沉到了 native 层。

    :param analysis_obj: Analysis 对象
    :param limit: 返回的 native 方法上限（默认 200）
    :return: native 方法枚举
    """
    try:
        analysis_obj.create_xref()
    except Exception:
        pass

    natives = []
    scanned = 0
    for ma in analysis_obj.get_methods():
        try:
            if ma.is_external():
                continue
        except Exception:
            continue
        scanned += 1
        try:
            em = ma.get_method()
            flags = em.get_access_flags_string()
        except Exception:
            flags = None
        if not flags or "native" not in flags:
            continue
        callers = []
        try:
            for _ca, caller, _off in ma.get_xref_from():
                callers.append(
                    {
                        "class": caller.get_class_name(),
                        "method": caller.name,
                        "descriptor": caller.descriptor,
                    }
                )
        except Exception:
            pass
        natives.append(
            {
                "class": ma.class_name,
                "method": ma.name,
                "descriptor": ma.descriptor,
                "access_flags": flags,
                "caller_count": len(callers),
                "callers": callers[:20],
            }
        )

    # 按声明类聚合
    by_class = {}
    for n in natives:
        by_class.setdefault(n["class"], 0)
        by_class[n["class"]] += 1

    return {
        "scanned_methods": scanned,
        "native_method_count": len(natives),
        "class_count": len(by_class),
        "by_class": by_class,
        "native_methods": natives[:limit],
        "truncated": len(natives) > limit,
    }


def analysis_crypto_usage(analysis_obj, per_type_limit: int = 100) -> dict:
    """
    加密 API 用法聚合 + **算法串还原** + 弱加密标记。

    与 security-hotspots 的 crypto 类别（仅列出调用点，不解析算法）的区别：本命令
    用指令级 const-string 提取还原 `Cipher.getInstance("AES/ECB/PKCS5Padding")` 等
    调用的**实际算法/模式/填充**字符串，并按已知弱点标记（ECB 模式、DES/DESede
    以外的弱算法、MD5/SHA-1 摘要、RC4、RSA NoPadding、ECB），直接产出可审计的
    加密配置清单——这是 Android 加密误用审计（MSTG-CRYPTO）的核心。

    :param analysis_obj: Analysis 对象
    :param per_type_limit: 每类返回上限
    :return: 加密用法聚合
    """
    import re as _re

    # 关注的加密工厂/构造方法（target 子串 → 类别）
    crypto_targets = {
        "Ljavax/crypto/Cipher;->getInstance": "cipher",
        "Ljava/security/MessageDigest;->getInstance": "digest",
        "Ljavax/crypto/Mac;->getInstance": "mac",
        "Ljavax/crypto/KeyGenerator;->getInstance": "keygen",
        "Ljava/security/KeyPairGenerator;->getInstance": "keypairgen",
        "Ljavax/crypto/SecretKeyFactory;->getInstance": "secretkeyfactory",
        "Ljava/security/Signature;->getInstance": "signature",
    }
    # 硬编码密钥/IV 指示器（构造即可能硬编码）
    material_targets = {
        "Ljavax/crypto/spec/SecretKeySpec;-><init>": "secret_key_spec",
        "Ljavax/crypto/spec/IvParameterSpec;-><init>": "iv_param_spec",
        "Ljavax/crypto/spec/PBEKeySpec;-><init>": "pbe_key_spec",
    }
    weak_algo = _re.compile(
        r"(^|[/_-])(DES|RC4|RC2|MD5|MD2|SHA-?1|ECB|NoPadding|Blowfish)([/_-]|$)",
        _re.IGNORECASE,
    )

    usages = {k: [] for k in set(crypto_targets.values())}
    material = {k: [] for k in set(material_targets.values())}
    weak_findings = []
    algorithms = {}  # 算法串 → 出现次数

    for ma in analysis_obj.get_methods():
        try:
            if ma.is_external():
                continue
        except Exception:
            continue
        from_sig = f"{ma.class_name}->{ma.name}{ma.descriptor}"
        try:
            for target, args, off in _iter_method_invoke_args(ma):
                for sub, cat in crypto_targets.items():
                    if sub in target:
                        algo = args[0] if args else None
                        entry = {
                            "from": from_sig,
                            "target": target,
                            "algorithm": algo,
                            "offset": off,
                        }
                        usages[cat].append(entry)
                        if algo:
                            algorithms[algo] = algorithms.get(algo, 0) + 1
                            if weak_algo.search(algo):
                                weak_findings.append(
                                    {
                                        "from": from_sig,
                                        "algorithm": algo,
                                        "category": cat,
                                        "reason": "weak_or_ecb",
                                    }
                                )
                        break
                for sub, cat in material_targets.items():
                    if sub in target:
                        material[cat].append(
                            {"from": from_sig, "target": target, "offset": off}
                        )
                        break
        except Exception:
            continue

    usage_summary = {
        k: {
            "count": len(v),
            "samples": sorted(
                v[:per_type_limit],
                key=lambda e: (
                    e["from"],
                    e.get("target", ""),
                    e.get("offset", 0),
                ),
            ),
        }
        for k, v in usages.items()
        if v
    }
    material_summary = {
        k: {
            "count": len(v),
            "samples": sorted(
                v[:per_type_limit],
                key=lambda e: (
                    e["from"],
                    e.get("target", ""),
                    e.get("offset", 0),
                ),
            ),
        }
        for k, v in material.items()
        if v
    }
    # usages/material 来自 get_methods() set 迭代，切片前先排好（上面 samples 已 sort）；
    # weak_findings 同源 set 迭代，切片前排序
    weak_findings.sort(
        key=lambda f: (
            f["from"],
            f.get("algorithm", ""),
            f.get("category", ""),
        )
    )
    # usage_summary/material_summary 是 dict（key 来自 set），按 key 重建固定 JSON 顺序
    usage_summary = {k: usage_summary[k] for k in sorted(usage_summary.keys())}
    material_summary = {
        k: material_summary[k] for k in sorted(material_summary.keys())
    }

    return {
        "algorithms": dict(sorted(algorithms.items(), key=lambda x: -x[1])),
        "weak_finding_count": len(weak_findings),
        "weak_findings": weak_findings[:per_type_limit],
        "usages": usage_summary,
        "key_material": material_summary,
    }


def analysis_reflection_targets(
    analysis_obj, per_type_limit: int = 100
) -> dict:
    """
    反射调用点 + **反射目标字符串还原**（反混淆）。

    与 security-hotspots 的 reflection 类别（仅列出调用点）的区别：本命令用指令级
    const-string 提取还原 `Class.forName("com.x.Hidden")`、`getMethod("doSecret")`
    等反射调用的**实际目标类名/方法名字符串**，直接暴露被反射隐藏的类/方法——
    对抗"用反射规避静态 xref"的常见混淆/反检测手法。

    :param analysis_obj: Analysis 对象
    :param per_type_limit: 每类返回上限
    :return: 反射目标聚合
    """
    reflect_targets = {
        "Ljava/lang/Class;->forName": "class_forname",
        "Ljava/lang/Class;->getMethod": "get_method",
        "Ljava/lang/Class;->getDeclaredMethod": "get_declared_method",
        "Ljava/lang/Class;->getField": "get_field",
        "Ljava/lang/Class;->getDeclaredField": "get_declared_field",
        "Ljava/lang/Class;->newInstance": "new_instance",
        "Ljava/lang/reflect/Method;->invoke": "method_invoke",
        "Ljava/lang/ClassLoader;->loadClass": "loadclass",
        "Ljava/lang/System;->getProperty": "get_property",
    }

    hits = {k: [] for k in set(reflect_targets.values())}
    resolved_names = {}  # 还原出的目标名 → 次数

    for ma in analysis_obj.get_methods():
        try:
            if ma.is_external():
                continue
        except Exception:
            continue
        from_sig = f"{ma.class_name}->{ma.name}{ma.descriptor}"
        try:
            for target, args, off in _iter_method_invoke_args(ma):
                for sub, cat in reflect_targets.items():
                    if sub in target:
                        resolved = args[0] if args else None
                        hits[cat].append(
                            {
                                "from": from_sig,
                                "target": target,
                                "resolved": resolved,
                                "offset": off,
                            }
                        )
                        if resolved:
                            resolved_names[resolved] = (
                                resolved_names.get(resolved, 0) + 1
                            )
                        break
        except Exception:
            continue

    total = sum(len(v) for v in hits.values())
    categories = {
        k: {
            "count": len(v),
            "samples": sorted(
                v[:per_type_limit],
                key=lambda e: (
                    e["from"],
                    e.get("target", ""),
                    e.get("offset", 0),
                ),
            ),
        }
        for k, v in hits.items()
        if v
    }
    # hits 来自 get_methods() set 迭代，categories 是 dict（key 来自 set）→ 按 key 重建
    categories = {k: categories[k] for k in sorted(categories.keys())}

    return {
        "total_reflection_calls": total,
        "resolved_target_names": dict(
            sorted(resolved_names.items(), key=lambda x: -x[1])
        ),
        "categories": categories,
    }


def analysis_url_endpoints(analysis_obj, per_type_limit: int = 200) -> dict:
    """
    网络端点提取——从字符串常量池扫描 URL / 主机 / IP + 引用方法。

    与 dex regex-strings（需手工给正则，无分类无引用聚合）、hardcoded-secrets
    （只扫 static 字段初值中的 url）的区别：本命令扫描**全部**字符串分析对象，
    按 http/https/ws/ip/host 分类，并附上引用每个端点的方法（`get_xref_from`），
    直接产出网络攻击面地图——C2 / 数据外传端点 / 后端 API 一览。

    :param analysis_obj: Analysis 对象
    :param per_type_limit: 每类返回上限
    :return: 网络端点聚合
    """
    import re as _re

    patterns = {
        "https_url": _re.compile(r"https://[^\s\"'<>]+"),
        "http_url": _re.compile(r"http://[^\s\"'<>]+"),
        "ws_url": _re.compile(r"wss?://[^\s\"'<>]+"),
        "ftp_url": _re.compile(r"ftps?://[^\s\"'<>]+"),
        "ip_addr": _re.compile(
            r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"
        ),
    }

    buckets = {k: [] for k in patterns}
    hosts = {}  # host → 次数

    def _host_of(url):
        m = _re.match(r"[a-z]+://([^/:\s]+)", url, _re.IGNORECASE)
        return m.group(1) if m else None

    for sa in analysis_obj.get_strings():
        try:
            value = sa.get_value()
        except Exception:
            continue
        if not value:
            continue
        for cat, pat in patterns.items():
            m = pat.search(value)
            if not m:
                continue
            matched = m.group(0)
            # 引用方法
            origins = []
            try:
                for ref in sa.get_xref_from():
                    # 兼容 2 元组 (ClassAnalysis, MethodAnalysis) 与 3 元组含 offset
                    rc = ref[0]
                    rm = ref[1]
                    origins.append({"class": rc.name, "method": rm.name})
            except Exception:
                pass
            # get_xref_from() 返回 set，迭代序非确定 → 排序固定 used_in 顺序
            origins.sort(key=lambda o: (o["class"], o["method"]))
            entry = {
                "value": matched,
                "full_string": value if value != matched else None,
                "used_in": origins[:10],
                "used_in_count": len(origins),
            }
            buckets[cat].append(entry)
            h = _host_of(matched)
            if h:
                hosts[h] = hosts.get(h, 0) + 1
            break  # 一个字符串只归首个命中类别

    # buckets[cat] 来自 get_strings_analysis() 迭代（可能 set 驱动），切片前排序；
    # summary 是 dict（key 来自 patterns 但 if v 过滤后顺序依赖 buckets），按 key 重建
    for cat in buckets:
        buckets[cat].sort(
            key=lambda e: (
                e.get("value", ""),
                e.get("full_string") or "",
                e.get("used_in_count", 0),
            )
        )
    summary = {
        k: {"count": len(v), "samples": v[:per_type_limit]}
        for k, v in buckets.items()
        if v
    }
    summary = {k: summary[k] for k in sorted(summary.keys())}
    total = sum(len(v) for v in buckets.values())

    return {
        "total_endpoints": total,
        "unique_hosts": dict(sorted(hosts.items(), key=lambda x: -x[1])),
        "categories": summary,
    }


def analysis_taint_path(
    analysis_obj,
    src_class: str,
    src_method: str,
    dst_class: str,
    dst_method: str,
    src_descriptor: str = None,
    dst_descriptor: str = None,
    max_depth: int = 8,
    max_nodes: int = 20000,
) -> dict:
    """
    源→汇调用路径搜索——在调用图上找从源方法到汇方法的一条最短前向调用路径。

    与 method-reachable（只判断可达性，输出整个可达子图）、method-callers（反向
    子图）的区别：本命令给定 **两个具体方法**，用前向 BFS + 父指针重建，返回一条
    从 source 到 sink 的**具体调用链**（若存在）——直接回答"用户可控入口是否、
    经由哪条路径到达危险 sink"，是污点分析 / 攻击路径确认的收尾命令。

    :param analysis_obj: Analysis 对象
    :param src_class/src_method: 源方法
    :param dst_class/dst_method: 汇方法
    :param src_descriptor/dst_descriptor: 可选描述符
    :param max_depth: 搜索深度上限（默认 8）
    :param max_nodes: 访问节点上限（默认 20000）
    :return: 调用路径（存在则含 path 列表）
    """
    try:
        analysis_obj.create_xref()
    except Exception:
        pass

    def _locate(cn, mn, desc):
        try:
            if desc:
                return analysis_obj.get_method_analysis_by_name(cn, mn, desc)
            ca = analysis_obj.get_class_analysis(cn)
            if ca is None:
                return None
            for m in ca.get_methods():
                if m.name == mn:
                    return m
        except Exception:
            return None
        return None

    src = _locate(src_class, src_method, src_descriptor)
    if src is None:
        return {"error": f"Source method not found: {src_class}->{src_method}"}
    dst = _locate(dst_class, dst_method, dst_descriptor)
    if dst is None:
        return {"error": f"Sink method not found: {dst_class}->{dst_method}"}

    def _key(m):
        return f"{m.get_class_name()}->{m.name}{m.descriptor}"

    dst_key = _key(dst)
    src_key = _key(src)

    # 前向 BFS，parent 记录到达每个节点的上一跳
    from collections import deque

    parent = {src_key: None}
    node_obj = {src_key: src}
    depth = {src_key: 0}
    q = deque([src])
    visited_count = 0
    found = False

    while q:
        cur = q.popleft()
        ck = _key(cur)
        visited_count += 1
        if visited_count > max_nodes:
            break
        if ck == dst_key:
            found = True
            break
        if depth[ck] >= max_depth:
            continue
        try:
            xrefs = cur.get_xref_to()
        except Exception:
            xrefs = []
        for _ca, callee, off in xrefs:
            nk = _key(callee)
            if nk in parent:
                continue
            parent[nk] = (ck, off)
            node_obj[nk] = callee
            depth[nk] = depth[ck] + 1
            q.append(callee)
            if nk == dst_key:
                found = True
                q.clear()
                break

    if not found or dst_key not in parent:
        return {
            "source": {"class": src_class, "method": src_method},
            "sink": {"class": dst_class, "method": dst_method},
            "found": False,
            "visited_nodes": visited_count,
            "note": "no forward call path within max_depth/max_nodes",
        }

    # 从 dst 回溯到 src 重建路径
    path = []
    k = dst_key
    while k is not None:
        m = node_obj[k]
        step = {
            "class": m.get_class_name(),
            "method": m.name,
            "descriptor": m.descriptor,
        }
        p = parent[k]
        if p is not None:
            k, off = p
            step["call_offset_from_prev"] = off
        else:
            k = None
        path.append(step)
    path.reverse()

    return {
        "source": {
            "class": src_class,
            "method": src_method,
            "descriptor": src_descriptor,
        },
        "sink": {
            "class": dst_class,
            "method": dst_method,
            "descriptor": dst_descriptor,
        },
        "found": True,
        "path_length": len(path),
        "visited_nodes": visited_count,
        "path": path,
    }


def analysis_webview_security(analysis_obj, per_type_limit: int = 100) -> dict:
    """
    WebView 安全配置审计——扫描所有内部方法对 WebView/WebSettings 危险 API 的调用，
    定位可导致 RCE / 文件泄露 / XSS / 中间人的配置。

    与 security-hotspots（通用危险调用聚合，不区分 WebView 语义）、attack-surface
    （组件→sink，不解析具体配置项）的区别：本命令专注 WebView 攻击面，把每个配置
    调用按其安全含义（js_bridge/js_enabled/file_access/mixed_content/debug/load）
    分类，并对高危项（addJavascriptInterface、setAllowUniversalAccessFromFileURLs、
    setWebContentsDebuggingEnabled）打 findings 标记，是 WebView 漏洞审计的一站式入口。

    :param analysis_obj: Analysis 对象
    :param per_type_limit: 每类返回样本上限（默认 100）
    :return: WebView 配置调用聚合 + 高危 findings
    """
    import re

    # WebView 危险配置：类别 -> (方法名正则, 是否默认高危, 安全含义)
    checks = {
        "js_bridge": (
            re.compile(r"->addJavascriptInterface\("),
            True,
            "JS↔Java 桥（targetSdk<17 可 RCE，>=17 仍可调 @JavascriptInterface 方法）",
        ),
        "js_enabled": (
            re.compile(r"->setJavaScriptEnabled\("),
            False,
            "启用 JavaScript（配合不可信内容→XSS）",
        ),
        "file_access": (
            re.compile(
                r"->setAllowFileAccess\(|->setAllowFileAccessFromFileURLs\(|"
                r"->setAllowUniversalAccessFromFileURLs\(|->setAllowContentAccess\("
            ),
            True,
            "文件/内容 URL 访问（file:// 跨源读取本地文件）",
        ),
        "mixed_content": (
            re.compile(r"->setMixedContentMode\("),
            False,
            "混合内容模式（HTTPS 页面加载 HTTP 资源→MITM）",
        ),
        "debug": (
            re.compile(r"->setWebContentsDebuggingEnabled\("),
            True,
            "远程调试（可被 adb/其他应用 inspect WebView）",
        ),
        "load": (
            re.compile(
                r"->loadUrl\(|->loadData\(|->loadDataWithBaseURL\(|->postUrl\("
            ),
            False,
            "内容加载入口（若 URL 用户可控→加载任意页面）",
        ),
        "settings": (
            re.compile(r"->getSettings\(\)Landroid/webkit/WebSettings;"),
            False,
            "获取 WebSettings（配置入口，追踪后续 setter）",
        ),
    }

    try:
        results = {k: [] for k in checks}
        webview_using_methods = set()
        scanned = 0

        for ma in analysis_obj.get_methods():
            if ma.is_external():
                continue
            scanned += 1
            from_sig = f"{ma.class_name}->{ma.name}{ma.descriptor}"
            try:
                xrefs = ma.get_xref_to()
            except Exception:
                continue
            for ref_class, ref_method, off in xrefs:
                full = f"{ref_class.name}->{ref_method.name}{ref_method.descriptor}"
                if (
                    "webkit" in full.lower()
                    or "WebView" in full
                    or "WebSettings" in full
                ):
                    webview_using_methods.add(from_sig)
                for cat, (pat, _high, _desc) in checks.items():
                    if pat.search(full):
                        results[cat].append(
                            {"from": from_sig, "calls": full, "offset": off}
                        )
                        break

        categories = {}
        findings = []
        for cat, (pat, high_risk, desc) in checks.items():
            items = results[cat]
            # set 迭代非确定，切片前排序固定输出（与 insecure-storage 同构缺陷）
            items.sort(key=lambda it: (it["from"], it["calls"], it["offset"]))
            categories[cat] = {
                "count": len(items),
                "high_risk": high_risk,
                "meaning": desc,
                "samples": items[:per_type_limit] if per_type_limit else items,
            }
            if high_risk and items:
                for it in items[:per_type_limit]:
                    findings.append(
                        {
                            "category": cat,
                            "severity": "high",
                            "from": it["from"],
                            "calls": it["calls"],
                            "offset": it["offset"],
                            "reason": desc,
                        }
                    )

        return {
            "scanned_methods": scanned,
            "webview_using_method_count": len(webview_using_methods),
            "uses_webview": len(webview_using_methods) > 0,
            "finding_count": len(findings),
            "findings": findings,
            "categories": categories,
        }
    except Exception as e:
        return {"error": str(e)}


def analysis_ssl_safety(analysis_obj, per_type_limit: int = 100) -> dict:
    """
    SSL/TLS 校验绕过检测——识别自定义 TrustManager / HostnameVerifier 的不安全实现
    以及"接受全部证书/主机名"的调用，是中间人（MITM）攻击面审计。

    检测两类：
    (1) **不安全实现**：内部类实现 X509TrustManager（含 checkServerTrusted/
        checkClientTrusted 方法）但方法体近乎为空（无 throw，只 return）——即"信任
        全部证书"；或实现 HostnameVerifier.verify 直接返回 true（不校验主机名）。
    (2) **不安全调用**：ALLOW_ALL_HOSTNAME_VERIFIER、SSLCertificateSocketFactory
        ->getInsecure、setDefaultHostnameVerifier、TrustManagerFactory 等已知绕过点。

    与 crypto-usage（加密算法，不涉及证书校验）、security-hotspots（通用网络类，不判
    校验逻辑）的区别：本命令专查"证书/主机名校验是否被削弱"这一 MITM 核心弱点。

    :param analysis_obj: Analysis 对象
    :param per_type_limit: 每类返回样本上限（默认 100）
    :return: 不安全 TrustManager/HostnameVerifier + 绕过调用
    """
    import re

    # 危险调用点（已知绕过 API）
    bypass_calls = re.compile(
        r"->getInsecure\(|ALLOW_ALL_HOSTNAME_VERIFIER|"
        r"Lorg/apache/http/conn/ssl/SSLSocketFactory;->|"
        r"->setDefaultHostnameVerifier\(|->setHostnameVerifier\("
    )

    def _method_is_trivially_true_or_empty(ma):
        """判定方法体是否近乎空（无 throw / 无实质逻辑），即不做校验。"""
        try:
            has_throw = False
            has_conditional_throw = False
            returns_const_true = False
            ins_count = 0
            last_const = None
            for bb in ma.get_basic_blocks().get():
                for ins in bb.get_instructions():
                    ins_count += 1
                    nm = ins.get_name()
                    if nm.startswith("throw"):
                        has_throw = True
                    if nm.startswith("const"):
                        out = ins.get_output() or ""
                        # const/4 vX, 1  -> 记录是否置 1（true）
                        last_const = out.strip().split(",")[-1].strip()
                    if nm.startswith("return"):
                        if last_const in ("1", "0x1"):
                            returns_const_true = True
            # 无 throw 视为不校验；verify 场景额外看是否 return true
            return {
                "instruction_count": ins_count,
                "has_throw": has_throw,
                "returns_true": returns_const_true,
                "insecure": (not has_throw),
            }
        except Exception:
            return {
                "instruction_count": -1,
                "has_throw": False,
                "returns_true": False,
                "insecure": False,
            }

    trust_methods = {"checkServerTrusted", "checkClientTrusted"}
    try:
        insecure_trustmanagers = []
        insecure_hostname_verifiers = []
        bypass_findings = []
        scanned = 0

        for ma in analysis_obj.get_methods():
            if ma.is_external():
                continue
            scanned += 1
            cn = ma.class_name
            mn = ma.name
            from_sig = f"{cn}->{mn}{ma.descriptor}"

            # (1a) 自定义 TrustManager 的 checkServerTrusted/checkClientTrusted
            if mn in trust_methods:
                info = _method_is_trivially_true_or_empty(ma)
                if info.get("insecure"):
                    insecure_trustmanagers.append(
                        {
                            "class": cn,
                            "method": mn,
                            "descriptor": ma.descriptor,
                            "instruction_count": info["instruction_count"],
                            "reason": "checkServerTrusted/checkClientTrusted 无 throw，信任全部证书",
                        }
                    )
            # (1b) HostnameVerifier.verify 返回 true
            elif (
                mn == "verify"
                and ma.descriptor.endswith(")Z")
                and ("String" in ma.descriptor)
            ):
                info = _method_is_trivially_true_or_empty(ma)
                if info.get("returns_true") and not info.get("has_throw"):
                    insecure_hostname_verifiers.append(
                        {
                            "class": cn,
                            "method": mn,
                            "descriptor": ma.descriptor,
                            "instruction_count": info["instruction_count"],
                            "reason": "HostnameVerifier.verify 直接返回 true，不校验主机名",
                        }
                    )

            # (2) 不安全调用点
            try:
                for ref_class, ref_method, off in ma.get_xref_to():
                    full = f"{ref_class.name}->{ref_method.name}{ref_method.descriptor}"
                    if bypass_calls.search(full):
                        bypass_findings.append(
                            {"from": from_sig, "calls": full, "offset": off}
                        )
            except Exception:
                pass

        n = per_type_limit
        return {
            "scanned_methods": scanned,
            "insecure_trustmanager_count": len(insecure_trustmanagers),
            "insecure_hostname_verifier_count": len(
                insecure_hostname_verifiers
            ),
            "bypass_call_count": len(bypass_findings),
            "mitm_vulnerable": bool(
                insecure_trustmanagers or insecure_hostname_verifiers
            ),
            "insecure_trustmanagers": (
                insecure_trustmanagers[:n] if n else insecure_trustmanagers
            ),
            "insecure_hostname_verifiers": (
                insecure_hostname_verifiers[:n]
                if n
                else insecure_hostname_verifiers
            ),
            "bypass_calls": bypass_findings[:n] if n else bypass_findings,
        }
    except Exception as e:
        return {"error": str(e)}


def analysis_insecure_storage(analysis_obj, per_type_limit: int = 100) -> dict:
    """
    不安全数据存储审计（OWASP Mobile M9）——扫描所有内部方法对存储 API 的调用，
    定位世界可读/可写文件、外部存储写入、明文 SharedPreferences 等敏感数据暴露点。

    与 hardcoded-secrets（静态字段中的密钥）、security-hotspots（通用危险调用）的
    区别：本命令专注"数据落地"的安全性——数据写到哪、用什么权限模式，是敏感信息
    泄露（其他应用可读、adb 可导出、备份可提取）的审计入口。

    :param analysis_obj: Analysis 对象
    :param per_type_limit: 每类返回样本上限（默认 100）
    :return: 存储调用聚合 + 高危 findings
    """
    import re

    # 类别 -> (调用正则, 是否高危, 安全含义)
    checks = {
        "world_readable_writable": (
            re.compile(
                r"->openFileOutput\(|->getSharedPreferences\(|->getDir\("
            ),
            False,
            "文件/偏好写入入口（需核验 mode 是否 MODE_WORLD_READABLE/WRITEABLE=1/2）",
        ),
        "external_storage": (
            re.compile(
                r"->getExternalStorageDirectory\(|->getExternalFilesDir\(|"
                r"->getExternalCacheDir\(|->getExternalStoragePublicDirectory\(|"
                r"->getExternalMediaDirs\("
            ),
            True,
            "外部存储（世界可读，任意应用/用户可访问，勿存敏感数据）",
        ),
        "shared_prefs_edit": (
            re.compile(r"Landroid/content/SharedPreferences\$Editor;->put"),
            False,
            "SharedPreferences 明文写入（XML 明文，root/备份可提取）",
        ),
        "database_open": (
            re.compile(
                r"->openOrCreateDatabase\(|->getWritableDatabase\(|"
                r"->getReadableDatabase\(|SQLiteDatabase;->openDatabase\("
            ),
            False,
            "SQLite 数据库打开（默认明文，需核验是否加密/权限模式）",
        ),
        "internal_cache": (
            re.compile(r"->getCacheDir\(|->getFilesDir\(|->getDataDir\("),
            False,
            "内部存储（应用私有沙箱，相对安全，仅明文备份风险）",
        ),
        "world_mode_constant": (
            re.compile(r"->setReadable\(|->setWritable\(|->createTempFile\("),
            False,
            "文件权限设置/临时文件（核验是否设为全局可读写）",
        ),
    }

    try:
        results = {k: [] for k in checks}
        scanned = 0
        for ma in analysis_obj.get_methods():
            if ma.is_external():
                continue
            scanned += 1
            from_sig = f"{ma.class_name}->{ma.name}{ma.descriptor}"
            try:
                xrefs = ma.get_xref_to()
            except Exception:
                continue
            for ref_class, ref_method, off in xrefs:
                full = f"{ref_class.name}->{ref_method.name}{ref_method.descriptor}"
                for cat, (pat, _high, _desc) in checks.items():
                    if pat.search(full):
                        results[cat].append(
                            {"from": from_sig, "calls": full, "offset": off}
                        )
                        break

        categories = {}
        findings = []
        for cat, (pat, high_risk, desc) in checks.items():
            items = results[cat]
            # get_methods()/get_xref_to() 返回 set，迭代序非确定 → 切片前排序固定输出
            items.sort(key=lambda it: (it["from"], it["calls"], it["offset"]))
            categories[cat] = {
                "count": len(items),
                "high_risk": high_risk,
                "meaning": desc,
                "samples": items[:per_type_limit] if per_type_limit else items,
            }
            if high_risk and items:
                for it in items[:per_type_limit]:
                    findings.append(
                        {
                            "category": cat,
                            "severity": "high",
                            "from": it["from"],
                            "calls": it["calls"],
                            "offset": it["offset"],
                            "reason": desc,
                        }
                    )

        return {
            "scanned_methods": scanned,
            "uses_external_storage": categories["external_storage"]["count"]
            > 0,
            "finding_count": len(findings),
            "findings": findings,
            "categories": categories,
        }
    except Exception as e:
        return {"error": str(e)}


def analysis_sql_injection(analysis_obj, per_type_limit: int = 100) -> dict:
    """
    SQL 注入面审计（OWASP Mobile M7）——枚举所有 SQL 执行 API 调用点。rawQuery/
    execSQL 若拼接用户可控字符串则可注入；query(...) 的 selection 参数同理。本命令
    定位所有 SQL 执行入口，标记高危 API（rawQuery/execSQL 直接执行拼接 SQL），
    供人工核验参数是否用户可控 + 是否参数化。

    :param analysis_obj: Analysis 对象
    :param per_type_limit: 每类返回样本上限（默认 100）
    :return: SQL 执行调用聚合 + 高危 findings
    """
    import re

    checks = {
        "raw_query": (
            re.compile(r"->rawQuery(WithFactory)?\("),
            True,
            "rawQuery 执行原始 SQL（若拼接用户输入→注入）",
        ),
        "exec_sql": (
            re.compile(r"->execSQL\("),
            True,
            "execSQL 执行原始 SQL（若拼接用户输入→注入）",
        ),
        "query_builder": (
            re.compile(r"SQLiteQueryBuilder;->(query|buildQuery)\("),
            False,
            "QueryBuilder 构造查询（selection/appendWhere 拼接可注入）",
        ),
        "structured_query": (
            re.compile(
                r"SQLiteDatabase;->(query|queryWithFactory|update|delete|insert)\("
            ),
            False,
            "结构化 query/update/delete（selection 参数拼接可注入，用 ? 占位更安全）",
        ),
        "compile_statement": (
            re.compile(r"->compileStatement\("),
            False,
            "预编译语句（若 SQL 字符串含拼接仍可注入）",
        ),
    }

    try:
        results = {k: [] for k in checks}
        scanned = 0
        for ma in analysis_obj.get_methods():
            if ma.is_external():
                continue
            scanned += 1
            from_sig = f"{ma.class_name}->{ma.name}{ma.descriptor}"
            try:
                xrefs = ma.get_xref_to()
            except Exception:
                continue
            for ref_class, ref_method, off in xrefs:
                full = f"{ref_class.name}->{ref_method.name}{ref_method.descriptor}"
                for cat, (pat, _high, _desc) in checks.items():
                    if pat.search(full):
                        results[cat].append(
                            {"from": from_sig, "calls": full, "offset": off}
                        )
                        break

        categories = {}
        findings = []
        for cat, (pat, high_risk, desc) in checks.items():
            items = results[cat]
            # set 迭代非确定，切片前排序固定输出（与 insecure-storage 同构缺陷）
            items.sort(key=lambda it: (it["from"], it["calls"], it["offset"]))
            categories[cat] = {
                "count": len(items),
                "high_risk": high_risk,
                "meaning": desc,
                "samples": items[:per_type_limit] if per_type_limit else items,
            }
            if high_risk and items:
                for it in items[:per_type_limit]:
                    findings.append(
                        {
                            "category": cat,
                            "severity": "high",
                            "from": it["from"],
                            "calls": it["calls"],
                            "offset": it["offset"],
                            "reason": desc,
                        }
                    )

        return {
            "scanned_methods": scanned,
            "uses_sql": any(categories[c]["count"] for c in categories),
            "finding_count": len(findings),
            "findings": findings,
            "categories": categories,
        }
    except Exception as e:
        return {"error": str(e)}


def analysis_pending_intent(analysis_obj, per_type_limit: int = 100) -> dict:
    """
    PendingIntent 可变性审计（Intent 重定向 / CVE 类）——枚举所有 PendingIntent.get*
    创建点。可变（无 FLAG_IMMUTABLE）且包裹隐式 Intent 的 PendingIntent 允许攻击者
    篡改内部 Intent 实现权限提升 / Intent 重定向（Android 12+ 强制要求指定可变性）。

    本命令定位所有 PendingIntent 创建点 + getIntent/隐式 Intent 相关调用，供核验
    flag 是否含 FLAG_IMMUTABLE（0x4000000=67108864）。不做 flag 位值还原（or 运算
    寄存器跟踪易误报），而是枚举 + 标记需人工核验，保持可靠。

    :param analysis_obj: Analysis 对象
    :param per_type_limit: 每类返回样本上限（默认 100）
    :return: PendingIntent/Intent 重定向调用聚合 + findings
    """
    import re

    checks = {
        "pending_intent_create": (
            re.compile(
                r"Landroid/app/PendingIntent;->"
                r"(getActivity|getActivities|getBroadcast|getService|getForegroundService)\("
            ),
            True,
            "PendingIntent 创建（需核验 flag 含 FLAG_IMMUTABLE=0x4000000，否则可被篡改）",
        ),
        "get_intent": (
            re.compile(
                r"->getIntent\(\)Landroid/content/Intent;|"
                r"->getParcelableExtra\(|->getIntentExtra\("
            ),
            False,
            "读取传入 Intent（外部可控入口，若转发→Intent 重定向）",
        ),
        "intent_forward": (
            re.compile(
                r"->startActivity\(|->startActivities\(|->sendBroadcast\(|"
                r"->startService\(|->setResult\("
            ),
            False,
            "Intent 转发/回传（若转发外部传入的 Intent→重定向/权限提升）",
        ),
        "intent_component": (
            re.compile(
                r"Landroid/content/Intent;->(setComponent|setClassName|setPackage)\("
            ),
            False,
            "Intent 目标显式设定（显式 Intent 相对安全，隐式则风险高）",
        ),
    }

    try:
        results = {k: [] for k in checks}
        scanned = 0
        for ma in analysis_obj.get_methods():
            if ma.is_external():
                continue
            scanned += 1
            from_sig = f"{ma.class_name}->{ma.name}{ma.descriptor}"
            try:
                xrefs = ma.get_xref_to()
            except Exception:
                continue
            for ref_class, ref_method, off in xrefs:
                full = f"{ref_class.name}->{ref_method.name}{ref_method.descriptor}"
                for cat, (pat, _high, _desc) in checks.items():
                    if pat.search(full):
                        results[cat].append(
                            {"from": from_sig, "calls": full, "offset": off}
                        )
                        break

        categories = {}
        findings = []
        for cat, (pat, high_risk, desc) in checks.items():
            items = results[cat]
            # set 迭代非确定，切片前排序固定输出（与 insecure-storage 同构缺陷）
            items.sort(key=lambda it: (it["from"], it["calls"], it["offset"]))
            categories[cat] = {
                "count": len(items),
                "high_risk": high_risk,
                "meaning": desc,
                "samples": items[:per_type_limit] if per_type_limit else items,
            }
            if high_risk and items:
                for it in items[:per_type_limit]:
                    findings.append(
                        {
                            "category": cat,
                            "severity": "review",
                            "from": it["from"],
                            "calls": it["calls"],
                            "offset": it["offset"],
                            "reason": desc,
                        }
                    )

        return {
            "scanned_methods": scanned,
            "uses_pending_intent": categories["pending_intent_create"]["count"]
            > 0,
            "finding_count": len(findings),
            "findings": findings,
            "categories": categories,
        }
    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# 第三十四轮：完整安全分析矩阵（一次性铺满剩余漏洞/恶意/加固/隐私维度）
# 共享 xref_to 语义归类骨架 + 10 专项审计 + 1 综合报告闭环
# ============================================================================


def _xref_semantic_audit(
    analysis_obj,
    checks: dict,
    per_type_limit: int = 100,
    auto_finding: bool = True,
    finding_severity: str = "high",
) -> dict:
    """
    通用 xref_to 语义审计骨架：遍历全量内部方法 get_xref_to()，按 checks 归类被调 API，
    高危类别（high_risk=True）自动生成 findings。是第三十三/三十四轮所有漏洞类审计命令
    的共享内核。

    :param checks: {category: (compiled_regex, is_high_risk, meaning)}
    :param per_type_limit: 每类样本上限
    :param auto_finding: 高危类别是否自动生成 findings
    :param finding_severity: findings 的 severity 标签（high / review）
    :return: {scanned_methods, finding_count, findings, categories}
    """
    results = {k: [] for k in checks}
    scanned = 0
    for ma in analysis_obj.get_methods():
        if ma.is_external():
            continue
        scanned += 1
        from_sig = f"{ma.class_name}->{ma.name}{ma.descriptor}"
        try:
            xrefs = ma.get_xref_to()
        except Exception:
            continue
        for ref_class, ref_method, off in xrefs:
            full = (
                f"{ref_class.name}->{ref_method.name}{ref_method.descriptor}"
            )
            for cat, (pat, _h, _d) in checks.items():
                if pat.search(full):
                    results[cat].append(
                        {"from": from_sig, "calls": full, "offset": off}
                    )
                    break
    categories = {}
    findings = []
    for cat, (pat, high_risk, desc) in checks.items():
        items = results[cat]
        # items 来自 get_xref_to() 的 set 迭代，顺序非确定（依赖哈希）。
        # 排序固定 samples/findings 顺序，让输出确定（agent 对接需确定性）。
        # 修此共享内核，所有用 _xref_semantic_audit 的漏洞类审计命令都受益。
        items.sort(key=lambda it: (it["from"], it["calls"], it["offset"]))
        categories[cat] = {
            "count": len(items),
            "high_risk": high_risk,
            "meaning": desc,
            "samples": items[:per_type_limit] if per_type_limit else items,
        }
        if auto_finding and high_risk and items:
            for it in items[:per_type_limit]:
                findings.append(
                    {
                        "category": cat,
                        "severity": finding_severity,
                        "from": it["from"],
                        "calls": it["calls"],
                        "offset": it["offset"],
                        "reason": desc,
                    }
                )
    return {
        "scanned_methods": scanned,
        "finding_count": len(findings),
        "findings": findings,
        "categories": categories,
    }


def analysis_privacy_sinks(analysis_obj, per_type_limit: int = 100) -> dict:
    """隐私数据收集审计（OWASP M6）——设备标识/位置/联系人/账户/已装应用/剪贴板/录音摄像。"""
    import re

    checks = {
        "device_id": (
            re.compile(
                r"->getDeviceId\(|->getImei\(|->getMeid\(|->getSubscriberId\(|"
                r"->getSimSerialNumber\(|->getLine1Number\(|->getSerial\(|->getAndroidId\("
            ),
            True,
            "设备唯一标识读取（IMEI/IMSI/序列号/电话号，可追踪用户）",
        ),
        "location": (
            re.compile(
                r"->getLastKnownLocation\(|->requestLocationUpdates\(|->getLatitude\(|"
                r"->getLongitude\(|->requestSingleUpdate\(|LocationManager;->"
            ),
            True,
            "位置信息读取（精确地理位置，隐私敏感）",
        ),
        "contacts": (
            re.compile(
                r"ContactsContract|->getContentResolver\(\).*contacts|CommonDataKinds"
            ),
            True,
            "联系人读取（通讯录数据）",
        ),
        "accounts": (
            re.compile(
                r"AccountManager;->(getAccounts|getAccountsByType|getAuthToken|getPassword)"
            ),
            False,
            "账户信息读取（AccountManager，可枚举登录账户）",
        ),
        "installed_apps": (
            re.compile(
                r"->getInstalledPackages\(|->getInstalledApplications\(|->queryIntentActivities\("
            ),
            False,
            "已安装应用枚举（用户画像/竞品侦察）",
        ),
        "clipboard": (
            re.compile(
                r"ClipboardManager;->(getPrimaryClip|getText|hasPrimaryClip)"
            ),
            False,
            "剪贴板读取（可窃取复制的密码/验证码）",
        ),
        "capture": (
            re.compile(
                r"MediaRecorder;->|Landroid/hardware/Camera;->(open|takePicture)|"
                r"AudioRecord;-><init>|->startRecording\("
            ),
            True,
            "录音/拍照（麦克风/摄像头采集，隐私高危）",
        ),
    }
    r = _xref_semantic_audit(analysis_obj, checks, per_type_limit)
    r["privacy_category_hit"] = sum(
        1 for c in r["categories"].values() if c["count"] > 0
    )
    return r


def analysis_telephony_sms(analysis_obj, per_type_limit: int = 100) -> dict:
    """电话短信滥用审计——发短信/读短信/拨号/短信拦截/通话状态监听（恶意扣费/拦截马特征）。"""
    import re

    checks = {
        "send_sms": (
            re.compile(
                r"SmsManager;->(sendTextMessage|sendMultipartTextMessage|sendDataMessage)"
            ),
            True,
            "发送短信（可静默扣费/发送高级短信，恶意软件高频行为）",
        ),
        "read_sms": (
            re.compile(
                r"content://sms|Telephony\$Sms|Telephony;.*Sms|->getMessageBody\(|"
                r"SmsMessage;->createFromPdu"
            ),
            True,
            "读取/解析短信（窃取验证码/银行短信，短信拦截马特征）",
        ),
        "make_call": (
            re.compile(
                r"Intent;->.*ACTION_CALL|TelecomManager;->placeCall|->ACTION_DIAL"
            ),
            False,
            "拨打电话（可拨打付费号码）",
        ),
        "intercept": (
            re.compile(
                r"->abortBroadcast\(|BroadcastReceiver;->abortBroadcast"
            ),
            True,
            "中止广播（配合短信 receiver 拦截短信不让系统显示）",
        ),
        "phone_state": (
            re.compile(
                r"PhoneStateListener|->getCallState\(|->listen\(|TelephonyManager;->getNetworkOperator"
            ),
            False,
            "电话状态监听（通话监听/运营商信息）",
        ),
    }
    r = _xref_semantic_audit(analysis_obj, checks, per_type_limit)
    r["telephony_category_hit"] = sum(
        1 for c in r["categories"].values() if c["count"] > 0
    )
    return r


def analysis_dynamic_code(analysis_obj, per_type_limit: int = 100) -> dict:
    """动态代码加载审计——DexClassLoader/native 库加载/运行时 defineClass（加固脱壳/恶意 payload 加载）。"""
    import re

    checks = {
        "dex_loader": (
            re.compile(
                r"DexClassLoader;->|PathClassLoader;->|InMemoryDexClassLoader;->|"
                r"BaseDexClassLoader;->|DexFile;->(loadDex|loadClass)"
            ),
            True,
            "动态 DEX 加载（运行时加载额外代码，脱壳/热更新/恶意 payload）",
        ),
        "native_load": (
            re.compile(
                r"Runtime;->(load|loadLibrary)\(|Ljava/lang/System;->(load|loadLibrary)\("
            ),
            False,
            "native 库加载（System.load 可加载任意路径 .so）",
        ),
        "define_class": (
            re.compile(
                r"ClassLoader;->(defineClass|loadClass)\(|->getClassLoader\("
            ),
            False,
            "ClassLoader 操作（自定义类加载，可绕过完整性校验）",
        ),
        "reflection_load": (
            re.compile(
                r"Ljava/lang/Class;->forName\(|->getDeclaredMethod\(|Method;->invoke\("
            ),
            False,
            "反射加载（配合动态加载调用隐藏代码，见 reflection-targets）",
        ),
    }
    r = _xref_semantic_audit(analysis_obj, checks, per_type_limit)
    r["uses_dynamic_loading"] = r["categories"]["dex_loader"]["count"] > 0
    return r


def analysis_persistence(analysis_obj, per_type_limit: int = 100) -> dict:
    """持久化/后台驻留审计——定时任务/闹钟/前台服务/设备管理员/无障碍（恶意驻留/提权特征）。"""
    import re

    checks = {
        "device_admin": (
            re.compile(
                r"DevicePolicyManager;->|DeviceAdminReceiver|->lockNow\(|->wipeData\(|"
                r"->resetPassword\("
            ),
            True,
            "设备管理员（锁屏/清除数据/强制策略，勒索软件特征，难卸载）",
        ),
        "accessibility": (
            re.compile(
                r"AccessibilityService|->performGlobalAction\(|AccessibilityNodeInfo;->|"
                r"->getRootInActiveWindow\("
            ),
            True,
            "无障碍服务（可读取屏幕/模拟点击，覆盖攻击/自动化恶意操作）",
        ),
        "job_alarm": (
            re.compile(
                r"JobScheduler;->schedule|AlarmManager;->(set|setRepeating|setExact|setInexactRepeating)|"
                r"WorkManager;->enqueue"
            ),
            False,
            "定时任务/闹钟（后台周期唤醒，驻留机制）",
        ),
        "foreground_service": (
            re.compile(
                r"->startForeground\(|->startForegroundService\(|Service;->startForeground"
            ),
            False,
            "前台服务（保活，长期后台运行）",
        ),
        "notification_listener": (
            re.compile(
                r"NotificationListenerService|->getActiveNotifications\("
            ),
            True,
            "通知监听（读取所有应用通知，窃取验证码/消息）",
        ),
    }
    r = _xref_semantic_audit(analysis_obj, checks, per_type_limit)
    r["persistence_category_hit"] = sum(
        1 for c in r["categories"].values() if c["count"] > 0
    )
    return r


def analysis_weak_random(analysis_obj, per_type_limit: int = 100) -> dict:
    """不安全随机数审计（OWASP M10）——java.util.Random/Math.random 用于安全场景 vs SecureRandom。"""
    import re

    checks = {
        "insecure_random": (
            re.compile(
                r"Ljava/util/Random;->(<init>|nextInt|nextLong|nextBytes|nextDouble|nextFloat)|"
                r"Ljava/lang/Math;->random\("
            ),
            True,
            "不安全随机（java.util.Random/Math.random 可预测，勿用于密钥/token/IV/盐）",
        ),
        "fixed_seed": (
            re.compile(r"->setSeed\(|Random;-><init>\(J\)"),
            True,
            "固定随机种子（setSeed 使随机数可预测复现）",
        ),
        "secure_random": (
            re.compile(
                r"SecureRandom;->(<init>|nextBytes|nextInt|generateSeed)"
            ),
            False,
            "安全随机（SecureRandom，正确用法，对比参考）",
        ),
    }
    r = _xref_semantic_audit(analysis_obj, checks, per_type_limit)
    r["uses_insecure_random"] = r["categories"]["insecure_random"]["count"] > 0
    return r


def analysis_broadcast_safety(analysis_obj, per_type_limit: int = 100) -> dict:
    """广播收发安全审计——无权限广播/动态 receiver 注册/粘性广播（组件间通信劫持面）。"""
    import re

    checks = {
        "send_broadcast": (
            re.compile(
                r"->sendBroadcast\(|->sendOrderedBroadcast\(|->sendBroadcastAsUser\("
            ),
            False,
            "发送广播（无 receiverPermission 参数则任意应用可接收→敏感数据泄露）",
        ),
        "sticky_broadcast": (
            re.compile(
                r"->sendStickyBroadcast\(|->sendStickyOrderedBroadcast\("
            ),
            True,
            "粘性广播（已废弃，无法限制接收者，数据持久暴露）",
        ),
        "register_dynamic": (
            re.compile(r"->registerReceiver\("),
            False,
            "动态注册 receiver（无 permission 参数则任意应用可触发→组件劫持）",
        ),
        "local_broadcast": (
            re.compile(
                r"LocalBroadcastManager;->(sendBroadcast|registerReceiver)"
            ),
            False,
            "本地广播（进程内，安全用法，对比参考）",
        ),
    }
    r = _xref_semantic_audit(analysis_obj, checks, per_type_limit)
    return r


def analysis_provider_safety(analysis_obj, per_type_limit: int = 100) -> dict:
    """ContentProvider 安全审计——openFile 路径穿越/URI 权限授予/跨应用数据访问。"""
    import re

    checks = {
        "open_file": (
            re.compile(
                r"ContentProvider;->openFile\(|->openAssetFile\(|ParcelFileDescriptor;->open\("
            ),
            True,
            "Provider openFile（若拼接 URI path 未校验→路径穿越读任意文件）",
        ),
        "grant_uri": (
            re.compile(
                r"->grantUriPermission\(|FLAG_GRANT_READ_URI_PERMISSION|FLAG_GRANT_WRITE_URI_PERMISSION"
            ),
            False,
            "URI 权限授予（临时授予其他应用访问，需核验范围）",
        ),
        "resolver_access": (
            re.compile(
                r"ContentResolver;->(query|insert|update|delete|openInputStream|openOutputStream)"
            ),
            False,
            "ContentResolver 访问（跨应用数据读写入口）",
        ),
        "provider_query": (
            re.compile(r"ContentProvider;->(query|insert|update|delete)\("),
            False,
            "Provider 查询实现（需核验 selection 注入 + 权限校验）",
        ),
    }
    r = _xref_semantic_audit(analysis_obj, checks, per_type_limit)
    return r


def analysis_anti_analysis(analysis_obj, per_type_limit: int = 100) -> dict:
    """反分析/加固对抗侦察——root/模拟器/调试器/Frida/Xposed 检测特征（字符串 + API 双路扫描）。"""
    import re

    # API 层检测（xref_to）
    api_checks = {
        "debugger_api": (
            re.compile(
                r"Debug;->(isDebuggerConnected|waitForDebugger)|->isDebuggerConnected\("
            ),
            True,
            "调试器检测 API（isDebuggerConnected，反调试）",
        ),
    }
    r = _xref_semantic_audit(analysis_obj, api_checks, per_type_limit)

    # 字符串特征层检测（get_strings）
    str_patterns = {
        "root_detect": (
            re.compile(
                r"/system/(bin|xbin)/su|/system/app/Superuser|busybox|magisk|"
                r"test-keys|RootTools|/su/bin|which su",
                re.I,
            ),
            "Root 检测特征串（su 路径/Magisk/Superuser/test-keys）",
        ),
        "emulator_detect": (
            re.compile(
                r"ro\.kernel\.qemu|goldfish|ranchu|generic_x86|vbox|genymotion|"
                r"android_x86|/dev/socket/qemud|nox|bluestacks",
                re.I,
            ),
            "模拟器检测特征串（qemu/goldfish/genymotion/nox/bluestacks）",
        ),
        "frida_xposed": (
            re.compile(
                r"frida|xposed|de\.robv\.android|/data/local/tmp/re\.frida|"
                r"substrate|libfrida|EdXposed|LSPosed|riru",
                re.I,
            ),
            "Frida/Xposed 检测特征串（hook 框架侦测）",
        ),
    }
    str_results = {k: [] for k in str_patterns}
    strings_scanned = 0
    try:
        for sa in analysis_obj.get_strings():
            val = sa.get_value()
            if not val:
                continue
            strings_scanned += 1
            for cat, (pat, _desc) in str_patterns.items():
                if pat.search(val):
                    xf = []
                    try:
                        # get_xref_from() set 迭代序非确定 → 排序后切片固定 used_in
                        refs = sorted(
                            list(sa.get_xref_from())[:3],
                            key=lambda t: f"{t[1].class_name}->{t[1].name}",
                        )
                        for cm, mm, off in refs:
                            xf.append(f"{mm.class_name}->{mm.name}")
                    except Exception:
                        pass
                    str_results[cat].append(
                        {"value": val[:120], "used_in": xf}
                    )
                    break
    except Exception:
        pass

    string_categories = {}
    for cat, (pat, desc) in str_patterns.items():
        items = str_results[cat]
        # get_strings() set 迭代序非确定 → 切片前排序
        items.sort(key=lambda it: (it.get("value", ""),))
        string_categories[cat] = {
            "count": len(items),
            "high_risk": True,
            "meaning": desc,
            "samples": items[:per_type_limit] if per_type_limit else items,
        }
    total_indicators = r["categories"]["debugger_api"]["count"] + sum(
        c["count"] for c in string_categories.values()
    )
    return {
        "scanned_methods": r["scanned_methods"],
        "strings_scanned": strings_scanned,
        "total_anti_analysis_indicators": total_indicators,
        "has_anti_analysis": total_indicators > 0,
        "api_categories": r["categories"],
        "string_indicator_categories": string_categories,
    }


def analysis_network_security(analysis_obj, per_type_limit: int = 100) -> dict:
    """网络安全配置审计——明文 URL/证书固定/SSL 上下文/HTTP 客户端（通信安全总览，与 ssl-safety 互补）。"""
    import re

    # API 层
    api_checks = {
        "cert_pinning": (
            re.compile(
                r"CertificatePinner|->certificatePinner\(|->setSSLSocketFactory\(|"
                r"X509TrustManager|network_security_config"
            ),
            False,
            "证书固定/TLS 配置（CertificatePinner=有固定，缺失则可被 MITM）",
        ),
        "http_client": (
            re.compile(
                r"HttpURLConnection;->|OkHttpClient;->|Landroid/net/http/|"
                r"DefaultHttpClient;->|HttpsURLConnection;->"
            ),
            False,
            "HTTP 客户端使用（网络请求入口，核验是否 https + 固定）",
        ),
        "ssl_context": (
            re.compile(
                r"SSLContext;->(getInstance|init)|->getSocketFactory\(|SSLSocketFactory;->"
            ),
            False,
            "SSL 上下文（自定义 SSLContext 需核验 TrustManager，见 ssl-safety）",
        ),
    }
    r = _xref_semantic_audit(analysis_obj, api_checks, per_type_limit)

    # 字符串层：明文 http URL
    cleartext = []
    https_count = 0
    strings_scanned = 0
    http_pat = re.compile(r"^http://", re.I)
    https_pat = re.compile(r"^https://", re.I)
    try:
        for sa in analysis_obj.get_strings():
            val = sa.get_value()
            if not val:
                continue
            strings_scanned += 1
            if http_pat.search(val.strip()):
                xf = []
                try:
                    for cm, mm, off in list(sa.get_xref_from())[:3]:
                        xf.append(f"{mm.class_name}->{mm.name}")
                except Exception:
                    pass
                cleartext.append({"url": val[:150], "used_in": xf})
            elif https_pat.search(val.strip()):
                https_count += 1
    except Exception:
        pass

    return {
        "scanned_methods": r["scanned_methods"],
        "strings_scanned": strings_scanned,
        "cleartext_url_count": len(cleartext),
        "https_url_count": https_count,
        "has_cert_pinning": r["categories"]["cert_pinning"]["count"] > 0,
        "cleartext_urls": (
            cleartext[:per_type_limit] if per_type_limit else cleartext
        ),
        "api_categories": r["categories"],
    }


def analysis_obfuscation_metrics(analysis_obj) -> dict:
    """混淆度量——类名长度分布/反射密度/字符串覆盖/DEX 特征，量化 APK 混淆/加固程度。"""
    import re

    short_name = 0  # 单/双字符类名（ProGuard/R8 混淆特征）
    total_internal = 0
    reflection_calls = 0
    total_method_calls = 0
    name_len_hist = {}

    for ca in analysis_obj.get_internal_classes():
        total_internal += 1
        cname = ca.name  # Lpkg/Xx;
        simple = cname.rstrip(";").split("/")[-1]
        # 去掉内部类 $ 后缀取最短段
        base = simple.split("$")[-1]
        L = len(base)
        name_len_hist[L] = name_len_hist.get(L, 0) + 1
        if L <= 2:
            short_name += 1

    reflect_pat = re.compile(
        r"Ljava/lang/reflect/|Class;->forName\(|->getDeclaredMethod\(|"
        r"->getDeclaredField\(|Method;->invoke\(|ClassLoader;->loadClass\("
    )
    for ma in analysis_obj.get_methods():
        if ma.is_external():
            continue
        try:
            for ref_class, ref_method, off in ma.get_xref_to():
                total_method_calls += 1
                full = f"{ref_class.name}->{ref_method.name}"
                if reflect_pat.search(full):
                    reflection_calls += 1
        except Exception:
            continue

    # 被覆盖字符串数（字符串解密特征）
    overwritten = 0
    try:
        for sa in analysis_obj.get_strings():
            try:
                if sa.get_value() != sa.get_orig_value():
                    overwritten += 1
            except Exception:
                pass
    except Exception:
        pass

    short_ratio = (
        round(short_name / total_internal, 4) if total_internal else 0.0
    )
    reflect_density = (
        round(reflection_calls / total_method_calls, 6)
        if total_method_calls
        else 0.0
    )
    # 简单混淆评分（0-100）
    score = min(
        100,
        int(
            short_ratio * 70
            + min(reflect_density * 3000, 20)
            + min(overwritten / 10, 10)
        ),
    )
    return {
        "internal_class_count": total_internal,
        "short_name_class_count": short_name,
        "short_name_ratio": short_ratio,
        "reflection_call_count": reflection_calls,
        "total_method_call_count": total_method_calls,
        "reflection_density": reflect_density,
        "overwritten_string_count": overwritten,
        "obfuscation_score": score,
        "assessment": (
            "heavily_obfuscated"
            if score >= 60
            else (
                "moderately_obfuscated"
                if score >= 30
                else "lightly_or_not_obfuscated"
            )
        ),
        "name_length_histogram": dict(sorted(name_len_hist.items())),
    }


def apk_security_report(
    apk_obj, analysis_obj, dex_list=None, per_type_limit: int = 20
) -> dict:
    """
    一键全量安全报告——聚合调用所有专项审计命令，输出顶层风险总览 + 风险评分。
    是整个漏洞审计套件的闭环入口：一条命令得到 APK 的完整安全画像。

    聚合维度：漏洞类（webview/ssl/storage/sql/pending）、恶意行为（隐私/短信电话/
    动态加载/持久化）、密码学（弱加密/弱随机）、通信（网络安全）、组件（广播/provider）、
    加固（反分析/混淆）、通用（security-hotspots/hardcoded-secrets/attack-surface）。

    :return: 各审计域顶层计数 + 高危 findings 汇总 + 综合风险评分
    """
    report = {"domains": {}, "high_risk_findings": [], "errors": []}

    def _safe(name, fn):
        try:
            return fn()
        except Exception as e:
            report["errors"].append(f"{name}: {str(e)}")
            return None

    L = per_type_limit
    # 漏洞类审计
    audits = {
        "webview_security": lambda: analysis_webview_security(analysis_obj, L),
        "ssl_safety": lambda: analysis_ssl_safety(analysis_obj, L),
        "insecure_storage": lambda: analysis_insecure_storage(analysis_obj, L),
        "sql_injection": lambda: analysis_sql_injection(analysis_obj, L),
        "pending_intent": lambda: analysis_pending_intent(analysis_obj, L),
        "privacy_sinks": lambda: analysis_privacy_sinks(analysis_obj, L),
        "telephony_sms": lambda: analysis_telephony_sms(analysis_obj, L),
        "dynamic_code": lambda: analysis_dynamic_code(analysis_obj, L),
        "persistence": lambda: analysis_persistence(analysis_obj, L),
        "weak_random": lambda: analysis_weak_random(analysis_obj, L),
        "broadcast_safety": lambda: analysis_broadcast_safety(analysis_obj, L),
        "provider_safety": lambda: analysis_provider_safety(analysis_obj, L),
        "network_security": lambda: analysis_network_security(analysis_obj, L),
        "anti_analysis": lambda: analysis_anti_analysis(analysis_obj, L),
    }
    total_findings = 0
    for name, fn in audits.items():
        res = _safe(name, fn)
        if res is None:
            continue
        fc = res.get(
            "finding_count", res.get("total_anti_analysis_indicators", 0)
        )
        # ssl-safety 用 mitm_vulnerable
        mitm = res.get("mitm_vulnerable")
        summary = {"finding_count": fc}
        for k in (
            "uses_webview",
            "mitm_vulnerable",
            "uses_external_storage",
            "uses_sql",
            "uses_pending_intent",
            "uses_dynamic_loading",
            "uses_insecure_random",
            "has_anti_analysis",
            "has_cert_pinning",
            "cleartext_url_count",
            "privacy_category_hit",
            "telephony_category_hit",
            "persistence_category_hit",
        ):
            if k in res:
                summary[k] = res[k]
        report["domains"][name] = summary
        total_findings += fc if isinstance(fc, int) else 0
        # 收集高危 findings（前几条）
        for f in (res.get("findings") or [])[:3]:
            report["high_risk_findings"].append(
                {
                    "domain": name,
                    **{
                        kk: f.get(kk)
                        for kk in ("category", "from", "calls", "reason")
                    },
                }
            )

    # 混淆度量
    obf = _safe(
        "obfuscation_metrics",
        lambda: analysis_obfuscation_metrics(analysis_obj),
    )
    if obf:
        report["domains"]["obfuscation"] = {
            "score": obf.get("obfuscation_score"),
            "assessment": obf.get("assessment"),
            "short_name_ratio": obf.get("short_name_ratio"),
        }
    # 通用扫描
    hs = _safe(
        "security_hotspots",
        lambda: analysis_security_hotspots(analysis_obj, L),
    )
    if hs:
        report["domains"]["security_hotspots"] = {
            "total": hs.get("total_findings", hs.get("total", 0))
        }
    if dex_list is None:
        dex_list = getattr(analysis_obj, "vms", None) or []
    sec = _safe(
        "hardcoded_secrets",
        lambda: analysis_hardcoded_secrets(analysis_obj, dex_list, L),
    )
    if sec:
        report["domains"]["hardcoded_secrets"] = {
            "finding_count": sec.get(
                "total_findings", sec.get("finding_count", 0)
            )
        }
    atk = _safe(
        "attack_surface", lambda: apk_attack_surface(apk_obj, analysis_obj)
    )
    if atk:
        report["domains"]["attack_surface"] = {
            "exposed_component_count": atk.get(
                "exposed_component_count", atk.get("total_exposed", 0)
            ),
            "critical_component_count": len(
                atk.get("critical_components", [])
            ),
        }
    # deeplinks（跨模块局部导入避免循环）
    try:
        from . import apk_skills as _aps

        dl = apk_skills_deeplinks = _aps.apk_deeplinks(apk_obj)
        report["domains"]["deeplinks"] = {
            "deeplink_count": dl.get("deeplink_count", 0),
            "web_reachable_count": dl.get("web_reachable_count", 0),
        }
    except Exception as e:
        report["errors"].append(f"deeplinks: {str(e)}")

    # 综合风险评分（加权）
    d = report["domains"]
    risk = 0
    if d.get("ssl_safety", {}).get("mitm_vulnerable"):
        risk += 25
    risk += min(d.get("webview_security", {}).get("finding_count", 0) * 5, 15)
    risk += min(d.get("sql_injection", {}).get("finding_count", 0) * 2, 15)
    risk += min(d.get("insecure_storage", {}).get("finding_count", 0) * 1, 10)
    if d.get("telephony_sms", {}).get("telephony_category_hit", 0) >= 2:
        risk += 10
    if d.get("dynamic_code", {}).get("uses_dynamic_loading"):
        risk += 8
    if d.get("persistence", {}).get("persistence_category_hit", 0) >= 1:
        risk += 7
    if d.get("anti_analysis", {}).get("has_anti_analysis"):
        risk += 5
    if d.get("network_security", {}).get("cleartext_url_count", 0) > 0:
        risk += 5
    risk = min(100, risk)
    report["total_high_risk_findings"] = total_findings
    report["composite_risk_score"] = risk
    report["risk_level"] = (
        "critical"
        if risk >= 60
        else "high" if risk >= 35 else "medium" if risk >= 15 else "low"
    )
    report["high_risk_findings"] = report["high_risk_findings"][
        :per_type_limit
    ]
    return report


def analysis_find_methods_advanced(
    analysis_obj,
    classname: str = ".*",
    methodname: str = ".*",
    descriptor: str = ".*",
    accessflags: str = ".*",
    no_external: bool = False,
    limit: int = 500,
) -> dict:
    """
    多维正则方法搜索——直接用 androguard 原生 `Analysis.find_methods`，支持类名×方法名×
    描述符×访问标志×排除外部 五维联合正则过滤（远强于仅按名匹配的 find-methods）。

    典型用途：`--accessflags 'public.*static.*native'` 找所有 public static native 方法；
    `--descriptor '.*Ljava/lang/String;$' --classname '.*crypto.*'` 找 crypto 类中返回 String 的方法。

    :param classname: 类名正则（默认 .* 全部）
    :param methodname: 方法名正则
    :param descriptor: 方法描述符正则（含参数与返回类型）
    :param accessflags: 访问标志正则（如 public/private/static/final/native/synchronized）
    :param no_external: 是否排除外部（未实现于 DEX 内的）方法
    :param limit: 返回上限
    :return: 匹配方法列表 + 命中总数
    """
    methods = []
    truncated = False
    for i, ma in enumerate(
        analysis_obj.find_methods(
            classname=classname,
            methodname=methodname,
            descriptor=descriptor,
            accessflags=accessflags,
            no_external=no_external,
        )
    ):
        if len(methods) >= limit:
            truncated = True
            break
        try:
            flags = ma.get_access_flags_string()
        except Exception:
            flags = None
        methods.append(
            {
                "class": ma.class_name,
                "method": ma.name,
                "descriptor": ma.descriptor,
                "access_flags": flags,
                "is_external": ma.is_external(),
            }
        )
    return {
        "filters": {
            "classname": classname,
            "methodname": methodname,
            "descriptor": descriptor,
            "accessflags": accessflags,
            "no_external": no_external,
        },
        "total": len(methods),
        "truncated": truncated,
        "methods": methods,
    }


def analysis_find_classes_advanced(
    analysis_obj, name: str = ".*", no_external: bool = False, limit: int = 500
) -> dict:
    """
    多维正则类搜索——直接用 androguard 原生 `Analysis.find_classes`，支持类名正则 +
    排除外部类（现有 find-classes 缺 no_external 维度）。

    :param name: 类名正则
    :param no_external: 是否排除外部（Android/第三方未实现）类
    :param limit: 返回上限
    :return: 匹配类列表 + 命中总数
    """
    classes = []
    truncated = False
    for ca in analysis_obj.find_classes(name=name, no_external=no_external):
        if len(classes) >= limit:
            truncated = True
            break
        classes.append(
            {
                "name": ca.name,
                "is_external": ca.is_external(),
                "is_android_api": ca.is_android_api(),
                "method_count": ca.get_nb_methods(),
            }
        )
    return {
        "filters": {"name": name, "no_external": no_external},
        "total": len(classes),
        "truncated": truncated,
        "classes": classes,
    }
