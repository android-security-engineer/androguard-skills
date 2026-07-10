# resources resolved-strings

> Get all resolved string resources (package-&gt;locale-&gt;rid-&gt;value)

## 用法

```bash
androguard-skills resources resolved-strings
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--locale` | string | — | — | Locale filter (e.g. zh/en); all if omitted |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Get all resolved string resources (package-&gt;locale-&gt;rid-&gt;value)

## 对应 API

`skills.resource_resolved_strings(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [resources 命令组](./)
- [命令索引](../)
