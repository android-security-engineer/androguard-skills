# APK 元信息补充

> DEX 文件名、签名文件名、应用显示名、APK 有效性、重复签名 ID 检测

## 命令

### `apk dex-names`

列出 APK 内所有 DEX 文件的名称（multidex 应用会有 `classes.dex`、`classes2.dex`...）。

```bash
androguard-skills apk dex-names --apk-path test.apk
```

**输出：**
```json
{
  "total": 1,
  "dex_names": ["classes.dex"]
}
```

`total > 1` 表示多 DEX 应用（方法数超 65535 触发 multidex）。

### `apk signature-names`

列出 APK 中所有签名相关文件名（如 `META-INF/CERT.RSA`、`META-INF/CERT.SF`）。

```bash
androguard-skills apk signature-names --apk-path test.apk
```

**输出：**
```json
{
  "total": 1,
  "signature_names": ["META-INF/13258F09.RSA"]
}
```

文件名前缀（如 `13258F09`）取自签名证书，可用于比对不同 APK 的签名主体。与 `apk signature`（返回签名内容详情）互补。

### `apk app-name`

获取应用显示名（`android:label` 资源反解后的字符串）。

```bash
# 默认 locale
androguard-skills apk app-name --apk-path test.apk

# 指定语言
androguard-skills apk app-name --locale zh --apk-path test.apk
```

**参数：**
- `--locale`：语言区域代码（如 `zh`、`en`），省略取默认

**输出（正常）：**
```json
{
  "app_name": "Editor",
  "locale": null
}
```

**输出（locale 无对应资源）：**
```json
{
  "app_name": "@7F080001",
  "locale": "zh",
  "note": "Resource ID not resolved for this locale, returned as-is"
}
```

`note` 字段出现时，`app_name` 是未解析的资源 ID（该 locale 无对应字符串资源），可用 `apk res-value` 反解默认值。

### `apk valid`

检查 APK 结构是否有效（ZIP 结构 + 必需文件完整性）。

```bash
androguard-skills apk valid --apk-path test.apk
```

**输出：**
```json
{
  "valid": true
}
```

`valid: false` 通常表示文件损坏或非标准 APK（可能是壳或恶意构造）。

### `apk duplicate-signatures`

检测 APK 是否存在重复的签名 ID（v2/v3 签名块中证书链重复）。

```bash
androguard-skills apk duplicate-signatures --apk-path test.apk
```

**输出：**
```json
{
  "has_duplicate": false
}
```

`has_duplicate: true` 可能是签名打包工具异常、多渠道打包残留或二次签名，可作为可疑特征进一步排查。

### `apk security-overview`

**APK 安全概览**——一键聚合安全审计关键信号，便于快速体检。与 `apk info`（基本信息，无安全维度）的区别：本命令聚合签名验证、危险权限、导出组件、manifest 安全标志、加固检测等安全信号于一处。

```bash
androguard-skills apk security-overview --apk-path test.apk
```

**输出：**
```json
{
  "package": "org.billthefarmer.editor",
  "app_name": "Editor",
  "version_name": "1.96",
  "min_sdk": "21",
  "target_sdk": "28",
  "effective_target_sdk": 28,
  "signature": {
    "is_signed": true,
    "is_signed_v1": true,
    "is_signed_v2": true,
    "is_signed_v3": true,
    "is_signed_v31": false,
    "is_valid_apk": true,
    "has_duplicate_signature_ids": false,
    "v1_verified": true
  },
  "manifest_flags": {
    "allowBackup": "true"
  },
  "permissions": {
    "total": 1,
    "dangerous": ["android.permission.WRITE_EXTERNAL_STORAGE"],
    "dangerous_count": 1,
    "other": []
  },
  "implied_permissions_count": 1,
  "components": {
    "activities": {"total": 3, "exported_explicit": ["...Editor", "...NewFile", "...OpenFile"], "exported_implicit": []},
    "services": {"total": 0, "exported_explicit": [], "exported_implicit": []},
    "receivers": {"total": 0, "exported_explicit": [], "exported_implicit": []},
    "providers": {"total": 1, "exported_explicit": [], "exported_implicit": []}
  },
  "axml_tampered": false,
  "packerwarning": false,
  "is_multidex": false,
  "is_wearable": false,
  "is_androidtv": false
}
```

| 字段 | 安全含义 |
|------|---------|
| `signature.v1_verified` | v1 签名密码学验证结果（`false` = 内容被篡改或签名无效） |
| `manifest_flags.debuggable` | 出现 `true` = 可调试（发布包严重风险） |
| `manifest_flags.allowBackup` | `true` = 允许备份（敏感数据可被提取） |
| `manifest_flags.usesCleartextTraffic` | `true` = 允许明文流量（中间人风险） |
| `permissions.dangerous` | 危险权限列表（protectionLevel=dangerous） |
| `components.*.exported_explicit` | 显式 `exported="true"` 的组件（攻击面） |
| `components.*.exported_implicit` | 无 exported 属性但有 intent-filter 的组件（默认导出，攻击面） |
| `axml_tampered`/`packerwarning` | AXML 篡改/加壳警告（混淆/加固信号） |

> 复用 `apk_verify_signature`（v1 密码学验证）、`get_details_permissions`（危险权限判定）、`get_attribute_value`（manifest 标志 + exported）、`AXMLPrinter`（加固检测）。组件导出分两类：`exported_explicit`（显式 `android:exported="true"`）和 `exported_implicit`（无属性但带 intent-filter，默认导出）。两者都是潜在攻击面。

### `apk native-libraries [--include-data]`

提取 APK 中打包的 **native 共享库**（`lib/<abi>/*.so`），按 ABI 分组。与 `apk libraries`（manifest `<uses-library>` 声明，Java 层依赖）和 `apk files`（全量文件）的区别：本命令聚焦实际打包进 APK 的 `.so` 文件，用于定位 native 层（JNI）实现。

```bash
androguard-skills apk native-libraries --apk-path test.apk

# 含 .so 二进制数据（base64，用于脱壳/转储到磁盘分析）
androguard-skills apk native-libraries --include-data --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--include-data` | 返回每个 .so 的 base64 数据（输出量大，谨慎用于大型 APK） |

**输出：**
```json
{
  "total": 7,
  "abis": {"arm64-v8a": 1, "armeabi-v7a": 1, "armeabi": 1, "mips": 1, "mips64": 1, "x86": 1, "x86_64": 1},
  "libraries": [
    {"path": "lib/arm64-v8a/libnative-lib.so", "name": "libnative-lib.so", "abi": "arm64-v8a", "size": 5808},
    ...
  ]
}
```

| 字段 | 说明 |
|------|------|
| `abis` | ABI → 该架构下 .so 数量（arm64-v8a/armeabi-v7a/x86/x86_64 等） |
| `libraries[].abi` | 库所属 ABI（`lib/<abi>/` 路径解析） |
| `libraries[].size` | .so 文件字节数 |
| `libraries[].data_base64` | 仅 `--include-data` 时返回，base64 编码的 .so 数据 |

> 底层 API：`APK.get_files()` 遍历 + 过滤 `.so` 后缀 + `APK.get_file(fn)` 取数据。纯 Java 应用（如 editor.apk）返回 `total:0`。配合 `analysis security-hotspots` 的 `native_methods`（JNI 声明方法）定位需 so 层分析的方法。

### `apk application-flags`

**Manifest `<application>` 安全属性完整审计**——对每个安全相关属性读取显式值、按 Android 官方规则推断默认值（依赖 targetSdkVersion）、给出风险评级与说明。

与 `apk security-overview`（聚合多维度信号，`manifest_flags` 仅列非 None 值）的区别：本命令聚焦 `<application>` 标签的**全部**安全属性，**对 None 值推断默认值并评级**——例如 `debuggable` 未设置时默认 `false`（safe），`usesCleartextTraffic` 未设置时按 targetSdk 推断（≥28 默认 false，<28 默认 true）。这是 manifest 安全审计的核心入口。

```bash
androguard-skills apk application-flags --apk-path test.apk
```

**输出：**
```json
{
  "effective_target_sdk": 22,
  "risk_summary": {"critical": 1, "warning": 4, "info": 3, "safe": 2},
  "flags": [
    {"name": "debuggable", "value": "true", "effective": true, "default": false, "risk": "critical", "desc": "允许调试应用（可附加 jdb 调试器，绕过保护读取内存/数据）"},
    {"name": "allowBackup", "value": "true", "effective": true, "default": true, "risk": "warning", "desc": "允许 adb backup 导出应用数据"},
    {"name": "usesCleartextTraffic", "value": null, "effective": true, "default": true, "risk": "warning", "desc": "允许 HTTP 明文流量（中间人可窃听/篡改）"},
    ...
  ]
}
```

| 属性 | 默认值规则 | 风险 |
|------|-----------|------|
| `debuggable` | 默认 `false`；`true` 为 **critical**（可 jdb 调试） | critical |
| `allowBackup` | 默认 `true`；允许 `adb backup` 提取数据 | warning |
| `usesCleartextTraffic` | targetSdk≥28 默认 `false`；<28 默认 `true`（明文流量） | warning |
| `networkSecurityConfig` | 未设置用系统默认，明文策略取决于 usesCleartextTraffic | warning/info |
| `testOnly` | 默认 `false`；`true` 为 **critical**（仅测试构建） | critical |
| `requestLegacyExternalStorage` | 默认 `false`；`true` 绕过 Scoped Storage | warning |
| `extractNativeLibs` | minSdk≥23 倾向 `false`；`true` 增加可替换风险 | info |
| `directBootAware` | 默认 `false`（用户解锁前是否运行） | info |
| `dataExtractionRules` | Android 12+ 备份/迁移规则 | info |
| `fullBackupContent` | 未设置则全量备份（取决于 allowBackup） | warning/info |

> 底层 API：`APK.get_attribute_value("application", attr)` 逐属性读取 + `get_effective_target_sdk_version()` 用于默认值推断。`effective` 是推断后的实际生效值，`default` 是 Android 官方默认。InsecureBankv2（targetSdk=22）典型输出 1 critical（debuggable=true）+ 4 warning，准确反映其不安全配置。

## 使用场景

- **multidex 检测**：`dex-names` 的 `total > 1` 判断是否多 DEX
- **签名一致性比对**：`signature-names` 的文件名前缀跨 APK 比对签名主体
- **本地化分析**：`app-name --locale` 查看不同语言下的应用名（检测伪装应用）
- **完整性校验**：`valid` + `duplicate-signatures` 双重检查 APK 是否被篡改/加壳

## 相关命令

- [`apk info`](apk-info.md) — APK 基本信息（包名/版本/SDK）
- [`apk signature`](apk-signature.md) — 签名内容详情
- [`apk res-value`](apk-manifest-tree.md) — 资源 ID 反解（配合 app-name）
- [`apk signing-versions`](apk-signing-advanced.md) — 签名方案检测
