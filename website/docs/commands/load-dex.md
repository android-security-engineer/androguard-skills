# load-dex

> 🔝 加载一个独立的 DEX 文件（不通过 APK），用于直接分析单独的 `.dex`。

## 用法

```bash
androguard-skills load-dex <DEX_PATH>
```

## 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `dex_path` | `click.Path(exists=True)` | ✅ | DEX 文件路径 |

## 说明

- 适用于没有 APK 容器、只有裸 `.dex` 的场景（如从内存 dump 出来的 DEX、单独编译的 DEX）。
- 加载后 `dex` 组命令可直接用；`apk` 组命令不可用（因为没有 APK 容器）。
- daemon 模式下缓存到 daemon 进程，跨命令复用。
- `is_loaded` 会识别 DEX 模式，后续 dex 查询正常工作。

## 示例

```bash
androguard-skills daemon start
androguard-skills load-dex /path/to/classes.dex
androguard-skills dex classes
androguard-skills dex header
androguard-skills daemon stop
```

## 对应 API

`skills.load_dex(dex_path)`。

## 相关命令

- [load](./load) — 加载 APK
- [unload](./unload) — 卸载
- [dex 命令组](./dex/) — DEX 查询
