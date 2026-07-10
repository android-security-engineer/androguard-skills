# resources public

> Get public.xml (full type/name/id resource mapping)

## 用法

```bash
androguard-skills resources public
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `<package_name>` | string | ✅ | — |  |
| `--locale` | string | — | — | Locale (optional) |
| `--raw` | flag | — | `False` | Return raw XML text instead of parsed list |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Get public.xml (full type/name/id resource mapping)

## 对应 API

`skills.resource_public(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [resources 命令组](./)
- [命令索引](../)
