# analysis method-callers

> Reverse reachability: callers that can reach a given method (recursive xref_from expansion)

## 用法

```bash
androguard-skills analysis method-callers
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `<class_name>` | string | ✅ | — |  |
| `<method_name>` | string | ✅ | — |  |
| `--descriptor` | string | — | — | Method descriptor (optional; first match if omitted) |
| `--max-depth` | int | — | `3` | Max reverse recursion depth (default 3) |
| `--include-external` | flag | — | `False` | Also recurse into external/API methods (rarely useful upstream) |
| `--max-nodes` | int | — | `5000` | Node cap to prevent explosion (default 5000) |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Reverse reachability: callers that can reach a given method (recursive xref_from expansion)

## 对应 API

`skills.analysis_method_callers(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [analysis 命令组](./)
- [命令索引](../)
