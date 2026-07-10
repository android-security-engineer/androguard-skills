# 污点路径

> 🔬 `analysis taint-path` —— 在调用图上搜索从**源方法**到**汇方法**的最短前向调用路径。

## 命令

```bash
androguard-skills analysis taint-path \
  --src-class Lcom/app/Login; --src-method getPassword \
  --dst-class Lcom/evil/Net; --dst-method send \
  [--src-descriptor] [--dst-descriptor] [--max-depth 8] [--max-nodes 20000]
```

详见 [analysis taint-path 命令](../commands/analysis/taint-path)。

## 原理

- 在 `Analysis` 的调用图上做 BFS。
- 从源方法出发，沿 xref_to（被调用方）前向展开。
- 找到第一条到达汇方法的路径即返回。

## 局限

::: warning 不是数据流分析
`taint-path` 只追踪**调用关系**，不追踪具体数据是否真的流动。它回答"从 A 能不能调用到 B"，而非"A 的返回值会不会流到 B 的参数"。完整污点分析需配合动态插桩（`pentest`）。
:::

## 典型用法

```bash
# 验证密码字段是否会被发到网络
androguard-skills analysis taint-path \
  --src-class Lcom/app/LoginActivity; --src-method getPassword \
  --dst-class Lcom/app/NetClient; --dst-method post

# 验证用户输入是否到达 SQL 执行点
androguard-skills analysis taint-path \
  --src-class Lcom/app/Form; --src-method getInput \
  --dst-class Lcom/db/Helper; --dst-method execSQL
```

## 相关

- [method-reachable](../commands/analysis/method-reachable) — 单方法前向可达
- [method-callers](../commands/analysis/method-callers) — 反向溯源
- [攻击面分析](./attack-surface)
