# 模块：daemon.py · Daemon 进程管理

> 📌 TCP/JSON-RPC 常驻进程，缓存已解析对象，跨命令复用

## 概述

`androguard/skills/daemon.py`（457 行）提供 **进程管理** 与 **RPC 通道** 两条能力，自身**不实现任何业务逻辑**。所有查询能力仍由 `AndroguardSkillsMain`（在 `main.py`）承载，daemon 通过 `getattr(skills, method_name)` 反射路由请求。

架构（行 7–17）：

```
┌─────────────────┐     TCP localhost       ┌──────────────────┐
│  CLI Client     │ ◄────────────────────► │  Daemon Process  │
│  (androguard-   │    JSON-RPC 协议         │  (常驻后台)       │
│   skills CLI)   │                         │                  │
└─────────────────┘                         │  缓存:           │
                                            │  - APK 对象      │
                                            │  - DEX 对象      │
                                            │  - Analysis 对象  │
                                            └──────────────────┘
```

CLI 通过 `main.py` 的 `_try_daemon_call` 先探测 daemon：在跑则走 RPC 复用已解析对象，不在跑则单次执行 fallback。daemon 的价值在于避免每个命令都重新 `AnalyzeAPK()`（大 APK 解析耗时数十秒），常驻后 `load` 一次即可被几十个命令、多个 agent 跨连接复用。

## 类结构

### `DaemonServer` — TCP 服务器（行 77）

监听 TCP localhost，接受 JSON-RPC 请求，调用 `AndroguardSkillsMain` 方法并返回结果。

| 方法 | 行号 | 职责 |
|------|------|------|
| `__init__(port=8899, host="127.0.0.1")` | 85 | 持有 `_skills`/`_server`/`_running`/`_start_time`，`_skills` 初始为 `None`（懒加载） |
| `_get_skills()` | 92 | 懒加载 `AndroguardSkillsMain` 单例（首次调用时 import，避免 daemon 启动即加载重依赖） |
| `_handle_client(reader, writer)` | 100 | 处理客户端连接，按 `\n` 缓冲累积切出完整请求逐条分发（见关键机制） |
| `_dispatch(request)` | 155 | 分发 JSON-RPC 请求，支持单请求（`dict`）与批量请求（`list`，JSON-RPC 2.0） |
| `_dispatch_single(request)` | 171 | 分发单个请求：内置 `status`/`shutdown`，其余 `getattr(skills, method)` 反射路由 |
| `_run_server()` | 230 | 运行 TCP 服务器：配置日志、`asyncio.start_server`、写 PID/PORT 文件、循环等待 |
| `start()` | 274 | 启动 daemon 进程：先 `_is_daemon_running()` 防重，再 `asyncio.run(_run_server())` |
| `_cleanup()` | 296 | 清理 `daemon.pid` 与 `daemon.port` 文件 |
| `_is_daemon_running()`（静态方法） | 304 | 端口探测 + PID 双重确认（见关键机制） |

### `DaemonClient` — RPC 客户端封装（行 371）

CLI 命令通过此类与 daemon 通信。

| 方法 | 行号 | 职责 |
|------|------|------|
| `__init__(timeout=30.0)` | 378 | 默认 30s timeout；`_try_daemon_call` 对慢命令传入 600s |
| `is_daemon_running()` | 381 | 委托 `DaemonServer._is_daemon_running()` |
| `_get_daemon_port()` | 385 | 读 `daemon.port` 文件，失败回退默认 `8899` |
| `call(method, params)` | 393 | 发送 JSON-RPC 请求并读取响应；返回 `result`，遇 `error` 抛 `RuntimeError` |
| `stop_daemon()` | 446 | 调 `shutdown` 方法并轮询等待 daemon 停止（最多 10×0.5s） |

`call`（行 393–444）发送 `{"jsonrpc":"2.0","method":...,"params":...,"id":1}` 加 `\n`，循环 `recv` 直到读到 `\n`。错误处理：`socket.timeout` → `ConnectionError("timed out")`；`ConnectionRefusedError` → `ConnectionError("refused")`；响应含 `error` → `RuntimeError(f"Daemon error: {msg}")`（被 `_try_daemon_call` 捕获转结构化 error）。

## 关键机制

### 🔄 `_handle_client` — 按 \n 缓冲累积（行 100）

此前假设一次 `read` 即完整 JSON，大请求（&gt;64KB 批量/大 params）会被 TCP 分片截断致 `JSONDecodeError`。修复后维护逐连接缓冲区（行 108–144）：

```python
buffer = b""
while self._running:
    data = await reader.read(65536)
    if not data:
        break
    buffer += data
    while b"\n" in buffer:                       # 切出所有完整请求
        line, buffer = buffer.split(b"\n", 1)
        line = line.strip()
        if not line:
            continue
        request = json.loads(line.decode("utf-8"))
        response = await self._dispatch(request)
        ...
        writer.write(json.dumps(response, cls=_DaemonJsonEncoder).encode() + b"\n")
        await writer.drain()
```

效果：**大请求不截断**（分片重组）、**多请求流水线**（一次 read 拿到多条拼在一起的请求逐条分发）、空行跳过。`ConnectionResetError`/`BrokenPipeError` 静默忽略，`finally` 关闭 writer。

### 🎯 `_dispatch` / `_dispatch_single` — JSON-RPC 2.0 分发（行 155 / 171）

`_dispatch`（行 155）：批量请求（`list`）逐个分发，每个独立隔离（一个失败不影响其余），返回批量响应列表；单请求（`dict`）直接委托 `_dispatch_single`。

`_dispatch_single`（行 171）三段路由：

1. **内置方法**（行 178–197）：`status` 返回 `{"status":"running","pid":...,"uptime":...,"apk_loaded":...}`；`shutdown` 置 `_running=False` 返回 `{"status":"shutting_down"}`。
2. **反射路由**（行 200–210）：`getattr(skills, method_name, None)` 取方法，`None` 返回 JSON-RPC error `-32601 Method not found`。
3. **执行**（行 212–228）：`load_apk`/`load_dex` 特殊处理参数名（`path` 优先于 `apk_path`/`dex_path`），其余 `method(**params)`；成功返回 `result`，异常返回 error `-32603`。

### 🛡️ `_is_daemon_running` — 端口探测 + PID 双重确认（行 304）

PID 复用问题（daemon 崩溃后 OS 把 PID 分配给别的进程）会让单纯 PID 检查误判"在跑"→`start` 拒绝启动。双重确认流程：

1. **PID 文件检查**（行 313）：不存在 → 直接返回 `False`。
2. **进程存活检查**（行 317–335）：`os.kill(pid, 0)` 探测进程；`ProcessLookupError`/`FileNotFoundError`/`ValueError`/`OSError` 均视为进程不存在，清理残留 PID 文件后返回 `False`。
3. **端口探测兜底**（行 337–368）：读 `daemon.port`，`socket.create_connection` 连 `127.0.0.1:port`（timeout=1s），发 `{"method":"status"}` 请求，确认响应含 `"running"` 才返回 `True`。

端口被别的服务占了（响应不含 `running`）→ 返回 `False`；PID 存活但端口不响应（daemon 卡死/崩溃）→ 清理残留 PID 文件后返回 `False`。这保证 `start`/`status`/`stop` 在 PID 复用、卡死、端口被占三种异常下都不会误判。

### ⏱️ 慢命令 600s timeout

daemon 侧本身无 timeout（`_dispatch` 同步调用方法），timeout 发生在客户端 `DaemonClient.call`。`main._try_daemon_call`（行 2551）对 `load_apk`/`load_dex`/`session_analyze_apk`/`session_add_apk`/`session_add_dex` 五个慢命令用 `600.0` timeout，其余用 `30.0`。见 [main.py 模块](./main#🔌-try-daemon-call-method-params-daemon-探测-fallback行-2533)。

### 📝 日志 — WARNING 级，文件轮转（行 230–251）

`_run_server` 的日志配置是生产健壮性关键（行 232–238 注释）：AndroGuard 在 `INFO` 级别就会对每个 `ClassAnalysis`/`MethodAnalysis` 打日志，解析一个 APK 产生数万行 INFO，瞬间塞满 stderr 管道缓冲（64KB）。daemon 的事件循环同时往 stderr 写日志和往 socket 写响应，stderr 满了会阻塞整个循环，导致响应无法写回、客户端超时——经典死锁。

配置（行 241–251）：

- 默认 `LOGURU_LEVEL=WARNING`（仅错误/警告），可用环境变量覆盖为 `DEBUG`/`INFO` 调试，但生产环境勿用低级别。
- `logger.remove()` 移除默认 stderr handler（避免管道死锁），落文件到 `${XDG_RUNTIME_DIR:-/tmp}/androguard-skills-daemon/daemon.log`。
- `rotation="5 MB"`、`retention=3`（5MB 轮转，保留 3 份）。

运行时文件目录（行 64–69）：

```
DAEMON_DIR = ${XDG_RUNTIME_DIR:-/tmp}/androguard-skills-daemon/
├── daemon.pid   # daemon 进程 PID
└── daemon.port  # 监听端口
└── daemon.log   # 日志（5MB 轮转）
```

## 对应 CLI 命令

| CLI 命令 | 行为 | 走 daemon？ |
|----------|------|-------------|
| `androguard-skills daemon start` | `DaemonServer.start()` 启动常驻进程（行 2616） | 启动它 |
| `androguard-skills daemon stop` | `DaemonClient.stop_daemon()` 发 `shutdown`（行 2626） | 是 |
| `androguard-skills daemon status` | `DaemonClient.call("status")`（行 2639） | 是 |
| `androguard-skills load <apk>` | `_try_daemon_call("load_apk", {"path":...})` 优先（行 2656） | 优先，fallback 单次 |
| `androguard-skills unload` | `_try_daemon_call("unload")` 优先（行 2672） | 优先，fallback 单次 |
| `androguard-skills load-dex <dex>` | 直接单次 `skills.load_dex()`（行 6938） | 否（DEX 无缓存语义） |
| 各 `apk`/`dex`/`analysis`/... 命令 | `_try_daemon_call("<method>")` 优先，fallback 走加载器 | 优先，fallback 单次 |

详见 [`/commands/daemon/`](../commands/daemon/) 与 [main.py 模块](./main#命令方法映射)。

## 相关

- 📚 [代码模块总览](./) — 全部模块地图
- 📡 [main.py 模块](./main) — 对应的 CLI 入口（`_try_daemon_call` 在此）
- 🔌 [Daemon 模式](../guide/daemon-mode) — 使用指南
- 📡 [JSON-RPC 协议](../guide/jsonrpc-protocol) — 请求/响应/批量/错误码规范
- 🗂️ [daemon 命令组](../commands/daemon/) — `start`/`stop`/`status` 命令参考
- 🧠 [内存管理](../guide/memory-management) — daemon 长跑下的内存边界（`unload` + `malloc_trim`）
