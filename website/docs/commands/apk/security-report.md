# apk security-report

> One-shot full security report: aggregate all audits + composite risk score (audit suite closure)

## 用法

```bash
androguard-skills apk security-report
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--limit` | int | — | `20` | Max samples/findings per domain (default 20) |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

One-shot full security report: aggregate all audits + composite risk score (audit suite closure)

## 对应 API

`skills.apk_security_report(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [apk 命令组](./)
- [命令索引](../)
