"""
Session 会话能力封装。

将 androguard.misc.Session 的方法封装为返回 dict 的函数。
Session 支持多 APK/DEX 关联分析，可按类查文件名/digest。

与 AndroguardSkillsMain 的单 APK 模式不同，Session 用于：
- 多 APK/DEX 文件关联分析
- 按类定位其所属的 DEX 文件名和摘要
- 全局字符串统计
"""

from __future__ import annotations

import os

from loguru import logger


def session_create() -> dict:
    """
    返回 Session 创建说明（实际 Session 对象由调用方持有）。

    此前此函数内部创建 Session 但只返回字典（对象丢失），调用方又单独
    new 一个，导致两个不相干的 Session 实例——result.is_open 反映的是
    被丢弃的那个。现改为纯说明性返回，Session 对象由 main.session_create
    创建并持有，语义一致。

    :return: 创建结果说明
    """
    return {
        "status": "created",
        "hint": "Session object held by caller; use session add-apk/add-dex to populate",
    }


def session_add_apk(session_obj, filename: str, data: bytes) -> dict:
    """
    向 Session 添加 APK。

    :param session_obj: Session 对象
    :param filename: 文件名
    :param data: APK 原始字节
    :return: 添加结果（含 digest）
    """
    try:
        digest, apk_obj = session_obj.addAPK(filename, data)
        info = {
            "status": "added",
            "filename": filename,
            "digest": digest,
            "package": apk_obj.get_package(),
        }
        try:
            info["is_open"] = session_obj.isOpen()
        except Exception:
            pass
        return info
    except Exception as e:
        return {"filename": filename, "error": str(e)}


def session_add_dex(session_obj, filename: str, data: bytes) -> dict:
    """
    向 Session 添加 DEX。

    :param session_obj: Session 对象
    :param filename: 文件名
    :param data: DEX 原始字节
    :return: 添加结果
    """
    try:
        digest, dex_obj, dx = session_obj.addDEX(filename, data)
        return {
            "status": "added",
            "filename": filename,
            "digest": digest,
            "classes": len(list(dex_obj.get_classes())),
        }
    except Exception as e:
        return {"filename": filename, "error": str(e)}


def session_info(session_obj) -> dict:
    """
    获取 Session 概要信息。

    :param session_obj: Session 对象
    :return: Session 概要
    """
    try:
        apks = list(session_obj.get_all_apks())
        dexes = list(session_obj.get_objects_dex())
        # get_all_apks 返回 (digest, [APK, ...])，APK 列表可能含多个同名实例
        apk_infos = []
        for digest, apk_list in apks:
            for a in apk_list:
                apk_infos.append(
                    {
                        "digest": digest,
                        "package": a.get_package(),
                    }
                )
        return {
            "is_open": session_obj.isOpen(),
            "apk_count": len(apk_infos),
            "dex_count": len(dexes),
            "nb_strings": session_obj.get_nb_strings(),
            "apks": apk_infos,
            "dexes": [{"digest": d} for d, _, _ in dexes],
        }
    except Exception as e:
        return {"error": str(e)}


def session_filename_by_class(session_obj, class_name: str) -> dict:
    """
    查询指定类所属的文件名和摘要。

    Session.get_filename_by_class 返回类首次出现的文件名（APK 场景下返回 APK 文件名
    而非 DEX 文件名）；get_digest_by_class 返回对应摘要。

    :param session_obj: Session 对象
    :param class_name: 类名（格式如 Lcom/example/MyClass;）
    :return: 类所属文件名/摘要
    """
    try:
        # 遍历 session 的 dex 查找类
        results = []
        for dex_digest, d, dx in session_obj.get_objects_dex():
            cls = d.get_class(class_name)
            if cls is not None:
                # get_filename_by_class 内部按 analyzed_digest 查找，返回文件名
                filename = session_obj.get_filename_by_class(cls)
                digest = session_obj.get_digest_by_class(cls)
                fmt = session_obj.get_format(cls)
                results.append(
                    {
                        "class": class_name,
                        "dex_digest": dex_digest,
                        "session_filename": filename,
                        "digest": digest,
                        "format": (
                            type(fmt).__name__ if fmt is not None else None
                        ),
                    }
                )
        if not results:
            return {"class": class_name, "error": "Class not found in session"}
        return {"class": class_name, "total": len(results), "results": results}
    except Exception as e:
        return {"class": class_name, "error": str(e)}


def session_strings(session_obj, limit: int = None) -> dict:
    """
    获取 Session 中各 DEX 的字符串分析。

    Session.get_strings() 返回 (digest, filename, dict[str, StringAnalysis])，
    每个 DEX 一个条目，dict 的 key 是字符串值，value 是 StringAnalysis（含 xref）。

    :param session_obj: Session 对象
    :param limit: 每个 DEX 返回的字符串数量限制
    :return: 各 DEX 的字符串列表
    """
    try:
        dexes = []
        for digest, filename, strings_map in session_obj.get_strings():
            items = []
            for value, sa in strings_map.items():
                xref_from = (
                    sa.get_xref_from()
                    if hasattr(sa, "get_xref_from")
                    else set()
                )
                items.append(
                    {
                        "value": value,
                        "xref_count": (
                            len(xref_from)
                            if hasattr(xref_from, "__len__")
                            else 0
                        ),
                    }
                )
            total = len(items)
            if limit:
                items = items[:limit]
            dexes.append(
                {
                    "digest": digest,
                    "filename": filename,
                    "total": total,
                    "returned": len(items),
                    "strings": items,
                }
            )
        return {"dex_count": len(dexes), "dexes": dexes}
    except Exception as e:
        return {"error": str(e)}


def session_classes(session_obj, limit: int = None) -> dict:
    """
    获取 Session 中的所有类（按 DEX 分组）。

    :param session_obj: Session 对象
    :param limit: 返回数量限制
    :return: 类列表
    """
    try:
        classes = []
        for idx, filename, digest, class_list in session_obj.get_classes():
            classes.append(
                {
                    "index": idx,
                    "filename": filename,
                    "digest": digest,
                    "class_count": len(class_list),
                    "classes": [c.get_name() for c in class_list],
                }
            )
        total = len(classes)
        if limit:
            classes = classes[:limit]
        return {"total": total, "returned": len(classes), "dexes": classes}
    except Exception as e:
        return {"error": str(e)}


def session_analyze_apk(apk_path: str) -> dict:
    """
    用 Session 完整分析一个 APK（封装 create + addAPK + addDEX 流程）。

    这是便捷方法：内部创建 Session，加载 APK 及其所有 DEX，
    返回 Session 概要。返回的 Session 对象可通过 daemon 复用。

    :param apk_path: APK 文件路径
    :return: 分析结果（含 session 概要）
    """
    try:
        from androguard.misc import Session

        if not os.path.exists(apk_path):
            return {"error": f"File not found: {apk_path}"}

        sess = Session()
        with open(apk_path, "rb") as f:
            data = f.read()

        digest, apk_obj = sess.addAPK(apk_path, data)
        # addAPK 内部已自动加载所有 DEX，无需再手动 addDEX
        # 否则会重复加载（nb_strings 翻倍、get_classes 出现重复条目）
        dex_names = list(apk_obj.get_dex_names())

        info = session_info(sess)
        info["status"] = "analyzed"
        info["path"] = apk_path
        info["main_digest"] = digest
        info["dex_count"] = len(dex_names)
        info["dex_names"] = dex_names
        return info
    except Exception as e:
        return {"path": apk_path, "error": str(e)}
