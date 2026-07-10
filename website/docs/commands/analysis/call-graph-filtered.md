# analysis call-graph-filtered

> Get a filtered sub call-graph (by class/method/descriptor/accessflags)

## 用法

```bash
androguard-skills analysis call-graph-filtered
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--classname` | string | — | — | Class name regex filter (e.g. Lcom/example/Foo;) |
| `--methodname` | string | — | — | Method name regex filter |
| `--descriptor` | string | — | — | Descriptor regex filter |
| `--accessflags` | string | — | — | Access flags regex filter (e.g. public.*static) |
| `--no-isolated` | flag | — | `False` | Remove isolated nodes (no edges) |
| `--external` | flag | — | `False` | Include external method nodes/edges |
| `--limit` | int | — | — | Max number of edges to return |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Get a filtered sub call-graph (by class/method/descriptor/accessflags)

## 对应 API

`skills.analysis_call_graph_filtered(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [analysis 命令组](./)
- [命令索引](../)
