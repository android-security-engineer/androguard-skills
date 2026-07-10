# analysis call-graph

> Get the full call graph (nodes + edges)

## 用法

```bash
androguard-skills analysis call-graph
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--limit` | int | — | — | Max number of edges to return |
| `--external` | flag | — | `False` | Include external method nodes/edges |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Get the full call graph (nodes + edges)

## 对应 API

`skills.analysis_call_graph(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [analysis 命令组](./)
- [命令索引](../)
