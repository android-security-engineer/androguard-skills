# analysis callgraph

> Generate and export call graph

## 用法

```bash
androguard-skills analysis callgraph
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--output` | string | ✅ | — | Output file path |
| `--format` | choice: `gml` / `gexf` / `graphml` / `net` | — | `gml` | Output format (default: gml) |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Generate and export call graph

## 对应 API

`skills.analysis_callgraph(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [analysis 命令组](./)
- [命令索引](../)
