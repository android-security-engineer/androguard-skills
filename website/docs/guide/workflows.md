# 常见工作流

> 🔧 这一页给出几条端到端工作流，把多个命令串起来解决实际问题。

## 工作流 1：APK 安全体检（CI 友好）

**目标**：对一个 APK 快速出安全报告，CI 里跑。

```bash
#!/bin/bash
set -e
APK="$1"

androguard-skills daemon start
trap 'androguard-skills daemon stop' EXIT

androguard-skills load "$APK"

# 一键全量报告
androguard-skills apk security-report --limit 30 > security-report.json

# 单独深挖几个高危域
androguard-skills analysis hardcoded-secrets > secrets.json
androguard-skills analysis webview-security > webview.json
androguard-skills apk attack-surface > attack-surface.json

# 用 jq 提取高危项
echo "=== 高危发现 ==="
jq '[.findings[] | select(.severity=="high" or .severity=="critical")] | length' \
  security-report.json
```

## 工作流 2：追踪一个危险方法的来源

**目标**：发现 `Lcom/evil/Crypto;` 的 `weakEncrypt` 方法，找出谁调用它、从哪个入口能到达。

```bash
androguard-skills daemon start
androguard-skills load app.apk

# 1. 确认方法存在 + 看签名
androguard-skills analysis method-detail Lcom/evil/Crypto; weakEncrypt "()Ljavax/crypto/Cipher;"

# 2. 直接调用者（1 层）
androguard-skills analysis method-xrefs-detail Lcom/evil/Crypto; weakEncrypt "()Ljavax/crypto/Cipher;"

# 3. 反向可达：递归溯源到入口（5 层）
androguard-skills analysis method-callers Lcom/evil/Crypto; weakEncrypt \
  --descriptor "()Ljavax/crypto/Cipher;" --max-depth 5

# 4. 看方法源码
androguard-skills decompile method Lcom/evil/Crypto; weakEncrypt
```

## 工作流 3：污点分析——从密码字段到网络发送

**目标**：验证用户密码是否会被明文发送到网络。

```bash
androguard-skills load app.apk

# 源：取密码的方法
# 汇：网络发送方法
androguard-skills analysis taint-path \
  --src-class Lcom/app/LoginActivity; \
  --src-method getPassword \
  --dst-class Lcom/app/NetClient; \
  --dst-method post \
  --max-depth 8
```

若有路径返回，说明存在从密码到网络的调用链，需进一步看是否加密。

## 工作流 4：脱壳——定位加固与动态加载

**目标**：判断 APK 是否加固、是否有动态加载 DEX 的行为。

```bash
# AXML 加固检测
androguard-skills apk manifest-axml

# 混淆/加固评分（0-100）
androguard-skills analysis obfuscation-metrics

# 反分析检测（root/模拟器/Frida/Xposed）
androguard-skills analysis anti-analysis

# 动态代码加载审计
androguard-skills analysis dynamic-code

# native 方法枚举（找 .so 入口）
androguard-skills analysis native-methods
```

## 工作流 5：导出全量资源

**目标**：把 APK 的字符串、布局资源导出供本地化检查。

```bash
androguard-skills load app.apk

# 包名
androguard-skills resources packages

# 全量字符串（含多语言）
androguard-skills resources strings-all > strings.json

# public.xml 映射
androguard-skills resources public <package> > public.json

# 指定 locale 的字符串
androguard-skills resources resolved-strings --locale zh
```

## 工作流 6：攻击面枚举

**目标**：找出所有导出组件 + 它们能到达的危险 sink。

```bash
androguard-skills load app.apk

# 组件安全属性详情（哪些 exported）
androguard-skills apk component-details

# 深链接（外部可达入口）
androguard-skills apk deeplinks

# 攻击面聚合（导出组件 × 前向可达危险 sink）
androguard-skills apk attack-surface --max-depth 4 --include-safe
```

## 工作流 7：批量处理多个 APK

**目标**：处理一个目录下的 APK，每个出一份报告，控制内存。

```bash
#!/bin/bash
androguard-skills daemon start
trap 'androguard-skills daemon stop' EXIT

for apk in /apks/*.apk; do
  name=$(basename "$apk" .apk)
  androguard-skills load "$apk"
  androguard-skills apk security-report --limit 20 > "reports/${name}.json"
  androguard-skills unload    # ← 释放内存，避免下一个叠加
done
```

::: tip 长跑必 unload
连续 `load` 不同 APK 时，每个处理完务必 `unload`，否则 RSS 会高位驻留。详见 [内存管理](./memory-management)。
:::

## 工作流 8：从字节码到 CFG 可视化

**目标**：把某个方法的控制流图导出成图片，人工分析逻辑分支。

```bash
androguard-skills load app.apk

# 先看方法基本信息
androguard-skills dex method-info Lcom/app/Logic; decide "(Z)V"

# 基本块列表（CFG 节点）
androguard-skills analysis method-basic-blocks Lcom/app/Logic; decide "(Z)V"

# 导出为 DOT（无需 Graphviz）
androguard-skills visualize method-dot Lcom/app/Logic; decide > cfg.dot

# 导出为图片（需要 Graphviz 的 dot）
androguard-skills visualize method-image Lcom/app/Logic; decide -o cfg.png -f png

# 或导出为 JSON 自行渲染
androguard-skills visualize method-json Lcom/app/Logic; decide > cfg.json
```

## 工作流 9：硬编码密钥扫描

```bash
androguard-skills load app.apk

# 扫描所有 static 字段值
androguard-skills analysis hardcoded-secrets --limit 200

# 配合 URL 端点
androguard-skills analysis url-endpoints

# 配合加密用法
androguard-skills analysis crypto-usage
```

## 工作流 10：多 DEX 关联分析（session）

**目标**：一个 APK 含多个 DEX，跨 DEX 查类归属与字符串。

```bash
androguard-skills session analyze-apk app.apk

# 或手动建 session
androguard-skills session create
androguard-skills session add-apk app.apk
androguard-skills session info
androguard-skills session filename-by-class Lcom/example/Foo;
androguard-skills session strings --limit 100
androguard-skills session classes --limit 5
```

---

👈 [Python API](./python-api) · [FAQ →](./faq) 👉
