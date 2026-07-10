# resources strings-all

> Get all string resources (full strings.xml across packages)

## 用法

```bash
androguard-skills resources strings-all
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--raw` | flag | — | `False` | Return raw XML text instead of parsed list |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Get all string resources (full strings.xml across packages)

## 对应 API

`skills.resource_strings_all(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [resources 命令组](./)
- [命令索引](../)
