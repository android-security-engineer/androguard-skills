# 类名与描述符

> 🏷️ Android/Dalvik 世界里有三种常见的"类名"写法，Skills 命令在不同上下文使用不同写法。这一页讲清三者的区别与转换。

## 三种写法

| 名称 | 示例 | 用途 |
|------|------|------|
| **Dalvik 描述符** | `Lcom/example/MainActivity;` | DEX 字节码、Analysis、大多数 Skills 命令的 `--class` / `class_name` 参数 |
| **Java 全限定名** | `com.example.MainActivity` | 人类阅读、反编译输出、日志 |
| **Python 模块路径** | `com.example.MainActivity` | 内部映射（与 Java 名相似） |

## Dalvik 描述符规则

- 以 `L` 开头，`;` 结尾。
- 内部用 `/` 分隔包。
- 内部类用 `$` 连接：`Lcom/example/Foo$Bar;`

```
Lcom/example/MainActivity;
Landroid/app/Activity;
Lcom/example/Util$Helper;
```

::: warning 必须带分号
Skills 命令的 `class_name` 参数要求**完整 Dalvik 描述符**，包括末尾的 `;`。漏掉分号会查不到类。
:::

## 在命令中的使用

大多数 `analysis` / `dex` / `decompile` / `visualize` 命令的类参数用 Dalvik 描述符：

```bash
# 正确：带 L 和 ;
androguard-skills analysis method-callers Lcom/example/Crypto; encrypt

# 错误：漏分号
androguard-skills analysis method-callers Lcom/example/Crypto encrypt   # ❌
```

## 方法描述符

方法描述符（descriptor）描述参数与返回值类型，格式 `(参数类型列表)返回类型`：

```
()V                        # 无参，返回 void
(Ljava/lang/String;)V      # 接收一个 String，返回 void
(II)I                      # 接收两个 int，返回 int
([B)Ljava/lang/String;     # 接收 byte[]，返回 String
```

常见类型缩写：

| 描述符 | Java 类型 |
|--------|----------|
| `V` | void |
| `Z` | boolean |
| `B` | byte |
| `S` | short |
| `C` | char |
| `I` | int |
| `J` | long |
| `F` | float |
| `D` | double |
| `L...;` | 对象 |
| `[` 前缀 | 数组 |

## 精确查方法需要 descriptor

一个类里可能有多个同名方法（重载），此时需要 descriptor 精确定位：

```bash
# 不带 descriptor：返回所有同名方法
androguard-skills analysis method-summary Lcom/Foo; bar

# 带 descriptor：精确单个（部分命令支持 --descriptor）
androguard-skills analysis method-detail Lcom/Foo; bar --descriptor "(I)V"
```

## 格式转换：`util format`

不想手动转换？用 `util format` 命令：

```bash
# Dalvik → Java
androguard-skills util format Lcom/example/MainActivity; --to java
# → {"value": "com.example.MainActivity"}

# Java → Dalvik
androguard-skills util format com.example.MainActivity --to dalvik
# → {"value": "Lcom/example/MainActivity;"}

# → Python
androguard-skills util format Lcom/example/MainActivity; --to python
```

详见 [util format 命令](../commands/util/format)。

## 字段描述符

字段也有描述符（类型）：

```
Ljava/lang/String;   # String 字段
I                    # int 字段
[B                   # byte[] 字段
```

精确查字段用 `dex encoded-field-descriptor`：

```bash
androguard-skills dex encoded-field-descriptor Lcom/Foo; data Ljava/lang/String;
```

## 小结

- 命令参数里的类名 → 用 **Dalvik 描述符**（`L...;`，带分号）。
- 重载方法 → 用 **method descriptor** 精确定位。
- 不确定格式 → `util format` 互转。

---

👈 [输出格式规范](./output-format) · [资源 ID 体系 →](./resource-ids) 👉
