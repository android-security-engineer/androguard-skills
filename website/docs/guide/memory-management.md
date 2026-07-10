# 内存管理（长跑）

> 🧠 daemon 长时间运行、连续分析多个 APK 时，需要主动管理内存，否则 RSS 会高位驻留。这一页讲清原理与操作。

## 问题：为什么 RSS 不回落

连续 `load` 不同 APK 时，`load_apk` 已经会 **gc 旧的 Analysis 对象**——Analysis 持有海量 xref 跨引用成环，纯引用计数无法回收，所以 `load_apk` 内部主动调用 `gc.collect()` 释放。

但即便 Python 层对象已释放，**glibc 的 malloc 不主动把内存归还给操作系统**——已释放的堆块留在 arena 里供下次分配复用。结果：Python 对象没了，但 daemon 进程的 RSS（常驻内存）依然高位。

## 解法：显式 `unload`

处理完一个 APK、即将切换上下文或空闲时，显式执行：

```bash
androguard-skills load big.apk          # 解析（峰值高）
androguard-skills apk security-report   # 取结果
androguard-skills unload                # 释放引用 + malloc_trim(0)，RSS 回落
```

`unload` 做两件事：

1. **释放 Python 引用**：清空持有的 APK/DEX/Analysis 对象。
2. **`malloc_trim(0)`**：显式让 glibc 把空闲 arena 归还给 OS，RSS 立即下降。

## 典型长跑工作流

```bash
androguard-skills daemon start

# 处理 APK 1
androguard-skills load app1.apk
androguard-skills apk security-report > report1.json
androguard-skills unload                  # ← 关键：释放 + trim

# 处理 APK 2（峰值从低位重新爬升，不会叠加上一个的残留）
androguard-skills load app2.apk
androguard-skills apk security-report > report2.json
androguard-skills unload

# ...可安全处理任意多个

androguard-skills daemon stop
```

## 何时需要 `unload`

| 场景 | 是否需要 unload |
|------|----------------|
| 连续 `load` 不同 APK | ✅ 每次处理完后 unload |
| 单个 APK 内反复查询 | ❌ 不需要（对象要复用） |
| daemon 即将空闲一段时间 | ✅ unload 释放给 OS |
| daemon 即将停止 | 不必（`daemon stop` 进程退出全释放） |

## load 失败不会腐化状态

如果 `load` 一个损坏的 APK 失败：

- `load_apk` 抛异常（而非返回 dict），CLI 的 `_SkillsCliGroup` 统一捕获为 `{"error": ...}`。
- 内部会 gc 旧 Analysis 对象，**不会**留下半解析的腐化状态。
- 之前的 APK 缓存若存在则保持可用（除非你显式 unload）。

## 监控 daemon 内存

```bash
# 查看 daemon 进程 RSS
ps -o pid,rss,cmd -p $(cat ~/.androguard/skills/daemon.pid)

# 或用 daemon status
androguard-skills daemon status
```

如果观察到 RSS 持续上涨且不回落，确认是否在长跑流程里漏了 `unload`。

## 相关文档

- [unload 命令](../commands/unload)
- [Daemon 模式](./daemon-mode)
- [load 命令](../commands/load)

---

👈 [Daemon 模式](./daemon-mode) · [JSON-RPC 协议 →](./jsonrpc-protocol) 👉
