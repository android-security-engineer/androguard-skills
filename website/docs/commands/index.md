# 命令索引

> 📋 **219 个命令**，分属 10 个组 + 3 个顶层命令。所有命令输出 JSON。

## 按组浏览

| 组 | 命令数 | 说明 | 进入 |
|----|--------|------|------|
| 🔝 顶层 | 3 | `load` / `load-dex` / `unload` — 加载与卸载 | [顶层命令](#顶层命令) |
| ⚙️ `daemon` | 3 | daemon 进程管理 | [daemon 组](./daemon/) |
| 📦 `apk` | 56 | APK 信息、签名、组件、Manifest、攻击面 | [apk 组](./apk/) |
| 🧩 `dex` | 44 | DEX 类/方法/字段、字节码、常量池 | [dex 组](./dex/) |
| 🔍 `analysis` | 69 | 交叉引用、调用图、可达性、安全审计 | [analysis 组](./analysis/) |
| 🧠 `decompile` | 6 | 反编译（源码/AST/token） | [decompile 组](./decompile/) |
| 🧪 `pentest` | 2 | Frida 动态分析 | [pentest 组](./pentest/) |
| 🎨 `resources` | 20 | ARSC 资源解析 | [resources 组](./resources/) |
| 📊 `visualize` | 3 | CFG 可视化导出 | [visualize 组](./visualize/) |
| 🔧 `util` | 5 | 文件检测、权限数据、格式转换 | [util 组](./util/) |
| 🗂️ `session` | 8 | 多 APK/DEX 关联分析 | [session 组](./session/) |

## 顶层命令

| 命令 | 说明 | 文档 |
|------|------|------|
| `load <apk>` | 加载 APK（daemon 模式下缓存） | [load](./load) |
| `load-dex <dex>` | 加载独立 DEX 文件（不走 APK 路径） | [load-dex](./load-dex) |
| `unload` | 卸载对象 + `malloc_trim` 归还内存 | [unload](./unload) |

## 快速查找

### APK 维度

<details>
<summary>展开 apk 组 56 个命令</summary>

| 命令 | 简述 |
|------|------|
| `apk info` | 基本信息 |
| `apk permissions` | 权限列表 |
| `apk activities` / `services` / `receivers` / `providers` | 四大组件 |
| `apk intent-filters` | Intent Filter |
| `apk signature` | 签名信息 |
| `apk files` / `apk files-info` / `apk files-types` / `apk files-crc32` | 文件列表与详情 |
| `apk manifest` / `manifest-attrs` / `manifest-attr` / `manifest-tags` / `manifest-tree` / `manifest-axml` | Manifest |
| `apk features` / `libraries` / `icon` | 特性/库/图标 |
| `apk file <name>` | 提取文件内容 |
| `apk verify` / `verify-signature` / `signing-block` / `signing-versions` | 完整性与签名方案 |
| `apk certificate` / `certificates-scheme` / `certificates-der` / `cert-names` | 证书 |
| `apk public-keys` / `fingerprint` / `signature-files` / `signature-names` | 公钥与签名文件 |
| `apk axml` / `fingerprint` | AXML 解码 |
| `apk declared-permissions` / `requested-permissions` / `details-permissions` / `sdk-versions` / `main-activities` / `device-features` | 权限与 SDK 详情 |
| `apk dex-data` / `dex-names` / `raw` | DEX 与原始字节 |
| `apk app-name` / `valid` / `duplicate-signatures` / `security-overview` | 元信息 |
| `apk native-libraries` | native 库 |
| `apk application-flags` | application 安全属性 |
| `apk component-details` / `attack-surface` / `deeplinks` | 组件与攻击面 |
| `apk security-report` | 一键全量安全报告 |
| `apk res-value` / `find-tags-xml` | 资源反解与标签查找 |

</details>

### DEX 维度

<details>
<summary>展开 dex 组 44 个命令</summary>

| 命令 | 简述 |
|------|------|
| `dex classes` / `class-names` / `class` / `class-meta` / `class-data` | 类 |
| `dex methods` / `fields` / `strings` / `strings-table` / `regex-strings` | 基础列表 |
| `dex header` / `version` / `stats` / `hierarchy` / `hidden-api` | 头与统计 |
| `dex disassemble` / `method-instructions` / `method-instructions-idx` / `method-code` / `method-info` | 字节码 |
| `dex encoded-fields` / `encoded-methods` / `encoded-method` / `encoded-method-descriptor` / `encoded-fields-class` / `encoded-methods-class` / `encoded-method-by-idx` / `encoded-field-by-name` / `encoded-field-descriptor` / `encoded-method-class-method` / `field-init-value` / `static-values` | 底层 Encoded 表 |
| `dex method-ids` / `method-id-by-name` / `field-id-by-name` / `fields-id` / `proto-ids` / `type-ids` | 常量池表 |
| `dex items` / `lens` / `class-manager` / `cm-lookup` / `debug-info` / `annotations` | 底层结构 |

</details>

### 静态分析维度

<details>
<summary>展开 analysis 组 69 个命令</summary>

| 类别 | 命令 |
|------|------|
| 交叉引用 | `xrefs-from` / `xrefs-to` / `method-xrefs` / `method-xrefs-detail` / `field-xrefs` / `field-xrefs-detail` |
| 搜索 | `find-classes` / `find-methods` / `find-strings` / `find-fields` / `find-classes-advanced` / `find-methods-advanced` / `find-fields-advanced` |
| 内外部 | `internal-classes` / `external-classes` / `internal-methods` / `external-methods` |
| 类详情 | `class-exists` / `class-detail` / `class-hierarchy-info` / `class-xref-new-instance` / `class-xref-const-class` / `class-fields` / `class-fields-xref` |
| 方法详情 | `method-analysis` / `method-detail` / `method-summary` / `method-api-info` / `method-basic-blocks` / `method-exceptions` / `method-block-instructions` / `method-switch-payloads` / `get-method` |
| 可达性 | `method-reachable` / `method-callers` / `taint-path` |
| 调用图 | `callgraph` / `call-graph` / `call-graph-filtered` |
| 权限与 API | `permission-usage` / `permissions` / `permissions-map` / `api-usage` / `android-api-usage` / `method-api-info` |
| 字段分析 | `field-analysis` / `class-fields` / `class-fields-xref` |
| 字符串分析 | `strings-analysis` / `string-info` / `strings-overwritten` |
| 安全审计 | `security-hotspots` / `hardcoded-secrets` / `native-methods` / `crypto-usage` / `reflection-targets` / `url-endpoints` / `webview-security` / `ssl-safety` / `insecure-storage` / `sql-injection` / `pending-intent` / `privacy-sinks` / `telephony-sms` / `dynamic-code` / `persistence` / `weak-random` / `broadcast-safety` / `provider-safety` / `anti-analysis` / `network-security` / `obfuscation-metrics` |
| 攻击面 | `apk attack-surface`（在 apk 组）/ `apk security-report`（在 apk 组） |

</details>

## 公共参数

### `--apk-path`

`apk` / `dex` / `analysis` / `resources` / `visualize` 组的命令支持 `--apk-path`，或环境变量 `ANDROGUARD_APK_PATH`。daemon 模式下若已 `load` 则可省略。

### `--limit`

许多列表类命令支持 `--limit N` 限制返回条数。

### 类名/方法名参数

类名用 Dalvik 描述符（`Lcom/example/Foo;`，带分号），见 [类名与描述符](../guide/class-descriptors)。

## 约定

- 所有命令的输出都是 JSON，失败返回 `{"error": "..."}`。
- 命令名中连字符 `-` 在对应 API 方法名中是下划线 `_`。
- 二进制字段以 base64 编码出现。
