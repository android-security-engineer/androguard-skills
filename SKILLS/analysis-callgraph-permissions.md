# 调用图与 API 权限映射

封装第六轮新增的 Analysis 调用图导出和基于 API level 的方法→权限映射分析。

## 命令

### `analysis call-graph`

获取完整的**调用图**（call graph）并序列化为 JSON。调用图是 networkx `DiGraph`，节点是方法，边是调用关系。

```bash
androguard-skills analysis call-graph --apk-path test.apk
androguard-skills analysis call-graph --limit 50 --apk-path test.apk
androguard-skills analysis call-graph --external --apk-path test.apk
```

**参数：**
- `--limit`：返回边数量上限（调用图可能很大，建议先用小 limit 探查）
- `--external`：是否包含外部方法（Android Framework / 第三方库）节点和边。默认只返回内部方法

**输出：**
```json
{
  "total_nodes": 2023,
  "total_edges": 3760,
  "returned_nodes": 1500,
  "returned_edges": 50,
  "nodes": [
    {
      "classname": "Lcom/example/Foo;",
      "methodname": "onCreate",
      "descriptor": "(Landroid/os/Bundle;)V",
      "accessflags": "protected",
      "external": false,
      "entrypoint": false
    },
    ...
  ],
  "edges": [
    {
      "from": {"classname": "Lcom/example/Foo;", "methodname": "onCreate"},
      "to": {"classname": "Lcom/example/Bar;", "methodname": "init"}
    },
    ...
  ]
}
```

**字段说明：**
- `total_nodes` / `total_edges`：调用图完整规模
- `nodes`：方法节点（含类名/方法名/描述符/访问标志/是否外部/是否入口）
- `edges`：调用边（from 调用 to）
- `entrypoint`：是否为入口方法（如 `onCreate`）

**用途：** 调用图是程序分析的核心数据结构，可用于：
- 梳理方法调用链（A→B→C）
- 定位某方法的所有调用者/被调用者
- 死代码检测（无入边的非入口方法）
- 与 CFG（`method-basic-blocks`）结合做路径敏感分析

> 底层 API：`Analysis.get_call_graph()` 返回 `networkx.DiGraph`。

### `analysis call-graph-filtered`

生成**按类/方法/描述符/访问标志过滤的子调用图**。与 `call-graph`（全量图）的区别：本命令透传 `get_call_graph` 的过滤参数，只保留匹配方法的调用关系，避免全图过大。

```bash
# 只看某个类的内部调用关系
androguard-skills analysis call-graph-filtered --classname "Lcom/example/Foo;" --apk-path test.apk

# 只看名为 onCreate 的方法相关调用
androguard-skills analysis call-graph-filtered --methodname "onCreate" --limit 20 --apk-path test.apk

# 移除孤立节点（无任何边的节点），只看有调用关系的子图
androguard-skills analysis call-graph-filtered --classname "Lcom/example/Foo;" --no-isolated --apk-path test.apk

# 包含外部方法（Framework）节点
androguard-skills analysis call-graph-filtered --methodname "onCreate" --external --apk-path test.apk
```

**参数：**
- `--classname`：类名正则过滤（如 `Lcom/example/Foo;`，`;` 需注意正则转义）
- `--methodname`：方法名正则过滤
- `--descriptor`：方法描述符正则过滤
- `--accessflags`：访问标志正则过滤（如 `public.*static`）
- `--no-isolated`：移除孤立节点（无任何边的节点）
- `--external`：是否包含外部方法节点/边（默认只内部）
- `--limit`：返回边数量上限

**输出：**
```json
{
  "filter": {"classname": "Lcom/example/Foo;", "methodname": null, "descriptor": null, "accessflags": null, "no_isolated": false, "external": false},
  "total_nodes": 455,
  "total_edges": 782,
  "returned_nodes": 157,
  "returned_edges": 5,
  "nodes": [...],
  "edges": [
    {"from": {"classname": "Lcom/example/Foo;", "methodname": "access$1100"}, "to": {"classname": "Lcom/example/Foo;", "methodname": "readFile"}}
  ]
}
```

`total_nodes`/`total_edges` 是**过滤后子图**的规模（非全图）。`filter` 字段回显实际生效的过滤条件。

**用途：**
- 聚焦单个类/方法的调用关系，避免全图噪声
- 配合 `--no-isolated` 做死代码检测（孤立非入口方法）
- 按访问标志筛选（如只看 `public static` 入口方法）

> 底层 API：`Analysis.get_call_graph(classname, methodname, descriptor, accessflags, no_isolated)`，过滤参数均为正则。

### `analysis permissions`

基于 API level 的**方法→权限映射**批量分析。列出 APK 调用到的、需要权限的 API 方法及其所需权限。

```bash
androguard-skills analysis permissions --apk-path test.apk
androguard-skills analysis permissions --apilevel 28 --limit 20 --apk-path test.apk
```

**参数：**
- `--apilevel`：API level（用于加载对应的权限映射表，默认用 APK effective target SDK）
- `--limit`：返回结果上限

**输出：**
```json
{
  "apilevel": "28",
  "total": 5,
  "returned": 5,
  "results": [
    {
      "method": {
        "class_name": "Landroid/telephony/TelephonyManager;",
        "name": "getDeviceId",
        "descriptor": "()Ljava/lang/String;",
        "is_external": true
      },
      "permissions": ["android.permission.READ_PHONE_STATE"]
    },
    ...
  ]
}
```

**字段说明：**
- `method`：调用的 API 方法（类名/方法名/描述符/是否外部）
- `permissions`：该方法所需的权限列表（一个方法可能需要多个权限）

**与 `permission-usage` 的区别：**
- `permission-usage <perm>`：**按权限反查**——给定一个权限，找哪些方法需要它
- `permissions`：**批量正查**——列出所有需权限的 API 调用，不需指定权限

> 底层 API：`Analysis.get_permissions(apilevel)`，基于 [Axplorer](https://github.com/reddr/axplorer) 的 API↔权限映射。**注意**：映射可能不完整，部分 APK 返回 0 是数据特性（调用的方法不在映射表中），非 bug。

### `analysis android-api-usage`

批量列出 APK 使用的**所有 Android 平台 API 方法**（`is_android_api=True` 的外部方法）。

与 `method-api-info`（单方法查询 is_android_api）和 `permissions`（仅列需权限的 API）的区别：本命令列出**全部**被调用的 Android API（不论是否需权限），用于安全审计"这个 APK 调用了哪些系统 API"。

```bash
androguard-skills analysis android-api-usage --apk-path test.apk

# 限制返回数量
androguard-skills analysis android-api-usage --limit 50 --apk-path test.apk

# 展开每个 API 的调用方（谁调用了这个 API）
androguard-skills analysis android-api-usage --limit 10 --with-xrefs --apk-path test.apk
```

**输出：**
```json
{
  "total": 500,
  "returned": 3,
  "apis": [
    {
      "class": "Ljava/io/File;",
      "method": "<init>",
      "descriptor": "(Ljava/lang/String;)V",
      "full_name": "Ljava/io/File; <init> (Ljava/lang/String;)V"
    },
    ...
  ]
}
```

加 `--with-xrefs` 时每项额外含 `callers_count` 和 `callers` 列表（`{from_class, from_method, from_descriptor, offset}`），标识哪个内部方法在哪处调用了该 API。

| 参数 | 说明 |
|------|------|
| `--limit` | 返回 API 数量上限（默认全部） |
| `--with-xrefs` | 展开每个 API 的调用方 xref |

`total` 是 APK 使用的去重 Android API 总数，`returned` 受 `--limit` 限制。`--with-xrefs` 会显著增大输出（每个 API 展开所有调用方），建议配合 `--limit`。

> 底层 API：`Analysis.create_xref()`（幂等，确保交叉引用已建立）+ `Analysis.get_android_api_usage()`，返回 `Iterator[MethodAnalysis]`（需 `list()` 物化）。API 判定基于类名前缀（`Ljava/*`/`Landroid/*` 等系统包）。

### `analysis security-hotspots [--limit]`

**安全热点批量扫描**——按安全敏感的调用模式扫描所有内部方法的 `xref_to`，聚合每类热点的调用位置，一处输出便于快速定位需审计的代码。

```bash
androguard-skills analysis security-hotspots --apk-path test.apk

# 每类热点最多返回 20 个样本
androguard-skills analysis security-hotspots --limit 20 --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--limit` | 每类热点返回的调用位置上限（默认 50） |

**输出：**
```json
{
  "scanned_methods": 1431,
  "native_methods_count": 0,
  "native_methods": [],
  "categories": {
    "reflection": {"count": 0, "samples": []},
    "crypto": {"count": 0, "samples": []},
    "dynamic_load": {"count": 0, "samples": []},
    "command_exec": {"count": 0, "samples": []},
    "network": {"count": 0, "samples": []},
    "file_io": {"count": 197, "samples": [{"from": "L.../FileProvider;-><clinit>()V", "calls": "Ljava/io/File;-><init>(Ljava/lang/String;)V", "offset": 20}]},
    "intent": {"count": 48, "samples": [{"from": "L.../Editor;->openRecent(...)", "calls": "Landroid/content/Intent;-><init>(...)", "offset": 0}]},
    "telephony": {"count": 0, "samples": []},
    "content_provider": {"count": 34, "samples": [{"from": "L.../Editor$ReadTask;->doInBackground(...)", "calls": "...->getContentResolver()...", "offset": 0}]}
  }
}
```

| 类别 | 检测模式 | 安全含义 |
|------|---------|---------|
| `reflection` | `Class.forName`/`Method.invoke`/`Ljava/lang/reflect/` | 反射（动态加载类、调用隐藏 API，常用于绕过检查） |
| `crypto` | `javax.crypto`/`java.security`/`Base64` | 加密（密钥/算法分析，检测硬编码密钥配合 `field-init-value`） |
| `dynamic_load` | `DexClassLoader`/`PathClassLoader`/`loadClass` | 动态加载（热修复/插件化/加壳，运行时加载 DEX） |
| `command_exec` | `Runtime.exec`/`ProcessBuilder` | 命令执行（命令注入风险） |
| `network` | `Socket`/`URL`/`HttpURLConnection`/`okhttp` | 网络（数据外传、C2 通信） |
| `file_io` | `File`/`FileInputStream`/`RandomAccessFile` | 文件 I/O（路径遍历、敏感文件读写） |
| `intent` | `Intent`/`startActivity`/`sendBroadcast` | Intent（组件间通信、隐式 Intent 劫持） |
| `telephony` | `SmsManager`/`TelephonyManager` | 电话（短信发送、IMEI 读取，隐私） |
| `content_provider` | `ContentResolver`/`Cursor` | ContentProvider（跨应用数据访问） |
| `native_methods` | `access_flags` 含 `native` | native 方法（JNI 实现，需 so 层分析） |

> 底层 API：遍历 `Analysis.get_methods()`（仅内部方法，`is_external()==False`）→ `MethodAnalysis.get_xref_to()` 扫描调用目标 → 正则匹配危险类名/方法签名。`native` 通过 `EncodedMethod.get_access_flags_string()` 含 `native` 判定。每个调用只归一类（break）。`samples` 含 `{from（调用方签名）, calls（被调目标）, offset}`，offset 可传给 `dex method-instructions-idx`/`disassemble` 定位指令。

### `analysis hardcoded-secrets [--limit]`

**硬编码敏感字符串扫描**——扫描所有类的静态值数组（EncodedArray），检测 `static final` 字段中的硬编码敏感凭证。

与 `dex regex-strings`（全量字符串正则搜索，含普通字符串）和 `security-hotspots`（方法级调用模式）的区别：本命令只扫 static 字段的初始值（开发者主动硬编码的常量），按敏感模式分类聚合。用于检测硬编码的 API 密钥、令牌、后端 URL、私钥等——常见的安全漏洞。

```bash
androguard-skills analysis hardcoded-secrets --apk-path test.apk

# 每类最多返回 20 个
androguard-skills analysis hardcoded-secrets --limit 20 --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--limit` | 每类敏感项返回上限（默认 100） |

**输出：**
```json
{
  "scanned_classes": 585,
  "scanned_static_values": 10796,
  "counts": {"private_key": 0, "jwt": 0, "url": 5, "google_api_key": 0, "aws_key": 0, "base64_long": 0, "api_key_field": 5},
  "categories": {
    "url": [
      {"class": "Lcom/google/android/gms/auth/api/credentials/IdentityProviders;", "field": "GOOGLE", "value": "https://accounts.google.com", "value_len": 28}
    ],
    "api_key_field": [
      {"class": "Lcom/android/insecurebankv2/ChangePassword;", "field": "PASSWORD_PATTERN", "value": "(?=.*\\d)...", "value_len": 50}
    ]
  }
}
```

| 类别 | 检测模式 | 安全含义 |
|------|---------|---------|
| `private_key` | `-----BEGIN (RSA\|EC\|DSA\|OPENSSH) PRIVATE KEY-----` | 私钥泄露（最高危） |
| `jwt` | `eyJ...` JWT 格式 | JWT 令牌硬编码 |
| `url` | `https?://...` | 后端 URL（攻击面/C2/数据外传端点） |
| `google_api_key` | `AIza[0-9A-Za-z_-]{35}` | Google API 密钥 |
| `aws_key` | `AKIA[0-9A-Z]{16}` | AWS 访问密钥 |
| `base64_long` | 40+ 字符 base64 | 长 base64 串（可能为加密密钥/凭证） |
| `api_key_field` | 字段名含 api_key/secret/token/password/auth/credential | 字段名暗示敏感（值需人工核验） |

> 底层 API：遍历 `DEX.get_classes()` → `ClassDefItem.get_static_values_off()` → `dex.raw.seek(off)` → `EncodedArrayItem(raw, cm).get_value()` → `EncodedArray.get_values()`，每个 EncodedValue 的 `get_value()` 取值，配对 `ClassDataItem.get_static_fields()` 字段名。值与字段名分别匹配敏感模式。`scanned_static_values` 是扫描的静态值总数。误报控制：`base64_long` 收紧到 40+ 字符（排除普通类名）。`api_key_field` 是字段名匹配（值可能是正则模式而非真密钥，需人工核验）。配 `dex static-values <class>` 查看完整静态值，配 `dex field-init-value` 查单字段。

### `apk attack-surface [--max-depth] [--include-safe]`

**攻击面聚合分析**——交叉引用 **导出组件**（manifest 暴露面）与其处理类 **前向可达的危险 sink**（字节码危险能力），直接产出"**外部可触发的入口 → 危险操作**"的攻击面地图。

与 `security-hotspots`（全局 sink 扫描，不区分入口是否可外部触达）、`apk component-details`（仅 manifest 属性，无字节码分析）、`method-reachable`（单方法正向可达，需手工指定入口）的区别：本命令**只从外部可达的入口出发**（导出且无权限保护的 Activity/Service/Receiver/Provider），对每个入口类前向 BFS 收集可达的危险 sink，是组件劫持 / 越权 / 污点分析的自动化起点。

```bash
# 分析所有暴露组件的攻击面（默认只看导出且无权限保护的组件）
androguard-skills apk attack-surface --apk-path test.apk

# 加深可达性深度，并把受保护/非导出组件也纳入
androguard-skills apk attack-surface --max-depth 6 --include-safe --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--max-depth` | 从组件类方法前向递归深度（默认 4） |
| `--per-sink-limit` | 每组件每类 sink 的调用样本上限（默认 10） |
| `--max-nodes` | 单组件 BFS 节点上限防爆（默认 2000） |
| `--include-safe` | 也分析非导出/受保护组件（默认只看暴露面） |

**输出：**
```json
{
  "package": "com.android.insecurebankv2",
  "exposed_component_count": 7,
  "analyzed_component_count": 7,
  "surface_sink_categories": {"command_exec": 1, "crypto": 3, "webview": 1, "...": "..."},
  "critical_component_count": 2,
  "critical_components": [
    {"type": "activity", "name": "...PostLogin", "critical_sinks": ["command_exec"]}
  ],
  "components": [
    {
      "type": "activity", "name": "...PostLogin",
      "exported": true, "permission": null, "exposed": true,
      "class_descriptor": "Lcom/android/insecurebankv2/PostLogin;",
      "class_resolved": true, "methods_explored": 40,
      "reachable_sink_categories": ["command_exec", "file_io", "intent_redirect"],
      "sinks": {"command_exec": {"count": 1, "samples": [{"from": "...", "calls": "Ljava/lang/Runtime;->exec...", "offset": 12, "depth": 2}]}}
    }
  ]
}
```

| 字段 | 说明 |
|------|------|
| `surface_sink_categories` | 全局聚合：每类危险 sink 在攻击面上出现于多少个组件 |
| `critical_components` | 暴露 + 可达高危 sink（`command_exec`/`dynamic_load`/`reflection`/`webview`/`sql` 任一）的组件——优先审计 |
| `components[].exposed` | 导出且无 permission/readPermission/writePermission 保护 |
| `components[].class_resolved` | 处理类是否在 DEX 中定位到（false = 框架类/缺失/混淆） |
| `components[].reachable_sink_categories` | 从该组件类前向可达的危险 sink 类别 |
| `sinks[cat].samples[].depth` | sink 调用点距组件入口方法的跳数 |

**sink 类别**：`reflection`/`command_exec`/`dynamic_load`/`crypto`/`network`/`file_io`/`webview`/`sql`/`intent_redirect`/`content_provider`。

> 底层 API：`APK.get_activities()/get_services()/get_receivers()/get_providers()` 取组件 + `get_attribute_value(tag, "exported"/"permission", name=...)` 判暴露（无显式 exported 时按 intent-filter 隐式推断），组件 dotted 名转 Dalvik 描述符后 `Analysis.get_class_analysis()` 定位处理类，从类内所有内部方法 BFS 展开 `MethodAnalysis.get_xref_to()` 到 `--max-depth`，沿途外部调用按 sink 正则分类。与 `analysis method-callers` 互为正/反向验证：本命令正向（入口→sink），method-callers 反向（sink→入口）。

## 相关命令

- [`analysis-callgraph`](analysis-callgraph.md) — 调用图导出为 DOT/图片（可视化）
- [`analysis-permissions`](analysis-permissions.md) — 单权限使用追踪
- [`apk requested-permissions`](apk-permissions-sdk.md) — APK 请求的权限分类
- [`util permission-mappings`](util.md) — 查看 API level 的方法→权限映射原始数据
