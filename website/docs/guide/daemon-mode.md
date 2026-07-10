# Daemon 模式

> ⚡ 后台常驻进程，缓存已加载的 APK/DEX/Analysis，跨命令复用，避免重复解析。这是高频分析与多 agent 协同的推荐模式。

## 基本用法

```bash
# 1. 启动 daemon
androguard-skills daemon start

# 2. 加载 APK（这一步慢，只做一次）
androguard-skills load /path/to/big.apk

# 3. 后续命令全部复用缓存（毫秒级）
androguard-skills apk info
androguard-skills apk permissions
androguard-skills dex classes --filter "Activity"
androguard-skills analysis call-graph
androguard-skills apk security-report

# 4. 用完停止
androguard-skills daemon stop
```

## 生命周期命令

| 命令 | 作用 |
|------|------|
| `daemon start [--port 8899]` | 启动后台进程，默认监听 `127.0.0.1:8899` |
| `daemon status` | 检查 daemon 是否在线、端口、加载状态 |
| `daemon stop` | 停止 daemon |
| `load <apk>` | 向 daemon 加载 APK（缓存在 daemon 进程内） |
| `load-dex <dex>` | 向 daemon 加载独立 DEX（不走 APK 路径） |
| `unload` | 卸载当前对象 + `malloc_trim` 归还内存 |

详见 [daemon 命令组](../commands/daemon/) 与 [顶层命令 load/unload](../commands/load)。

## CLI 如何探测 daemon

每条业务命令执行时，CLI 会先调 `_try_daemon_call`：

- **daemon 在线** → 通过 `DaemonClient.call` 发 JSON-RPC 请求，daemon 用 `getattr(skills, method)` 反射调用，复用已缓存对象。
- **daemon 离线** → 自动降级为单次执行模式，本地加载。

因此**同一套命令在两种模式下写法完全一致**，仅性能不同。

## 为什么快

解析一个大 APK 的开销集中在三处：

1. **APK 解压与 AXML 解码**（`APK` 对象构建）
2. **DEX 字节码反汇编**（`DalvikVMFormat`）
3. **交叉引用构建**（`Analysis`，类与方法之间的 xref 成环，构建最耗时）

单次模式下每条命令都要重做这三步。daemon 模式下只在 `load` 时做一次，后续查询直接复用内存中的对象。

## 端口与并发

- 默认 `127.0.0.1:8899`，仅本机可访问（安全：不暴露到网络）。
- 可用 `--port` 自定义端口。
- daemon 基于 asyncio TCP，单连接顺序处理请求，支持**流水线**（多个请求在一个连接内排队执行）。
- 多个客户端可同时连接，daemon 会串行化处理（避免对共享 Analysis 对象的并发竞争）。

## 批量请求（JSON-RPC 2.0）

daemon 支持 JSON-RPC 2.0 批量请求——单连接一次发送一个请求**数组**，服务端顺序执行并返回批量响应：

```bash
# 一次发两个请求
echo '[{"jsonrpc":"2.0","method":"status","params":{},"id":1},
       {"jsonrpc":"2.0","method":"apk_info","params":{},"id":2}]' | \
  nc 127.0.0.1 8899
# → [{"jsonrpc":"2.0","result":{...},"id":1},{"jsonrpc":"2.0","result":{...},"id":2}]
```

批量内单个失败不影响其余请求。详见 [JSON-RPC 协议](./jsonrpc-protocol)。

## 多 agent 协同

多个 AI Agent / 脚本可共用一个 daemon：

- A agent `load` APK 后，B agent 直接 `apk info` 即可拿到结果（共享缓存）。
- 适合"一个 agent 做重解析，多个 agent 做轻查询"的分工。

::: warning 共享状态非隔离
所有客户端共享同一份已加载对象。若一个客户端 `load` 了新 APK，旧 APK 缓存会被替换。需要多 APK 并行分析时，请开多个 daemon（不同端口）或用 [session 组](../commands/session/)。
:::

## 何时该用 daemon

| 场景 | 推荐 |
|------|------|
| 连续执行 5 条以上命令 | ✅ daemon |
| 大 APK（>50MB 或多 DEX） | ✅ daemon |
| 多 agent / 多脚本共享解析 | ✅ daemon |
| 交互式探索（边查边改命令） | ✅ daemon |
| CI 里只跑 1-2 条命令 | 单次即可 |
| 一次性脚本 | 单次即可 |

## 日志与排障

daemon 默认以 **WARNING** 级别把日志写入 `~/.androguard/skills/daemon.log`（5MB 轮转，保留 3 份）。

需要详细日志时：

```bash
LOGURU_LEVEL=DEBUG androguard-skills daemon start
```

::: danger 生产环境勿用低级别
AndroGuard 在 **INFO** 级别就会对每个类/方法打日志，解析大 APK 时产生数万行，可能拖慢 daemon。生产用 WARNING。
:::

daemon 不向 stderr 输出 AndroGuard 内部日志，避免后台启动时 stderr 管道阻塞导致死锁。

## 相关文档

- [内存管理（长跑）](./memory-management) — 长跑下 RSS 控制
- [JSON-RPC 协议](./jsonrpc-protocol) — 协议细节
- [daemon 命令组](../commands/daemon/) — 命令参数

---

👈 [单次执行模式](./standalone-mode) · [内存管理 →](./memory-management) 👉
