# 模块：dex_skills

> 📌 DEX 维度业务逻辑：类/方法/字段/字符串/注解/常量池/指令流等 44 个公开函数。

## 🧩 概述

`dex_skills.py` 是业务层中函数最多的模块之一（44 个公开方法），覆盖 DEX 文件的全部结构层：文件头、类表、方法表、字段表、字符串常量池、类型表、原型表、注解目录、静态值数组、调试信息、Dalvik 指令反汇编等。它直接操作 `androguard.core.dex` 的 `DEX` / `ClassDefItem` / `EncodedMethod` / `EncodedField` 等底层对象。

在三层架构中位于**业务层**：第一参数是 `dex_list`（多 DEX 列表，支持 multidex 跨 DEX 搜索）或 `dex_obj`（单 DEX，用于文件头/反汇编等单 DEX 操作），输出是结构化字典。遵循模块级函数约定，无类、无状态。

## 🔧 公开方法

| 方法名 | 签名 | 说明 | 对应 CLI 命令 |
|--------|------|------|-------------|
| `dex_classes` | `(dex_list, filter_regex=None)` | DEX 中的类列表 | `dex classes` |
| `dex_methods` | `(dex_list, class_name=None)` | DEX 中的方法列表 | `dex methods` |
| `dex_strings` | `(dex_list, filter_regex=None)` | DEX 中的字符串 | `dex strings` |
| `dex_fields` | `(dex_list, class_name=None)` | DEX 中的字段列表 | `dex fields` |
| `dex_header` | `(dex_obj)` | DEX 文件头信息 | `dex header` |
| `dex_class_names` | `(dex_list)` | 快速类名列表（不解析整个类） | `dex class-names` |
| `dex_hidden_api` | `(dex_obj)` | 隐藏 API 列表 | `dex hidden-api` |
| `dex_disassemble` | `(dex_obj, offset, size)` | 按 offset+size 反汇编任意代码段 | `dex disassemble` |
| `dex_hierarchy` | `(dex_list)` | 类继承层级树 | `dex hierarchy` |
| `dex_stats` | `(dex_list)` | DEX 统计（各类计数、API 版本、格式） | `dex stats` |
| `dex_class` | `(dex_list, class_name)` | 指定类的详细信息 | `dex class` |
| `dex_regex_strings` | `(dex_list, pattern)` | 正则高效搜索字符串（底层 C 实现） | `dex regex-strings` |
| `dex_debug_info` | `(dex_list, class_name=None)` | 调试信息（参数名恢复 + 行号 + 调试字节码） | `dex debug-info` |
| `dex_encoded_fields` | `(dex_list, class_name=None, limit=None)` | 全部 EncodedField（底层字段表） | `dex encoded-fields` |
| `dex_encoded_methods` | `(dex_list, class_name=None, limit=None)` | 全部 EncodedMethod（底层方法表） | `dex encoded-methods` |
| `dex_encoded_method` | `(dex_list, method_name)` | 按方法名查 EncodedMethod（跨类） | `dex encoded-method` |
| `dex_encoded_method_descriptor` | `(dex_list, class_name, method_name, descriptor)` | 按 class+method+descriptor 精确查（处理重载） | `dex encoded-method-descriptor` |
| `dex_cm_lookup` | `(dex_list, idx, kind='string')` | 按 ID 查 ClassManager 常量池表 | `dex cm-lookup` |
| `dex_fields_id` | `(dex_list, limit=None)` | 字段索引表 FieldIdItem 列表 | `dex fields-id` |
| `dex_version` | `(dex_list)` | DEX 版本号 | `dex version` |
| `dex_items` | `(dex_list)` | 底层 item 表信息 | `dex items` |
| `dex_lens` | `(dex_list)` | 各表长度 | `dex lens` |
| `dex_class_manager` | `(dex_list)` | ClassManager 概要 | `dex class-manager` |
| `dex_encoded_fields_class` | `(dex_list, class_name, limit=None)` | 指定类的全部 EncodedField | `dex encoded-fields-class` |
| `dex_encoded_methods_class` | `(dex_list, class_name, limit=None)` | 指定类的全部 EncodedMethod | `dex encoded-methods-class` |
| `dex_encoded_method_by_idx` | `(dex_list, idx)` | 按 DEX 内方法索引取 EncodedMethod | `dex encoded-method-by-idx` |
| `dex_encoded_field_by_name` | `(dex_list, name, limit=None)` | 按字段名取 EncodedField（跨类） | `dex encoded-field-by-name` |
| `dex_encoded_field_descriptor` | `(dex_list, class_name, field_name, descriptor)` | 按 class+field+descriptor 精确查 EncodedField | `dex encoded-field-descriptor` |
| `dex_method_id_by_name` | `(dex_list, name, limit=None)` | 常量池 method_ids 表按名搜索 | `dex method-id-by-name` |
| `dex_method_ids` | `(dex_list, limit=None)` | 常量池 method_ids 全量表 | `dex method-ids` |
| `dex_field_id_by_name` | `(dex_list, name, limit=None)` | 常量池 field_ids 表按名搜索 | `dex field-id-by-name` |
| `dex_encoded_method_class_method` | `(dex_list, class_name, method_name)` | 类内按方法名查（无需 descriptor） | `dex encoded-method-class-method` |
| `dex_method_info` | `(dex_list, class_name, method_name)` | 方法寄存器/参数映射等签名级元信息 | `dex method-info` |
| `dex_method_code` | `(dex_list, class_name, method_name)` | DalvikCode 底层（寄存器帧 + try/catch + handlers） | `dex method-code` |
| `dex_method_instructions` | `(dex_list, class_name, method_name, limit=None)` | 按方法反汇编所有 Dalvik 指令 | `dex method-instructions` |
| `dex_class_meta` | `(dex_list, class_name)` | ClassDefItem 底层元信息 | `dex class-meta` |
| `dex_class_data` | `(dex_list, class_name, limit=None)` | ClassDataItem 分类视图（direct/virtual + static/instance） | `dex class-data` |
| `dex_field_init_value` | `(dex_list, class_name, field_name)` | 字段初始值（硬编码常量检测） | `dex field-init-value` |
| `dex_method_instructions_idx` | `(dex_list, class_name, method_name, limit=None)` | 按方法反汇编指令带字节偏移 idx | `dex method-instructions-idx` |
| `dex_proto_ids` | `(dex_list, limit=None)` | 方法原型表 ProtoIdItem（shorty/返回类型/参数） | `dex proto-ids` |
| `dex_annotations` | `(dex_list, class_name=None, limit=None)` | 注解目录（类级/字段级/方法级/参数级） | `dex annotations` |
| `dex_static_values` | `(dex_list, class_name)` | 类静态值数组 EncodedArray | `dex static-values` |
| `dex_strings_table` | `(dex_list, filter_regex=None, limit=None)` | 字符串常量池完整表（idx+值+偏移+UTF-16 长度） | `dex strings-table` |
| `dex_type_ids` | `(dex_list, limit=None)` | 类型常量池表 type_ids | `dex type-ids` |

## 🧩 关键实现要点

- **跨 DEX 搜索**：多数函数取 `dex_list`（multidex 场景下 `classes.dex / classes2.dex ...`），遍历所有 DEX 聚合结果，而非只查首个；少数单 DEX 操作（`dex_header` / `dex_hidden_api` / `dex_disassemble`）取 `dex_obj` 或 `dex_list[0]`。
- **`dex_method_instructions` 指令流序列化**：用 `EncodedMethod.get_instructions()` 迭代器 `list()` 物化后，逐条提取 `name` / `output` / `op_value` / `hex` / `length`，并进一步 `get_operands()` 把操作数结构化（寄存器/常量池 idx/字面值），比 `output` 字符串更精确可程序化解析。`limit` 截断返回但保留 `total` 原始计数。
- **`dex_regex_strings` 用 C 实现**：注释指出底层是 C 实现的正则搜索，比全量遍历字符串表快；`dex_strings_table` 则提供完整常量池表（含字节偏移与 UTF-16 长度），用于精确索引。
- **重载处理**：`dex_encoded_method_descriptor` / `dex_encoded_field_descriptor` 按 class+name+descriptor 三元组精确匹配，处理同名重载；而 `dex_encoded_method` / `dex_encoded_field_by_name` 仅按名跨类搜索，返回所有同名命中。

## 🔗 与 CLI 的映射

`main.py` 的 `dex` 命令组通过 `_try_daemon_call("dex_classes", {...})` 等走 daemon；daemon 端持有已加载的 `dex_list`（由 `load_apk` 时从 APK 提取或 `load_dex` 独立加载），按命令分发到本模块函数。非 daemon 模式由 `AndroguardSkills` 实例直接调用 `dex_skills.*`。

## 📚 相关

- [代码模块总览](./)
- 命令组文档：`/commands/dex/`
