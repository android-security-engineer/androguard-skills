# 🔧 util · 工具

> 工具命令：文件类型检测、AOSP 权限数据查询、类名/描述符格式转换。不依赖已加载 APK。共 5 个命令。

共 **5** 个命令。

## 命令列表

| 命令 | 说明 |
|------|------|
| [`api-levels`](./api-levels) | List locally available API levels for permission data |
| [`detect`](./detect) | Detect the Android file type (APK/DEX/ODEX/ELF) of a file |
| [`format`](./format) | Convert class name/descriptor between Dalvik/Java/Python formats |
| [`permission-mappings`](./permission-mappings) | Load method-signature -&gt; permission mappings for a given API level |
| [`permissions`](./permissions) | Load AOSP permission definitions for a given API level |

## 用法示例

```bash
androguard-skills util --help    # 查看本组所有命令
androguard-skills util <子命令> --help
```

- [命令索引](../)
