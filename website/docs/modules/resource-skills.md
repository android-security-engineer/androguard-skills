# 模块：resource_skills

> 📌 封装 `androguard.core.apk.ARSC` 资源解析，提供包/语言/类型/配置/字符串/ID 双向查询。

## 🧩 概述

`resource_skills.py` 共 20 个公开函数，全部围绕 `ARSC`（已编译资源表 `resources.arsc`）展开。它把 `ARSC` 对象的方法封装成返回 `dict` 的纯函数，覆盖：包枚举、语言/配置变体、按类型取值（string/bool/color/dimen/integer）、资源 ID 双向查询、`public.xml` / `ids.xml` 导出、配置变体查询等。

在三层架构中位于**业务层**：第一参数是 `arsc_obj`（由 APK 加载时 `apk_obj.get_android_resources()` 得到），输出是结构化字典。遵循模块级函数约定，无类、无状态。默认 `locale = "\x00\x00"` 表示根语言（默认语言）。

## 🔧 公开方法

| 方法名 | 签名 | 说明 | 对应 CLI 命令 |
|--------|------|------|-------------|
| `resource_packages` | `(arsc_obj)` | 获取资源包名列表 | `resources packages` |
| `resource_locales` | `(arsc_obj, package_name)` | 指定包支持的语言/地区列表 | `resources locales` |
| `resource_types` | `(arsc_obj, package_name)` | 指定包的资源类型列表 | `resources types` |
| `resource_configs` | `(arsc_obj, resource_id)` | 指定资源 ID 的所有配置 | `resources configs` |
| `resource_strings` | `(arsc_obj)` | 所有解析后的字符串资源 | `resources strings` |
| `resource_bool` | `(arsc_obj, package_name, locale = "\x00\x00")` | 布尔类型资源 | `resources bool` |
| `resource_color` | `(arsc_obj, package_name, locale = "\x00\x00")` | 颜色类型资源 | `resources color` |
| `resource_dimen` | `(arsc_obj, package_name, locale = "\x00\x00")` | 尺寸类型资源 | `resources dimen` |
| `resource_integer` | `(arsc_obj, package_name, locale = "\x00\x00")` | 整数类型资源 | `resources integer` |
| `resource_id` | `(arsc_obj, package_name, resource_id = None, resource_type = None, key = None, locale = "\x00\x00")` | 资源 ID 双向查询 | `resources id` |
| `resource_string_resources` | `(arsc_obj, package_name, locale = "\x00\x00", raw = False)` | 指定包+语言的字符串资源（strings.xml） | `resources string-resources` |
| `resource_strings_all` | `(arsc_obj, raw = False)` | 所有包的字符串资源（全量 strings.xml） | `resources strings-all` |
| `resource_public` | `(arsc_obj, package_name, locale = "\x00\x00", raw = False)` | public.xml（type/name/id 完整映射） | `resources public` |
| `resource_id_resources` | `(arsc_obj, package_name, locale = "\x00\x00", raw = False)` | ids.xml（id 类型资源列表） | `resources id-resources` |
| `resource_get_string` | `(arsc_obj, package_name, name, locale = "\x00\x00")` | 按包名+键名+语言精确取单个字符串值 | `resources get-string` |
| `resource_xml_name` | `(arsc_obj, resource_id, package = None)` | 资源 ID → 可读 XML 名称（@pkg:type/name） | `resources xml-name` |
| `resource_type_configs` | `(arsc_obj, package_name, resource_type = None)` | 资源类型的配置变体列表 | `resources type-configs` |
| `resource_res_configs` | `(arsc_obj, resource_id, fallback = True)` | 按资源 ID 查配置变体（原始 entry 视图） | `resources res-configs` |
| `resource_resolved_strings` | `(arsc_obj, locale = None)` | 全量解析后字符串（保留 package→locale→rid 三层结构） | `resources resolved-strings` |
| `resource_value` | `(arsc_obj, resource_id, package = None)` | 按 ID 取类型化解析值（自动识别 string/bool/int/color/dimen/integer/style/id） | `resources value` |

## 🧩 关键实现要点

- **`resource_id` 双向查询**：既能 ID→名称（给定 `resource_id` 查 `type/name`），也能名称→ID（给定 `resource_type` + `key` 查 ID），由哪个参数非空决定方向，是资源解析最常用的入口。
- **`raw` 开关**：`resource_string_resources` / `resource_strings_all` / `resource_public` / `resource_id_resources` 都支持 `raw` 参数，控制返回 ARSC 原始结构还是规整后的字典，便于既可人读又可机器遍历。
- **`resource_value` 类型自动识别**：按资源 ID 取值时一次性尝试 string/bool/int/color/dimen/integer/style/id 多种类型，命中即返回带 `type` 标签的值，免去调用方按类型分别试。
- **`resource_resolved_strings` 三层结构**：保留 `package → locale → resource_id` 的完整嵌套，区别于 `resource_strings`（扁平化），适合做多语言资源对比。

## 🔗 与 CLI 的映射

`main.py` 的 `resources` 命令组通过 `_try_daemon_call("resource_packages", {...})` 等走 daemon；daemon 端从已加载的 APK 取出 `arsc_obj` 后调用本模块函数。非 daemon 模式由 `AndroguardSkills` 实例直接调用 `resource_skills.*`。

## 📚 相关

- [代码模块总览](./)
- 命令组文档：`/commands/resources/`
