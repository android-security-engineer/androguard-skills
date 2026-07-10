# 模块：analysis_skills

> 📌 静态分析与安全审计核心：交叉引用、调用图、可达性、污点路径、OWASP 专项审计、一键安全报告，共 71 个公开函数。

## 🧩 概述

`analysis_skills.py` 是业务层体量最大、能力最深的模块（71 个公开函数）。它围绕 `androguard.core.analysis.Analysis` 对象展开，覆盖三大类能力：

1. **交叉引用与检索**：类/方法/字段的 xref（from/to/read/write/new_instance/const_class 六类）、正则搜索、多维高级搜索。
2. **图分析**：networkx 调用图、子图过滤、方法前向可达性、调用方反向溯源、源→汇最短调用路径（污点传播）。
3. **安全审计**：20+ 个 OWASP Mobile 专项审计命令（WebView/SSL/存储/SQL 注入/PendingIntent/隐私 sink/电话短信/动态代码/持久化/弱随机/广播/Provider/反分析/网络/混淆度量），以及攻击面聚合与一键全量安全报告。

在三层架构中位于**业务层**：第一参数多为 `analysis_obj`（由 `load_apk` 时 `AnalyzeAPK` 得到的 `Analysis`），输出是结构化字典。多数图分析与审计函数内部先 `analysis_obj.create_xref()` 确保 xref 已建立。遵循模块级函数约定，无类、无状态。

## 🔧 公开方法

| 方法名 | 签名 | 说明 | 对应 CLI 命令 |
|--------|------|------|-------------|
| `analysis_xrefs_from` | `(analysis_obj, class_name)` | 谁引用了指定类（XrefFrom） | `analysis xrefs-from` |
| `analysis_xrefs_to` | `(analysis_obj, class_name)` | 指定类引用了谁（XrefTo） | `analysis xrefs-to` |
| `analysis_method_xrefs` | `(analysis_obj, class_name, method_name)` | 指定方法的交叉引用 | `analysis method-xrefs` |
| `analysis_find_classes` | `(analysis_obj, pattern)` | 正则搜索类 | `analysis find-classes` |
| `analysis_find_methods` | `(analysis_obj, pattern)` | 正则搜索方法 | `analysis find-methods` |
| `analysis_find_strings` | `(analysis_obj, pattern)` | 正则搜索字符串 | `analysis find-strings` |
| `analysis_callgraph` | `(analysis_obj, apk_obj, output, fmt='gml')` | 生成调用图并导出为指定格式 | `analysis callgraph` |
| `analysis_permission_usage` | `(analysis_obj, permission)` | 追踪指定权限的使用情况 | `analysis permission-usage` |
| `analysis_internal_classes` | `(analysis_obj, filter_regex=None)` | 应用内部类列表（非外部依赖） | `analysis internal-classes` |
| `analysis_external_classes` | `(analysis_obj, filter_regex=None)` | 外部依赖类列表 | `analysis external-classes` |
| `analysis_internal_methods` | `(analysis_obj, filter_regex=None)` | 应用内部方法列表 | `analysis internal-methods` |
| `analysis_external_methods` | `(analysis_obj, filter_regex=None)` | 外部方法列表 | `analysis external-methods` |
| `analysis_field_xrefs` | `(analysis_obj, class_name, field_name)` | 指定字段的交叉引用 | `analysis field-xrefs` |
| `analysis_field_xrefs_detail` | `(analysis_obj, class_name, field_name)` | 字段读/写引用完整列表（含 offset，不去重） | `analysis field-xrefs-detail` |
| `analysis_find_fields` | `(analysis_obj, pattern)` | 正则搜索字段 | `analysis find-fields` |
| `analysis_permissions_map` | `(analysis_obj)` | 完整权限映射 | `analysis permissions-map` |
| `analysis_class_exists` | `(analysis_obj, class_name)` | 类是否存在（快速布尔判断） | `analysis class-exists` |
| `analysis_method_analysis` | `(analysis_obj, class_name, method_name, descriptor)` | 按 class+method+descriptor 精确取方法分析（含完整 xref） | `analysis method-analysis` |
| `analysis_strings_analysis` | `(analysis_obj, limit=None)` | 全部字符串分析（含引用位置） | `analysis strings-analysis` |
| `analysis_get_method` | `(analysis_obj, class_name, method_name, descriptor)` | 取底层 EncodedMethod（含访问标志等元数据） | `analysis get-method` |
| `analysis_find_fields_advanced` | `(analysis_obj, classname='.*', fieldname='.*', fieldtype='.*', accessflags='.*', limit=None, with_xrefs=False)` | 多维正则字段查找（Analysis 原生 find_fields） | `analysis find-fields-advanced` |
| `analysis_field_analysis` | `(analysis_obj, class_name, field_name)` | 字段完整分析（含 read/write xref 详情） | `analysis field-analysis` |
| `analysis_api_usage_grouped` | `(analysis_obj, limit=None, group_by_class=False)` | 使用的 Android API（可选按类分组） | `analysis api-usage` |
| `analysis_class_hierarchy_info` | `(analysis_obj, class_name)` | 继承关系（父类+接口） | `analysis class-hierarchy-info` |
| `analysis_class_xref_new_instance` | `(analysis_obj, class_name)` | 谁实例化了指定类（new-instance xref） | `analysis class-xref-new-instance` |
| `analysis_class_xref_const_class` | `(analysis_obj, class_name)` | 谁引用了指定类的 Class 对象（const-class xref） | `analysis class-xref-const-class` |
| `analysis_class_detail` | `(analysis_obj, class_name)` | 类综合分析（继承/接口/方法数/xref 统计/vm_class） | `analysis class-detail` |
| `analysis_method_basic_blocks` | `(analysis_obj, class_name, method_name, descriptor)` | 方法基本块 BasicBlock 列表 | `analysis method-basic-blocks` |
| `analysis_method_exceptions` | `(analysis_obj, class_name, method_name, descriptor)` | 方法 try/catch 异常处理表 | `analysis method-exceptions` |
| `analysis_method_detail` | `(analysis_obj, class_name, method_name, descriptor)` | 方法综合分析（full_name/access/length/各类 xref 统计） | `analysis method-detail` |
| `analysis_method_xrefs_detail` | `(analysis_obj, class_name, method_name, descriptor)` | 方法级 xref 完整列表（6 类） | `analysis method-xrefs-detail` |
| `analysis_strings_overwritten` | `(analysis_obj)` | 被覆盖的字符串（运行时被改原值） | `analysis strings-overwritten` |
| `analysis_call_graph` | `(analysis_obj, limit=None, external=False)` | 完整调用图（networkx DiGraph）并序列化 | `analysis call-graph` |
| `analysis_call_graph_filtered` | `(analysis_obj, classname=None, methodname=None, descriptor=None, accessflags=None, no_isolated=False, external=False, limit=None)` | 按类/方法/描述符/访问标志过滤的子调用图 | `analysis call-graph-filtered` |
| `analysis_permissions` | `(analysis_obj, apilevel=None, limit=None)` | 基于 API level 的方法→权限映射（get_permissions） | `analysis permissions` |
| `analysis_method_api_info` | `(analysis_obj, class_name, method_name, descriptor)` | 方法的 API 与权限标注属性 | `analysis method-api-info` |
| `analysis_method_summary` | `(dex_list, analysis_obj, class_name, method_name, descriptor=None, include_source=True, xref_limit=10)` | 聚合方法全部分析信息（一键出方法全貌） | `analysis method-summary` |
| `analysis_android_api_usage` | `(analysis_obj, limit=None, with_xrefs=False)` | 批量列出使用的所有 Android 平台 API 方法 | `analysis android-api-usage` |
| `analysis_class_fields` | `(analysis_obj, class_name, limit=None)` | 类全部字段及 xref 统计（类级字段视图） | `analysis class-fields` |
| `analysis_string_info` | `(analysis_obj, value, xref_limit=None)` | 按精确字符串值查单字符串完整分析详情 | `analysis string-info` |
| `analysis_security_hotspots` | `(analysis_obj, limit=50)` | 安全热点批量扫描（按危险调用模式扫所有内部方法） | `analysis security-hotspots` |
| `analysis_class_fields_xref` | `(analysis_obj, class_name, xref_limit=20)` | 类内所有字段完整读写 xref | `analysis class-fields-xref` |
| `analysis_hardcoded_secrets` | `(analysis_obj, dex_list, limit=100)` | 扫描静态值数组检测硬编码敏感字符串 | `analysis hardcoded-secrets` |
| `analysis_method_reachable` | `(analysis_obj, class_name, method_name, descriptor=None, max_depth=3, include_external=False, max_nodes=5000)` | 方法前向可达性（递归展开 xref_to 到 max_depth） | `analysis method-reachable` |
| `analysis_method_block_instructions` | `(analysis_obj, class_name, method_name, descriptor=None, ins_limit_per_block=None)` | 按基本块反汇编方法指令（CFG 节点级视图） | `analysis method-block-instructions` |
| `analysis_method_switch_payloads` | `(analysis_obj, class_name, method_name, descriptor=None)` | 解析 switch 分支表与 fill-array-data 数组 payload | `analysis method-switch-payloads` |
| `analysis_method_callers` | `(analysis_obj, class_name, method_name, descriptor=None, max_depth=3, include_external=False, max_nodes=5000)` | 方法反向可达性（调用方溯源，递归展开 xref_from） | `analysis method-callers` |
| `apk_attack_surface` | `(apk_obj, analysis_obj, max_depth=4, per_sink_limit=10, max_nodes_per_component=2000, include_safe=False)` | 攻击面聚合（导出组件 × 前向可达危险 sink） | `apk attack-surface` |
| `analysis_native_methods` | `(analysis_obj, limit=200)` | 枚举所有 native 方法（JNI 边界） | `analysis native-methods` |
| `analysis_crypto_usage` | `(analysis_obj, per_type_limit=100)` | 加密 API 用法聚合 + 算法串还原 + 弱加密标记 | `analysis crypto-usage` |
| `analysis_reflection_targets` | `(analysis_obj, per_type_limit=100)` | 反射调用点 + 反射目标字符串还原（反混淆） | `analysis reflection-targets` |
| `analysis_url_endpoints` | `(analysis_obj, per_type_limit=200)` | 网络端点提取（URL/主机/IP + 引用方法） | `analysis url-endpoints` |
| `analysis_taint_path` | `(analysis_obj, src_class, src_method, dst_class, dst_method, src_descriptor=None, dst_descriptor=None, max_depth=8, max_nodes=20000)` | 源→汇最短前向调用路径搜索（污点传播） | `analysis taint-path` |
| `analysis_webview_security` | `(analysis_obj, per_type_limit=100)` | WebView 安全配置审计 | `analysis webview-security` |
| `analysis_ssl_safety` | `(analysis_obj, per_type_limit=100)` | SSL/TLS 校验绕过检测（自定义 TrustManager/HostnameVerifier） | `analysis ssl-safety` |
| `analysis_insecure_storage` | `(analysis_obj, per_type_limit=100)` | 不安全数据存储审计（OWASP M9） | `analysis insecure-storage` |
| `analysis_sql_injection` | `(analysis_obj, per_type_limit=100)` | SQL 注入面审计（OWASP M7） | `analysis sql-injection` |
| `analysis_pending_intent` | `(analysis_obj, per_type_limit=100)` | PendingIntent 可变性审计（Intent 重定向/CVE 类） | `analysis pending-intent` |
| `analysis_privacy_sinks` | `(analysis_obj, per_type_limit=100)` | 隐私数据收集审计（OWASP M6） | `analysis privacy-sinks` |
| `analysis_telephony_sms` | `(analysis_obj, per_type_limit=100)` | 电话短信滥用审计 | `analysis telephony-sms` |
| `analysis_dynamic_code` | `(analysis_obj, per_type_limit=100)` | 动态代码加载审计（DexClassLoader/native 加载/defineClass） | `analysis dynamic-code` |
| `analysis_persistence` | `(analysis_obj, per_type_limit=100)` | 持久化/后台驻留审计（定时/闹钟/前台服务/设备管理员/无障碍） | `analysis persistence` |
| `analysis_weak_random` | `(analysis_obj, per_type_limit=100)` | 不安全随机数审计（OWASP M10） | `analysis weak-random` |
| `analysis_broadcast_safety` | `(analysis_obj, per_type_limit=100)` | 广播收发安全审计 | `analysis broadcast-safety` |
| `analysis_provider_safety` | `(analysis_obj, per_type_limit=100)` | ContentProvider 安全审计（openFile 路径穿越/URI 权限） | `analysis provider-safety` |
| `analysis_anti_analysis` | `(analysis_obj, per_type_limit=100)` | 反分析/加固对抗侦察（root/模拟器/调试器/Frida/Xposed） | `analysis anti-analysis` |
| `analysis_network_security` | `(analysis_obj, per_type_limit=100)` | 网络安全配置审计（明文 URL/证书固定/SSL 上下文） | `analysis network-security` |
| `analysis_obfuscation_metrics` | `(analysis_obj)` | 混淆度量（类名长度/反射密度/字符串覆盖/DEX 特征） | `analysis obfuscation-metrics` |
| `apk_security_report` | `(apk_obj, analysis_obj, dex_list=None, per_type_limit=20)` | 一键全量安全报告（聚合所有专项审计 + 风险评分） | `apk security-report` |
| `analysis_find_methods_advanced` | `(analysis_obj, classname='.*', methodname='.*', descriptor='.*', accessflags='.*', no_external=False, limit=500)` | 多维正则方法搜索（Analysis 原生 find_methods） | `analysis find-methods-advanced` |
| `analysis_find_classes_advanced` | `(analysis_obj, name='.*', no_external=False, limit=500)` | 多维正则类搜索（Analysis 原生 find_classes） | `analysis find-classes-advanced` |

## 🧩 关键实现要点

- **六类 xref 体系**：`analysis_method_xrefs_detail` 一次返回方法级 6 类交叉引用——from（谁调用我）/to（我调用谁）/read（字段读）/write（字段写）/new_instance（谁 new 了我）/const_class（谁引用了我的 Class 对象），覆盖 Dalvik 字节码中所有跨方法/跨类的引用形态。类级对称有 `analysis_xrefs_from/to`、`analysis_class_xref_new_instance/const_class`。
- **图分析与防爆**：`analysis_method_reachable`（前向）与 `analysis_method_callers`（反向）都基于 `xref_to` / `xref_from` 递归展开，默认 `max_depth=3`、`max_nodes=5000`，默认只递归内部方法（`include_external=False`）避免外部 API 调用链爆炸。`analysis_taint_path` 在调用图上做源→汇最短路径搜索（BFS），`max_depth=8` / `max_nodes=20000`，用于污点传播路径取证。所有图函数入口先 `analysis_obj.create_xref()` 兜底。
- **专项审计统一形态**：20+ 个 `analysis_*_security/safety/usage` 审计函数签名高度一致（`analysis_obj, per_type_limit=100`），内部按危险 API 模式扫描所有内部方法的 xref，输出 `findings` 列表 + 每条含调用方法/偏移/匹配模式。`apk_attack_surface` 把「导出组件」（来自 APK manifest）与「前向可达的危险 sink」（来自 analysis 可达性）交叉，输出每个组件触达的 sink 列表，是组件级攻击面取证入口。
- **`apk_security_report` 一键聚合**：调用所有专项审计命令，聚合输出顶层风险总览 + 综合风险评分，是本模块的「拔河终点」入口。`analysis_method_summary` 则是方法级聚合（xref + 基本块 + 异常表 + 可选源码），一键出方法全貌。两个聚合函数都容忍子调用失败（逐项 try/except），保证整体不因单项报错而腐化。

## 🔗 与 CLI 的映射

`main.py` 的 `analysis` 命令组通过 `_try_daemon_call("analysis_xrefs_from", {...})` 等走 daemon；daemon 端持有已加载的 `analysis_obj`（`load_apk` 时 `AnalyzeAPK` 得到并缓存，含已建立的 xref）。注意 `apk_attack_surface` 与 `apk_security_report` 虽定义在本模块、以 `apk_` 开头，但由 `apk` 命令组暴露（`apk attack-surface` / `apk security-report`，因需同时具备 `apk_obj` 与 `analysis_obj`，归在 apk 组便于复用已加载的 apk）。非 daemon 模式由 `AndroguardSkills` 实例直接调用。

## 📚 相关

- [代码模块总览](./)
- 命令组文档：`/commands/analysis/`
