# DEX 底层 item 表与计数

封装第六轮新增的 DEX 底层 item 表查询能力。DEX 文件由多个 item 表组成（header/string_data/fields_id/methods_id/classes_def/codes），这些命令暴露其 offset/length/计数，用于 DEX 结构分析与修补定位。

## 命令

### `dex items`

获取 DEX 底层 item 表信息（offset/length/raw_size）。

```bash
androguard-skills dex items --apk-path test.apk
```

**输出：**
```json
{
  "dex_count": 1,
  "dexes": [
    {
      "dex_index": 0,
      "header": {"type": "HeaderItem", "off": 0, "length": 112},
      "codes": {"type": "CodeItem", "off": 52240, "length": 106898, "raw_size": 106898},
      "string_data": {"type": "list", "count": 2575},
      "fields_id": {"type": "FieldHIdItem", "off": 20024, "length": 6624, "raw_size": 6624},
      "methods_id": {"type": "MethodHIdItem", "off": 26648, "length": 16184, "raw_size": 16184},
      "classes_def": {"type": "ClassHDefItem", "off": 42832, "length": "error: 169664"}
    }
  ]
}
```

**字段说明：**
- `off`：item 表在 DEX 文件中的偏移
- `length`：item 表字节长度
- `raw_size`：原始字节大小（`get_raw()` 成功时）
- `string_data` 是 list 类型，返回 `count`

> 注意：部分 item（如 `classes_def`）的 `length` 可能显示 `error: ...`——这是 AndroGuard 自身 `get_length()` 的已知 bug（内部访问未初始化字段），offset 仍可用。命令已用 try/except 兜底，不影响其他字段。

### `dex lens`

获取 DEX 各表的条目计数。

```bash
androguard-skills dex lens --apk-path test.apk
```

**输出：**
```json
{
  "dex_count": 1,
  "dexes": [
    {
      "dex_index": 0,
      "classes": 294,
      "methods": 2023,
      "strings": 2575,
      "fields": 828,
      "encoded_fields": 799,
      "encoded_methods": 1431
    }
  ]
}
```

**字段说明：**
- `classes` / `methods` / `strings` / `fields`：DEX 顶级表条目数（`get_len_*`）
- `encoded_fields` / `encoded_methods`：实际编码的字段/方法数（`get_len_encoded_*`，去除重复定义后）

`methods`（2023）与 `encoded_methods`（1431）的差值反映方法表与类内编码方法的区别（方法表含所有声明，encoded 只含类体定义）。

### `dex class-manager`

获取 DEX 的 ClassManager 概要信息。ClassManager 是 DEX 的常量池管理器，`cm-lookup` 命令的底层对象。

```bash
androguard-skills dex class-manager --apk-path test.apk
```

**输出：**
```json
{
  "dex_count": 1,
  "dexes": [
    {
      "dex_index": 0,
      "type": "ClassManager",
      "methods": ["add_type_item", "get_ascii_string", "get_class_data_item", "get_code", "get_field", "get_field_ref", "get_method", "get_method_ref", "get_string", "get_type", ...]
    }
  ]
}
```

`methods` 列出 ClassManager 可用的查询方法（用于了解常量池查询能力）。

## 相关命令

- [`dex-encoded`](dex-encoded.md) — EncodedField/EncodedMethod 详情 + cm-lookup 常量池查询
- [`dex-disassemble`](dex-disassemble.md) — DEX 反汇编/层级/统计
- [`dex-header`](dex-header.md) — DEX 头信息
