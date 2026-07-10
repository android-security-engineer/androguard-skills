# decompile class-ast

> Decompile a class and return class-level AST (all methods + fields)

## 用法

```bash
androguard-skills decompile class-ast
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `<class_name>` | string | ✅ | — |  |
| `--fields-limit` | int | — | — | Max number of field ASTs to return (default: all) |
| `--methods-limit` | int | — | — | Max number of method ASTs to return (default: all) |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Decompile a class and return class-level AST (all methods + fields)

## 对应 API

`skills.decompile_class_ast(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [decompile 命令组](./)
- [命令索引](../)
