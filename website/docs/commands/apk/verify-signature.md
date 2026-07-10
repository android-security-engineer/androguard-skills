# apk verify-signature

> Cryptographically verify APK signatures (signer info vs .SF file)

## 用法

```bash
androguard-skills apk verify-signature
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--filename` | string | — | — | Signature file name (e.g. META-INF/CERT.RSA). If omitted, verify all signature files |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Cryptographically verify APK signatures (signer info vs .SF file)

## 对应 API

`skills.apk_verify_signature(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [apk 命令组](./)
- [命令索引](../)
