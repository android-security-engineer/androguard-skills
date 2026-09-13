# Agent API：无头模式与 GUI 模式

> 🤖 面向 AI Agent 的接入层。工具暴露**两类**互补的 API：**无头模式**（纯 API 调用，无需启动任何界面）与 **GUI 模式**（通过 API 自动化控制界面，同时人工可正常使用）。

它们共享同一个工具注册表（`ToolRegistry`）与状态，但边界清晰：**无头模式是纯净的、零 GUI 依赖**，**GUI 模式额外叠加 9 个 `ui.*` 工具**来驱动你正在看的那个终端界面。

## 两种模式速览

| 模式 | 构造 | MCP 命令 | 工具数 | 是否引入 GUI 依赖 |
|------|------|----------|--------|------------------|
| **无头** | `HeadlessAPI()` | `androguard-skills mcp` | 217（全部分析工具） | ❌ 否 |
| **GUI** | `HeadlessAPI(include_ui=True)` | `androguard-skills mcp --with-ui` | 226（217 分析 + 9 个 `ui.*`） | ✅ 是（惰性） |

两类模式的能力集完全一致：GUI 模式的分析工具与无头模式**逐名相同**，只是额外多了控制界面的工具。

## 无头模式：纯 API，不启动程序

无头模式是默认形态。它把 217 个分析命令包装成可发现的类型化工具，状态保存在底层 `AndroguardSkillsMain` 单例中——Agent 可以 `load_apk` 一次，然后连续多次分析，无需重复解析。

```python
from androguard.agent import HeadlessAPI

api = HeadlessAPI()          # 无头：纯净，不导入任何 prompt_toolkit / TUI

tools = api.list_tools()     # 217 个工具
print(len(tools))

result = api.call_tool("load_apk", {"path": "/tmp/app.apk"})
result = api.call_tool("apk_info", {})
result = api.call_tool("apk_security_report", {"per_type_limit": 20})
```

MCP 接入（JSON-RPC line-framed on stdio）——最常用于 Claude Desktop / Claude Code：

```bash
# 直接作为 stdio MCP 服务器运行
androguard-skills mcp
```

Claude Code 配置 `~/.claude/settings.json`：

```json
{
  "mcpServers": {
    "androguard": { "command": "androguard-skills", "args": ["mcp"] }
  }
}
```

无头模式的关键承诺：**不启动界面、零 GUI 依赖**。它在干净子进程里不会导入 `prompt_toolkit` 或 `androguard.ui`（这是有回归测试锁住的）。

## GUI 模式：自动化界面，同时人工可用

GUI 模式额外暴露 9 个 `ui.*` 工具，用于**自动化控制你在用的那个终端界面**。核心设计：Agent 与人工共享**同一个** `DynamicUI` 状态——Agent 发的每个动作（选中、过滤、聚焦）都会通过 `app.invalidate()` 触发重绘，让屏幕上的操作者实时看到变化。

```python
from androguard.agent import HeadlessAPI

api = HeadlessAPI(include_ui=True)   # GUI：217 分析 + 9 个 ui.* 工具

# 启动终端 UI（后台线程），操作者可在其中查看 trace 事件
api.call_tool("ui.start", {})

# 查看界面当前状态（结构化快照，无需解析终端转义序列）
snap = api.call_tool("ui.snapshot", {})
```

MCP 接入：

```bash
androguard-skills mcp --with-ui
```

### `ui.*` 工具清单

| 工具 | 作用 |
|------|------|
| `ui.start` | 后台线程启动终端 UI |
| `ui.stop` | 请求退出正在运行的 prompt_toolkit 应用 |
| `ui.snapshot` | 返回结构化界面快照（状态/选中项/可见事务/焦点/过滤器） |
| `ui.action` | 执行语义动作：`select` / `move` / `focus` / `filter` / `toggle_help` / `toggle_filters` / `close_modals` / `clear`，并返回新快照 |
| `ui.get_transaction` | 按索引取单个事务的完整参数与返回值 |
| `ui.export_transactions` | 导出全部事务（可选按接口/方法/类型过滤），含完整参数；支持 `limit` / `offset` 分页 |
| `ui.query` | 非破坏性统计/查询，不改动操作者当前视图；支持 `limit` / `offset` 分页 |
| `ui.search` | 全文搜索（参数/返回值/方法名），不改动当前过滤器；支持 `limit` / `offset` 分页 |
| `ui.publish` | 发布一条 trace 事件（供 UI 测试或外部 trace 生产者） |

### 示例：Agent 驱动界面

```python
api.call_tool("ui.publish", {
    "index": 0,
    "from_method": "com.example.LoginActivity.onClick",
    "to_method": "com.example.api.login",
    "params": {"username": "admin", "password": "***"},
    "ret_value": {"token": "..."},
})

# 选中第 0 条事务
api.call_tool("ui.action", {"action": "select", "index": 0})

# 设置过滤器（界面上的过滤器面板会同步，操作者看到同一个过滤）
api.call_tool("ui.action", {
    "action": "filter",
    "interface": "com.example",
    "types": ["event"],
})

# 非破坏性搜索敏感串，不打乱操作者当前视图
api.call_tool("ui.search", {"keyword": "password", "limit": 100, "offset": 0})

# 返回结果包含 count（匹配总数）、transactions（当前页）和 has_more（是否还有下一页）。
# 快照确认操作者当前看到的状态
api.call_tool("ui.snapshot", {})
```

### Agent 与人工共存机制

- **共享状态**：`UIAgentController` 持有（或附着到）同一个 `DynamicUI`；Agent 的读写与人工的键盘操作落在同一份事务列表、同一个过滤器上。
- **实时刷新**：所有会改变界面的动作都调用线程安全的 `app.invalidate()`，人工立即看到 Agent 的变更。
- **线程安全**：过滤面板的文本同步被推迟到渲染线程（`_apply_filter_sync`），避免从 Agent 线程直接触碰 prompt_toolkit 控件。
- **惰性构造**：`HeadlessAPI(include_ui=True)` 只实例化轻量的 `UIAgentController`（不碰 `prompt_toolkit`）；真正的 `DynamicUI` 直到调用某个 `ui.*` 工具才经 `_ensure_ui()` 生成。

## 入口工厂

`androguard.agent` 包提供统一工厂，让两种模式在语义上一眼可见：

```python
from androguard.agent import build_agent_api

headless = build_agent_api()              # 无头
gui = build_agent_api(include_ui=True)    # GUI
```

## 协议处理

`HeadlessAPI.handle()` 同时兼容两套调用约定，适合直接嵌入进程或放在 stdio/TCP/HTTP 之后：

- **MCP 方法**：`initialize`、`notifications/initialized`、`tools/list`、`tools/call`
- **直接方法名**：`method` 为工具名时等价于 `call_tool(name, params)`（兼容既有 daemon 方法名）

## 相关文档

- [Python API](./python-api) — `AndroguardSkillsMain` 方法直调
- [Daemon 模式](./daemon-mode) — 跨进程共享技能
- [JSON-RPC 协议](./jsonrpc-protocol) — daemon 侧线协议

---

👈 [Python API](./python-api) · [常见工作流 →](./workflows) 👉
