# decompile class

> Decompile a specific class

## 用法

```bash
androguard-skills decompile class
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `<class_name>` | string | ✅ | — |  |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Decompile a specific class

## 对应 API

`skills.decompile_class(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [decompile 命令组](./)
- [命令索引](../)
