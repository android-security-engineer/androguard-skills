# 🔍 analysis · 静态分析

> 静态分析与安全审计：交叉引用、调用图、可达性、污点路径、19 域漏洞审计。共 69 个命令。

共 **69** 个命令。

## 命令列表

| 命令 | 说明 |
|------|------|
| [`android-api-usage`](./android-api-usage) | List all Android platform APIs used by the APK (batch) |
| [`anti-analysis`](./anti-analysis) | Detect anti-analysis/hardening (root/emulator/debugger/Frida/Xposed detection, string+API dual scan) |
| [`api-usage`](./api-usage) | Get Android API usage |
| [`broadcast-safety`](./broadcast-safety) | Audit broadcast send/receive safety (unprotected broadcasts/dynamic receivers/sticky broadcasts) |
| [`call-graph`](./call-graph) | Get the full call graph (nodes + edges) |
| [`call-graph-filtered`](./call-graph-filtered) | Get a filtered sub call-graph (by class/method/descriptor/accessflags) |
| [`callgraph`](./callgraph) | Generate and export call graph |
| [`class-detail`](./class-detail) | Get comprehensive class info (methods/inheritance/xref stats/vm_class type) |
| [`class-exists`](./class-exists) | Check if a class exists in analysis (boolean) |
| [`class-fields`](./class-fields) | List all fields of a class with xref read/write counts |
| [`class-fields-xref`](./class-fields-xref) | List all fields of a class with full read/write xref sources (which methods) |
| [`class-hierarchy-info`](./class-hierarchy-info) | Get class inheritance info (extends / implements) |
| [`class-xref-const-class`](./class-xref-const-class) | Get const-class xrefs of a class (where the class literal is referenced) |
| [`class-xref-new-instance`](./class-xref-new-instance) | Get new-instance xrefs of a class (where it is instantiated) |
| [`crypto-usage`](./crypto-usage) | Aggregate crypto API usage, resolve algorithm strings, flag weak crypto (ECB/DES/MD5/SHA1/RC4) |
| [`dynamic-code`](./dynamic-code) | Audit dynamic code loading (DexClassLoader/native libs/reflection, unpacking/malicious payload) |
| [`external-classes`](./external-classes) | List external (dependency) classes |
| [`external-methods`](./external-methods) | List external (dependency) methods |
| [`field-analysis`](./field-analysis) | Get full field analysis (with read/write xref details) |
| [`field-xrefs`](./field-xrefs) | Find cross-references for a specific field |
| [`field-xrefs-detail`](./field-xrefs-detail) | Get field read/write refs with per-access offset (not deduped) |
| [`find-classes`](./find-classes) | Search classes by regex pattern |
| [`find-classes-advanced`](./find-classes-advanced) | Multi-dimensional regex class search: name regex + exclude-external (native find_classes) |
| [`find-fields`](./find-fields) | Search fields by regex pattern |
| [`find-fields-advanced`](./find-fields-advanced) | Multi-dimensional regex field search (native find_fields) |
| [`find-methods`](./find-methods) | Search methods by regex pattern |
| [`find-methods-advanced`](./find-methods-advanced) | Multi-dimensional regex method search: class x method x descriptor x accessflags (native find_methods) |
| [`find-strings`](./find-strings) | Search strings by regex pattern |
| [`get-method`](./get-method) | Get underlying EncodedMethod metadata by class+method+descriptor |
| [`hardcoded-secrets`](./hardcoded-secrets) | Scan static field values for hardcoded secrets (API keys/tokens/URLs/private keys) |
| [`insecure-storage`](./insecure-storage) | Audit insecure data storage (external storage/world-readable modes/plaintext prefs+db, OWASP M9) |
| [`internal-classes`](./internal-classes) | List internal (app) classes |
| [`internal-methods`](./internal-methods) | List internal (app) methods |
| [`method-analysis`](./method-analysis) | Get method analysis by class+method+descriptor (with full xref) |
| [`method-api-info`](./method-api-info) | Get method API/permission annotation (is_android_api/domain_flag/restriction_flag/apilist) |
| [`method-basic-blocks`](./method-basic-blocks) | Get basic blocks (CFG nodes) of a method |
| [`method-block-instructions`](./method-block-instructions) | Disassemble method instructions organized by basic block (CFG node-level view) |
| [`method-callers`](./method-callers) | Reverse reachability: callers that can reach a given method (recursive xref_from expansion) |
| [`method-detail`](./method-detail) | Get comprehensive method info (full_name/access/length/xref stats/bb count) |
| [`method-exceptions`](./method-exceptions) | Get try/catch exception table for a method |
| [`method-reachable`](./method-reachable) | Reachability analysis: methods reachable from a given method (recursive xref_to expansion) |
| [`method-summary`](./method-summary) | Aggregate method overview (info + 6 xref summaries + CFG/exception counts + source) |
| [`method-switch-payloads`](./method-switch-payloads) | Decode switch branch tables (case-&gt;target) and fill-array-data payloads in a method |
| [`method-xrefs`](./method-xrefs) | Find cross-references for a specific method |
| [`method-xrefs-detail`](./method-xrefs-detail) | Get full method-level xref lists (from/to/read/write/new_instance/const_class) |
| [`native-methods`](./native-methods) | Enumerate all native (JNI) methods with declaring class and callers |
| [`network-security`](./network-security) | Audit network security config (cleartext URLs/cert pinning/SSL context/HTTP clients) |
| [`obfuscation-metrics`](./obfuscation-metrics) | Quantify obfuscation/hardening (class-name length distribution/reflection density/string coverage) |
| [`pending-intent`](./pending-intent) | Audit PendingIntent mutability (missing FLAG_IMMUTABLE + Intent redirection surface) |
| [`permission-usage`](./permission-usage) | Trace usage of a specific permission |
| [`permissions`](./permissions) | List API methods that require permissions (batch, by API level) |
| [`permissions-map`](./permissions-map) | Get complete permissions mapping from analysis |
| [`persistence`](./persistence) | Audit persistence/background residency (device admin/accessibility/scheduled jobs/foreground service) |
| [`privacy-sinks`](./privacy-sinks) | Audit privacy data collection (device IDs/location/contacts/accounts/clipboard/camera-mic, OWASP M6) |
| [`provider-safety`](./provider-safety) | Audit ContentProvider safety (openFile path traversal/URI permission grants/cross-app access) |
| [`reflection-targets`](./reflection-targets) | Resolve reflection call targets (Class.forName/getMethod string args) for deobfuscation |
| [`security-hotspots`](./security-hotspots) | Scan all methods for security-sensitive calls (reflection/crypto/exec/native/etc.) |
| [`sql-injection`](./sql-injection) | Audit SQL injection surface (rawQuery/execSQL/query execution points, OWASP M7) |
| [`ssl-safety`](./ssl-safety) | Detect SSL/TLS validation bypass (insecure TrustManager/HostnameVerifier + bypass calls, MITM audit) |
| [`string-info`](./string-info) | Get single string analysis (orig_value/current_value/is_overwritten + xrefs) |
| [`strings-analysis`](./strings-analysis) | Get all string analyses (with reference locations) |
| [`strings-overwritten`](./strings-overwritten) | Get overwritten strings (is_overwritten / get_orig_value) |
| [`taint-path`](./taint-path) | Find a forward call path from a source method to a sink method (source-&gt;sink chain) |
| [`telephony-sms`](./telephony-sms) | Audit telephony/SMS abuse (send/read SMS, dial, SMS interception, call monitoring) |
| [`url-endpoints`](./url-endpoints) | Extract URL/host/IP network endpoints from the string pool with referencing methods |
| [`weak-random`](./weak-random) | Audit insecure randomness (java.util.Random/Math.random/fixed seed vs SecureRandom, OWASP M10) |
| [`webview-security`](./webview-security) | Audit WebView security configuration (JS bridge/file access/JS/debug risky settings + findings) |
| [`xrefs-from`](./xrefs-from) | Find what references this class (XrefFrom) |
| [`xrefs-to`](./xrefs-to) | Find what this class references (XrefTo) |

## 用法示例

```bash
androguard-skills analysis --help    # 查看本组所有命令
androguard-skills analysis <子命令> --help
```

- [命令索引](../)
