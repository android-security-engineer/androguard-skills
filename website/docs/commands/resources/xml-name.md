# resources xml-name

> Resolve a resource ID to its XML reference name (@pkg:type/name)

## 用法

```bash
androguard-skills resources xml-name
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `<resource_id>` | string | ✅ | — |  |
| `--package` | string | — | — | Resource package (optional) |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Resolve a resource ID to its XML reference name (@pkg:type/name)

## 对应 API

`skills.resource_xml_name(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [resources 命令组](./)
- [命令索引](../)
