# load

> 🔝 加载 APK 到（daemon 的）缓存，或单次模式下的当前进程。

## 用法

```bash
androguard-skills load <APK_PATH>
```

## 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `apk_path` | `click.Path(exists=True)` | ✅ | APK 文件路径 |

## 说明

- **daemon 模式**：`load` 把 APK 解析结果缓存到 daemon 进程，后续所有命令复用，无需重复解析。这是推荐用法。
- **单次模式**：`load` 只在当次进程内有效，下一条命令是新进程，不会复用——要跨命令复用必须用 daemon。
- 解析失败时抛异常（而非返回 dict），CLI 统一捕获为 `{"error": ...}`，且会 gc 旧 Analysis 对象，不会留下腐化状态。

## 示例

```bash
# daemon 模式（推荐）
androguard-skills daemon start
androguard-skills load /path/to/app.apk
androguard-skills apk info          # 复用缓存
androguard-skills daemon stop
```

```bash
# 单次模式（不跨进程复用）
androguard-skills load /path/to/app.apk   # 仅当次有效
```

## 对应 API

`skills.load_apk(apk_path)` — 见 [Python API](../guide/python-api)。

## 输出示例

```json
{
  "loaded": true,
  "apk_path": "/path/to/app.apk",
  "package": "com.example.app",
  "version": "1.0.0"
}
```

## 相关命令

- [unload](./unload) — 卸载并释放内存
- [load-dex](./load-dex) — 加载独立 DEX
- [daemon start](./daemon/start) — 启动 daemon
