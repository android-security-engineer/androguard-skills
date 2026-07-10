# 模块：decompiler_skills

> 📌 封装 `androguard.decompiler`，把 DvMethod / DvClass 反编译结果导出为文本源码、AST、token 流三种形态。

## 🧩 概述

`decompiler_skills.py` 共 6 个公开函数，对称分布在「方法级」与「类级」两个粒度，各三种输出形态：源码 / AST / token。它直接使用底层 `androguard.decompiler.decompile.DvMethod` 与 `DvClass`而非走 `DecompilerDAD` 高层包装（后者有 bug，见实现要点）。

在三层架构中位于**业务层**：输入是 `dex_list` + `analysis_obj` + 类名/方法名，输出是结构化字典。遵循模块级函数约定，无类、无状态。

## 🔧 公开方法

| 方法名 | 签名 | 说明 | 对应 CLI 命令 |
|--------|------|------|-------------|
| `decompile_class` | `(dex_list, analysis_obj, class_name: str)` | 反编译指定类为纯文本源码 | `decompile class` |
| `decompile_method` | `(dex_list, analysis_obj, class_name: str, method_name: str)` | 反编译指定方法为纯文本源码 | `decompile method` |
| `decompile_method_ast` | `(dex_list, analysis_obj, class_name: str, method_name: str)` | 反编译方法为结构化 AST | `decompile method-ast` |
| `decompile_method_tokens` | `(dex_list, analysis_obj, class_name: str, method_name: str, limit: int = None)` | 反编译方法为 token 流 | `decompile method-tokens` |
| `decompile_class_ast` | `(dex_list, analysis_obj, class_name: str, fields_limit: int = None, methods_limit: int = None)` | 反编译类为类级 AST（含全部字段+方法 AST） | `decompile class-ast` |
| `decompile_class_tokens` | `(dex_list, analysis_obj, class_name: str, limit: int = None)` | 反编译类为类级 token 流 | `decompile class-tokens` |

## 🧩 关键实现要点

- **绕过 DAD bug**：`decompile_method` 在 docstring 中注明 `DecompilerDAD.get_source_method()` 有 bug——它调用 `analysis.get_method(MethodAnalysis)` 但该方法期望 `EncodedMethod` 参数，导致返回 None。本函数直接 `from androguard.decompiler.decompile import DvMethod`，`DvMethod(method_analysis).process()` 后 `get_source()`，绕过高层包装。
- **AST vs token vs 源码三层**：`decompile_method_ast` 用 `dv.process(doAST=True)` + `get_ast()` 返回嵌套 AST dict（triple/flags/ret/params/comments/body），body 是可程序化遍历的节点；`decompile_method_tokens` 用 `get_source_ext()` 返回 `(token_type, value)` 二元组列表，适合词法级定位；`decompile_method` 则是 `get_source()` 纯文本。三者互补覆盖自动检测代码模式、精确片段定位、人工阅读三类需求。
- **类级 token 递归序列化**：`decompile_class_tokens` 的子 token 可能是 `(type, value)`、`(type, value, extra...)` 或嵌套 list，函数定义内部 `_ser_subtoken` 递归序列化，过滤不可序列化对象（如 `EncodedField`），按 `category`（PACKAGE/PROTOTYPE/FIELD/METHOD）分组输出。
- **类级 AST 限量**：`decompile_class_ast` 支持 `fields_limit` / `methods_limit` 截断字段与方法 AST 列表，但保留 `fields_total` / `methods_total` 原始计数，避免类级 AST 过大撑爆响应。

## 🔗 与 CLI 的映射

`main.py` 的 `decompile` 命令组通过 `_try_daemon_call("decompile_method", {...})` 走 daemon JSON-RPC；daemon 端持有已加载的 `dex_list` 与 `analysis_obj`，按 class/method 定位后调用本模块函数。非 daemon 模式由 `AndroguardSkills` 实例直接调用。

## 📚 相关

- [代码模块总览](./)
- 命令组文档：`/commands/decompile/`
