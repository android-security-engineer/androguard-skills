# 模块：util_skills

> 📌 工具函数集：文件类型检测、AOSP 权限数据加载、证书名格式化、类名格式转换。

## 🧩 概述

`util_skills.py` 封装 `androguard.core.androconf` 与 `androguard.util` 的杂项能力，共 8 个公开函数。这些函数大多不依赖已加载的 APK/DEX，而是面向「纯数据查询」（权限表、API level 列表）或「无状态转换」（类名格式、指纹计算），因此 CLI 层调用它们时通常不需要 daemon 持有引擎对象。

在三层架构中位于**业务层**，但偏工具属性——部分函数第一参数是普通值（文件名、字节、字符串）而非引擎对象。遵循模块级函数约定，无类、无状态。

## 🔧 公开方法

| 方法名 | 签名 | 说明 | 对应 CLI 命令 |
|--------|------|------|-------------|
| `util_detect_file` | `(filename: str)` | 检测文件的 Android 类型（APK/DEX/ODEX/ELF） | `util detect` |
| `util_detect_raw` | `(data: bytes)` | 检测原始字节的 Android 类型 | 无 CLI（需原始字节，CLI 层无入口） |
| `util_permissions` | `(apilevel)` | 加载指定 API level 的 AOSP 权限定义 | `util permissions` |
| `util_permission_mappings` | `(apilevel)` | 加载指定 API level 的方法签名 → 权限映射 | `util permission-mappings` |
| `util_certificate_name_string` | `(name_obj, short: bool = True)` | 将 asn1crypto Name 对象格式化为可读字符串 | 无 CLI（需 asn1crypto Name 对象，内部使用） |
| `util_calculate_fingerprint` | `(public_key_info)` | 计算公钥的 SHA-256 指纹（hex + base64） | 无 CLI（需公钥字节，内部使用） |
| `util_available_api_levels` | `()` | 列出本地可用的权限数据 API level | `util api-levels` |
| `util_format` | `(value: str, to: str = "java")` | Dalvik/Java/Python 类名与描述符双向转换 | `util format` |

## 🧩 关键实现要点

- **`util_format` 自实现转换**：AndroGuard 内置的 `FormatClassToJava` / `FormatClassToPython` 存在 bug（Python 版截断类名、`FormatNameToPython` 不转换）。本函数完全自实现 `to_java` / `to_dalvik` / `to_python` 三个内部闭包，并自动识别输入格式（含 `L/;` 为 Dalvik、含 `.` 为 Java），还单独处理方法描述符（含括号场景），保证三种目标格式互转无信息丢失。
- **`util_available_api_levels` 扫描资源目录**：不依赖引擎，直接 `os.listdir` 扫描 `androconf.__file__` 同级下的 `aosp_permissions/` 与 `api_permission_mappings/`（兼容 `api_specific_resources/` 子目录两种布局），用正则 `^permissions_(\d+)\.json$` 提取 level，分别归入 `permissions` / `permission_mappings` 两个列表并排序。
- **`util_calculate_fingerprint` 双编码输出**：调用 `androguard.util.calculate_fingerprint` 得到原始字节后，同时返回 `fingerprint_hex` 与 `fingerprint_base64`，省去调用方二次转换。
- **`util_permissions` / `util_permission_mappings` 纯数据**：直接转发 `androconf.load_permissions` / `load_permission_mappings`，附 `total` 计数，便于 CLI 层做截断与统计展示。

## 🔗 与 CLI 的映射

`main.py` 的 `util` 命令组通过 `_try_daemon_call("util_detect_file", ...)` 等走 daemon；这几个命令多为纯数据查询，daemon 模式下也能直接响应。非 daemon 模式由 `AndroguardSkills` 实例直接调用 `util_skills.*`。

## 📚 相关

- [代码模块总览](./)
- 命令组文档：`/commands/util/`
