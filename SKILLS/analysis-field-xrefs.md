# 字段交叉引用与搜索

> 字段级别的引用分析：谁读取/写入了字段、按正则搜索字段

## 命令

### `analysis field-xrefs <class_name> <field_name>`

获取指定字段的交叉引用（谁读取/写入了此字段）。

```bash
androguard-skills analysis field-xrefs "Lcom/example/CryptoUtils;" "secretKey" --apk-path test.apk
```

输出示例：

```json
{
  "class": "Lcom/example/CryptoUtils;",
  "field": "secretKey",
  "descriptor": "Ljava/lang/String;",
  "access_flags": "private",
  "xref_read_count": 1,
  "xref_read": [
    {
      "class": "Lcom/example/CryptoUtils;",
      "method": "encryptAES",
      "descriptor": "(Ljava/lang/String;)Ljava/lang/String;"
    }
  ],
  "xref_write_count": 1,
  "xref_write": [
    {
      "class": "Lcom/example/CryptoUtils;",
      "method": "initKeys",
      "descriptor": "()V"
    }
  ]
}
```

| 字段 | 说明 |
|------|------|
| `xref_read` | 读取此字段的方法列表 |
| `xref_write` | 写入/修改此字段的方法列表 |
| `descriptor` | 字段类型 |
| `access_flags` | 访问修饰符（public/private/static 等） |

### `analysis field-xrefs-detail <class_name> <field_name>`

获取字段读/写引用的**完整列表（含每处引用的 offset，不去重）**。与 `field-xrefs`（用 `get_xref_read()` 无 offset、set 去重）的区别：本命令用 `with_offset=True`，每处引用一条记录，同一方法多处读/写会出现多条，可精确定位字段被访问的指令位置。

```bash
androguard-skills analysis field-xrefs-detail Lcom/example/Foo; textView --apk-path test.apk
```

**输出：**
```json
{
  "class": "Lcom/example/Foo;",
  "field": "textView",
  "descriptor": "Landroid/widget/EditText;",
  "access_flags": "private",
  "xref_read": {
    "count": 89,
    "refs": [
      {"class": "Lcom/example/Foo;", "method": "loadText", "descriptor": "(Ljava/lang/CharSequence;)V", "offset": 180},
      {"class": "Lcom/example/Foo;", "method": "onCreate", "descriptor": "(Landroid/os/Bundle;)V", "offset": 644},
      ...
    ]
  },
  "xref_write": {
    "count": 1,
    "refs": [
      {"class": "Lcom/example/Foo;", "method": "onCreate", "descriptor": "(Landroid/os/Bundle;)V", "offset": 502}
    ]
  }
}
```

**与 `field-xrefs` 的对比：**

| 维度 | `field-xrefs` | `field-xrefs-detail` |
|------|--------------|---------------------|
| offset | 无 | 有（每处引用的指令偏移） |
| 去重 | 是（按方法去重） | 否（每处引用一条） |
| 返回结构 | `xref_read: [{class,method,descriptor}]` | `xref_read: {count, refs: [{class,method,descriptor,offset}]}` |
| 示例值 | read_count=32 | read count=89（32 个方法共 89 处读取） |

**用途：**
- 精确定位字段访问的指令位置（offset 可传给 `dex disassemble` 反汇编上下文）
- 统计字段的真实访问频次（去重版只看方法数，detail 看实际访问次数）
- 高频读写的字段是数据流分析的关键节点

### `analysis find-fields <pattern>`

按正则表达式搜索字段。

```bash
androguard-skills analysis find-fields "key" --apk-path test.apk
androguard-skills analysis find-fields "password|token|secret" --apk-path test.apk
```

输出示例：

```json
{
  "pattern": "key",
  "total": 5,
  "fields": [
    {
      "name": "secretKey",
      "class": "Lcom/example/CryptoUtils;",
      "descriptor": "Ljava/lang/String;",
      "access_flags": "private static final"
    },
    {
      "name": "apiKey",
      "class": "Lcom/example/network/ApiClient;",
      "descriptor": "Ljava/lang/String;",
      "access_flags": "private"
    }
  ]
}
```

### `analysis permissions-map`

获取分析层面的完整权限映射。

```bash
androguard-skills analysis permissions-map --apk-path test.apk
```

输出示例：

```json
{
  "total": 3,
  "permissions": [
    "android.permission.INTERNET",
    "android.permission.ACCESS_NETWORK_STATE",
    "android.permission.READ_EXTERNAL_STORAGE"
  ]
}
```

> 与 `apk permissions` 不同，此命令从分析层面获取权限映射，可能包含隐含权限。

## 安全分析用途

- **密钥追踪**：搜索 `key`/`secret`/`password` 字段，然后追踪谁读写
- **硬编码凭证**：`private static final String` 类型的密钥字段通常是硬编码
- **字段泄露**：`public` 修饰的敏感字段可被外部类直接访问
- **写入追踪**：追踪谁修改了安全相关的字段（如认证状态、令牌）
