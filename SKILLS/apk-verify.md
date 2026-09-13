# APK 完整性校验与签名块

> APK 验证、签名状态检查、v2/v3 签名块详情

## 命令

### `apk verify`

验证 APK 完整性和签名状态。

```bash
androguard-skills apk verify --apk-path test.apk
```

输出示例：

```json
{
  "is_valid": true,
  "is_signed": true,
  "is_signed_v1": true,
  "is_signed_v2": true,
  "is_signed_v3": true,
  "is_signed_v31": false,
  "signature_names": ["META-INF/CERT.RSA"],
  "has_duplicate_signature_ids": false
}
```

| 字段 | 说明 |
|------|------|
| `is_valid` | APK ZIP 结构是否完整 |
| `is_signed_v1` | 是否有 JAR 签名（v1） |
| `is_signed_v2` | 是否有 APK Signature Scheme v2 |
| `is_signed_v3` | 是否有 APK Signature Scheme v3（密钥轮替） |
| `is_signed_v31` | 是否有 APK Signature Scheme v3.1 |
| `has_duplicate_signature_ids` | 是否存在重复签名 ID（可能被篡改） |

### `apk signing-block`

获取 v2/v3 签名块详细信息，包括公钥指纹。

```bash
androguard-skills apk signing-block --apk-path test.apk
```

输出示例：

```json
{
  "v2_public_keys": [
    {
      "sha256": "b00b9a2c244b4d7add259b9168756cc5199c0ff8...",
      "size": 294
    }
  ],
  "v3_public_keys": [
    {
      "sha256": "b00b9a2c244b4d7add259b9168756cc5199c0ff8...",
      "size": 294
    }
  ]
}
```

### `apk verify-signature [--filename]`

对 APK 签名做**密码学验证**（验证签名者信息是否匹配签名文件）。与 `apk verify`（结构 + 签名方案存在性检查）和 `apk certificate`（取证书，间接验证）的区别：本命令显式调用 `get_certificate_der(filename)`，它内部走 `verify_signer_info_against_sig_file` —— 真正验证 PKCS7 签名者信息对 `.SF` 签名文件的密码学有效性（签名是否匹配内容、证书是否对签名有效），返回每个签名文件的验证结果（通过含证书摘要，或失败含原因）。

```bash
# 验证所有签名文件
androguard-skills apk verify-signature --apk-path test.apk

# 验证指定签名文件
androguard-skills apk verify-signature --filename META-INF/CERT.RSA --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--filename` | 签名文件名（如 `META-INF/CERT.RSA`）。省略时验证所有签名文件 |

**输出：**
```json
{
  "verified": true,
  "total": 1,
  "signatures": [
    {
      "filename": "META-INF/13258F09.RSA",
      "verified": true,
      "der_size": 867,
      "sha256": "dc44ca63efa29803...",
      "certificate": {
        "sha256": "dc44ca63...",
        "issuer": "CN=Editor",
        "subject": "CN=Editor",
        "serial_number": "0x1",
        "valid_not_before": "2020-01-01 00:00:00",
        "valid_not_after": "2047-01-01 00:00:00"
      }
    }
  ]
}
```

| 字段 | 说明 |
|------|------|
| `verified` | 全部签名文件是否都验证通过 |
| `signatures[].verified` | 单个签名文件是否验证通过 |
| `signatures[].sha256` | 验证通过的证书 DER 的 SHA-256（仅通过时有） |
| `signatures[].certificate` | 证书摘要（issuer/subject/serial/有效期，仅通过时有） |
| `signatures[].error` | 验证失败原因（仅失败时有，如 `Signature file not found` / `Signature verification failed` / `InvalidSignature: ...`） |

> 仅适用于 v1（JAR）签名（基于 `META-INF/*.RSA` 签名文件）。v2/v3 签名方案的存在性检查用 `apk verify`（`is_signed_v2`/`is_signed_v3`）。验证失败（`verified: false`）意味着 APK 内容被篡改或签名无效——安全审计中用于确认 APK 完整性的关键信号。

## 安全分析用途

- **签名验证绕过检测**：`is_valid` 为 false 可能是被篡改的 APK
- **v1 签名风险**：仅 v1 签名的 APK 容易被修改（不校验内容完整性）
- **签名块分析**：v2/v3 签名块的公钥指纹可用于追踪开发者
- **重复签名 ID**：可能表明签名注入攻击
- **密钥轮替**：v3 签名支持密钥轮替，对比 v2/v3 公钥是否一致
