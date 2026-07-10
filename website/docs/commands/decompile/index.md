# 🧠 decompile · 反编译

> 把 DEX 字节码反编译为可读形式：纯文本 Java 源码、结构化 AST、词法 token 流。共 6 个命令。

共 **6** 个命令。

## 命令列表

| 命令 | 说明 |
|------|------|
| [`class`](./class) | Decompile a specific class |
| [`class-ast`](./class-ast) | Decompile a class and return class-level AST (all methods + fields) |
| [`class-tokens`](./class-tokens) | Decompile a class and return class-level token stream (lexical tokens) |
| [`method`](./method) | Decompile a specific method |
| [`method-ast`](./method-ast) | Decompile a method and return structured AST (triple/flags/ret/params/body) |
| [`method-tokens`](./method-tokens) | Decompile a method and return token stream (type, value) pairs |

## 用法示例

```bash
androguard-skills decompile --help    # 查看本组所有命令
androguard-skills decompile <子命令> --help
```

- [命令索引](../)
