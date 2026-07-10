# apk intent-filters

> Get intent filters for a specific component

## 用法

```bash
androguard-skills apk intent-filters
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `<component>` | string | ✅ | — |  |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Get intent filters for a specific component

## 对应 API

`skills.apk_intent_filters(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [apk 命令组](./)
- [命令索引](../)
