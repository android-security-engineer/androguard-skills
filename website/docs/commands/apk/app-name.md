# apk app-name

> Get the app display name (resolved android:label)

## 用法

```bash
androguard-skills apk app-name
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--locale` | string | — | — | Locale code (e.g. zh, en); default if omitted |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Get the app display name (resolved android:label)

## 对应 API

`skills.apk_app_name(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [apk 命令组](./)
- [命令索引](../)
