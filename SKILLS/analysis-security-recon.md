# 安全侦察聚合命令

一组**跨方法聚合 / 跨对象关联**分析命令。区别于单方法查询（`method-detail`/`method-summary`）和单类查询（`class-detail`），本组命令一次扫描全量内部方法或全量字符串，按安全语义归类聚合，直接产出可审计的清单——JNI 边界、加密用法、反射目标、网络端点、源→汇路径、深链接攻击面，以及针对具体漏洞类的审计（WebView/SSL/存储/SQL 注入/PendingIntent）。

**A 组·侦察聚合（第三十二轮）：**

| 命令 | 维度 | 回答的问题 |
|------|------|-----------|
| `analysis native-methods` | JNI 边界 | 哪些方法进入 native（.so），谁调用它们 |
| `analysis crypto-usage` | 加密 | 用了什么算法/密钥，哪些是弱加密 |
| `analysis reflection-targets` | 反射 | 反射调用了什么，能否静态还原目标 |
| `analysis url-endpoints` | 网络 | APK 里硬编码了哪些 URL/主机/IP |
| `analysis taint-path` | 污点 | 某入口能否经某条调用链到达某危险 sink |
| `apk deeplinks` | 攻击面 | 有哪些深链接，哪些可被浏览器直接触达 |

**B 组·具体漏洞类审计（第三十三轮，OWASP Mobile 对齐）：** 统一模式——遍历全量内部方法 `get_xref_to()`，按漏洞语义把危险 API 调用分类，高危类别生成 `findings`，返回 `{scanned_methods, finding_count, findings, categories{cat:{count,high_risk,meaning,samples}}}`。

| 命令 | 漏洞类 | 回答的问题 |
|------|------|-----------|
| `analysis webview-security` | WebView 配置 | JS 桥/file 访问/调试等危险配置在哪 |
| `analysis ssl-safety` | MITM | 有无绕过证书校验的 TrustManager/HostnameVerifier |
| `analysis insecure-storage` | 数据存储 (M9) | 敏感数据是否写到外部存储/世界可读/明文 |
| `analysis sql-injection` | 注入 (M7) | rawQuery/execSQL 执行点在哪，是否可能拼接 |
| `analysis pending-intent` | Intent 重定向 | PendingIntent 是否可变、Intent 是否被转发 |

**C 组·完整安全分析矩阵（第三十四轮，恶意/隐私/加固/通信/组件全维度）：** 共享内核 `_xref_semantic_audit`——同一 xref_to 归类骨架，各命令 checks 字典不同。10 个专项审计覆盖剩余安全维度，`apk security-report` 一键聚合全部审计并给出综合风险评分（**审计套件闭环入口**）。

| 命令 | 维度 | 回答的问题 |
|------|------|-----------|
| `analysis privacy-sinks` | 隐私采集 (M6) | 采集了哪些隐私（设备标识/位置/联系人/剪贴板/录音摄像） |
| `analysis telephony-sms` | 电话短信 | 有无发/读短信、拨号、短信拦截（扣费/拦截马特征） |
| `analysis dynamic-code` | 动态加载 | 有无 DexClassLoader/native 库/反射加载（脱壳/payload） |
| `analysis persistence` | 后台驻留 | 有无设备管理员/无障碍/定时任务/通知监听 |
| `analysis weak-random` | 弱随机 (M10) | 安全场景是否误用 java.util.Random/固定种子 |
| `analysis broadcast-safety` | 组件通信 | 有无无权限广播/动态 receiver/粘性广播 |
| `analysis provider-safety` | Provider | openFile 路径穿越/URI 权限授予/跨应用访问 |
| `analysis anti-analysis` | 加固对抗 | 有无 root/模拟器/调试器/Frida/Xposed 检测（串+API 双路） |
| `analysis network-security` | 通信安全 | 明文 URL 有多少、有无证书固定 |
| `analysis obfuscation-metrics` | 混淆度量 | 混淆/加固程度评分（类名/反射密度/字符串覆盖） |
| `apk security-report` | **闭环** | 一条命令得到完整安全画像 + 综合风险评分 |

---

## `analysis native-methods [--limit]`

枚举所有 **native（JNI）方法**——Java 侧声明为 `native` 的方法，是 Java↔C/C++ 的边界。逆向加固/反调试/白盒加密常把核心逻辑放在 native 层，此命令定位所有进入 .so 的入口及其调用方。

```bash
androguard-skills analysis native-methods --apk-path test.apk
androguard-skills analysis native-methods --limit 50 --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--limit` | 返回 native 方法数量上限（默认 200） |

**输出（HelloWord-JNI.apk）：**
```json
{
  "scanned_methods": 13883,
  "native_method_count": 1,
  "class_count": 1,
  "by_class": {"Lsg/vantagepoint/helloworldjni/MainActivity;": 1},
  "native_methods": [
    {
      "class": "Lsg/vantagepoint/helloworldjni/MainActivity;",
      "method": "stringFromJNI",
      "descriptor": "()Ljava/lang/String;",
      "access_flags": "public native",
      "caller_count": 1,
      "callers": [
        {"class": "Lsg/vantagepoint/helloworldjni/MainActivity;", "method": "onCreate", "descriptor": "(Landroid/os/Bundle;)V"}
      ]
    }
  ],
  "truncated": false
}
```

| 字段 | 说明 |
|------|------|
| `by_class` | 每个类的 native 方法计数（快速定位 JNI 密集类） |
| `native_methods[].callers` | 谁调用了这个 native 方法（`get_xref_from`，即 Java 侧触发点） |
| `caller_count` | 调用方数量（0 = 无 Java 调用方，可能由 JNI_OnLoad/反射间接调用） |

**用途：** native 方法名 + 类名即 `RegisterNatives` 或 `Java_<class>_<method>` 符号线索，配合 `apk native-libraries` 定位 .so，再用 objdump/ghidra 深入 native 层。`native_count=0` 表示无 Java 侧 native 声明（native 逻辑可能全在 .so 通过 JNI_OnLoad 动态注册，无对应 Java stub）。

> 底层 API：遍历 `Analysis.get_methods()` → `EncodedMethod.get_access_flags_string()` 含 `native` → `MethodAnalysis.get_xref_from()` 取调用方。

---

## `analysis crypto-usage [--limit]`

聚合 **加密 API 用法**并**还原算法字符串**。扫描所有 `Cipher/MessageDigest/Mac/Signature/KeyGenerator/...` 的 `getInstance` 及 `SecretKeySpec/IvParameterSpec/PBEKeySpec` 构造，通过指令级寄存器跟踪还原 `getInstance("AES/CBC/PKCS5Padding")` 的字面参数，并标记弱算法。

```bash
androguard-skills analysis crypto-usage --apk-path test.apk
androguard-skills analysis crypto-usage --limit 50 --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--limit` | 每类加密操作返回样本上限（默认 100） |

**输出（InsecureBankv2.apk）：**
```json
{
  "algorithms": {"MD5": 4, "AES/CBC/PKCS5Padding": 3, "SHA1withRSA": 1, "SHA1": 1, "RSA": 1, "SHA256withRSA": 1},
  "weak_finding_count": 5,
  "weak_findings": [
    {"from": "L.../zza;->zzax(...)", "algorithm": "MD5", "category": "digest", "reason": "weak_or_ecb"}
  ],
  "usages": {
    "signature": {"count": 2, "samples": [{"from": "...", "target": "Ljava/security/Signature;->getInstance(...)", "algorithm": "SHA1withRSA", "offset": 2}]},
    "cipher": {"count": 3, "samples": [{"...": "..."}]}
  },
  "key_material": {
    "secret_key_spec": {"count": 3, "samples": [{"from": "Lcom/android/insecurebankv2/CryptoClass;->aes256encrypt(...)", "target": "Ljavax/crypto/spec/SecretKeySpec;-><init>([B Ljava/lang/String;)V", "offset": 0}]}
  }
}
```

| 字段 | 说明 |
|------|------|
| `algorithms` | 还原出的算法字符串 → 出现次数（**核心产出**，直接看用了什么加密） |
| `weak_findings` | 弱算法/不安全模式命中（DES/RC4/MD5/MD2/SHA-1/ECB/NoPadding/Blowfish） |
| `usages` | 按加密操作类型（cipher/digest/mac/signature/...）分组的调用点 |
| `key_material` | 密钥/IV 构造点（`SecretKeySpec`/`IvParameterSpec`/`PBEKeySpec`），追硬编码密钥的入口 |

**弱算法判定正则：** `(^|[/_-])(DES|RC4|RC2|MD5|MD2|SHA-?1|ECB|NoPadding|Blowfish)([/_-]|$)`。

**用途：** 一眼看出 APK 的加密栈是否安全——`ECB` 模式、`MD5` 摘要、`NoPadding` 都是常见漏洞。`key_material` 的 `from` 方法配合 `dex method-instructions-idx <class> <method>` 可继续追密钥字节来源（硬编码 vs 派生）。

> 底层 API：`_iter_method_invoke_args` 遍历基本块指令，维护寄存器→字符串映射，`const-string` 更新映射，`invoke` 时取目标+实参。算法串从 `getInstance` 的字符串实参还原。

---

## `analysis reflection-targets [--limit]`

聚合 **反射调用**并尝试**静态还原反射目标**。反射（`Class.forName`/`Method.invoke`/`ClassLoader.loadClass`/`getDeclaredField`...）常用于绕过 API 隐藏检查、加载隐藏类、调用私有方法——是加固/恶意逻辑的高频手法。

```bash
androguard-skills analysis reflection-targets --apk-path test.apk
androguard-skills analysis reflection-targets --limit 50 --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--limit` | 每类反射调用返回样本上限（默认 100） |

**输出（InsecureBankv2.apk）：**
```json
{
  "total_reflection_calls": 168,
  "resolved_target_names": ["com.android.vending.billing.IInAppBillingService", "com.google.android.gms.common.security.ProviderInstallerImpl", "..."],
  "categories": {
    "loadclass": {"count": 13, "samples": [
      {"from": "Lcom/google/android/gms/ads/internal/purchase/zzb;->zzK(...)", "target": "Ljava/lang/ClassLoader;->loadClass(...)", "resolved": "com.android.vending.billing.IInAppBillingService$Stub", "offset": 0}
    ]},
    "get_field": {"count": 6, "samples": [{"...": "...", "resolved": "STATUS_CONNECTING"}]},
    "invoke": {"count": "...", "samples": ["..."]}
  }
}
```

| 字段 | 说明 |
|------|------|
| `total_reflection_calls` | 全部反射调用点计数 |
| `resolved_target_names` | 静态还原出的反射目标名（类名/方法名/字段名，去重）——**可读性最高的产出** |
| `categories` | 按反射操作分类（forname/loadclass/get_method/get_field/invoke/newinstance/get_property） |
| `samples[].resolved` | 该调用点的反射目标字面值（`None` = 目标为运行时动态计算，无法静态还原） |

**用途：** `resolved_target_names` 暴露 APK 试图反射访问的隐藏类/API（如 `IInAppBillingService`、`ProviderInstallerImpl`）。`resolved=None` 的调用点需动态分析（Frida hook `Method.invoke`）。

> 底层 API：`_iter_method_invoke_args` 跟踪 `getInstance`/`forName`/`loadClass` 等的字符串实参还原目标。分类基于目标方法签名正则匹配。

---

## `analysis url-endpoints [--limit]`

提取 APK 中所有硬编码的 **网络端点**——URL、主机名、IP。扫描全量字符串常量池，按协议分类，并附引用该端点的方法。用于梳理攻击面（后端 API / C2 / 数据外传端点）。

```bash
androguard-skills analysis url-endpoints --apk-path test.apk
androguard-skills analysis url-endpoints --limit 100 --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--limit` | 每类端点返回样本上限（默认 200） |

**输出（InsecureBankv2.apk）：**
```json
{
  "total_endpoints": 67,
  "unique_hosts": ["www.googleapis.com", "accounts.google.com", "..."],
  "categories": {
    "https_url": {"count": 34, "samples": [
      {"value": "https://accounts.google.com", "full_string": null,
       "used_in": [{"class": "Lcom/google/android/gms/auth/api/credentials/IdentityProviders;", "method": "getIdentityProviderForAccount"}],
       "used_in_count": 1}
    ]},
    "http_url": {"count": 33, "samples": ["..."]}
  }
}
```

| 字段 | 说明 |
|------|------|
| `total_endpoints` | 命中的端点字符串总数 |
| `unique_hosts` | 去重主机名列表（快速看 APK 通信对象） |
| `categories` | 按 `https_url`/`http_url`/`ws_url`/`ftp_url`/`ip_addr` 分类 |
| `samples[].used_in` | 引用该端点的方法（`StringAnalysis.get_xref_from`，即哪里用到这个 URL） |

**用途：** `http_url`（明文）是传输安全问题；`unique_hosts` 结合威胁情报判断是否有可疑域名；`used_in` 定位使用点做进一步分析。

> 底层 API：`Analysis.get_strings()` → `StringAnalysis.get_value()` 正则匹配协议 → `get_xref_from()` 取引用方。

---

## `analysis taint-path <src_class> <src_method> <dst_class> <dst_method>`

在调用图上搜索从 **源方法**到 **汇方法**的一条**前向调用链**（若存在）。这是污点分析 / 攻击路径确认的收尾命令：给定两个具体方法，直接回答"用户可控入口是否、经由哪条路径到达危险 sink"。

与 `method-reachable`（输出整个可达子图）、`method-callers`（反向子图）的区别：本命令给定 **两端**，用前向 BFS + 父指针重建，返回**一条具体路径**。

```bash
# 确认加密方法是否可达某危险 API
androguard-skills analysis taint-path \
  "Lcom/android/insecurebankv2/CryptoClass;" "aes256encrypt" \
  "Ljavax/crypto/Cipher;" "getInstance" \
  --apk-path test.apk

# 带描述符精确定位 + 加深搜索
androguard-skills analysis taint-path \
  "L.../Src;" "entry" "L.../Sink;" "danger" \
  --src-descriptor "(Landroid/os/Bundle;)V" --dst-descriptor "()V" \
  --max-depth 10 --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `src_class` / `src_method` | 源方法（必填位置参数） |
| `dst_class` / `dst_method` | 汇方法（必填位置参数） |
| `--src-descriptor` / `--dst-descriptor` | 可选描述符（同名重载时精确定位） |
| `--max-depth` | 前向搜索深度上限（默认 8） |
| `--max-nodes` | 访问节点上限防爆（默认 20000） |

**输出（找到路径）：**
```json
{
  "source": {"class": "Lcom/android/insecurebankv2/CryptoClass;", "method": "aes256encrypt"},
  "sink": {"class": "Ljavax/crypto/Cipher;", "method": "getInstance"},
  "found": true,
  "path_length": 2,
  "visited_nodes": 1,
  "path": [
    {"class": "Lcom/android/insecurebankv2/CryptoClass;", "method": "aes256encrypt", "descriptor": "([B [B [B)[B"},
    {"class": "Ljavax/crypto/Cipher;", "method": "getInstance", "descriptor": "(Ljava/lang/String;)Ljavax/crypto/Cipher;", "call_offset_from_prev": 30}
  ]
}
```

**输出（无路径）：**
```json
{"source": {"...": "..."}, "sink": {"...": "..."}, "found": false, "visited_nodes": 6, "note": "no forward call path within max_depth/max_nodes"}
```

| 字段 | 说明 |
|------|------|
| `found` | 是否存在从 source 到 sink 的前向调用路径 |
| `path` | 调用链（从 source 到 sink 的方法序列），每步 `call_offset_from_prev` 是上一跳调用该方法的字节偏移 |
| `path_length` | 路径节点数（跳数 + 1） |
| `visited_nodes` | BFS 访问节点数（性能/覆盖度参考） |

**用途：** 先用 `apk attack-surface` 或 `method-callers` 找到候选源/汇，再用本命令确认二者间是否真存在调用路径并拿到具体链条——把"可能可达"坐实为"这条链可达"。`call_offset_from_prev` 可传给 `dex method-instructions-idx` 查看该调用点上下文。

> 底层 API：`get_method_analysis_by_name`（有描述符）或 `get_class_analysis().get_methods()` 按名定位两端 → 前向 BFS（`get_xref_to()`）+ parent 父指针（记录 `(key, offset)`）重建路径。

---

## `apk deeplinks`

枚举 APK 的所有 **深链接（deep link）**——组件 `intent-filter` 下的 `data` 标签定义的 URI 匹配规则，并判定哪些可被**浏览器直接触达**（`web_reachable`：BROWSABLE + VIEW + http/https scheme）。深链接是外部可控的组件入口，是 URL 参数注入 / 组件劫持 / 越权的攻击面。

```bash
androguard-skills apk deeplinks --apk-path test.apk
```

**输出（editor.apk）：**
```json
{
  "deeplink_count": 3,
  "web_reachable_count": 0,
  "schemes": {},
  "deeplinks": [
    {
      "component": "org.billthefarmer.editor.Editor",
      "component_type": "activity",
      "component_exported": "true",
      "scheme": null, "host": null, "port": null,
      "path": null, "pathPrefix": null, "pathPattern": null,
      "mimeType": "text/*",
      "browsable": false, "view_action": true,
      "web_reachable": false, "uri_preview": null
    }
  ]
}
```

| 字段 | 说明 |
|------|------|
| `deeplink_count` | data 标签定义的深链接总数 |
| `web_reachable_count` | 可被浏览器直接打开的深链接数（BROWSABLE + VIEW + http(s)） |
| `schemes` | 出现的 scheme → 次数统计（如 `{"myapp": 2, "https": 1}`） |
| `deeplinks[].web_reachable` | `browsable && view_action && scheme∈{http,https}`（最高危：任意网页可触发） |
| `deeplinks[].uri_preview` | 拼接的 URI 预览（`scheme://host:port/path`），无 scheme 时为 null（仅 mimeType 过滤，如上例的 text/* 文件关联） |

**用途：** `web_reachable=true` 的深链接可被恶意网页 `<a href="scheme://...">` 直接触发对应 Activity——重点审计其参数处理（配合 `apk attack-surface` 看该组件的可达 sink）。仅有 `mimeType` 无 scheme 的（如上例）是文件类型关联而非 URL 深链接。

> 底层 API：`APK.get_android_manifest_xml()` → 遍历 activity/activity-alias/service/receiver → `intent-filter` → `data` 标签提取 scheme/host/port/path*/mimeType，配合 `action.VIEW` + `category.BROWSABLE` 判定 web 可达。

---

## `analysis webview-security [--limit]`

聚合审计 **WebView 安全配置**。WebView 是 Android 应用最常见的漏洞面之一：JS↔Java 桥（`addJavascriptInterface` 在 targetSdk<17 下可 RCE）、`file://` 跨源读取、混合内容、远程调试等。此命令扫描所有内部方法的 `get_xref_to()`，按 7 个类别归类 WebView 相关 API 调用点，并对高危类别（js_bridge/file_access/debug）生成 findings。

```bash
androguard-skills analysis webview-security --apk-path test.apk
androguard-skills analysis webview-security --limit 50 --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--limit` | 每类别返回样本上限（per_type_limit，默认 100） |

**输出（InsecureBankv2.apk，节选）：**
```json
{
  "scanned_methods": 40188,
  "uses_webview": true,
  "webview_using_method_count": 94,
  "finding_count": 1,
  "findings": [
    {"category": "js_bridge", "severity": "high",
     "from": "Lcom/google/android/gms/internal/zzig;-><init>(...)V",
     "calls": "Lcom/google/android/gms/internal/zzig;->addJavascriptInterface(Ljava/lang/Object; Ljava/lang/String;)V",
     "offset": 284, "reason": "JS↔Java 桥（targetSdk<17 可 RCE，>=17 仍可调 @JavascriptInterface 方法）"}
  ],
  "categories": {
    "js_bridge":    {"count": 1,  "high_risk": true,  "meaning": "JS↔Java 桥（...RCE...）", "samples": [...]},
    "js_enabled":   {"count": 3,  "high_risk": false, "meaning": "启用 JavaScript（配合不可信内容→XSS）", "samples": [...]},
    "file_access":  {"count": 0,  "high_risk": true,  "meaning": "文件/内容 URL 访问（file:// 跨源读取本地文件）", "samples": []},
    "mixed_content":{"count": 1,  "high_risk": false, "meaning": "混合内容模式（HTTPS 页面加载 HTTP 资源→MITM）", "samples": [...]},
    "debug":        {"count": 0,  "high_risk": true,  "meaning": "远程调试（可被 adb/其他应用 inspect WebView）", "samples": []},
    "load":         {"count": 17, "high_risk": false, "meaning": "内容加载入口（若 URL 用户可控→加载任意页面）", "samples": [...]},
    "settings":     {"count": 7,  "high_risk": false, "meaning": "获取 WebSettings（配置入口，追踪后续 setter）", "samples": [...]}
  }
}
```

| 字段 | 说明 |
|------|------|
| `uses_webview` | 是否检测到任何 WebView 相关 API 调用（false = 应用不用 WebView，无此攻击面） |
| `webview_using_method_count` | 调用了 WebView API 的内部方法数 |
| `findings` | 高危类别命中（js_bridge/file_access/debug），每项含 `from`（调用方）/`calls`（被调 API）/`offset`/`reason` |
| `categories` | 7 类别的完整统计：`count`（命中数）/`high_risk`（是否高危类别）/`meaning`（安全含义）/`samples`（调用点样本） |

**7 个检测类别：**

| 类别 | 高危 | 匹配 API | 安全含义 |
|------|:----:|----------|---------|
| `js_bridge` | ✔ | `addJavascriptInterface` | targetSdk<17 可 RCE；>=17 仍暴露 `@JavascriptInterface` 方法 |
| `file_access` | ✔ | `setAllowFileAccess*` / `setAllowUniversalAccessFromFileURLs` / `setAllowContentAccess` | `file://` 跨源读取本地文件 |
| `debug` | ✔ | `setWebContentsDebuggingEnabled` | 远程调试，可被 adb/其他应用 inspect |
| `js_enabled` | | `setJavaScriptEnabled` | 启用 JS，配合不可信内容→XSS |
| `mixed_content` | | `setMixedContentMode` | HTTPS 页加载 HTTP 资源→MITM |
| `load` | | `loadUrl` / `loadData` / `loadDataWithBaseURL` | 内容加载入口，URL 可控→加载任意页 |
| `settings` | | `getSettings` | WebSettings 配置入口，追踪后续 setter |

**用途：** `findings` 直接是可审计的高危项清单。`js_bridge` 命中后配合 `dex method-instructions-idx <from-class> <from-method>` 看 `addJavascriptInterface` 注入的对象与桥接名，再审计该桥对象的 `@JavascriptInterface` 方法是否暴露敏感操作。`load` 类别定位 `loadUrl` 调用点，追 URL 是否用户可控（deeplink/Intent extra）。

> 底层 API：遍历 `Analysis.get_methods()` 内部方法 → `MethodAnalysis.get_xref_to()` 取被调 API 全名 → 7 类正则匹配归类。高危类别命中即生成 finding。

---

## `analysis ssl-safety [--limit]`

检测 **SSL/TLS 证书校验绕过**——MITM 漏洞的根因。审计三类模式：(1) 自定义 `X509TrustManager` 的 `checkServerTrusted`/`checkClientTrusted` **方法体无 `throw`**（信任任意证书）；(2) `HostnameVerifier.verify(...)Z` **恒返回 true**（接受任意主机名）；(3) 调用已知绕过 API（`SSLSocketFactory.getInsecure`/`ALLOW_ALL_HOSTNAME_VERIFIER`/`setHostnameVerifier`...）。

```bash
androguard-skills analysis ssl-safety --apk-path test.apk
androguard-skills analysis ssl-safety --limit 50 --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--limit` | 每类明细返回上限（per_type_limit，默认 100） |

**输出（InsecureBankv2.apk — 负例，无自定义 TrustManager）：**
```json
{
  "scanned_methods": 40188,
  "insecure_trustmanager_count": 0,
  "insecure_hostname_verifier_count": 0,
  "bypass_call_count": 0,
  "mitm_vulnerable": false,
  "insecure_trustmanagers": [],
  "insecure_hostname_verifiers": [],
  "bypass_calls": []
}
```

**命中时（`insecure_trustmanagers[]` 元素形态）：**
```json
{"class": "Lcom/example/MyTrustManager;", "method": "checkServerTrusted",
 "descriptor": "([Ljava/security/cert/X509Certificate; Ljava/lang/String;)V",
 "instruction_count": 2, "reason": "empty_or_no_throw"}
```

| 字段 | 说明 |
|------|------|
| `mitm_vulnerable` | **核心结论**：存在不安全 TrustManager 或 HostnameVerifier 即为 true |
| `insecure_trustmanagers` | `checkServerTrusted`/`checkClientTrusted` 方法体无 `throw`（不抛异常=信任全部证书） |
| `insecure_hostname_verifiers` | `verify(...)Z` 含 String 参数、恒返回 true 且无 throw（接受任意主机名） |
| `bypass_calls` | 调用已知不安全 API 的点（`getInsecure`/`ALLOW_ALL_HOSTNAME_VERIFIER`/`SSLSocketFactory`/`setDefaultHostnameVerifier`/`setHostnameVerifier`） |

**判定逻辑（`_method_is_trivially_true_or_empty`）：** 遍历方法基本块指令，统计 `instruction_count`、是否含 `throw`、是否 `const 1` 后 `return`。TrustManager 的校验方法**只要不 throw** 即视为不安全（正常实现校验失败必抛 `CertificateException`）；HostnameVerifier 的 `verify` **恒返回 true 且不 throw** 即不安全。

**用途：** `mitm_vulnerable=true` 是高危 MITM 漏洞——APP 可被中间人用任意伪造证书解密流量。命中后用 `decompile method <class> <method>` 看具体实现确认，`method-callers` 溯源哪个 `SSLContext.init`/`HttpsURLConnection` 使用了它。

> **验证说明：** 检测机制的两个原子子判定已在真实字节码上验证正确——含 `throw` 的方法正确判为安全（不误报），无 throw 且返回 const 1 的 `)Z` 方法正确判为不安全（结构等同于恶意 `verify()`）。当前测试语料库中无任何 APK 含名为 `checkServerTrusted`/`verify` 的自定义方法（InsecureBankv2/certificatePinningXamarin/UnCrackable-1/2/3/r2pay/vulcrack/editor 全数排查为 0），故负例全部返回 0 是**真实结果**而非静默失效——命令干净扫描 40188 方法无报错。

> 底层 API：遍历 `Analysis.get_methods()` 内部方法 → 按名匹配 `checkServerTrusted`/`checkClientTrusted`/`verify` → `get_basic_blocks()` 遍历指令判 throw/return-true；`get_xref_to()` 匹配 bypass API 正则。

---

## `analysis insecure-storage [--limit]`

审计 **不安全数据存储**（OWASP Mobile M9）。扫描所有内部方法对存储 API 的调用，按"数据落地位置与权限"归类：外部存储写入（世界可读）、世界可读/写文件模式、明文 SharedPreferences、SQLite 打开、内部私有存储。定位敏感信息可能泄露（其他应用可读、adb 可导出、备份可提取）的落地点。

```bash
androguard-skills analysis insecure-storage --apk-path test.apk
androguard-skills analysis insecure-storage --limit 50 --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--limit` | 每类别返回样本上限（per_type_limit，默认 100） |

**输出（InsecureBankv2.apk，节选）：**
```json
{
  "scanned_methods": 40188,
  "uses_external_storage": true,
  "finding_count": 14,
  "categories": {
    "external_storage":         {"count": 14, "high_risk": true,  "meaning": "外部存储（世界可读，任意应用/用户可访问，勿存敏感数据）", "samples": [...]},
    "world_readable_writable":  {"count": 20, "high_risk": false, "meaning": "文件/偏好写入入口（需核验 mode 是否 MODE_WORLD_READABLE/WRITEABLE=1/2）"},
    "shared_prefs_edit":        {"count": 22, "high_risk": false, "meaning": "SharedPreferences 明文写入（XML 明文，root/备份可提取）"},
    "database_open":            {"count": 31, "high_risk": false, "meaning": "SQLite 数据库打开（默认明文，需核验是否加密/权限模式）"},
    "internal_cache":           {"count": 10, "high_risk": false, "meaning": "内部存储（应用私有沙箱，相对安全，仅明文备份风险）"},
    "world_mode_constant":      {"count": 12, "high_risk": false, "meaning": "文件权限设置/临时文件（核验是否设为全局可读写）"}
  }
}
```

| 字段 | 说明 |
|------|------|
| `uses_external_storage` | 是否检测到外部存储 API 调用（true = 存在世界可读落地面） |
| `findings` | 高危项（external_storage 类别命中），含 `from`/`calls`/`offset`/`reason` |
| `categories.database_open` | SQLite 打开点——InsecureBankv2 的著名漏洞即本地明文 DB 存凭据 |

**用途：** `external_storage` finding 定位后配合 `dex method-instructions-idx <from-class> <from-method>` 看写入的是什么数据（是否敏感）。`world_readable_writable`/`world_mode_constant` 是需核验 mode 常量（1=MODE_WORLD_READABLE，2=WORLD_WRITEABLE）的入口，配合 `dex method-instructions` 查 `getSharedPreferences`/`openFileOutput` 的第二个实参。

> 底层 API：遍历 `Analysis.get_methods()` 内部方法 → `get_xref_to()` 取被调 API 全名 → 6 类正则归类。external_storage 为高危类别自动生成 finding。

---

## `analysis sql-injection [--limit]`

审计 **SQL 注入面**（OWASP Mobile M7）。枚举所有 SQL 执行 API 调用点——`rawQuery`/`execSQL` 执行原始 SQL（若拼接用户可控字符串则可注入），`query`/`update`/`delete` 的 `selection` 参数、`SQLiteQueryBuilder.appendWhere` 同理。高危类别（rawQuery/execSQL）生成 findings，供人工核验参数是否用户可控 + 是否参数化（`?` 占位）。

```bash
androguard-skills analysis sql-injection --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--limit` | 每类别返回样本上限（per_type_limit，默认 100） |

**输出（InsecureBankv2.apk，节选）：**
```json
{
  "scanned_methods": 40188,
  "uses_sql": true,
  "finding_count": 20,
  "categories": {
    "raw_query":         {"count": 11, "high_risk": true,  "meaning": "rawQuery 执行原始 SQL（若拼接用户输入→注入）", "samples": [...]},
    "exec_sql":          {"count": 9,  "high_risk": true,  "meaning": "execSQL 执行原始 SQL（若拼接用户输入→注入）"},
    "query_builder":     {"count": 1,  "high_risk": false, "meaning": "QueryBuilder 构造查询（selection/appendWhere 拼接可注入）"},
    "structured_query":  {"count": 33, "high_risk": false, "meaning": "结构化 query/update/delete（selection 参数拼接可注入，用 ? 占位更安全）"},
    "compile_statement": {"count": 0,  "high_risk": false, "meaning": "预编译语句（若 SQL 字符串含拼接仍可注入）"}
  }
}
```

| 字段 | 说明 |
|------|------|
| `uses_sql` | 是否检测到任何 SQL 执行 API（false = 无本地 DB 交互） |
| `findings` | rawQuery/execSQL 命中（直接执行原始 SQL，注入风险最高） |
| `categories.structured_query` | `query`/`update`/`delete`——安全性取决于 `selection` 是否参数化 |

**用途：** `rawQuery`/`execSQL` finding 是审计重点。用 `decompile method <from-class> <from-method>` 看 SQL 字符串如何构造——若含 `+` 拼接或 `String.format` 注入用户输入（`getIntent().getStringExtra` / EditText）即为可注入。参数化查询（`rawQuery("... WHERE x=?", new String[]{v})`）则安全。

> 底层 API：遍历 `Analysis.get_methods()` 内部方法 → `get_xref_to()` 匹配 SQLite API 正则 → 5 类归类。rawQuery/execSQL 为高危类别自动生成 finding。

---

## `analysis pending-intent [--limit]`

审计 **PendingIntent 可变性与 Intent 重定向**面。可变（无 `FLAG_IMMUTABLE`）且包裹隐式 Intent 的 PendingIntent 允许攻击者篡改内部 Intent 实现权限提升 / Intent 重定向（Android 12+ 强制指定可变性）。本命令枚举所有 `PendingIntent.get*` 创建点及 `getIntent`/Intent 转发调用，供核验 flag 与转发链——**不做 flag 位值还原**（`or` 运算寄存器跟踪易误报），而是枚举 + 标记需人工核验，保持可靠（findings 的 `severity` 为 `review` 而非 `high`）。

```bash
androguard-skills analysis pending-intent --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--limit` | 每类别返回样本上限（per_type_limit，默认 100） |

**输出（InsecureBankv2.apk，节选）：**
```json
{
  "scanned_methods": 40188,
  "uses_pending_intent": true,
  "finding_count": 16,
  "categories": {
    "pending_intent_create": {"count": 16,  "high_risk": true,  "meaning": "PendingIntent 创建（需核验 flag 含 FLAG_IMMUTABLE=0x4000000，否则可被篡改）", "samples": [...]},
    "get_intent":            {"count": 36,  "high_risk": false, "meaning": "读取传入 Intent（外部可控入口，若转发→Intent 重定向）"},
    "intent_forward":        {"count": 180, "high_risk": false, "meaning": "Intent 转发/回传（若转发外部传入的 Intent→重定向/权限提升）"},
    "intent_component":      {"count": 58,  "high_risk": false, "meaning": "Intent 目标显式设定（显式 Intent 相对安全，隐式则风险高）"}
  }
}
```

| 字段 | 说明 |
|------|------|
| `uses_pending_intent` | 是否创建 PendingIntent |
| `findings` | PendingIntent 创建点（`severity: review`——需核验 flag，非自动判定漏洞） |
| `categories.intent_forward` | Intent 转发点——与 `get_intent` 交叉看是否"读外部 Intent→转发"（重定向链） |

**用途：** `pending_intent_create` finding 后用 `dex method-instructions-idx <from-class> <from-method>` 查 `getActivity`/`getBroadcast` 的 flag 实参（第 4 个参数）是否含 `FLAG_IMMUTABLE`（67108864 / 0x4000000）。Intent 重定向审计：`get_intent` 与 `intent_forward` 在同一方法出现时，用 `taint-path` 确认"外部传入 Intent → startActivity"是否真的形成转发链。

> 底层 API：遍历 `Analysis.get_methods()` 内部方法 → `get_xref_to()` 匹配 PendingIntent/Intent API 正则 → 4 类归类。pending_intent_create 生成 review 级 finding（不断言漏洞，提示核验）。

---

## 相关命令

- [`analysis security-hotspots`](analysis-callgraph-permissions.md) — 全局危险调用模式扫描（本组的通用版）
- [`analysis hardcoded-secrets`](analysis-callgraph-permissions.md) — static 字段硬编码密钥扫描
- [`apk attack-surface`](analysis-callgraph-permissions.md) — 导出组件 × 可达 sink 攻击面地图
- [`analysis method-reachable` / `method-callers`](analysis-class-method-detail.md) — 单方法正/反向可达子图
- [`apk native-libraries`](apk-meta.md) — .so 文件列表（配合 native-methods 深入 native 层）

---

# C 组：完整安全分析矩阵（第三十四轮）

以下 10 个专项审计命令共享内核 `_xref_semantic_audit(analysis_obj, checks, per_type_limit)`——遍历全量内部方法 `get_xref_to()`，按各命令的 `checks={类别:(正则, 是否高危, 含义)}` 归类被调 API，高危类别自动生成 `findings`。统一返回结构 `{scanned_methods, finding_count, findings[], categories{cat:{count,high_risk,meaning,samples}}}` + 各命令特定顶层字段。全部命令均支持 `--limit`（每类样本上限，默认 100）与 `--apk-path`。

> **样本区分度实证**（`apk security-report` 跨样本）：r2pay-v1.0（商业加固支付 SDK）obfuscation=80/heavily_obfuscated + anti-analysis=True；UnCrackable-Level1（OWASP crackme）正确识别 root 检测 anti-analysis=True；certificatePinningXamarin（Xamarin，Java 层无混淆）obfuscation=0。检测逻辑有真实区分度，跨 4 样本零 error。

## `analysis privacy-sinks [--limit]`

隐私数据收集审计（OWASP **M6 Inadequate Privacy Controls**）。7 类：`device_id`（IMEI/IMSI/序列号/电话号，**高危**，可追踪用户）、`location`（精确地理位置，**高危**）、`contacts`（通讯录，**高危**）、`accounts`（AccountManager 枚举账户）、`installed_apps`（已装应用枚举，用户画像）、`clipboard`（剪贴板读取，可窃取复制的密码/验证码）、`capture`（录音/拍照 MediaRecorder/Camera/AudioRecord，**高危**）。

```bash
androguard-skills analysis privacy-sinks --apk-path app.apk
```

**输出（InsecureBankv2）：** `scanned_methods=40188, finding_count=17, privacy_category_hit=3`（命中 3 类隐私）。顶层额外字段 `privacy_category_hit`=命中的隐私类别数。

## `analysis telephony-sms [--limit]`

电话短信滥用审计（恶意扣费/短信拦截马特征）。5 类：`send_sms`（SmsManager.sendTextMessage，**高危**，静默扣费/发高级短信）、`read_sms`（读取/解析短信 content://sms、SmsMessage.createFromPdu，**高危**，窃取验证码/银行短信）、`make_call`（ACTION_CALL 拨号）、`intercept`（**高危** abortBroadcast，配合短信 receiver 拦截短信不让系统显示）、`phone_state`（PhoneStateListener 通话监听/运营商信息）。

```bash
androguard-skills analysis telephony-sms --apk-path app.apk
```

**输出（InsecureBankv2）：** `finding_count=1, telephony_category_hit=2`。顶层额外字段 `telephony_category_hit`。

## `analysis dynamic-code [--limit]`

动态代码加载审计（加固脱壳/热更新/恶意 payload 加载点）。4 类：`dex_loader`（DexClassLoader/PathClassLoader/InMemoryDexClassLoader/DexFile.loadDex，**高危**，运行时加载额外代码）、`native_load`（System.load/loadLibrary 加载任意 .so）、`define_class`（ClassLoader.defineClass/loadClass，可绕过完整性校验）、`reflection_load`（Class.forName/Method.invoke，配合动态加载调隐藏代码）。

```bash
androguard-skills analysis dynamic-code --apk-path app.apk
```

**输出（InsecureBankv2）：** `finding_count=14, uses_dynamic_loading=True`。顶层额外字段 `uses_dynamic_loading`（是否用了动态 DEX 加载）。

## `analysis persistence [--limit]`

持久化/后台驻留审计（恶意驻留/提权特征）。5 类：`device_admin`（DevicePolicyManager/lockNow/wipeData，**高危**，勒索软件特征，难卸载）、`accessibility`（AccessibilityService/performGlobalAction，**高危**，读屏/模拟点击/覆盖攻击）、`job_alarm`（JobScheduler/AlarmManager/WorkManager 定时唤醒）、`foreground_service`（startForeground 保活）、`notification_listener`（NotificationListenerService，**高危**，读所有应用通知窃取验证码）。

```bash
androguard-skills analysis persistence --apk-path app.apk
```

**输出（InsecureBankv2）：** `finding_count=100（达 limit 上限）, persistence_category_hit=3`。顶层额外字段 `persistence_category_hit`。

## `analysis weak-random [--limit]`

不安全随机数审计（OWASP **M10**）。3 类：`insecure_random`（**高危** java.util.Random/Math.random，可预测，勿用于密钥/token/IV/盐）、`fixed_seed`（**高危** setSeed 固定种子使随机可复现）、`secure_random`（SecureRandom 正确用法，作对比参考）。

```bash
androguard-skills analysis weak-random --apk-path app.apk
```

**输出（InsecureBankv2）：** `finding_count=9, uses_insecure_random=True`。顶层额外字段 `uses_insecure_random`。注意：需结合上下文——UI 动画用 Random 无害，密钥生成用 Random 才是漏洞。

## `analysis broadcast-safety [--limit]`

广播收发安全审计（组件间通信劫持面）。4 类：`send_broadcast`（sendBroadcast/sendOrderedBroadcast，无 receiverPermission 参数则任意应用可接收→数据泄露）、`sticky_broadcast`（**高危** sendStickyBroadcast，已废弃，无法限制接收者）、`register_dynamic`（registerReceiver，无 permission 则任意应用可触发→组件劫持）、`local_broadcast`（LocalBroadcastManager 进程内，安全用法参考）。

```bash
androguard-skills analysis broadcast-safety --apk-path app.apk
```

**输出（InsecureBankv2）：** `finding_count=0`（无高危粘性广播，send/register 归入非高危类别待人工核验 permission 参数）。

## `analysis provider-safety [--limit]`

ContentProvider 安全审计。4 类：`open_file`（**高危** ContentProvider.openFile/openAssetFile，若拼接 URI path 未校验→路径穿越读任意文件）、`grant_uri`（grantUriPermission/FLAG_GRANT_*_URI_PERMISSION 临时授权，需核验范围）、`resolver_access`（ContentResolver.query/openInputStream 跨应用读写入口）、`provider_query`（Provider.query 实现，需核验 selection 注入 + 权限）。

```bash
androguard-skills analysis provider-safety --apk-path app.apk
```

**输出（InsecureBankv2）：** `finding_count=4`（openFile 高危点）。

## `analysis anti-analysis [--limit]`

反分析/加固对抗侦察——**字符串 + API 双路扫描**（不同于纯 xref 命令）。API 层（xref_to）：`debugger_api`（isDebuggerConnected/waitForDebugger）。字符串层（get_strings）：`root_detect`（su 路径/Magisk/Superuser/test-keys）、`emulator_detect`（qemu/goldfish/genymotion/nox/bluestacks）、`frida_xposed`（Frida/Xposed/LSPosed/riru hook 框架侦测）。

```bash
androguard-skills analysis anti-analysis --apk-path app.apk
```

**输出（UnCrackable-Level1）：** `has_anti_analysis=True`（正确识别该 crackme 的 root 检测）。返回结构特殊：`{scanned_methods, strings_scanned, total_anti_analysis_indicators, has_anti_analysis, api_categories{}, string_indicator_categories{}}`。字符串命中样本含 `used_in`（引用该串的方法，前 3 个）。

## `analysis network-security [--limit]`

网络安全配置审计（通信安全总览，与 `ssl-safety` 互补）——**字符串 + API 双路**。API 层：`cert_pinning`（CertificatePinner/X509TrustManager）、`http_client`（HttpURLConnection/OkHttpClient）、`ssl_context`（SSLContext/SSLSocketFactory）。字符串层：扫描 `http://` 明文 URL（对比统计 `https://` 数量）。

```bash
androguard-skills analysis network-security --apk-path app.apk
```

**输出（InsecureBankv2）：** `cleartext_url_count=22, has_cert_pinning=True`。返回结构：`{scanned_methods, strings_scanned, cleartext_url_count, https_url_count, has_cert_pinning, cleartext_urls[{url,used_in}], api_categories{}}`。

## `analysis obfuscation-metrics`

混淆度量（**度量统计类，非 findings**，无 `--limit`）。量化 APK 混淆/加固程度：类名长度分布（单双字符类名比例=ProGuard/R8 特征）、反射密度（反射调用/总调用）、被覆盖字符串数（字符串解密特征）。综合评分 0-100 → `heavily_obfuscated`(≥60)/`moderately_obfuscated`(≥30)/`lightly_or_not_obfuscated`。

```bash
androguard-skills analysis obfuscation-metrics --apk-path app.apk
```

**输出（r2pay-v1.0 商业加固）：** `obfuscation_score=80, assessment=heavily_obfuscated`。返回字段：`internal_class_count, short_name_class_count, short_name_ratio, reflection_call_count, reflection_density, overwritten_string_count, obfuscation_score, assessment, name_length_histogram{长度:类数}`。

## `apk security-report [--limit]`

**审计套件闭环入口**——一条命令聚合调用全部专项审计（webview/ssl/storage/sql/pending/privacy/telephony/dynamic/persistence/weak-random/broadcast/provider/network/anti-analysis + obfuscation + security-hotspots + hardcoded-secrets + attack-surface + deeplinks 共 **19 个域**），输出顶层风险总览 + 加权综合风险评分。`--limit` 控制每域样本/findings 上限（默认 20，比单命令小以控体积）。

```bash
androguard-skills apk security-report --apk-path app.apk
androguard-skills apk security-report --limit 5 --apk-path app.apk   # 更精简
```

**输出（InsecureBankv2）：**
```json
{
  "domains": {
    "webview_security": {"finding_count": ..., "uses_webview": ...},
    "ssl_safety": {"finding_count": 0, "mitm_vulnerable": false},
    "insecure_storage": {"finding_count": ..., "uses_external_storage": ...},
    "...": "...(19 个域)",
    "obfuscation": {"score": 16, "assessment": "lightly_or_not_obfuscated", "short_name_ratio": 0.1838},
    "attack_surface": {"exposed_component_count": 7, "critical_component_count": 2},
    "deeplinks": {"deeplink_count": 0, "web_reachable_count": 0}
  },
  "high_risk_findings": [ {"domain": "...", "category": "...", "from": "...", "calls": "...", "reason": "..."} ],
  "errors": [],
  "total_high_risk_findings": 118,
  "composite_risk_score": 65,
  "risk_level": "critical"
}
```

**综合风险评分权重**（0-100）：ssl mitm_vulnerable +25；webview findings ×5(≤15)；sql ×2(≤15)；storage ×1(≤10)；telephony 命中≥2 类 +10；动态加载 +8；持久化 +7；反分析 +5；明文 URL +5。`risk_level`：critical(≥60)/high(≥35)/medium(≥15)/low。`errors` 收集单个审计域的异常而不中断整体（韧性设计）。

**典型用法**：接手一个陌生 APK 时先跑 `security-report` 得到全局画像与风险评分，再按 `high_risk_findings` 里指向的域调用对应单命令（如 `analysis webview-security`）深挖细节——这是漏洞审计套件的**推荐入口**。
