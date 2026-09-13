# 字段分析与多维查找

> 多维正则字段查找（类名/字段名/类型/访问标志）、字段完整分析（含 read/write xref 详情）、Android API 使用统计

## 命令

### `analysis find-fields-advanced`

使用 Analysis 原生 `find_fields` 进行多维正则字段查找。

```bash
# 按类名正则查找
androguard-skills analysis find-fields-advanced --classname '.*Editor;' --limit 10 --apk-path test.apk

# 按访问标志查找（所有 private 字段）
androguard-skills analysis find-fields-advanced --accessflags 'private' --limit 10 --apk-path test.apk

# 按字段类型查找（所有 Pattern 类型字段）
androguard-skills analysis find-fields-advanced --fieldtype '.*Pattern.*' --apk-path test.apk

# 含完整 xref 列表
androguard-skills analysis find-fields-advanced --fieldtype '.*Pattern.*' --with-xrefs --limit 5 --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--classname` | 类名正则（默认 `.*`） |
| `--fieldname` | 字段名正则（默认 `.*`） |
| `--fieldtype` | 字段类型正则（默认 `.*`） |
| `--accessflags` | 访问标志正则（如 `private\|static`，默认 `.*`） |
| `--limit` | 返回数量限制 |
| `--with-xrefs` | 展开字段的完整 read/write xref 列表 |

输出示例：

```json
{
  "filters": {"classname": ".*Editor;", "fieldname": ".*", "fieldtype": ".*", "accessflags": ".*"},
  "total": 134,
  "returned": 3,
  "fields": [
    {
      "name": "ANNOTATION",
      "class": "Lcom/example/Editor;",
      "descriptor": "Ljava/util/regex/Pattern;",
      "access_flags": "public static final",
      "xref_read_count": 1,
      "xref_write_count": 1
    }
  ]
}
```

> 与 `analysis find-fields` 的区别：`find-fields` 只能按字段名单维正则匹配；`find-fields-advanced` 支持类名/字段名/类型/访问标志四维正则，且底层用 Analysis 原生 `find_fields`（更快）。

### `analysis find-methods-advanced`

使用 Analysis 原生 `find_methods` 进行**五维正则方法查找**（类名 × 方法名 × 描述符 × 访问标志 × 是否排除外部方法）。这是对单维 `find-methods`（仅按方法名）的完整补齐。

```bash
# 按访问标志查找所有 native 方法（注意：底层用 re.match 锚定行首，需写 .*native）
androguard-skills analysis find-methods-advanced --accessflags '.*native' --no-external --apk-path test.apk

# 按描述符查找（限 crypto 类中返回 String 的方法）
androguard-skills analysis find-methods-advanced --classname '.*[Cc]rypto.*' --descriptor '.*Ljava/lang/String;$' --no-external --apk-path test.apk

# 组合：public static 方法
androguard-skills analysis find-methods-advanced --accessflags 'public.*static' --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--classname` | 类名正则（默认 `.*`） |
| `--methodname` | 方法名正则（默认 `.*`） |
| `--descriptor` | 描述符正则（默认 `.*`，如 `.*Ljava/lang/String;$`） |
| `--accessflags` | 访问标志正则（默认 `.*`） |
| `--no-external` | 排除外部（继承自 framework 的）方法 |
| `--limit` | 返回数量限制（默认 500） |

输出示例：

```json
{
  "filters": {"classname": ".*", "methodname": ".*", "descriptor": ".*", "accessflags": ".*native", "no_external": true},
  "total": 1,
  "truncated": false,
  "methods": [
    {"class": "Lsg/vantagepoint/helloworldjni/MainActivity;", "method": "stringFromJNI", "descriptor": "()Ljava/lang/String;", "access_flags": "public native", "is_external": false}
  ]
}
```

> ⚠️ **`--accessflags` 用 `re.match` 锚定行首**：`--accessflags native` 匹配不到 `public native`（"public" 开头），须写 `.*native`。这是 AndroGuard 原生 `find_methods` 行为。
> 与 `analysis find-methods` 的区别：后者只按方法名单维正则；本命令支持五维过滤，直接调用原生 `find_methods`。**典型用途**：定位 JNI 桥接（`--accessflags '.*native'`）、按签名精确定位重载方法（`--descriptor`）、按可见性审计（`--accessflags 'public'`）。

### `analysis find-classes-advanced`

使用 Analysis 原生 `find_classes` 进行类名正则 + 是否排除外部类的查找，返回每类的外部/API/方法数元信息。

```bash
# 仅内部类（排除 framework）
androguard-skills analysis find-classes-advanced --name '.*insecurebank.*' --no-external --apk-path test.apk

# 全部匹配类（含外部引用）
androguard-skills analysis find-classes-advanced --name '.*Activity.*' --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--name` | 类名正则（默认 `.*`） |
| `--no-external` | 排除外部类（仅返回 APK 内定义的类） |
| `--limit` | 返回数量限制（默认 500） |

输出示例：

```json
{
  "filters": {"name": ".*insecurebank.*", "no_external": true},
  "total": 49,
  "truncated": false,
  "classes": [
    {"name": "Lcom/android/insecurebankv2/BuildConfig;", "is_external": false, "is_android_api": false, "method_count": 2}
  ]
}
```

> 与 `analysis find-classes` 的区别：后者用 `get_classes()` + 正则重实现且只返回类名；本命令调用原生 `find_classes`，支持 `--no-external` 过滤并附带 `is_external`/`is_android_api`/`method_count` 元信息。

### `analysis field-analysis`

获取指定字段的完整分析信息（含 read/write 交叉引用详情）。

```bash
androguard-skills analysis field-analysis "Lcom/example/Editor;" "ANNOTATION" --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `class_name`（位置参数） | 类名 |
| `field_name`（位置参数） | 字段名 |

输出示例：

```json
{
  "class": "Lcom/example/Editor;",
  "field": "ANNOTATION",
  "descriptor": "Ljava/util/regex/Pattern;",
  "access_flags": "public static final",
  "xref_read_count": 1,
  "xref_read": [
    {"class": "Lcom/example/Editor;", "method": "highlightText", "descriptor": "()V"}
  ],
  "xref_write_count": 1,
  "xref_write": [
    {"class": "Lcom/example/Editor;", "method": "<clinit>", "descriptor": "()V"}
  ]
}
```

> 与 `analysis field-xrefs` 的区别：`field-xrefs` 只返回 xref 列表；`field-analysis` 同时返回字段的描述符和访问标志，且通过原生 `find_fields` 精确匹配类名，更稳健。

### `analysis class-fields <class>`

列出指定类的**全部字段**及其交叉引用**计数**（类级字段视图）。

与 `field-xrefs`/`field-analysis`（单字段全 xref）和 `find-fields`（全局正则搜索）的区别：本命令遍历 `ClassAnalysis.get_fields()` 一次列出类内所有字段，每项只含 `xref_read_count`/`xref_write_count` **计数**（不带完整引用列表，避免输出过大），用于快速定位类内哪些字段被频繁读写——状态字段、配置字段、敏感字段往往有较高读写计数。

```bash
androguard-skills analysis class-fields "Lorg/billthefarmer/editor/Editor;" --apk-path test.apk

# 限制返回数量
androguard-skills analysis class-fields "Lcom/example/Foo;" --limit 10 --apk-path test.apk
```

输出示例：

```json
{
  "class": "Lorg/billthefarmer/editor/Editor;",
  "is_external": false,
  "fields_total": 134,
  "returned": 5,
  "fields": [
    {"name": "ANNOTATION", "descriptor": "Ljava/util/regex/Pattern;", "access_flags": "...", "xref_read_count": 1, "xref_write_count": 1},
    {"name": "BLACK", "descriptor": "I", "access_flags": "public static final", "xref_read_count": 0, "xref_write_count": 0},
    ...
  ]
}
```

| 字段 | 说明 |
|------|------|
| `fields_total` | 类内字段总数（即使 `--limit` 截断仍返回完整总数） |
| `name`/`descriptor`/`access_flags` | 字段元数据 |
| `xref_read_count` | 该字段被读取的引用数（计数，非完整列表） |
| `xref_write_count` | 该字段被写入的引用数 |

> 读写计数为 0 的字段（如 `BLACK` static final 常量）通常是硬编码常量——可配 `dex field-init-value` 查其初始值。计数高的字段可配 `field-xrefs-detail` 查完整引用。底层 API：`ClassAnalysis.get_fields()` → `FieldAnalysis`，其 `get_xref_read()`/`get_xref_write()`（`with_offset=False`）。

### `analysis class-fields-xref <class> [--xref-limit]`

列出类内所有字段的**完整读写交叉引用**（哪些方法读/写了每个字段）。

与 `class-fields`（仅 xref 计数）和 `field-xrefs-detail`（单字段全 xref）的区别：本命令遍历类内所有字段并展开完整读写来源列表——每个字段列出 `xref_read`/`xref_write`（class + method + descriptor + access_flags），一次性给出类级字段数据流。用于追踪敏感字段（密钥/令牌/配置）的赋值点（write）和消费点（read）、状态字段生命周期分析。

```bash
androguard-skills analysis class-fields-xref "Lcom/example/Foo;" --apk-path test.apk

# 限制每个字段的读写引用展开数（默认 20）
androguard-skills analysis class-fields-xref "Lcom/example/Foo;" --xref-limit 5 --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `class_name`（位置） | 类名（Dalvik 格式） |
| `--xref-limit` | 每个字段的读写引用展开上限（默认 20，防止字段引用过多导致输出过大） |

**输出：**
```json
{
  "class": "Lcom/example/Foo;",
  "is_external": false,
  "fields_total": 13,
  "xref_limit": 20,
  "fields": [
    {
      "name": "IMPL",
      "descriptor": "Lcom/example/Foo$IMPL;",
      "access_flags": "static",
      "xref_read_count": 6,
      "xref_read": [
        {"class": "Lcom/example/Foo;", "method": "getSettingsActivityName", "descriptor": "(...)Ljava/lang/String;", "access_flags": "public static"}
      ],
      "xref_write_count": 1,
      "xref_write": [
        {"class": "Lcom/example/Foo;", "method": "<clinit>", "descriptor": "()V", "access_flags": "static constructor"}
      ]
    }
  ]
}
```

| 字段 | 说明 |
|------|------|
| `xref_read`/`xref_write` | 读写来源列表（每项含 class/method/descriptor/access_flags） |
| `xref_read_count`/`xref_write_count` | 完整计数（不受 `--xref-limit` 影响，`xref_*` 列表才截断） |

> `xref_write` 通常是字段赋值点（如 `<clinit>` static 初始化、setter），`xref_read` 是消费点（getter、逻辑分支）。敏感字段追踪：先 `class-fields` 定位高读写计数字段 → 本命令展开读写来源 → 配合 `method-instructions` 反汇编读写方法查看具体指令。底层 API：`FieldAnalysis.get_xref_read()`/`get_xref_write()` 返回 `list[(ClassAnalysis, MethodAnalysis)]`。

### `analysis api-usage`（增强）

获取应用使用的 Android API（外部 API 方法），支持限制和按类分组。

```bash
# 列出使用的 API（限制数量）
androguard-skills analysis api-usage --limit 20 --apk-path test.apk

# 按类分组统计
androguard-skills analysis api-usage --group-by-class --apk-path test.apk

# 分组 + 限制类数
androguard-skills analysis api-usage --group-by-class --limit 20 --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--limit` | 返回数量限制（分组模式下限制类数） |
| `--group-by-class` | 按 API 类分组统计 |

输出示例（列表）：

```json
{
  "total": 500,
  "returned": 20,
  "apis": [
    {"class": "Ljava/io/File;", "method": "<init>", "descriptor": "(Ljava/lang/String;)V", "is_external": true}
  ]
}
```

输出示例（分组）：

```json
{
  "total": 500,
  "class_count": 127,
  "classes": {
    "Ljava/io/File;": [
      {"method": "<init>", "descriptor": "(Ljava/lang/String;)V"},
      {"method": "getAbsolutePath", "descriptor": "()Ljava/lang/String;"}
    ]
  }
}
```

> `group_by_class` 模式适合快速了解应用使用了哪些 API 类（如 `Ljava/net/HttpURLConnection;` 表明有网络请求，`Ljavax/crypto/Cipher;` 表明有加密操作）。

## 安全分析用途

- **敏感字段定位**：`find-fields-advanced --fieldtype '.*SecretKey.*\|.*Cipher.*'` 查找加密相关字段
- **配置字段审计**：`--accessflags 'private.*static'` 查找硬编码配置常量
- **字段读写追踪**：`field-analysis` 的 xref_read/write 揭示字段在哪些方法被读写
  - `<clinit>` 中的 write 表示静态初始化（常被硬编码密钥）
  - 多处 read 的字段可能是全局配置
- **API 调用面分析**：`api-usage --group-by-class` 快速枚举应用使用的所有 API 类，识别危险 API（网络/加密/反射/文件/SQLite）
- **混淆字段识别**：`find-fields-advanced --fieldname 'a{1,3}$'` 查找短名混淆字段

## 相关命令

- [`analysis field-xrefs`](analysis-field-xrefs.md) — 字段交叉引用（轻量）
- [`analysis find-fields`](analysis-field-xrefs.md) — 单维字段名搜索
- [`analysis api-usage`](analysis-permissions.md) — API 使用分析（原版）
- [`analysis method-analysis`](analysis-lookup.md) — 方法分析（含 xref）
