# 快速开始

> ⏱️ 五分钟，从安装到拿到第一份安全报告。

## 1. 安装

```bash
pip install androguard
```

## 2. 准备一个 APK

如果你手头没有 APK，可用任意示例。后续命令以 `test.apk` 为例。

## 3. 单次执行模式（最简单）

每条命令独立执行，通过 `--apk-path` 指定 APK：

```bash
# 基本信息
androguard-skills apk info --apk-path test.apk

# 权限
androguard-skills apk permissions --apk-path test.apk

# 签名
androguard-skills apk signature --apk-path test.apk
```

::: tip 用环境变量省去 --apk-path
```bash
export ANDROGUARD_APK_PATH=/path/to/test.apk
androguard-skills apk info        # 不再需要 --apk-path
androguard-skills apk permissions
```
:::

每条命令都会输出 **JSON**，可直接管道给 `jq`：

```bash
androguard-skills apk permissions --apk-path test.apk | jq '.permissions[0]'
```

## 4. Daemon 模式（推荐，避免重复解析）

大 APK 解析慢，重复执行多条命令时启动 daemon 缓存解析结果：

```bash
# 启动后台常驻进程
androguard-skills daemon start

# 加载一次（这一步慢）
androguard-skills load test.apk

# 后续命令复用缓存（毫秒级）
androguard-skills apk info
androguard-skills apk permissions
androguard-skills dex classes --filter "Activity"
androguard-skills analysis call-graph

# 用完停止
androguard-skills daemon stop
```

CLI 会自动探测 daemon 是否在线——在线走 JSON-RPC 复用缓存，离线自动降级单次执行，**命令写法不变**。

## 5. 静态分析：找危险调用

```bash
# 搜索所有包含 "password" 的字符串
androguard-skills dex strings --filter "password"

# 列出所有 native 方法（JNI 边界）
androguard-skills analysis native-methods

# 查某个方法的调用者（反向可达）
androguard-skills analysis method-callers Lcom/example/Crypto; encrypt
```

## 6. 一键安全报告

最高频的用法——一次调用聚合 19 个安全域并给出综合风险评分：

```bash
androguard-skills apk security-report --apk-path test.apk > report.json
jq '.risk_score, .summary' report.json
```

报告涵盖：WebView 安全、SSL 绕过、不安全存储、SQL 注入、PendingIntent、隐私采集、电话短信、动态加载、持久化、弱随机、广播安全、Provider 安全、反分析、网络安全、混淆度量、硬编码密钥、攻击面、深链接……详见 [安全审计总览](../audit/overview)。

## 7. 反编译

```bash
# 反编译某个类为 Java 源码
androguard-skills decompile class Lcom/example/MainActivity;

# 反编译某个方法
androguard-skills decompile method Lcom/example/Crypto; encrypt
```

## 8. 用 Python API

也可直接在 Python 中调用，等价于 CLI：

```python
from androguard.skills import AndroguardSkillsMain
import json

skills = AndroguardSkillsMain()
skills.load_apk("test.apk")

print(json.dumps(skills.apk_info(), indent=2, ensure_ascii=False))
print(json.dumps(skills.apk_permissions(), indent=2, ensure_ascii=False))

# 搜索字符串
print(json.dumps(skills.dex_strings(filter_regex="password"), indent=2, ensure_ascii=False))
```

::: tip CLI 即 API
每条 CLI 命令 `androguard-skills <group> <subcommand>` 几乎一一对应 `AndroguardSkillsMain` 的一个方法（如 `apk info` → `skills.apk_info()`）。详见各命令组文档。
:::

## 下一步

- 🏗️ [架构总览](./architecture) — 理解 CLI / Skills / Daemon 三层
- ⚡ [Daemon 模式](./daemon-mode) — 进阶常驻模式与 JSON-RPC
- 📋 [命令索引](../commands/) — 219 个命令总览
- 🛡️ [安全审计总览](../audit/overview) — 19 域审计详解

---

👈 [安装](./installation) · [架构总览 →](./architecture) 👉
