# DEX 底层表项与 ClassManager 查询

> EncodedField/EncodedMethod 全量列表、按名/描述符精确查找、ClassManager 常量池查询、字段索引表、DEX 版本

## 命令

### `dex encoded-fields`

获取 DEX 全部 EncodedField（底层字段表，含访问标志）。

```bash
# 全量（可能很大）
androguard-skills dex encoded-fields --apk-path test.apk

# 限定某个类
androguard-skills dex encoded-fields --class "Lcom/example/MyClass;" --apk-path test.apk

# 限制返回数量
androguard-skills dex encoded-fields --limit 50 --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--class` | 限定某个类（可选，格式如 `Lcom/example/MyClass;`） |
| `--limit` | 返回数量限制 |

输出示例：

```json
{
  "total": 799,
  "returned": 3,
  "fields": [
    {
      "name": "ANNOTATION",
      "descriptor": "Ljava/util/regex/Pattern;",
      "access_flags": "public static final",
      "class": "Lcom/example/Editor;"
    }
  ]
}
```

> 与 `dex fields` 的区别：`fields` 返回的是分析层视图（已合并多 DEX、按类组织）；`encoded-fields` 返回 DEX 原始的 EncodedField 表项，适合底层 DEX 格式分析。

### `dex encoded-methods`

获取 DEX 全部 EncodedMethod（底层方法表，含 code offset）。

```bash
androguard-skills dex encoded-methods --apk-path test.apk
androguard-skills dex encoded-methods --class "Lcom/example/MyClass;" --apk-path test.apk
androguard-skills dex encoded-methods --limit 50 --apk-path test.apk
```

输出示例：

```json
{
  "total": 1431,
  "returned": 2,
  "methods": [
    {
      "name": "onCreate",
      "descriptor": "(Landroid/os/Bundle;)V",
      "access_flags": "protected",
      "class": "Lcom/example/Editor;",
      "code_off": 96032,
      "code_size": 570,
      "registers": 9
    }
  ]
}
```

> `code_off` 是方法字节码在 DEX 中的偏移，可直接传给 `dex disassemble --offset` 反汇编。`registers` 是寄存器数量。

### `dex encoded-method`

按方法名查找 EncodedMethod（跨所有类，返回所有同名方法）。

```bash
androguard-skills dex encoded-method onCreate --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `method_name`（位置参数） | 方法名 |

输出示例：

```json
{
  "method": "onCreate",
  "total": 5,
  "methods": [
    {"name": "onCreate", "descriptor": "()Z", "access_flags": "public", "class": "Landroid/support/v4/content/FileProvider;"},
    {"name": "onCreate", "descriptor": "(Landroid/os/Bundle;)V", "access_flags": "protected", "class": "Lcom/example/Editor;", "code_off": 96032}
  ]
}
```

> 用于查找所有重写/重载的 `onCreate`、`onClick` 等回调方法。

### `dex encoded-method-descriptor`

按 class+method+descriptor 精确查找 EncodedMethod（处理重载）。

```bash
androguard-skills dex encoded-method-descriptor "Lcom/example/Editor;" "onCreate" "(Landroid/os/Bundle;)V" --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `class_name`（位置参数） | 类名 |
| `method_name`（位置参数） | 方法名 |
| `descriptor`（位置参数） | 方法描述符（如 `(Landroid/os/Bundle;)V`） |

> 与 `analysis get-method` 的区别：此命令直接从 DEX 表查找 EncodedMethod（含 code_off），不需要 Analysis 对象。

### `dex cm-lookup`

按 ID 查询 ClassManager 常量池表（string/method/field/type）。

```bash
# 查字符串
androguard-skills dex cm-lookup 0 --kind string --apk-path test.apk

# 查方法
androguard-skills dex cm-lookup 5 --kind method --apk-path test.apk

# 查字段
androguard-skills dex cm-lookup 0 --kind field --apk-path test.apk

# 查类型
androguard-skills dex cm-lookup 0 --kind type --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `idx`（位置参数，int） | 常量池索引 |
| `--kind` | 查询类型（string/method/field/type，默认 string） |

输出示例（method）：

```json
{
  "idx": 5,
  "kind": "method",
  "class": "Landroid/app/Activity;",
  "name": "<init>",
  "params": "()",
  "return_type": "V"
}
```

输出示例（type）：

```json
{"idx": 0, "kind": "type", "value": "B"}
```

> ClassManager 是 DEX 的常量池，索引在多个表间共享。`cm-lookup` 用于反汇编时解析指令操作数（如 `invoke-virtual` 引用的 method_idx）。注意：idx 在不同 DEX 间不通用，此命令操作第一个 DEX。

### `dex fields-id`

获取 DEX 字段索引表（FieldIdItem，含 class_idx/type_idx/name_idx 索引）。

```bash
androguard-skills dex fields-id --apk-path test.apk
androguard-skills dex fields-id --limit 50 --apk-path test.apk
```

输出示例：

```json
{
  "total": 828,
  "returned": 2,
  "fields": [
    {
      "name": "authority",
      "descriptor": "Ljava/lang/String;",
      "class": "Landroid/content/pm/ProviderInfo;",
      "type": "Ljava/lang/String;",
      "name_idx": 1413,
      "type_idx": 201,
      "class_idx": 23
    }
  ]
}
```

> `*_idx` 字段是 ClassManager 索引，可用 `dex cm-lookup` 进一步解析。这是 DEX 格式最底层的字段表，适合脱壳/格式研究。

### `dex encoded-fields-class`

获取**指定类**的全部 EncodedField（直接走类的字段表，比 `encoded-fields --class` 全表过滤更精确）。

```bash
androguard-skills dex encoded-fields-class Lcom/example/Foo; --apk-path test.apk
androguard-skills dex encoded-fields-class Lcom/example/Foo; --limit 10 --apk-path test.apk
```

**输出：**
```json
{
  "class": "Lcom/example/Foo;",
  "dex_count": 1,
  "dexes": [
    {
      "dex_index": 0,
      "class": "Lcom/example/Foo;",
      "total": 134,
      "returned": 10,
      "fields": [
        {"name": "ANNOTATION", "descriptor": "Ljava/util/regex/Pattern;", "access_flags": "public static final", "class": "Lcom/example/Foo;"},
        ...
      ]
    }
  ]
}
```

### `dex encoded-methods-class`

获取**指定类**的全部 EncodedMethod（含 code_off/size/registers）。

```bash
androguard-skills dex encoded-methods-class Lcom/example/Foo; --apk-path test.apk
```

**输出：**
```json
{
  "class": "Lcom/example/Foo;",
  "dexes": [
    {
      "total": 114,
      "methods": [
        {"name": "<init>", "descriptor": "()V", "access_flags": "public constructor", "class": "Lcom/example/Foo;", "code_off": 87644, "code_size": 31, "registers": 3},
        ...
      ]
    }
  ]
}
```

`code_off` 是方法字节码在 DEX 中的偏移，可用于 `dex disassemble` 反汇编该方法的指令。

### `dex encoded-method-by-idx`

按 DEX 方法索引（`method_idx`）获取 EncodedMethod。idx 指向 `method_ids` 表，但只有类内定义的方法才有对应 EncodedMethod（外部引用方法返回 null）。

```bash
androguard-skills dex encoded-method-by-idx 132 --apk-path test.apk
```

**输出：**
```json
{
  "idx": 132,
  "dex_count": 1,
  "dexes": [
    {
      "dex_index": 0,
      "idx": 132,
      "method": {
        "name": "getFileForUri",
        "descriptor": "(Landroid/net/Uri;)Ljava/io/File;",
        "access_flags": "public abstract",
        "class": "Lcom/example/Foo$PathStrategy;"
      }
    }
  ]
}
```

> 注意：idx 范围因 APK 而异（editor.apk 内部方法从 idx 132 起，前 132 个是外部引用）。idx 不命中时 `method` 为 `null`，需用 `dex lens` 查看方法总数后调整 idx。idx 在不同 DEX 间不通用。

### `dex encoded-field-by-name`

按字段名搜索整个 DEX，返回所有类中的同名字段（跨类查询）。

```bash
androguard-skills dex encoded-field-by-name ANNOTATION --apk-path test.apk
```

**输出：**
```json
{
  "name": "ANNOTATION",
  "dexes": [
    {
      "total": 1,
      "fields": [
        {"name": "ANNOTATION", "descriptor": "Ljava/util/regex/Pattern;", "access_flags": "public static final", "class": "Lcom/example/Foo;"}
      ]
    }
  ]
}
```

用于追踪同名字段在不同类中的定义（如多个类都有 `TAG`/`INSTANCE` 字段）。

### `dex encoded-field-descriptor`

按 **class+field+descriptor** 精确查找 `EncodedField`。与 `encoded-field-by-name`（按名跨类返回所有同名字段）的区别：本命令用三参数精确查，返回单个 `EncodedField`，适合区分同名但类型不同的字段（如多个 `TAG` 字段，`Ljava/lang/String;` vs `I`）。与 `encoded-method-descriptor`（方法版）对称。

```bash
androguard-skills dex encoded-field-descriptor "Lcom/example/Foo;" "ANNOTATION" "Ljava/util/regex/Pattern;" --apk-path test.apk
```

**参数：**
- `class_name`：类名（如 `Lcom/example/Foo;`）
- `field_name`：字段名
- `descriptor`：字段描述符（如 `Ljava/lang/String;`、`I`、`Z`）

**输出：**
```json
{
  "class": "Lcom/example/Foo;",
  "field_name": "ANNOTATION",
  "descriptor": "Ljava/util/regex/Pattern;",
  "dex_count": 1,
  "dexes": [
    {
      "dex_index": 0,
      "class": "Lcom/example/Foo;",
      "field_name": "ANNOTATION",
      "descriptor": "Ljava/util/regex/Pattern;",
      "found": true,
      "field": {
        "name": "ANNOTATION",
        "descriptor": "Ljava/util/regex/Pattern;",
        "access_flags": "public static final",
        "class": "Lcom/example/Foo;"
      }
    }
  ]
}
```

`found: false` 表示该类无此 class+field+descriptor 组合的字段（`field: null`）。可能字段名存在但 descriptor 不匹配（同名不同类型），可用 `encoded-field-by-name` 查看该名的所有变体。

> 底层 API：`DEX.get_encoded_field_descriptor(class, field, descriptor)` → `EncodedMethod` 或 `None`。

### `dex encoded-method-class-method`

按**类名 + 方法名**获取 EncodedMethod（不需 descriptor）。与 `encoded-method-descriptor`（需 class+method+descriptor 三参数精确查）互补：此命令只需两参数，适合快速确认某类是否定义了某方法。若有重载，返回第一个匹配。

```bash
androguard-skills dex encoded-method-class-method Lcom/example/Foo; onCreate --apk-path test.apk
```

**参数：**
- `class_name`：类名（如 `Lcom/example/Foo;`）
- `method_name`：方法名

**输出：**
```json
{
  "class": "Lcom/example/Foo;",
  "method_name": "onCreate",
  "dex_count": 1,
  "dexes": [
    {
      "dex_index": 0,
      "class": "Lcom/example/Foo;",
      "method_name": "onCreate",
      "found": true,
      "method": {
        "name": "onCreate",
        "descriptor": "(Landroid/os/Bundle;)V",
        "access_flags": "protected",
        "class": "Lcom/example/Foo;",
        "code_off": 96032,
        "code_size": 570,
        "registers": 9
      }
    }
  ]
}
```

`found: false` 表示该类未定义此方法（`method: null`）。

> 底层 API：`DEX.get_encoded_methods_class_method(class, method)`，返回 `EncodedMethod` 或 `None`。

### `dex method-id-by-name`

在 DEX 常量池 `method_ids` 表中按方法名搜索，返回 `MethodIdItem` 列表（class/proto/name 三元组）。与 `encoded-method`（返回含 code 的 `EncodedMethod`）的关键区别：本命令走常量池，**包含外部引用的方法声明**（无实现体），适合查"哪些类声明/引用了某方法名"。

```bash
androguard-skills dex method-id-by-name onCreate --apk-path test.apk
androguard-skills dex method-id-by-name onCreate --limit 10 --apk-path test.apk
```

**参数：**
- `name`：方法名（精确匹配）
- `--limit`：每个 DEX 返回上限

**输出：**
```json
{
  "name": "onCreate",
  "dex_count": 1,
  "dexes": [
    {
      "dex_index": 0,
      "total": 5,
      "returned": 3,
      "methods": [
        {"name": "onCreate", "descriptor": "(Landroid/os/Bundle;)V", "class": "Landroid/app/Activity;", "proto": [["(Landroid/os/Bundle;)"], "V"]},
        {"name": "onCreate", "descriptor": "()Z", "class": "Landroid/support/v4/content/FileProvider;"},
        {"name": "onCreate", "descriptor": "(Landroid/os/Bundle;)V", "class": "Lorg/billthefarmer/editor/Editor;"}
      ]
    }
  ]
}
```

注意结果含 `Landroid/app/Activity;->onCreate` 这类**外部引用**（Framework 方法，无实现体），这是常量池表与 encoded 方法表的本质区别——常量池记录所有引用声明，encoded 只记录类内定义。

> 底层 API：`DEX.get_methods()` 全表 + `get_name()` 精确过滤。AndroGuard 的 `DEX.get_method(name)` 有 bug（访问不存在的 `.name` 属性会抛 `AttributeError`），故绕过。每项额外含 `proto`（参数列表+返回类型）、`triple`、`class_idx/name_idx/proto_idx` 等常量池字段。

### `dex method-ids`

获取 DEX 常量池 `method_ids` **全量表**（`MethodIdItem` 列表，含外部引用）。与 `encoded-methods`（仅类内定义、含 `code_off`）的关键区别：本命令枚举常量池所有被引用的方法声明（含 Framework 外部方法，无实现体），适合 DEX 格式分析、常量池枚举、外部依赖统计。

```bash
androguard-skills dex method-ids --apk-path test.apk
androguard-skills dex method-ids --limit 50 --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--limit` | 每个 DEX 返回上限 |

**输出：**
```json
{
  "dex_count": 1,
  "dexes": [
    {
      "dex_index": 0,
      "total": 2023,
      "returned": 2,
      "methods": [
        {"name": "getCustomView", "descriptor": "()Landroid/view/View;", "class": "Landroid/app/ActionBar;", "proto": ["()", "Landroid/view/View;"], "triple": ["android/app/ActionBar", "getCustomView", "()Landroid/view/View;"], "class_idx": 6, "name_idx": 1687, "proto_idx": 116}
      ]
    }
  ]
}
```

注意结果含 `Landroid/app/ActionBar;->getCustomView` 这类**外部引用**（Framework 方法，无实现体），这是常量池表与 encoded 方法表的本质区别。全量表可能很大（数千项），建议配合 `--limit` 或改用 `method-id-by-name` 按名过滤。

> 底层 API：`DEX.get_methods()`。每项结构与 `method-id-by-name` 一致（含 proto/triple/idx）。

### `dex field-id-by-name`

在 DEX 常量池 `field_ids` 表中按字段名搜索，返回 `FieldIdItem` 列表（含外部引用字段）。与 `encoded-field-by-name`（仅类内定义的 `EncodedField`）的关键区别：本命令走常量池，**包含外部引用的字段声明**（Framework 字段，无实现体），适合查"哪些类引用了某同名字段"。

```bash
androguard-skills dex field-id-by-name ANNOTATION --apk-path test.apk
androguard-skills dex field-id-by-name TAG --limit 10 --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `name`（位置参数） | 字段名（精确匹配） |
| `--limit` | 每个 DEX 返回上限 |

**输出：**
```json
{
  "name": "ANNOTATION",
  "dex_count": 1,
  "dexes": [
    {
      "dex_index": 0,
      "total": 1,
      "returned": 1,
      "fields": [
        {"name": "ANNOTATION", "descriptor": "Ljava/util/regex/Pattern;", "class": "Lcom/example/Editor;", "type": "Ljava/util/regex/Pattern;", "name_idx": 159, "type_idx": 232, "class_idx": 269}
      ]
    }
  ]
}
```

`*_idx` 字段是常量池索引，可用 `dex cm-lookup` 进一步解析。常量池表的字段可能含外部类（如 `Landroid/os/Build;` 的字段），与 encoded 字段表（仅类内定义）互补。

> 底层 API：`DEX.get_fields()` 全表 + `get_name()` 精确过滤。AndroGuard 的 `DEX.get_field(name)` 有 bug（访问不存在的 `.name` 属性，与 `get_method(name)` 同类 bug），故绕过。

### `dex field-init-value <class> <field>`

获取字段的**初始值**（硬编码常量检测）。

与 `encoded-fields`/`encoded-field-by-name`（字段表元数据，不含初始值）的区别：本命令用 `EncodedField.get_init_value()` 返回 `EncodedValue`，提取 `get_value()`（原生 Python 值）和 `get_value_type()`（DEX 类型码），用于检测硬编码常量（密钥、URL、魔法数等静态字段初始值）。

```bash
androguard-skills dex field-init-value "Lorg/billthefarmer/editor/Editor;" "BLACK" --apk-path test.apk
```

输出示例：

```json
{
  "class": "Lorg/billthefarmer/editor/Editor;",
  "field": "BLACK",
  "dex_index": 0,
  "descriptor": "I",
  "access_flags": "public static final",
  "has_init_value": true,
  "value": 5,
  "value_type": 4
}
```

| 字段 | 说明 |
|------|------|
| `value` | 字段初始值（原生 Python 类型：int/str/None 等） |
| `value_type` | DEX 类型码（见下表） |
| `has_init_value` | 是否有初始值（实例字段/无初始值的静态字段为 false 或 value=null） |

**`value_type` 类型码映射：** 0=byte, 2=short, 3=char, 4=int, 6=long, 16=float, 17=double, 23=String, 24=type, 25=field 引用, 26=method 引用, 27=enum, 28=array, 29=annotation, 30=null, 31=boolean。

**安全用途：** 检测硬编码密钥、URL、加密密钥常量、魔法数等。配合 `dex strings`/`analysis find-strings` 全文搜索，定位敏感静态字段。

> 底层 API：`EncodedField.get_init_value()` → `EncodedValue`，其 `get_value()` 返回原生 Python 值（int/str/None/bytes 等），`get_value_type()` 返回 DEX 类型码。仅 static 字段通常有初始值。

### `dex version`

获取 DEX 版本号。

```bash
androguard-skills dex version --apk-path test.apk
```

输出示例：

```json
{"dex_count": 1, "versions": [35]}
```

> 版本对应：35 = Android 6.0+（默认），37 = Android 8.0+（compact dex），38 = Android 9.0+（hidden API）。`dex_count > 1` 表示 multidex。

## 安全分析用途

- **字节码定位**：`encoded-methods` 的 `code_off` 直接喂给 `dex disassemble` 反汇编关键方法
- **方法枚举**：`encoded-method <name>` 找出所有同名回调（如 `onCreate`/`onReceive`），定位入口点
- **重载处理**：`encoded-method-descriptor` 用描述符区分重载方法
- **常量池解析**：`cm-lookup` 反汇编时解析操作数引用的类/方法/字段/类型
- **底层格式分析**：`fields-id` 用于 DEX 格式研究、脱壳后结构恢复
- **DEX 版本**：`version` 判断 DEX 格式特性（如是否支持 compact dex）

## 相关命令

- [`dex disassemble`](dex-disassemble.md) — 用 code_off 反汇编字节码
- [`dex class`](dex-disassemble.md) — 类详情（访问标志/父类/接口）
- [`dex stats`](dex-disassemble.md) — DEX 统计信息
- [`analysis get-method`](analysis-lookup.md) — 分析层的方法元数据
