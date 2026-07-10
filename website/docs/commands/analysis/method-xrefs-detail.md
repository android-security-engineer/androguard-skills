# analysis method-xrefs-detail

> Get full method-level xref lists (from/to/read/write/new_instance/const_class)

## 用法

```bash
androguard-skills analysis method-xrefs-detail
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

Get full method-level xref lists (from/to/read/write/new_instance/const_class)

## 对应 API

`skills.analysis_method_xrefs_detail(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [analysis 命令组](./)
- [命令索引](../)
