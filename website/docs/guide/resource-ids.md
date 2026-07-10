# 资源 ID 体系

> 🎨 Android 资源用 32 位整数 ID 标识。这一页讲 ID 的结构、如何查询、以及 Skills 资源命令的关系。

## 资源 ID 结构

一个资源 ID 是 32 位整数，分三段：

```
  0x7F080001
  ─┬─ ─┬─ ─┬─
   │   │   └─ entry index（条目索引）
   │   └───── type index（类型索引，如 string/layout/drawable）
   └───────── package index（包索引，应用自己的通常是 0x7F）
```

- `0x7F` —— 应用自有资源包（`application` package）。
- `0x01` —— 系统资源包（`android` package）。

## Manifest 与代码里的资源引用

AndroidManifest.xml 与代码里的 `@string/app_name`、`@drawable/icon` 在编译后变成数字 ID：

```xml
<!-- 编译前 -->
<application android:label="@string/app_name" ...>

<!-- 编译后（AXML 里是数字） -->
<application android:label="@7F0F0001" ...>
```

要把数字 ID 还原成可读引用，用 `resources xml-name`：

```bash
androguard-skills resources xml-name 2131099649
# → {"xml_name": "@string/app_name"}
```

## 取资源值

拿到 ID 后想看实际值，用 `resources value`：

```bash
androguard-skills resources value 2131099649
# → {"type": "string", "value": "MyApp"}
```

它会自动推断类型（string/bool/int/color/dimen/integer/style/id）并返回主值。

## apk 组里的资源反解

Manifest 里的属性值常是资源 ID。`apk res-value` 直接反解：

```bash
androguard-skills apk res-value @7F0F0001
# 或用十进制
androguard-skills apk res-value 2131099649
```

## 资源 ID 双向查询

`resources id` 支持两个方向：

```bash
# ID → name（已知数字 ID，查类型+名）
androguard-skills resources id android --rid 2131099649

# name → ID（已知类型+名，查数字 ID）
androguard-skills resources id android --type string --key app_name
```

## 包 / locale / 类型 / 配置

ARSC（资源表）是四维结构：

```
Package（包，如 "android" / 应用包）
  └─ Locale（语言地区，如 "" 默认 / "zh" / "en-rUS"）
      └─ Type（类型，如 string / layout / drawable）
          └─ Config（配置变体，如 hdpi / xhdpi / night）
              └─ Entry（具体条目）
```

对应命令：

| 维度 | 命令 |
|------|------|
| 列出所有包 | `resources packages` |
| 列出某包的 locale | `resources locales <pkg>` |
| 列出某包的类型 | `resources types <pkg>` |
| 列出某 ID 的配置变体 | `resources configs <rid>` |
| 取某 ID 的值 | `resources value <rid>` |

## 常用工作流

### "这个 Manifest 里的数字是什么资源？"

```bash
# 1. 从 manifest-attrs 拿到属性值（可能是 @7Fxxxxxx）
androguard-skills apk manifest-attrs --tag application --attribute label

# 2. 反解为可读引用
androguard-skills resources xml-name 2131099649
# → @string/app_name

# 3. 取实际值
androguard-skills resources value 2131099649
# → "MyApp"
```

### "导出所有字符串资源"

```bash
androguard-skills resources strings-all
# 全量 strings.xml，含多包多语言
```

### "这个应用支持哪些语言？"

```bash
androguard-skills resources packages        # 先看包名
androguard-skills resources locales <pkg>   # 再列 locale
```

## 相关文档

- [resources 命令组](../commands/resources/)
- [apk res-value 命令](../commands/apk/res-value)
- [类名与描述符](./class-descriptors)

---

👈 [类名与描述符](./class-descriptors) · [Python API →](./python-api) 👉
