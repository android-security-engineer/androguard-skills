# 交叉引用分析

追踪类和方法的调用关系。

> 注：所有 xref 列表（xref_from/xref_to）按 `from_class`/`to_class` → method →
> descriptor → offset 排序，保证同一 APK 多次运行输出字节级一致（agent 对接需
> 确定性比对）。

## XrefFrom - 谁引用了此类

查看哪些类引用了指定类：

```bash
androguard-skills analysis xrefs-from "Lcom/example/app/CryptoHelper;" --apk-path test.apk
```

输出示例：

```json
{
  "class": "Lcom/example/app/CryptoHelper;",
  "xref_from_count": 2,
  "xref_from": [
    {
      "from_class": "Lcom/example/app/LoginActivity;",
      "from_method": "encryptPassword",
      "offset": 42
    },
    {
      "from_class": "Lcom/example/app/NetworkClient;",
      "from_method": "signRequest",
      "offset": 18
    }
  ]
}
```

## XrefTo - 此类引用了谁

查看指定类引用了哪些类：

```bash
androguard-skills analysis xrefs-to "Lcom/example/app/LoginActivity;" --apk-path test.apk
```

输出示例：

```json
{
  "class": "Lcom/example/app/LoginActivity;",
  "xref_to_count": 3,
  "xref_to": [
    {
      "to_class": "Lcom/example/app/CryptoHelper;",
      "to_method": "encrypt",
      "offset": 10
    },
    {
      "to_class": "Lcom/example/app/NetworkClient;",
      "to_method": "sendData",
      "offset": 24
    },
    {
      "to_class": "Landroid/widget/Toast;",
      "to_method": "show",
      "offset": 36
    }
  ]
}
```

## 方法交叉引用

查看指定方法的调用关系：

```bash
androguard-skills analysis method-xrefs "Lcom/example/app/CryptoHelper;" "encrypt" --apk-path test.apk
```

输出示例：

```json
{
  "class": "Lcom/example/app/CryptoHelper;",
  "method": "encrypt",
  "is_external": false,
  "is_android_api": false,
  "xref_from_count": 2,
  "xref_from": [
    {
      "from_class": "Lcom/example/app/LoginActivity;",
      "from_method": "encryptPassword",
      "offset": 42
    }
  ],
  "xref_to_count": 1,
  "xref_to": [
    {
      "to_class": "Ljavax/crypto/Cipher;",
      "to_method": "doFinal",
      "offset": 8
    }
  ]
}
```

## 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `xref_from` | list | 谁调用了此类/方法 |
| `xref_to` | list | 此类/方法调用了谁 |
| `from_class` / `to_class` | string | 调用方/被调用方的类 |
| `from_method` / `to_method` | string | 调用方/被调用方的方法 |
| `offset` | int | 调用指令在方法中的偏移量 |
| `is_external` | bool | 是否为外部类（Android API 等） |
| `is_android_api` | bool | 是否为 Android API |

## 使用场景

- 攻击链追踪：从入口点追踪到敏感操作的完整调用链
- 影响范围评估：修改某方法后，找出所有受影响的调用方
- 敏感数据流分析：追踪密码、密钥等数据的流向
- 死代码检测：没有被任何地方引用的方法
- 依赖分析：了解类之间的耦合关系
