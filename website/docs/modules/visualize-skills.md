# 模块：visualize_skills

> 📌 将 AndroGuard 的方法控制流图（CFG）导出为 DOT / 图片 / JSON 三种可消费形态，共 3 个公开函数。

## 🧩 概述

`visualize_skills.py` 是业务层最薄的一个模块，仅 3 个公开函数。它把 `androguard.core.bytecode` 的三个可视化入口（`method2dot` / `method2format` / `method2json`）封装成返回 `dict` 的纯函数，便于 CLI 层统一 JSON 序列化。

在三层架构中位于**业务层**：输入是 `MethodAnalysis` 对象（由 analysis 模块或 daemon 提供），输出是结构化字典。设计上遵循模块级函数约定，第一参数即引擎对象，无类、无状态。

## 🔧 公开方法

| 方法名 | 签名 | 说明 | 对应 CLI 命令 |
|--------|------|------|-------------|
| `visualize_method_dot` | `(method_analysis)` | 导出方法 CFG 为 DOT 格式字符串 | `visualize method-dot` |
| `visualize_method_image` | `(method_analysis, output: str, fmt: str = "png")` | 导出方法 CFG 为图片（PNG/JPG），需 Graphviz | `visualize method-image` |
| `visualize_method_json` | `(method_analysis)` | 导出方法 CFG 为 JSON 结构 | `visualize method-json` |

## 🧩 关键实现要点

- **延迟导入引擎**：三个函数都在函数体内 `from androguard.core.bytecode import method2dot / method2format / method2json`，避免模块加载期依赖 Graphviz；当 Graphviz 缺失时图片导出会进入 `except` 分支返回结构化 error，而非崩溃 CLI。
- **异常降级保留标识**：失败时仍尽量回填 `class` / `method` 字段（用 `if method_analysis else "unknown"` 守卫），保证错误响应里能定位到是哪个方法的可视化失败。
- **三元对称**：DOT（文本可 diff）/ image（人看）/ JSON（程序化遍历 CFG 节点）覆盖三种下游消费场景，三者入参同为 `MethodAnalysis`，仅输出载体不同。

## 🔗 与 CLI 的映射

`main.py` 中的 `visualize` 命令组通过 `_try_daemon_call("visualize_method_dot", ...)` 等走 daemon JSON-RPC；daemon 端持有已加载的 `Analysis` 对象，按方法定位到 `MethodAnalysis` 后调用本模块函数。非 daemon 模式下则由 `AndroguardSkills` 实例直接调用 `visualize_skills.visualize_method_dot(...)`。

## 📚 相关

- [代码模块总览](./)
- 命令组文档：`/commands/visualize/`
