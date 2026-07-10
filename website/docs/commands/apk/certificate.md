# apk certificate

> Get APK signing certificate details

## 用法

```bash
androguard-skills apk certificate
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--filename` | string | — | — | Signature file name (e.g. META-INF/CERT.RSA). If omitted, returns all certificates |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Get APK signing certificate details

## 对应 API

`skills.apk_certificate(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [apk 命令组](./)
- [命令索引](../)
