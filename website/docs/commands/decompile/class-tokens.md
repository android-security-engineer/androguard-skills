# decompile class-tokens

> Decompile a class and return class-level token stream (lexical tokens)

## 用法

```bash
androguard-skills decompile class-tokens
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `<class_name>` | string | ✅ | — |  |
| `--limit` | int | — | — | Max number of top-level tokens to return (default: all) |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Decompile a class and return class-level token stream (lexical tokens)

## 对应 API

`skills.decompile_class_tokens(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [decompile 命令组](./)
- [命令索引](../)
