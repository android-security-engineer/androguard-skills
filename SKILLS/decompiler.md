# 反编译

将 DEX 字节码反编译为 Java 源码。

## 反编译整个类

```bash
androguard-skills decompile class "Lcom/example/app/MainActivity;" --apk-path test.apk
```

输出示例：

```json
{
  "class": "Lcom/example/app/MainActivity;",
  "source": "package com.example.app;\n\nimport android.app.Activity;\nimport android.os.Bundle;\n\npublic class MainActivity extends Activity {\n    @Override\n    protected void onCreate(Bundle savedInstanceState) {\n        super.onCreate(savedInstanceState);\n        setContentView(R.layout.activity_main);\n    }\n}\n"
}
```

## 反编译单个方法

```bash
androguard-skills decompile method "Lcom/example/app/CryptoHelper;" "encrypt" --apk-path test.apk
```

输出示例：

```json
{
  "class": "Lcom/example/app/CryptoHelper;",
  "method": "encrypt",
  "descriptor": "([B)[B",
  "source": "public byte[] encrypt(byte[] data) {\n    Cipher cipher = Cipher.getInstance(\"AES/CBC/PKCS5Padding\");\n    cipher.init(1, this.secretKey, this.ivSpec);\n    return cipher.doFinal(data);\n}"
}
```

## 反编译方法 AST（结构化抽象语法树）

```bash
androguard-skills decompile method-ast "Lcom/example/app/CryptoHelper;" "encrypt" --apk-path test.apk
```

与 `method`（返回纯文本源码）的区别：本命令用 `DvMethod.process(doAST=True)` + `get_ast()` 返回**嵌套 AST 字典**，body 是可程序化遍历的语法树节点（如 `MethodInvocation`/`IfStatement`），适合自动检测特定代码模式、方法调用提取、控制流结构分析。

输出示例：

```json
{
  "class": "Lorg/billthefarmer/editor/Editor;",
  "method": "onCreate",
  "descriptor": "(Landroid/os/Bundle;)V",
  "ast": {
    "triple": ["org/billthefarmer/editor/Editor", "onCreate", "(Landroid/os/Bundle;)V"],
    "flags": ["protected"],
    "ret": ["TypeName", [".void", 0]],
    "params": [[["TypeName", ["android/os/Bundle", 0]], ["Local", "p8"]]],
    "comments": [],
    "body": [ /* 语句节点列表，每个是嵌套 AST */ ]
  }
}
```

**AST 字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `triple` | `[class, method, descriptor]` | 方法三元组（类名无 L/; 包裹） |
| `flags` | `list[str]` | 访问标志（如 `protected`/`static`） |
| `ret` | `[type, value]` | 返回类型节点 |
| `params` | `list[[type, name]]` | 参数列表，每项是类型+局部变量名 |
| `comments` | `list` | 反编译注释 |
| `body` | `list` | 方法体语句节点（嵌套 AST，可递归遍历） |

> 底层 API：`DvMethod(method_analysis).process(doAST=True)` + `get_ast()`。body 节点结构由 DAD 反编译器定义，节点类型如 `MethodInvocation`（方法调用）、`IfStatement`（条件）、`ReturnStatement`（返回）等，可程序化匹配检测特定模式。

## 反编译方法 Token 流（词法 token）

```bash
androguard-skills decompile method-tokens "Lcom/example/app/CryptoHelper;" "encrypt" --apk-path test.apk

# 限制返回数量（默认全部）
androguard-skills decompile method-tokens "Lcom/example/app/CryptoHelper;" "encrypt" --limit 50 --apk-path test.apk
```

与 `method`（纯文本）和 `method-ast`（AST）的区别：本命令用 `DvMethod.get_source_ext()` 返回**带词法类型的 token 列表**，每项是 `{type, value}`（如 `{"type":"IDENTIFIER","value":"onCreate"}`、`{"type":"NEWLINE","value":"\n    "}`），适合词法级分析、精确源码片段定位。

输出示例：

```json
{
  "class": "Lorg/billthefarmer/editor/Editor;",
  "method": "onCreate",
  "descriptor": "(Landroid/os/Bundle;)V",
  "total": 903,
  "returned": 20,
  "tokens": [
    {"type": "NEWLINE", "value": "\n    "},
    {"type": "PROTOTYPE_ACCESS", "value": "protected "},
    {"type": "PROTOTYPE_TYPE", "value": "void"},
    ...
  ]
}
```

| 参数 | 说明 |
|------|------|
| `class_name`（位置） | 类名（Dalvik 格式） |
| `method_name`（位置） | 方法名 |
| `--limit` | 返回 token 数量上限（默认全部） |

`total` 是完整 token 总数，`returned` 是实际返回数（受 `--limit` 限制）。token 的 `type` 由 DAD 词法器定义（`IDENTIFIER`/`NEWLINE`/`PROTOTYPE_ACCESS`/`PROTOTYPE_TYPE`/`STRING` 等）。

## 反编译类 AST（类级结构化语法树）

```bash
androguard-skills decompile class-ast "Lcom/example/app/CryptoHelper;" --apk-path test.apk

# 限制返回的 fields/methods 数量（大型类 AST 可达数百 KB，limit 避免输出过大）
androguard-skills decompile class-ast "Lcom/example/Foo;" --fields-limit 5 --methods-limit 3 --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `class_name`（位置） | 类名（Dalvik 格式） |
| `--fields-limit` | 返回字段 AST 数量上限（默认全部；截断后仍返回 `fields_total` 总数） |
| `--methods-limit` | 返回方法 AST 数量上限（默认全部；截断后仍返回 `methods_total` 总数） |

> 大型类的完整 AST 可能很大（如 editor.apk 的 `Editor` 类约 415KB，含 134 字段 + 114 方法）。若只需类结构概览，用 `--fields-limit 0 --methods-limit 0` 取空列表 + 总数，或配 `dex class-data` 取方法/字段元数据清单。

与 `method-ast`（单方法 AST）和 `class`（纯文本源码）的区别：本命令用 `DvClass.process(doAST=True)` + `get_ast()` 一次返回**类级 AST 字典**，含 `rawname`/`name`/`super`/`flags`/`isInterface`/`interfaces`/`fields`/`methods`，`fields` 是字段 AST 列表、`methods` 是方法 AST 列表（每项含 `triple`/`flags`/`ret`/`params`/`comments`/`body`，与 `method-ast` 结构一致），适合批量自动检测类内代码模式。

输出示例：

```json
{
  "class": "Lcom/ibm/icu/text/CharsetMatch;",
  "ast": {
    "rawname": "com/ibm/icu/text/CharsetMatch",
    "name": ["TypeName", ["com/ibm/icu/text/CharsetMatch", 0]],
    "super": ["TypeName", ["java/lang/Object", 0]],
    "flags": ["public"],
    "isInterface": false,
    "interfaces": [],
    "fields": [
      {"triple": ["com/ibm/icu/text/CharsetMatch", "fInputBytes", "[B"], "type": ["TypeName", ...], "flags": [...], "expr": [...]},
      ...
    ],
    "methods": [
      {"triple": ["com/ibm/icu/text/CharsetMatch", "getName", "()Ljava/lang/String;"], "flags": ["public"], "ret": [...], "params": [], "comments": [], "body": [...]},
      ...
    ]
  }
}
```

**类 AST 字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `rawname` | string | 类全名（`/` 分隔，无 `L`/`;`） |
| `name`/`super` | `[type, value]` | 类名/父类名节点 |
| `flags` | `list[str]` | 类访问标志（如 `public`/`abstract`/`final`） |
| `isInterface` | bool | 是否为接口 |
| `interfaces` | `list` | 实现的接口列表 |
| `fields` | `list` | 字段 AST 列表（每项含 `triple`/`type`/`flags`/`expr`） |
| `methods` | `list` | 方法 AST 列表（每项含 `triple`/`flags`/`ret`/`params`/`comments`/`body`） |
| `fields_total` | int | 字段 AST 总数（即使 `--fields-limit` 截断，仍返回完整总数） |
| `methods_total` | int | 方法 AST 总数（即使 `--methods-limit` 截断，仍返回完整总数） |

> 底层 API：`DvClass(ClassDefItem, Analysis).process(doAST=True)` + `get_ast()`。`methods` 内每项的 `body` 是可递归遍历的语句 AST（节点类型如 `MethodInvocation`/`IfStatement`），与 `method-ast` 输出同构——可对类内所有方法批量做模式匹配。大型类的 AST 可能很大（Editor 类约 415KB）。

## 反编译类 Token 流（类级词法 token）

```bash
androguard-skills decompile class-tokens "Lcom/example/app/CryptoHelper;" --apk-path test.apk

# 限制返回的顶层 token 数量
androguard-skills decompile class-tokens "Lcom/example/Foo;" --limit 10 --apk-path test.apk
```

与 `class-ast`（类级 AST）和 `class`（纯文本源码）的区别：本命令用 `DvClass.get_source_ext()` 返回**类级 token 列表**，每项是 `{category, tokens}`，`category` 标识语法单元（`PACKAGE`/`PROTOTYPE`/`FIELD`/`METHOD`/`CLASS_END`），`tokens` 是该单元的子 token 列表（每项含词法类型如 `FIELD_ACCESS`/`FIELD_TYPE`/`NAME_FIELD`）。与 `method-tokens`（单方法 token）对称，适合类级词法分析、精确源码片段定位。

输出示例：

```json
{
  "class": "Lcom/ibm/icu/text/CharsetMatch;",
  "total": 19,
  "returned": 3,
  "tokens": [
    {"category": "PACKAGE", "tokens": [["PACKAGE_START", "package "], ["NAME_PACKAGE", "com.ibm.icu.text"], ["PACKAGE_END", ";\n"]]},
    {"category": "PROTOTYPE", "tokens": [["PROTOTYPE_ACCESS", "public class "], ["NAME_PROTOTYPE", "CharsetMatch", "com.ibm.icu.text"], ...]},
    {"category": "FIELD", "tokens": [["FIELD_ACCESS", "    private "], ["FIELD_TYPE", "String"], ["SPACE", " "], ["NAME_FIELD", "fCharsetName", "String", "..."], ["FIELD_END", ";\n"]]},
    ...
  ]
}
```

| 参数 | 说明 |
|------|------|
| `class_name`（位置） | 类名（Dalvik 格式） |
| `--limit` | 返回顶层 token 数量上限（默认全部；截断后仍返回 `total` 总数） |

`total` 是完整顶层 token 总数，`returned` 是实际返回数（受 `--limit` 限制）。顶层 token 类别：`PACKAGE`（包声明）/`PROTOTYPE`（类声明含 extends/implements）/`FIELD`（字段声明）/`METHOD`（方法）/`CLASS_END`（类结束）。子 token 的词法类型由 DAD 词法器定义（与 `method-tokens` 一致，如 `FIELD_ACCESS`/`NAME_FIELD`/`PROTOTYPE_TYPE`）。

> 底层 API：`DvClass(ClassDefItem, Analysis).process()` + `get_source_ext()`，返回 `list[(category, [subtokens])]`。子 token 中可能含 EncodedField 等对象引用，序列化时已转为字符串。

## 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `class` | string | 类名 |
| `method` | string | 方法名（仅方法反编译有此字段） |
| `descriptor` | string | 方法描述符 |
| `source` | string | 反编译后的 Java 源码 |
| `error` | string | 错误信息（反编译失败时） |

## 注意事项

1. **类名格式**：必须使用 Dalvik 格式，如 `Lcom/example/app/MainActivity;`
2. **反编译质量**：使用内置 DAD 反编译器，输出质量可能不如 JEB/Ghidra
3. **混淆代码**：如果 APK 使用了 ProGuard/R8 混淆，反编译结果可能难以阅读
4. **大型类**：反编译大型类可能耗时较长

## 使用场景

- 代码审计：阅读反编译后的源码，发现安全漏洞
- 算理密钥：发现硬编码的密钥、密码、URL
- 算法分析：分析加密/解密算法的实现
- 协险方法检测：识别使用不安全 API 的代码
- 动态分析辅助：确定 Frida Hook 的精确位置

## 与原始 CLI 的区别

原始 `androguard decompile` 命令会反编译所有类并输出到目录，
而 `androguard-skills decompile` 可以精确反编译单个类或方法，
输出 JSON 格式，更适合程序化调用。
