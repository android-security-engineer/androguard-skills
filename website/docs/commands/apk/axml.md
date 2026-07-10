# apk axml

> Decode any binary AXML file in APK to readable XML (layouts/drawables/config)

## 用法

```bash
androguard-skills apk axml
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `<filename>` | string | ✅ | — |  |
| `--no-pretty` | flag | — | `False` | Disable pretty-printing (compact XML) |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Decode any binary AXML file in APK to readable XML (layouts/drawables/config)

## 对应 API

`skills.apk_axml(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [apk 命令组](./)
- [命令索引](../)
