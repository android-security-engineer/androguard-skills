# analysis url-endpoints

> Extract URL/host/IP network endpoints from the string pool with referencing methods

## 用法

```bash
androguard-skills analysis url-endpoints
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--limit` | int | — | `200` | Max samples per category (default 200) |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Extract URL/host/IP network endpoints from the string pool with referencing methods

## 对应 API

`skills.analysis_url_endpoints(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [analysis 命令组](./)
- [命令索引](../)
