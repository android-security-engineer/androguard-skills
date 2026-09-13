# 分析层类与方法查找

> 类存在性检查、精确方法分析（含完整 xref）、全量字符串分析、EncodedMethod 元数据

## 命令

### `analysis class-exists`

检查指定类是否存在于分析中（快速布尔判断）。

```bash
androguard-skills analysis class-exists "Lcom/example/MainActivity;" --apk-path test.apk
```

输出示例：

```json
{
  "class": "Lcom/example/MainActivity;",
  "exists": true
}
```

> 比遍历所有类更快，适合批量验证类是否存在。

### `analysis method-analysis`

按 class+method+descriptor 精确获取方法分析（含完整 xref 信息）。

```bash
androguard-skills analysis method-analysis "Lcom/example/MainActivity;" "onCreate" "(Landroid/os/Bundle;)V" --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `class_name` | 类名（格式如 Lcom/example/MyClass;） |
| `method_name` | 方法名 |
| `descriptor` | 方法描述符（如 `(Landroid/os/Bundle;)V`） |

> descriptor 格式：`(参数类型列表)返回类型`，如 `()V` = 无参返回 void，`(I[BI)V` = int+byte数组+int 返回 void。

输出示例：

```json
{
  "class": "Lcom/example/MainActivity;",
  "method": "onCreate",
  "descriptor": "(Landroid/os/Bundle;)V",
  "is_external": false,
  "is_android_api": false,
  "xref_from_count": 0,
  "xref_from": [],
  "xref_to_count": 15,
  "xref_to": [
    {"to_class": "Landroid/app/Activity;", "to_method": "onCreate", "to_descriptor": "(Landroid/os/Bundle;)V", "offset": 0}
  ]
}
```

> 与 `analysis method-xrefs` 的区别：此命令需要 descriptor 参数，精确匹配单个方法（处理重载）。

### `analysis strings-analysis`

获取全部字符串分析（含每个字符串的引用位置）。

```bash
# 全量（可能很大）
androguard-skills analysis strings-analysis --apk-path test.apk

# 限制返回数量
androguard-skills analysis strings-analysis --limit 100 --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--limit` | 返回数量限制（可选，全量时输出可能很大） |

输出示例：

```json
{
  "total": 100,
  "all_strings_count": 2575,
  "strings": [
    {
      "value": "https://api.example.com",
      "used_in_count": 3,
      "used_in": [
        {"class": "Lcom/example/ApiClient;", "method": "getBaseUrl", "descriptor": "()Ljava/lang/String;"}
      ]
    }
  ]
}
```

> 与 `analysis find-strings` 的区别：find-strings 需要正则过滤；strings-analysis 返回全量字符串及其引用，适合全量审计。

### `analysis get-method`

按 class+method+descriptor 获取底层 EncodedMethod 元数据（访问标志等）。

```bash
androguard-skills analysis get-method "Lcom/example/MainActivity;" "onCreate" "(Landroid/os/Bundle;)V" --apk-path test.apk
```

输出示例：

```json
{
  "class": "Lcom/example/MainActivity;",
  "method": "onCreate",
  "descriptor": "(Landroid/os/Bundle;)V",
  "access_flags": "protected"
}
```

> 与 `method-analysis` 的区别：此命令返回 EncodedMethod 的元数据（访问标志），不含 xref 信息，更轻量。

## 安全分析用途

- **类存在性**：快速判断混淆/加壳后的类是否存在
- **精确方法定位**：处理方法重载时，用 descriptor 精确定位
- **全量字符串审计**：strings-analysis 一次性获取所有字符串及使用位置
- **访问标志分析**：`get-method` 的 access_flags 揭示方法是否 `private`/`static`/`native`/`abstract`
  - `native` 方法可能有 JNI 调用，需结合 .so 分析
  - `public` 的敏感方法可能被外部调用
