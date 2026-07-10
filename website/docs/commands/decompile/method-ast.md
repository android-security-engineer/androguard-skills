# decompile method-ast

> Decompile a method and return structured AST (triple/flags/ret/params/body)

## 用法

```bash
androguard-skills decompile method-ast
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `<class_name>` | string | ✅ | — |  |
| `<method_name>` | string | ✅ | — |  |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Decompile a method and return structured AST (triple/flags/ret/params/body)

## 对应 API

`skills.decompile_method_ast(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [decompile 命令组](./)
- [命令索引](../)
