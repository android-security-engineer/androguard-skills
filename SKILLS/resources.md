# Android 资源解析

> ARSC 资源解析：包名、语言、类型、配置、字符串

## 命令

### `resources packages`

获取 APK 中的资源包名列表。

```bash
androguard-skills resources packages --apk-path test.apk
```

输出示例：

```json
{
  "total": 1,
  "packages": ["com.example.app"]
}
```

### `resources locales <package>`

获取指定资源包支持的语言/地区列表。

```bash
androguard-skills resources locales "com.example.app" --apk-path test.apk
```

输出示例：

```json
{
  "package": "com.example.app",
  "total": 12,
  "locales": ["default", "zh", "en", "ja", "ko", "de", "fr"]
}
```

> `default` 表示无语言限定符的默认资源。

### `resources types <package>`

获取指定资源包的资源类型列表。

```bash
androguard-skills resources types "com.example.app" --apk-path test.apk
```

输出示例：

```json
{
  "package": "com.example.app",
  "total": 8,
  "types": ["public", "string", "layout", "drawable", "id", "attr", "color", "style"]
}
```

### `resources configs <resource_id>`

获取指定资源 ID 的所有配置变体（不同语言/密度/主题下的值）。

```bash
androguard-skills resources configs 2131230720 --apk-path test.apk
```

> `resource_id` 为整型，如 `0x7f080000` 对应十进制 `2131623936`。

输出示例：

```json
{
  "resource_id": "0x7f080000",
  "total": 3,
  "configs": [
    {"value": "About", "config": "<ARSCResTableConfig ''=(0, 0, ...)>"},
    {"value": "关于", "config": "<ARSCResTableConfig 'zh'=(0, ...)>"},
    {"value": "Sobre", "config": "<ARSCResTableConfig 'pt'=(0, ...)>"}
  ]
}
```

### `resources strings`

获取所有解析后的字符串资源（含多语言）。

```bash
androguard-skills resources strings --apk-path test.apk
```

## 类型化资源查询

按资源类型获取资源键值对（解析自 ARSC 的 XML 表示）。

### `resources bool` / `color` / `dimen` / `integer`

获取指定类型的资源列表。

```bash
androguard-skills resources bool "com.example.app" --apk-path test.apk
androguard-skills resources color "com.example.app" --apk-path test.apk
androguard-skills resources dimen "com.example.app" --apk-path test.apk
androguard-skills resources integer "com.example.app" --apk-path test.apk

# 指定语言
androguard-skills resources color "com.example.app" --locale zh --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `package_name` | 资源包名（用 `resources packages` 查询） |
| `--locale` | 语言（如 zh、en，默认为默认资源） |

输出示例（color）：

```json
{
  "package": "com.example.app",
  "type": "color",
  "locale": "default",
  "total": 3,
  "resources": [
    {"name": "colorPrimary", "value": "#ff3f51b5"},
    {"name": "colorAccent", "value": "#ffff4081"}
  ]
}
```

### `resources id`

资源 ID 双向查询。

```bash
# ID → 名称（传 --rid）
androguard-skills resources id "com.example.app" --rid 2131230720 --apk-path test.apk

# 名称 → ID（传 --type --key）
androguard-skills resources id "com.example.app" --type string --key app_name --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `package_name` | 资源包名 |
| `--rid` | 资源 ID（十进制），用于 ID→名称查询 |
| `--type` | 资源类型（string/color/layout/id 等），用于名称→ID 查询 |
| `--key` | 资源键名，用于名称→ID 查询 |

输出示例（ID→名称）：

```json
{
  "package": "com.example.app",
  "query": "id_to_name",
  "resource_id": "0x7f080000",
  "type": "string",
  "key": "about",
  "resolved_id": 2131230720,
  "xml_name": "@com.example.app:string/about"
}
```

输出示例（名称→ID）：

```json
{
  "package": "com.example.app",
  "query": "name_to_id",
  "type": "string",
  "key": "app_name",
  "resource_id": "0x7f080001",
  "decimal_id": 2131230721,
  "xml_name": "@com.example.app:string/app_name"
}
```

## 资源 XML 导出

导出 ARSC 解析后的标准 Android 资源 XML（strings.xml / public.xml / ids.xml），既可解析为结构化列表，也可返回原始 XML 文本。

### `resources string-resources`

获取指定包+语言的字符串资源（strings.xml）。

```bash
# 解析为列表
androguard-skills resources string-resources "com.example.app" --apk-path test.apk

# 返回原始 XML
androguard-skills resources string-resources "com.example.app" --raw --apk-path test.apk

# 指定语言
androguard-skills resources string-resources "com.example.app" --locale zh --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `package_name`（位置参数） | 资源包名 |
| `--locale` | 语言（如 zh、en，默认为默认资源） |
| `--raw` | 返回原始 XML 文本而非解析列表 |

输出示例（解析）：

```json
{
  "package": "com.example.app",
  "locale": "default",
  "total": 56,
  "resources": [
    {"name": "about", "value": "About"},
    {"name": "appName", "value": "Editor"}
  ]
}
```

> 与 `resources strings` 的区别：`strings` 返回所有包的字符串混合列表；`string-resources` 按**指定包+语言**返回，且支持 `--raw` 导出可直接使用的 strings.xml。

### `resources strings-all`

获取所有包的字符串资源（全量 strings.xml，含多语言）。

```bash
androguard-skills resources strings-all --apk-path test.apk
androguard-skills resources strings-all --raw --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--raw` | 返回原始 XML 文本 |

> 全量字符串（含所有包和语言），适合一次性导出做离线分析。`--raw` 输出可重定向到文件作为 strings.xml。

### `resources public`

获取 public.xml（所有资源的 type/name/id 完整映射）。

```bash
androguard-skills resources public "com.example.app" --apk-path test.apk
androguard-skills resources public "com.example.app" --raw --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `package_name`（位置参数） | 资源包名 |
| `--locale` | 语言（可选） |
| `--raw` | 返回原始 XML 文本 |

输出示例（解析）：

```json
{
  "package": "com.example.app",
  "locale": "default",
  "total": 174,
  "resources": [
    {"type": "array", "name": "typefaces", "id": "0x7f010000"},
    {"type": "string", "name": "about", "id": "0x7f080000"}
  ]
}
```

> public.xml 是 aapt 生成的资源 ID 注册表，包含**所有**资源的 type/name/id 三元组。可用于：① 批量 ID→name 反查（比 `resources id` 逐个查快）；② 重建 resources.arsc；③ 检测未使用的资源。

### `resources id-resources`

获取 ids.xml（id 类型资源列表）。

```bash
androguard-skills resources id-resources "com.example.app" --apk-path test.apk
androguard-skills resources id-resources "com.example.app" --raw --apk-path test.apk
```

> ids.xml 包含 `<item type="id" name="x">false</item>` 形式的 id 资源声明，常用于 `findViewById` 的视图 ID。某些 APK 可能没有 ids.xml（输出 total 为 0）。

### `resources get-string`

按包名+键名+语言精确获取单个字符串资源值。

```bash
androguard-skills resources get-string "com.example.app" "app_name" --apk-path test.apk
androguard-skills resources get-string "com.example.app" "about" --locale zh --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `package_name`（位置参数） | 资源包名 |
| `name`（位置参数） | 字符串资源键名 |
| `--locale` | 语言（可选） |

输出示例：

```json
{
  "package": "com.example.app",
  "name": "about",
  "value": "About",
  "locale": "default"
}
```

> 与 `resources id`（name→id）的区别：`get-string` 返回字符串资源的**值**（如本地化文本），而非资源 ID。适合精确读取某个已知键名的字符串（如 `app_name`、`about`）。

### `resources xml-name <resource_id>`

资源 ID → 可读的 XML 名称（如 `@pkg:type/name`）。直接给定 rid，返回其规范 XML 引用名，适合反编译/manifest 中 `@7Fxxxxxx` 引用的快速反解。

```bash
# 支持 hex 或十进制
androguard-skills resources xml-name 0x7f020000 --apk-path test.apk
androguard-skills resources xml-name 2130837504 --apk-path test.apk

# 限定包名（缩小查找范围）
androguard-skills resources xml-name 0x7f020000 --package com.example.app --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `resource_id`（位置参数） | 资源 ID（支持 `0x7f020000` hex 或十进制） |
| `--package` | 资源包名（可选，缩小查找范围） |

**输出：**
```json
{
  "resource_id": "0x7f020000",
  "decimal_id": 2130837504,
  "xml_name": "@org.billthefarmer.editor:attr/application",
  "found": true
}
```

> 与 `resources id --rid`（返回 type/key，需十进制）的区别：本命令返回完整 `@pkg:type/name` 引用名，且支持 hex 输入，适合反编译输出中对齐。`found: false` 表示 rid 未在资源表中找到。

### `resources type-configs <package> [--type]`

获取资源类型的配置变体列表（语言/密度/屏幕等）。返回每个类型下存在的所有 `ARSCResTableConfig`，例如 `--type string` 时返回该包 string 资源的所有 locale 配置（default/fa/ja/...）。

```bash
# 某类型的配置变体（如 string 资源支持哪些语言）
androguard-skills resources type-configs com.example.app --type string --apk-path test.apk

# 全部类型的配置概览
androguard-skills resources type-configs com.example.app --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `package_name`（位置参数） | 资源包名 |
| `--type` | 资源类型过滤（如 string/color；不指定返回全部类型） |

**输出：**
```json
{
  "package": "com.example.app",
  "filter_type": "string",
  "total_types": 1,
  "types": [
    {
      "type": "string",
      "total": 24,
      "configs": [
        {"name": "", "qualifier": "", "language": "", "country": "", "density": 0, "is_default": true, "raw": "<ARSCResTableConfig ...>"},
        {"name": "fa", "qualifier": "fa", "language": "fa", "country": "", "density": 0, "is_default": false, "raw": "..."}
      ]
    }
  ]
}
```

> 用于审计 APK 支持的 locale 列表（配合 `locales` 命令）。`name`/`qualifier` 为空表示默认配置。

### `resources res-configs <resource_id>`

按资源 ID 查询配置变体（**原始 entry 视图**）。与 `configs`（`get_resolved_res_configs`，返回 cfg+解析后的字面值）的区别：本命令走 `get_res_configs`，返回原始 `ARSCResTableEntry`（含 `mResId`/`flags`/`complex` 父引用），适合资源表底层结构分析。每项含 config（locale/密度）+ entry（原始表项）。

```bash
# 支持 hex 或十进制
androguard-skills resources res-configs 0x7f020000 --apk-path test.apk
androguard-skills resources res-configs 2130837504 --apk-path test.apk

# 不回退到默认配置（只返回精确匹配的配置）
androguard-skills resources res-configs 0x7f020000 --no-fallback --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `resource_id`（位置参数） | 资源 ID（支持 `0x7f020000` hex 或十进制） |
| `--no-fallback` | 找不到精确配置时不回退到默认配置 |

**输出：**
```json
{
  "resource_id": "0x7f020000",
  "decimal_id": 2130837504,
  "fallback": true,
  "total": 1,
  "configs": [
    {
      "config": {"name": "", "qualifier": "", "language": "", "country": "", "density": 0, "is_default": true, "raw": "<ARSCResTableConfig ...>"},
      "entry": {"idx": "0x0000a764", "mResId": 2130837504, "flags": 1, "complex": {"idx": "0x0000a76c", "parent": 0, "count": 1}}
    }
  ]
}
```

> 与 `configs`（resolved，含解析值）的区别：本命令返回原始 entry，含 `mResId`/`flags`/`complex`（`ARSCComplex` 父引用、子项计数），用于资源表结构研究。`flags=1` 表示该资源是 complex（样式/多配置）类型。`--no-fallback` 时若该 rid 无精确配置则返回空（不回退默认）。

### `resources value <resource_id> [--package]`

按资源 ID 取**类型化解析值**。与 `res-configs`（原始 entry 视图）和 `configs`（resolved cfg+字面值）的区别：本命令先通过 `get_resource_xml_name` 推断资源类型（string/bool/color/dimen/integer/style/id），再按类型调对应的 `get_resource_*` 方法解析出值，返回主值 + 各类型方法的全量解析结果，适合「拿到 rid 后想知道它实际是什么值」的快速反解场景。

```bash
# 支持 hex 或十进制
androguard-skills resources value 0x7f080020 --apk-path test.apk
androguard-skills resources value 2131230720 --apk-path test.apk

# 指定包名（多包 APK）
androguard-skills resources value 0x7f080020 --package org.billthefarmer.editor --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `resource_id`（位置参数） | 资源 ID（支持 `0x7f080020` hex 或十进制） |
| `--package` | 资源包名（可选，多包 APK 时指定） |

**输出：**
```json
{
  "resource_id": 2131362848,
  "type": "string",
  "xml_name": "@org.billthefarmer.editor:string/about",
  "value": "About",
  "parsed": {
    "get_resource_string": ["about", "About"],
    "get_resource_bool": ["about"],
    "get_resource_color": ["about", "#0000003f"],
    "get_resource_dimen": ["about", 63],
    "get_resource_integer": ["about", 63],
    "get_resource_style": ["", ""],
    "get_resource_id": ["about"]
  }
}
```

| 字段 | 说明 |
|------|------|
| `type` | 推断的资源类型（`get_resource_xml_name` 返回的 `@pkg:type/name` 中的 type） |
| `xml_name` | 资源的 XML 引用名（`@pkg:type/name`） |
| `value` | 主值（按推断类型对应方法的解析结果末元素，如 string 资源取 `get_resource_string` 的字面值） |
| `parsed` | 所有 `get_resource_*` 方法的解析结果，键是方法名，值是该方法的返回（list/tuple）。注意非主类型的结果是对同一 entry 强行按其他类型解析的产物，仅作参考 |

> 底层 API：`ARSCParser.get_resource_xml_name(rid, package)` 推断类型 → `get_res_configs(rid, fallback=True)` 取 entry → 按类型调 `get_resource_string`/`get_resource_bool`/`get_resource_color`/`get_resource_dimen`/`get_resource_integer`/`get_resource_style`/`get_resource_id`。`value` 取主类型方法的末元素（如 string 资源 `get_resource_string` 返回 `["about", "About"]`，取 `"About"`）。

### `resources resolved-strings [--locale]`

获取全量解析后的字符串资源（保留 `package→locale→rid` 三层结构）。与 `strings`（扁平化为 package/key/value，丢失 locale 和 rid）的区别：本命令保留完整嵌套，含 rid 和所有 locale，适合多语言资源全量审计。

```bash
# 全量（所有包所有语言）
androguard-skills resources resolved-strings --apk-path test.apk

# 只看某语言
androguard-skills resources resolved-strings --locale fa --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--locale` | 语言过滤（如 `fa`/`ja`；不指定返回全部） |

**输出：**
```json
{
  "total": 56,
  "total_packages": 1,
  "filter_locale": "fa",
  "packages": [
    {
      "package": "org.billthefarmer.editor",
      "total_locales": 1,
      "locales": [
        {
          "locale": "fa",
          "total": 56,
          "strings": [
            {"rid": 2131230720, "value": "درباره"},
            {"rid": 2131230721, "value": "ویرایشگر"}
          ]
        }
      ]
    }
  ]
}
```

> 与 `strings`（扁平化、丢失 locale/rid）和 `strings-all`（合并 XML、单维度）的区别：本命令保留三层结构，每个字符串带 rid（可用于反汇编中 const-string 引用的反解）和所属 locale。`total` 是所有 locale 下的字符串总数。

## 安全分析用途

- **信息泄露**：字符串资源可能包含硬编码的 URL、密钥、错误信息
- **多语言分析**：不同语言的字符串可能有不同的隐私政策描述
- **资源枚举**：识别隐藏功能入口（未在代码中引用的布局/菜单）
- **配置差异**：不同配置下的资源值差异可能暴露条件逻辑
- **颜色资源**：`color` 资源可能用于 UI 伪装（如钓鱼界面配色）
- **ID 映射**：`resources id` 用于在反编译代码中的资源引用（如 `0x7f080000`）与资源名之间转换
- **布尔配置**：`bool` 资源常用于功能开关，可能暴露隐藏功能
- **批量 ID 反查**：`resources public` 一次导出所有 type/name/id，用于批量解析反编译代码中的资源引用
- **XML 导出**：`--raw` 模式导出的 strings.xml/public.xml 可用于重建项目或离线 diff 比对两个版本 APK 的资源差异
- **本地化审计**：`get-string --locale` 比对不同语言下同一键名的值，可能发现隐藏的市场特定行为


