"""
APK 相关能力封装。

将 androguard.core.apk.APK 的方法封装为返回 dict 的函数，
便于 JSON 序列化和 CLI 输出。
"""

from __future__ import annotations

import base64
import hashlib
from typing import Union

from loguru import logger


def apk_info(apk_obj) -> dict:
    """
    获取 APK 基本信息。

    :param apk_obj: androguard.core.apk.APK 对象
    :return: 包含基本信息的字典
    """
    return {
        "package": apk_obj.get_package(),
        "app_name": apk_obj.get_app_name(),
        "version_code": apk_obj.get_androidversion_code(),
        "version_name": apk_obj.get_androidversion_name(),
        "min_sdk": apk_obj.get_min_sdk_version(),
        "target_sdk": apk_obj.get_target_sdk_version(),
        "max_sdk": apk_obj.get_max_sdk_version(),
        "effective_target_sdk": apk_obj.get_effective_target_sdk_version(),
        "is_multidex": apk_obj.is_multidex(),
        "is_valid": apk_obj.is_valid_APK(),
        "is_wearable": apk_obj.is_wearable(),
        "is_leanback": apk_obj.is_leanback(),
        "is_androidtv": apk_obj.is_androidtv(),
        "dex_names": apk_obj.get_dex_names(),
        "main_activity": apk_obj.get_main_activity(),
    }


def apk_permissions(apk_obj) -> dict:
    """
    获取 APK 权限信息。

    :param apk_obj: androguard.core.apk.APK 对象
    :return: 包含权限详情的字典

    注：get_permissions()/get_requested_aosp_permissions() 等底层由 set 转 list，
    且 get_details_permissions()/get_*_permissions_details() 返回的 dict key 插入序
    来自 set 迭代——同一 APK 多次加载顺序不同，导致字节级 JSON 输出非确定。
    对 list 排序、对 dict 按 key 重建，固定输出，让 agent 对接能稳定比对。
    """
    def _sorted_dict(d):
        """按 key 排序重建 dict，固定 JSON key 顺序（dict 来自 set 构建，key 序非确定）。"""
        if not isinstance(d, dict):
            return d
        return {k: d[k] for k in sorted(d.keys())}

    return {
        "permissions": sorted(apk_obj.get_permissions()),
        "details_permissions": _sorted_dict(apk_obj.get_details_permissions()),
        "uses_implied_permissions": sorted(apk_obj.get_uses_implied_permission_list()),
        "requested_aosp_permissions": sorted(apk_obj.get_requested_aosp_permissions()),
        "requested_aosp_permissions_details": _sorted_dict(apk_obj.get_requested_aosp_permissions_details()),
        "requested_third_party_permissions": sorted(apk_obj.get_requested_third_party_permissions()),
        "declared_permissions": sorted(apk_obj.get_declared_permissions()),
        "declared_permissions_details": _sorted_dict(apk_obj.get_declared_permissions_details()),
    }


def apk_activities(apk_obj) -> dict:
    """
    获取 APK Activity 列表。

    :param apk_obj: androguard.core.apk.APK 对象
    :return: Activity 列表信息

    注：get_activities()/get_main_activities() 底层由 set 转 list，迭代序非确定；
    get_intent_filters() 返回的 dict key 亦来自 set。排序 list + 按 key 重建 dict，
    固定字节级输出（agent 对接需确定性）。
    """
    activities = sorted(apk_obj.get_activities())
    main_activities = sorted(apk_obj.get_main_activities())
    activity_aliases = sorted(apk_obj.get_activity_aliases())

    result = {
        "activities": activities,
        "main_activities": main_activities,
        "activity_aliases": activity_aliases,
    }

    # 为每个 Activity 获取 intent-filter（按 activity 名序遍历 + dict 按 key 重建）
    activity_filters = {}
    for activity in activities:
        filters = apk_obj.get_intent_filters("activity", activity)
        if filters:
            activity_filters[activity] = {
                k: filters[k] for k in sorted(filters.keys())
            }
    result["intent_filters"] = activity_filters

    return result


def apk_services(apk_obj) -> dict:
    """
    获取 APK Service 列表。

    :param apk_obj: androguard.core.apk.APK 对象
    :return: Service 列表信息（同 activities 的确定性处理）
    """
    services = sorted(apk_obj.get_services())
    result = {"services": services}

    # 为每个 Service 获取 intent-filter（按 service 名序遍历 + dict 按 key 重建）
    service_filters = {}
    for service in services:
        filters = apk_obj.get_intent_filters("service", service)
        if filters:
            service_filters[service] = {
                k: filters[k] for k in sorted(filters.keys())
            }
    result["intent_filters"] = service_filters

    return result


def apk_receivers(apk_obj) -> dict:
    """
    获取 APK BroadcastReceiver 列表。

    :param apk_obj: androguard.core.apk.APK 对象
    :return: Receiver 列表信息（同 activities 的确定性处理）
    """
    receivers = sorted(apk_obj.get_receivers())
    result = {"receivers": receivers}

    # 为每个 Receiver 获取 intent-filter（按 receiver 名序遍历 + dict 按 key 重建）
    receiver_filters = {}
    for receiver in receivers:
        filters = apk_obj.get_intent_filters("receiver", receiver)
        if filters:
            receiver_filters[receiver] = {
                k: filters[k] for k in sorted(filters.keys())
            }
    result["intent_filters"] = receiver_filters

    return result


def apk_providers(apk_obj) -> dict:
    """
    获取 APK ContentProvider 列表。

    :param apk_obj: androguard.core.apk.APK 对象
    :return: Provider 列表信息
    """
    providers = sorted(apk_obj.get_providers())
    result = {"providers": providers}

    # 为每个 Provider 获取 intent-filter（按 provider 名序遍历 + dict 按 key 重建）
    provider_filters = {}
    for provider in providers:
        filters = apk_obj.get_intent_filters("provider", provider)
        if filters:
            provider_filters[provider] = {
                k: filters[k] for k in sorted(filters.keys())
            }
    result["intent_filters"] = provider_filters

    return result


def apk_intent_filters(apk_obj, component_name: str) -> dict:
    """
    获取指定组件的 Intent Filter。

    :param apk_obj: androguard.core.apk.APK 对象
    :param component_name: 组件名称（完整类名）
    :return: Intent Filter 信息
    """
    # 尝试在所有组件类型中查找
    component_type = None
    for ctype in ["activity", "service", "receiver", "provider"]:
        components = {
            "activity": apk_obj.get_activities(),
            "service": apk_obj.get_services(),
            "receiver": apk_obj.get_receivers(),
            "provider": apk_obj.get_providers(),
        }
        if component_name in components.get(ctype, []):
            component_type = ctype
            break

    if component_type is None:
        return {
            "component": component_name,
            "error": f"Component '{component_name}' not found in APK",
        }

    filters = apk_obj.get_intent_filters(component_type, component_name)
    return {
        "component": component_name,
        "type": component_type,
        "intent_filters": filters,
    }


def apk_signature(apk_obj) -> dict:
    """
    获取 APK 签名信息。

    :param apk_obj: androguard.core.apk.APK 对象
    :return: 签名信息字典
    """
    result = {
        "is_signed": apk_obj.is_signed(),
        "is_signed_v1": apk_obj.is_signed_v1(),
        "is_signed_v2": apk_obj.is_signed_v2(),
        "is_signed_v3": apk_obj.is_signed_v3(),
        "is_signed_v31": apk_obj.is_signed_v31(),
        "signature_names": apk_obj.get_signature_names(),
    }

    # 证书指纹
    certs_info = []
    try:
        certs_der = set()

        # v1 证书通过 get_certificates_v1() 获取 asn1crypto.x509.Certificate 对象
        try:
            for cert in apk_obj.get_certificates_v1():
                if cert is not None:
                    certs_der.add(cert.dump())
        except Exception:
            pass

        # v2/v3/v31 证书通过 get_certificates_der_*() 获取 DER 字节
        for getter_name in [
            "get_certificates_der_v2",
            "get_certificates_der_v3",
            "get_certificates_der_v31",
        ]:
            try:
                getter = getattr(apk_obj, getter_name, None)
                if getter is not None:
                    for der in getter():
                        certs_der.add(der)
            except Exception:
                pass

        for cert_der in certs_der:
            cert_info = {
                "sha1": hashlib.sha1(cert_der).hexdigest(),
                "sha256": hashlib.sha256(cert_der).hexdigest(),
                "md5": hashlib.md5(cert_der).hexdigest(),
            }

            # 尝试解析证书详情
            try:
                from asn1crypto import x509
                from androguard.util import get_certificate_name_string

                x509_cert = x509.Certificate.load(cert_der)
                cert_info["issuer"] = get_certificate_name_string(
                    x509_cert.issuer, short=True
                )
                cert_info["subject"] = get_certificate_name_string(
                    x509_cert.subject, short=True
                )
                cert_info["serial_number"] = hex(x509_cert.serial_number)
                cert_info["hash_algorithm"] = x509_cert.hash_algo
                cert_info["signature_algorithm"] = x509_cert.signature_algo
                cert_info["valid_not_before"] = str(
                    x509_cert["tbs_certificate"]["validity"][
                        "not_before"
                    ].native
                )
                cert_info["valid_not_after"] = str(
                    x509_cert["tbs_certificate"]["validity"][
                        "not_after"
                    ].native
                )
            except Exception as e:
                cert_info["parse_error"] = str(e)

            certs_info.append(cert_info)
    except Exception as e:
        result["certs_error"] = str(e)

    result["certificates"] = certs_info
    return result


def apk_files(apk_obj) -> dict:
    """
    获取 APK 文件列表。

    :param apk_obj: androguard.core.apk.APK 对象
    :return: 文件列表信息
    """
    files = apk_obj.get_files()
    files_types = apk_obj.get_files_types()
    files_crc32 = apk_obj.get_files_crc32()

    file_list = []
    for f in files:
        file_list.append(
            {
                "name": f,
                "type": files_types.get(f, "unknown"),
                "crc32": hex(files_crc32.get(f, 0)),
            }
        )

    return {"total": len(file_list), "files": file_list}


def apk_manifest(apk_obj) -> dict:
    """
    获取 AndroidManifest.xml 内容。

    :param apk_obj: androguard.core.apk.APK 对象
    :return: Manifest XML 字符串
    """
    from lxml import etree

    try:
        xml_obj = apk_obj.get_android_manifest_xml()
        if xml_obj is not None:
            xml_str = etree.tostring(
                xml_obj, pretty_print=True, encoding="unicode"
            )
            return {"manifest": xml_str}
        else:
            return {"error": "Failed to parse AndroidManifest.xml"}
    except Exception as e:
        return {"error": f"Error parsing manifest: {str(e)}"}


def apk_features(apk_obj) -> dict:
    """
    获取 APK uses-feature 列表。

    :param apk_obj: androguard.core.apk.APK 对象
    :return: feature 列表
    """
    features = apk_obj.get_features()
    return {
        "total": len(features),
        "features": features,
    }


def apk_libraries(apk_obj) -> dict:
    """
    获取 APK uses-library 列表。

    :param apk_obj: androguard.core.apk.APK 对象
    :return: library 列表
    """
    libraries = apk_obj.get_libraries()
    return {
        "total": len(libraries),
        "libraries": libraries,
    }


def apk_icon(apk_obj, max_dpi: int = 65536) -> dict:
    """
    获取 APK 应用图标信息。

    :param apk_obj: androguard.core.apk.APK 对象
    :param max_dpi: 最大 DPI（默认 65536）
    :return: 图标信息
    """
    icon_path = apk_obj.get_app_icon(max_dpi=max_dpi)
    result = {"icon_path": icon_path}

    if icon_path:
        try:
            icon_data = apk_obj.get_file(icon_path)
            if icon_data:
                result["size"] = len(icon_data)
                result["base64"] = base64.b64encode(icon_data).decode("ascii")
        except Exception as e:
            result["extract_error"] = str(e)

    return result


def apk_file(apk_obj, filename: str) -> dict:
    """
    提取 APK 中指定文件的内容。

    :param apk_obj: androguard.core.apk.APK 对象
    :param filename: 文件名
    :return: 文件内容（base64 编码）
    """
    try:
        data = apk_obj.get_file(filename)
        if data is not None:
            return {
                "filename": filename,
                "size": len(data),
                "base64": base64.b64encode(data).decode("ascii"),
            }
        else:
            return {"filename": filename, "error": f"File '{filename}' not found in APK"}
    except Exception as e:
        return {"filename": filename, "error": str(e)}


def apk_verify(apk_obj) -> dict:
    """
    验证 APK 完整性。

    :param apk_obj: androguard.core.apk.APK 对象
    :return: 验证结果
    """
    result = {
        "is_valid": apk_obj.is_valid_APK(),
        "is_signed": apk_obj.is_signed(),
        "is_signed_v1": apk_obj.is_signed_v1(),
        "is_signed_v2": apk_obj.is_signed_v2(),
        "is_signed_v3": apk_obj.is_signed_v3(),
        "is_signed_v31": apk_obj.is_signed_v31(),
    }

    # 检查签名名称
    try:
        result["signature_names"] = apk_obj.get_signature_names()
    except Exception:
        pass

    # 检查是否有重复签名 ID
    try:
        result["has_duplicate_signature_ids"] = apk_obj.has_duplicate_apk_signature_ids()
    except Exception:
        pass

    return result


def apk_signing_block(apk_obj) -> dict:
    """
    获取 APK v2/v3 签名块详细信息。

    :param apk_obj: androguard.core.apk.APK 对象
    :return: 签名块信息
    """
    result = {}

    # v2 签名块
    try:
        v2_block = apk_obj.parse_v2_signing_block()
        if v2_block:
            result["v2_signing_block"] = str(v2_block)
    except Exception as e:
        result["v2_signing_block_error"] = str(e)

    # v3 签名块
    try:
        v3_block = apk_obj.parse_v3_signing_block()
        if v3_block:
            result["v3_signing_block"] = str(v3_block)
    except Exception as e:
        result["v3_signing_block_error"] = str(e)

    # v2/v3 签名信息
    for version, getter in [
        ("v2", apk_obj.get_public_keys_der_v2),
        ("v3", apk_obj.get_public_keys_der_v3),
        ("v31", apk_obj.get_public_keys_der_v31),
    ]:
        try:
            keys = getter()
            if keys:
                key_infos = []
                for key_der in keys:
                    key_infos.append({
                        "sha256": hashlib.sha256(key_der).hexdigest(),
                        "size": len(key_der),
                    })
                result[f"{version}_public_keys"] = key_infos
        except Exception:
            pass

    return result


def apk_manifest_attrs(
    apk_obj, tag_name: str, attribute: str, attribute_filter: dict = None
) -> dict:
    """
    批量提取 AndroidManifest.xml 中指定标签的属性值。

    :param apk_obj: androguard.core.apk.APK 对象
    :param tag_name: 标签名（如 uses-permission、activity、service）
    :param attribute: 属性名（如 name、exported）
    :param attribute_filter: 额外的属性过滤条件（如 {"exported": "true"}）
    :return: 属性值列表
    """
    try:
        kwargs = attribute_filter or {}
        values = list(
            apk_obj.get_all_attribute_value(tag_name, attribute, **kwargs)
        )
        # get_all_attribute_value 返回 filter/set，list 转换后顺序非确定 → 排序
        values.sort()
        return {
            "tag": tag_name,
            "attribute": attribute,
            "filter": attribute_filter,
            "total": len(values),
            "values": values,
        }
    except Exception as e:
        return {
            "tag": tag_name,
            "attribute": attribute,
            "error": str(e),
        }


def apk_manifest_attr(
    apk_obj, tag_name: str, attribute: str, attribute_filter: dict = None
) -> dict:
    """
    提取 AndroidManifest.xml 中单个标签的属性值（首个匹配）。

    :param apk_obj: androguard.core.apk.APK 对象
    :param tag_name: 标签名
    :param attribute: 属性名
    :param attribute_filter: 额外的属性过滤条件
    :return: 单个属性值
    """
    try:
        kwargs = attribute_filter or {}
        value = apk_obj.get_attribute_value(tag_name, attribute, **kwargs)
        return {
            "tag": tag_name,
            "attribute": attribute,
            "filter": attribute_filter,
            "value": value,
        }
    except Exception as e:
        return {
            "tag": tag_name,
            "attribute": attribute,
            "error": str(e),
        }


def _parse_certificate(cert) -> dict:
    """将 asn1crypto.x509.Certificate 解析为可序列化的字典"""
    try:
        cert_der = cert.dump()
        info = {
            "sha1": hashlib.sha1(cert_der).hexdigest(),
            "sha256": hashlib.sha256(cert_der).hexdigest(),
            "md5": hashlib.md5(cert_der).hexdigest(),
            "size": len(cert_der),
        }
        try:
            from androguard.util import get_certificate_name_string

            info["issuer"] = get_certificate_name_string(cert.issuer, short=True)
            info["subject"] = get_certificate_name_string(
                cert.subject, short=True
            )
            info["serial_number"] = hex(cert.serial_number)
            info["hash_algorithm"] = cert.hash_algo
            info["signature_algorithm"] = cert.signature_algo
            info["valid_not_before"] = str(
                cert["tbs_certificate"]["validity"]["not_before"].native
            )
            info["valid_not_after"] = str(
                cert["tbs_certificate"]["validity"]["not_after"].native
            )
        except Exception as e:
            info["parse_error"] = str(e)
        return info
    except Exception as e:
        return {"error": str(e)}


def apk_certificate(apk_obj, filename: str = None) -> dict:
    """
    获取 APK 签名证书详情。

    :param apk_obj: androguard.core.apk.APK 对象
    :param filename: 签名文件名（如 META-INF/CERT.RSA）。若为 None，返回所有证书
    :return: 证书详情
    """
    try:
        if filename:
            cert = apk_obj.get_certificate(filename)
            if cert is None:
                return {"filename": filename, "error": "Certificate not found"}
            return {"filename": filename, "certificate": _parse_certificate(cert)}

        # 返回所有证书
        certs = apk_obj.get_certificates()
        cert_list = [_parse_certificate(c) for c in certs if c is not None]
        return {"total": len(cert_list), "certificates": cert_list}
    except Exception as e:
        return {"filename": filename, "error": str(e)}


def apk_verify_signature(apk_obj, filename: str = None) -> dict:
    """
    对 APK 签名做密码学验证（验证签名者信息是否匹配签名文件）。

    与 apk verify（结构+签名方案存在性检查）和 apk certificate（取证书，间接验证）
    的区别：本命令显式调用 get_certificate_der(filename)，它内部走
    verify_signer_info_against_sig_file —— 真正验证 PKCS7 签名者信息对 .SF 签名文件
    的密码学有效性（签名是否匹配内容、证书是否对签名有效）。返回每个签名文件的
    验证结果：通过（含证书摘要 sha256/issuer/subject）或失败（含原因）。

    :param apk_obj: androguard.core.apk.APK 对象
    :param filename: 签名文件名（如 META-INF/CERT.RSA）。None 时验证所有签名文件
    :return: 验证结果
    """
    try:
        if filename:
            filenames = [filename]
        else:
            try:
                filenames = list(apk_obj.get_signature_names())
            except Exception:
                filenames = []

        if not filenames:
            return {
                "verified": False,
                "error": "No signature files found (APK not v1-signed; v2/v3 use apk verify)",
            }

        results = []
        all_verified = True
        for fn in filenames:
            entry = {"filename": fn}
            try:
                # 先确认文件存在于 APK（get_file 对不存在文件可能抛异常或返回字符串）
                raw = apk_obj.get_file(fn)
                if raw is None or isinstance(raw, str):
                    entry["verified"] = False
                    entry["error"] = "Signature file not found in APK"
                    all_verified = False
                    results.append(entry)
                    continue
                # get_certificate_der 内部做完整密码学验证
                der = apk_obj.get_certificate_der(fn)
                if der is None:
                    entry["verified"] = False
                    entry["error"] = (
                        "Signature verification failed (returned None)"
                    )
                    all_verified = False
                else:
                    entry["verified"] = True
                    entry["der_size"] = len(der)
                    entry["sha256"] = hashlib.sha256(der).hexdigest()
                    # 解析证书摘要
                    try:
                        import asn1crypto.x509 as _x509

                        cert = _x509.Certificate.load(der)
                        entry["certificate"] = _parse_certificate(cert)
                    except Exception as ce:
                        entry["cert_parse_error"] = str(ce)[:80]
            except Exception as e:
                entry["verified"] = False
                entry["error"] = f"{type(e).__name__}: {e}"
                all_verified = False
            results.append(entry)

        return {
            "verified": all_verified,
            "total": len(results),
            "signatures": results,
        }
    except Exception as e:
        return {"verified": False, "error": str(e)}


def apk_files_info(apk_obj) -> dict:
    """
    获取 APK 中所有文件的详细信息（名称/类型/CRC32）。

    :param apk_obj: androguard.core.apk.APK 对象
    :return: 文件详细信息列表
    """
    try:
        files = []
        for name, ftype, crc32 in apk_obj.get_files_information():
            files.append(
                {
                    "name": name,
                    "type": ftype,
                    "crc32": hex(crc32),
                }
            )
        return {"total": len(files), "files": files}
    except Exception as e:
        return {"error": str(e)}


def apk_dex_data(apk_obj, all_dex: bool = False) -> dict:
    """
    提取 APK 中的 DEX 二进制数据（base64 编码）。

    :param apk_obj: androguard.core.apk.APK 对象
    :param all_dex: 是否提取所有 DEX（multidex）。False 时只提取主 DEX
    :return: DEX 数据
    """
    try:
        if all_dex:
            dex_list = []
            for dex_bytes in apk_obj.get_all_dex():
                dex_list.append(
                    {
                        "size": len(dex_bytes),
                        "base64": base64.b64encode(dex_bytes).decode("ascii"),
                    }
                )
            return {"dex_count": len(dex_list), "dexes": dex_list}
        else:
            dex_bytes = apk_obj.get_dex()
            return {
                "size": len(dex_bytes),
                "base64": base64.b64encode(dex_bytes).decode("ascii"),
            }
    except Exception as e:
        return {"error": str(e)}


def apk_raw(apk_obj) -> dict:
    """
    提取整个 APK 的原始字节（base64 编码）。

    :param apk_obj: androguard.core.apk.APK 对象
    :return: APK 原始数据
    """
    try:
        raw = apk_obj.get_raw()
        return {
            "size": len(raw),
            "base64": base64.b64encode(raw).decode("ascii"),
        }
    except Exception as e:
        return {"error": str(e)}


def apk_manifest_tags(
    apk_obj, tag_name: str, attribute_filter: dict = None
) -> dict:
    """
    按属性过滤查找 AndroidManifest.xml 中的标签。

    :param apk_obj: androguard.core.apk.APK 对象
    :param tag_name: 标签名
    :param attribute_filter: 属性过滤条件（如 {"exported": "true"}）
    :return: 匹配的标签列表
    """
    try:
        kwargs = attribute_filter or {}
        tags = apk_obj.find_tags(tag_name, **kwargs)
        # find_tags 返回 lxml Element 列表，需序列化为可读字典
        tag_list = []
        for tag in tags:
            tag_info = {"tag": tag.tag}
            # 提取所有属性（带命名空间的会以 {uri}name 形式）
            attrs = {}
            for attr_name, attr_value in tag.attrib.items():
                # 简化命名空间属性名
                if "}" in attr_name:
                    attr_name = attr_name.split("}")[-1]
                attrs[attr_name] = attr_value
            # attrib 迭代序非确定（lxml attrib 来自 set），按 key 重建固定输出
            attrs = {k: attrs[k] for k in sorted(attrs.keys())}
            tag_info["attributes"] = attrs
            tag_list.append(tag_info)
        # find_tags 列表序非确定，按 tag 名 + 属性排序
        tag_list.sort(
            key=lambda t: (t["tag"], tuple(sorted(t["attributes"].items())))
        )
        return {
            "tag": tag_name,
            "filter": attribute_filter,
            "total": len(tag_list),
            "tags": tag_list,
        }
    except Exception as e:
        return {"tag": tag_name, "error": str(e)}


def apk_signing_versions(apk_obj) -> dict:
    """
    检测 APK 支持的签名方案（v1/v2/v3/v3.1）。

    :param apk_obj: androguard.core.apk.APK 对象
    :return: 各签名方案的启用状态
    """
    try:
        return {
            "is_signed": apk_obj.is_signed(),
            "is_valid_apk": apk_obj.is_valid_APK(),
            "is_multidex": apk_obj.is_multidex(),
            "v1": apk_obj.is_signed_v1(),
            "v2": apk_obj.is_signed_v2(),
            "v3": apk_obj.is_signed_v3(),
            "v31": apk_obj.is_signed_v31(),
            "has_duplicate_apk_signature_ids": apk_obj.has_duplicate_apk_signature_ids(),
        }
    except Exception as e:
        return {"error": str(e)}


def _certificates_by_scheme(apk_obj, scheme: str) -> list:
    """按签名方案获取证书列表（统一调用 _parse_certificate）"""
    getters = {
        "v1": apk_obj.get_certificates_v1,
        "v2": apk_obj.get_certificates_v2,
        "v3": apk_obj.get_certificates_v3,
        "v31": apk_obj.get_certificates_v31,
    }
    getter = getters.get(scheme.lower())
    if getter is None:
        return []
    certs = getter()
    return [_parse_certificate(c) for c in certs if c is not None]


def apk_certificates_scheme(apk_obj, scheme: str = "v3") -> dict:
    """
    按签名方案批量获取证书详情。

    :param apk_obj: androguard.core.apk.APK 对象
    :param scheme: 签名方案（v1/v2/v3/v31）
    :return: 证书列表
    """
    try:
        scheme = scheme.lower()
        cert_list = _certificates_by_scheme(apk_obj, scheme)
        if not cert_list:
            # 该方案未启用或无证书
            enabled = getattr(apk_obj, f"is_signed_{scheme}", lambda: False)()
            return {
                "scheme": scheme,
                "enabled": bool(enabled),
                "total": 0,
                "certificates": [],
                "note": f"scheme {scheme} not enabled or no certificates",
            }
        return {
            "scheme": scheme,
            "total": len(cert_list),
            "certificates": cert_list,
        }
    except Exception as e:
        return {"scheme": scheme, "error": str(e)}


def apk_certificates_der(apk_obj, scheme: str = "v3") -> dict:
    """
    按签名方案获取证书 DER 二进制（base64 编码）。

    :param apk_obj: androguard.core.apk.APK 对象
    :param scheme: 签名方案（v2/v3/v31；v1 通过文件获取，需用 apk certificate）
    :return: DER 证书列表
    """
    try:
        scheme = scheme.lower()
        # v1 没有 der 批量方法
        der_getters = {
            "v2": apk_obj.get_certificates_der_v2,
            "v3": apk_obj.get_certificates_der_v3,
            "v31": apk_obj.get_certificates_der_v31,
        }
        getter = der_getters.get(scheme)
        if getter is None:
            return {
                "scheme": scheme,
                "error": "DER extraction only supports v2/v3/v31; use 'apk certificate' for v1",
            }
        ders = getter()
        cert_list = [
            {
                "size": len(d),
                "sha1": hashlib.sha1(d).hexdigest(),
                "sha256": hashlib.sha256(d).hexdigest(),
                "base64": base64.b64encode(d).decode("ascii"),
            }
            for d in ders
        ]
        return {"scheme": scheme, "total": len(cert_list), "certificates": cert_list}
    except Exception as e:
        return {"scheme": scheme, "error": str(e)}


def apk_public_keys(apk_obj, scheme: str = "v3") -> dict:
    """
    按签名方案获取签名公钥信息。

    :param apk_obj: androguard.core.apk.APK 对象
    :param scheme: 签名方案（v2/v3/v31）
    :return: 公钥列表
    """
    try:
        scheme = scheme.lower()
        pk_getters = {
            "v2": apk_obj.get_public_keys_v2,
            "v3": apk_obj.get_public_keys_v3,
            "v31": apk_obj.get_public_keys_v31,
        }
        getter = pk_getters.get(scheme)
        if getter is None:
            return {"scheme": scheme, "error": "Public keys only support v2/v3/v31"}
        pks = getter()
        key_list = []
        for pk in pks:
            info = {
                "algorithm": str(pk.algorithm),
            }
            try:
                info["key_size"] = pk.bit_size
            except Exception:
                pass
            try:
                der = pk.dump()
                info["size"] = len(der)
                info["sha1"] = hashlib.sha1(der).hexdigest()
                info["sha256"] = hashlib.sha256(der).hexdigest()
                info["base64"] = base64.b64encode(der).decode("ascii")
            except Exception as e:
                info["der_error"] = str(e)
            key_list.append(info)
        return {"scheme": scheme, "total": len(key_list), "public_keys": key_list}
    except Exception as e:
        return {"scheme": scheme, "error": str(e)}


def apk_signature_files(apk_obj) -> dict:
    """
    获取 APK 的签名文件信息（文件名 + 原始签名数据 base64）。

    :param apk_obj: androguard.core.apk.APK 对象
    :return: 签名文件列表
    """
    try:
        result = {
            "signature_name": apk_obj.get_signature_name(),
            "signature_names": list(apk_obj.get_signature_names()),
        }
        # 原始签名数据（v1 PKCS#7）
        try:
            sig = apk_obj.get_signature()
            if sig:
                result["signature_base64"] = base64.b64encode(sig).decode("ascii")
                result["signature_size"] = len(sig)
        except Exception as e:
            result["signature_error"] = str(e)
        # 所有签名块
        try:
            sigs = apk_obj.get_signatures()
            result["signatures"] = [
                {
                    "size": len(s),
                    "sha256": hashlib.sha256(s).hexdigest(),
                    "base64": base64.b64encode(s).decode("ascii"),
                }
                for s in sigs
            ]
            result["signatures_count"] = len(sigs)
        except Exception as e:
            result["signatures_error"] = str(e)
        return result
    except Exception as e:
        return {"error": str(e)}


def apk_files_crc32(apk_obj) -> dict:
    """
    获取 APK 中所有文件的 CRC32 校验值。

    :param apk_obj: androguard.core.apk.APK 对象
    :return: 文件名 → CRC32 映射
    """
    try:
        crc = apk_obj.get_files_crc32()
        files = [
            {"name": name, "crc32": hex(value), "crc32_dec": value}
            for name, value in crc.items()
        ]
        return {"total": len(files), "files": files}
    except Exception as e:
        return {"error": str(e)}


def apk_fingerprint(apk_obj, scheme: str = "v3") -> dict:
    """
    计算签名公钥的 SHA-256 指纹。

    :param apk_obj: androguard.core.apk.APK 对象
    :param scheme: 签名方案（v2/v3/v31，用于取公钥）
    :return: 公钥指纹
    """
    try:
        scheme = scheme.lower()
        pk_getters = {
            "v2": apk_obj.get_public_keys_v2,
            "v3": apk_obj.get_public_keys_v3,
            "v31": apk_obj.get_public_keys_v31,
        }
        getter = pk_getters.get(scheme)
        if getter is None:
            return {"scheme": scheme, "error": "Fingerprint only supports v2/v3/v31"}
        pks = getter()
        if not pks:
            return {
                "scheme": scheme,
                "error": f"No public keys found for scheme {scheme}",
            }
        from androguard.util import calculate_fingerprint

        fingerprints = []
        for pk in pks:
            fp = calculate_fingerprint(pk)
            fingerprints.append(
                {
                    "algorithm": str(pk.algorithm),
                    "fingerprint_hex": fp.hex(),
                    "fingerprint_base64": base64.b64encode(fp).decode("ascii"),
                }
            )
        return {"scheme": scheme, "total": len(fingerprints), "fingerprints": fingerprints}
    except Exception as e:
        return {"scheme": scheme, "error": str(e)}


def apk_manifest_axml(apk_obj) -> dict:
    """
    分析 AndroidManifest.xml 的 AXML 格式（加固检测 + 原始 XML）。

    :param apk_obj: androguard.core.apk.APK 对象
    :return: AXML 分析结果（is_valid/is_packed + 原始 XML + 根标签）
    """
    try:
        axml = apk_obj.get_android_manifest_axml()
        if axml is None:
            return {"error": "No AndroidManifest.xml AXML found"}
        result = {
            "is_valid": axml.is_valid(),
            "is_packed": axml.is_packed(),
        }
        # 篡改检测（AXMLParser 层）：axml_tampered/packerwarning
        try:
            parser = axml.axml
            if parser is not None:
                result["axml_tampered"] = parser.axml_tampered
                result["packerwarning"] = parser.packerwarning
        except Exception:
            pass
        # 原始 XML 文本
        try:
            xml_bytes = axml.get_xml()
            if xml_bytes:
                result["xml"] = xml_bytes.decode("utf-8", errors="replace")
                result["xml_size"] = len(xml_bytes)
        except Exception as e:
            result["xml_error"] = str(e)
        # XML 对象的根标签信息
        try:
            xml_obj = axml.get_xml_obj()
            if xml_obj is not None:
                result["root_tag"] = xml_obj.tag
                # 提取根标签属性（简化命名空间）
                attrs = {}
                for name, value in xml_obj.attrib.items():
                    if "}" in name:
                        name = name.split("}")[-1]
                    attrs[name] = value
                result["root_attributes"] = attrs
        except Exception as e:
            result["xml_obj_error"] = str(e)
        return result
    except Exception as e:
        return {"error": str(e)}


def apk_axml(apk_obj, filename: str, pretty: bool = True) -> dict:
    """
    解析 APK 内任意二进制 AXML 文件为可读 XML。

    与 apk_manifest_axml（仅解析 AndroidManifest.xml）的区别：本命令可解析
    APK 内任意 AXML 文件——res/layout/*.xml（布局）、res/xml/*.xml（preferences
    等配置）、res/drawable*.xml（vector/shape drawable）等。APK 内这些 XML
    都是二进制 AXML 格式（无法直接 cat），需 AXMLPrinter 解码为可读文本，
    用于 UI 结构分析、drawable 内容查看、配置文件审计。

    :param apk_obj: androguard.core.apk.APK 对象
    :param filename: APK 内文件路径（如 res/layout/main.xml、res/xml/settings.xml）
    :param pretty: 是否美化输出（缩进，默认 True）
    :return: AXML 解析结果（is_valid/is_packed + 可读 XML + root tag）
    """
    try:
        from androguard.core.axml import AXMLPrinter

        raw = apk_obj.get_file(filename)
        if raw is None or isinstance(raw, str):
            return {"filename": filename, "error": "File not found in APK"}
        result = {
            "filename": filename,
            "raw_size": len(raw),
        }
        ap = AXMLPrinter(raw)
        result["is_valid"] = ap.is_valid()
        result["is_packed"] = ap.is_packed()
        try:
            result["packerwarning"] = ap.packerwarning
        except Exception:
            pass
        # 篡改检测（AXMLParser 层）
        try:
            parser = ap.axml
            if parser is not None:
                result["axml_tampered"] = parser.axml_tampered
        except Exception:
            pass
        # 可读 XML 文本
        try:
            xml_bytes = ap.get_xml(pretty=pretty)
            if xml_bytes:
                result["xml"] = xml_bytes.decode("utf-8", errors="replace")
                result["xml_size"] = len(xml_bytes)
        except Exception as e:
            result["xml_error"] = str(e)
        # 根标签信息
        try:
            xml_obj = ap.get_xml_obj()
            if xml_obj is not None:
                result["root_tag"] = xml_obj.tag
                attrs = {}
                for name, value in xml_obj.attrib.items():
                    if "}" in name:
                        name = name.split("}")[-1]
                    attrs[name] = value
                result["root_attributes"] = attrs
                # 直接子标签统计（了解文件结构规模）
                children = list(xml_obj)
                result["children_count"] = len(children)
                result["children_tags"] = sorted({c.tag.split("}")[-1] for c in children})
        except Exception as e:
            result["xml_obj_error"] = str(e)
        return result
    except Exception as e:
        return {"filename": filename, "error": str(e)}


# ================================================================
# 第六轮：APK 权限分类 / SDK 版本 / 设备特性
# ================================================================


def apk_declared_permissions(apk_obj) -> dict:
    """
    获取 APK 声明（自定义）的权限。

    declared_permissions 是 APK 通过 <permission> 标签自定义的权限
    （区别于 <uses-permission> 请求的权限）。

    :param apk_obj: androguard.core.apk.APK 对象
    :return: 声明权限列表 + 详情
    """
    try:
        perms = apk_obj.get_declared_permissions()
        details = apk_obj.get_declared_permissions_details()
        return {
            "total": len(perms),
            "permissions": perms,
            "details": details,
        }
    except Exception as e:
        return {"error": str(e)}


def apk_requested_permissions(apk_obj) -> dict:
    """
    获取 APK 请求的权限分类（AOSP 系统 / 第三方 / 隐含）。

    :param apk_obj: androguard.core.apk.APK 对象
    :return: 权限分类汇总
    """
    try:
        aosp = list(apk_obj.get_requested_aosp_permissions())
        aosp_details = list(apk_obj.get_requested_aosp_permissions_details())
        third_party = list(apk_obj.get_requested_third_party_permissions())
        implied = list(apk_obj.get_uses_implied_permission_list())
        # implied 是 [[perm, level], ...]，标准化
        implied_norm = []
        for item in implied:
            if isinstance(item, (list, tuple)) and len(item) >= 1:
                implied_norm.append(
                    {"permission": item[0], "level": item[1] if len(item) > 1 else None}
                )
            else:
                implied_norm.append({"permission": str(item), "level": None})
        return {
            "aosp_permissions": aosp,
            "aosp_permissions_count": len(aosp),
            "aosp_permissions_details": aosp_details,
            "third_party_permissions": third_party,
            "third_party_permissions_count": len(third_party),
            "implied_permissions": implied_norm,
            "implied_permissions_count": len(implied_norm),
        }
    except Exception as e:
        return {"error": str(e)}


def apk_sdk_versions(apk_obj) -> dict:
    """
    获取 APK 的 SDK 版本信息（min/max/target/effective_target）。

    :param apk_obj: androguard.core.apk.APK 对象
    :return: SDK 版本信息
    """
    try:
        return {
            "min_sdk_version": apk_obj.get_min_sdk_version(),
            "max_sdk_version": apk_obj.get_max_sdk_version(),
            "target_sdk_version": apk_obj.get_target_sdk_version(),
            "effective_target_sdk_version": apk_obj.get_effective_target_sdk_version(),
        }
    except Exception as e:
        return {"error": str(e)}


def apk_main_activities(apk_obj) -> dict:
    """
    获取 APK 的主 Activity（含别名 aliases）。

    :param apk_obj: androguard.core.apk.APK 对象
    :return: 主 Activity 信息
    """
    try:
        return {
            "main_activity": apk_obj.get_main_activity(),
            "main_activities": list(apk_obj.get_main_activities()),
            "activity_aliases": list(apk_obj.get_activity_aliases()),
        }
    except Exception as e:
        return {"error": str(e)}


def apk_device_features(apk_obj) -> dict:
    """
    获取 APK 的设备特性布尔标记（TV/Wearable/Leanback/Multidex）。

    :param apk_obj: androguard.core.apk.APK 对象
    :return: 设备特性标记
    """
    try:
        return {
            "is_androidtv": apk_obj.is_androidtv(),
            "is_wearable": apk_obj.is_wearable(),
            "is_leanback": apk_obj.is_leanback(),
            "is_multidex": apk_obj.is_multidex(),
        }
    except Exception as e:
        return {"error": str(e)}


def apk_files_types(apk_obj) -> dict:
    """
    获取 APK 中所有文件的类型识别结果（基于 file 命令）。

    :param apk_obj: androguard.core.apk.APK 对象
    :return: 文件名 → 类型 字典
    """
    try:
        types = apk_obj.get_files_types()
        if hasattr(types, "items"):
            result = dict(types)
        else:
            result = list(types)
        return {"total": len(result), "files": result}
    except Exception as e:
        return {"error": str(e)}


# ================================================================
# 第七轮：APK 权限详情
# ================================================================


def apk_details_permissions(apk_obj) -> dict:
    """
    获取 APK 请求权限的详细信息（protection_level / label / description）。

    比 permissions 更详细：每个权限附带保护级别、用户可见标签和描述。
    用于权限审计时评估各权限的危险等级。

    :param apk_obj: androguard.core.apk.APK 对象
    :return: 权限名 → [protection_level, label, description]
    """
    try:
        details = apk_obj.get_details_permissions()
        # details 是 dict[权限名, [protection_level, label, description]]
        result = {}
        for perm, info in details.items():
            if isinstance(info, (list, tuple)):
                result[perm] = {
                    "protection_level": info[0] if len(info) > 0 else None,
                    "label": info[1] if len(info) > 1 else None,
                    "description": info[2] if len(info) > 2 else None,
                }
            else:
                result[perm] = {"raw": info}
        return {"total": len(result), "permissions": result}
    except Exception as e:
        return {"error": str(e)}


# ================================================================
# 第八轮：APK manifest 标签树 / 证书名规范化
# ================================================================


def apk_manifest_tree(apk_obj) -> dict:
    """
    获取 AndroidManifest.xml 的标签树统计（标签计数 + 属性概览）。

    基于 get_android_manifest_xml 返回的 lxml Element，遍历整棵标签树，
    统计每种标签的数量，并提取各标签的属性集合。
    与 manifest-tags（按单标签查）不同，此命令给出 manifest 的整体结构概览。

    :param apk_obj: androguard.core.apk.APK 对象
    :return: 标签树统计
    """
    try:
        xml = apk_obj.get_android_manifest_xml()
        if xml is None:
            return {"error": "Failed to parse manifest XML"}

        from collections import Counter, OrderedDict

        tag_counts = Counter()
        tag_attrs = {}  # tag -> set of attr names (simplified)
        for elem in xml.iter():
            # 简化命名空间：{ns}tag -> tag
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            tag_counts[tag] += 1
            attrs = set()
            for name in elem.attrib:
                attrs.add(name.split("}")[-1] if "}" in name else name)
            if tag not in tag_attrs:
                tag_attrs[tag] = set()
            tag_attrs[tag] |= attrs

        # 按出现次数降序
        tags = []
        for tag, count in tag_counts.most_common():
            tags.append({
                "tag": tag,
                "count": count,
                "attributes": sorted(tag_attrs.get(tag, set())),
            })
        return {
            "root_tag": xml.tag.split("}")[-1] if "}" in xml.tag else xml.tag,
            "total_tags": sum(tag_counts.values()),
            "distinct_tags": len(tag_counts),
            "tags": tags,
        }
    except Exception as e:
        return {"error": str(e)}


def apk_find_tags_xml(apk_obj, xml_name: str, tag_name: str, **filter_kwargs) -> dict:
    """
    从 APK 中指定 XML 文件查找标签（find_tags_from_xml）。

    与 manifest-tags（查 manifest）不同，此命令可查 APK 内任意 XML 文件
    （如 res/xml/*.xml）中的标签。返回匹配标签的 tag 名和属性。

    :param apk_obj: androguard.core.apk.APK 对象
    :param xml_name: APK 内的 XML 文件名（如 AndroidManifest.xml）
    :param tag_name: 要查找的标签名
    :param filter_kwargs: 属性过滤条件
    :return: 匹配的标签列表
    """
    try:
        results = apk_obj.find_tags_from_xml(xml_name, tag_name, **filter_kwargs)
        # find_tags_from_xml 返回 lxml _Element 列表，需序列化
        tags = []
        for elem in results or []:
            # 简化命名空间
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            attrib = {}
            for name, value in elem.attrib.items():
                key = name.split("}")[-1] if "}" in name else name
                attrib[key] = value
            tags.append({"tag": tag, "attributes": attrib})
        return {
            "xml_name": xml_name,
            "tag_name": tag_name,
            "filter": filter_kwargs,
            "total": len(tags),
            "results": tags,
        }
    except Exception as e:
        return {
            "xml_name": xml_name,
            "tag_name": tag_name,
            "error": str(e),
        }


def apk_cert_names(apk_obj, scheme: str = "v3", android: bool = True) -> dict:
    """
    获取签名证书主题/颁发者的规范化名称（canonical_name / comparison_name）。

    canonical_name 将 X.509 Name 规范化为 cn=...,ou=... 格式，
    便于跨 APK 比对签名证书是否一致。

    :param apk_obj: androguard.core.apk.APK 对象
    :param scheme: 签名方案（v1/v2/v3/v31）
    :param android: 是否使用 Android 风格规范化
    :return: 各证书的规范化名
    """
    try:
        scheme = scheme.lower()
        cert_getters = {
            "v1": apk_obj.get_certificates_v1,
            "v2": apk_obj.get_certificates_v2,
            "v3": apk_obj.get_certificates_v3,
            "v31": apk_obj.get_certificates_v31,
        }
        if scheme not in cert_getters:
            return {"error": f"Unsupported scheme: {scheme}"}

        certs = cert_getters[scheme]()
        # 过滤 None（v1 可能含 None）
        certs = [c for c in certs if c is not None]

        results = []
        for cert in certs:
            entry = {}
            try:
                subj = cert.subject
                issuer = cert.issuer
                entry["subject_canonical"] = apk_obj.canonical_name(subj, android=android)
                entry["issuer_canonical"] = apk_obj.canonical_name(issuer, android=android)
                entry["subject_comparison"] = apk_obj.comparison_name(subj, android=android)
                entry["issuer_comparison"] = apk_obj.comparison_name(issuer, android=android)
            except Exception as e:
                entry["error"] = str(e)
            results.append(entry)

        return {
            "scheme": scheme,
            "android": android,
            "total": len(results),
            "certificates": results,
        }
    except Exception as e:
        return {"error": str(e)}


# ================================================================
# 第九轮：APK 资源 ID 反解
# ================================================================


def apk_res_value(apk_obj, name: str) -> dict:
    """
    将资源 ID（如 @7F080001）解析为字面值。

    AndroidManifest 中大量属性引用资源 ID（如 android:label="@7F080001"），
    此命令把这类 ID 反解为实际资源值（字符串、文件路径等）。
    用于还原 manifest 中被资源引用遮挡的真实值。

    :param apk_obj: androguard.core.apk.APK 对象
    :param name: 资源 ID（如 @7F080001，无 @ 前缀会自动补）
    :return: 资源 ID 对应的值
    """
    try:
        # get_res_value 要求 name 以 @ 开头
        raw_name = name
        if not name.startswith("@"):
            name = "@" + name

        value = apk_obj.get_res_value(name)

        # value 可能是 str、list[(config, value)] 或其他复杂结构
        result = {"input": raw_name, "normalized": name}
        if isinstance(value, str):
            result["value"] = value
            result["value_type"] = "string"
        elif isinstance(value, (list, tuple)):
            # list of (ARSCResTableConfig, value) 二元组
            configs = []
            for item in value:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    config, val = item[0], item[1]
                    config_str = str(config) if config is not None else None
                    configs.append({"config": config_str, "value": val})
                else:
                    configs.append({"value": str(item)})
            result["value"] = configs
            result["value_type"] = "configs"
        else:
            result["value"] = str(value)
            result["value_type"] = type(value).__name__

        # 标记是否回退为原值（资源未找到时 get_res_value 返回原 name）
        if value == name:
            result["note"] = "Resource ID not resolved, returned as-is"
        return result
    except Exception as e:
        return {"input": name, "error": str(e)}


# ================================================================
# 第十轮：APK 元信息补充（DEX 名/签名名/应用名/有效性/重复签名）
# ================================================================


def apk_dex_names(apk_obj) -> dict:
    """
    获取 APK 内所有 DEX 文件的名称列表（multidex 场景下会有 classes.dex、classes2.dex...）。

    :param apk_obj: androguard.core.apk.APK 对象
    :return: DEX 文件名列表
    """
    try:
        names = apk_obj.get_dex_names()
        # get_dex_names 可能返回 filter 迭代器，需 list() 物化
        names = list(names)
        return {"total": len(names), "dex_names": names}
    except Exception as e:
        return {"error": str(e)}


def apk_signature_names(apk_obj) -> dict:
    """
    获取 APK 中所有签名文件的名称列表（如 CERT.RSA、CERT.SF）。

    与 get_signature_name（返回单个）互补，此为全量列表，用于排查多签名场景。

    :param apk_obj: androguard.core.apk.APK 对象
    :return: 签名文件名列表
    """
    try:
        names = apk_obj.get_signature_names()
        return {"total": len(names), "signature_names": list(names)}
    except Exception as e:
        return {"error": str(e)}


def apk_app_name(apk_obj, locale: str = None) -> dict:
    """
    获取应用显示名（android:label 资源反解后的字符串）。

    :param apk_obj: androguard.core.apk.APK 对象
    :param locale: 语言区域（如 zh、en），None 取默认
    :return: 应用名
    """
    try:
        name = apk_obj.get_app_name(locale=locale)
        result = {"app_name": name, "locale": locale}
        # 未解析的资源引用会以 @ 开头原样返回
        if isinstance(name, str) and name.startswith("@"):
            result["note"] = "Resource ID not resolved for this locale, returned as-is"
        return result
    except Exception as e:
        return {"error": str(e)}


def apk_valid(apk_obj) -> dict:
    """
    检查 APK 是否为有效 APK（结构完整性判断）。

    :param apk_obj: androguard.core.apk.APK 对象
    :return: 有效性布尔值
    """
    try:
        valid = apk_obj.is_valid_APK()
        return {"valid": bool(valid)}
    except Exception as e:
        return {"error": str(e)}


def apk_duplicate_signatures(apk_obj) -> dict:
    """
    检测 APK 是否存在重复的签名 ID（v2/v3 签名块中的证书链重复）。

    重复签名 ID 可能是签名打包工具异常或多渠道打包残留，可作为可疑特征。

    :param apk_obj: androguard.core.apk.APK 对象
    :return: 是否存在重复签名 ID
    """
    try:
        dup = apk_obj.has_duplicate_apk_signature_ids()
        return {"has_duplicate": bool(dup)}
    except Exception as e:
        return {"error": str(e)}


def apk_security_overview(apk_obj) -> dict:
    """
    APK 安全概览（一键聚合安全审计关键信号）。

    与 apk info（基本信息，无安全维度）的区别：本命令聚合安全审计关心的
    信号——签名验证结果、危险权限、导出组件、manifest 安全标志（debuggable/
    allowBackup/usesCleartextTraffic）、SDK 版本、加固检测、隐含权限、重复签名，
    一处输出便于快速体检。

    :param apk_obj: androguard.core.apk.APK 对象
    :return: 安全概览
    """
    result = {}

    # 基本信息
    try:
        result["package"] = apk_obj.get_package()
        result["app_name"] = apk_obj.get_app_name()
        result["version_code"] = apk_obj.get_androidversion_code()
        result["version_name"] = apk_obj.get_androidversion_name()
    except Exception:
        pass

    # SDK 版本
    try:
        result["min_sdk"] = apk_obj.get_min_sdk_version()
        result["target_sdk"] = apk_obj.get_target_sdk_version()
        result["max_sdk"] = apk_obj.get_max_sdk_version()
        result["effective_target_sdk"] = apk_obj.get_effective_target_sdk_version()
    except Exception:
        pass

    # 签名验证
    try:
        sig = {
            "is_signed": apk_obj.is_signed(),
            "is_signed_v1": apk_obj.is_signed_v1(),
            "is_signed_v2": apk_obj.is_signed_v2(),
            "is_signed_v3": apk_obj.is_signed_v3(),
            "is_signed_v31": apk_obj.is_signed_v31(),
            "is_valid_apk": apk_obj.is_valid_APK(),
            "has_duplicate_signature_ids": apk_obj.has_duplicate_apk_signature_ids(),
        }
        # 密码学验证（v1）
        try:
            sig["v1_verified"] = apk_verify_signature(apk_obj).get("verified")
        except Exception:
            pass
        result["signature"] = sig
    except Exception:
        pass

    # manifest 安全标志
    manifest_flags = {}
    for attr in (
        "debuggable",
        "allowBackup",
        "usesCleartextTraffic",
        "networkSecurityConfig",
        "testOnly",
        "extractNativeLibs",
    ):
        try:
            v = apk_obj.get_attribute_value("application", attr)
            if v is not None:
                manifest_flags[attr] = v
        except Exception:
            pass
    result["manifest_flags"] = manifest_flags

    # 权限（区分危险权限）
    try:
        perms = list(apk_obj.get_permissions())
        dangerous = []
        other = []
        try:
            details = apk_obj.get_details_permissions()
        except Exception:
            details = {}
        for p in perms:
            level = None
            if p in details:
                d = details[p]
                if isinstance(d, (list, tuple)) and d:
                    level = d[0]
            if level == "dangerous":
                dangerous.append(p)
            else:
                other.append(p)
        result["permissions"] = {
            "total": len(perms),
            "dangerous": dangerous,
            "dangerous_count": len(dangerous),
            "other": other,
        }
    except Exception:
        pass

    # 隐含权限
    try:
        implied = list(apk_obj.get_uses_implied_permission_list())
        result["implied_permissions_count"] = len(implied)
    except Exception:
        pass

    # 导出组件
    exported = {}
    # kind → manifest tag 名
    tag_map = {
        "activities": "activity",
        "services": "service",
        "receivers": "receiver",
        "providers": "provider",
    }
    for kind, getter in (
        ("activities", apk_obj.get_activities),
        ("services", apk_obj.get_services),
        ("receivers", apk_obj.get_receivers),
        ("providers", apk_obj.get_providers),
    ):
        try:
            items = list(getter())
            tag = tag_map.get(kind, kind[:-1])
            exp_list = []
            implicit_list = []
            for name in items:
                try:
                    exp = apk_obj.get_attribute_value(tag, "exported", name=name)
                except Exception:
                    exp = None
                if str(exp).lower() == "true":
                    exp_list.append(name)
                elif exp is None:
                    # 无显式 exported 属性：若有 intent-filter，默认导出（隐式导出）
                    try:
                        ifs = apk_obj.get_intent_filters(tag, name)
                        if ifs:
                            implicit_list.append(name)
                    except Exception:
                        pass
            exported[kind] = {
                "total": len(items),
                "exported_explicit": exp_list,
                "exported_implicit": implicit_list,
            }
        except Exception:
            pass
    result["components"] = exported

    # 加固检测（AXML 篡改/打包警告）
    try:
        from androguard.core.axml import AXMLPrinter

        axml = apk_obj.get_android_manifest_axml()
        if axml is not None:
            parser = axml.axml
            if parser is not None:
                result["axml_tampered"] = parser.axml_tampered
                result["packerwarning"] = parser.packerwarning
    except Exception:
        pass

    # 设备特性
    try:
        result["is_multidex"] = apk_obj.is_multidex()
        result["is_wearable"] = apk_obj.is_wearable()
        result["is_androidtv"] = apk_obj.is_androidtv()
    except Exception:
        pass

    return result


# ================================================================
# 第八轮：Native 库提取
# ================================================================


def apk_native_libraries(apk_obj, include_data: bool = False) -> dict:
    """
    提取 APK 中的 native 库（lib/<abi>/*.so）列表。

    与 apk_libraries（manifest <uses-library> 声明）和 apk_files（全量文件列表）
    的区别：本命令聚焦实际打包的 .so 共享库，按 ABI（arm64-v8a/armeabi-v7a/
    x86/x86_64 等）分组，含每个库的大小、架构。用于 native 层分析入口
    （配合 security-hotspots 的 native_methods 定位 JNI 实现类）。

    :param apk_obj: androguard.core.apk.APK 对象
    :param include_data: 是否返回 .so 的 base64 数据（默认 False，仅元数据）
    :return: native 库信息
    """
    try:
        import base64

        libs = []
        abis = {}
        for fn in apk_obj.get_files():
            if not fn.endswith(".so"):
                continue
            # 解析 ABI: lib/<abi>/<name>.so
            abi = None
            parts = fn.split("/")
            if len(parts) >= 3 and parts[0] == "lib":
                abi = parts[1]
            data = apk_obj.get_file(fn)
            size = len(data) if data else 0
            entry = {
                "path": fn,
                "name": parts[-1],
                "abi": abi,
                "size": size,
            }
            if include_data and data:
                entry["data_base64"] = base64.b64encode(data).decode("ascii")
            libs.append(entry)
            if abi:
                abis.setdefault(abi, 0)
                abis[abi] += 1

        return {
            "total": len(libs),
            "abis": abis,
            "libraries": libs,
        }
    except Exception as e:
        return {"error": str(e)}


# ================================================================
# 第九轮：Application 安全标志（默认值推断 + 风险评级）
# ================================================================


def apk_application_flags(apk_obj) -> dict:
    """
    Manifest <application> 安全属性完整审计（带默认值推断与风险评级）。

    与 apk_security_overview（聚合多维度信号，manifest_flags 只列非 None 值）的区别：
    本命令聚焦 <application> 标签的全部安全相关属性，对每个属性：
      1. 读取显式值（None 表示未显式设置）
      2. 按 Android 官方规则推断默认值（依赖 targetSdkVersion）
      3. 给出风险评级（critical/warning/info/safe）与说明

    这是 manifest 安全审计的核心入口——debuggable=true、allowBackup=true、
    明文流量等是常见漏洞的直接信号。

    :param apk_obj: androguard.core.apk.APK 对象
    :return: application 安全标志审计结果
    """
    def _effective_target():
        try:
            t = apk_obj.get_effective_target_sdk_version()
            return int(t) if t is not None else None
        except Exception:
            return None

    eff_target = _effective_target()

    def _attr(name):
        try:
            v = apk_obj.get_attribute_value("application", name)
            return v
        except Exception:
            return None

    def _bool(v):
        if v is None:
            return None
        return str(v).lower() == "true"

    flags = []

    # ---- debuggable ----
    v = _attr("debuggable")
    eff = _bool(v) if v is not None else False  # 默认 false
    flags.append({
        "name": "debuggable",
        "value": v,
        "effective": eff,
        "default": False,
        "risk": "critical" if eff else "safe",
        "desc": "允许调试应用（可附加 jdb 调试器，绕过保护读取内存/数据）",
    })

    # ---- allowBackup ----
    v = _attr("allowBackup")
    eff = _bool(v) if v is not None else True  # 默认 true
    flags.append({
        "name": "allowBackup",
        "value": v,
        "effective": eff,
        "default": True,
        "risk": "warning" if eff else "safe",
        "desc": "允许 adb backup 导出应用数据（敏感数据可被提取）",
    })

    # ---- usesCleartextTraffic ----
    v = _attr("usesCleartextTraffic")
    if v is not None:
        eff = _bool(v)
    else:
        # targetSdk >= 28 默认 false（拒绝明文）；< 28 默认 true（允许）
        eff = False if (eff_target is not None and eff_target >= 28) else True
    flags.append({
        "name": "usesCleartextTraffic",
        "value": v,
        "effective": eff,
        "default": (eff_target is None and None) or (eff_target < 28),
        "risk": "warning" if eff else "safe",
        "desc": "允许 HTTP 明文流量（中间人可窃听/篡改）",
    })

    # ---- networkSecurityConfig ----
    v = _attr("networkSecurityConfig")
    flags.append({
        "name": "networkSecurityConfig",
        "value": v,
        "effective": v,
        "default": None,
        "risk": "info" if v else "warning",
        "desc": "网络安全配置资源（未设置则用系统默认，明文策略取决于 usesCleartextTraffic）",
    })

    # ---- extractNativeLibs ----
    v = _attr("extractNativeLibs")
    if v is not None:
        eff = _bool(v)
        default = None
    else:
        # minSdk >= 23 且使用较新 AGP 默认 false；保守按 true
        try:
            min_sdk = int(apk_obj.get_min_sdk_version())
        except Exception:
            min_sdk = None
        eff = True  # 默认 true（解压 native 库）
        default = True
        if min_sdk is not None and min_sdk >= 23:
            default = False  # minSdk>=23 倾向 false（取决于构建工具）
    flags.append({
        "name": "extractNativeLibs",
        "value": v,
        "effective": eff,
        "default": default,
        "risk": "info",
        "desc": "是否解压 native 库到磁盘（true 增加体积/可被替换，false 提升完整性）",
    })

    # ---- testOnly ----
    v = _attr("testOnly")
    eff = _bool(v) if v is not None else False
    flags.append({
        "name": "testOnly",
        "value": v,
        "effective": eff,
        "default": False,
        "risk": "critical" if eff else "safe",
        "desc": "仅测试安装（android:testOnly，正常发布不应为 true）",
    })

    # ---- requestLegacyExternalStorage ----
    v = _attr("requestLegacyExternalStorage")
    eff = _bool(v) if v is not None else False
    flags.append({
        "name": "requestLegacyExternalStorage",
        "value": v,
        "effective": eff,
        "default": False,
        "risk": "warning" if eff else "safe",
        "desc": "请求旧版外部存储访问（绕过 Scoped Storage 限制）",
    })

    # ---- directBootAware ----
    v = _attr("directBootAware")
    eff = _bool(v) if v is not None else False
    flags.append({
        "name": "directBootAware",
        "value": v,
        "effective": eff,
        "default": False,
        "risk": "info",
        "desc": "设备直接启动（用户解锁前）即可运行",
    })

    # ---- dataExtractionRules (Android 12+) ----
    v = _attr("dataExtractionRules")
    flags.append({
        "name": "dataExtractionRules",
        "value": v,
        "effective": v,
        "default": None,
        "risk": "info",
        "desc": "备份/迁移数据规则（Android 12+，替代 allowBackup/fullBackupContent）",
    })

    # ---- fullBackupContent ----
    v = _attr("fullBackupContent")
    flags.append({
        "name": "fullBackupContent",
        "value": v,
        "effective": v,
        "default": None,
        "risk": "info" if v else "warning",
        "desc": "备份包含/排除规则资源（未设置则全量备份，取决于 allowBackup）",
    })

    # 汇总
    risk_summary = {"critical": 0, "warning": 0, "info": 0, "safe": 0}
    for f in flags:
        risk_summary[f["risk"]] = risk_summary.get(f["risk"], 0) + 1

    result = {
        "effective_target_sdk": eff_target,
        "risk_summary": risk_summary,
        "flags": flags,
    }
    return result


# ================================================================
# 第十轮：组件安全属性详情
# ================================================================


def apk_component_details(apk_obj) -> dict:
    """
    所有组件（Activity/Service/Receiver/Provider）的安全属性详情。

    与 apk activities/services/receivers/providers（返回名称列表 + intent-filter）
    和 apk security-overview（仅统计导出数）的区别：本命令列出**每个组件的
    完整安全属性**——exported/enabled/permission/process 以及各自特有的属性
    （activity 的 launchMode、provider 的 authorities/readPermission 等），
    并推断 exported 默认值、标记暴露风险。

    用于组件级暴露面审计：导出且无 permission 保护的组件是 Android 安全审计
    的核心攻击面（组件劫持、越权访问）。

    :param apk_obj: androguard.core.apk.APK 对象
    :return: 组件安全属性详情
    """
    def _attr(tag, attr, name):
        try:
            return apk_obj.get_attribute_value(tag, attr, name=name)
        except Exception:
            return None

    def _has_intent_filter(tag, name):
        try:
            ifs = apk_obj.get_intent_filters(tag, name)
            return bool(ifs)
        except Exception:
            return False

    # exported 推断规则：
    # - 显式值优先
    # - None 时：有 intent-filter 默认 True（隐式导出），无则 False
    def _infer_exported(tag, name, explicit):
        if explicit is not None:
            return str(explicit).lower() == "true"
        return _has_intent_filter(tag, name)

    def _component(tag, name, extra_attrs):
        exported_explicit = _attr(tag, "exported", name)
        enabled = _attr(tag, "enabled", name)
        permission = _attr(tag, "permission", name)
        process = _attr(tag, "process", name)
        exported_eff = _infer_exported(tag, name, exported_explicit)
        # 风险：导出且无 permission 保护
        risk = "exposed" if (exported_eff and not permission) else "safe"
        info = {
            "name": name,
            "exported": exported_explicit,
            "exported_effective": exported_eff,
            "exported_inferred": exported_explicit is None,
            "enabled": enabled,
            "permission": permission,
            "process": process,
            "has_intent_filter": _has_intent_filter(tag, name),
            "risk": risk,
        }
        for attr in extra_attrs:
            info[attr] = _attr(tag, attr, name)
        return info

    result = {}

    # Activity
    try:
        activities = [
            _component("activity", n, [
                "launchMode", "taskAffinity", "noHistory", "configChanges",
                "screenOrientation", "windowSoftInputMode", "theme",
            ])
            for n in apk_obj.get_activities()
        ]
        result["activities"] = activities
    except Exception:
        result["activities"] = []

    # Activity aliases
    try:
        aliases = [
            _component("activity-alias", n, [
                "targetActivity", "launchMode", "taskAffinity", "noHistory",
            ])
            for n in apk_obj.get_activity_aliases()
        ]
        result["activity_aliases"] = aliases
    except Exception:
        result["activity_aliases"] = []

    # Service
    try:
        services = [
            _component("service", n, [
                "foregroundServiceType", "isolatedProcess", "exported",
            ])
            for n in apk_obj.get_services()
        ]
        result["services"] = services
    except Exception:
        result["services"] = []

    # Receiver
    try:
        receivers = [
            _component("receiver", n, ["exported"])
            for n in apk_obj.get_receivers()
        ]
        result["receivers"] = receivers
    except Exception:
        result["receivers"] = []

    # Provider
    try:
        providers = []
        for n in apk_obj.get_providers():
            c = _component("provider", n, [
                "authorities", "grantUriPermissions", "readPermission",
                "writePermission", "uriPermissionPatterns", "multiprocess",
                "initOrder",
            ])
            # provider 风险修正：导出且无 read/writePermission 保护
            rp = c.get("readPermission")
            wp = c.get("writePermission")
            if c["exported_effective"] and not (c["permission"] or rp or wp):
                c["risk"] = "exposed"
            else:
                c["risk"] = "safe"
            providers.append(c)
        result["providers"] = providers
    except Exception:
        result["providers"] = []

    # 汇总
    exposed = {"activities": 0, "activity_aliases": 0, "services": 0,
               "receivers": 0, "providers": 0}
    totals = dict(exposed)
    for kind in exposed:
        for c in result.get(kind, []):
            totals[kind] += 1
            if c.get("risk") == "exposed":
                exposed[kind] += 1
    result["summary"] = {
        "total_components": sum(totals.values()),
        "exposed_unprotected": sum(exposed.values()),
        "exposed_by_type": exposed,
        "total_by_type": totals,
    }
    return result


def apk_deeplinks(apk_obj) -> dict:
    """
    深链接（deep link）枚举——遍历 manifest 的 intent-filter/data 标签，提取
    每个 URI 入口的 scheme/host/port/path + 关联组件 + 是否可浏览器触发。

    与 apk component-details（组件安全属性，不含 intent data）、apk intent-filters
    （仅 action/category，不含 data）的区别：本命令专门解析 `<data>` 标签，把
    scheme://host/path 形式的**外部 URI 入口**与其处理组件关联，并标记 BROWSABLE
    + VIEW（可被浏览器/其他 App 通过链接直接唤起的真正 deep link）——这是 deep
    link 劫持 / 未授权 URI 访问 / WebView 注入的核心攻击面。

    :param apk_obj: androguard APK 对象
    :return: 深链接枚举
    """
    NS = "{http://schemas.android.com/apk/res/android}"

    def _a(el, name):
        return el.get(NS + name)

    try:
        xml = apk_obj.get_android_manifest_xml()
    except Exception as e:
        return {"error": f"cannot read manifest: {e}"}

    deeplinks = []
    component_tags = ("activity", "activity-alias", "service", "receiver")
    for tag in component_tags:
        for comp in xml.iter(tag):
            comp_name = _a(comp, "name")
            comp_exported = _a(comp, "exported")
            for itf in comp.iter("intent-filter"):
                actions = [_a(a, "name") for a in itf.iter("action")]
                categories = [_a(c, "name") for c in itf.iter("category")]
                browsable = "android.intent.category.BROWSABLE" in categories
                view = "android.intent.action.VIEW" in actions
                data_tags = list(itf.iter("data"))
                if not data_tags:
                    continue
                for data in data_tags:
                    attrs = {k.replace(NS, ""): v for k, v in data.attrib.items()}
                    if not attrs:
                        continue
                    scheme = attrs.get("scheme")
                    host = attrs.get("host")
                    uri_preview = None
                    if scheme:
                        uri_preview = scheme + "://" + (host or "")
                        path = (attrs.get("path") or attrs.get("pathPrefix")
                                or attrs.get("pathPattern") or "")
                        uri_preview += path
                    deeplinks.append(
                        {
                            "component": comp_name,
                            "component_type": tag,
                            "component_exported": comp_exported,
                            "scheme": scheme,
                            "host": host,
                            "port": attrs.get("port"),
                            "path": attrs.get("path"),
                            "pathPrefix": attrs.get("pathPrefix"),
                            "pathPattern": attrs.get("pathPattern"),
                            "mimeType": attrs.get("mimeType"),
                            "browsable": browsable,
                            "view_action": view,
                            "web_reachable": browsable and view and bool(scheme),
                            "uri_preview": uri_preview,
                        }
                    )

    schemes = {}
    for d in deeplinks:
        s = d.get("scheme")
        if s:
            schemes[s] = schemes.get(s, 0) + 1
    web_reachable = [d for d in deeplinks if d["web_reachable"]]

    return {
        "deeplink_count": len(deeplinks),
        "web_reachable_count": len(web_reachable),
        "schemes": dict(sorted(schemes.items(), key=lambda x: -x[1])),
        "deeplinks": deeplinks,
    }
