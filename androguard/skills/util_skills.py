"""
工具能力封装。

将 androguard.util 和 androguard.core.androconf 的方法封装为返回 dict 的函数，
便于 JSON 序列化和 CLI 输出。
"""

from __future__ import annotations

from loguru import logger


def util_detect_file(filename: str) -> dict:
    """
    检测文件的 Android 类型（APK/DEX/ODEX/ELF 等）。

    :param filename: 文件路径
    :return: 文件类型字符串
    """
    try:
        from androguard.core import androconf

        ftype = androconf.is_android(filename)
        return {"filename": filename, "type": ftype}
    except Exception as e:
        return {"filename": filename, "error": str(e)}


def util_detect_raw(data: bytes) -> dict:
    """
    检测原始字节的 Android 类型。

    :param data: 原始字节（base64 解码后）
    :return: 文件类型字符串
    """
    try:
        from androguard.core import androconf

        ftype = androconf.is_android_raw(data)
        return {"size": len(data), "type": ftype}
    except Exception as e:
        return {"error": str(e)}


def util_permissions(apilevel) -> dict:
    """
    加载指定 API level 的 AOSP 权限定义。

    :param apilevel: API level（整数或字符串，如 35）
    :return: 权限名 → {description, label, ...} 映射
    """
    try:
        from androguard.core import androconf

        perms = androconf.load_permissions(apilevel)
        return {
            "apilevel": apilevel,
            "total": len(perms),
            "permissions": perms,
        }
    except Exception as e:
        return {"apilevel": apilevel, "error": str(e)}


def util_permission_mappings(apilevel) -> dict:
    """
    加载指定 API level 的方法签名 → 权限映射。

    :param apilevel: API level（整数或字符串，如 23）
    :return: 方法签名 → [权限列表] 映射
    """
    try:
        from androguard.core import androconf

        mappings = androconf.load_permission_mappings(apilevel)
        return {
            "apilevel": apilevel,
            "total": len(mappings),
            "mappings": mappings,
        }
    except Exception as e:
        return {"apilevel": apilevel, "error": str(e)}


def util_certificate_name_string(name_obj, short: bool = True) -> dict:
    """
    将 asn1crypto Name 对象格式化为可读字符串。

    通常通过 daemon 或 Python API 调用（CLI 层面证书名已在证书命令中解析）。
    """
    try:
        from androguard.util import get_certificate_name_string

        return {
            "name": get_certificate_name_string(name_obj, short=short),
            "short": short,
        }
    except Exception as e:
        return {"error": str(e)}


def util_calculate_fingerprint(public_key_info) -> dict:
    """
    计算公钥的 SHA-256 指纹。

    :param public_key_info: asn1crypto PublicKeyInfo 对象
    :return: 指纹（hex + base64）
    """
    try:
        import base64
        import hashlib

        from androguard.util import calculate_fingerprint

        fp_bytes = calculate_fingerprint(public_key_info)
        return {
            "algorithm": "sha256",
            "fingerprint_hex": fp_bytes.hex(),
            "fingerprint_base64": base64.b64encode(fp_bytes).decode("ascii"),
            "size": len(fp_bytes),
        }
    except Exception as e:
        return {"error": str(e)}


def util_available_api_levels() -> dict:
    """
    列出本地可用的权限数据 API level。

    数据位于 androguard/core/api_specific_resources/ 下。

    :return: 可用的 API level 列表
    """
    try:
        import os
        import re

        from androguard.core import androconf

        root = os.path.dirname(os.path.realpath(androconf.__file__))
        levels = {"permissions": [], "permission_mappings": []}

        # 权限数据实际在 api_specific_resources 下
        # load_permissions 内部会查找，这里直接扫描两个可能位置
        search_dirs = [
            ("permissions", os.path.join(root, "aosp_permissions")),
            (
                "permissions",
                os.path.join(
                    root, "api_specific_resources", "aosp_permissions"
                ),
            ),
            (
                "permission_mappings",
                os.path.join(root, "api_permission_mappings"),
            ),
            (
                "permission_mappings",
                os.path.join(
                    root, "api_specific_resources", "api_permission_mappings"
                ),
            ),
        ]
        found_dirs = set()
        for key, d in search_dirs:
            if d in found_dirs:
                continue
            if os.path.isdir(d):
                found_dirs.add(d)
                for f in os.listdir(d):
                    m = re.match(r"^permissions_(\d+)\.json$", f)
                    if m:
                        lv = int(m.group(1))
                        if lv not in levels[key]:
                            levels[key].append(lv)

        levels["permissions"].sort()
        levels["permission_mappings"].sort()
        return levels
    except Exception as e:
        return {"error": str(e)}


def util_format(value: str, to: str = "java") -> dict:
    """
    Dalvik/Java 类名与描述符格式双向转换。

    AndroGuard 内置的 FormatClassToJava/FormatClassToPython 有 bug（Python 版
    截断类名、FormatNameToPython 不转换），本命令自实现清晰的格式转换：
    - java：→ Java 类名（com.foo.Bar），自动去除 Dalvik 的 L/; 包裹
    - dalvik：→ Dalvik 类名（Lcom/foo/Bar;），自动加 L/; 并将 . 换 /
    - python：→ Python 标识符（com_foo_Bar，/ 和 . 换 _，去 L/;）

    支持自动识别输入格式（含 L/; 为 Dalvik，含 . 为 Java，含 / 为路径）。

    :param value: 待转换的类名/描述符
    :param to: 目标格式（java/dalvik/python，默认 java）
    :return: 转换结果
    """
    try:
        v = value.strip()
        # 描述符场景（含括号，如 (Landroid/os/Bundle;)V）单独处理
        is_descriptor = v.startswith("(") or ")" in v

        def to_java(cls: str) -> str:
            # 去 L/;，/ 换 .
            c = cls
            if c.startswith("L") and c.endswith(";") and len(c) > 2:
                c = c[1:-1]
            return c.replace("/", ".")

        def to_dalvik(cls: str) -> str:
            c = cls
            if c.startswith("L") and c.endswith(";"):
                return c  # 已是 dalvik
            c = c.replace(".", "/")
            if not c.startswith("L") and not c.endswith(";"):
                # 仅当像类名（含 / 或大写）才包裹
                if "/" in c or any(ch.isupper() for ch in c):
                    c = "L" + c + ";"
            return c

        def to_python(cls: str) -> str:
            c = cls
            if c.startswith("L") and c.endswith(";") and len(c) > 2:
                c = c[1:-1]
            return (
                c.replace("/", "_")
                .replace(".", "_")
                .replace("[", "array_")
                .replace(";", "")
            )

        if is_descriptor:
            # 描述符级转换：逐类型替换
            if to == "python":
                result = v.replace("/", "_").replace(".", "_")
            else:
                result = v  # 描述符 java/dalvik 同形
            return {
                "input": value,
                "to": to,
                "output": result,
                "note": "descriptor (unchanged for java/dalvik)",
            }

        if to == "java":
            out = to_java(v)
        elif to == "dalvik":
            out = to_dalvik(v)
        elif to == "python":
            out = to_python(v)
        else:
            return {
                "input": value,
                "error": f"Unknown target format: {to} (use java/dalvik/python)",
            }

        return {
            "input": value,
            "to": to,
            "output": out,
        }
    except Exception as e:
        return {"input": value, "error": str(e)}
