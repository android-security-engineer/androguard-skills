# DEX 类信息

获取 DEX 中的类列表，支持正则过滤。

## 列出所有类

```bash
androguard-skills dex classes --apk-path test.apk
```

## 按正则过滤

```bash
# 只看 Activity 相关类
androguard-skills dex classes --filter "Activity" --apk-path test.apk

# 使用完整正则
androguard-skills dex classes --filter "Lcom/example/.*" --apk-path test.apk
```

## 输出示例

```json
{
  "total": 2,
  "classes": [
    {
      "name": "Lcom/example/app/MainActivity;",
      "access_flags": "public",
      "superclass": "Landroid/app/Activity;"
    },
    {
      "name": "Lcom/example/app/utils/CryptoHelper;",
      "access_flags": "public"
    }
  ]
}
```

## 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `total` | int | 匹配的类总数 |
| `name` | string | 类名（Dalvik 格式，如 `Lcom/example/MyClass;`） |
| `access_flags` | string | 访问标志（public, private, abstract 等） |
| `superclass` | string | 父类名（部分类无父类则缺省） |

> 注：`dex classes` 是轻量清单命令，只返回类名/标志/父类，**不含反编译源码**
> （避免输出膨胀与非确定性）。需要某类的反编译源码用 `decompile class`，
> 需要 ClassDefItem 底层元信息（源文件名/接口/注解）用 `dex class-meta`。

## 类名格式说明

DEX 中的类名使用 Dalvik 格式：
- `Lcom/example/app/MainActivity;` → 对应 Java 的 `com.example.app.MainActivity`
- `L` 开头，`;` 结尾，`/` 代替 `.`

## 使用场景

- 应用结构分析：了解类组织方式
- 安全审计：定位可疑类（如包含 crypto、password、login 等关键词的类）
- 逆向分析：找到目标类后进一步反编译
- 搜索特定框架类（如 Flutter、React Native 相关类）

## 搜索类（Analysis 模式）

使用 Analysis 的 find-classes 可以获取更详细的信息：

```bash
androguard-skills analysis find-classes ".*Crypto.*" --apk-path test.apk
```

输出包含 `is_external` 和 `is_android_api` 字段，可以区分内部类和外部 API 类。
