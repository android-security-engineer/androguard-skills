# analysis insecure-storage

> Audit insecure data storage (external storage/world-readable modes/plaintext prefs+db, OWASP M9)

## 用法

```bash
androguard-skills analysis insecure-storage
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--limit` | int | — | `100` | Max samples per category (default 100) |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Audit insecure data storage (external storage/world-readable modes/plaintext prefs+db, OWASP M9)

## 对应 API

`skills.analysis_insecure_storage(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [analysis 命令组](./)
- [命令索引](../)
