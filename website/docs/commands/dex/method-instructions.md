# dex method-instructions

> Disassemble all Dalvik instructions of a method (instruction stream)

## 用法

```bash
androguard-skills dex method-instructions
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `<class_name>` | string | ✅ | — |  |
| `<method_name>` | string | ✅ | — |  |
| `--limit` | int | — | — | Max number of instructions to return |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Disassemble all Dalvik instructions of a method (instruction stream)

## 对应 API

`skills.dex_method_instructions(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [dex 命令组](./)
- [命令索引](../)
