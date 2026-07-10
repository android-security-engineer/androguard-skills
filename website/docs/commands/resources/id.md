# resources id

> Bidirectional resource ID lookup (ID&lt;-&gt;name)

## 用法

```bash
androguard-skills resources id
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `<package_name>` | string | ✅ | — |  |
| `--rid` | int | — | — | Resource ID (decimal) for ID-&gt;name lookup |
| `--type` | string | — | — | Resource type (string/color/layout) for name-&gt;ID lookup |
| `--key` | string | — | — | Resource key name for name-&gt;ID lookup |
| `--locale` | string | — | — | Locale (optional) |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Bidirectional resource ID lookup (ID&lt;-&gt;name)

## 对应 API

`skills.resource_id(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [resources 命令组](./)
- [命令索引](../)
