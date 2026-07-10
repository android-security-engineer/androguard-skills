# 模块：apk_skills

> 📌 APK 维度业务逻辑：manifest、签名、组件、权限、文件、资源、安全概览等 54 个公开函数。

## 🧩 概述

`apk_skills.py` 共 54 个公开函数，围绕 `androguard.core.apk.APK` 对象展开，覆盖 APK 静态信息的方方面面：基本元数据、四大组件、权限、签名（v1/v2/v3/v3.1 多方案）、文件清单与 CRC、AXML 解析、SDK 版本、native 库、深链接、应用图标，以及一键安全概览。

在三层架构中位于**业务层**：第一参数是 `apk_obj`（由 `load_apk` 加载并缓存于 daemon / `AndroguardSkills` 实例），输出是结构化字典。遵循模块级函数约定，无类、无状态。所有签名相关函数默认 `scheme='v3'`，图标 `max_dpi=65536`。

## 🔧 公开方法

| 方法名 | 签名 | 说明 | 对应 CLI 命令 |
|--------|------|------|-------------|
| `apk_info` | `(apk_obj)` | APK 基本信息 | `apk info` |
| `apk_permissions` | `(apk_obj)` | APK 权限信息 | `apk permissions` |
| `apk_activities` | `(apk_obj)` | Activity 列表 | `apk activities` |
| `apk_services` | `(apk_obj)` | Service 列表 | `apk services` |
| `apk_receivers` | `(apk_obj)` | BroadcastReceiver 列表 | `apk receivers` |
| `apk_providers` | `(apk_obj)` | ContentProvider 列表 | `apk providers` |
| `apk_intent_filters` | `(apk_obj, component_name)` | 指定组件的 Intent Filter | `apk intent-filters` |
| `apk_signature` | `(apk_obj)` | APK 签名信息 | `apk signature` |
| `apk_files` | `(apk_obj)` | APK 文件列表 | `apk files` |
| `apk_manifest` | `(apk_obj)` | AndroidManifest.xml 内容 | `apk manifest` |
| `apk_features` | `(apk_obj)` | uses-feature 列表 | `apk features` |
| `apk_libraries` | `(apk_obj)` | uses-library 列表 | `apk libraries` |
| `apk_icon` | `(apk_obj, max_dpi=65536)` | 应用图标信息 | `apk icon` |
| `apk_file` | `(apk_obj, filename)` | 提取指定文件内容 | `apk file` |
| `apk_verify` | `(apk_obj)` | 验证 APK 完整性 | `apk verify` |
| `apk_signing_block` | `(apk_obj)` | v2/v3 签名块详情 | `apk signing-block` |
| `apk_manifest_attrs` | `(apk_obj, tag_name, attribute, attribute_filter=None)` | 批量提取 manifest 标签属性值 | `apk manifest-attrs` |
| `apk_manifest_attr` | `(apk_obj, tag_name, attribute, attribute_filter=None)` | 提取单个标签属性值（首个匹配） | `apk manifest-attr` |
| `apk_certificate` | `(apk_obj, filename=None)` | 签名证书详情 | `apk certificate` |
| `apk_verify_signature` | `(apk_obj, filename=None)` | 签名密码学验证 | `apk verify-signature` |
| `apk_files_info` | `(apk_obj)` | 所有文件详情（名称/类型/CRC32） | `apk files-info` |
| `apk_dex_data` | `(apk_obj, all_dex=False)` | 提取 DEX 二进制（base64） | `apk dex-data` |
| `apk_raw` | `(apk_obj)` | 整个 APK 原始字节（base64） | `apk raw` |
| `apk_manifest_tags` | `(apk_obj, tag_name, attribute_filter=None)` | 按属性过滤查找 manifest 标签 | `apk manifest-tags` |
| `apk_signing_versions` | `(apk_obj)` | 检测支持的签名方案（v1/v2/v3/v3.1） | `apk signing-versions` |
| `apk_certificates_scheme` | `(apk_obj, scheme='v3')` | 按签名方案批量取证书详情 | `apk certificates-scheme` |
| `apk_certificates_der` | `(apk_obj, scheme='v3')` | 按方案取证书 DER 二进制（base64） | `apk certificates-der` |
| `apk_public_keys` | `(apk_obj, scheme='v3')` | 按方案取签名公钥信息 | `apk public-keys` |
| `apk_signature_files` | `(apk_obj)` | 签名文件信息（文件名+原始签名 base64） | `apk signature-files` |
| `apk_files_crc32` | `(apk_obj)` | 所有文件 CRC32 校验值 | `apk files-crc32` |
| `apk_fingerprint` | `(apk_obj, scheme='v3')` | 签名公钥 SHA-256 指纹 | `apk fingerprint` |
| `apk_manifest_axml` | `(apk_obj)` | AndroidManifest 的 AXML 格式（加固检测+原始 XML） | `apk manifest-axml` |
| `apk_axml` | `(apk_obj, filename, pretty=True)` | 解析任意二进制 AXML 为可读 XML | `apk axml` |
| `apk_declared_permissions` | `(apk_obj)` | APK 声明（自定义）的权限 | `apk declared-permissions` |
| `apk_requested_permissions` | `(apk_obj)` | 请求权限分类（AOSP/第三方/隐含） | `apk requested-permissions` |
| `apk_sdk_versions` | `(apk_obj)` | SDK 版本（min/max/target/effective_target） | `apk sdk-versions` |
| `apk_main_activities` | `(apk_obj)` | 主 Activity（含 aliases） | `apk main-activities` |
| `apk_device_features` | `(apk_obj)` | 设备特性布尔标记（TV/Wearable/Leanback/Multidex） | `apk device-features` |
| `apk_files_types` | `(apk_obj)` | 所有文件类型识别（基于 file 命令） | `apk files-types` |
| `apk_details_permissions` | `(apk_obj)` | 请求权限详情（protection_level/label/description） | `apk details-permissions` |
| `apk_manifest_tree` | `(apk_obj)` | manifest 标签树统计 | `apk manifest-tree` |
| `apk_find_tags_xml` | `(apk_obj, xml_name, tag_name)` | 从指定 XML 文件查找标签 | `apk find-tags-xml` |
| `apk_cert_names` | `(apk_obj, scheme='v3', android=True)` | 证书主题/颁发者规范化名称 | `apk cert-names` |
| `apk_res_value` | `(apk_obj, name)` | 资源 ID（@7F080001）解析为字面值 | `apk res-value` |
| `apk_dex_names` | `(apk_obj)` | 所有 DEX 文件名列表（multidex） | `apk dex-names` |
| `apk_signature_names` | `(apk_obj)` | 所有签名文件名列表 | `apk signature-names` |
| `apk_app_name` | `(apk_obj, locale=None)` | 应用显示名（label 资源反解） | `apk app-name` |
| `apk_valid` | `(apk_obj)` | 是否有效 APK（结构完整性） | `apk valid` |
| `apk_duplicate_signatures` | `(apk_obj)` | 检测重复签名 ID | `apk duplicate-signatures` |
| `apk_security_overview` | `(apk_obj)` | APK 安全概览（一键聚合审计信号） | `apk security-overview` |
| `apk_native_libraries` | `(apk_obj, include_data=False)` | native 库（lib/&lt;abi&gt;/*.so）列表 | `apk native-libraries` |
| `apk_application_flags` | `(apk_obj)` | &lt;application&gt; 安全属性审计（带默认值推断+风险评级） | `apk application-flags` |
| `apk_component_details` | `(apk_obj)` | 所有组件安全属性详情 | `apk component-details` |
| `apk_deeplinks` | `(apk_obj)` | 深链接枚举（intent-filter/data 标签） | `apk deeplinks` |

## 🧩 关键实现要点

- **`apk_security_overview` 一键聚合**：与 `apk_info`（基本信息、无安全维度）不同，本函数聚合安全审计关心的信号——签名验证结果（`is_signed_v1/v2/v3/v31`、`is_valid_APK`、`has_duplicate_apk_signature_ids`，还内嵌调 `apk_verify_signature` 取 v1 密码学验证）、危险权限分类（用 `get_details_permissions` 取 protection_level，筛出 `dangerous`）、manifest 安全标志（`debuggable` / `allowBackup` / `usesCleartextTraffic` / `networkSecurityConfig` / `testOnly` / `extractNativeLibs`）、SDK 版本、加固检测、隐含权限、重复签名，一处输出便于快速体检。每段都用 `try/except` 包裹，单段失败不腐化整体。
- **多签名方案对称**：`apk_certificates_scheme` / `apk_certificates_der` / `apk_public_keys` / `apk_fingerprint` / `apk_cert_names` 都接受 `scheme` 参数（默认 `v3`），按 v1/v2/v3/v3.1 统一接口取证书/公钥/指纹，避免调用方为每种方案写不同代码。
- **AXML 加固检测**：`apk_manifest_axml` 不仅解析 manifest，还做加固检测（原始 AXML 与解压后 XML 比对）；`apk_axml` 则通用地把任意二进制 AXML 文件转可读 XML，`pretty=True` 默认美化输出。
- **base64 二进制导出**：`apk_dex_data` / `apk_raw` / `apk_certificates_der` / `apk_signature_files` 把原始字节 base64 编码后塞进 dict，便于 JSON 传输与 CLI 层落盘。

## 🔗 与 CLI 的映射

`main.py` 的 `apk` 命令组通过 `_try_daemon_call("apk_info", {...})` 等走 daemon JSON-RPC；daemon 端从已加载的 `apk_obj`（`load_apk` 时缓存）取数据。非 daemon 模式由 `AndroguardSkills` 实例直接调用 `apk_skills.apk_info(self._apk)` 等。

## 📚 相关

- [代码模块总览](./)
- 命令组文档：`/commands/apk/`
