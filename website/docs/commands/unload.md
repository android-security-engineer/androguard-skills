# unload

> 🔝 卸载当前已加载的 APK/DEX/Analysis 对象，并调用 `malloc_trim(0)` 归还内存给 OS。

## 用法

```bash
androguard-skills unload
```

## 参数

无。

## 说明

主要服务于 **daemon 长跑场景**。处理完一个 APK、即将切换上下文或空闲时调用：

1. **释放 Python 引用**：清空持有的 APK / DEX / Analysis 对象。
2. **`malloc_trim(0)`**：让 glibc 把空闲 arena 归还给操作系统，daemon 进程 RSS 立即回落。

不调用 `unload` 时，即便 Python 层对象已被 `load` 新 APK 时 gc，glibc 也不主动归还 arena，导致 RSS 高位驻留。

## 示例

```bash
androguard-skills daemon start

androguard-skills load big.apk
androguard-skills apk security-report > report.json
androguard-skills unload                # ← 释放 + trim，RSS 回落

androguard-skills load next.apk         # 从低位重新爬升，不叠加
androguard-skills apk security-report > report2.json
androguard-skills unload

androguard-skills daemon stop
```

## 何时该用

| 场景 | 是否 unload |
|------|------------|
| 连续 `load` 不同 APK | ✅ 每次处理完后 |
| 单 APK 内反复查询 | ❌ 对象要复用 |
| daemon 即将空闲 | ✅ 释放给 OS |
| daemon 即将 stop | 不必（进程退出全释放） |

## 对应 API

`skills.unload()`。

## 相关命令

- [load](./load) — 加载
- [内存管理](../guide/memory-management) — 长跑内存控制详解
- [daemon 模式](../guide/daemon-mode)
