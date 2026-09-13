# 方法控制流图可视化

> 将方法 CFG 导出为 DOT、PNG/JPG 图片、JSON 格式

## 命令

### `visualize method-dot <class_name> <method_name>`

导出方法的控制流图（CFG）为 DOT 格式（Graphviz 文本格式）。

```bash
androguard-skills visualize method-dot "Lcom/example/MainActivity;" "onCreate" --apk-path test.apk
```

输出示例：

```json
{
  "class": "Lcom/example/MainActivity;",
  "method": "onCreate",
  "descriptor": "(Landroid/os/Bundle;)V",
  "dot": {
    "name": "...",
    "nodes": "... (DOT 格式节点定义)",
    "edges": "... (DOT 格式边定义)"
  }
}
```

> DOT 输出可用于 Graphviz 渲染：`dot -Tpng input.dot -o output.png`

### `visualize method-image <class_name> <method_name> -o <output>`

导出方法的控制流图为图片（PNG 或 JPG）。

```bash
androguard-skills visualize method-image "Lcom/example/MainActivity;" "onCreate" -o /tmp/onCreate_cfg.png --apk-path test.apk
# JPG 格式
androguard-skills visualize method-image "Lcom/example/MainActivity;" "onCreate" -o /tmp/onCreate_cfg.jpg -f jpg --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `-o / --output` | 输出图片文件路径（必选） |
| `-f / --format` | 图片格式：`png` 或 `jpg`（默认 png） |

> 需要系统安装 Graphviz（`apt install graphviz` 或 `brew install graphviz`）。

输出示例（成功时）：

```json
{
  "class": "Lcom/example/MainActivity;",
  "method": "onCreate",
  "descriptor": "(Landroid/os/Bundle;)V",
  "output": "/tmp/onCreate_cfg.png",
  "format": "png"
}
```

### `visualize method-json <class_name> <method_name>`

导出方法的控制流图为 JSON 格式。

```bash
androguard-skills visualize method-json "Lcom/example/MainActivity;" "onCreate" --apk-path test.apk
```

输出示例：

```json
{
  "class": "Lcom/example/MainActivity;",
  "method": "onCreate",
  "descriptor": "(Landroid/os/Bundle;)V",
  "cfg": { ... }
}
```

## 独立 DEX 文件加载

### `load-dex <dex_path>`

加载独立的 DEX 文件（不依赖 APK），可用于分析从内存 dump 出来的 DEX。

```bash
androguard-skills load-dex /path/to/classes.dex
```

> 加载 DEX 后，可以使用 `dex`、`analysis`、`decompile`、`visualize` 等命令分析，
> 但不能使用 `apk` 和 `resources` 命令（无 APK 上下文）。

输出示例：

```json
{
  "status": "loaded",
  "path": "/path/to/classes.dex",
  "dex_count": 1,
  "classes": 294
}
```

## 安全分析用途

- **CFG 分析**：可视化加密/认证方法的控制流，发现异常分支
- **条件判断**：CFG 中的条件节点揭示安全检查逻辑
- **图片报告**：导出 PNG 可直接嵌入安全审计报告
- **程序化分析**：JSON/DOT 格式适合自动化工具处理
- **内存 DEX**：通过 `load-dex` 分析 Frida dump 出来的 DEX
