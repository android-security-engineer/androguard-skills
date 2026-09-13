# APK 文件提取

> 从 APK 中提取指定文件内容

## 命令

### `apk file <filename>`

提取 APK 中指定文件的内容，返回 base64 编码。

```bash
androguard-skills apk file "AndroidManifest.xml" --apk-path test.apk
androguard-skills apk file "assets/config.json" --apk-path test.apk
androguard-skills apk file "lib/armeabi-v7a/libnative.so" --apk-path test.apk
```

输出示例：

```json
{
  "filename": "assets/config.json",
  "size": 1024,
  "base64": "eyJkZWJ1ZyI6..."
}
```

如果文件不存在：

```json
{
  "filename": "nonexistent.txt",
  "error": "File 'nonexistent.txt' not found in APK"
}
```

## 安全分析用途

- **提取配置文件**：`assets/` 下的 JSON/XML 配置可能包含 API 密钥、服务器地址
- **提取 native 库**：`lib/` 下的 `.so` 文件可用于进一步 native 分析
- **提取证书/密钥**：`assets/` 或 `res/raw/` 中可能硬编码证书
- **提取 DEX 文件**：secondary DEX 可能有隐藏逻辑

## 提取后解码

```bash
# 提取并解码文件
androguard-skills apk file "assets/config.json" --apk-path test.apk | \
  python3 -c "import sys,json,base64; d=json.load(sys.stdin); print(base64.b64decode(d['base64']).decode())"
```
