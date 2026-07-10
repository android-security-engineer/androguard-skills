# 项目简介

> 🤖 **Androguard Skills** 是 [AndroGuard](https://github.com/androguard/androguard) 之上的一层 **JSON CLI 封装**，把 Android 逆向工程的全部能力（APK、DEX、AXML、资源、反编译、交叉引用、安全审计、Frida 动态分析）以 **219 个命令** 的形式暴露出来，且每条命令的输出都是 **结构化 JSON**。

## 一句话定位

**让 Android 逆向分析的结果可被程序直接消费，而不需要人去盯屏幕、正则解析控制台文本。**

## 适合谁用

| 👤 角色 | 🎯 为什么需要 Skills |
|---------|---------------------|
| **安全研究员** | 一条命令拿到 APK 的攻击面、19 域漏洞审计、综合风险评分，不用手写 AndroGuard 脚本 |
| **自动化流水线** | 所有输出 JSON，CI 里 `androguard-skills apk security-report` 即出报告，jq 可直接消费 |
| **AI Agent / LLM 工具链** | JSON 输出天然适合喂给大模型做进一步推理；daemon 模式让多步分析共享上下文 |
| **逆向初学者** | 命令即能力索引——不用啃 API 文档，看命令名就知道能做什么 |
| **上层工具开发者** | 通过 Python API 或 JSON-RPC 直接集成，不必重复造 AndroGuard 封装轮子 |

## 核心特性速览

- 🧩 **219 个命令**，覆盖 10 个领域：`daemon` / `apk` / `dex` / `analysis` / `decompile` / `pentest` / `resources` / `visualize` / `util` / `session`
- 📋 **全 JSON 输出**：成功返回数据对象，失败返回 `{"error": "..."}`，结构统一
- ⚡ **Daemon 常驻模式**：后台进程缓存已解析的 APK/DEX/Analysis，跨命令复用，避免重复解析大文件
- 🔌 **JSON-RPC 2.0**：支持单请求与批量请求，多 agent 协同可复用一个 daemon
- 🛡️ **一键安全审计**：`apk security-report` 聚合 19 个安全域 + 综合风险评分
- 🔍 **深度静态分析**：交叉引用、调用图、可达性、污点路径、CFG 基本块
- 🧠 **反编译三态**：纯文本源码 / 结构化 AST / 词法 token 流
- 🎨 **资源深潜**：ARSC 包/locale/类型/配置变体全解析
- 🧪 **动态分析**：基于 Frida 的方法追踪与内存 dump

## 不是什么

- ❌ 不是一个新的反编译器引擎——底层引擎仍是 AndroGuard 与其 DAD 反编译器
- ❌ 不是图形化 IDE——它是 CLI 与 API，定位是"可编程的逆向能力层"
- ❌ 不替代动态插桩框架——`pentest` 组只是对 Frida 的便捷封装

## 下一步

- 🚀 [它能解决什么问题](./what-it-solves) — 理解设计动机
- 📦 [安装](./installation) — 准备环境
- ⏱️ [快速开始](./quick-start) — 五分钟跑通第一条命令
- 🏗️ [架构总览](./architecture) — 理解 CLI / Skills / Daemon 三层
