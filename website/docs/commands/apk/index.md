# 📦 apk · APK 信息

> APK 维度的全部信息：基础元数据、签名（v1/v2/v3/v31）、四大组件、Manifest、文件、native 库、组件暴露面、攻击面、一键安全报告。共 56 个命令。

共 **56** 个命令。

## 命令列表

| 命令 | 说明 |
|------|------|
| [`activities`](./activities) | Get APK activities |
| [`app-name`](./app-name) | Get the app display name (resolved android:label) |
| [`application-flags`](./application-flags) | Audit &lt;application&gt; security flags (debuggable/allowBackup/cleartext/etc) with default inference &amp; risk rating |
| [`attack-surface`](./attack-surface) | Attack surface: cross-reference exported components with forward-reachable dangerous sinks |
| [`axml`](./axml) | Decode any binary AXML file in APK to readable XML (layouts/drawables/config) |
| [`cert-names`](./cert-names) | Get canonical/normalized names of signing certificate subject and issuer |
| [`certificate`](./certificate) | Get APK signing certificate details |
| [`certificates-der`](./certificates-der) | Get certificate DER bytes (base64) by signing scheme |
| [`certificates-scheme`](./certificates-scheme) | Get certificates by signing scheme (v1/v2/v3/v31) |
| [`component-details`](./component-details) | List all components (Activity/Service/Receiver/Provider) with security attrs &amp; exposure risk |
| [`declared-permissions`](./declared-permissions) | Get permissions declared (custom &lt;permission&gt; tags) by the APK |
| [`deeplinks`](./deeplinks) | Enumerate deep links (intent-filter/data: scheme/host/path + component + BROWSABLE) |
| [`details-permissions`](./details-permissions) | Get requested permissions with details (protection_level/label/description) |
| [`device-features`](./device-features) | Get device feature flags (TV/Wearable/Leanback/Multidex) |
| [`dex-data`](./dex-data) | Extract DEX binary data (base64 encoded) |
| [`dex-names`](./dex-names) | List all DEX file names in the APK (multidex aware) |
| [`duplicate-signatures`](./duplicate-signatures) | Check for duplicate signature IDs (suspicious packing artifact) |
| [`features`](./features) | Get uses-feature list |
| [`file`](./file) | Extract a file from APK (content returned as base64) |
| [`files`](./files) | Get APK file listing |
| [`files-crc32`](./files-crc32) | Get CRC32 checksums of all APK files |
| [`files-info`](./files-info) | Get detailed file information (name/type/CRC32) |
| [`files-types`](./files-types) | Get MIME/file type of all APK entries |
| [`find-tags-xml`](./find-tags-xml) | Find tags in a specific XML file inside the APK |
| [`fingerprint`](./fingerprint) | Get SHA-256 fingerprints of signing public keys |
| [`icon`](./icon) | Get app icon information |
| [`info`](./info) | Get APK basic information |
| [`intent-filters`](./intent-filters) | Get intent filters for a specific component |
| [`libraries`](./libraries) | Get uses-library list |
| [`main-activities`](./main-activities) | Get main activity (with aliases) |
| [`manifest`](./manifest) | Get AndroidManifest.xml content |
| [`manifest-attr`](./manifest-attr) | Extract a single manifest attribute value (first match) |
| [`manifest-attrs`](./manifest-attrs) | Batch extract attribute values from AndroidManifest tags |
| [`manifest-axml`](./manifest-axml) | Analyze AndroidManifest.xml AXML structure (packing detection / root tag attrs) |
| [`manifest-tags`](./manifest-tags) | Find manifest tags by attribute filter |
| [`manifest-tree`](./manifest-tree) | Get AndroidManifest.xml tag tree statistics (tag counts + attributes) |
| [`native-libraries`](./native-libraries) | List native libraries (lib/&lt;abi&gt;/*.so) grouped by ABI |
| [`permissions`](./permissions) | Get APK permissions |
| [`providers`](./providers) | Get APK content providers |
| [`public-keys`](./public-keys) | Get signing public keys by scheme |
| [`raw`](./raw) | Extract the whole APK raw bytes (base64 encoded) |
| [`receivers`](./receivers) | Get APK broadcast receivers |
| [`requested-permissions`](./requested-permissions) | Get requested permissions grouped by source (AOSP/third-party/implied) |
| [`res-value`](./res-value) | Resolve a resource ID (e.g. @7F080001) to its literal value |
| [`sdk-versions`](./sdk-versions) | Get SDK version info (min/max/target/effective_target) |
| [`security-overview`](./security-overview) | Security audit overview (signatures/permissions/components/manifest flags/packing) |
| [`security-report`](./security-report) | One-shot full security report: aggregate all audits + composite risk score (audit suite closure) |
| [`services`](./services) | Get APK services |
| [`signature`](./signature) | Get APK signature information |
| [`signature-files`](./signature-files) | Get APK signature file info (name + raw signature base64) |
| [`signature-names`](./signature-names) | List all signature file names (e.g. CERT.RSA, CERT.SF) |
| [`signing-block`](./signing-block) | Get v2/v3 signing block details |
| [`signing-versions`](./signing-versions) | Detect APK signing schemes (v1/v2/v3/v3.1) |
| [`valid`](./valid) | Check if the APK is structurally valid |
| [`verify`](./verify) | Verify APK integrity and signature status |
| [`verify-signature`](./verify-signature) | Cryptographically verify APK signatures (signer info vs .SF file) |

## 用法示例

```bash
androguard-skills apk --help    # 查看本组所有命令
androguard-skills apk <子命令> --help
```

- [命令索引](../)
