# analysis method-block-instructions

> Disassemble method instructions organized by basic block (CFG node-level view)

## 用法

```bash
androguard-skills analysis method-block-instructions
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `<class_name>` | string | ✅ | — |  |
| `<method_name>` | string | ✅ | — |  |
| `--descriptor` | string | — | — | Method descriptor (optional; first match if omitted) |
| `--ins-limit` | int | — | — | Max instructions per block (0 = all) |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Disassemble method instructions organized by basic block (CFG node-level view)

## 对应 API

`skills.analysis_method_block_instructions(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [analysis 命令组](./)
- [命令索引](../)
