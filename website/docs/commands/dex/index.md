# 🧩 dex · DEX 信息

> DEX 字节码与底层结构：类/方法/字段、反汇编、常量池表（string/type/proto/method/field_ids）、Encoded 表、注解、静态值。共 44 个命令。

共 **44** 个命令。

## 命令列表

| 命令 | 说明 |
|------|------|
| [`annotations`](./annotations) | List DEX annotation directory (class/field/method/parameter annotations) |
| [`class`](./class) | Get detailed information for a specific DEX class |
| [`class-data`](./class-data) | Get ClassDataItem categorized view (direct/virtual methods + static/instance fields) |
| [`class-manager`](./class-manager) | Get DEX ClassManager summary (constant pool manager) |
| [`class-meta`](./class-meta) | Get ClassDefItem low-level meta (annotations/source_file/interfaces/superclass/offsets) |
| [`class-names`](./class-names) | Get quick class name list (without full class parsing) |
| [`classes`](./classes) | List DEX classes |
| [`cm-lookup`](./cm-lookup) | Look up ClassManager constant pool entry by index |
| [`debug-info`](./debug-info) | Get DEX debug information |
| [`disassemble`](./disassemble) | Disassemble DEX bytecode at a given offset |
| [`encoded-field-by-name`](./encoded-field-by-name) | Get EncodedField by field name (across all classes) |
| [`encoded-field-descriptor`](./encoded-field-descriptor) | Find EncodedField by class + field + descriptor (exact match) |
| [`encoded-fields`](./encoded-fields) | List all EncodedField (low-level field table) |
| [`encoded-fields-class`](./encoded-fields-class) | Get all EncodedField of a specific class (class field table) |
| [`encoded-method`](./encoded-method) | Find EncodedMethod by method name (across all classes) |
| [`encoded-method-by-idx`](./encoded-method-by-idx) | Get EncodedMethod by DEX method index |
| [`encoded-method-class-method`](./encoded-method-class-method) | Find EncodedMethod by class + method name (no descriptor needed) |
| [`encoded-method-descriptor`](./encoded-method-descriptor) | Find EncodedMethod by class+method+descriptor (handles overloads) |
| [`encoded-methods`](./encoded-methods) | List all EncodedMethod (low-level method table) |
| [`encoded-methods-class`](./encoded-methods-class) | Get all EncodedMethod of a specific class (class method table) |
| [`field-id-by-name`](./field-id-by-name) | Search field_ids constant-pool table by field name (includes external refs) |
| [`field-init-value`](./field-init-value) | Get field initial value (hardcoded constant detection) |
| [`fields`](./fields) | List DEX fields |
| [`fields-id`](./fields-id) | Get DEX field index table (FieldIdItem) |
| [`header`](./header) | Get DEX file header information |
| [`hidden-api`](./hidden-api) | Get hidden API list from DEX |
| [`hierarchy`](./hierarchy) | Get DEX class inheritance hierarchy tree |
| [`items`](./items) | Get low-level DEX item tables (header/codes/string_data/fields_id/methods_id/classes_def) |
| [`lens`](./lens) | Get DEX table lengths (classes/methods/strings/fields/encoded_*) |
| [`method-code`](./method-code) | Get method DalvikCode low-level info (register frame + try/catch + handlers) |
| [`method-id-by-name`](./method-id-by-name) | Search method_ids constant-pool table by method name (includes external refs) |
| [`method-ids`](./method-ids) | List all method_ids constant-pool entries (includes external refs, no code) |
| [`method-info`](./method-info) | Method signature-level info (registers/params mapping/locals/address) |
| [`method-instructions`](./method-instructions) | Disassemble all Dalvik instructions of a method (instruction stream) |
| [`method-instructions-idx`](./method-instructions-idx) | Disassemble all instructions of a method with byte offset idx |
| [`methods`](./methods) | List DEX methods |
| [`proto-ids`](./proto-ids) | List DEX method prototype table (ProtoIdItem: shorty/return_type/parameters) |
| [`regex-strings`](./regex-strings) | Search DEX strings using regex (fast C-level implementation) |
| [`static-values`](./static-values) | Get class static values array (EncodedArray: all static field init values) |
| [`stats`](./stats) | Get DEX statistics (counts, API version, format) |
| [`strings`](./strings) | List DEX strings |
| [`strings-table`](./strings-table) | List string constant pool with idx/offset/utf16_size (binary location for patching) |
| [`type-ids`](./type-ids) | List DEX type constant pool (type_ids: descriptor_idx -&gt; type descriptor) |
| [`version`](./version) | Get DEX version number |

## 用法示例

```bash
androguard-skills dex --help    # 查看本组所有命令
androguard-skills dex <子命令> --help
```

- [命令索引](../)
