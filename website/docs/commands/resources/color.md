# resources color

> Get color resources for a package

## 用法

```bash
androguard-skills resources color
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `<package_name>` | string | ✅ | — |  |
| `--locale` | string | — | — | Locale (e.g. zh, en). Default is the default locale |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Get color resources for a package

## 对应 API

`skills.resource_color(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [resources 命令组](./)
- [命令索引](../)
