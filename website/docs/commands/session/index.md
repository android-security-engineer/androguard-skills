# 🗂️ session · 会话

> 多 APK/DEX 关联分析：Session 创建、添加文件、跨 DEX 查类归属与字符串。共 8 个命令。

共 **8** 个命令。

## 命令列表

| 命令 | 说明 |
|------|------|
| [`add-apk`](./add-apk) | Add an APK to the current Session (multi-file association analysis) |
| [`add-dex`](./add-dex) | Add a standalone DEX to the current Session |
| [`analyze-apk`](./analyze-apk) | Analyze an APK via a Session (independent loading path) |
| [`classes`](./classes) | List all classes in the Session (grouped by DEX) |
| [`create`](./create) | Create a new Session (held for subsequent session commands; use daemon mode for cross-command persistence) |
| [`filename-by-class`](./filename-by-class) | Find which file/digest a class belongs to (multi-APK/DEX association) |
| [`info`](./info) | Get current Session overview (APK/DEX counts + string count) |
| [`strings`](./strings) | Get strings analysis across all DEXes in the Session |

## 用法示例

```bash
androguard-skills session --help    # 查看本组所有命令
androguard-skills session <子命令> --help
```

- [命令索引](../)
