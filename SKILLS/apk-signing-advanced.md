# APK 高级签名与证书分析

> 签名方案检测、按方案批量获取证书/DER/公钥、签名文件原始数据、文件 CRC32

## 命令

### `apk signing-versions`

检测 APK 支持的签名方案（v1/v2/v3/v3.1）。

```bash
androguard-skills apk signing-versions --apk-path test.apk
```

输出示例：

```json
{
  "is_signed": true,
  "is_valid_apk": true,
  "is_multidex": false,
  "v1": true,
  "v2": true,
  "v3": true,
  "v31": false,
  "has_duplicate_apk_signature_ids": false
}
```

> - **v1**：JAR 签名（META-INF/*.RSA），Android 7.0 前唯一方案
> - **v2**：APK 签名方案 v2（全文件签名），Android 7.0+，覆盖整个 APK
> - **v3**：APK 签名方案 v3（支持密钥轮换），Android 9.0+
> - **v31**：v3.1（ lineage 密钥轮换），Android 11+
> - `has_duplicate_apk_signature_ids` 为 true 表示签名 ID 重复，可能存在签名冲突

### `apk certificates-scheme`

按签名方案批量获取证书详情。

```bash
androguard-skills apk certificates-scheme --scheme v3 --apk-path test.apk
androguard-skills apk certificates-scheme --scheme v1 --apk-path test.apk
androguard-skills apk certificates-scheme --scheme v31 --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--scheme` | 签名方案（v1/v2/v3/v31，默认 v3） |

输出示例：

```json
{
  "scheme": "v3",
  "total": 1,
  "certificates": [
    {
      "sha1": "66efa4b5...",
      "sha256": "...",
      "issuer": "CN=FDroid, OU=FDroid, O=fdroid.org...",
      "subject": "CN=FDroid, OU=FDroid, O=fdroid.org...",
      "serial_number": "0x7450b7bc",
      "hash_algorithm": "sha256",
      "signature_algorithm": "sha256_rsa",
      "valid_not_before": "2017-07-23 19:19:28+00:00",
      "valid_not_after": "2044-12-08 19:19:28+00:00"
    }
  ]
}
```

> 与 `apk certificate` 的区别：`certificate` 按**签名文件名**查单个证书；`certificates-scheme` 按**签名方案**批量获取该方案下所有证书，便于对比不同方案的证书链。

### `apk certificates-der`

按签名方案获取证书 DER 二进制（base64 编码）。

```bash
androguard-skills apk certificates-der --scheme v3 --apk-path test.apk
androguard-skills apk certificates-der --scheme v2 --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--scheme` | 签名方案（v2/v3/v31，默认 v3；v1 不支持，需用 `apk certificate`） |

输出示例：

```json
{
  "scheme": "v3",
  "total": 1,
  "certificates": [
    {
      "size": 867,
      "sha1": "66efa4b57667a4c2...",
      "sha256": "...",
      "base64": "MIIF..."
    }
  ]
}
```

> DER 是证书的原始 ASN.1 编码，可用于外部工具（如 openssl）重新解析，或与系统证书库比对。base64 字段可直接 `| base64 -d > cert.der` 导出。

### `apk public-keys`

按签名方案获取签名公钥信息。

```bash
androguard-skills apk public-keys --scheme v3 --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--scheme` | 签名方案（v2/v3/v31，默认 v3） |

输出示例：

```json
{
  "scheme": "v3",
  "total": 1,
  "public_keys": [
    {
      "algorithm": "rsa",
      "key_size": 2048,
      "size": 294,
      "sha1": "...",
      "sha256": "b00b9a2c244b4d7a...",
      "base64": "MIIB..."
    }
  ]
}
```

> `key_size` 反映密钥强度（2048 位 RSA 为常见最小值）。base64 是公钥的 DER 编码，可导入其他工具验证签名。

### `apk signature-files`

获取 APK 签名文件信息（文件名 + 原始签名数据 base64）。

```bash
androguard-skills apk signature-files --apk-path test.apk
```

输出示例：

```json
{
  "signature_name": "META-INF/13258F09.RSA",
  "signature_names": ["META-INF/13258F09.RSA"],
  "signature_base64": "MIIE...",
  "signature_size": 1334,
  "signatures": [
    {"size": 1334, "sha256": "...", "base64": "MIIE..."}
  ],
  "signatures_count": 1
}
```

> `signature_base64` 是 v1 PKCS#7 签名块的原始字节，可用于离线验签或与签名服务端比对。

### `apk files-crc32`

获取 APK 中所有文件的 CRC32 校验值。

```bash
androguard-skills apk files-crc32 --apk-path test.apk
```

输出示例：

```json
{
  "total": 47,
  "files": [
    {"name": "classes.dex", "crc32": "0xbec1d89f", "crc32_dec": 3200374943},
    {"name": "AndroidManifest.xml", "crc32": "0x...", "crc32_dec": 123456}
  ]
}
```

> CRC32 用于文件完整性校验。比对两个 APK 的 CRC32 可快速定位被篡改的文件（如植入后门的 `classes.dex`）。

## 安全分析用途

- **签名方案审计**：仅 v1 签名的 APK 可被 Janus 漏洞攻击（CVE-2017-13156），应同时具备 v2+
- **证书有效期**：`valid_not_after` 过期的证书会导致安装失败，但仍可被已安装应用使用
- **自签名检测**：`issuer` == `subject` 表示自签名证书（如调试证书、FDroid 签名）
- **密钥强度**：RSA < 2048 位或 DSA 密钥应视为弱签名
- **签名比对**：`certificates-der` 的 sha256 可用于验证 APK 是否由同一签名者发布
- **完整性校验**：`files-crc32` 检测 APK 内文件是否被篡改（与官方发布版本比对）
- **签名冲突**：`has_duplicate_apk_signature_ids` 为 true 可能导致安装失败

## 相关命令

- [`apk signature`](apk-signature.md) — 签名验证结果
- [`apk certificate`](apk-certificate.md) — 按文件名查单个证书
- [`apk verify`](apk-verify.md) — APK 完整性校验
- [`apk signing-block`](apk-verify.md) — v2/v3 签名块详情
