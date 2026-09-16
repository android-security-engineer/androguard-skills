"""
资源解析能力封装。

将 androguard.core.axml.ARSCParser 的方法封装为返回 dict 的函数，
便于 JSON 序列化和 CLI 输出。
"""

from __future__ import annotations

import re
from typing import Union

from loguru import logger


def resource_packages(arsc_obj) -> dict:
    """
    获取资源包名列表。

    :param arsc_obj: ARSCParser 对象
    :return: 包名列表
    """
    if arsc_obj is None:
        return {"error": "No ARSC resources found in APK"}

    packages = arsc_obj.get_packages_names()
    return {"total": len(packages), "packages": packages}


def resource_locales(arsc_obj, package_name: str) -> dict:
    """
    获取指定资源包支持的语言/地区列表。

    :param arsc_obj: ARSCParser 对象
    :param package_name: 资源包名
    :return: 语言列表
    """
    if arsc_obj is None:
        return {"error": "No ARSC resources found in APK"}

    try:
        locales = arsc_obj.get_locales(package_name)
        # 将 \x00\x00 替换为默认标记
        clean_locales = []
        for loc in locales:
            if loc == "\x00\x00":
                clean_locales.append("default")
            else:
                clean_locales.append(loc)
        return {
            "package": package_name,
            "total": len(clean_locales),
            "locales": clean_locales,
        }
    except Exception as e:
        return {"package": package_name, "error": str(e)}


def resource_types(arsc_obj, package_name: str) -> dict:
    """
    获取指定资源包的资源类型列表。

    :param arsc_obj: ARSCParser 对象
    :param package_name: 资源包名
    :return: 资源类型列表
    """
    if arsc_obj is None:
        return {"error": "No ARSC resources found in APK"}

    try:
        types = arsc_obj.get_types(package_name)
        return {
            "package": package_name,
            "total": len(types),
            "types": types,
        }
    except Exception as e:
        return {"package": package_name, "error": str(e)}


def resource_configs(arsc_obj, resource_id: int) -> dict:
    """
    获取指定资源 ID 的所有配置。

    :param arsc_obj: ARSCParser 对象
    :param resource_id: 资源 ID（整型，如 0x7f030000）
    :return: 资源配置列表
    """
    if arsc_obj is None:
        return {"error": "No ARSC resources found in APK"}

    try:
        configs = arsc_obj.get_resolved_res_configs(resource_id)
        config_list = []
        for config, value in configs:
            config_info = {
                "value": str(value) if value is not None else None,
            }
            # 提取配置信息
            if hasattr(config, "get_config"):
                try:
                    cfg = config.get_config()
                    config_info["config"] = str(cfg)
                except Exception:
                    config_info["config"] = str(config)
            else:
                config_info["config"] = str(config)
            config_list.append(config_info)

        return {
            "resource_id": hex(resource_id),
            "total": len(config_list),
            "configs": config_list,
        }
    except Exception as e:
        return {"resource_id": hex(resource_id), "error": str(e)}


def resource_strings(arsc_obj) -> dict:
    """
    获取所有解析后的字符串资源。

    :param arsc_obj: ARSCParser 对象
    :return: 字符串资源
    """
    if arsc_obj is None:
        return {"error": "No ARSC resources found in APK"}

    try:
        resolved = arsc_obj.get_resolved_strings()
        string_list = []
        if isinstance(resolved, dict):
            for pkg, values in resolved.items():
                if isinstance(values, dict):
                    for key, value in values.items():
                        string_list.append(
                            {
                                "package": pkg,
                                "key": str(key),
                                "value": str(value),
                            }
                        )
                elif isinstance(values, list):
                    for item in values:
                        string_list.append(
                            {
                                "package": pkg,
                                "value": str(item),
                            }
                        )
        elif isinstance(resolved, list):
            for item in resolved:
                string_list.append({"value": str(item)})

        return {"total": len(string_list), "strings": string_list}
    except Exception as e:
        return {"error": str(e)}


def _parse_xml_resources(data) -> list:
    """将 ARSC 类型化资源返回的 XML bytes 解析为 (name, value) 列表"""
    if data is None:
        return []
    try:
        if isinstance(data, bytes):
            xml = data.decode("utf-8", errors="replace")
        else:
            xml = str(data)
        items = []
        # 匹配 <tagname name="key">value</tagname>
        for m in re.finditer(r"<(\w+)\s+name=\"([^\"]+)\">([^<]*)</\1>", xml):
            items.append({"name": m.group(2), "value": m.group(3)})
        return items
    except Exception:
        return []


def _typed_resources(
    arsc_obj, package_name: str, getter_name: str, locale: str = "\x00\x00"
) -> dict:
    """通用类型化资源获取"""
    if arsc_obj is None:
        return {"error": "No ARSC resources found in APK"}
    try:
        getter = getattr(arsc_obj, getter_name)
        data = getter(package_name, locale)
        items = _parse_xml_resources(data)
        locale_label = "default" if locale == "\x00\x00" else locale
        return {
            "package": package_name,
            "type": getter_name.replace("_resources", "").replace("get_", ""),
            "locale": locale_label,
            "total": len(items),
            "resources": items,
        }
    except Exception as e:
        return {"package": package_name, "error": str(e)}


def resource_bool(
    arsc_obj, package_name: str, locale: str = "\x00\x00"
) -> dict:
    """获取布尔类型资源"""
    return _typed_resources(
        arsc_obj, package_name, "get_bool_resources", locale
    )


def resource_color(
    arsc_obj, package_name: str, locale: str = "\x00\x00"
) -> dict:
    """获取颜色类型资源"""
    return _typed_resources(
        arsc_obj, package_name, "get_color_resources", locale
    )


def resource_dimen(
    arsc_obj, package_name: str, locale: str = "\x00\x00"
) -> dict:
    """获取尺寸类型资源"""
    return _typed_resources(
        arsc_obj, package_name, "get_dimen_resources", locale
    )


def resource_integer(
    arsc_obj, package_name: str, locale: str = "\x00\x00"
) -> dict:
    """获取整数类型资源"""
    return _typed_resources(
        arsc_obj, package_name, "get_integer_resources", locale
    )


def resource_id(
    arsc_obj,
    package_name: str,
    resource_id: int = None,
    resource_type: str = None,
    key: str = None,
    locale: str = "\x00\x00",
) -> dict:
    """
    资源 ID 双向查询。

    - 传 resource_id：查询 ID 对应的类型和名称
    - 传 resource_type + key：查询名称对应的 ID

    :param arsc_obj: ARSCParser 对象
    :param package_name: 资源包名
    :param resource_id: 资源 ID（整型，用于 ID→名称查询）
    :param resource_type: 资源类型（如 string/color/layout，用于名称→ID 查询）
    :param key: 资源键名
    :param locale: 语言（可选）
    """
    if arsc_obj is None:
        return {"error": "No ARSC resources found in APK"}
    try:
        locale_label = "default" if locale == "\x00\x00" else locale

        if resource_id is not None:
            # ID → 名称
            result = arsc_obj.get_id(package_name, resource_id, locale)
            if result:
                # 返回 (type, key, rid)
                return {
                    "package": package_name,
                    "query": "id_to_name",
                    "resource_id": hex(resource_id),
                    "type": result[0],
                    "key": result[1],
                    "resolved_id": result[2],
                    "xml_name": arsc_obj.get_resource_xml_name(resource_id),
                    "locale": locale_label,
                }
            return {
                "package": package_name,
                "resource_id": hex(resource_id),
                "error": "Resource ID not found",
            }
        elif resource_type and key:
            # 名称 → ID
            rid = arsc_obj.get_res_id_by_key(package_name, resource_type, key)
            if rid is not None:
                return {
                    "package": package_name,
                    "query": "name_to_id",
                    "type": resource_type,
                    "key": key,
                    "resource_id": hex(rid),
                    "decimal_id": rid,
                    "xml_name": arsc_obj.get_resource_xml_name(rid),
                    "locale": locale_label,
                }
            return {
                "package": package_name,
                "type": resource_type,
                "key": key,
                "error": "Resource key not found",
            }
        else:
            return {
                "package": package_name,
                "error": "Provide either resource_id, or resource_type+key",
            }
    except Exception as e:
        return {"package": package_name, "error": str(e)}


def _xml_to_text(data) -> str:
    """将 ARSC 返回的 bytes/str 资源 XML 统一为文本"""
    if data is None:
        return ""
    if isinstance(data, bytes):
        return data.decode("utf-8", errors="replace")
    return str(data)


def _parse_public_resources(data) -> list:
    """解析 public.xml 中的自闭合 <public type= name= id= /> 标签"""
    xml = _xml_to_text(data)
    items = []
    # 匹配 <public type="t" name="n" id="0x..." />
    for m in re.finditer(
        r'<public\s+type="([^"]+)"\s+name="([^"]+)"\s+id="([^"]+)"\s*/?>',
        xml,
    ):
        items.append(
            {
                "type": m.group(1),
                "name": m.group(2),
                "id": m.group(3),
            }
        )
    return items


def resource_string_resources(
    arsc_obj, package_name: str, locale: str = "\x00\x00", raw: bool = False
) -> dict:
    """
    获取指定包+语言的字符串资源（strings.xml）。

    :param arsc_obj: ARSCParser 对象
    :param package_name: 资源包名
    :param locale: 语言（默认为默认资源）
    :param raw: 是否返回原始 XML 文本（而非解析后的列表）
    :return: 字符串资源
    """
    if arsc_obj is None:
        return {"error": "No ARSC resources found in APK"}
    try:
        data = arsc_obj.get_string_resources(package_name, locale)
        locale_label = "default" if locale == "\x00\x00" else locale
        result = {
            "package": package_name,
            "locale": locale_label,
        }
        if raw:
            result["xml"] = _xml_to_text(data)
            return result
        items = _parse_xml_resources(data)
        result["total"] = len(items)
        result["resources"] = items
        return result
    except Exception as e:
        return {"package": package_name, "error": str(e)}


def resource_strings_all(arsc_obj, raw: bool = False) -> dict:
    """
    获取所有包的字符串资源（全量 strings.xml，含多语言）。

    :param arsc_obj: ARSCParser 对象
    :param raw: 是否返回原始 XML 文本
    :return: 全量字符串资源
    """
    if arsc_obj is None:
        return {"error": "No ARSC resources found in APK"}
    try:
        data = arsc_obj.get_strings_resources()
        if raw:
            return {"xml": _xml_to_text(data), "size": len(data)}
        items = _parse_xml_resources(data)
        return {"total": len(items), "resources": items}
    except Exception as e:
        return {"error": str(e)}


def resource_public(
    arsc_obj, package_name: str, locale: str = "\x00\x00", raw: bool = False
) -> dict:
    """
    获取 public.xml（所有资源的 type/name/id 完整映射）。

    :param arsc_obj: ARSCParser 对象
    :param package_name: 资源包名
    :param locale: 语言
    :param raw: 是否返回原始 XML 文本
    :return: public 资源映射列表
    """
    if arsc_obj is None:
        return {"error": "No ARSC resources found in APK"}
    try:
        data = arsc_obj.get_public_resources(package_name, locale)
        locale_label = "default" if locale == "\x00\x00" else locale
        result = {
            "package": package_name,
            "locale": locale_label,
        }
        if raw:
            result["xml"] = _xml_to_text(data)
            return result
        items = _parse_public_resources(data)
        result["total"] = len(items)
        result["resources"] = items
        return result
    except Exception as e:
        return {"package": package_name, "error": str(e)}


def resource_id_resources(
    arsc_obj, package_name: str, locale: str = "\x00\x00", raw: bool = False
) -> dict:
    """
    获取 ids.xml（id 类型资源列表）。

    :param arsc_obj: ARSCParser 对象
    :param package_name: 资源包名
    :param locale: 语言
    :param raw: 是否返回原始 XML 文本
    :return: id 资源列表
    """
    if arsc_obj is None:
        return {"error": "No ARSC resources found in APK"}
    try:
        data = arsc_obj.get_id_resources(package_name, locale)
        locale_label = "default" if locale == "\x00\x00" else locale
        result = {
            "package": package_name,
            "locale": locale_label,
        }
        if raw:
            result["xml"] = _xml_to_text(data)
            return result
        # ids.xml 用 <item type="id" name="x">value</item> 格式
        items = _parse_xml_resources(data)
        result["total"] = len(items)
        result["resources"] = items
        return result
    except Exception as e:
        return {"package": package_name, "error": str(e)}


def resource_get_string(
    arsc_obj, package_name: str, name: str, locale: str = "\x00\x00"
) -> dict:
    """
    按包名+键名+语言精确获取单个字符串资源的值。

    :param arsc_obj: ARSCParser 对象
    :param package_name: 资源包名
    :param name: 字符串资源键名
    :param locale: 语言（默认为默认资源）
    :return: 字符串资源值
    """
    if arsc_obj is None:
        return {"error": "No ARSC resources found in APK"}
    try:
        value = arsc_obj.get_string(package_name, name, locale)
        locale_label = "default" if locale == "\x00\x00" else locale
        # get_string 返回 [name, value] 列表或 None
        if value is None:
            return {
                "package": package_name,
                "name": name,
                "locale": locale_label,
                "error": "String resource not found",
            }
        if isinstance(value, list) and len(value) >= 2:
            return {
                "package": package_name,
                "name": value[0],
                "value": value[1],
                "locale": locale_label,
            }
        return {
            "package": package_name,
            "name": name,
            "value": str(value),
            "locale": locale_label,
        }
    except Exception as e:
        return {"package": package_name, "name": name, "error": str(e)}


def _config_info(cfg) -> dict:
    """将 ARSCResTableConfig 序列化为可读字典"""
    info = {}
    for attr, getter in [
        ("name", "get_config_name_friendly"),
        ("qualifier", "get_qualifier"),
        ("language", "get_language"),
        ("country", "get_country"),
        ("language_and_region", "get_language_and_region"),
        ("density", "get_density"),
        ("is_default", "is_default"),
    ]:
        try:
            v = getattr(cfg, getter)
            info[attr] = v() if callable(v) else v
        except Exception:
            pass
    info["raw"] = str(cfg)
    return info


def resource_xml_name(arsc_obj, resource_id: int, package: str = None) -> dict:
    """
    资源 ID → 可读的 XML 名称（如 @pkg:type/name）。

    与 resource_id（双向查询，需指定方向）的区别：本命令直接给定 rid，
    返回其规范 XML 引用名，适合反编译/manifest 中 @7Fxxxxxx 引用的快速反解。

    :param arsc_obj: ARSCParser 对象
    :param resource_id: 资源 ID（整型，如 0x7f020000）
    :param package: 资源包名（可选，缩小查找范围）
    :return: 资源 ID 对应的 XML 名称
    """
    if arsc_obj is None:
        return {"error": "No ARSC resources found in APK"}
    try:
        xml_name = arsc_obj.get_resource_xml_name(resource_id, package)
        return {
            "resource_id": hex(resource_id),
            "decimal_id": resource_id,
            "xml_name": xml_name,
            "found": xml_name is not None,
        }
    except Exception as e:
        return {"resource_id": hex(resource_id), "error": str(e)}


def resource_type_configs(
    arsc_obj, package_name: str, resource_type: str = None
) -> dict:
    """
    获取资源类型的配置变体列表。

    返回每个资源类型下存在的所有 ARSCResTableConfig（语言/密度/屏幕等变体）。
    例如 type=string 时返回该包 string 资源的所有 locale 配置（default/fa/ja/...）。

    :param arsc_obj: ARSCParser 对象
    :param package_name: 资源包名
    :param resource_type: 资源类型（如 string/color，可选，None 返回全部类型）
    :return: 类型→配置列表映射
    """
    if arsc_obj is None:
        return {"error": "No ARSC resources found in APK"}
    try:
        tc = arsc_obj.get_type_configs(package_name, resource_type)
        types = []
        for t_name, configs in tc.items():
            cfg_list = [_config_info(c) for c in configs]
            types.append(
                {
                    "type": t_name,
                    "total": len(cfg_list),
                    "configs": cfg_list,
                }
            )
        return {
            "package": package_name,
            "filter_type": resource_type,
            "total_types": len(types),
            "types": types,
        }
    except Exception as e:
        return {"package": package_name, "error": str(e)}


def _entry_info(entry) -> dict:
    """将 ARSCResTableEntry 序列化为可读字典（原始资源表项）"""
    info = {}
    for attr in ("idx", "mResId", "flags"):
        try:
            v = getattr(entry, attr, None)
            if v is not None:
                info[attr] = str(v) if not isinstance(v, int) else v
        except Exception:
            pass
    # 布尔标志：是否 public/complex/compact/weak（资源项类型特征）
    for flag_method in ("is_public", "is_complex", "is_compact", "is_weak"):
        try:
            info[flag_method] = bool(
                entry.is_public()
                if flag_method == "is_public"
                else (
                    entry.is_complex()
                    if flag_method == "is_complex"
                    else (
                        entry.is_compact()
                        if flag_method == "is_compact"
                        else entry.is_weak()
                    )
                )
            )
        except Exception:
            pass
    # 值与键名
    try:
        info["value"] = entry.get_value()
    except Exception:
        pass
    try:
        info["key_data"] = entry.get_key_data()
    except Exception:
        pass
    # holding 是 ARSCComplex（父引用、子项计数）
    try:
        holding = getattr(entry, "holding", None)
        if holding is not None:
            complex_info = {}
            for cattr in ("idx", "parent", "count"):
                try:
                    cv = getattr(holding, cattr, None)
                    if cv is not None:
                        complex_info[cattr] = (
                            str(cv) if not isinstance(cv, int) else cv
                        )
                except Exception:
                    pass
            if complex_info:
                info["complex"] = complex_info
    except Exception:
        pass
    return info


def resource_res_configs(
    arsc_obj, resource_id: int, fallback: bool = True
) -> dict:
    """
    按资源 ID 查询配置变体（原始 entry 视图）。

    与 resource_configs（get_resolved_res_configs，返回 cfg+解析值）的区别：
    本命令走 get_res_configs，返回原始 ARSCResTableEntry（含 mResId/flags/complex 父引用），
    适合资源表底层结构分析。每项含 config（locale/密度等）+ entry（原始表项）。

    :param arsc_obj: ARSCParser 对象
    :param resource_id: 资源 ID（整型）
    :param fallback: 找不到精确配置时是否回退到默认配置（默认 True）
    :return: 配置变体列表（含原始 entry）
    """
    if arsc_obj is None:
        return {"error": "No ARSC resources found in APK"}
    try:
        configs = arsc_obj.get_res_configs(resource_id, fallback=fallback)
        config_list = []
        for item in configs:
            # item 是 (ARSCResTableConfig, ARSCResTableEntry) 二元组
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                cfg, entry = item[0], item[1]
                entry_info = _entry_info(entry) if entry is not None else None
            else:
                cfg = item
                entry_info = None
            config_list.append(
                {
                    "config": _config_info(cfg) if cfg is not None else None,
                    "entry": entry_info,
                }
            )
        return {
            "resource_id": hex(resource_id),
            "decimal_id": resource_id,
            "fallback": fallback,
            "total": len(config_list),
            "configs": config_list,
        }
    except Exception as e:
        return {"resource_id": hex(resource_id), "error": str(e)}


def resource_resolved_strings(arsc_obj, locale: str = None) -> dict:
    """
    获取全量解析后的字符串资源（保留 package→locale→rid 三层结构）。

    与 resource_strings（扁平化为 package/key/value，丢失 locale 和 rid）的区别：
    本命令保留完整的 pkg→locale→{rid: value} 嵌套，适合多语言资源全量审计。
    可选 locale 过滤只返回指定语言的字符串。

    :param arsc_obj: ARSCParser 对象
    :param locale: 语言过滤（如 'fa'/'ja'，None 返回全部）
    :return: 三层嵌套的字符串资源
    """
    if arsc_obj is None:
        return {"error": "No ARSC resources found in APK"}
    try:
        resolved = arsc_obj.get_resolved_strings()
        packages = []
        total = 0
        if isinstance(resolved, dict):
            for pkg, locales_dict in resolved.items():
                if not isinstance(locales_dict, dict):
                    continue
                locale_list = []
                for loc, rid_map in locales_dict.items():
                    loc_label = (
                        "default"
                        if loc in ("DEFAULT", "\x00\x00", "")
                        else loc
                    )
                    if (
                        locale is not None
                        and loc_label != locale
                        and loc != locale
                    ):
                        continue
                    entries = []
                    if isinstance(rid_map, dict):
                        for rid, value in rid_map.items():
                            entries.append(
                                {
                                    "rid": (
                                        rid
                                        if isinstance(rid, int)
                                        else str(rid)
                                    ),
                                    "value": (
                                        str(value)
                                        if value is not None
                                        else None
                                    ),
                                }
                            )
                            total += 1
                    elif isinstance(rid_map, (list, tuple)):
                        for item in rid_map:
                            entries.append({"value": str(item)})
                            total += 1
                    locale_list.append(
                        {
                            "locale": loc_label,
                            "total": len(entries),
                            "strings": entries,
                        }
                    )
                packages.append(
                    {
                        "package": pkg,
                        "total_locales": len(locale_list),
                        "locales": locale_list,
                    }
                )
        return {
            "total": total,
            "total_packages": len(packages),
            "filter_locale": locale,
            "packages": packages,
        }
    except Exception as e:
        return {"error": str(e)}


# ================================================================
# 第十四轮：按资源 ID 查配置变体（见上方 resource_res_configs，已实现）
# ================================================================


def resource_value(arsc_obj, resource_id: int, package: str = None) -> dict:
    """
    按资源 ID 取类型化解析值（自动识别 string/bool/int/color/dimen/integer/style/id）。

    与 resources get-string（按名取 string）和 res-configs（entry 元数据）的区别：
    本命令按 rid 自动识别资源类型，调用对应 get_resource_* 返回解析值——如 string
    返回字符串值、bool 返回布尔、color 返回颜色值、dimen 返回尺寸。一次调用拿到
    类型化解析结果，无需先查类型再调对应方法。

    :param arsc_obj: ARSCParser 对象
    :param resource_id: 资源 ID（int 或 hex 字符串）
    :param package: 指定包名（多包 APK 用，默认自动推断）
    :return: 类型化解析值
    """
    try:
        # 解析 rid：支持 int 或 hex/十进制字符串
        if isinstance(resource_id, str):
            rid = (
                int(resource_id, 16)
                if resource_id.lower().startswith("0x")
                else int(resource_id)
            )
        else:
            rid = int(resource_id)
        result = {"resource_id": rid}

        # 用 xml_name 推断类型 (@pkg:type/name)
        xml_name = None
        try:
            xml_name = arsc_obj.get_resource_xml_name(rid, package)
            result["xml_name"] = xml_name
        except Exception:
            pass

        res_type = None
        if xml_name and "/" in xml_name:
            body = xml_name.lstrip("@")
            type_part = body.split("/")[0]
            if ":" in type_part:
                type_part = type_part.split(":")[1]
            res_type = type_part
            result["type"] = res_type

        # 取 entry（用 get_res_configs）
        entry = None
        try:
            rc = arsc_obj.get_res_configs(rid, fallback=True)
            if rc:
                entry = rc[0][1]
                result["config"] = (
                    _config_info(rc[0][0]) if rc[0][0] is not None else None
                )
        except Exception as e:
            result["entry_error"] = str(e)[:80]

        if entry is None:
            result["error"] = "Resource entry not found"
            return result

        # 按类型调对应 get_resource_*，全部尝试并返回第一个成功的解析值
        type_method_map = {
            "string": "get_resource_string",
            "bool": "get_resource_bool",
            "color": "get_resource_color",
            "dimen": "get_resource_dimen",
            "integer": "get_resource_integer",
            "style": "get_resource_style",
            "id": "get_resource_id",
        }

        parsed = {}
        # 优先按推断类型取
        primary_method = type_method_map.get(res_type) if res_type else None
        methods_to_try = []
        if primary_method:
            methods_to_try.append(primary_method)
        # 兜底：尝试所有类型方法（资源可能类型推断不准）
        for m in type_method_map.values():
            if m not in methods_to_try:
                methods_to_try.append(m)

        for method_name in methods_to_try:
            try:
                method = getattr(arsc_obj, method_name)
                val = method(entry)
                if val is not None:
                    # 序列化（可能含嵌套 list/tuple）
                    def _ser(v):
                        if isinstance(v, (list, tuple)):
                            return [_ser(x) for x in v]
                        return v

                    parsed[method_name] = _ser(val)
            except Exception:
                pass

        result["parsed"] = parsed
        # 提取主值（按推断类型的解析结果，取首个元素或原值）
        if primary_method and primary_method in parsed:
            pv = parsed[primary_method]
            if isinstance(pv, list) and pv:
                # string 返回 [key, value]，取 value；其他取末元素
                result["value"] = pv[-1] if len(pv) > 1 else pv[0]
            else:
                result["value"] = pv
        return result
    except Exception as e:
        return {"resource_id": resource_id, "error": str(e)}
