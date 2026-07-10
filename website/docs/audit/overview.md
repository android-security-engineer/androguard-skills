# 安全审计总览

> 🛡️ Androguard Skills 内置 **19 个安全审计域** + 一键全量报告。这一页是审计能力的导航中心。

## 一键全量报告

最高频入口——一次调用聚合全部审计域并给出综合风险评分：

```bash
androguard-skills apk security-report --apk-path app.apk
```

详见 [一键安全报告](./security-report)。

## 19 个审计域

| # | 域 | 命令 | 关注点 | OWASP |
|---|-----|------|--------|-------|
| 1 | WebView 安全 | `analysis webview-security` | JS 桥 RCE / file 访问 / 调试 / 混合内容 | — |
| 2 | SSL 绕过 | `analysis ssl-safety` | TrustManager / HostnameVerifier 恒真 → MITM | — |
| 3 | 不安全存储 | `analysis insecure-storage` | 外部存储 / 世界可读写 / 明文 prefs+db | M9 |
| 4 | SQL 注入 | `analysis sql-injection` | rawQuery / execSQL / query 执行点 | M7 |
| 5 | PendingIntent | `analysis pending-intent` | FLAG_IMMUTABLE 缺失 / Intent 重定向 | — |
| 6 | 隐私采集 | `analysis privacy-sinks` | 设备标识 / 位置 / 联系人 / 剪贴板 / 录音摄像 | M6 |
| 7 | 电话短信 | `analysis telephony-sms` | 发读短信 / 拨号 / 短信拦截 | — |
| 8 | 动态加载 | `analysis dynamic-code` | DexClassLoader / native 库 / 反射加载 | — |
| 9 | 持久化驻留 | `analysis persistence` | 设备管理员 / 无障碍 / 定时任务 / 通知监听 | — |
| 10 | 弱随机 | `analysis weak-random` | java.util.Random / 固定种子 vs SecureRandom | M10 |
| 11 | 广播安全 | `analysis broadcast-safety` | 无权限广播 / 动态 receiver / 粘性广播 | — |
| 12 | Provider 安全 | `analysis provider-safety` | openFile 路径穿越 / URI 权限授予 | — |
| 13 | 反分析 | `analysis anti-analysis` | root / 模拟器 / 调试器 / Frida / Xposed 检测 | — |
| 14 | 网络安全 | `analysis network-security` | 明文 URL / 证书固定 / SSL 上下文 / HTTP 客户端 | — |
| 15 | 混淆度量 | `analysis obfuscation-metrics` | 类名长度 / 反射密度 / 字符串覆盖 → 0-100 评分 | — |
| 16 | 硬编码密钥 | `analysis hardcoded-secrets` | static 值中的 API key / URL / 私钥 / JWT | — |
| 17 | 攻击面 | `apk attack-surface` | 导出组件 × 前向可达危险 sink | — |
| 18 | 深链接 | `apk deeplinks` | intent-filter / data / web 可达性 | — |
| 19 | native 方法 | `analysis native-methods` | JNI 边界 + 调用方 | — |

## 风险评分

`apk security-report` 输出一个 0-100 的 `risk_score`，综合各域 findings 的数量与严重程度。详见 [一键安全报告](./security-report)。

## 进阶分析

- [攻击面分析](./attack-surface) — 导出组件到危险 sink 的可达地图
- [污点路径](./taint-path) — 源→汇调用链搜索
- [OWASP 映射](./owasp-mapping) — 各域对应的 OWASP Mobile Top 10
- [反分析与加固](./anti-analysis) — 加固识别与对抗

## 典型工作流

```bash
androguard-skills daemon start
androguard-skills load app.apk

# 全量报告
androguard-skills apk security-report --limit 30 > report.json

# 深挖高危域
androguard-skills analysis hardcoded-secrets
androguard-skills analysis webview-security
androguard-skills analysis ssl-safety
androguard-skills apk attack-surface

androguard-skills daemon stop
```
