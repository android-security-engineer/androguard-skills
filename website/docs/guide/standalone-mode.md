# 单次执行模式

> 🔹 每条命令独立进程执行，自动加载 APK 并输出 JSON。最简单、无状态、适合脚本与 CI。

## 工作原理

单次模式下，每执行一条 `androguard-skills` 命令：

1. click 解析参数。
2. `_try_daemon_call` 探测 daemon——**不在线**则 fallback 本地。
3. 公共加载器（如 `_apk_loader`）检查是否已加载，未加载则用 `--apk-path` 或环境变量调用 `skills.load_apk()`。
4. 调用对应 skills 方法，`_output_json` 输出 JSON 到 stdout。
5. 进程退出，解析对象随之释放。

## 指定 APK 的三种方式

### 方式 1：`--apk-path` 选项

```bash
androguard-skills apk info --apk-path /path/to/app.apk
```

`apk` / `dex` / `analysis` / `resources` / `visualize` 组的命令都支持该选项。

### 方式 2：环境变量

```bash
export ANDROGUARD_APK_PATH=/path/to/app.apk
androguard-skills apk info
androguard-skills apk permissions
androguard-skills dex classes
```

适合在同一 shell 会话里连续执行多条命令。

### 方式 3：先 `load`（但单次模式下不跨进程）

::: warning 单次模式无法跨进程缓存
单次模式下 `load` 只在**当次进程**内有效，下一条命令是新进程，不会复用。要跨命令复用，必须用 [daemon 模式](./daemon-mode)。
:::

```bash
# 这两条是独立进程，第二条会重新解析
androguard-skills load /path/to/app.apk
androguard-skills apk info --apk-path /path/to/app.apk
```

## 适用场景

| 场景 | 是否适合单次模式 |
|------|-----------------|
| CI 流水线里跑一两条命令出报告 | ✅ 适合 |
| Shell 脚本里做一次性检查 | ✅ 适合 |
| 快速试用某个命令 | ✅ 适合 |
| 连续执行 10+ 条分析命令 | ❌ 用 daemon（避免重复解析） |
| 多 agent 共享同一份解析结果 | ❌ 用 daemon + JSON-RPC |

## 错误处理

单次模式下错误也会以 JSON 返回，不会抛 traceback 到 stdout：

```bash
$ androguard-skills apk info --apk-path /nonexistent.apk
{"error": "APK file not found: /nonexistent.apk"}
```

退出码非零，便于脚本判断：

```bash
if androguard-skills apk verify --apk-path app.apk | jq -e '.valid' >/dev/null; then
  echo "校验通过"
fi
```

## 与 daemon 模式的切换

命令写法**完全一致**——`--apk-path` 参数在两种模式下都可用。区别只在于是否启动了 daemon：

```bash
# 单次模式（无 daemon）
androguard-skills apk info --apk-path app.apk

# daemon 模式
androguard-skills daemon start
androguard-skills load app.apk
androguard-skills apk info          # 自动走 RPC
androguard-skills daemon stop
```

CLI 自动探测，无需改写命令。

---

👈 [架构总览](./architecture) · [Daemon 模式 →](./daemon-mode) 👉
