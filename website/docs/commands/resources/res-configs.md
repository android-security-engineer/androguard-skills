# resources res-configs

> List config variants (locale/density, raw entry) for a specific resource ID

## 用法

```bash
androguard-skills resources res-configs
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `<resource_id>` | string | ✅ | — |  |
| `--no-fallback` | flag | — | `False` | Do not fall back to default config when exact match missing |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

List config variants (locale/density, raw entry) for a specific resource ID

## 对应 API

`skills.resource_res_configs(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [resources 命令组](./)
- [命令索引](../)
