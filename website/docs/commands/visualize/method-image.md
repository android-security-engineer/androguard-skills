# visualize method-image

> Export method CFG as image (PNG/JPG)

## 用法

```bash
androguard-skills visualize method-image
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `<class_name>` | string | ✅ | — |  |
| `<method_name>` | string | ✅ | — |  |
| `--output` | string | ✅ | — | Output image file path |
| `--format` | choice: `png` / `jpg` | — | `png` | Image format (default: png) |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Export method CFG as image (PNG/JPG)

## 对应 API

`skills.visualize_method_image(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [visualize 命令组](./)
- [命令索引](../)
