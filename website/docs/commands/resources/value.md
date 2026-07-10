# resources value

> Resolve a resource ID to its typed value (string/bool/color/dimen/integer/style/id)

## 用法

```bash
androguard-skills resources value
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `<resource_id>` | string | ✅ | — |  |
| `--package` | string | — | — | Resource package name (optional) |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Resolve a resource ID to its typed value (string/bool/color/dimen/integer/style/id)

## 对应 API

`skills.resource_value(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [resources 命令组](./)
- [命令索引](../)
