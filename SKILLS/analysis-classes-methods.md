# 内部/外部类与方法分析

> 区分应用内部代码与外部依赖，枚举内部类/方法/外部类/方法

## 命令

### `analysis internal-classes`

获取应用内部类列表（非外部依赖库的类）。

```bash
androguard-skills analysis internal-classes --apk-path test.apk
# 过滤包含特定关键词的类
androguard-skills analysis internal-classes --filter "Login" --apk-path test.apk
```

输出示例：

```json
{
  "total": 36,
  "classes": [
    {"name": "Lcom/example/app/LoginActivity;", "is_android_api": false},
    {"name": "Lcom/example/app/CryptoUtils;", "is_android_api": false}
  ]
}
```

### `analysis external-classes`

获取外部依赖类列表（第三方库和 Android API）。

```bash
androguard-skills analysis external-classes --apk-path test.apk
androguard-skills analysis external-classes --filter "okhttp" --apk-path test.apk
```

输出示例：

```json
{
  "total": 1500,
  "classes": [
    {"name": "Lokhttp3/OkHttpClient;", "is_android_api": false},
    {"name": "Landroid/app/Activity;", "is_android_api": true}
  ]
}
```

### `analysis internal-methods`

获取应用内部方法列表。

```bash
androguard-skills analysis internal-methods --apk-path test.apk
androguard-skills analysis internal-methods --filter "encrypt" --apk-path test.apk
```

输出示例：

```json
{
  "total": 200,
  "methods": [
    {"class": "Lcom/example/CryptoUtils;", "method": "encryptAES", "descriptor": "(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;"},
    {"class": "Lcom/example/LoginActivity;", "method": "validateToken", "descriptor": "(Ljava/lang/String;)Z"}
  ]
}
```

### `analysis external-methods`

获取外部方法列表（第三方库和 Android API 方法）。

```bash
androguard-skills analysis external-methods --apk-path test.apk
androguard-skills analysis external-methods --filter "Cipher" --apk-path test.apk
```

输出示例：

```json
{
  "total": 15,
  "methods": [
    {"class": "Ljavax/crypto/Cipher;", "method": "doFinal", "descriptor": "([B)[B"}
  ]
}
```

## 安全分析用途

- **内部类定位**：只分析应用自有代码，忽略第三方库噪音
- **外部类识别**：识别使用了哪些第三方库（OkHttp、Retrofit、Glide 等）
- **敏感方法发现**：在内部方法中搜索 `encrypt`、`decrypt`、`login`、`token` 等关键词
- **Android API 使用**：`external-methods --filter "Cipher"` 可发现加密 API 使用
- **代码量评估**：`internal-classes` 数量反映应用自身代码规模
