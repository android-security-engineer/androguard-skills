# APK Manifest 标签树与证书名规范化

封装第八轮新增的 manifest 结构概览、跨 XML 文件标签查找、证书名规范化能力。

## 命令

### `apk manifest-tree`

获取 `AndroidManifest.xml` 的**标签树统计**——遍历整棵 XML 树，统计每种标签的数量和属性集合。

```bash
androguard-skills apk manifest-tree --apk-path test.apk
```

**输出：**
```json
{
  "root_tag": "manifest",
  "total_tags": 37,
  "distinct_tags": 11,
  "tags": [
    {"tag": "action", "count": 12, "attributes": ["name"]},
    {"tag": "intent-filter", "count": 6, "attributes": ["scheme"]},
    {"tag": "activity", "count": 3, "attributes": ["documentLaunchMode", "exported", "label", "name"]},
    ...
  ]
}
```

**字段说明：**
- `total_tags`：所有标签总数（含嵌套）
- `distinct_tags`：不同标签种类数
- `tags`：按出现次数降序排列，每个标签含 `count` 和 `attributes`（该标签用到的所有属性名，命名空间已简化）

**与 `manifest-tags` 的区别：** `manifest-tags` 按指定标签名查具体实例；`manifest-tree` 给出整体结构概览（哪些标签、各多少个、用什么属性），用于快速了解 manifest 复杂度。

### `apk find-tags-xml`

从 APK 中**指定 XML 文件**查找标签（不限于 manifest，可查任意 XML）。

```bash
# 查 manifest 中所有 uses-permission
androguard-skills apk find-tags-xml AndroidManifest.xml uses-permission --apk-path test.apk

# 带 filter 过滤
androguard-skills apk find-tags-xml AndroidManifest.xml action \
  --filter "name=android.intent.action.MAIN" --apk-path test.apk
```

**参数：**
- `xml_name`：APK 内的 XML 文件名（如 `AndroidManifest.xml`、`res/xml/backup.xml`）
- `tag_name`：要查找的标签名
- `--filter`：属性过滤条件，`key=value` 形式，可重复

**输出：**
```json
{
  "xml_name": "AndroidManifest.xml",
  "tag_name": "action",
  "filter": {"name": "android.intent.action.MAIN"},
  "total": 1,
  "results": [
    {"tag": "action", "attributes": {"name": "android.intent.action.MAIN"}}
  ]
}
```

### `apk cert-names`

获取签名证书主题（subject）和颁发者（issuer）的**规范化名称**，便于跨 APK 比对签名是否一致。

```bash
androguard-skills apk cert-names --apk-path test.apk
androguard-skills apk cert-names --scheme v2 --apk-path test.apk
androguard-skills apk cert-names --no-android --apk-path test.apk
```

**参数：**
- `--scheme`：签名方案（`v1`/`v2`/`v3`/`v31`，默认 `v3`）
- `--no-android`：使用非 Android 风格规范化（默认 Android 风格）

**输出：**
```json
{
  "scheme": "v3",
  "android": true,
  "total": 1,
  "certificates": [
    {
      "subject_canonical": "cn=fdroid,ou=fdroid,o=fdroid.org,l=org,st=org,c=uk",
      "issuer_canonical": "cn=fdroid,ou=fdroid,o=fdroid.org,l=org,st=org,c=uk",
      "subject_comparison": [[["cn", "fdroid"]], [["ou", "fdroid"]], ...],
      "issuer_comparison": [[["cn", "fdroid"]], ...]
    }
  ]
}
```

**字段说明：**
- `subject_canonical` / `issuer_canonical`：规范化名（`cn=...,ou=...` 格式），可直接字符串比对
- `subject_comparison` / `issuer_comparison`：结构化名（`[[[key, value], ...], ...]`，按 RDN 序）

**用途：** 比对两个 APK 是否同一签名——`subject_canonical` 字符串相等即同一证书主体。

### `apk res-value`

将资源 ID（如 `@7F080001`）解析为字面值。AndroidManifest 中大量属性引用资源 ID（`android:label="@7F080001"`），此命令把这类 ID 反解为实际值，还原被资源引用遮挡的真实内容。

```bash
androguard-skills apk res-value @7F080001 --apk-path test.apk
# 无 @ 前缀自动补
androguard-skills apk res-value 7F040008 --apk-path test.apk
```

**输出（字符串值）：**
```json
{
  "input": "@7F080001",
  "normalized": "@7F080001",
  "value": "Editor",
  "value_type": "string"
}
```

**输出（多配置值，如 theme 引用多个变体）：**
```json
{
  "input": "@7F090003",
  "normalized": "@7F090003",
  "value": [
    {"config": "<ARSCResTableConfig ...>", "value": "res/iY.xml"},
    {"config": "<ARSCResTableConfig ...>", "value": "res/yf.xml"},
    ...
  ],
  "value_type": "configs"
}
```

**字段说明：**
- `value_type`：`string`（单值）或 `configs`（多配置变体，每项含 `config` 和 `value`）
- `note`：资源未解析时标注 `Resource ID not resolved, returned as-is`，`value` 回退为原 ID

**用途：** 配合 `manifest-attrs`/`manifest-tree` 还原 manifest 真实内容——先查到属性值是 `@7F080001`，再用 `res-value` 反解为 `"Editor"`。

## 相关命令

- [`manifest-attrs`](manifest-attrs.md) — manifest 属性批量提取
- [`resources id`](resources.md) — 资源 ID 双向查询（ID↔名称）
- [`resources get-string`](resources.md) — 精确取单个字符串值
- [`apk-axml-packing`](apk-axml-packing.md) — AXML 加固检测
- [`apk-signing-advanced`](apk-signing-advanced.md) — 签名方案/证书/公钥详情
- [`apk-fingerprint`](apk-axml-packing.md) — 公钥指纹
