# analysis taint-path

> Find a forward call path from a source method to a sink method (source-&gt;sink chain)

## 用法

```bash
androguard-skills analysis taint-path
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `<src_class>` | string | ✅ | — |  |
| `<src_method>` | string | ✅ | — |  |
| `<dst_class>` | string | ✅ | — |  |
| `<dst_method>` | string | ✅ | — |  |
| `--src-descriptor` | string | — | — | Source method descriptor (optional) |
| `--dst-descriptor` | string | — | — | Sink method descriptor (optional) |
| `--max-depth` | int | — | `8` | Max search depth (default 8) |
| `--max-nodes` | int | — | `20000` | Max nodes visited (default 20000) |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Find a forward call path from a source method to a sink method (source-&gt;sink chain)

## 对应 API

`skills.analysis_taint_path(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [analysis 命令组](./)
- [命令索引](../)
