# APK 证书详情与二进制提取

> 签名证书详情、DEX 二进制提取、APK 原始字节、文件详细信息

## 命令

### `apk certificate`

获取 APK 签名证书详情（颁发者/主题/序列号/有效期/指纹）。

```bash
# 获取所有证书
androguard-skills apk certificate --apk-path test.apk

# 获取指定签名文件的证书
androguard-skills apk certificate --filename "META-INF/CERT.RSA" --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--filename` | 签名文件名（如 META-INF/CERT.RSA）。省略则返回所有证书 |

输出示例：

```json
{
  "total": 1,
  "certificates": [
    {
      "sha1": "a1b2c3...",
      "sha256": "d4e5f6...",
      "md5": "7890ab...",
      "issuer": "CN=Example",
      "subject": "CN=Example",
      "serial_number": "0x1",
      "valid_not_before": "2020-01-01 00:00:00",
      "valid_not_after": "2045-01-01 00:00:00"
    }
  ]
}
```

### `apk files-info`

获取 APK 中所有文件的详细信息（名称/类型/CRC32）。

```bash
androguard-skills apk files-info --apk-path test.apk
```

输出示例：

```json
{
  "total": 150,
  "files": [
    {"name": "AndroidManifest.xml", "type": "Unknown", "crc32": "0x1234abcd"},
    {"name": "classes.dex", "type": "Unknown", "crc32": "0x5678ef90"}
  ]
}
```

### `apk dex-data`

提取 DEX 二进制数据（base64 编码），用于脱壳/转储分析。

```bash
# 仅主 DEX
androguard-skills apk dex-data --apk-path test.apk

# 所有 DEX（multidex）
androguard-skills apk dex-data --all-dex --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--all-dex` | 提取所有 DEX（multidex 场景） |

输出示例：

```json
{
  "size": 252792,
  "base64": "ZGV4CjAzNQ..."
}
```

### `apk raw`

提取整个 APK 的原始字节（base64 编码）。

```bash
androguard-skills apk raw --apk-path test.apk
```

输出示例：

```json
{
  "size": 1500000,
  "base64": "UEsDBBQ..."
}
```

## 提取后解码

```bash
# 解码 DEX 并保存为文件
androguard-skills apk dex-data --apk-path test.apk | \
  python3 -c "import sys,json,base64; d=json.load(sys.stdin); open('/tmp/classes.dex','wb').write(base64.b64decode(d['base64']))"
```

## 安全分析用途

- **证书指纹对比**：识别同一开发者签名的多个应用（指纹相同）
- **证书有效期**：检查证书是否过期或有效期异常长
- **DEX 提取**：脱壳后提取 DEX 用于进一步分析，或对比官方版本
- **CRC 完整性**：`files-info` 的 CRC32 可用于检测文件被篡改
- **APK 原始数据**：完整 APK 字节可用于哈希校验或离线分析
