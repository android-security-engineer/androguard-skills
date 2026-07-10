# analysis method-detail

> Get comprehensive method info (full_name/access/length/xref stats/bb count)

## 用法

```bash
androguard-skills analysis method-detail
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `<class_name>` | string | ✅ | — |  |
| `<method_name>` | string | ✅ | — |  |
| `<descriptor>` | string | ✅ | — |  |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Get comprehensive method info (full_name/access/length/xref stats/bb count)

## 对应 API

`skills.analysis_method_detail(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [analysis 命令组](./)
- [命令索引](../)
