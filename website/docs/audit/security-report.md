# 一键安全报告

> 🛡️ `apk security-report` —— 一次调用聚合 19 个安全审计域，输出顶层风险总览 + 综合风险评分。

## 命令

```bash
androguard-skills apk security-report [--limit N] [--apk-path <apk>]
```

- `--limit`：每个域的最大 findings 数（默认 20）。
- 输出含 `risk_score`（0-100）与按域分组的 `findings`。

详见 [apk security-report 命令](../commands/apk/security-report)。

## 输出结构（节选）

```json
{
  "risk_score": 72,
  "summary": { "high": 5, "medium": 12, "low": 8 },
  "findings": {
    "webview_security": [...],
    "hardcoded_secrets": [...],
    ...
  }
}
```

## 聚合的 19 域

见 [安全审计总览](./overview)。

## 工作流

```bash
androguard-skills apk security-report --apk-path app.apk > report.json
jq '.risk_score, .summary' report.json
jq '.findings.hardcoded_secrets' report.json
```
