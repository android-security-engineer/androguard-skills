# analysis method-summary

> Aggregate method overview (info + 6 xref summaries + CFG/exception counts + source)

## 用法

```bash
androguard-skills analysis method-summary
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `<class_name>` | string | ✅ | — |  |
| `<method_name>` | string | ✅ | — |  |
| `--descriptor` | string | — | — | Method descriptor (optional; first match if omitted) |
| `--no-source` | flag | — | `False` | Exclude decompiled Java source |
| `--xref-limit` | int | — | `10` | Max refs per xref category (0 = all) |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Aggregate method overview (info + 6 xref summaries + CFG/exception counts + source)

## 对应 API

`skills.analysis_method_summary(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [analysis 命令组](./)
- [命令索引](../)
