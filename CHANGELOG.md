# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/) 与 [语义化版本](https://semver.org/lang/zh-CN/)。所有新增功能、变更与修复都会记录在此文件。

## [4.2.0] - 2026-09-13

本次发布为 Androguard 带来面向 **AI Agent / 自动化安全审计** 的完整接入能力：新增 MCP 服务、Skill 命令系统与常驻 daemon 模式，并配套文档站。整体向后兼容，未移除任何既有 API。

### 新增

- **MCP 服务（`androguard-mcp`）**：基于 MCP 2024-11-05 协议的 stdio server，支持 AI Agent（Claude Desktop / Claude Code 等）通过 JSON-RPC 直接调用整个 Androguard 能力面。
  - 新增 `androguard/agent/`：`headless`（HeadlessAPI 统一路由）、`protocol`（ToolRegistry / JSON Schema 工具定义）、`server`（stdio 传输）、`ui`（GUI 双模控制工具）。
  - 提供 `--with-ui` 参数，可同时暴露 UI 控制工具（`ui.snapshot`、`ui.action` 等）。
- **`androguard-skills` 命令系统**：将 219 个 CLI 命令组织为 Skill，覆盖 APK / DEX / 分析（analysis）/ 资源（resources）/ 反编译（decompile）/ 可视化（visualize）/ 会话（session）/ util / pentest 九大域，方便 Agent 与脚本逐命令调用。
- **daemon 模式**：常驻进程，通过 JSON-RPC 批量处理请求，内置会话缓存与隔离，提升多 APK 连续分析的内存有界性与吞吐；支持优雅关闭（SIGTERM / SIGINT）。
- **VitePress 文档站**（`website/`）：覆盖 219 个 CLI 命令、daemon 模式、MCP 接入说明与代码模块参考；命令文档由 `introspect_commands.py` 从 click 树自动内省生成，与 CLI 保持同步。
- **GUI 双模（`ui.*`）**：在 headless 基础上提供快照、动作、选择、表格等 UI 控制工具，共 6 个 `ui.*` 工具。

### 变更

- 更新权限数据（`aosp_permissions` / `api_permission_mappings`）与资源数据（`public.xml`）。
- CLI 入口：新增 `androguard-mcp`，并暴露 `androguard-skills` 命令。

### 安全 / 依赖

- 升级 `cryptography` 至 `>=46.0.6`。

### 质量保障

- 测试规模大幅扩充：覆盖 CLI 冒烟与错误路径、API 覆盖矩阵（公开 API 表面 100% 映射）、daemon JSON-RPC / 并发 / 内存 / 生命周期、文档一致性、website 构建与命令同步、MCP 协议与 headless server 等，累计 1200+ 测试用例。

### 文档

- 新增 `website/` 下的 GitHub Pages 文档站（`https://android-security-engineer.github.io/androguard-skills/`），README 已加入指引。

[4.1.4] 之前的版本历史请参见上游仓库 [androguard/androguard](https://github.com/androguard/androguard)。
