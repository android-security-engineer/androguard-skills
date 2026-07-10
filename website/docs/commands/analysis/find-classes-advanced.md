# analysis find-classes-advanced

> Multi-dimensional regex class search: name regex + exclude-external (native find_classes)

## 用法

```bash
androguard-skills analysis find-classes-advanced
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--name` | string | — | `.*` | Regex for class name |
| `--no-external` | flag | — | `False` | Exclude external (Android/third-party) classes |
| `--limit` | int | — | `500` | Max results (default 500) |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Multi-dimensional regex class search: name regex + exclude-external (native find_classes)

## 对应 API

`skills.analysis_find_classes_advanced(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [analysis 命令组](./)
- [命令索引](../)
