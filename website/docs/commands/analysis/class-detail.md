# analysis class-detail

> Get comprehensive class info (methods/inheritance/xref stats/vm_class type)

## 用法

```bash
androguard-skills analysis class-detail
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `<class_name>` | string | ✅ | — |  |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Get comprehensive class info (methods/inheritance/xref stats/vm_class type)

## 对应 API

`skills.analysis_class_detail(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [analysis 命令组](./)
- [命令索引](../)
