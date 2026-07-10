# ⚙️ daemon · 进程管理

> 管理 daemon 常驻进程：启动、停止、查看状态。daemon 缓存已加载的 APK/DEX/Analysis，跨命令复用，避免重复解析。

共 **3** 个命令。

## 命令列表

| 命令 | 说明 |
|------|------|
| [`start`](./start) | Start the daemon process |
| [`status`](./status) | Check daemon status |
| [`stop`](./stop) | Stop the daemon process |

## 用法示例

```bash
androguard-skills daemon --help    # 查看本组所有命令
androguard-skills daemon <子命令> --help
```

- [命令索引](../)
