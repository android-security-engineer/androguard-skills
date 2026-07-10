# 攻击面分析

> 🎯 `apk attack-surface` —— 交叉引用**导出组件**与其处理类**前向可达的危险 sink**，构建入口→sink 地图。

## 命令

```bash
androguard-skills apk attack-surface [--max-depth 4] [--per-sink-limit 10] [--max-nodes 2000] [--include-safe]
```

详见 [apk attack-surface 命令](../commands/apk/attack-surface)。

## 原理

1. 枚举所有 `exported=true` 的组件（Activity/Service/Receiver/Provider）——外部入口。
2. 对每个组件的处理类，做前向可达性分析（递归 xref_to）。
3. 标记可达路径上出现的危险 sink（加密、网络、文件、反射、native 等）。
4. 输出"入口组件 → 危险 sink"的可达地图。

## 与 `method-reachable` 的区别

`analysis method-reachable` 是单方法可达性；`apk attack-surface` 是**批量**对所有导出组件做可达性，并自动识别 sink。

## 相关

- [组件安全详情](../commands/apk/component-details)
- [深链接枚举](../commands/apk/deeplinks)
- [污点路径](./taint-path)
