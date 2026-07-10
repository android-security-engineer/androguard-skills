# analysis dynamic-code

> Audit dynamic code loading (DexClassLoader/native libs/reflection, unpacking/malicious payload)

## 用法

```bash
androguard-skills analysis dynamic-code
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--limit` | int | — | `100` | Max samples per category (default 100) |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Audit dynamic code loading (DexClassLoader/native libs/reflection, unpacking/malicious payload)

## 相关

- [analysis 命令组](./)
- [命令索引](../)
