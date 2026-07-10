# dex method-ids

> List all method_ids constant-pool entries (includes external refs, no code)

## 用法

```bash
androguard-skills dex method-ids
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--limit` | int | — | — | Max results per DEX |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

List all method_ids constant-pool entries (includes external refs, no code)

## 对应 API

`skills.dex_method_ids(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [dex 命令组](./)
- [命令索引](../)
