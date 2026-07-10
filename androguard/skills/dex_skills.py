"""
DEX 相关能力封装。

将 androguard.core.dex.DEX 的方法封装为返回 dict 的函数，
便于 JSON 序列化和 CLI 输出。
"""

from __future__ import annotations

import re
from typing import Union

from loguru import logger


def dex_classes(dex_list, filter_regex: str = None) -> dict:
    """
    获取 DEX 中的类列表。

    :param dex_list: DEX 对象列表
    :param filter_regex: 类名过滤正则表达式（可选）
    :return: 类列表信息
    """
    pattern = re.compile(filter_regex) if filter_regex else None
    classes = []

    for dex_obj in dex_list:
        for cls in dex_obj.get_classes():
            name = cls.get_name()
            if pattern and not pattern.search(name):
                continue

            class_info = {
                "name": name,
            }

            # 获取访问标志
            try:
                class_info["access_flags"] = cls.get_access_flags_string()
            except Exception:
                pass

            # 获取父类
            try:
                superclass = cls.get_superclassname()
                if superclass:
                    class_info["superclass"] = superclass
            except Exception:
                pass

            classes.append(class_info)

    return {"total": len(classes), "classes": classes}


def dex_methods(dex_list, class_name: str = None) -> dict:
    """
    获取 DEX 中的方法列表。

    :param dex_list: DEX 对象列表
    :param class_name: 指定类名（可选，格式如 Lcom/example/MyClass;）
    :return: 方法列表信息
    """
    methods = []

    for dex_obj in dex_list:
        for cls in dex_obj.get_classes():
            cls_name = cls.get_name()

            if class_name and cls_name != class_name:
                continue

            for method in cls.get_methods():
                method_info = {
                    "class": cls_name,
                    "name": method.get_name(),
                    "descriptor": method.get_descriptor(),
                    "access_flags": method.get_access_flags_string(),
                }
                methods.append(method_info)

    return {"total": len(methods), "methods": methods}


def dex_strings(dex_list, filter_regex: str = None) -> dict:
    """
    获取 DEX 中的字符串。

    :param dex_list: DEX 对象列表
    :param filter_regex: 字符串过滤正则表达式（可选）
    :return: 字符串列表信息
    """
    pattern = re.compile(filter_regex) if filter_regex else None
    all_strings = []

    for dex_obj in dex_list:
        for s in dex_obj.get_strings():
            if pattern and not pattern.search(s):
                continue
            all_strings.append(s)

    return {"total": len(all_strings), "strings": all_strings}


def dex_fields(dex_list, class_name: str = None) -> dict:
    """
    获取 DEX 中的字段列表。

    :param dex_list: DEX 对象列表
    :param class_name: 指定类名（可选，格式如 Lcom/example/MyClass;）
    :return: 字段列表信息
    """
    fields = []

    for dex_obj in dex_list:
        for cls in dex_obj.get_classes():
            cls_name = cls.get_name()

            if class_name and cls_name != class_name:
                continue

            for field in cls.get_fields():
                field_info = {
                    "class": cls_name,
                    "name": field.get_name(),
                    "access_flags": field.get_access_flags_string(),
                }
                try:
                    field_info["descriptor"] = field.get_descriptor()
                except Exception:
                    pass
                fields.append(field_info)

    return {"total": len(fields), "fields": fields}


def dex_header(dex_obj) -> dict:
    """
    获取 DEX 文件头信息。

    :param dex_obj: DEX 对象
    :return: DEX 头信息
    """
    try:
        header = dex_obj.get_header_item()
        result = {}

        if header is not None:
            # 提取头信息的各个字段
            for attr in dir(header):
                if attr.startswith("get_") and not attr.startswith("get_obj"):
                    try:
                        val = getattr(header, attr)()
                        # 只保留基本类型的值
                        if isinstance(val, (int, str, bytes, bool, type(None))):
                            if isinstance(val, bytes):
                                val = val.hex()
                            result[attr[4:]] = val
                    except Exception:
                        pass

            # 直接访问属性
            for attr in ["magic", "checksum", "signature", "file_size",
                         "header_size", "endian_tag", "link_size", "link_off",
                         "map_off", "string_ids_size", "string_ids_off",
                         "type_ids_size", "type_ids_off",
                         "proto_ids_size", "proto_ids_off",
                         "field_ids_size", "field_ids_off",
                         "method_ids_size", "method_ids_off",
                         "class_defs_size", "class_defs_off",
                         "data_size", "data_off"]:
                try:
                    val = getattr(header, attr, None)
                    if val is not None:
                        if isinstance(val, bytes):
                            val = val.hex()
                        result[attr] = val
                except Exception:
                    pass

        return {"header": result}
    except Exception as e:
        return {"error": str(e)}


def dex_class_names(dex_list) -> dict:
    """
    快速获取 DEX 中的类名列表（不解析整个类）。

    :param dex_list: DEX 对象列表
    :return: 类名列表
    """
    all_names = []
    for dex_obj in dex_list:
        try:
            names = dex_obj.get_classes_names()
            if names:
                all_names.extend(names)
        except Exception:
            # 降级到遍历
            for cls in dex_obj.get_classes():
                all_names.append(cls.get_name())

    return {"total": len(all_names), "classes": all_names}


def dex_hidden_api(dex_obj) -> dict:
    """
    获取 DEX 中的隐藏 API 列表。

    :param dex_obj: DEX 对象
    :return: 隐藏 API 列表
    """
    try:
        hidden = dex_obj.get_hidden_api()
        if hidden is None:
            return {"total": 0, "hidden_api": [], "note": "No hidden API data in this DEX"}

        result = {}
        for attr in dir(hidden):
            if not attr.startswith("_") and not attr.startswith("get_obj"):
                try:
                    val = getattr(hidden, attr)
                    if callable(val):
                        continue
                    if isinstance(val, (list, tuple, set)):
                        result[attr] = list(val)
                    elif isinstance(val, (int, str, bool, type(None))):
                        result[attr] = val
                except Exception:
                    pass

        return {"hidden_api": result}
    except Exception as e:
        return {"error": str(e)}


def dex_disassemble(dex_obj, offset: int, size: int) -> dict:
    """
    反汇编 DEX 指定偏移处的字节码指令。

    :param dex_obj: DEX 对象
    :param offset: 起始偏移（必须是有效代码段偏移，如方法 code_off）
    :param size: 反汇编的字节大小
    :return: 反汇编指令列表
    """
    instructions = []
    error = None
    try:
        for instr in dex_obj.disassemble(offset, size):
            try:
                instructions.append(
                    {
                        "name": instr.get_name(),
                        "output": instr.get_output(),
                        "hex": instr.get_hex(),
                        "length": instr.get_length(),
                    }
                )
            except Exception:
                instructions.append({"error": "Failed to serialize instruction"})
    except Exception as e:
        error = str(e)

    result = {
        "offset": offset,
        "size": size,
        "count": len(instructions),
        "instructions": instructions,
    }
    if error:
        result["error"] = error
        result["note"] = "Disassembly stopped at invalid instruction; partial results returned"
    return result


def dex_hierarchy(dex_list) -> dict:
    """
    获取 DEX 中的类继承层级树。

    :param dex_list: DEX 对象列表
    :return: 继承层级树
    """
    try:
        hierarchy = {}
        for dex_obj in dex_list:
            try:
                h = dex_obj.list_classes_hierarchy()
                if isinstance(h, dict):
                    hierarchy.update(h)
            except Exception:
                pass
        return {"total_roots": len(hierarchy), "hierarchy": hierarchy}
    except Exception as e:
        return {"error": str(e)}


def dex_stats(dex_list) -> dict:
    """
    获取 DEX 统计信息（各类计数、API 版本、格式）。

    :param dex_list: DEX 对象列表
    :return: DEX 统计信息
    """
    try:
        stats_list = []
        for i, dex_obj in enumerate(dex_list):
            stat = {"index": i}
            for attr, getter in [
                ("classes", "get_len_classes"),
                ("methods", "get_len_methods"),
                ("strings", "get_len_strings"),
                ("encoded_fields", "get_len_encoded_fields"),
                ("encoded_methods", "get_len_encoded_methods"),
            ]:
                try:
                    stat[attr] = getattr(dex_obj, getter)()
                except Exception:
                    pass
            try:
                stat["api_version"] = dex_obj.get_api_version()
            except Exception:
                pass
            try:
                stat["format_type"] = dex_obj.get_format_type()
            except Exception:
                pass
            stats_list.append(stat)
        return {"dex_count": len(stats_list), "stats": stats_list}
    except Exception as e:
        return {"error": str(e)}


def dex_class(dex_list, class_name: str) -> dict:
    """
    获取 DEX 中指定类的详细信息。

    :param dex_list: DEX 对象列表
    :param class_name: 类名（格式如 Lcom/example/MyClass;）
    :return: 类详细信息
    """
    try:
        for dex_obj in dex_list:
            cls = dex_obj.get_class(class_name)
            if cls is not None:
                result = {
                    "name": cls.get_name(),
                    "access_flags": cls.get_access_flags_string(),
                }
                try:
                    sname = cls.get_superclassname()
                    if sname:
                        result["superclass"] = sname
                except Exception:
                    pass
                try:
                    result["interfaces"] = list(cls.get_interfaces())
                except Exception:
                    pass
                # dex class 是结构详情命令，不含反编译源码（要源码用
                # `decompile class`，它专门提供等价 source 字段）。此前此处
                # 调 cls.get_source() 返回反编译源码——语义错乱（注释误称
                # "源文件"）且与 decompile class 冗余，移除。
                return result
        return {"class": class_name, "error": "Class not found in DEX"}
    except Exception as e:
        return {"class": class_name, "error": str(e)}


def dex_regex_strings(dex_list, pattern: str) -> dict:
    """
    用正则表达式高效搜索 DEX 中的字符串（底层 C 实现，比全量遍历快）。

    :param dex_list: DEX 对象列表
    :param pattern: 正则表达式
    :return: 匹配的字符串列表
    """
    try:
        all_matches = []
        for dex_obj in dex_list:
            matches = dex_obj.get_regex_strings(pattern)
            if matches:
                all_matches.extend(matches)
        return {"pattern": pattern, "total": len(all_matches), "strings": all_matches}
    except Exception as e:
        return {"pattern": pattern, "error": str(e)}


def dex_debug_info(dex_list, class_name: str = None) -> dict:
    """
    获取 DEX 调试信息（结构化：参数名恢复 + 行号起始 + 调试字节码）。

    :param dex_list: DEX 对象列表
    :param class_name: 指定类名（可选，提取该类所有方法的调试信息）
    :return: 调试信息
    """
    from androguard.core.dex import DebugInfoItem

    try:
        debug_list = []
        for dex_obj in dex_list:
            cm = dex_obj.get_class_manager()
            raw = getattr(dex_obj, "raw", None)
            if class_name:
                cls = dex_obj.get_class(class_name)
                if cls is None:
                    continue
                for method in cls.get_methods():
                    code = method.get_code()
                    if code is None:
                        continue
                    try:
                        dbg_off = code.get_debug_info_off()
                    except Exception:
                        dbg_off = 0
                    if not dbg_off:
                        continue
                    try:
                        # 直接构造 DebugInfoItem 绕过 code.get_debug() 的
                        # 'DEX' object has no attribute 'seek' bug（ClassManager.buff
                        # 被设为 DEX 对象而非 raw BufferedReader）
                        if raw is not None:
                            raw.seek(dbg_off)
                            debug = DebugInfoItem(raw, cm)
                        else:
                            debug = code.get_debug()
                    except Exception:
                        debug = None
                    if debug is None:
                        continue
                    entry = {
                        "method": method.get_name(),
                        "descriptor": method.get_descriptor(),
                    }
                    try:
                        entry["line_start"] = debug.get_line_start()
                    except Exception:
                        pass
                    try:
                        entry["parameters_size"] = debug.get_parameters_size()
                    except Exception:
                        pass
                    try:
                        entry["parameter_names_idx"] = debug.get_parameter_names()
                    except Exception:
                        pass
                    try:
                        entry["translated_parameter_names"] = (
                            debug.get_translated_parameter_names()
                        )
                    except Exception:
                        pass
                    debug_list.append(entry)
            else:
                # 全局：遍历 map_list 的 DEBUG_INFO_ITEM（非类维度）
                try:
                    debug = dex_obj.get_debug_info_item()
                    if debug is not None:
                        debug_list.append({"debug": str(debug)})
                except Exception:
                    pass
        return {"total": len(debug_list), "debug_info": debug_list}
    except Exception as e:
        return {"error": str(e)}


def _encoded_field_info(field) -> dict:
    """将 EncodedField 序列化为可读字典"""
    info = {
        "name": field.get_name(),
        "descriptor": field.get_descriptor(),
        "access_flags": field.get_access_flags_string(),
    }
    try:
        info["class"] = field.get_class_name()
    except Exception:
        pass
    return info


def _encoded_method_info(method) -> dict:
    """将 EncodedMethod 序列化为可读字典"""
    info = {
        "name": method.get_name(),
        "descriptor": method.get_descriptor(),
        "access_flags": method.get_access_flags_string(),
    }
    try:
        info["class"] = method.get_class_name()
    except Exception:
        pass
    try:
        code = method.get_code()
        if code is not None:
            info["code_off"] = code.get_off()
            info["code_size"] = code.get_length()
            info["registers"] = code.get_registers_size()
    except Exception:
        pass
    return info


def dex_encoded_fields(dex_list, class_name: str = None, limit: int = None) -> dict:
    """
    获取 DEX 中的全部 EncodedField（底层字段表）。

    :param dex_list: DEX 对象列表
    :param class_name: 可选，限定某个类的字段
    :param limit: 返回数量限制
    :return: 字段列表
    """
    try:
        fields = []
        for dex_obj in dex_list:
            if class_name:
                items = dex_obj.get_encoded_fields_class(class_name)
            else:
                items = dex_obj.get_encoded_fields()
            fields.extend([_encoded_field_info(f) for f in items])
        total = len(fields)
        if limit:
            fields = fields[:limit]
        return {"total": total, "returned": len(fields), "fields": fields}
    except Exception as e:
        return {"error": str(e)}


def dex_encoded_methods(dex_list, class_name: str = None, limit: int = None) -> dict:
    """
    获取 DEX 中的全部 EncodedMethod（底层方法表）。

    :param dex_list: DEX 对象列表
    :param class_name: 可选，限定某个类的方法
    :param limit: 返回数量限制
    :return: 方法列表
    """
    try:
        methods = []
        for dex_obj in dex_list:
            if class_name:
                items = dex_obj.get_encoded_methods_class(class_name)
            else:
                items = dex_obj.get_encoded_methods()
            methods.extend([_encoded_method_info(m) for m in items])
        total = len(methods)
        if limit:
            methods = methods[:limit]
        return {"total": total, "returned": len(methods), "methods": methods}
    except Exception as e:
        return {"error": str(e)}


def dex_encoded_method(dex_list, method_name: str) -> dict:
    """
    按方法名查找 DEX 中的 EncodedMethod（跨类，返回所有同名方法）。

    :param dex_list: DEX 对象列表
    :param method_name: 方法名
    :return: 匹配的方法列表
    """
    try:
        methods = []
        for dex_obj in dex_list:
            items = dex_obj.get_encoded_method(method_name)
            if items:
                methods.extend([_encoded_method_info(m) for m in items])
        return {
            "method": method_name,
            "total": len(methods),
            "methods": methods,
        }
    except Exception as e:
        return {"method": method_name, "error": str(e)}


def dex_encoded_method_descriptor(
    dex_list, class_name: str, method_name: str, descriptor: str
) -> dict:
    """
    按 class+method+descriptor 精确查找 EncodedMethod（处理重载）。

    :param dex_list: DEX 对象列表
    :param class_name: 类名（格式如 Lcom/example/MyClass;）
    :param method_name: 方法名
    :param descriptor: 方法描述符（如 ()V）
    :return: 匹配的方法
    """
    try:
        for dex_obj in dex_list:
            method = dex_obj.get_encoded_method_descriptor(
                class_name, method_name, descriptor
            )
            if method is not None:
                return {
                    "class": class_name,
                    "method": method_name,
                    "descriptor": descriptor,
                    **_encoded_method_info(method),
                }
        return {
            "class": class_name,
            "method": method_name,
            "descriptor": descriptor,
            "error": "Method not found",
        }
    except Exception as e:
        return {
            "class": class_name,
            "method": method_name,
            "descriptor": descriptor,
            "error": str(e),
        }


def dex_cm_lookup(dex_list, idx: int, kind: str = "string") -> dict:
    """
    按 ID 查询 ClassManager 的常量池表（string/method/field/type）。

    :param dex_list: DEX 对象列表（操作第一个 DEX）
    :param idx: 常量池索引
    :param kind: 查询类型（string/method/field/type）
    :return: 常量池表项
    """
    try:
        if not dex_list:
            return {"error": "No DEX loaded"}
        dex_obj = dex_list[0]
        kind = kind.lower()
        if kind == "string":
            value = dex_obj.get_cm_string(idx)
            return {"idx": idx, "kind": "string", "value": value}
        elif kind == "method":
            value = dex_obj.get_cm_method(idx)
            # 返回 [class, name, [params, return_type]]
            result = {"idx": idx, "kind": "method"}
            if isinstance(value, list) and len(value) >= 3:
                result["class"] = value[0]
                result["name"] = value[1]
                sig = value[2]
                if isinstance(sig, list) and len(sig) >= 2:
                    result["params"] = sig[0]
                    result["return_type"] = sig[1]
                else:
                    result["signature"] = sig
            else:
                result["raw"] = value
            return result
        elif kind == "field":
            value = dex_obj.get_cm_field(idx)
            # 返回 [class, type, name]
            result = {"idx": idx, "kind": "field"}
            if isinstance(value, list) and len(value) >= 3:
                result["class"] = value[0]
                result["type"] = value[1]
                result["name"] = value[2]
            else:
                result["raw"] = value
            return result
        elif kind == "type":
            value = dex_obj.get_cm_type(idx)
            return {"idx": idx, "kind": "type", "value": value}
        else:
            return {"error": f"Unknown kind: {kind}; use string/method/field/type"}
    except Exception as e:
        return {"idx": idx, "kind": kind, "error": str(e)}


def dex_fields_id(dex_list, limit: int = None) -> dict:
    """
    获取 DEX 字段索引表（FieldIdItem 列表，含 class_idx/type_idx/name_idx）。

    :param dex_list: DEX 对象列表（操作第一个 DEX）
    :param limit: 返回数量限制
    :return: 字段索引列表
    """
    try:
        if not dex_list:
            return {"error": "No DEX loaded"}
        dex_obj = dex_list[0]
        fields = []
        for f in dex_obj.get_fields():
            fields.append(
                {
                    "name": f.get_name(),
                    "descriptor": f.get_descriptor(),
                    "class": f.get_class_name(),
                    "type": f.get_type(),
                    "name_idx": f.get_name_idx(),
                    "type_idx": f.get_type_idx(),
                    "class_idx": f.get_class_idx(),
                }
            )
        total = len(fields)
        if limit:
            fields = fields[:limit]
        return {"total": total, "returned": len(fields), "fields": fields}
    except Exception as e:
        return {"error": str(e)}


def dex_version(dex_list) -> dict:
    """
    获取 DEX 版本号。

    :param dex_list: DEX 对象列表
    :return: DEX 版本
    """
    try:
        versions = []
        for dex_obj in dex_list:
            try:
                versions.append(dex_obj.version)
            except Exception:
                pass
        return {
            "dex_count": len(versions),
            "versions": versions,
        }
    except Exception as e:
        return {"error": str(e)}


# ================================================================
# 第六轮：DEX 底层 item 表与计数
# ================================================================


def _item_info(item) -> dict:
    """提取底层 item 的通用信息（offset/length/raw）。"""
    info = {"type": type(item).__name__}
    for prop in ("get_off", "get_length"):
        if hasattr(item, prop):
            try:
                info[prop[4:]] = getattr(item, prop)()
            except Exception as e:
                info[prop[4:]] = f"error: {e}"
    if hasattr(item, "get_raw"):
        try:
            raw = item.get_raw()
            if isinstance(raw, (bytes, bytearray)):
                info["raw_size"] = len(raw)
        except Exception as e:
            info["raw_error"] = str(e)[:80]
    return info


def dex_items(dex_list) -> dict:
    """
    获取 DEX 底层 item 表信息（header/codes/string_data/fields_id/methods_id/classes_def）。

    :param dex_list: DEX 对象列表
    :return: 各 item 表的 offset/length
    """
    try:
        dexes = []
        for d in dex_list:
            entry = {"dex_index": dex_list.index(d) if d in dex_list else 0}
            for name in (
                "get_header_item",
                "get_codes_item",
                "get_string_data_item",
                "get_fields_id_item",
                "get_methods_id_item",
                "get_classes_def_item",
            ):
                key = name.replace("get_", "").replace("_item", "")
                try:
                    item = getattr(d, name)()
                    if isinstance(item, list):
                        entry[key] = {
                            "type": "list",
                            "count": len(item),
                        }
                    else:
                        entry[key] = _item_info(item)
                except Exception as e:
                    entry[key] = {"error": str(e)[:80]}
            dexes.append(entry)
        return {"dex_count": len(dexes), "dexes": dexes}
    except Exception as e:
        return {"error": str(e)}


def dex_lens(dex_list) -> dict:
    """
    获取 DEX 各表的长度（classes/methods/strings/fields/encoded_*）。

    :param dex_list: DEX 对象列表
    :return: 各表计数
    """
    try:
        dexes = []
        for idx, d in enumerate(dex_list):
            entry = {"dex_index": idx}
            for name in (
                "get_len_classes",
                "get_len_methods",
                "get_len_strings",
                "get_len_fields",
                "get_len_encoded_fields",
                "get_len_encoded_methods",
            ):
                key = name.replace("get_len_", "")
                try:
                    entry[key] = getattr(d, name)()
                except Exception as e:
                    entry[key] = f"error: {str(e)[:60]}"
            dexes.append(entry)
        return {"dex_count": len(dexes), "dexes": dexes}
    except Exception as e:
        return {"error": str(e)}


def dex_class_manager(dex_list) -> dict:
    """
    获取 DEX 的 ClassManager 概要信息。

    ClassManager 是 DEX 的常量池管理器（cm-lookup 的底层对象），
    此命令暴露其类型和可用查询方法。

    :param dex_list: DEX 对象列表
    :return: ClassManager 概要
    """
    try:
        dexes = []
        for idx, d in enumerate(dex_list):
            entry = {"dex_index": idx}
            try:
                cm = d.get_class_manager()
                entry["type"] = type(cm).__name__
                methods = sorted(
                    m for m in dir(cm)
                    if not m.startswith("_") and callable(getattr(cm, m, None))
                )
                entry["methods"] = methods
                dexes.append(entry)
            except Exception as e:
                entry["error"] = str(e)
                dexes.append(entry)
        return {"dex_count": len(dexes), "dexes": dexes}
    except Exception as e:
        return {"error": str(e)}


# ================================================================
# 第七轮：DEX 按类 / 按 idx 的 encoded 查询
# ================================================================


def dex_encoded_fields_class(dex_list, class_name: str, limit: int = None) -> dict:
    """
    获取指定类的全部 EncodedField（按类过滤的底层字段表）。

    与 dex_encoded_fields --class 不同：直接调用 DEX.get_encoded_fields_class，
    走类的字段表而非全表过滤，更精确。

    :param dex_list: DEX 对象列表
    :param class_name: 类名（如 Lcom/example/Foo;）
    :param limit: 返回数量限制
    :return: 指定类的字段列表
    """
    try:
        dexes = []
        for idx, d in enumerate(dex_list):
            try:
                fields = d.get_encoded_fields_class(class_name)
                items = [_encoded_field_info(f) for f in fields]
                total = len(items)
                if limit:
                    items = items[:limit]
                dexes.append({
                    "dex_index": idx,
                    "class": class_name,
                    "total": total,
                    "returned": len(items),
                    "fields": items,
                })
            except Exception as e:
                dexes.append({"dex_index": idx, "class": class_name, "error": str(e)[:80]})
        return {"class": class_name, "dex_count": len(dexes), "dexes": dexes}
    except Exception as e:
        return {"error": str(e)}


def dex_encoded_methods_class(dex_list, class_name: str, limit: int = None) -> dict:
    """
    获取指定类的全部 EncodedMethod（按类过滤的底层方法表）。

    :param dex_list: DEX 对象列表
    :param class_name: 类名
    :param limit: 返回数量限制
    :return: 指定类的方法列表
    """
    try:
        dexes = []
        for idx, d in enumerate(dex_list):
            try:
                methods = d.get_encoded_methods_class(class_name)
                items = [_encoded_method_info(m) for m in methods]
                total = len(items)
                if limit:
                    items = items[:limit]
                dexes.append({
                    "dex_index": idx,
                    "class": class_name,
                    "total": total,
                    "returned": len(items),
                    "methods": items,
                })
            except Exception as e:
                dexes.append({"dex_index": idx, "class": class_name, "error": str(e)[:80]})
        return {"class": class_name, "dex_count": len(dexes), "dexes": dexes}
    except Exception as e:
        return {"error": str(e)}


def dex_encoded_method_by_idx(dex_list, idx: int) -> dict:
    """
    按 DEX 内的方法索引获取 EncodedMethod。

    idx 是方法在 DEX method_ids 表中的索引（与 cm-lookup 的 idx 体系一致）。
    注意：idx 在不同 DEX 间不通用。

    :param dex_list: DEX 对象列表
    :param idx: 方法索引
    :return: 方法信息
    """
    try:
        dexes = []
        for di, d in enumerate(dex_list):
            try:
                method = d.get_encoded_method_by_idx(idx)
                if method is not None:
                    dexes.append({
                        "dex_index": di,
                        "idx": idx,
                        "method": _encoded_method_info(method),
                    })
                else:
                    dexes.append({"dex_index": di, "idx": idx, "method": None})
            except Exception as e:
                dexes.append({"dex_index": di, "idx": idx, "error": str(e)[:80]})
        return {"idx": idx, "dex_count": len(dexes), "dexes": dexes}
    except Exception as e:
        return {"error": str(e)}


def dex_encoded_field_by_name(dex_list, name: str, limit: int = None) -> dict:
    """
    按字段名获取 EncodedField（跨类，返回所有匹配）。

    与 dex_encoded_fields --class 不同：此命令按字段名搜索整个 DEX，
    返回所有类中同名字段。

    :param dex_list: DEX 对象列表
    :param name: 字段名
    :param limit: 返回数量限制
    :return: 字段列表
    """
    try:
        dexes = []
        for di, d in enumerate(dex_list):
            try:
                fields = d.get_encoded_field(name)
                items = [_encoded_field_info(f) for f in fields]
                total = len(items)
                if limit:
                    items = items[:limit]
                dexes.append({
                    "dex_index": di,
                    "name": name,
                    "total": total,
                    "returned": len(items),
                    "fields": items,
                })
            except Exception as e:
                dexes.append({"dex_index": di, "name": name, "error": str(e)[:80]})
        return {"name": name, "dex_count": len(dexes), "dexes": dexes}
    except Exception as e:
        return {"error": str(e)}


def dex_encoded_field_descriptor(
    dex_list, class_name: str, field_name: str, descriptor: str
) -> dict:
    """
    按 class+field+descriptor 精确查找 EncodedField（处理同名字段不同类型）。

    与 dex_encoded_field_by_name（按名跨类返回所有同名字段）的区别：
    本命令用 class+field+descriptor 三参数精确查，返回单个 EncodedField，
    适合区分同名但类型不同的字段（如多个 TAG 字段，String vs int）。

    :param dex_list: DEX 对象列表（跨所有 DEX 搜索）
    :param class_name: 类名（如 Lcom/example/Foo;）
    :param field_name: 字段名
    :param descriptor: 字段描述符（如 Ljava/lang/String;）
    :return: 各 DEX 匹配的 EncodedField
    """
    try:
        if not dex_list:
            return {"error": "No DEX loaded"}
        dexes = []
        for di, dex_obj in enumerate(dex_list):
            try:
                name_val = (
                    dex_obj.get_name() if hasattr(dex_obj, "get_name") else f"dex_{di}"
                )
                field = dex_obj.get_encoded_field_descriptor(
                    class_name, field_name, descriptor
                )
                dexes.append({
                    "dex_index": di,
                    "name": name_val,
                    "class": class_name,
                    "field_name": field_name,
                    "descriptor": descriptor,
                    "found": field is not None,
                    "field": _encoded_field_info(field) if field is not None else None,
                })
            except Exception as e:
                dexes.append({"dex_index": di, "error": str(e)[:80]})
        return {
            "class": class_name,
            "field_name": field_name,
            "descriptor": descriptor,
            "dex_count": len(dexes),
            "dexes": dexes,
        }
    except Exception as e:
        return {"error": str(e)}


# ================================================================
# 第十轮：DEX 常量池按名查询 + 类内按名查方法
# ================================================================


def _method_id_info(m) -> dict:
    """将 MethodIdItem 序列化为可读字典（常量池表，含 proto/triple）"""
    info = {
        "name": m.get_name(),
        "descriptor": m.get_descriptor(),
        "class": m.get_class_name(),
    }
    try:
        proto = m.get_proto()
        # get_proto 返回 [params_list, return_type] 二元组
        if isinstance(proto, (list, tuple)):
            info["proto"] = [list(p) if isinstance(p, (list, tuple)) else p for p in proto]
        else:
            info["proto"] = str(proto)
    except Exception:
        pass
    try:
        info["real_descriptor"] = m.get_real_descriptor()
    except Exception:
        pass
    try:
        info["triple"] = [list(t) if isinstance(t, (list, tuple)) else t for t in m.get_triple()]
    except Exception:
        pass
    try:
        info["class_idx"] = m.get_class_idx()
        info["name_idx"] = m.get_name_idx()
        info["proto_idx"] = m.get_proto_idx()
    except Exception:
        pass
    return info


def dex_method_id_by_name(dex_list, name: str, limit: int = None) -> dict:
    """
    在 DEX 常量池（method_ids 表）中按方法名搜索，返回 MethodIdItem 列表。

    与 get_encoded_method（返回含 code 的 EncodedMethod）的区别：
    本命令走常量池 method_ids 表，返回的是声明引用（class/proto/name 三元组），
    包含外部引用的方法（无实现体），适合查"哪些类声明引用了某方法名"。

    注意：AndroGuard 的 DEX.get_method(name) 有 bug（访问不存在的 .name 属性），
    故此处改用 get_methods() 全表 + get_name() 精确过滤。

    :param dex_list: DEX 对象列表（跨所有 DEX 搜索）
    :param name: 方法名（精确匹配）
    :param limit: 每个 DEX 返回数量限制
    :return: 各 DEX 匹配的方法常量池条目
    """
    try:
        if not dex_list:
            return {"error": "No DEX loaded"}
        dexes = []
        for di, dex_obj in enumerate(dex_list):
            try:
                name_val = dex_obj.get_name() if hasattr(dex_obj, "get_name") else f"dex_{di}"
                # get_method(name) 有 bug，改用全表过滤
                all_methods = dex_obj.get_methods() or []
                results = [m for m in all_methods if m.get_name() == name]
                items = [_method_id_info(m) for m in results]
                total = len(items)
                if limit:
                    items = items[:limit]
                dexes.append({
                    "dex_index": di,
                    "name": name_val,
                    "total": total,
                    "returned": len(items),
                    "methods": items,
                })
            except Exception as e:
                dexes.append({"dex_index": di, "error": str(e)[:80]})
        return {"name": name, "dex_count": len(dexes), "dexes": dexes}
    except Exception as e:
        return {"error": str(e)}


def dex_method_ids(dex_list, limit: int = None) -> dict:
    """
    获取 DEX 常量池 method_ids 全量表（MethodIdItem 列表，含外部引用）。

    与 dex_encoded_methods（仅类内定义、含 code_off）的关键区别：
    本命令走常量池 method_ids 表，记录所有被引用的方法声明（含 Framework 外部方法，
    无实现体），适合 DEX 格式分析、常量池枚举、外部依赖统计。

    :param dex_list: DEX 对象列表（跨所有 DEX）
    :param limit: 每个 DEX 返回数量限制
    :return: 各 DEX 的常量池方法条目列表
    """
    try:
        if not dex_list:
            return {"error": "No DEX loaded"}
        dexes = []
        for di, dex_obj in enumerate(dex_list):
            try:
                name_val = dex_obj.get_name() if hasattr(dex_obj, "get_name") else f"dex_{di}"
                all_methods = dex_obj.get_methods() or []
                items = [_method_id_info(m) for m in all_methods]
                total = len(items)
                if limit:
                    items = items[:limit]
                dexes.append({
                    "dex_index": di,
                    "name": name_val,
                    "total": total,
                    "returned": len(items),
                    "methods": items,
                })
            except Exception as e:
                dexes.append({"dex_index": di, "error": str(e)[:80]})
        return {"dex_count": len(dexes), "dexes": dexes}
    except Exception as e:
        return {"error": str(e)}


def dex_field_id_by_name(dex_list, name: str, limit: int = None) -> dict:
    """
    在 DEX 常量池（field_ids 表）中按字段名搜索，返回 FieldIdItem 列表（含外部引用字段）。

    与 dex_encoded_field_by_name（仅类内定义的 EncodedField）的关键区别：
    本命令走常量池 field_ids 表，记录所有被引用的字段声明（含 Framework 外部字段，
    无实现体），适合查"哪些类引用了某同名字段"。

    注意：AndroGuard 的 DEX.get_field(name) 有 bug（访问不存在的 .name 属性，
    与 get_method(name) 同类 bug），故改用 get_fields() 全表 + get_name() 精确过滤。

    :param dex_list: DEX 对象列表（跨所有 DEX 搜索）
    :param name: 字段名（精确匹配）
    :param limit: 每个 DEX 返回数量限制
    :return: 各 DEX 匹配的字段常量池条目
    """
    try:
        if not dex_list:
            return {"error": "No DEX loaded"}
        dexes = []
        for di, dex_obj in enumerate(dex_list):
            try:
                name_val = dex_obj.get_name() if hasattr(dex_obj, "get_name") else f"dex_{di}"
                # get_field(name) 有 bug，改用全表过滤
                all_fields = dex_obj.get_fields() or []
                results = [f for f in all_fields if f.get_name() == name]
                items = [{
                    "name": f.get_name(),
                    "descriptor": f.get_descriptor(),
                    "class": f.get_class_name(),
                    "type": f.get_type(),
                    "name_idx": f.get_name_idx(),
                    "type_idx": f.get_type_idx(),
                    "class_idx": f.get_class_idx(),
                } for f in results]
                total = len(items)
                if limit:
                    items = items[:limit]
                dexes.append({
                    "dex_index": di,
                    "name": name_val,
                    "total": total,
                    "returned": len(items),
                    "fields": items,
                })
            except Exception as e:
                dexes.append({"dex_index": di, "error": str(e)[:80]})
        return {"name": name, "dex_count": len(dexes), "dexes": dexes}
    except Exception as e:
        return {"error": str(e)}


def dex_encoded_method_class_method(dex_list, class_name: str, method_name: str) -> dict:
    """
    在指定类内按方法名查找 EncodedMethod（无需 descriptor，比 descriptor 精确查更宽松）。

    :param dex_list: DEX 对象列表（跨所有 DEX 搜索）
    :param class_name: 类名（如 Lorg/billthefarmer/editor/Editor;）
    :param method_name: 方法名（如 onCreate）
    :return: 匹配的 EncodedMethod 列表
    """
    try:
        if not dex_list:
            return {"error": "No DEX loaded"}
        dexes = []
        for di, dex_obj in enumerate(dex_list):
            try:
                name_val = dex_obj.get_name() if hasattr(dex_obj, "get_name") else f"dex_{di}"
                em = dex_obj.get_encoded_methods_class_method(class_name, method_name)
                if em is not None:
                    dexes.append({
                        "dex_index": di,
                        "name": name_val,
                        "found": True,
                        "method": _encoded_method_info(em),
                    })
                else:
                    dexes.append({
                        "dex_index": di,
                        "name": name_val,
                        "found": False,
                    })
            except Exception as e:
                dexes.append({"dex_index": di, "error": str(e)[:80]})
        return {
            "class": class_name,
            "method": method_name,
            "dex_count": len(dexes),
            "dexes": dexes,
        }
    except Exception as e:
        return {"error": str(e)}


# ================================================================
# 第十四轮：DEX 按类+字段名+描述符精确查 EncodedField
# ================================================================


def dex_encoded_field_descriptor(
    dex_list, class_name: str, field_name: str, descriptor: str
) -> dict:
    """
    按 class+field+descriptor 精确查找 EncodedField（处理同名字段不同类型）。

    与 dex_encoded_field_by_name（按名跨类，返回所有同名）的区别：
    本命令按三参数精确匹配单个字段，适合确认某类某类型字段是否存在。

    :param dex_list: DEX 对象列表（跨所有 DEX 搜索）
    :param class_name: 类名（如 Lcom/example/Foo;）
    :param field_name: 字段名
    :param descriptor: 字段描述符（如 Landroid/widget/EditText;）
    :return: 匹配的 EncodedField
    """
    try:
        if not dex_list:
            return {"error": "No DEX loaded"}
        dexes = []
        for di, dex_obj in enumerate(dex_list):
            try:
                name_val = dex_obj.get_name() if hasattr(dex_obj, "get_name") else f"dex_{di}"
                ef = dex_obj.get_encoded_field_descriptor(class_name, field_name, descriptor)
                if ef is not None:
                    dexes.append({
                        "dex_index": di,
                        "name": name_val,
                        "found": True,
                        "field": _encoded_field_info(ef),
                    })
                else:
                    dexes.append({
                        "dex_index": di,
                        "name": name_val,
                        "found": False,
                    })
            except Exception as e:
                dexes.append({"dex_index": di, "error": str(e)[:80]})
        return {
            "class": class_name,
            "field": field_name,
            "descriptor": descriptor,
            "dex_count": len(dexes),
            "dexes": dexes,
        }
    except Exception as e:
        return {"error": str(e)}


# ================================================================
# 第十六轮：方法寄存器/指令信息
# ================================================================


def _find_encoded_method(dex_list, class_name: str, method_name: str):
    """跨 DEX 按 class+method 查找 EncodedMethod（无需 descriptor，重载返回第一个）。

    返回 (dex_obj, dex_index, dex_name, EncodedMethod) 或 None。
    """
    for di, dex_obj in enumerate(dex_list):
        try:
            cls = dex_obj.get_class(class_name)
            if cls is None:
                continue
            for method in cls.get_methods():
                if method.get_name() == method_name:
                    name_val = (
                        dex_obj.get_name()
                        if hasattr(dex_obj, "get_name")
                        else f"dex_{di}"
                    )
                    return dex_obj, di, name_val, method
        except Exception:
            continue
    return None


def dex_method_info(
    dex_list, class_name: str, method_name: str
) -> dict:
    """
    获取方法的寄存器/参数映射等签名级元信息。

    与 dex_method_detail（analysis 视图，含 xref 统计）和 dex encoded-method
    （底层 EncodedMethod 表项）的区别：本命令用 EncodedMethod.get_information()
    返回方法签名级信息（返回类型、寄存器范围、参数到寄存器映射）+ locals/address/
    code_off/size，适合反汇编上下文理解（哪个寄存器对应哪个参数）。

    :param dex_list: DEX 对象列表（跨所有 DEX 搜索）
    :param class_name: 类名（如 Lcom/example/Foo;）
    :param method_name: 方法名
    :return: 方法签名级信息
    """
    try:
        if not dex_list:
            return {"error": "No DEX loaded"}
        found = _find_encoded_method(dex_list, class_name, method_name)
        if found is None:
            return {
                "class": class_name,
                "method": method_name,
                "error": "Method not found",
            }
        dex_obj, di, name_val, method = found
        info = {
            "class": class_name,
            "method": method_name,
            "dex_index": di,
            "dex_name": name_val,
            "descriptor": method.get_descriptor(),
            "access_flags": method.get_access_flags_string(),
            "full_name": method.full_name,
        }
        # get_information: {return, registers, params}
        try:
            data = method.get_information()
            if isinstance(data, dict):
                info["signature"] = {
                    "return": data.get("return"),
                    "registers": list(data.get("registers", []))
                    if isinstance(data.get("registers"), (list, tuple))
                    else data.get("registers"),
                    "params": [
                        list(p) if isinstance(p, (list, tuple)) else p
                        for p in (data.get("params") or [])
                    ],
                }
        except Exception as e:
            info["signature_error"] = str(e)[:80]
        try:
            info["locals"] = method.get_locals()
        except Exception:
            pass
        try:
            info["address"] = method.get_address()
        except Exception:
            pass
        try:
            info["code_off"] = method.get_code_off()
        except Exception:
            pass
        try:
            # get_length() = 字节码长度（即 code_size，与 code.get_length() 一致）
            info["size"] = method.get_length()
        except Exception:
            pass
        try:
            # get_size() = 方法项自身编码大小（通常很小，如 8 字节）
            info["item_size"] = method.get_size()
        except Exception:
            pass
        try:
            info["short_string"] = method.get_short_string()
        except Exception:
            pass
        try:
            info["method_idx"] = method.get_method_idx()
        except Exception:
            pass
        return info
    except Exception as e:
        return {"class": class_name, "method": method_name, "error": str(e)}


def dex_method_code(
    dex_list, class_name: str, method_name: str
) -> dict:
    """
    获取方法 DalvikCode 的底层信息（寄存器帧 + try/catch 异常表 + handlers）。

    与 dex_method_info（方法签名元信息）和 analysis method-exceptions（分析层
    basic_block 视图的异常表）的区别：本命令直接读 DEX 的 DalvikCode 表项，
    返回寄存器帧尺寸（registers_size/ins_size/outs_size/insns_size）、try 区间
    列表（TryItem: start_addr/insn_count/handler_off）、catch 处理器地址表
    （EncodedCatchHandler: catch_all_addr + 每个 type_idx→handler_addr）、
    debug_info_off，适合 DEX 格式分析、异常处理底层结构定位、与 method-exceptions
    交叉验证。

    :param dex_list: DEX 对象列表（跨所有 DEX 搜索）
    :param class_name: 类名（如 Lcom/example/Foo;）
    :param method_name: 方法名
    :return: 方法 DalvikCode 底层信息
    """
    try:
        if not dex_list:
            return {"error": "No DEX loaded"}
        found = _find_encoded_method(dex_list, class_name, method_name)
        if found is None:
            return {
                "class": class_name,
                "method": method_name,
                "error": "Method not found",
            }
        dex_obj, di, name_val, method = found
        code = method.get_code()
        result = {
            "class": class_name,
            "method": method_name,
            "dex_index": di,
            "dex_name": name_val,
            "descriptor": method.get_descriptor(),
            "has_code": code is not None,
        }
        if code is None:
            # abstract/native 方法无 code
            result["note"] = "Method has no code (abstract/native)"
            return result

        # 寄存器帧信息
        try:
            result["registers_size"] = code.get_registers_size()
            result["ins_size"] = code.get_ins_size()
            result["outs_size"] = code.get_outs_size()
            result["insns_size"] = code.get_insns_size()
        except Exception as e:
            result["frame_error"] = str(e)[:80]

        # 指令字节码长度与偏移
        try:
            result["code_length"] = code.get_length()
            result["code_off"] = code.get_off()
        except Exception:
            pass

        # 调试信息偏移
        try:
            result["debug_info_off"] = code.get_debug_info_off()
        except Exception:
            pass

        # try/catch 异常表（底层 TryItem + EncodedCatchHandler）
        try:
            tries_size = code.get_tries_size()
            result["tries_size"] = tries_size
            tries = code.get_tries() or []
            handlers_list_obj = code.get_handlers()
            # handlers 列表：每个 EncodedCatchHandler 含 catch_all_addr（finally 块地址，
            # 无对应 type 时为 catch-all）+ handlers（type_idx→handler_addr 列表）。
            # 注意：try.get_handler_off() 是相对 handlers 列表起始的字节偏移，
            # 因 EncodedCatchHandler 是变长编码（size 决定长度），精确关联需
            # 按字节累加各 handler 长度，本命令原样输出两者，由调用方按需关联。
            handler_list = []
            if handlers_list_obj is not None:
                raw_handlers = handlers_list_obj.get_list() or []
                for h in raw_handlers:
                    try:
                        off = h.get_off()
                    except Exception:
                        off = None
                    entry = {
                        "handler_off": off,
                        "catch_all_addr": None,
                        "handlers": [],
                    }
                    try:
                        entry["catch_all_addr"] = h.get_catch_all_addr()
                    except Exception:
                        pass
                    try:
                        for tp in (h.get_handlers() or []):
                            entry["handlers"].append({
                                "type_idx": tp.get_type_idx(),
                                "handler_addr": tp.get_addr(),
                            })
                    except Exception:
                        pass
                    handler_list.append(entry)
            result["handlers"] = handler_list

            try_items = []
            for t in tries:
                try:
                    try_items.append({
                        "start_addr": t.get_start_addr(),
                        "insn_count": t.get_insn_count(),
                        "length": t.get_length(),
                        "handler_off": t.get_handler_off(),
                    })
                except Exception:
                    try_items.append({"raw": str(t)[:120]})
            result["tries"] = try_items
        except Exception as e:
            result["tries_error"] = str(e)[:80]

        return result
    except Exception as e:
        return {"class": class_name, "method": method_name, "error": str(e)}


def dex_method_instructions(
    dex_list,
    class_name: str,
    method_name: str,
    limit: int = None,
) -> dict:
    """
    按方法反汇编所有 Dalvik 指令（指令流）。

    与 dex_disassemble（按 offset+size 反汇编任意代码段）的区别：本命令按
    class+method 定位方法，用 EncodedMethod.get_instructions() 返回该方法
    的完整指令流，每条含 offset/name/op_value/hex/output，适合方法级
    完整反汇编、指令模式检测（如检测 invoke-reflection 模式）。

    :param dex_list: DEX 对象列表（跨所有 DEX 搜索）
    :param class_name: 类名（如 Lcom/example/Foo;）
    :param method_name: 方法名
    :param limit: 返回指令数量上限（默认全部）
    :return: 方法指令流
    """
    try:
        if not dex_list:
            return {"error": "No DEX loaded"}
        found = _find_encoded_method(dex_list, class_name, method_name)
        if found is None:
            return {
                "class": class_name,
                "method": method_name,
                "error": "Method not found",
            }
        dex_obj, di, name_val, method = found
        # get_instructions() 返回迭代器，需 list 物化
        try:
            raw_instructions = list(method.get_instructions())
        except Exception as e:
            return {
                "class": class_name,
                "method": method_name,
                "descriptor": method.get_descriptor(),
                "error": f"get_instructions failed: {str(e)[:80]}",
            }
        total = len(raw_instructions)
        sliced = raw_instructions[:limit] if limit else raw_instructions
        instructions = []
        for ins in sliced:
            item = {
                "name": ins.get_name(),
                "output": ins.get_output(),
            }
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
            # 操作数结构化（寄存器/常量池 idx/字面值），比 output 字符串更精确可程序化解析
            try:
                ops = ins.get_operands()
                if ops:
                    ser_ops = []
                    for op in ops:
                        if isinstance(op, (list, tuple)):
                            parts = []
                            for o in op:
                                # Operand 枚举转字符串名；bytes 转 hex；其余原样
                                try:
                                    import enum

                                    if isinstance(o, enum.Enum):
                                        parts.append(o.name)
                                    elif isinstance(o, (bytes, bytearray)):
                                        parts.append(o.hex())
                                    else:
                                        parts.append(o)
                                except Exception:
                                    parts.append(str(o))
                            ser_ops.append(parts)
                        else:
                            ser_ops.append(str(op))
                    item["operands"] = ser_ops
            except Exception:
                pass
            instructions.append(item)
        return {
            "class": class_name,
            "method": method_name,
            "dex_index": di,
            "dex_name": name_val,
            "descriptor": method.get_descriptor(),
            "access_flags": method.get_access_flags_string(),
            "total": total,
            "returned": len(instructions),
            "instructions": instructions,
        }
    except Exception as e:
        return {"class": class_name, "method": method_name, "error": str(e)}


# ================================================================
# 第十九轮：ClassDefItem 底层元信息
# ================================================================


def dex_class_meta(dex_list, class_name: str) -> dict:
    """
    获取 ClassDefItem 的底层元信息（注解/源文件/接口/父类/各表偏移）。

    与 dex class（ClassDefItem 综合信息）和 analysis class-hierarchy-info
    （analysis 视图继承信息）的区别：本命令聚焦 ClassDefItem 层的**底层
    DEX 结构元信息**——类级注解列表、源文件名（混淆检测：混淆后常为 null）、
    接口列表、父类 idx、annotations/class_data/static_values 各表偏移，
    用于 DEX 结构分析和混淆检测。

    :param dex_list: DEX 对象列表（跨所有 DEX 搜索）
    :param class_name: 类名（如 Lcom/example/Foo;）
    :return: ClassDefItem 底层元信息
    """
    try:
        if not dex_list:
            return {"error": "No DEX loaded"}
        for di, dex_obj in enumerate(dex_list):
            try:
                cls = dex_obj.get_class(class_name)
            except Exception:
                cls = None
            if cls is None:
                continue
            cm = dex_obj.get_class_manager()
            name_val = (
                dex_obj.get_name() if hasattr(dex_obj, "get_name") else f"dex_{di}"
            )
            result = {
                "class": class_name,
                "dex_index": di,
                "dex_name": name_val,
            }
            # 类级注解（get_annotations 返回 list[str]）
            try:
                result["annotations"] = list(cls.get_annotations() or [])
            except Exception:
                pass
            # 注解目录：被注解的字段/方法/参数计数（快速判断注解使用密度，
            # 反射框架/DI 框架通常大量使用注解）
            try:
                adi = cls.annotations_directory_item
                if adi is not None:
                    result["annotated_fields_size"] = adi.get_annotated_fields_size()
                    result["annotated_methods_size"] = adi.get_annotated_methods_size()
                    result["annotated_parameters_size"] = adi.get_annotated_parameters_size()
            except Exception:
                pass
            # 源文件名（idx + class_manager 解析）
            try:
                sfi = cls.get_source_file_idx()
                result["source_file_idx"] = sfi
                if sfi is not None and sfi >= 0:
                    try:
                        result["source_file"] = cm.get_string(sfi)
                    except Exception:
                        pass
            except Exception:
                pass
            # 接口列表（已解析为 type 字符串）
            try:
                result["interfaces"] = list(cls.get_interfaces() or [])
            except Exception:
                pass
            # 父类 idx + 解析
            try:
                sci = cls.get_superclass_idx()
                result["superclass_idx"] = sci
                if sci is not None and sci >= 0:
                    try:
                        result["superclass"] = cm.get_type(sci)
                    except Exception:
                        pass
            except Exception:
                pass
            # class idx
            try:
                result["class_idx"] = cls.get_class_idx()
            except Exception:
                pass
            # 各表偏移
            for attr in (
                "annotations_off",
                "class_data_off",
                "static_values_off",
                "interfaces_off",
            ):
                try:
                    getter = getattr(cls, f"get_{attr}")
                    result[attr] = getter()
                except Exception:
                    pass
            return result
        return {"class": class_name, "error": "Class not found in DEX"}
    except Exception as e:
        return {"class": class_name, "error": str(e)}


# ================================================================
# 第二十轮：ClassDataItem 方法/字段分类视图
# ================================================================


def dex_class_data(dex_list, class_name: str, limit: int = None) -> dict:
    """
    获取类的 ClassDataItem 分类视图（direct/virtual 方法 + static/instance 字段）。

    与 dex encoded-methods-class（不区分 direct/virtual）和 dex encoded-fields-class
    （不区分 static/instance）的区别：本命令用 ClassDefItem.get_class_data() 返回
    ClassDataItem，按 DEX 方法定义分类（direct=private/static/构造器不可覆写；
    virtual=可覆写）和字段分类（static=类级；instance=实例级），含各类计数与列表，
    用于理解类的结构布局（如多少构造器、多少可覆写方法）。

    :param dex_list: DEX 对象列表（跨所有 DEX 搜索）
    :param class_name: 类名（如 Lcom/example/Foo;）
    :param limit: 每类列表返回上限（默认全部）
    :return: 方法/字段分类视图
    """
    try:
        if not dex_list:
            return {"error": "No DEX loaded"}
        for di, dex_obj in enumerate(dex_list):
            try:
                cls = dex_obj.get_class(class_name)
            except Exception:
                cls = None
            if cls is None:
                continue
            cd = cls.get_class_data()
            name_val = (
                dex_obj.get_name() if hasattr(dex_obj, "get_name") else f"dex_{di}"
            )
            if cd is None:
                return {
                    "class": class_name,
                    "dex_index": di,
                    "dex_name": name_val,
                    "error": "Class has no ClassData (e.g. marker/abstract w/o body)",
                }
            result = {
                "class": class_name,
                "dex_index": di,
                "dex_name": name_val,
            }
            # 方法分类：direct / virtual
            for kind, getter in (
                ("direct_methods", cd.get_direct_methods),
                ("virtual_methods", cd.get_virtual_methods),
            ):
                try:
                    methods = list(getter() or [])
                    result[f"{kind}_size"] = len(methods)
                    sliced = methods[:limit] if limit else methods
                    result[kind] = [_encoded_method_info(m) for m in sliced]
                except Exception:
                    pass
            # 字段分类：static / instance
            for kind, getter in (
                ("static_fields", cd.get_static_fields),
                ("instance_fields", cd.get_instance_fields),
            ):
                try:
                    fields = list(getter() or [])
                    result[f"{kind}_size"] = len(fields)
                    sliced = fields[:limit] if limit else fields
                    result[kind] = [_encoded_field_info(f) for f in sliced]
                except Exception:
                    pass
            return result
        return {"class": class_name, "error": "Class not found in DEX"}
    except Exception as e:
        return {"class": class_name, "error": str(e)}


# ================================================================
# 第二十一轮：字段初始值 + 带 idx 指令流
# ================================================================


def dex_field_init_value(dex_list, class_name: str, field_name: str) -> dict:
    """
    获取字段的初始值（EncodedField.get_init_value，硬编码常量检测）。

    与 dex encoded-fields（字段表元数据，不含初始值）的区别：本命令用
    EncodedField.get_init_value() 返回 EncodedValue，提取 get_value()
    （原生 Python 值：int/str/None 等）和 get_value_type()（DEX 类型码），
    用于检测硬编码常量（密钥、URL、魔法数等静态字段初始值）。

    :param dex_list: DEX 对象列表（跨所有 DEX 搜索）
    :param class_name: 类名
    :param field_name: 字段名
    :return: 字段初始值
    """
    try:
        if not dex_list:
            return {"error": "No DEX loaded"}
        for di, dex_obj in enumerate(dex_list):
            try:
                cls = dex_obj.get_class(class_name)
            except Exception:
                cls = None
            if cls is None:
                continue
            for f in cls.get_fields():
                if f.get_name() != field_name:
                    continue
                result = {
                    "class": class_name,
                    "field": field_name,
                    "dex_index": di,
                    "descriptor": f.get_descriptor(),
                    "access_flags": f.get_access_flags_string(),
                }
                try:
                    iv = f.get_init_value()
                    if iv is None:
                        result["has_init_value"] = False
                    else:
                        result["has_init_value"] = True
                        try:
                            result["value"] = iv.get_value()
                        except Exception:
                            pass
                        try:
                            result["value_type"] = iv.get_value_type()
                        except Exception:
                            pass
                except Exception as e:
                    result["error"] = f"get_init_value failed: {str(e)[:80]}"
                return result
            return {
                "class": class_name,
                "field": field_name,
                "dex_index": di,
                "error": "Field not found in class",
            }
        return {"class": class_name, "field": field_name, "error": "Class not found in DEX"}
    except Exception as e:
        return {"class": class_name, "field": field_name, "error": str(e)}


def dex_method_instructions_idx(
    dex_list, class_name: str, method_name: str, limit: int = None
) -> dict:
    """
    按方法反汇编所有指令，带字节偏移 idx（get_instructions_idx）。

    与 dex method-instructions（无 idx）的区别：本命令用
    EncodedMethod.get_instructions_idx() 返回 Iterator[(idx, Instruction)]，
    每条指令额外含字节偏移 idx（如 0/6/12，每条指令占 6 字节单位），
    用于精确定位指令在方法内的字节位置（配合 disassemble/method-exceptions 的 offset）。

    :param dex_list: DEX 对象列表（跨所有 DEX 搜索）
    :param class_name: 类名
    :param method_name: 方法名
    :param limit: 返回指令数量上限
    :return: 带 idx 的指令流
    """
    try:
        if not dex_list:
            return {"error": "No DEX loaded"}
        found = _find_encoded_method(dex_list, class_name, method_name)
        if found is None:
            return {
                "class": class_name,
                "method": method_name,
                "error": "Method not found",
            }
        dex_obj, di, name_val, method = found
        try:
            pairs = list(method.get_instructions_idx())
        except Exception as e:
            return {
                "class": class_name,
                "method": method_name,
                "descriptor": method.get_descriptor(),
                "error": f"get_instructions_idx failed: {str(e)[:80]}",
            }
        total = len(pairs)
        sliced = pairs[:limit] if limit else pairs
        instructions = []
        for idx, ins in sliced:
            item = {"idx": idx, "name": ins.get_name(), "output": ins.get_output()}
            try:
                item["op_value"] = ins.get_op_value()
            except Exception:
                pass
            try:
                item["length"] = ins.get_length()
            except Exception:
                pass
            instructions.append(item)
        return {
            "class": class_name,
            "method": method_name,
            "dex_index": di,
            "dex_name": name_val,
            "descriptor": method.get_descriptor(),
            "access_flags": method.get_access_flags_string(),
            "total": total,
            "returned": len(instructions),
            "instructions": instructions,
        }
    except Exception as e:
        return {"class": class_name, "method": method_name, "error": str(e)}


# ================================================================
# 第九轮：Proto / 注解底层结构
# ================================================================


def dex_proto_ids(dex_list, limit: int = None) -> dict:
    """
    获取 DEX 的方法原型表（ProtoIdItem）：每个原型的 shorty 短签名、返回类型、
    参数类型列表（去重的方法签名底层表）。

    与 dex method-ids（方法表，含 class+name+proto_idx）的区别：本命令聚焦
    proto_id_item 表本身——Dalvik 的方法原型去重表，每个原型含 shorty（短签名，
    如 'VBI'，首字符是返回类型首字母，后续是参数类型首字母）、return_type（完整
    返回类型名）、parameters（完整参数类型列表，从 parameters_off 解析的 type_list）。
    用于理解 DEX 方法签名底层布局、参数类型分析、与 method-ids 的 proto_idx 关联。

    :param dex_list: DEX 对象列表
    :param limit: 返回原型数量上限
    :return: 方法原型表
    """
    try:
        if not dex_list:
            return {"error": "No DEX loaded"}
        import struct

        all_protos = []
        for di, dex_obj in enumerate(dex_list):
            try:
                hdr = dex_obj.get_header_item()
                proto_off = hdr.proto_ids_off
                proto_size = hdr.proto_ids_size
            except Exception:
                continue
            if not proto_off or not proto_size:
                continue
            cm = dex_obj.get_class_manager()
            raw = getattr(dex_obj, "raw", None)
            if raw is None:
                continue
            try:
                raw.seek(proto_off)
            except Exception:
                continue
            for idx in range(proto_size):
                try:
                    chunk = raw.read(12)
                    if len(chunk) < 12:
                        break
                    shorty_idx, ret_idx, params_off = struct.unpack("<III", chunk)
                    entry = {
                        "dex_index": di,
                        "proto_idx": idx,
                        "shorty_idx": shorty_idx,
                        "return_type_idx": ret_idx,
                        "parameters_off": params_off,
                    }
                    try:
                        entry["shorty"] = cm.get_string(shorty_idx)
                    except Exception:
                        pass
                    try:
                        entry["return_type"] = cm.get_type(ret_idx)
                    except Exception:
                        pass
                    if params_off:
                        try:
                            entry["parameters"] = cm.get_type_list(params_off)
                        except Exception as e:
                            entry["parameters_error"] = str(e)[:60]
                    else:
                        entry["parameters"] = []
                    all_protos.append(entry)
                except Exception:
                    continue
        total = len(all_protos)
        if limit:
            all_protos = all_protos[:limit]
        return {
            "total": total,
            "returned": len(all_protos),
            "protos": all_protos,
        }
    except Exception as e:
        return {"error": str(e)}


def _encode_value_to_python(ev):
    """递归将 EncodedValue 转为可 JSON 序列化的 Python 值。"""
    if ev is None:
        return None
    try:
        v = ev.get_value()
    except Exception as e:
        return {"encode_error": str(e)[:80]}
    # 基本类型直接返回
    if isinstance(v, (int, float, str, bool, type(None))):
        return v
    if isinstance(v, (bytes, bytearray)):
        return {"bytes_hex": bytes(v).hex()[:200]}
    # EncodedArray / list
    if hasattr(v, "get_value"):
        return _encode_value_to_python(v)
    if hasattr(v, "__iter__") and not isinstance(v, str):
        try:
            items = []
            for it in v:
                if hasattr(it, "get_value"):
                    items.append(_encode_value_to_python(it))
                else:
                    items.append(str(it))
            return items
        except Exception:
            return str(v)[:200]
    return str(v)[:200]


def dex_annotations(dex_list, class_name: str = None, limit: int = None) -> dict:
    """
    获取 DEX 注解目录（AnnotationsDirectoryItem）：类级/字段级/方法级/参数级注解。

    与 dex class-meta（get_annotations 仅返回类级注解类型名列表）的区别：本命令
    深入 AnnotationsDirectoryItem 底层结构——展开每个注解的 visibility（可见性：
    0=BUILD/1=RUNTIME/2=SYSTEM）、type（注解类型，如 Landroid/support/annotation/Nullable;）、
    elements（注解元素，含 name 和 value，value 递归解析 EncodedValue），并按
    class/field/method/parameter 四级分组。用于反射/DI 框架检测（Room/Dagger/Hilt
    注解密度高）、安全审计（@SuppressLint/@GuardedBy/@Keep 等运行时注解）、混淆检测。

    :param dex_list: DEX 对象列表
    :param class_name: 类名（可选，省略则扫描所有有注解的类，可能很大）
    :param limit: 扫描类数量上限（仅 class_name 省略时生效）
    :return: 注解目录
    """
    try:
        if not dex_list:
            return {"error": "No DEX loaded"}

        visibility_names = {0: "BUILD", 1: "RUNTIME", 2: "SYSTEM"}

        def parse_annotation_set(off, cm):
            """从 annotations_off 解析注解列表。"""
            anns = []
            if not off:
                return anns
            try:
                asi = cm.get_annotation_set_item(off)
            except Exception:
                return anns
            if asi is None:
                return anns
            try:
                aoi_list = asi.get_annotation_off_item()
            except Exception:
                return anns
            if aoi_list is None:
                return anns
            for aoi in aoi_list:
                try:
                    ai = aoi.get_annotation_item()
                    if ai is None:
                        continue
                    vis = ai.get_visibility()
                    ann = ai.get_annotation()
                    entry = {"visibility": vis, "visibility_name": visibility_names.get(vis, str(vis))}
                    try:
                        tidx = ann.get_type_idx()
                        entry["type_idx"] = tidx
                        entry["type"] = cm.get_type(tidx)
                    except Exception:
                        pass
                    # 元素
                    elems = []
                    try:
                        for e in ann.get_elements():
                            elem = {}
                            try:
                                elem["name_idx"] = e.get_name_idx()
                                elem["name"] = cm.get_string(e.get_name_idx())
                            except Exception:
                                pass
                            try:
                                elem["value"] = _encode_value_to_python(e.get_value())
                            except Exception as ex:
                                elem["value_error"] = str(ex)[:60]
                            elems.append(elem)
                    except Exception:
                        pass
                    entry["elements"] = elems
                    anns.append(entry)
                except Exception:
                    continue
            return anns

        classes_out = []
        scanned = 0
        for di, dex_obj in enumerate(dex_list):
            try:
                classes = dex_obj.get_classes()
            except Exception:
                continue
            cm = dex_obj.get_class_manager()
            for c in classes:
                cname = None
                try:
                    cname = c.get_name()
                except Exception:
                    continue
                if class_name is not None and cname != class_name:
                    continue
                try:
                    ao = c.get_annotations_off()
                except Exception:
                    ao = 0
                if not ao:
                    if class_name is not None:
                        # 显式查询的类无注解
                        classes_out.append({
                            "class": cname,
                            "dex_index": di,
                            "has_annotations": False,
                        })
                    continue
                try:
                    cdi = c.annotations_directory_item
                except Exception:
                    continue
                if cdi is None:
                    continue
                entry = {
                    "class": cname,
                    "dex_index": di,
                    "has_annotations": True,
                    "annotated_fields_size": cdi.get_annotated_fields_size(),
                    "annotated_methods_size": cdi.get_annotated_methods_size(),
                    "annotated_parameters_size": cdi.get_annotated_parameters_size(),
                }
                # 类级注解
                try:
                    cao = cdi.get_class_annotations_off()
                    entry["class_annotations"] = parse_annotation_set(cao, cm)
                except Exception as e:
                    entry["class_annotations_error"] = str(e)[:60]
                # 字段注解
                field_anns = []
                try:
                    for fa in cdi.get_field_annotations():
                        item = {"annotations": []}
                        try:
                            fidx = fa.get_field_idx()
                            item["field_idx"] = fidx
                            item["field"] = cm.get_field(fidx)
                        except Exception:
                            pass
                        try:
                            item["annotations"] = parse_annotation_set(fa.get_annotations_off(), cm)
                        except Exception as e:
                            item["annotations_error"] = str(e)[:60]
                        field_anns.append(item)
                except Exception:
                    pass
                entry["field_annotations"] = field_anns
                # 方法注解
                method_anns = []
                try:
                    for ma in cdi.get_method_annotations():
                        item = {"annotations": []}
                        try:
                            midx = ma.get_method_idx()
                            item["method_idx"] = midx
                            item["method"] = cm.get_method(midx)
                        except Exception:
                            pass
                        try:
                            item["annotations"] = parse_annotation_set(ma.get_annotations_off(), cm)
                        except Exception as e:
                            item["annotations_error"] = str(e)[:60]
                        method_anns.append(item)
                except Exception:
                    pass
                entry["method_annotations"] = method_anns
                # 参数注解
                param_anns = []
                try:
                    for pa in cdi.get_parameter_annotations():
                        item = {}
                        try:
                            midx = pa.get_method_idx()
                            item["method_idx"] = midx
                            item["method"] = cm.get_method(midx)
                        except Exception:
                            pass
                        try:
                            off = pa.get_annotations_off()
                            item["annotations_off"] = off
                            # 参数注解是 AnnotationSetRefList：
                            # size u4 + N 个 u4 annotations_off（每参数一组 set）
                            import struct as _struct
                            raw = getattr(dex_obj, "raw", None)
                            params = []
                            if raw is not None and off:
                                raw.seek(off)
                                plist_size = _struct.unpack("<I", raw.read(4))[0]
                                for _ in range(plist_size):
                                    poff = _struct.unpack("<I", raw.read(4))[0]
                                    params.append(parse_annotation_set(poff, cm))
                            item["parameter_annotations"] = params
                        except Exception as e:
                            item["parameter_annotations_error"] = str(e)[:60]
                        param_anns.append(item)
                except Exception:
                    pass
                entry["parameter_annotations"] = param_anns
                classes_out.append(entry)
                scanned += 1
                if class_name is None and limit and scanned >= limit:
                    return {"total_scanned": scanned, "classes": classes_out}
            if class_name is not None:
                break
        return {"total_scanned": scanned, "classes": classes_out}
    except Exception as e:
        return {"error": str(e)}


def dex_static_values(dex_list, class_name: str) -> dict:
    """
    获取类的静态值数组（EncodedArray）：一次性返回所有 static 字段的初始值。

    与 field-init-value（单字段查初始值）的区别：本命令展开 ClassDefItem 的
    static_values_off 指向的 EncodedArray，返回类所有 static 字段的初始值列表，
    与 static_fields 顺序一一对应（含 type 码和递归解析的 value）。用于批量检测
    硬编码常量（密钥、URL、魔法数、正则模式等 static final 字段），比逐字段查
    field-init-value 高效。

    :param dex_list: DEX 对象列表
    :param class_name: 类名
    :return: 类静态值数组
    """
    try:
        if not dex_list:
            return {"error": "No DEX loaded"}
        from androguard.core.dex import EncodedArrayItem

        value_type_names = {
            0: "BYTE", 2: "SHORT", 3: "CHAR", 4: "INT", 6: "LONG",
            16: "FLOAT", 17: "DOUBLE", 23: "STRING", 24: "TYPE",
            25: "FIELD", 26: "METHOD", 27: "ENUM", 28: "ARRAY",
            29: "ANNOTATION", 30: "NULL", 31: "BOOLEAN",
        }

        for di, dex_obj in enumerate(dex_list):
            try:
                cls = dex_obj.get_class(class_name)
            except Exception:
                cls = None
            if cls is None:
                continue
            cm = dex_obj.get_class_manager()
            raw = getattr(dex_obj, "raw", None)
            try:
                off = cls.get_static_values_off()
            except Exception:
                off = 0
            if not off or raw is None:
                return {
                    "class": class_name,
                    "dex_index": di,
                    "has_static_values": False,
                    "note": "No static_values table",
                }
            try:
                raw.seek(off)
                ea_item = EncodedArrayItem(raw, cm)
                arr = ea_item.get_value()
            except Exception as e:
                return {
                    "class": class_name,
                    "dex_index": di,
                    "error": f"Failed to read EncodedArray: {str(e)[:80]}",
                }
            values = []
            try:
                evs = arr.get_values()
            except Exception:
                evs = []
            # 配对 static_fields 名（顺序一致）
            field_names = []
            try:
                cd = cls.get_class_data()
                if cd is not None:
                    field_names = [f.get_name() for f in cd.get_static_fields()]
            except Exception:
                pass
            for i, ev in enumerate(evs):
                entry = {}
                if i < len(field_names):
                    entry["field"] = field_names[i]
                try:
                    vt = ev.get_value_type()
                    entry["value_type"] = vt
                    entry["value_type_name"] = value_type_names.get(vt, str(vt))
                except Exception:
                    pass
                try:
                    entry["value"] = _encode_value_to_python(ev)
                except Exception as e:
                    entry["value_error"] = str(e)[:60]
                values.append(entry)
            return {
                "class": class_name,
                "dex_index": di,
                "has_static_values": True,
                "static_values_off": off,
                "count": len(values),
                "values": values,
            }
        return {"class": class_name, "error": "Class not found in DEX"}
    except Exception as e:
        return {"class": class_name, "error": str(e)}


# ================================================================
# 第十轮：字符串常量池完整表（带偏移）
# ================================================================


def dex_strings_table(dex_list, filter_regex: str = None, limit: int = None) -> dict:
    """
    字符串常量池完整表（idx + 值 + 字节偏移 + UTF-16 长度）。

    与 dex strings（仅返回字符串值列表，无定位信息）的区别：本命令返回每个
    字符串在 DEX 二进制中的精确位置（string_data_item 偏移）和 UTF-16 字符数，
    用于：
      - 定位字符串在 DEX 二进制中的偏移（patch/比较/脱壳后比对）
      - 字符串混淆检测（utf16_size 与解码值长度不一致，或 offset 异常）
      - 跨 DEX 字符串偏移映射

    :param dex_list: DEX 对象列表
    :param filter_regex: 字符串过滤正则（可选）
    :param limit: 返回条目上限（默认全部）
    :return: 字符串常量池表
    """
    import re

    pattern = re.compile(filter_regex) if filter_regex else None
    entries = []

    for dex_idx, dex_obj in enumerate(dex_list):
        try:
            cm = dex_obj.get_class_manager()
            sdi = dex_obj.get_string_data_item()
        except Exception:
            continue
        if not sdi:
            continue
        for idx, item in enumerate(sdi):
            try:
                value = cm.get_string(idx)
            except Exception:
                value = None
            if pattern and (value is None or not pattern.search(value)):
                continue
            entries.append({
                "dex_index": dex_idx,
                "string_idx": idx,
                "value": value,
                "offset": getattr(item, "offset", None),
                "utf16_size": getattr(item, "utf16_size", None),
            })
            if limit is not None and len(entries) >= limit:
                break
        if limit is not None and len(entries) >= limit:
            break

    return {"total": len(entries), "strings": entries}


# ================================================================
# 第十一轮：类型常量池（type_ids）
# ================================================================


def dex_type_ids(dex_list, limit: int = None) -> dict:
    """
    类型常量池表（type_ids）—— DEX 中所有类型描述符的索引表。

    与 dex fields-id/method-ids/proto-ids（引用类型 idx 的常量池表）的区别：
    本命令是类型描述符表本身——type_idx → descriptor_idx(指向 string_ids) →
    类型描述符（如 B/C/I/J/Z 基本类型，或 Lcom/example/Foo; 类类型，或 [I 数组）。
    是 DEX 四大基础常量池（string/type/proto/field/method）之一，proto-ids 的
    return_type/parameters 均引用此表。

    :param dex_list: DEX 对象列表
    :param limit: 返回条目上限（默认全部）
    :return: 类型常量池表
    """
    import struct

    entries = []
    for dex_idx, dex_obj in enumerate(dex_list):
        try:
            cm = dex_obj.get_class_manager()
            hdr = dex_obj.get_header_item()
            off = hdr.type_ids_off
            size = hdr.type_ids_size
            raw = dex_obj.raw
            if not off or not size:
                continue
            raw.seek(off)
            for type_idx in range(size):
                b = raw.read(4)
                if len(b) < 4:
                    break
                descriptor_idx = struct.unpack("<I", b)[0]
                try:
                    descriptor = cm.get_string(descriptor_idx)
                except Exception:
                    descriptor = None
                entries.append({
                    "dex_index": dex_idx,
                    "type_idx": type_idx,
                    "descriptor_idx": descriptor_idx,
                    "descriptor": descriptor,
                })
                if limit is not None and len(entries) >= limit:
                    break
        except Exception as e:
            entries.append({"dex_index": dex_idx, "error": str(e)})
        if limit is not None and len(entries) >= limit:
            break

    return {"total": len(entries), "type_ids": entries}
