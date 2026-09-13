# DEX 头信息与隐藏 API

> DEX 文件头结构分析、快速类名列表、隐藏 API 检测

## 命令

### `dex header`

获取 DEX 文件头信息（magic、checksum、各 section 偏移和大小）。

```bash
androguard-skills dex header --apk-path test.apk
```

输出示例：

```json
{
  "header": {
    "magic": "6465780a30333500",
    "checksum": 2679116363,
    "signature": "08ceba004016...",
    "file_size": 252792,
    "header_size": 112,
    "string_ids_size": 2575,
    "string_ids_off": 112,
    "type_ids_size": 501,
    "method_ids_size": 2023,
    "class_defs_size": 294,
    "data_size": 200552,
    "data_off": 52240
  }
}
```

| 字段 | 说明 |
|------|------|
| `magic` | DEX 格式标识（`dex\n035\0`） |
| `checksum` | Adler32 校验和 |
| `signature` | SHA-1 签名（覆盖 checksum 之后的所有内容） |
| `string_ids_size` | 字符串常量池大小 |
| `method_ids_size` | 方法 ID 数量（可估算方法总数） |
| `class_defs_size` | 类定义数量 |

### `dex class-names`

快速获取 DEX 类名列表（不解析整个类，速度更快）。

```bash
androguard-skills dex class-names --apk-path test.apk
```

输出示例：

```json
{
  "total": 294,
  "classes": [
    "Lcom/example/MyActivity;",
    "Lcom/example/utils/CryptoHelper;",
    "Landroid/support/v4/app/FragmentCompat;"
  ]
}
```

> 与 `dex classes` 不同，此命令只返回类名，不解析类结构，适合快速概览。

### `dex hidden-api`

获取 DEX 中标记的隐藏 API 列表。

```bash
androguard-skills dex hidden-api --apk-path test.apk
```

输出示例：

```json
{
  "total": 0,
  "hidden_api": [],
  "note": "No hidden API data in this DEX"
}
```

> 大多数 APK 的 DEX 不包含隐藏 API 元数据。如果存在，则表明应用可能使用了 Android framework 的内部/隐藏接口。

## 安全分析用途

- **DEX 头校验**：checksum/signature 不匹配可能表示 DEX 被篡改
- **快速类名扫描**：在大型 APK 中快速定位可疑类名
- **隐藏 API 检测**：使用隐藏/内部 API 可能绕过安全限制
- **方法数量估算**：`method_ids_size` 超过 65536 表示 multidex
