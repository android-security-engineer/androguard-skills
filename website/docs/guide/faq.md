# FAQ

> ❓ 常见问题与排障。

## 通用

### Q: `androguard-skills` 命令找不到？

确认安装了 `androguard` 且 `PATH` 正确：

```bash
pip install androguard
export PATH="$HOME/.local/bin:$PATH"   # 若用 --user 安装
androguard-skills --help
```

### Q: 命令输出是 JSON，但我想看人类可读？

配合 `jq`：

```bash
androguard-skills apk info --apk-path app.apk | jq
```

或用 Python API 直接处理 dict。

### Q: 大 APK 解析很慢，正常吗？

正常。APK 解压 + DEX 反汇编 + 交叉引用构建是大开销。**用 daemon 模式**只解析一次：

```bash
androguard-skills daemon start
androguard-skills load big.apk     # 慢，只此一次
androguard-skills apk info         # 快，复用缓存
```

## daemon

### Q: `daemon status` 说没运行，但我明明 start 过？

可能进程崩溃或被 kill 了。查日志 `~/.androguard/skills/daemon.log`。重新 `daemon start` 即可。

### Q: daemon 占用内存一直涨？

长跑连续 `load` 不同 APK 时，每个处理完要 `unload`：

```bash
androguard-skills load app1.apk
androguard-skills apk security-report > r1.json
androguard-skills unload    # ← 释放 + malloc_trim
```

详见 [内存管理](./memory-management)。

### Q: 多个客户端能同时连 daemon 吗？

能，但请求会被**串行化**处理（避免对共享 Analysis 对象的并发竞争）。要真正并行分析多 APK，开多个 daemon（不同端口）或用多个进程各自单次模式。

### Q: daemon 端口被占？

用 `--port` 换端口：

```bash
androguard-skills daemon start --port 8900
```

### Q: `load_apk` 通过 RPC 调用超时？

`load_apk` 大 APK 可能要数十秒。`DaemonClient` 对慢命令放宽到 600s。若你自写 RPC 客户端，务必对 `load_apk` 设大超时。

## 命令与参数

### Q: 类名要怎么写？

Dalvik 描述符，带 `L` 和 `;`：`Lcom/example/MainActivity;`。详见 [类名与描述符](./class-descriptors)。

### Q: 方法重载怎么精确指定？

用 `--descriptor`（部分命令支持），如 `--descriptor "(I)V"`。

### Q: `--apk-path` 每次都要写？

设环境变量省去：

```bash
export ANDROGUARD_APK_PATH=/path/to/app.apk
```

### Q: 二进制字段（如 `apk file` 的 content）是什么编码？

base64。解码：

```bash
androguard-skills apk file AndroidManifest.xml --apk-path app.apk | jq -r '.content' | base64 -d
```

## 安全审计

### Q: `apk security-report` 覆盖哪些域？

19 个：WebView、SSL、不安全存储、SQL 注入、PendingIntent、隐私采集、电话短信、动态加载、持久化、弱随机、广播安全、Provider 安全、反分析、网络安全、混淆度量、硬编码密钥、攻击面、深链接、native 方法。详见 [安全审计总览](../audit/overview)。

### Q: 误报多吗？

静态分析天然有误报。`security-report` 的 findings 标注了 severity，建议人工复核 high/critical 项，配合 `decompile method` 看源码确认。

### Q: `analysis taint-path` 是完整污点分析吗？

不是。它只在**调用图**上找源→汇的最短路径，不做数据流跟踪。适合快速验证调用链可达性，深度污点分析需配合动态插桩（`pentest`）。

## 性能

### Q: `analysis call-graph` 很慢/输出很大？

全量调用图节点边很多。用 `--limit` 限制边数，或用 `call-graph-filtered` 只取子图。

### Q: `dex classes` 返回太多？

用 `--filter` 正则过滤，或 `dex class-names` 只要名字（不解析整个类，更快）。

## 集成

### Q: 能在 CI 里用吗？

能。全 JSON 输出 + 非零退出码，天然适配 CI。见 [工作流 1](./workflows#工作流-1-apk-安全体检-ci-友好)。

### Q: 能让 AI Agent 用吗？

能。JSON 输出适合喂给 LLM；daemon 模式让多步分析共享上下文。method 命名清晰，便于 agent 选择工具。

### Q: 和原生 `androguard` CLI 的关系？

`androguard` 是上游原生 CLI（面向人类阅读输出）。`androguard-skills` 是其上的 JSON 化封装层，两者共享同一套引擎，安装一个包即得两个命令。

---

👈 [常见工作流](./workflows) · [命令索引 →](../commands/) 👉
