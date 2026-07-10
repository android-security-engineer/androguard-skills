# analysis security-hotspots

> Scan all methods for security-sensitive calls (reflection/crypto/exec/native/etc.)

## 用法

```bash
androguard-skills analysis security-hotspots
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--limit` | int | — | `50` | Max samples per hotspot category (default 50) |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Scan all methods for security-sensitive calls (reflection/crypto/exec/native/etc.)

## 对应 API

`skills.analysis_security_hotspots(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [analysis 命令组](./)
- [命令索引](../)
