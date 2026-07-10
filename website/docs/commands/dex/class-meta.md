# dex class-meta

> Get ClassDefItem low-level meta (annotations/source_file/interfaces/superclass/offsets)

## 用法

```bash
androguard-skills dex class-meta
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `<class_name>` | string | ✅ | — |  |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Get ClassDefItem low-level meta (annotations/source_file/interfaces/superclass/offsets)

## 对应 API

`skills.dex_class_meta(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [dex 命令组](./)
- [命令索引](../)
