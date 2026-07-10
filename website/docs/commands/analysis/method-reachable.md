# analysis method-reachable

> Reachability analysis: methods reachable from a given method (recursive xref_to expansion)

## 用法

```bash
androguard-skills analysis method-reachable
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `<class_name>` | string | ✅ | — |  |
| `<method_name>` | string | ✅ | — |  |
| `--descriptor` | string | — | — | Method descriptor (optional; first match if omitted) |
| `--max-depth` | int | — | `3` | Max recursion depth (default 3) |
| `--include-external` | flag | — | `False` | Also recurse into external/API methods (may explode; use small depth) |
| `--max-nodes` | int | — | `5000` | Node cap to prevent explosion (default 5000) |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Reachability analysis: methods reachable from a given method (recursive xref_to expansion)

## 对应 API

`skills.analysis_method_reachable(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [analysis 命令组](./)
- [命令索引](../)
