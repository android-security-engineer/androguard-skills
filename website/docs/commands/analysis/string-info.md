# analysis string-info

> Get single string analysis (orig_value/current_value/is_overwritten + xrefs)

## 用法

```bash
androguard-skills analysis string-info
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `<value>` | string | ✅ | — |  |
| `--xref-limit` | int | — | — | Max number of xref_from refs to return |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Get single string analysis (orig_value/current_value/is_overwritten + xrefs)

## 对应 API

`skills.analysis_string_info(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [analysis 命令组](./)
- [命令索引](../)
