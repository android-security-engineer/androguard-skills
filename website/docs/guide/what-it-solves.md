# 它能解决什么问题

> 这一页解释 Androguard Skills 的**设计动机**：原生 AndroGuard 优秀但难自动化，Skills 把它改造成"天然可被程序消费"的形态。

## 痛点一：逆向工具的输出是给人看的，不是给程序看的

传统的 Android 逆向工具（包括原生 AndroGuard 的 CLI）大量使用**面向人类阅读**的输出：彩色表格、分页器、混合的纯文本。当你想：

- 在 CI 里对一个 APK 自动出安全报告
- 让一个 AI Agent 分析 APK 的行为
- 批量处理 1000 个 APK 并把结果入库

……你就得**正则解析控制台文本**。这是脆弱的、易碎的、随版本崩溃的。

### Skills 的解法

> ✅ **每一条命令的输出都是合法 JSON。**

```bash
# 不再需要这样（脆弱）：
androguard packages test.apk | grep -oP 'Package: \K\S+' | ...

# 而是这样（稳定）：
androguard-skills apk permissions --apk-path test.apk | jq '.permissions[]'
```

成功返回数据对象，失败返回 `{"error": "..."}`——下游永远拿到可解析的结构。

## 痛点二：重复解析代价高昂

解析一个大 APK（含多个 DEX、上万个类、密集的交叉引用）可能耗时数秒到数十秒。如果你要依次执行 20 个分析命令，原生方式会**重复解析 20 次**。

### Skills 的解法

> ✅ **Daemon 常驻模式**：一次 `load`，后续命令复用已缓存的 APK/DEX/Analysis 对象。

```bash
androguard-skills daemon start   # 启动常驻进程
androguard-skills load big.apk   # 解析一次（慢）
androguard-skills apk info       # 复用缓存（快）
androguard-skills apk permissions
androguard-skills analysis call-graph
# ...任意多次查询，都是毫秒级
androguard-skills daemon stop
```

CLI 自动探测 daemon 是否在线：在线走 JSON-RPC，离线自动降级为单次执行——**同一套命令，两种模式无缝切换**。

## 痛点三：能力分散，没有"能力地图"

AndroGuard 的 Python API 非常强大，但方法散落在 `APK`、`DexFile`、`Analysis`、`DalvikVMFormat` 等多个对象上，参数风格不一，新人难以知道"到底能查什么"。

### Skills 的解法

> ✅ **219 个命令 = 219 个明确命名的能力点**，按 10 个领域分组。

你不需要读 API 源码——`apk permissions` 就是查权限，`analysis method-reachable` 就是方法可达性分析，`dex proto-ids` 就是原型表。命令名即文档索引。

```
androguard-skills apk <子命令>        # APK 维度
androguard-skills dex <子命令>        # DEX 维度
androguard-skills analysis <子命令>   # 静态分析维度
androguard-skills resources <子命令>  # 资源维度
...
```

## 痛点四：安全审计需要拼装

做一次完整的 APK 安全评估，原生方式要自己组合：查导出组件 → 查组件权限 → 查危险 API 调用 → 查 SSL 配置 → 查硬编码密钥……每一步都是手工活。

### Skills 的解法

> ✅ **19 域专项审计命令 + 一键聚合报告**。

```bash
# 单域审计（精修某一类问题）
androguard-skills analysis webview-security
androguard-skills analysis sql-injection
androguard-skills analysis hardcoded-secrets

# 一键全量报告（聚合全部 + 综合风险评分）
androguard-skills apk security-report
```

`apk security-report` 一次调用聚合 19 个安全域，输出顶层风险总览与评分，直接可作为审计闭环产物。

## 痛点五：调用关系难追溯

"这个危险方法是谁调用的？从入口能不能到达？"——原生 AndroGuard 提供了 xref，但要自己写 BFS/DFS 遍历调用图。

### Skills 的解法

> ✅ **内置可达性 / 反向可达 / 污点路径**命令。

```bash
# 从某方法出发，递归展开 3 层，看能到达哪些方法
androguard-skills analysis method-reachable Lcom/evil/Http; send --max-depth 3

# 反向：谁能调用到这个危险 sink？（溯源入口）
androguard-skills analysis method-callers Lcom/evil/Crypto; weakEncrypt

# 源→汇：在调用图上找一条从源到汇的最短路径（污点分析）
androguard-skills analysis taint-path \
  --src-class Lcom/app/Login; --src-method getPassword \
  --dst-class Lcom/evil/Net; --dst-method send
```

## 总结：它如何解决问题

| 痛点 | Skills 的解法 |
|------|--------------|
| 输出不可程序化 | 全 JSON 输出，统一错误结构 |
| 重复解析慢 | Daemon 常驻 + JSON-RPC 复用缓存 |
| 能力无地图 | 219 个命名命令 × 10 个领域分组 |
| 安全审计要拼装 | 19 域专项审计 + 一键 `security-report` |
| 调用关系难追溯 | `method-reachable` / `method-callers` / `taint-path` |

---

👈 [项目简介](./introduction) · [安装 →](./installation) 👉
