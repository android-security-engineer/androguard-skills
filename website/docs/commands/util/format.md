# util format

> Convert class name/descriptor between Dalvik/Java/Python formats

## 用法

```bash
androguard-skills util format
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `<value>` | string | ✅ | — |  |
| `--to` | choice: `java` / `dalvik` / `python` | — | `java` | Target format (java/dalvik/python, default java) |

## 说明

Convert class name/descriptor between Dalvik/Java/Python formats

## 对应 API

`skills.util_format(...)` — 详见 [Python API](../../guide/python-api)。

## 相关

- [util 命令组](./)
- [命令索引](../)
