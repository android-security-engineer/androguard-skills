# apk native-libraries

> List native libraries (lib/&lt;abi&gt;/*.so) grouped by ABI

## 用法

```bash
androguard-skills apk native-libraries
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--include-data` | flag | — | `False` | Include base64-encoded .so data (large output) |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

List native libraries (lib/&lt;abi&gt;/*.so) grouped by ABI

## 对应 API

`skills.apk_native_libraries(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [apk 命令组](./)
- [命令索引](../)
