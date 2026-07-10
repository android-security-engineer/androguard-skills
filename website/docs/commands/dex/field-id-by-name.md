# dex field-id-by-name

> Search field_ids constant-pool table by field name (includes external refs)

## 用法

```bash
androguard-skills dex field-id-by-name
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `<name>` | string | ✅ | — |  |
| `--limit` | int | — | — | Max results per DEX |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Search field_ids constant-pool table by field name (includes external refs)

## 对应 API

`skills.dex_field_id_by_name(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [dex 命令组](./)
- [命令索引](../)
