# DEX 字符串搜索

获取 DEX 中的字符串，支持正则过滤。

## 列出所有字符串

```bash
androguard-skills dex strings --apk-path test.apk
```

## 按正则过滤

```bash
# 搜索包含 URL 的字符串
androguard-skills dex strings --filter "https?://" --apk-path test.apk

# 搜索密码相关
androguard-skills dex strings --filter "password|passwd|pwd" --apk-path test.apk

# 搜索 IP 地址
androguard-skills dex strings --filter "\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}" --apk-path test.apk
```

## 输出示例

```json
{
  "total": 3,
  "strings": [
    "https://api.example.com/v1",
    "https://backup-server.example.com",
    "http://debug.local:8080"
  ]
}
```

## 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `total` | int | 匹配的字符串总数 |
| `strings` | list | 字符串列表 |

## 常用搜索模式

| 搜索目的 | 正则表达式 |
|----------|-----------|
| URL | `https?://` |
| 硬编码密码 | `password|passwd|pwd|secret` |
| API 密钥 | `api_key|apikey|API_KEY` |
| IP 地址 | `\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}` |
| 加密算法 | `AES|RSA|DES|MD5|SHA` |
| 域名 | `\\.com|\\.net|\\.org|\\.cn` |
| 文件路径 | `/sdcard/|/data/|/tmp/` |
| Base64 特征 | `[A-Za-z0-9+/]{20,}` |

## 使用场景

- 信息泄露检测：发现硬编码的 URL、密钥、密码
- 网络行为分析：找出所有通信目标地址
- 加密检测：发现使用的加密算法
- 调试痕迹：检测残留的 debug 字符串
- 恶意行为指标：搜索可疑的命令、路径、域名

## 字符串追踪（Analysis 模式）

查看字符串在代码中的使用位置：

```bash
androguard-skills analysis find-strings "https?://" --apk-path test.apk
```

输出会包含 `used_in` 字段，列出哪些类和方法使用了该字符串。
