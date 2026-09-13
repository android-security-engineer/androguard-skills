# AndroGuard Skills

Android 逆向工程能力的 CLI 封装，所有命令输出 JSON，方便程序化调用。

## 输出契约（agent 对接保证）

- **纯 JSON**：stdout 只输出合法 JSON，诊断信息走 stderr，便于程序化解析。
- **确定性**：同一 APK 同一命令多次运行，输出字节级一致（CLI 单次模式与 daemon JSON-RPC 模式均如此）。列表已排序、字典按 key 重建，agent 可直接做哈希比对/差异检测，无需担心集合迭代序导致的抖动。已固化为 `tests/test_cli_output_determinism.py`（44 用例）+ `tests/test_daemon_output_determinism.py`（17 用例）。
- **结构化错误**：出错时返回 `{"error": "...", "error_type": "..."}` 而非 traceback。

## 快速开始

```bash
# 安装
pip install androguard

# 加载 APK（必须先执行）
androguard-skills load test.apk

# 查看 APK 基本信息
androguard-skills apk info --apk-path test.apk

# 查看权限
androguard-skills apk permissions --apk-path test.apk

# 查看签名
androguard-skills apk signature --apk-path test.apk
```

## 两种模式

### 单次执行模式（默认）

每次命令独立执行，自动加载 APK 并输出结果：

```bash
androguard-skills apk info --apk-path test.apk
```

需要指定 `--apk-path` 参数或设置环境变量 `ANDROGUARD_APK_PATH`：

```bash
export ANDROGUARD_APK_PATH=/path/to/test.apk
androguard-skills apk info
```

### Daemon 模式（推荐，避免重复解析）

启动后台常驻进程，已加载的 APK 缓存可用：

```bash
# 启动 daemon
androguard-skills daemon start

# 加载 APK（只需一次）
androguard-skills load test.apk

# 后续命令无需重复加载
androguard-skills apk info
androguard-skills apk permissions
androguard-skills dex classes --filter "Activity"

# 停止 daemon
androguard-skills daemon stop
```

CLI 会自动检测 daemon 是否运行：
- **有 daemon** → 通过 JSON-RPC 发送请求，复用已加载的 APK
- **无 daemon** → 自动降级为单次执行模式

**内存管理（长跑）**：daemon 连续 `load` 不同 APK 时，`load_apk` 会 gc 旧解析对象（Analysis 持有海量 xref 跨引用成环，纯引用计数无法回收）。但 glibc malloc 不主动归还 arena 给 OS，长跑下 RSS 仍会高位驻留。处理完一个 APK 且将空闲或切换上下文时，显式 `unload` 释放引用 + 调 `malloc_trim(0)` 归还 arena，RSS 即可回落：

```bash
androguard-skills load big.apk        # 解析大 APK（峰值高）
androguard-skills apk security-report  # 取完结果
androguard-skills unload               # 释放 + trim，RSS 回落
```

**日志与排障**：daemon 默认以 WARNING 级别把日志写入 `~/.androguard/skills/daemon.log`（5MB 轮转，保留 3 份）。需要详细日志时设环境变量 `LOGURU_LEVEL=DEBUG androguard-skills daemon start`（生产环境勿用低级别——AndroGuard 在 INFO 级别就会对每个类/方法打日志，解析大 APK 时产生数万行，可能拖慢 daemon）。daemon 不向 stderr 输出 AndroGuard 内部日志，避免后台启动时 stderr 管道阻塞导致死锁。

**批量请求**：daemon 支持 JSON-RPC 2.0 批量请求（数组），单连接一次发多个请求，服务端顺序执行并返回批量响应。批量内单个失败不影响其余。对接多 agent 或需连续查询时可减少 TCP 往返：

```bash
# 示例：一条 JSON-RPC 批量请求（每行一个请求对象，整体是数组）
echo '[{"jsonrpc":"2.0","method":"status","params":{},"id":1},
       {"jsonrpc":"2.0","method":"apk_info","params":{},"id":2}]' | \
  nc 127.0.0.1 8899
# → [{"jsonrpc":"2.0","result":{...},"id":1},{"jsonrpc":"2.0","result":{...},"id":2}]
```

## 命令索引

| 命令 | 说明 | 详细文档 |
|------|------|---------|
| `load <apk>` | 加载 APK | - |
| `load-dex <dex>` | 加载独立 DEX 文件 | [visualize.md](visualize.md) |
| `unload` | 卸载 APK + 释放对象 + trim 内存（daemon 长跑） | - |
| `daemon start/stop/status` | 管理 Daemon | - |
| `apk info` | APK 基本信息 | [apk-info.md](apk-info.md) |
| `apk permissions` | 权限分析 | [apk-permissions.md](apk-permissions.md) |
| `apk activities` | Activity 列表 | [apk-components.md](apk-components.md) |
| `apk services` | Service 列表 | [apk-components.md](apk-components.md) |
| `apk receivers` | Receiver 列表 | [apk-components.md](apk-components.md) |
| `apk providers` | Provider 列表 | [apk-components.md](apk-components.md) |
| `apk intent-filters <component>` | Intent Filter | [apk-components.md](apk-components.md) |
| `apk signature` | 签名验证 | [apk-signature.md](apk-signature.md) |
| `apk files` | 文件列表 | [apk-files.md](apk-files.md) |
| `apk manifest` | Manifest XML | [apk-info.md](apk-info.md) |
| `apk features` | uses-feature 列表 | [apk-features.md](apk-features.md) |
| `apk libraries` | uses-library 列表 | [apk-features.md](apk-features.md) |
| `apk icon` | 应用图标提取 | [apk-features.md](apk-features.md) |
| `apk file <filename>` | 提取文件内容 | [apk-file-extract.md](apk-file-extract.md) |
| `apk verify` | APK 完整性校验 | [apk-verify.md](apk-verify.md) |
| `apk signing-block` | v2/v3 签名块详情 | [apk-verify.md](apk-verify.md) |
| `apk verify-signature` | 密码学签名验证（签名者信息 vs .SF） | [apk-verify.md](apk-verify.md) |
| `apk manifest-attrs` | 批量 manifest 属性值 | [manifest-attrs.md](manifest-attrs.md) |
| `apk manifest-attr` | 单个 manifest 属性值 | [manifest-attrs.md](manifest-attrs.md) |
| `apk manifest-tags` | 按属性查找 manifest 标签 | [manifest-attrs.md](manifest-attrs.md) |
| `apk certificate` | 签名证书详情 | [apk-certificate.md](apk-certificate.md) |
| `apk files-info` | 文件详细信息 | [apk-certificate.md](apk-certificate.md) |
| `apk dex-data` | DEX 二进制提取 | [apk-certificate.md](apk-certificate.md) |
| `apk raw` | APK 原始字节提取 | [apk-certificate.md](apk-certificate.md) |
| `apk signing-versions` | 签名方案检测（v1/v2/v3/v31） | [apk-signing-advanced.md](apk-signing-advanced.md) |
| `apk certificates-scheme` | 按方案批量获取证书 | [apk-signing-advanced.md](apk-signing-advanced.md) |
| `apk certificates-der` | 证书 DER（base64） | [apk-signing-advanced.md](apk-signing-advanced.md) |
| `apk public-keys` | 签名公钥信息 | [apk-signing-advanced.md](apk-signing-advanced.md) |
| `apk signature-files` | 签名文件名+原始签名 | [apk-signing-advanced.md](apk-signing-advanced.md) |
| `apk files-crc32` | 文件 CRC32 校验表 | [apk-signing-advanced.md](apk-signing-advanced.md) |
| `apk fingerprint` | 签名公钥 SHA-256 指纹 | [apk-axml-packing.md](apk-axml-packing.md) |
| `apk manifest-axml` | AXML 加固检测 + 根标签属性 | [apk-axml-packing.md](apk-axml-packing.md) |
| `apk axml <filename>` | 任意 AXML 文件解码为可读 XML（布局/drawable/配置） | [apk-axml-packing.md](apk-axml-packing.md) |
| `apk declared-permissions` | 声明（自定义）权限 | [apk-permissions-sdk.md](apk-permissions-sdk.md) |
| `apk details-permissions` | 权限详情（保护级别/标签/描述） | [apk-permissions-sdk.md](apk-permissions-sdk.md) |
| `apk requested-permissions` | 请求权限分类（AOSP/第三方/隐含） | [apk-permissions-sdk.md](apk-permissions-sdk.md) |
| `apk sdk-versions` | SDK 版本信息 | [apk-permissions-sdk.md](apk-permissions-sdk.md) |
| `apk main-activities` | 主 Activity + 别名 | [apk-permissions-sdk.md](apk-permissions-sdk.md) |
| `apk device-features` | 设备特性（TV/Wearable/Multidex） | [apk-permissions-sdk.md](apk-permissions-sdk.md) |
| `apk files-types` | 文件类型识别 | [apk-permissions-sdk.md](apk-permissions-sdk.md) |
| `apk manifest-tree` | Manifest 标签树统计 | [apk-manifest-tree.md](apk-manifest-tree.md) |
| `apk find-tags-xml <xml> <tag>` | 指定 XML 文件查标签 | [apk-manifest-tree.md](apk-manifest-tree.md) |
| `apk cert-names` | 证书名规范化（主体/颁发者） | [apk-manifest-tree.md](apk-manifest-tree.md) |
| `apk res-value <name>` | 资源 ID 反解为字面值 | [apk-manifest-tree.md](apk-manifest-tree.md) |
| `apk dex-names` | DEX 文件名列表（multidex） | [apk-meta.md](apk-meta.md) |
| `apk signature-names` | 签名文件名列表 | [apk-meta.md](apk-meta.md) |
| `apk app-name` | 应用显示名（支持 locale） | [apk-meta.md](apk-meta.md) |
| `apk valid` | APK 结构有效性检查 | [apk-meta.md](apk-meta.md) |
| `apk duplicate-signatures` | 重复签名 ID 检测 | [apk-meta.md](apk-meta.md) |
| `apk security-overview` | 安全概览聚合（签名/权限/组件/标志/加固） | [apk-meta.md](apk-meta.md) |
| `apk native-libraries` | native 库列表（lib/&#60;abi&#62;/*.so，按 ABI 分组） | [apk-meta.md](apk-meta.md) |
| `apk application-flags` | &#60;application&#62; 安全属性审计（默认值推断 + 风险评级） | [apk-meta.md](apk-meta.md) |
| `apk component-details` | 组件安全属性详情（exported/permission/暴露风险标记） | [apk-components.md](apk-components.md) |
| `apk attack-surface` | 攻击面聚合（导出组件 × 前向可达危险 sink，入口→sink 地图） | [analysis-callgraph-permissions.md](analysis-callgraph-permissions.md) |
| `apk deeplinks` | 深链接枚举（intent-filter/data，web 可达性判定，外部入口攻击面） | [analysis-security-recon.md](analysis-security-recon.md) |
| `dex classes` | 类列表 | [dex-classes.md](dex-classes.md) |
| `dex methods` | 方法列表 | [dex-methods.md](dex-methods.md) |
| `dex strings` | 字符串搜索 | [dex-strings.md](dex-strings.md) |
| `dex strings-table` | 字符串常量池完整表（idx/offset/utf16_size） | [dex-disassemble.md](dex-disassemble.md) |
| `dex fields` | 字段列表 | [dex-methods.md](dex-methods.md) |
| `dex header` | DEX 头信息 | [dex-header.md](dex-header.md) |
| `dex class-names` | 快速类名列表 | [dex-header.md](dex-header.md) |
| `dex hidden-api` | 隐藏 API 检测 | [dex-header.md](dex-header.md) |
| `dex disassemble` | 字节码反汇编 | [dex-disassemble.md](dex-disassemble.md) |
| `dex hierarchy` | 类继承层级树 | [dex-disassemble.md](dex-disassemble.md) |
| `dex stats` | DEX 统计信息 | [dex-disassemble.md](dex-disassemble.md) |
| `dex class <name>` | 类详细信息 | [dex-disassemble.md](dex-disassemble.md) |
| `dex class-meta <class>` | 类底层元信息（注解/源文件/接口/偏移） | [dex-disassemble.md](dex-disassemble.md) |
| `dex class-data <class>` | 类方法/字段分类视图（direct/virtual+static/instance） | [dex-disassemble.md](dex-disassemble.md) |
| `dex regex-strings` | 正则搜索字符串（高效） | [dex-disassemble.md](dex-disassemble.md) |
| `dex debug-info` | 调试信息 | [dex-disassemble.md](dex-disassemble.md) |
| `dex method-info <c> <m>` | 方法签名信息（寄存器/参数映射） | [dex-disassemble.md](dex-disassemble.md) |
| `dex method-instructions <c> <m>` | 按方法反汇编全部指令（指令流） | [dex-disassemble.md](dex-disassemble.md) |
| `dex method-instructions-idx <c> <m>` | 按方法反汇编指令（带字节偏移 idx） | [dex-disassemble.md](dex-disassemble.md) |
| `dex method-code <c> <m>` | 方法 DalvikCode 底层（寄存器帧 + try/catch + handlers） | [dex-disassemble.md](dex-disassemble.md) |
| `dex proto-ids` | 方法原型表（ProtoIdItem：shorty/return/parameters） | [dex-disassemble.md](dex-disassemble.md) |
| `dex type-ids` | 类型常量池表（type_ids：descriptor_idx → 类型描述符） | [dex-disassemble.md](dex-disassemble.md) |
| `dex annotations` | 注解目录（类/字段/方法/参数，含 visibility/elements） | [dex-disassemble.md](dex-disassemble.md) |
| `dex static-values <class>` | 类静态值数组（所有 static 字段初始值，硬编码常量批量检测） | [dex-disassemble.md](dex-disassemble.md) |
| `dex encoded-fields` | 底层字段表 | [dex-encoded.md](dex-encoded.md) |
| `dex encoded-methods` | 底层方法表（含 code_off） | [dex-encoded.md](dex-encoded.md) |
| `dex encoded-method <name>` | 按名查方法（跨类） | [dex-encoded.md](dex-encoded.md) |
| `dex encoded-method-descriptor` | 按描述符精确查方法 | [dex-encoded.md](dex-encoded.md) |
| `dex cm-lookup <idx>` | ClassManager 常量池查询 | [dex-encoded.md](dex-encoded.md) |
| `dex fields-id` | 字段索引表（FieldIdItem） | [dex-encoded.md](dex-encoded.md) |
| `dex version` | DEX 版本号 | [dex-encoded.md](dex-encoded.md) |
| `dex items` | 底层 item 表（offset/length） | [dex-items.md](dex-items.md) |
| `dex lens` | 各表条目计数 | [dex-items.md](dex-items.md) |
| `dex class-manager` | ClassManager 概要 | [dex-items.md](dex-items.md) |
| `dex encoded-fields-class <class>` | 指定类的字段表 | [dex-encoded.md](dex-encoded.md) |
| `dex encoded-methods-class <class>` | 指定类的方法表 | [dex-encoded.md](dex-encoded.md) |
| `dex encoded-method-by-idx <idx>` | 按 idx 查方法 | [dex-encoded.md](dex-encoded.md) |
| `dex encoded-field-by-name <name>` | 按名查字段（跨类） | [dex-encoded.md](dex-encoded.md) |
| `dex encoded-field-descriptor <c> <f> <d>` | 按描述符精确查字段 | [dex-encoded.md](dex-encoded.md) |
| `dex encoded-method-class-method <c> <m>` | 类内按名查方法（无需 descriptor） | [dex-encoded.md](dex-encoded.md) |
| `dex method-id-by-name <name>` | 常量池按名查方法（含外部引用） | [dex-encoded.md](dex-encoded.md) |
| `dex method-ids` | 常量池方法全量表（含外部引用） | [dex-encoded.md](dex-encoded.md) |
| `dex field-id-by-name <name>` | 常量池按名查字段（含外部引用） | [dex-encoded.md](dex-encoded.md) |
| `dex field-init-value <c> <f>` | 字段初始值（硬编码常量检测） | [dex-encoded.md](dex-encoded.md) |
| `analysis xrefs-from <class>` | 谁引用了此类 | [analysis-xrefs.md](analysis-xrefs.md) |
| `analysis xrefs-to <class>` | 此类引用了谁 | [analysis-xrefs.md](analysis-xrefs.md) |
| `analysis method-xrefs <class> <method>` | 方法交叉引用 | [analysis-xrefs.md](analysis-xrefs.md) |
| `analysis callgraph` | 调用图导出 | [analysis-callgraph.md](analysis-callgraph.md) |
| `analysis find-classes <pattern>` | 搜索类 | [dex-classes.md](dex-classes.md) |
| `analysis find-methods <pattern>` | 搜索方法 | [dex-methods.md](dex-methods.md) |
| `analysis find-strings <pattern>` | 搜索字符串 | [dex-strings.md](dex-strings.md) |
| `analysis permission-usage <perm>` | 权限使用追踪 | [analysis-permissions.md](analysis-permissions.md) |
| `analysis api-usage` | API 使用分析 | [analysis-permissions.md](analysis-permissions.md) |
| `analysis internal-classes` | 内部类列表 | [analysis-classes-methods.md](analysis-classes-methods.md) |
| `analysis external-classes` | 外部类列表 | [analysis-classes-methods.md](analysis-classes-methods.md) |
| `analysis internal-methods` | 内部方法列表 | [analysis-classes-methods.md](analysis-classes-methods.md) |
| `analysis external-methods` | 外部方法列表 | [analysis-classes-methods.md](analysis-classes-methods.md) |
| `analysis field-xrefs <class> <field>` | 字段交叉引用 | [analysis-field-xrefs.md](analysis-field-xrefs.md) |
| `analysis field-xrefs-detail <class> <field>` | 字段引用详情（含 offset，不去重） | [analysis-field-xrefs.md](analysis-field-xrefs.md) |
| `analysis find-fields <pattern>` | 搜索字段 | [analysis-field-xrefs.md](analysis-field-xrefs.md) |
| `analysis find-fields-advanced` | 多维正则字段查找 | [analysis-fields.md](analysis-fields.md) |
| `analysis find-methods-advanced` | 五维正则方法查找（类/名/描述符/访问标志/no-external） | [analysis-fields.md](analysis-fields.md) |
| `analysis find-classes-advanced` | 类名正则 + no-external 查找（含外部/API/方法数元信息） | [analysis-fields.md](analysis-fields.md) |
| `analysis field-analysis <c> <f>` | 字段完整分析（含 xref） | [analysis-fields.md](analysis-fields.md) |
| `analysis class-fields <class>` | 类内全部字段 + 读写计数 | [analysis-fields.md](analysis-fields.md) |
| `analysis class-fields-xref <class>` | 类内字段完整读写来源（哪些方法读/写） | [analysis-fields.md](analysis-fields.md) |
| `analysis permissions-map` | 完整权限映射 | [analysis-field-xrefs.md](analysis-field-xrefs.md) |
| `analysis class-exists <class>` | 类存在性检查 | [analysis-lookup.md](analysis-lookup.md) |
| `analysis method-analysis <c> <m> <d>` | 精确方法分析（含 xref） | [analysis-lookup.md](analysis-lookup.md) |
| `analysis strings-analysis` | 全量字符串分析 | [analysis-lookup.md](analysis-lookup.md) |
| `analysis get-method <c> <m> <d>` | EncodedMethod 元数据 | [analysis-lookup.md](analysis-lookup.md) |
| `analysis class-hierarchy-info <c>` | 类继承信息（extends/implements） | [analysis-class-method-detail.md](analysis-class-method-detail.md) |
| `analysis class-xref-new-instance <c>` | new-instance 交叉引用 | [analysis-class-method-detail.md](analysis-class-method-detail.md) |
| `analysis class-xref-const-class <c>` | const-class 交叉引用 | [analysis-class-method-detail.md](analysis-class-method-detail.md) |
| `analysis class-detail <c>` | 类综合信息（方法数/xref 统计） | [analysis-class-method-detail.md](analysis-class-method-detail.md) |
| `analysis method-detail <c> <m> <d>` | 方法综合信息（full_name/基本块数） | [analysis-class-method-detail.md](analysis-class-method-detail.md) |
| `analysis method-api-info <c> <m> <d>` | 方法 API/权限标注（is_android_api/apilist） | [analysis-class-method-detail.md](analysis-class-method-detail.md) |
| `analysis method-basic-blocks <c> <m> <d>` | 方法基本块（CFG 节点） | [analysis-class-method-detail.md](analysis-class-method-detail.md) |
| `analysis method-exceptions <c> <m> <d>` | 方法 try/catch 异常表 | [analysis-class-method-detail.md](analysis-class-method-detail.md) |
| `analysis method-xrefs-detail <c> <m> <d>` | 方法级 xref 完整引用列表（6 类） | [analysis-class-method-detail.md](analysis-class-method-detail.md) |
| `analysis method-summary <c> <m>` | 方法全貌聚合（信息+xref+CFG+源码） | [analysis-class-method-detail.md](analysis-class-method-detail.md) |
| `analysis method-reachable <c> <m>` | 方法可达性（递归 xref_to 展开，调用链/污点路径） | [analysis-class-method-detail.md](analysis-class-method-detail.md) |
| `analysis method-callers <c> <m>` | 方法反向可达性（递归 xref_from，sink 溯源/入口定位） | [analysis-class-method-detail.md](analysis-class-method-detail.md) |
| `analysis method-block-instructions <c> <m>` | 按基本块反汇编（CFG 节点级指令流） | [analysis-class-method-detail.md](analysis-class-method-detail.md) |
| `analysis method-switch-payloads <c> <m>` | switch 分支表（case→目标）+ fill-array-data 数组 payload 解码 | [analysis-class-method-detail.md](analysis-class-method-detail.md) |
| `analysis strings-overwritten` | 被覆盖字符串（混淆检测） | [analysis-class-method-detail.md](analysis-class-method-detail.md) |
| `analysis string-info <value>` | 单字符串详情（orig/当前值 + xref） | [analysis-class-method-detail.md](analysis-class-method-detail.md) |
| `analysis call-graph` | 完整调用图（节点+边） | [analysis-callgraph-permissions.md](analysis-callgraph-permissions.md) |
| `analysis call-graph-filtered` | 过滤子调用图（按类/方法/标志） | [analysis-callgraph-permissions.md](analysis-callgraph-permissions.md) |
| `analysis permissions` | API 方法→权限映射（批量） | [analysis-callgraph-permissions.md](analysis-callgraph-permissions.md) |
| `analysis android-api-usage` | 全量 Android API 使用（批量，可展开调用方） | [analysis-callgraph-permissions.md](analysis-callgraph-permissions.md) |
| `analysis security-hotspots` | 安全热点批量扫描（反射/加密/exec/native 等） | [analysis-callgraph-permissions.md](analysis-callgraph-permissions.md) |
| `analysis hardcoded-secrets` | 硬编码密钥扫描（static 值中的 API key/URL/私钥/JWT） | [analysis-callgraph-permissions.md](analysis-callgraph-permissions.md) |
| `analysis native-methods` | JNI 边界枚举（native 方法 + 调用方，定位 .so 入口） | [analysis-security-recon.md](analysis-security-recon.md) |
| `analysis crypto-usage` | 加密用法聚合（算法字符串还原 + 弱加密标记 + 密钥材料） | [analysis-security-recon.md](analysis-security-recon.md) |
| `analysis reflection-targets` | 反射目标还原（forName/loadClass/invoke 目标静态解析） | [analysis-security-recon.md](analysis-security-recon.md) |
| `analysis url-endpoints` | 网络端点提取（URL/host/IP 分类 + 引用方） | [analysis-security-recon.md](analysis-security-recon.md) |
| `analysis taint-path` | 源→汇调用路径搜索（前向 BFS 重建具体调用链） | [analysis-security-recon.md](analysis-security-recon.md) |
| `analysis webview-security` | WebView 安全配置审计（JS 桥/file 访问/调试/混合内容，7 类归类 + 高危 findings） | [analysis-security-recon.md](analysis-security-recon.md) |
| `analysis ssl-safety` | SSL 校验绕过检测（无 throw 的 TrustManager/恒真 HostnameVerifier/绕过 API → MITM 判定） | [analysis-security-recon.md](analysis-security-recon.md) |
| `analysis insecure-storage` | 不安全存储审计（外部存储/世界可读写/明文 prefs+db，OWASP M9） | [analysis-security-recon.md](analysis-security-recon.md) |
| `analysis sql-injection` | SQL 注入面审计（rawQuery/execSQL/query 执行点枚举，OWASP M7） | [analysis-security-recon.md](analysis-security-recon.md) |
| `analysis pending-intent` | PendingIntent 可变性审计（FLAG_IMMUTABLE 缺失 + Intent 重定向面） | [analysis-security-recon.md](analysis-security-recon.md) |
| `analysis privacy-sinks` | 隐私采集审计（设备标识/位置/联系人/剪贴板/录音摄像，OWASP M6） | [analysis-security-recon.md](analysis-security-recon.md) |
| `analysis telephony-sms` | 电话短信滥用审计（发/读短信、拨号、短信拦截，扣费/拦截马特征） | [analysis-security-recon.md](analysis-security-recon.md) |
| `analysis dynamic-code` | 动态代码加载审计（DexClassLoader/native 库/反射加载，脱壳/payload） | [analysis-security-recon.md](analysis-security-recon.md) |
| `analysis persistence` | 持久化/后台驻留审计（设备管理员/无障碍/定时任务/通知监听） | [analysis-security-recon.md](analysis-security-recon.md) |
| `analysis weak-random` | 不安全随机审计（java.util.Random/固定种子 vs SecureRandom，OWASP M10） | [analysis-security-recon.md](analysis-security-recon.md) |
| `analysis broadcast-safety` | 广播收发安全审计（无权限广播/动态 receiver/粘性广播） | [analysis-security-recon.md](analysis-security-recon.md) |
| `analysis provider-safety` | ContentProvider 安全审计（openFile 路径穿越/URI 权限授予） | [analysis-security-recon.md](analysis-security-recon.md) |
| `analysis anti-analysis` | 反分析侦察（root/模拟器/调试器/Frida/Xposed 检测，串+API 双路） | [analysis-security-recon.md](analysis-security-recon.md) |
| `analysis network-security` | 网络安全配置审计（明文 URL/证书固定/SSL 上下文/HTTP 客户端） | [analysis-security-recon.md](analysis-security-recon.md) |
| `analysis obfuscation-metrics` | 混淆度量（类名长度/反射密度/字符串覆盖 → 0-100 加固评分） | [analysis-security-recon.md](analysis-security-recon.md) |
| `apk security-report` | 一键全量安全报告（聚合 19 域审计 + 综合风险评分，审计套件闭环） | [analysis-security-recon.md](analysis-security-recon.md) |
| `resources packages` | 资源包名列表 | [resources.md](resources.md) |
| `resources locales <package>` | 支持语言列表 | [resources.md](resources.md) |
| `resources types <package>` | 资源类型列表 | [resources.md](resources.md) |
| `resources configs <rid>` | 资源配置变体 | [resources.md](resources.md) |
| `resources strings` | 字符串资源 | [resources.md](resources.md) |
| `resources bool <package>` | 布尔类型资源 | [resources.md](resources.md) |
| `resources color <package>` | 颜色类型资源 | [resources.md](resources.md) |
| `resources dimen <package>` | 尺寸类型资源 | [resources.md](resources.md) |
| `resources integer <package>` | 整数类型资源 | [resources.md](resources.md) |
| `resources id` | 资源 ID 双向查询 | [resources.md](resources.md) |
| `resources string-resources <pkg>` | strings.xml 导出 | [resources.md](resources.md) |
| `resources strings-all` | 全量 strings.xml | [resources.md](resources.md) |
| `resources public <pkg>` | public.xml 资源映射 | [resources.md](resources.md) |
| `resources id-resources <pkg>` | ids.xml 导出 | [resources.md](resources.md) |
| `resources get-string <pkg> <name>` | 精确取单个字符串值 | [resources.md](resources.md) |
| `resources xml-name <rid>` | 资源 ID→XML 名称（@pkg:type/name） | [resources.md](resources.md) |
| `resources type-configs <pkg> [--type]` | 类型配置变体（locale/密度） | [resources.md](resources.md) |
| `resources res-configs <rid>` | 按 ID 查配置变体（原始 entry） | [resources.md](resources.md) |
| `resources value <rid> [--package]` | 按 ID 取类型化解析值（推断类型+主值） | [resources.md](resources.md) |
| `resources resolved-strings [--locale]` | 全量解析字符串（三层结构） | [resources.md](resources.md) |
| `visualize method-dot <class> <method>` | CFG 导出为 DOT | [visualize.md](visualize.md) |
| `visualize method-image <class> <method>` | CFG 导出为图片 | [visualize.md](visualize.md) |
| `visualize method-json <class> <method>` | CFG 导出为 JSON | [visualize.md](visualize.md) |
| `decompile class <class>` | 反编译类 | [decompiler.md](decompiler.md) |
| `decompile method <class> <method>` | 反编译方法 | [decompiler.md](decompiler.md) |
| `decompile method-ast <c> <m>` | 反编译方法 AST（结构化语法树） | [decompiler.md](decompiler.md) |
| `decompile method-tokens <c> <m>` | 反编译方法 token 流（词法 token） | [decompiler.md](decompiler.md) |
| `decompile class-ast <class>` | 反编译类 AST（类级语法树，含全部方法/字段） | [decompiler.md](decompiler.md) |
| `decompile class-tokens <class>` | 反编译类 token 流（类级词法 token） | [decompiler.md](decompiler.md) |
| `pentest trace <apk>` | Frida 追踪 | [pentest.md](pentest.md) |
| `pentest dump <package>` | 内存 Dump | [pentest.md](pentest.md) |
| `util detect <filename>` | 文件类型检测（APK/DEX/ELF） | [util.md](util.md) |
| `util permissions <apilevel>` | AOSP 权限定义 | [util.md](util.md) |
| `util permission-mappings <apilevel>` | 方法→权限映射 | [util.md](util.md) |
| `util api-levels` | 可用权限数据 API level | [util.md](util.md) |
| `util format <value> [--to]` | 类名/描述符格式转换（Dalvik/Java/Python） | [util.md](util.md) |
| `session analyze-apk <apk>` | Session 一步分析 APK（单次可用） | [session.md](session.md) |
| `session create` | 创建 Session（daemon 模式跨命令持久） | [session.md](session.md) |
| `session add-apk <apk>` | 向 Session 添加 APK（多文件关联） | [session.md](session.md) |
| `session add-dex <dex>` | 向 Session 添加独立 DEX | [session.md](session.md) |
| `session info` | Session 概要（APK/DEX 计数 + 字符串数） | [session.md](session.md) |
| `session filename-by-class <class>` | 类所属文件定位（多 APK 关联） | [session.md](session.md) |
| `session strings` | 跨 DEX 字符串统计 | [session.md](session.md) |
| `session classes` | 跨 DEX 类列表（按 DEX 分组） | [session.md](session.md) |

## Python API 使用

也可以直接在 Python 中使用：

```python
from androguard.skills import AndroguardSkillsMain
import json

skills = AndroguardSkillsMain()
result = skills.load_apk("test.apk")
print(json.dumps(result, indent=2))

# 查看权限
perms = skills.apk_permissions()
print(json.dumps(perms, indent=2))

# 搜索包含 "password" 的字符串
strings = skills.dex_strings(filter_regex="password")
print(json.dumps(strings, indent=2))
```

## 输出格式

所有命令输出 JSON，结构统一：

```json
{
  "field1": "value1",
  "field2": "value2",
  ...
}
```

错误时输出：

```json
{
  "error": "Error message"
}
```
