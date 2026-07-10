# apk icon

> Get app icon information

## 用法

```bash
androguard-skills apk icon
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--max-dpi` | int | — | `65536` | Max DPI for icon selection (default: 65536) |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Get app icon information

## 对应 API

`skills.apk_icon(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [apk 命令组](./)
- [命令索引](../)
