# apk manifest-attrs

> Batch extract attribute values from AndroidManifest tags

## 用法

```bash
androguard-skills apk manifest-attrs
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--tag` | string | ✅ | — | Manifest tag name (e.g. uses-permission) |
| `--attribute` | string | ✅ | — | Attribute name (e.g. name) |
| `--filter` | string | — | — | (可重复) Attribute filter as key=value (can repeat) |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Batch extract attribute values from AndroidManifest tags

## 对应 API

`skills.apk_manifest_attrs(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [apk 命令组](./)
- [命令索引](../)
