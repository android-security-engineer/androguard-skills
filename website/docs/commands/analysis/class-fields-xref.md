# analysis class-fields-xref

> List all fields of a class with full read/write xref sources (which methods)

## 用法

```bash
androguard-skills analysis class-fields-xref
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `<class_name>` | string | ✅ | — |  |
| `--xref-limit` | int | — | `20` | Max read/write refs to expand per field (default 20) |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

List all fields of a class with full read/write xref sources (which methods)

## 对应 API

`skills.analysis_class_fields_xref(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [analysis 命令组](./)
- [命令索引](../)
