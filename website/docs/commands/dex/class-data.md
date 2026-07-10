# dex class-data

> Get ClassDataItem categorized view (direct/virtual methods + static/instance fields)

## 用法

```bash
androguard-skills dex class-data
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `<class_name>` | string | ✅ | — |  |
| `--limit` | int | — | — | Max items per category (direct/virtual/static/instance) |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Get ClassDataItem categorized view (direct/virtual methods + static/instance fields)

## 对应 API

`skills.dex_class_data(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [dex 命令组](./)
- [命令索引](../)
