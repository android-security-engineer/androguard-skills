# APK 签名验证

获取 APK 签名方案、证书指纹等安全信息。

## 命令

```bash
androguard-skills apk signature --apk-path test.apk
```

## 输出示例

```json
{
  "is_signed": true,
  "is_signed_v1": true,
  "is_signed_v2": true,
  "is_signed_v3": false,
  "is_signed_v31": false,
  "signature_names": ["META-INF/CERT.RSA"],
  "certificates": [
    {
      "sha1": "a1b2c3d4e5f6...",
      "sha256": "f1e2d3c4b5a6...",
      "md5": "1a2b3c4d5e6f...",
      "issuer": "CN=Android Debug,O=Android,C=US",
      "subject": "CN=Android Debug,O=Android,C=US",
      "serial_number": "0x1",
      "hash_algorithm": "sha256WithRSAEncryption",
      "signature_algorithm": "sha256WithRSAEncryption",
      "valid_not_before": "2024-01-01 00:00:00",
      "valid_not_after": "2051-01-01 00:00:00"
    }
  ]
}
```

## 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `is_signed` | bool | 是否有签名 |
| `is_signed_v1` | bool | JAR 签名（v1） |
| `is_signed_v2` | bool | APK 签名方案 v2 |
| `is_signed_v3` | bool | APK 签名方案 v3（支持密钥轮替） |
| `is_signed_v31` | bool | APK 签名方案 v3.1 |
| `signature_names` | list | 签名文件名 |
| `certificates` | list | 证书详情列表 |

## 证书字段说明

| 字段 | 说明 |
|------|------|
| `sha1` | SHA-1 指纹 |
| `sha256` | SHA-256 指纹 |
| `md5` | MD5 指纹 |
| `issuer` | 颁发者 |
| `subject` | 主体 |
| `serial_number` | 序列号 |
| `hash_algorithm` | 哈希算法 |
| `signature_algorithm` | 签名算法 |
| `valid_not_before` | 生效时间 |
| `valid_not_after` | 过期时间 |

## 使用场景

- 签名验证：确认 APK 是否被重新签名
- Debug 签名检测：检测是否使用 debug 证书签名
- 证书指纹比对：比对不同 APK 是否使用同一签名
- 签名方案分析：判断 APK 的签名安全级别

## 安全关注点

| 关注点 | 说明 |
|--------|------|
| 仅 v1 签名 | 可能遭受 V2 签名剥离攻击 |
| Debug 证书 | 不应出现在生产版本中 |
| 多证书 | v1/v2/v3 证书不一致可能存在问题 |
| 过期证书 | 签名已过期，无法验证 |
| 自签名证书 | 非知名 CA 签发，需额外审查 |
