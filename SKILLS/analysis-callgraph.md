# 调用图导出

生成并导出方法的调用关系图。

## 命令

```bash
androguard-skills analysis callgraph -o callgraph.gml -f gml --apk-path test.apk
```

## 支持的输出格式

| 格式 | 说明 | 用途 |
|------|------|------|
| `gml` | GML 格式（默认） | 通用图格式 |
| `gexf` | GEXF 格式 | Gephi 可视化 |
| `graphml` | GraphML 格式 | yEd 可视化 |
| `net` | Pajek 格式 | 网络分析 |

## 输出示例

```json
{
  "output": "callgraph.gml",
  "format": "gml",
  "nodes": 156,
  "edges": 342
}
```

## 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `output` | string | 输出文件路径 |
| `format` | string | 输出格式 |
| `nodes` | int | 图中节点数（方法数） |
| `edges` | int | 图中边数（调用关系数） |

## 使用场景

- 可视化分析：用 Gephi/yEd 打开图文件，直观查看调用关系
- 入口点分析：从四大组件的入口点追踪完整调用链
- 代码复杂度评估：通过节点/边数量评估代码规模
- 架构分析：识别核心模块和依赖关系

## 可视化建议

导出为 GEXF 格式后，可用 Gephi 进行可视化分析：

```bash
androguard-skills analysis callgraph -o callgraph.gexf -f gexf --apk-path test.apk
```

在 Gephi 中：
1. 导入 GEXF 文件
2. 使用 ForceAtlas2 布局
3. 按节点属性（external、entrypoint）着色
4. 过滤显示关键方法
