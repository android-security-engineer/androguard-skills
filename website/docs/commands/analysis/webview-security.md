# analysis webview-security

> Audit WebView security configuration (JS bridge/file access/JS/debug risky settings + findings)

## 用法

```bash
androguard-skills analysis webview-security
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--limit` | int | — | `100` | Max samples per category (default 100) |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Audit WebView security configuration (JS bridge/file access/JS/debug risky settings + findings)

## 对应 API

`skills.analysis_webview_security(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [analysis 命令组](./)
- [命令索引](../)
