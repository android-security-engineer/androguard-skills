# OWASP 映射

> 📐 各审计域与 [OWASP Mobile Top 10](https://owasp.org/www-project-mobile-top-10/) 的对应关系。

## OWASP Mobile Top 10 → Skills 命令

| OWASP | 名称 | Skills 命令 | 说明 |
|-------|------|-------------|------|
| M1 | 凭证使用不当 | `analysis hardcoded-secrets` | 硬编码密钥/凭证 |
| M2 | 服务器不可信 | `analysis network-security` | 服务端证书校验/固定 |
| M3 | 不安全通信 | `analysis ssl-safety` / `analysis network-security` | SSL 绕过、明文传输 |
| M4 | 不安全认证 | `analysis pending-intent` | Intent 重定向、认证绕过 |
| M5 | 密码学不足 | `analysis crypto-usage` | 弱加密（ECB/DES/MD5/SHA1/RC4） |
| M6 | 不安全授权 | `analysis privacy-sinks` | 隐私数据越权采集 |
| M7 | 客户端代码质量 | `analysis sql-injection` | SQL 注入面 |
| M8 | 代码篡改 | `apk verify` / `apk signing-versions` | 签名校验、完整性 |
| M9 | 逆向工程 | `analysis obfuscation-metrics` / `analysis anti-analysis` | 混淆与反分析 |
| M10 | 环境杂项 | `analysis weak-random` | 不安全随机数 |

> 注：OWASP Mobile Top 10 版本会迭代，上表基于经典条目做能力映射，非严格一一对应。

## 覆盖矩阵

| 域 | 命令 | 主要 OWASP |
|----|------|-----------|
| WebView 安全 | `analysis webview-security` | M3, M7 |
| SSL 绕过 | `analysis ssl-safety` | M3 |
| 不安全存储 | `analysis insecure-storage` | M9（OWASP 2024 重新归为存储） |
| SQL 注入 | `analysis sql-injection` | M7 |
| PendingIntent | `analysis pending-intent` | M4 |
| 隐私采集 | `analysis privacy-sinks` | M6 |
| 电话短信 | `analysis telephony-sms` | M6 |
| 动态加载 | `analysis dynamic-code` | M8 |
| 持久化驻留 | `analysis persistence` | M6 |
| 弱随机 | `analysis weak-random` | M10 |
| 反分析 | `analysis anti-analysis` | M9 |
| 网络安全 | `analysis network-security` | M3 |
| 混淆度量 | `analysis obfuscation-metrics` | M9 |
| 硬编码密钥 | `analysis hardcoded-secrets` | M1 |

## 相关

- [安全审计总览](./overview)
- [一键安全报告](./security-report)
