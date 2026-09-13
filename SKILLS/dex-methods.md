# DEX 方法和字段

获取 DEX 中的方法列表和字段列表。

## 方法列表

### 所有方法

```bash
androguard-skills dex methods --apk-path test.apk
```

### 指定类的方法

```bash
androguard-skills dex methods --class "Lcom/example/app/MainActivity;" --apk-path test.apk
```

### 输出示例

```json
{
  "total": 5,
  "methods": [
    {
      "class": "Lcom/example/app/MainActivity;",
      "name": "onCreate",
      "descriptor": "(Landroid/os/Bundle;)V",
      "access_flags": "protected"
    },
    {
      "class": "Lcom/example/app/MainActivity;",
      "name": "login",
      "descriptor": "(Ljava/lang/String;Ljava/lang/String;)Z",
      "access_flags": "private"
    }
  ]
}
```

## 字段列表

### 所有字段

```bash
androguard-skills dex fields --apk-path test.apk
```

### 指定类的字段

```bash
androguard-skills dex fields --class "Lcom/example/app/MainActivity;" --apk-path test.apk
```

### 输出示例

```json
{
  "total": 3,
  "fields": [
    {
      "class": "Lcom/example/app/MainActivity;",
      "name": "TAG",
      "access_flags": "private static final",
      "descriptor": "Ljava/lang/String;"
    },
    {
      "class": "Lcom/example/app/MainActivity;",
      "name": "apiKey",
      "access_flags": "private",
      "descriptor": "Ljava/lang/String;"
    }
  ]
}
```

## 方法描述符说明

Dalvik 方法描述符格式：

| 描述符 | Java 类型 |
|--------|-----------|
| `V` | void |
| `Z` | boolean |
| `I` | int |
| `J` | long |
| `L...;` | 对象类型 |
| `[` | 数组 |

示例：
- `(Ljava/lang/String;Ljava/lang/String;)Z` → `boolean method(String, String)`
- `(Landroid/os/Bundle;)V` → `void method(Bundle)`

## 使用场景

- 方法审计：找到特定方法（如 `login`、`encrypt`、`sendData`）
- 字段审计：发现硬编码的密钥、URL 等
- 攻击面评估：分析 public/protected 方法
- 逆向分析规划：确定 Hook 目标

## 搜索方法（Analysis 模式）

使用 Analysis 的 find-methods 可以按方法名正则搜索：

```bash
androguard-skills analysis find-methods ".*encrypt.*" --apk-path test.apk
```

输出包含 `is_external` 字段，可以区分应用内部方法和外部 API。
