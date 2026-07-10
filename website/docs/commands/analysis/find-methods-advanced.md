# analysis find-methods-advanced

> Multi-dimensional regex method search: class x method x descriptor x accessflags (native find_methods)

## 用法

```bash
androguard-skills analysis find-methods-advanced
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--classname` | string | — | `.*` | Regex for class name |
| `--methodname` | string | — | `.*` | Regex for method name |
| `--descriptor` | string | — | `.*` | Regex for method descriptor (params + return type) |
| `--accessflags` | string | — | `.*` | Regex for access flags (e.g. public.*static.*native) |
| `--no-external` | flag | — | `False` | Exclude external (non-DEX-implemented) methods |
| `--limit` | int | — | `500` | Max results (default 500) |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Multi-dimensional regex method search: class x method x descriptor x accessflags (native find_methods)

## 对应 API

`skills.analysis_find_methods_advanced(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [analysis 命令组](./)
- [命令索引](../)
