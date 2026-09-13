# APK 指纹与 AXML 加固检测

封装第五轮新增的 APK 能力：签名公钥指纹计算、AndroidManifest.xml 的 AXML 结构分析（含加固检测）。

## 命令

### `apk fingerprint`

计算 APK 签名公钥的 SHA-256 指纹。从指定签名方案（v2/v3/v31）的签名块中提取公钥，分别计算指纹。

```bash
androguard-skills apk fingerprint --apk-path test.apk
androguard-skills apk fingerprint --scheme v2 --apk-path test.apk
```

**参数：**
- `--scheme`：签名方案（`v2`/`v3`/`v31`，默认 `v3`），用于读取公钥来源

**输出：**
```json
{
  "scheme": "v3",
  "total": 1,
  "fingerprints": [
    {
      "algorithm": "rsa",
      "fingerprint_hex": "e407b8072e488e4cbe8e128702374a2223cd1fbb01538c15231a1bba5440d5bb",
      "fingerprint_base64": "5Ae4By5Ijky+jhKHAjdKIiPNH7sBU4wVIxobulRA1bs="
    }
  ]
}
```

指纹用于唯一标识签名证书对应的公钥，常用于比对不同 APK 是否使用同一签名。

> 底层 API：`androguard.util.calculate_fingerprint(public_key_info)`，公钥来自 `APK.get_public_keys_v2/v3/v31()`。

### `apk manifest-axml`

分析 `AndroidManifest.xml` 的 AXML 二进制结构，输出加固检测、完整 XML 文本和根标签属性。

```bash
androguard-skills apk manifest-axml --apk-path test.apk
```

**输出：**
```json
{
  "is_valid": true,
  "is_packed": false,
  "xml": "<manifest xmlns:android=\"...\" ...>",
  "xml_size": 3075,
  "root_tag": "manifest",
  "root_attributes": {
    "versionCode": "196",
    "versionName": "1.96",
    "package": "org.billthefarmer.editor",
    ...
  }
}
```

**字段说明：**
- `is_valid`：AXML 是否合法可解析
- `is_packed`：**是否被加固/加壳**。加固后的 APK 其 manifest 的 AXML 结构常被破坏或异常，此字段为 `true` 时需警惕
- `axml_tampered`：AXML 是否被篡改（AXMLParser 层检测，区别于 is_packed 的加固检测）
- `packerwarning`：加固告警标志（解析过程发现可疑特征）
- `xml`：解析还原后的标准 XML 文本
- `root_tag` / `root_attributes`：根标签名（通常为 `manifest`）及其属性（命名空间已简化为短名）

> 底层 API：`androguard.core.axml.AXMLPrinter`（`is_valid()`/`is_packed()`/`get_xml_obj()`）。

### `apk axml <filename>`

解析 APK 内**任意二进制 AXML 文件**为可读 XML。与 `manifest-axml`（仅 AndroidManifest.xml）的区别：本命令可解析 `res/layout/*.xml`（布局）、`res/xml/*.xml`（preferences 等配置）、`res/drawable*.xml`（vector/shape drawable）等任意 AXML 文件。APK 内这些 XML 均为二进制 AXML 格式（无法直接 `cat`），需 AXMLPrinter 解码为可读文本，用于 UI 结构分析、drawable 内容查看、配置文件审计。

```bash
# 解析布局文件
androguard-skills apk axml "res/layout/main.xml" --apk-path test.apk

# 解析 vector drawable
androguard-skills apk axml "res/drawable/ic_arrow.xml" --apk-path test.apk

# 紧凑输出（不缩进）
androguard-skills apk axml "res/xml/settings.xml" --no-pretty --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `filename`（位置参数） | APK 内文件路径（如 `res/layout/main.xml`） |
| `--no-pretty` | 禁用美化（紧凑 XML，减小体积） |

**输出：**
```json
{
  "filename": "res/drawable/ic_arrow.xml",
  "raw_size": 688,
  "is_valid": true,
  "is_packed": false,
  "packerwarning": false,
  "xml": "<vector xmlns:android=\"...\" android:height=\"24.0dip\" ...>\n  <path android:fillColor=\"#FF000000\" android:pathData=\"M18,2h-8...\"/>\n</vector>",
  "xml_size": 404,
  "root_tag": "vector",
  "root_attributes": {"height": "24.000000dip", "width": "24.000000dip", "viewportWidth": "24.000000", "viewportHeight": "24.000000"},
  "children_count": 1,
  "children_tags": ["path"]
}
```

**字段说明：**
- `is_valid`/`is_packed`/`packerwarning`：AXML 合法性、加固检测、加固告警标志
- `xml`：解码还原后的标准 XML 文本（可直接阅读或喂给 XML 解析器）
- `root_tag`/`root_attributes`：根标签名及属性（命名空间已简化）
- `children_count`/`children_tags`：直接子标签数量及去重标签名（了解文件结构规模，如 layout 的控件种类）

> 底层 API：`AXMLPrinter(apk.get_file(filename))`，`get_xml(pretty=True)` 返回 XML 字节，`get_xml_obj()` 返回 lxml Element。先用 `apk files` 或 `apk file` 查看文件列表/提取原始字节，再用本命令解码二进制 XML。

## 相关命令

- [`apk signature`](apk-signature.md) — 签名验证与证书
- [`apk signing-advanced`](apk-signing-advanced.md) — 签名方案/证书/公钥详情
- [`manifest-attrs`](manifest-attrs.md) — manifest 属性批量提取
