# analysis method-api-info

> Get method API/permission annotation (is_android_api/domain_flag/restriction_flag/apilist)

## 用法

```bash
androguard-skills analysis method-api-info
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

Get method API/permission annotation (is_android_api/domain_flag/restriction_flag/apilist)

## 对应 API

`skills.analysis_method_api_info(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [analysis 命令组](./)
- [命令索引](../)
