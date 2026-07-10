# analysis android-api-usage

> List all Android platform APIs used by the APK (batch)

## 用法

```bash
androguard-skills analysis android-api-usage
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--limit` | int | — | — | Max number of APIs to return |
| `--with-xrefs` | flag | — | `False` | Expand caller xrefs for each API |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

List all Android platform APIs used by the APK (batch)

## 对应 API

`skills.analysis_android_api_usage(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [analysis 命令组](./)
- [命令索引](../)
