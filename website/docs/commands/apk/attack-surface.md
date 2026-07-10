# apk attack-surface

> Attack surface: cross-reference exported components with forward-reachable dangerous sinks

## 用法

```bash
androguard-skills apk attack-surface
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--max-depth` | int | — | `4` | Forward reachability depth from component methods (default 4) |
| `--per-sink-limit` | int | — | `10` | Max call samples per sink category per component (default 10) |
| `--max-nodes` | int | — | `2000` | BFS node cap per component (default 2000) |
| `--include-safe` | flag | — | `False` | Also analyze non-exported/protected components (default: exposed only) |

::: tip 公共参数 `--apk-path`

支持 `--apk-path <路径>` 或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 可省略。

:::

## 说明

Attack surface: cross-reference exported components with forward-reachable dangerous sinks

## 对应 API

`skills.apk_attack_surface(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [apk 命令组](./)
- [命令索引](../)
