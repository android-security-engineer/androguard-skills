# apk certificates-scheme

> Get certificates by signing scheme (v1/v2/v3/v31)

## 用法

```bash
androguard-skills apk certificates-scheme
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--scheme` | choice: `v1` / `v2` / `v3` / `v31` | — | `v3` | Signing scheme |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Get certificates by signing scheme (v1/v2/v3/v31)

## 对应 API

`skills.apk_certificates_scheme(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [apk 命令组](./)
- [命令索引](../)
