# analysis method-basic-blocks

> Get basic blocks (CFG nodes) of a method

## 用法

```bash
androguard-skills analysis method-basic-blocks
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

Get basic blocks (CFG nodes) of a method

## 对应 API

`skills.analysis_method_basic_blocks(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [analysis 命令组](./)
- [命令索引](../)
