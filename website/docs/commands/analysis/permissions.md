# analysis permissions

> List API methods that require permissions (batch, by API level)

## 用法

```bash
androguard-skills analysis permissions
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--apilevel` | string | — | — | API level for permission mapping (default: APK effective target) |
| `--limit` | int | — | — | Max number of results |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

List API methods that require permissions (batch, by API level)

## 对应 API

`skills.analysis_permissions(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [analysis 命令组](./)
- [命令索引](../)
