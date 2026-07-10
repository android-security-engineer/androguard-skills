---
layout: home

hero:
  name: Androguard Skills
  text: Android 逆向的 JSON CLI
  tagline: 219 个命令 · Daemon 常驻 · 一键安全审计 · 全输出 JSON，天然适配 Agent 与流水线
  image:
    src: /android-icon.svg
    alt: Androguard Skills
  actions:
    - theme: brand
      text: 快速开始
      link: /guide/quick-start
    - theme: alt
      text: 它能解决什么问题
      link: /guide/what-it-solves
    - theme: alt
      text: 命令索引
      link: /commands/

features:
  - icon: 🤖
    title: 全输出 JSON
    details: 每一条命令的输出都是结构化 JSON，可直接被 jq、Python、或大语言模型消费——告别正则解析控制台文本。
    link: /guide/output-format
    linkText: 输出格式规范 →
  - icon: ⚡
    title: Daemon 常驻模式
    details: 后台进程缓存已加载的 APK/DEX/Analysis，跨命令复用，避免重复解析。JSON-RPC 2.0 协议，支持批量请求。
    link: /guide/daemon-mode
    linkText: Daemon 模式 →
  - icon: 🛡️
    title: 19 域安全审计
    details: WebView/SSL/存储/SQL 注入/PendingIntent/隐私采集/电话短信/动态加载/持久化……一键全量报告 + 综合风险评分。
    link: /audit/overview
    linkText: 安全审计总览 →
  - icon: 🔍
    title: 深度静态分析
    details: 交叉引用、调用图、可达性分析、污点路径、CFG 基本块、switch payload——从字节码到调用链全覆盖。
    link: /commands/analysis/
    linkText: analysis 命令组 →
  - icon: 🧩
    title: 底层 DEX 解构
    details: string_ids/type_ids/proto_ids/method_ids/field_ids/annotations/static_values——直达 DEX 二进制常量池，支持二进制 patch 定位。
    link: /commands/dex/
    linkText: dex 命令组 →
  - icon: 🧠
    title: 反编译三态输出
    details: 纯文本源码、结构化 AST、词法 token 流——适配从人工阅读到自动变换的各类下游需求。
    link: /commands/decompile/
    linkText: decompile 命令组 →
  - icon: 📦
    title: APK 全维度解析
    details: 签名 v1/v2/v3/v31、AXML 加固检测、native 库、组件暴露面、深链接、Manifest 属性批量提取。
    link: /commands/apk/
    linkText: apk 命令组 →
  - icon: 🎨
    title: 资源 ARSC 深潜
    details: 包/locale/类型/配置变体、public.xml、ids.xml、资源 ID 双向查询、类型化解析值。
    link: /commands/resources/
    linkText: resources 命令组 →
  - icon: 🔧
    title: Frida 动态分析
    details: 方法调用追踪、内存 DEX dump——静态分析与动态注入无缝衔接。
    link: /commands/pentest/
    linkText: pentest 命令组 →
---
