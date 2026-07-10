# apk manifest-attr

> Extract a single manifest attribute value (first match)

## 用法

```bash
androguard-skills apk manifest-attr
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--tag` | string | ✅ | — | Manifest tag name |
| `--attribute` | string | ✅ | — | Attribute name |
| `--filter` | string | — | — | (可重复) Attribute filter as key=value (can repeat) |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Extract a single manifest attribute value (first match)

## 对应 API

`skills.apk_manifest_attr(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [apk 命令组](./)
- [命令索引](../)
