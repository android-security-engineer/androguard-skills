# dex type-ids

> List DEX type constant pool (type_ids: descriptor_idx -&gt; type descriptor)

## 用法

```bash
androguard-skills dex type-ids
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--limit` | int | — | — | Max number of types to return |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

List DEX type constant pool (type_ids: descriptor_idx -&gt; type descriptor)

## 对应 API

`skills.dex_type_ids(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [dex 命令组](./)
- [命令索引](../)
