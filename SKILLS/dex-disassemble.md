# DEX 反汇编、层级与统计

> 字节码反汇编、类继承层级树、统计信息、类详情、调试信息

## 命令

### `dex disassemble`

反汇编 DEX 指定偏移处的字节码指令。

```bash
androguard-skills dex disassemble --offset 96032 --size 100 --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--offset` | 起始偏移（必须是有效代码段偏移，如方法的 `code_off`） |
| `--size` | 反汇编的字节大小 |

> **获取 code_off**：用 `analysis method-analysis` 或 `analysis get-method` 查看方法的 code offset。
> 若 offset 指向非法指令，会返回部分结果并附带 error 字段。

输出示例：

```json
{
  "offset": 96032,
  "size": 100,
  "count": 15,
  "instructions": [
    {"name": "invoke-super", "output": "v7, v8, Landroid/app/Activity;->onCreate...", "hex": "68 20 30 00", "length": 6},
    {"name": "invoke-static", "output": "v7, Landroid/preference/PreferenceManager;->...", "hex": "71 20 50 02", "length": 6}
  ]
}
```

### `dex hierarchy`

获取 DEX 类继承层级树。

```bash
androguard-skills dex hierarchy --apk-path test.apk
```

输出示例：

```json
{
  "total_roots": 1,
  "hierarchy": {
    "Root": [
      {"java/lang/Object": [...]}
    ]
  }
}
```

### `dex stats`

获取 DEX 统计信息（各类计数、API 版本、格式）。

```bash
androguard-skills dex stats --apk-path test.apk
```

输出示例：

```json
{
  "dex_count": 1,
  "stats": [
    {
      "index": 0,
      "classes": 294,
      "methods": 2023,
      "strings": 2575,
      "encoded_fields": 828,
      "encoded_methods": 2023,
      "api_version": 35,
      "format_type": "DEX"
    }
  ]
}
```

> `methods > 65535` 表示 multidex。`api_version` 反映 DEX 格式版本（35=Android 6.0+）。

### `dex class`

获取 DEX 中指定类的详细信息（访问标志/父类/接口）。

```bash
androguard-skills dex class "Lcom/example/MainActivity;" --apk-path test.apk
```

输出示例：

```json
{
  "name": "Lcom/example/MainActivity;",
  "access_flags": "public",
  "superclass": "Landroid/app/Activity;",
  "interfaces": ["Landroid/view/View$OnClickListener;"],
  "source": "MainActivity.java"
}
```

### `dex class-meta <class>`

获取 ClassDefItem 的**底层 DEX 结构元信息**（类级注解/源文件名/接口/父类 idx/各表偏移）。

与 `dex class`（综合信息）和 `analysis class-hierarchy-info`（analysis 视图继承）的区别：本命令聚焦 ClassDefItem 层的底层结构——**类级注解列表**（如 `@MemberClasses`）、**源文件名**（混淆检测：混淆后常为 null）、**接口/父类的常量池 idx + 解析名**、annotations/class_data/static_values 各表偏移，用于 DEX 结构分析和混淆检测。

```bash
androguard-skills dex class-meta "Lorg/billthefarmer/editor/Editor;" --apk-path test.apk
```

输出示例：

```json
{
  "class": "Lorg/billthefarmer/editor/Editor;",
  "dex_index": 0,
  "dex_name": "dex_0",
  "annotations": ["Ldalvik/annotation/MemberClasses;"],
  "annotated_fields_size": 2,
  "annotated_methods_size": 2,
  "annotated_parameters_size": 0,
  "source_file_idx": 335,
  "source_file": "Editor.java",
  "interfaces": [],
  "superclass_idx": 7,
  "superclass": "Landroid/app/Activity;",
  "class_idx": 269,
  "annotations_off": 249304,
  "class_data_off": 235740,
  "static_values_off": 245552,
  "interfaces_off": 0
}
```

| 字段 | 说明 |
|------|------|
| `annotations` | 类级注解列表（运行时注解，安全审计价值高） |
| `annotated_*_size` | 注解目录中被注解的字段/方法/参数计数（密度高提示反射/DI 框架，如 Room/Dagger） |
| `source_file` | 源文件名（`source_file_idx` 经 class_manager 解析；混淆后常为 null） |
| `interfaces` | 实现的接口列表（已解析为 type 字符串） |
| `superclass` | 父类名（`superclass_idx` 经 class_manager 解析） |
| `*_idx` | 对应常量池索引（`class_idx`/`superclass_idx`/`source_file_idx`） |
| `*_off` | DEX 内各表偏移（annotations/class_data/static_values/interfaces） |

> 底层 API：`ClassDefItem.get_annotations()`（返回 `list[str]`）/`get_source_file_idx()`/`get_interfaces()`/`get_superclass_idx()`/`get_*_off()`，idx 经 `ClassManager.get_string(idx)`/`get_type(idx)` 解析为可读名。

### `dex class-data <class>`

获取类的 ClassDataItem **分类视图**（direct/virtual 方法 + static/instance 字段）。

与 `encoded-methods-class`（不区分 direct/virtual）和 `encoded-fields-class`（不区分 static/instance）的区别：本命令按 DEX 方法定义分类——**direct 方法**（`private`/`static`/构造器，不可覆写）vs **virtual 方法**（可覆写），**static 字段**（类级）vs **instance 字段**（实例级），含各类计数与列表，用于理解类的结构布局。

```bash
androguard-skills dex class-data "Lorg/billthefarmer/editor/Editor;" --apk-path test.apk

# 限制每类返回数量
androguard-skills dex class-data "Lcom/example/Foo;" --limit 5 --apk-path test.apk
```

输出示例：

```json
{
  "class": "Lorg/billthefarmer/editor/Editor;",
  "dex_index": 0,
  "dex_name": "dex_0",
  "direct_methods_size": 80,
  "virtual_methods_size": 34,
  "static_fields_size": 105,
  "instance_fields_size": 29,
  "direct_methods": [
    {"name": "<clinit>", "descriptor": "()V", "access_flags": "static constructor", "class": "...", "code_off": ..., "code_size": ..., "registers": ...},
    ...
  ],
  "virtual_methods": [
    {"name": "dispatchTouchEvent", "descriptor": "...", "access_flags": "public", ...},
    ...
  ],
  "static_fields": [
    {"name": "ANNOTATION", "descriptor": "I", "access_flags": "...", "class": "..."},
    ...
  ],
  "instance_fields": [
    {"name": "changed", "descriptor": "Z", "access_flags": "...", "class": "..."},
    ...
  ]
}
```

| 字段 | 说明 |
|------|------|
| `direct_methods` | 不可覆写方法（private/static/构造器），`*_size` 是总数 |
| `virtual_methods` | 可覆写方法（public/protected 实例方法） |
| `static_fields` | 类级字段（`static`） |
| `instance_fields` | 实例级字段（非 static） |
| `--limit` | 每类列表返回上限（`*_size` 仍为完整总数） |

> 底层 API：`ClassDefItem.get_class_data()` → `ClassDataItem`，其 `get_direct_methods()`/`get_virtual_methods()`/`get_static_fields()`/`get_instance_fields()` 返回 EncodedMethod/EncodedField 列表。无 ClassData 的类（如 marker 接口/abstract 无体）返回 error。

### `dex regex-strings`

用正则表达式高效搜索 DEX 字符串（底层 C 实现，比全量 `strings`+过滤快）。

```bash
androguard-skills dex regex-strings "http.*" --apk-path test.apk
androguard-skills dex regex-strings "[A-Za-z0-9+/]{40,}" --apk-path test.apk
```

输出示例：

```json
{
  "pattern": "http.*",
  "total": 12,
  "strings": ["http://", "https://api.example.com", "http://schemas.android.com/..."]
}
```

### `dex strings-table [--filter] [--limit]`

**字符串常量池完整表**——返回每个字符串的 `idx`、值、`offset`（在 DEX 二进制中的字节偏移）、`utf16_size`（UTF-16 字符数）。

与 `dex strings`（仅返回字符串值列表，无定位信息）和 `regex-strings`（仅值，C 层高效搜索）的区别：本命令额外提供**二进制偏移**，用于：
- 定位字符串在 DEX 二进制中的精确位置（patch、脱壳前后比对、字符串替换）
- 字符串混淆检测（`utf16_size` 与解码值长度不一致，或 offset 序列异常）
- 跨 DEX 字符串偏移映射（multidex 关联）

```bash
androguard-skills dex strings-table --apk-path test.apk

# 过滤 + 限制（避免大 DEX 全量输出）
androguard-skills dex strings-table --filter "Editor" --limit 20 --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--filter` | 正则过滤字符串值（可选） |
| `--limit` | 返回条目上限（默认全部，大 DEX 建议设限） |

**输出：**
```json
{
  "total": 2,
  "strings": [
    {"dex_index": 0, "string_idx": 333, "value": "Editor", "offset": 178623, "utf16_size": 6},
    {"dex_index": 0, "string_idx": 334, "value": "Editor.html", "offset": 178631, "utf16_size": 11}
  ]
}
```

| 字段 | 说明 |
|------|------|
| `string_idx` | 字符串在常量池中的索引 |
| `offset` | string_data_item 在 DEX 二进制中的字节偏移（递增，符合 DEX 布局） |
| `utf16_size` | UTF-16 字符数（与值长度不一致可能是混淆/编码异常） |
| `dex_index` | multidex 中所属 DEX 的索引 |

> 底层 API：`DEX.get_string_data_item()` 返回 `list[StringDataItem]`（每项有 `offset`/`utf16_size` 属性）+ `ClassManager.get_string(idx)` 取解码值。`offset` 可配合 `dex header` 的 `string_ids_off` 做 patch 定位。

### `dex debug-info`

获取 DEX 调试信息（**结构化**：行号起始 + 参数名恢复 + 参数数量）。从 DebugInfoItem 提取 `line_start`（源码行号起始，定位方法在源文件的位置）、`parameters_size`（参数数量）、`parameter_names_idx`（参数名常量池 idx，-1 表示无名）、`translated_parameter_names`（翻译后的参数名，从调试信息恢复，如 release 构建被剥离时为 None）。

```bash
# 全局调试信息
androguard-skills dex debug-info --apk-path test.apk

# 指定类的所有方法调试信息
androguard-skills dex debug-info --class "Lcom/example/MainActivity;" --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--class` | 类名（Dalvik 格式，可选）。省略返回全局调试信息 |

**输出：**
```json
{
  "total": 114,
  "debug_info": [
    {
      "method": "onCreate",
      "descriptor": "(Landroid/os/Bundle;)V",
      "line_start": 464,
      "parameters_size": 1,
      "parameter_names_idx": [-1],
      "translated_parameter_names": [null]
    },
    ...
  ]
}
```

| 字段 | 说明 |
|------|------|
| `line_start` | 方法在源文件的起始行号（定位源码位置，混淆检测） |
| `parameters_size` | 参数数量 |
| `parameter_names_idx` | 参数名常量池 idx 列表（`-1` 表示该参数无名） |
| `translated_parameter_names` | 翻译后的参数名（idx→字符串；release 构建常剥离为 `null`，debug 构建恢复为真实名如 `"savedInstanceState"`） |

> 底层 API：`DalvikCode.get_debug_info_off()` 取偏移 → `DebugInfoItem(buff, cm)` 直接构造（绕过 `code.get_debug()` 的 `'DEX' object has no attribute 'seek'` bug —— ClassManager.buff 被设为 DEX 对象而非 raw BufferedReader，故用 `dex.raw.seek(off)` + 直接构造）→ `get_line_start()`/`get_parameters_size()`/`get_parameter_names()`/`get_translated_parameter_names()`。`translated_parameter_names` 对 release APK 常为 `[null, ...]`（参数名被剥离），debug 构建才有真实名。

### `dex method-info <class> <method>`

获取方法的**签名级元信息**（返回类型、寄存器范围、参数到寄存器映射、局部变量数、代码偏移）。与 `analysis method-detail`（分析视图，含 xref 统计）的区别：本命令走 EncodedMethod 底层，提供反汇编上下文所需的寄存器布局。

```bash
androguard-skills dex method-info Lcom/example/Foo; onCreate --apk-path test.apk
```

**输出：**
```json
{
  "class": "Lorg/billthefarmer/editor/Editor;",
  "method": "onCreate",
  "dex_index": 0,
  "dex_name": "dex_0",
  "descriptor": "(Landroid/os/Bundle;)V",
  "access_flags": "protected",
  "full_name": "Lorg/billthefarmer/editor/Editor; onCreate (Landroid/os/Bundle;)V",
  "signature": {
    "return": "void",
    "registers": [0, 7],
    "params": [[8, "android.os.Bundle"]]
  },
  "locals": 7,
  "address": 96048,
  "code_off": 96032,
  "size": 5,
  "method_idx": 936
}
```

**字段说明：**

| 字段 | 说明 |
|------|------|
| `signature.return` | 返回类型 |
| `signature.registers` | `[起始, 结束]` 寄存器范围 |
| `signature.params` | `[[寄存器号, 参数类型], ...]` 参数到寄存器映射 |
| `locals` | 局部变量寄存器数 |
| `address` | 方法在 DEX 中的地址 |
| `code_off` | 代码段偏移（传给 `dex disassemble` 反汇编） |
| `method_idx` | 方法在 DEX 中的索引 |

> `signature.params` 的寄存器号与 `method-instructions` 输出的 `v0`/`v8` 对应，用于理解反汇编中哪个寄存器持有哪个参数。

### `dex method-instructions <class> <method>`

按方法反汇编**所有 Dalvik 指令**（指令流）。与 `dex disassemble`（按 offset+size 反汇编任意代码段）的区别：本命令按 class+method 定位，用 `get_instructions()` 返回方法完整指令流，每条含 name/output/op_value/hex/length，适合方法级完整反汇编、指令模式检测。

```bash
# 全部指令
androguard-skills dex method-instructions Lcom/example/Foo; onCreate --apk-path test.apk

# 限制返回数量
androguard-skills dex method-instructions Lcom/example/Foo; onCreate --limit 50 --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `class_name`（位置） | 类名（Dalvik 格式） |
| `method_name`（位置） | 方法名 |
| `--limit` | 返回指令数量上限（默认全部） |

**输出：**
```json
{
  "class": "Lorg/billthefarmer/editor/Editor;",
  "method": "onCreate",
  "dex_index": 0,
  "dex_name": "dex_0",
  "descriptor": "(Landroid/os/Bundle;)V",
  "access_flags": "protected",
  "total": 258,
  "returned": 3,
  "instructions": [
    {
      "name": "const-string",
      "output": "v0, \"[\\(\\)\\[\\]\\{\\}\\<\\>\"'`]",
      "op_value": 26,
      "hex": "1a 00 fb 04",
      "length": 4,
      "operands": [["REGISTER", 0], [257, 1259, "[\\(\\)\\[\\]\\{\\}\\<\\>\"'`]"]]
    },
    {
      "name": "invoke-static",
      "output": "v0, Ljava/util/regex/Pattern;->compile(Ljava/lang/String;)Ljava/util/regex/Pattern;",
      "op_value": 113,
      "hex": "71 10 fb 04 00 00",
      "length": 6,
      "operands": [["REGISTER", 0], [256, 755, "Ljava/util/regex/Pattern;->compile(Ljava/lang/String;)Ljava/util/regex/Pattern;"]]
    },
    ...
  ]
}
```

**指令字段说明：**

| 字段 | 说明 |
|------|------|
| `name` | 指令助记符（如 `invoke-super`/`move-result-object`/`const-string`） |
| `output` | 操作数的可读表示（寄存器/方法引用/字面量） |
| `op_value` | 操作码数值 |
| `hex` | 指令的十六进制字节 |
| `length` | 指令字节长度 |
| `operands` | 操作数结构化列表，每个操作数是一个数组：寄存器操作数为 `["REGISTER", 寄存器号]`，常量池引用为 `[kind, idx, 字面值]`（如 `[257, 1259, "..."]`，257=string 引用、1259=常量池 idx、第三项是已解析的字面值）。比 `output` 字符串更精确可程序化解析——能直接拿到常量池 idx 和字面值 |

`total` 是方法指令总数，`returned` 受 `--limit` 限制。`output` 中的方法引用（`Lclass;->method(desc)ret`）可直接传给 `analysis method-xrefs-detail` 追踪调用。`operands` 的常量池 idx 可传给 `dex cm-lookup <idx>` 解析为字符串/方法/字段/类型名（用 `--kind` 指定类型）。

> 底层 API：`EncodedMethod.get_instructions()` 返回迭代器（需 list 物化）。`get_size()` 返回值与指令数不同（是 code 单元数），指令总数以 `get_instructions()` 物化后的 `total` 为准。

### `dex method-instructions-idx <class> <method>`

按方法反汇编所有指令，**带字节偏移 idx**。

与 `method-instructions`（无 idx）的区别：本命令用 `get_instructions_idx()` 返回 `Iterator[(idx, Instruction)]`，每条指令额外含字节偏移 `idx`（如 0/6/12，每条指令占 6 字节单位），用于精确定位指令在方法内的字节位置（配合 `disassemble`/`method-exceptions` 的 offset）。

```bash
androguard-skills dex method-instructions-idx "Lcom/example/Foo;" "onCreate" --limit 5 --apk-path test.apk
```

输出示例：

```json
{
  "class": "Lorg/billthefarmer/editor/Editor;",
  "method": "onCreate",
  "total": 258,
  "returned": 3,
  "instructions": [
    {"idx": 0, "name": "invoke-super", "output": "v7, v8, Landroid/app/Activity;->onCreate(...)", "op_value": 111, "length": 6},
    {"idx": 6, "name": "invoke-static", "output": "...", "op_value": 113, "length": 6},
    {"idx": 12, "name": "move-result-object", "output": "v0", "op_value": 12, "length": 2}
  ]
}
```

`idx` 是指令在方法内的字节偏移（相对方法起始），可与 `method-exceptions` 的 `start`/`end` try 区间、`disassemble` 的 offset 对照定位。

> 底层 API：`EncodedMethod.get_instructions_idx()` 返回 `Iterator[tuple[int, Instruction]]`（需 list 物化）。

### `dex method-code <class> <method>`

获取方法 DalvikCode 的**底层结构信息**（寄存器帧 + try/catch 异常表 + handlers）。与 `method-info`（签名元信息）和 `analysis method-exceptions`（分析层 basic_block 视图异常表）的区别：本命令直接读 DEX 的 DalvikCode 表项，返回寄存器帧尺寸（registers_size/ins_size/outs_size/insns_size）、try 区间列表（TryItem: start_addr/insn_count/handler_off）、catch 处理器地址表（EncodedCatchHandler: catch_all_addr + 每个 type_idx→handler_addr）、debug_info_off，适合 DEX 格式分析、异常处理底层结构定位、与 method-exceptions 交叉验证。

```bash
androguard-skills dex method-code "Landroid/support/v4/content/FileProvider;" getPathStrategy --apk-path test.apk
```

输出示例：

```json
{
  "class": "Landroid/support/v4/content/FileProvider;",
  "method": "getPathStrategy",
  "dex_index": 0,
  "dex_name": "dex_0",
  "descriptor": "(...)Landroid/support/v4/content/FileProvider$PathStrategy;",
  "has_code": true,
  "registers_size": 6,
  "ins_size": 2,
  "outs_size": 3,
  "insns_size": 123,
  "code_length": 570,
  "code_off": 96032,
  "debug_info_off": 96124,
  "tries_size": 3,
  "tries": [
    {"start_addr": 3, "insn_count": 8, "length": 8, "handler_off": 1}
  ],
  "handlers": [
    {"handler_off": 1, "catch_all_addr": 43, "handlers": [{"type_idx": 12, "handler_addr": 20}]}
  ]
}
```

| 字段 | 说明 |
|------|------|
| `has_code` | 是否有 code 项（abstract/native 方法为 false，附 note） |
| `registers_size`/`ins_size`/`outs_size` | 寄存器帧：总寄存器数/参数寄存器数/调用其他方法所需寄存器数 |
| `insns_size`/`code_length`/`code_off` | 指令单元数/字节长度/代码段偏移 |
| `tries_size` | try 块数量 |
| `tries[]` | TryItem：`start_addr`（try 起始指令偏移）/`insn_count`（覆盖指令数）/`handler_off`（指向 handlers 列表的字节偏移） |
| `handlers[]` | EncodedCatchHandler：`catch_all_addr`（finally 块地址，无对应 type 时为 catch-all）/`handlers[]`（每个 type_idx→handler_addr，type_idx 经 `dex cm-lookup <idx> --kind type` 解析为类名） |
| `debug_info_off` | 调试信息偏移（含行号/局部变量名，混淆后可能为 0） |

> `tries[].handler_off` 是相对 handlers 列表起始的**字节偏移**（EncodedCatchHandler 变长编码，size 决定长度），与 `handlers[].handler_off` 对齐可关联 try 块到具体 catch handler。abstract/native 方法无 code，`has_code=false` 并附 note。底层 API：`EncodedMethod.get_code()` → `DalvikCode`，其 `get_registers_size()`/`get_tries()`/`get_handlers()`。

### `dex proto-ids [--limit]`

获取 DEX **方法原型表**（ProtoIdItem）：Dalvik 的方法签名去重表，每个原型含 shorty 短签名、返回类型、参数类型列表。

与 `method-ids`（方法表，class+name+proto_idx）的区别：本命令聚焦 proto_id_item 表本身——被多个方法共享的去重原型。`shorty` 是单字母签名（首字符=返回类型首字母，后续=各参数类型首字母，如 `VBI`=返回void+参数byte+int），`return_type`/`parameters` 是完整类型名列表。

```bash
androguard-skills dex proto-ids --apk-path test.apk
androguard-skills dex proto-ids --limit 10 --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--limit` | 返回原型数量上限（默认全部） |

**输出：**
```json
{
  "total": 634,
  "returned": 3,
  "protos": [
    {"dex_index": 0, "proto_idx": 0, "shorty_idx": 5, "return_type_idx": 2023, "parameters_off": 169992, "shorty": "BB", "return_type": "B", "parameters": ["B"]},
    {"dex_index": 0, "proto_idx": 1, "shorty": "C", "return_type": "C", "parameters": []},
    {"dex_index": 0, "proto_idx": 2, "shorty": "CI", "return_type": "C", "parameters": ["I"]}
  ]
}
```

| 字段 | 说明 |
|------|------|
| `proto_idx` | 原型在表中的索引（`method-ids` 的 `proto_idx` 指向此） |
| `shorty_idx`/`return_type_idx` | 常量池索引（shorty 字符串 idx / 返回类型 type idx） |
| `shorty` | 短签名（首字符返回类型，后续参数类型，单字母） |
| `return_type` | 完整返回类型名（如 `B`/`Ljava/lang/String;`） |
| `parameters` | 完整参数类型列表（从 `parameters_off` 解析的 type_list，无参为 `[]`） |
| `parameters_off` | type_list 表偏移（0 表示无参数） |

> 底层 API：`HeaderItem.proto_ids_off`/`proto_ids_size` 取表位置 → `dex.raw.seek(off)` 手动 unpack 12 字节（shorty_idx/return_type_idx/parameters_off 各 u4）→ `ClassManager.get_string()`/`get_type()`/`get_type_list()` 解析。`parameters` 是完整类型名（区别于 shorty 的单字母），用于精确参数类型分析。

### `dex type-ids [--limit]`

**类型常量池表**（type_ids）—— DEX 中所有类型描述符的索引表。

与 `dex proto-ids`（引用 type_idx 的方法原型表）的区别：本命令是类型描述符表本身——`type_idx → descriptor_idx`（指向 string_ids）→ 类型描述符。是 DEX 四大基础常量池之一（string/type/proto/field/method），proto-ids 的 return_type/parameters、field-ids 的 type_idx、method-ids 的 class_idx 均引用此表。

```bash
androguard-skills dex type-ids --apk-path test.apk
androguard-skills dex type-ids --limit 50 --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--limit` | 返回类型条目上限（默认全部） |

**输出：**
```json
{
  "total": 501,
  "type_ids": [
    {"dex_index": 0, "type_idx": 0, "descriptor_idx": 187, "descriptor": "B"},
    {"dex_index": 0, "type_idx": 1, "descriptor_idx": 216, "descriptor": "C"},
    {"dex_index": 0, "type_idx": 100, "descriptor_idx": 1234, "descriptor": "Landroid/widget/LinearLayout;"},
    ...
  ]
}
```

| 字段 | 说明 |
|------|------|
| `type_idx` | 类型在表中的索引（proto/field/method-ids 引用此） |
| `descriptor_idx` | 指向 string_ids 的描述符索引 |
| `descriptor` | 类型描述符（`B`/`C`/`I`/`J`/`Z` 基本类型，`Lcom/example/Foo;` 类，`[I`/`[Ljava/lang/String;` 数组） |

> 底层 API：`HeaderItem.type_ids_off`/`type_ids_size` 取表位置 → `dex.raw.seek(off)` unpack 4 字节 descriptor_idx → `ClassManager.get_string(descriptor_idx)` 解析描述符。前几项固定为基本类型（B/C/D/F/I/J/S/Z）。配合 `dex proto-ids` 的 `return_type_idx`/`parameters` 做完整类型解析。

### `dex annotations [--class] [--limit]`

获取 DEX **注解目录**（AnnotationsDirectoryItem）：类级/字段级/方法级/参数级注解，含可见性、类型、元素值。

与 `class-meta`（仅类级注解类型名列表）的区别：本命令展开注解底层完整结构——每个注解含 `visibility`（0=BUILD/1=RUNTIME/2=SYSTEM）、`type`（注解类型）、`elements`（元素名+值，值递归解析 EncodedValue），按 class/field/method/parameter 四级分组。用于反射/DI 框架检测（Room/Dagger/Hilt 注解密度高）、安全审计（`@SuppressLint`/`@GuardedBy`/`@Keep`）、混淆检测。

```bash
# 扫描所有有注解的类（输出量大，建议配合 --limit）
androguard-skills dex annotations --limit 50 --apk-path test.apk

# 指定类的完整注解目录
androguard-skills dex annotations --class "Lcom/example/Foo;" --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--class` | 类名（Dalvik）。省略则扫描所有有注解的类 |
| `--limit` | 扫描类数量上限（仅省略 `--class` 时生效） |

**输出：**
```json
{
  "total_scanned": 1,
  "classes": [
    {
      "class": "Lcom/example/Foo;",
      "dex_index": 0,
      "has_annotations": true,
      "annotated_fields_size": 2,
      "annotated_methods_size": 3,
      "annotated_parameters_size": 1,
      "class_annotations": [
        {"visibility": 1, "visibility_name": "RUNTIME", "type_idx": 35147, "type": "Ljava/lang/annotation/Retention;", "elements": [{"name_idx": 35147, "name": "value", "value": ["Ljava/lang/annotation/RetentionPolicy;"]}]}
      ],
      "field_annotations": [{"field_idx": 100, "field": ["Lcom/example/Foo;", "I", "count"], "annotations": [...]}],
      "method_annotations": [{"method_idx": 1635, "method": ["Lcom/example/Foo;", "bar", ["()", "V"]], "annotations": [{"visibility": 0, "visibility_name": "BUILD", "type": "Landroid/support/annotation/Nullable;", "elements": []}]}],
      "parameter_annotations": [{"method_idx": 1636, "method": ["...", "setX", ["(I)", "V"]], "parameter_annotations": [[{"type": "Landroid/support/annotation/StringRes;"}]]}]
    }
  ]
}
```

| 字段 | 说明 |
|------|------|
| `annotated_*_size` | 注解目录中被注解的字段/方法/参数计数（密度高→反射/DI 框架） |
| `class_annotations` | 类级注解列表 |
| `field_annotations[].annotations` | 该字段的注解列表（`field` 是 `[class, type, name]`） |
| `method_annotations[].annotations` | 该方法的注解列表（`method` 是 `[class, name, [params, return]]`） |
| `parameter_annotations[].parameter_annotations` | 二维列表：每参数一组注解 |
| `visibility`/`visibility_name` | 注解可见性：0=BUILD（仅编译期）/1=RUNTIME（运行时反射可见）/2=SYSTEM |
| `type` | 注解类型（如 `Landroid/support/annotation/Nullable;`） |
| `elements[].name`/`value` | 注解元素名和值（value 递归解析 EncodedValue：基本类型原样、bytes 转 hex、数组展开） |

> 底层 API：`ClassDefItem.get_annotations_off()` → `annotations_directory_item`（属性）→ `get_class_annotations_off()`/`get_field_annotations()`/`get_method_annotations()`/`get_parameter_annotations()`。每项的 `annotations_off` → `ClassManager.get_annotation_set_item(off)` → `get_annotation_off_item()` → `get_annotation_item()` → `get_visibility()`/`get_annotation()` → `get_type_idx()`+`get_elements()`。参数注解是 AnnotationSetRefList（手动 unpack：size u4 + N 个 u4 off），每参数一组 set。元素值经 `_encode_value_to_python` 递归处理 EncodedValue（基本类型/bytes/EncodedArray 嵌套）。

### `dex static-values <class>`

获取类的**静态值数组**（EncodedArray）：一次性返回所有 static 字段的初始值，与字段名配对。

与 `field-init-value`（单字段查初始值，需逐字段调）的区别：本命令展开 `ClassDefItem.get_static_values_off()` 指向的 EncodedArray，一次返回类所有 static 字段的初始值列表（含 value_type 码 + 递归解析的 value），与 `class-data` 的 static_fields 顺序一一对应。用于**批量检测硬编码常量**（密钥、URL、魔法数、正则模式等 `static final` 字段），比逐字段查高效。

```bash
androguard-skills dex static-values "Lcom/example/Foo;" --apk-path test.apk
```

**输出：**
```json
{
  "class": "Lorg/billthefarmer/editor/Editor;",
  "dex_index": 0,
  "has_static_values": true,
  "static_values_off": 245552,
  "count": 104,
  "values": [
    {"field": "ANNOTATION", "value_type": 30, "value_type_name": "NULL", "value": null},
    {"field": "BLACK", "value_type": 4, "value_type_name": "INT", "value": 5},
    {"field": "BRACKET_CHARS", "value_type": 23, "value_type_name": "STRING", "value": "([{<"},
    {"field": "CC_EXT", "value_type": 23, "value_type_name": "STRING", "value": "\\.(c(c|pp|...)?|go|h|java|...)"}
  ]
}
```

| 字段 | 说明 |
|------|------|
| `static_values_off` | EncodedArray 在 DEX 中的偏移 |
| `count` | 静态值总数（应等于 static_fields 数） |
| `values[].field` | 字段名（与 `class-data` 的 static_fields 顺序对齐） |
| `value_type`/`value_type_name` | DEX 类型码（0=BYTE/4=INT/23=STRING/30=NULL/31=BOOLEAN 等） |
| `values[].value` | 递归解析的值（null/int/str/bytes_hex/嵌套数组） |

> 底层 API：`ClassDefItem.get_static_values_off()` → `dex.raw.seek(off)` → `EncodedArrayItem(raw, cm).get_value()` → `EncodedArray.get_values()` 返回 `list[EncodedValue]`，每个 `get_value_type()`+`get_value()`。**字段顺序与 `ClassDataItem.get_static_fields()` 一致**（DEX 规范保证）。无 static_values 表的类（无 static 字段或全为默认 0/null）返回 `has_static_values: false`。配合 `class-data`（static_fields 清单）可定位每个值对应的字段。常量检测：`value_type=23`(STRING) 的字段是硬编码字符串（URL/密钥/正则），`value_type=4`(INT) 是魔法数。

## 安全分析用途

- **反汇编分析**：配合 code_off 反汇编关键方法，查看底层 Dalvik 指令
- **继承层级**：发现应用自定义的类层次结构，定位核心逻辑类
- **统计评估**：快速了解 APK 代码规模，判断是否包含大量第三方库
- **类详情**：查看类实现的接口（如 `OnClickListener` 表明有交互逻辑）
- **字符串搜索**：`regex-strings` 高效定位 URL、密钥模式（如 base64 长串）
- **调试信息**：保留调试信息的 APK 可能泄露源码行号和变量名
