# analysis find-fields-advanced

> Multi-dimensional regex field search (native find_fields)

## 用法

```bash
androguard-skills analysis find-fields-advanced
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--classname` | string | — | `.*` | Regex for class name |
| `--fieldname` | string | — | `.*` | Regex for field name |
| `--fieldtype` | string | — | `.*` | Regex for field type |
| `--accessflags` | string | — | `.*` | Regex for access flags (e.g. private|static) |
| `--limit` | int | — | — | Limit number of results |
| `--with-xrefs` | flag | — | `False` | Include full xref lists |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Multi-dimensional regex field search (native find_fields)

## 对应 API

`skills.analysis_find_fields_advanced(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [analysis 命令组](./)
- [命令索引](../)
