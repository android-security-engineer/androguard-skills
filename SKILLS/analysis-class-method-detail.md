# 类与方法深度分析

封装第五轮新增的 `ClassAnalysis`/`MethodAnalysis` 遗漏能力：继承信息、new-instance/const-class 交叉引用、类/方法综合详情、基本块（CFG 节点）、被覆盖字符串。

## 类分析命令

### `analysis class-hierarchy-info <class>`

获取类的继承信息（extends / implements）。

```bash
androguard-skills analysis class-hierarchy-info Lcom/example/Foo;
```

**输出：**
```json
{
  "class": "Lcom/example/Foo;",
  "is_external": false,
  "is_android_api": false,
  "extends": "Landroid/app/Activity;",
  "implements": []
}
```

### `analysis class-xref-new-instance <class>`

获取类的 `new-instance` 交叉引用——即**何处实例化此类**（`new Foo()`）。

```bash
androguard-skills analysis class-xref-new-instance Lcom/example/Foo;
```

返回 `(MethodAnalysis, offset)` 列表，标识实例化此类的每处方法及偏移。

### `analysis class-xref-const-class <class>`

获取类的 `const-class` 交叉引用——即**何处引用此类字面量**（`Foo.class`）。

```bash
androguard-skills analysis class-xref-const-class Lcom/example/Foo;
```

返回 `(MethodAnalysis, offset)` 列表。

### `analysis class-detail <class>`

获取类的综合信息（方法数、继承、接口、xref 统计、vm_class 类型）。

```bash
androguard-skills analysis class-detail Lcom/example/Foo;
```

**输出：**
```json
{
  "class": "Lcom/example/Foo;",
  "is_external": false,
  "is_android_api": false,
  "nb_methods": 136,
  "extends": "Landroid/app/Activity;",
  "implements": [],
  "xref_from_count": 30,
  "xref_to_count": 115,
  "xref_new_instance_count": 0,
  "xref_const_class_count": 2,
  "vm_class_type": "ClassDefItem"
}
```

`vm_class_type` 区分内部类（`ClassDefItem`）与外部类（`ExternalClass`）。

## 方法分析命令

### `analysis method-detail <class> <method> <descriptor>`

获取方法的综合信息（全名、访问标志、长度、xref 统计、基本块数）。

```bash
androguard-skills analysis method-detail Lcom/example/Foo; onCreate "(Landroid/os/Bundle;)V"
```

**输出：**
```json
{
  "class": "Lcom/example/Foo;",
  "method": "onCreate",
  "descriptor": "(Landroid/os/Bundle;)V",
  "full_name": "Lcom/example/Foo; onCreate (Landroid/os/Bundle;)V",
  "access_flags": "protected",
  "is_external": false,
  "is_android_api": false,
  "length": 570,
  "xref_from_count": 0,
  "xref_to_count": 75,
  "xref_new_instance_count": 4,
  "xref_const_class_count": 0,
  "xref_read_count": 13,
  "xref_write_count": 17,
  "basic_blocks_count": 61
}
```

- `full_name`：`类 方法 (描述符)返回类型` 完整签名
- `length`：方法字节码长度
- `xref_read_count`/`xref_write_count`：字段读写引用数
- `basic_blocks_count`：基本块（CFG 节点）数量

### `analysis method-api-info <class> <method> <descriptor>`

查询方法的 API 与权限标注属性（`is_android_api`/`is_external`/`domain_flag`/`restriction_flag`/`apilist`）。

与 `method-detail`（含 xref 统计但不含权限标注）的区别：本命令聚焦**权限审计维度**——`is_android_api` 判断是否为 AOSP 平台 API，`domain_flag`/`restriction_flag`/`apilist` 是 AndroGuard 权限映射流程（`Analysis.create_xref` + `PermissionAnalysis`）填充的标注。

```bash
androguard-skills analysis method-api-info Ljava/io/File; "<init>" "(Ljava/lang/String;)V"
```

**输出：**
```json
{
  "class": "Ljava/io/File;",
  "method": "<init>",
  "descriptor": "(Ljava/lang/String;)V",
  "full_name": "Ljava/io/File; <init> (Ljava/lang/String;)V",
  "access_flags": "",
  "is_external": true,
  "is_android_api": true,
  "domain_flag": null,
  "restriction_flag": null,
  "apilist": null,
  "length": 0
}
```

- `is_android_api`：是否为 Android 平台 API（`Ljava/*`/`Landroid/*` 等系统类的方法）
- `is_external`：是否为外部方法（无实现体，`length=0`）
- `domain_flag`/`restriction_flag`/`apilist`：权限映射标注，常规加载下为 `null`（需先运行权限映射流程才有值，见 `analysis permissions` 和 `util permission-mappings`）
- `length`：字节码长度，外部方法为 `0`

### `analysis method-basic-blocks <class> <method> <descriptor>`

获取方法的基本块（CFG 节点）列表，含控制流转移关系。

```bash
androguard-skills analysis method-basic-blocks Lcom/example/Foo; onCreate "(Landroid/os/Bundle;)V"
```

**输出：**
```json
{
  "method_name": "onCreate",
  "total": 61,
  "basic_blocks": [
    {
      "name": "onCreate-BB@0x0",
      "start": 0,
      "end": 238,
      "nb_instructions": 60,
      "last_instruction": {"name": "if-eqz", "output": "v1, +020h"},
      "childs": [
        {"start": 234, "end": 238, "name": "onCreate-BB@0xee"},
        {"start": 234, "end": 298, "name": "onCreate-BB@0x12a"}
      ],
      "fathers": [...]
    },
    ...
  ]
}
```

- `name`：基本块标识（方法名 + 起始偏移）
- `start`/`end`：基本块字节码范围
- `nb_instructions`：指令数
- `last_instruction`：块的最后一条指令（终止指令，决定 CFG 后继方向，如 `if-eqz`/`return-void`/`goto`）
- `notes`：分析器注释（检测到的特殊模式标记，无则为不输出）
- `childs`：后继基本块（控制流去向）
- `fathers`：前驱基本块（控制流来源）

`childs`/`fathers` 是 `list of (start, end, DEXBasicBlock)` 三元组，已序列化为 `{start, end, name}`。

### `analysis method-exceptions <class> <method> <descriptor>`

获取方法的 **try/catch 异常处理表**。遍历方法所有基本块的 `get_exception_analysis()`，返回每个含异常处理的基本块及其 try 区间和 catch 块列表。用于逆向定位异常处理结构、追踪 catch 流向。

```bash
androguard-skills analysis method-exceptions Lcom/example/Foo; readFile "()V" --apk-path test.apk
```

**输出：**
```json
{
  "class": "Landroid/support/v4/content/FileProvider;",
  "method": "getPathStrategy",
  "descriptor": "(Landroid/content/Context; Ljava/lang/String;)Landroid/support/v4/content/FileProvider$PathStrategy;",
  "full_name": "Landroid/support/v4/content/FileProvider; getPathStrategy (...)...",
  "total": 6,
  "exceptions": [
    {
      "basic_block": "getPathStrategy-BB@0x1a",
      "start": 26,
      "end": 33,
      "handlers": [
        {"exception_class": "Ljava/io/IOException;", "idx": 79, "catch_block": "getPathStrategy-BB@0x40"},
        {"exception_class": "Lorg/xmlpull/v1/XmlPullParserException;", "idx": 88, "catch_block": "getPathStrategy-BB@0x2e"},
        {"exception_class": "Ljava/lang/Throwable;", "idx": 86, "catch_block": "getPathStrategy-BB@0x56"}
      ]
    }
  ]
}
```

**字段说明：**
- `basic_block`：含异常处理的基本块名（`方法名-BB@0x偏移`）
- `start`/`end`：try 区间的指令 offset 范围（相对方法起始）
- `handlers`：catch 块列表，`exception_class` 是捕获的异常类，`catch_block` 是处理该异常的基本块名，`idx` 是常量池 type 索引

**用途：**
- 定位 try/catch 结构，分析异常处理流向（哪个 catch 块处理哪个异常）
- 与 `method-basic-blocks`（CFG 节点）结合，构建完整的控制流图（含异常边）
- 安全分析：异常处理块常被用于反调试/混淆（如 catch 中检测调试器），定位这些块辅助识别

> 底层 API：`MethodAnalysis.get_basic_blocks()` 遍历 + `DEXBasicBlock.get_exception_analysis()`，`ExceptionAnalysis.get()` 返回 `{start, end, list: [{name, idx, basic_block}]}`。不含异常处理的方法 `total=0`。

### `analysis method-xrefs-detail <class> <method> <descriptor>`

获取方法级 xref 的**完整引用列表**（6 类），用于逆向追踪"某方法读写了哪些字段、new 了哪些类、调用了哪些方法、被谁调用"。

与 `method-detail`（仅返回各类 xref 的统计数）和 `method-xrefs`（仅 from/to 两类、且按 class+method 无 descriptor 查）的区别：本命令按 class+method+descriptor 精确查，返回 6 类 xref 的全部引用详情（含 offset）。

```bash
androguard-skills analysis method-xrefs-detail Lcom/example/Foo; onCreate "(Landroid/os/Bundle;)V" --apk-path test.apk
```

**输出：**
```json
{
  "class": "Lcom/example/Foo;",
  "method": "onCreate",
  "descriptor": "(Landroid/os/Bundle;)V",
  "full_name": "Lcom/example/Foo; onCreate (Landroid/os/Bundle;)V",
  "xref_from": {"count": 0, "refs": []},
  "xref_to": {
    "count": 75,
    "refs": [
      {"class": "Ljava/util/Iterator;", "method": "next", "descriptor": "()Ljava/lang/Object;", "offset": 258},
      ...
    ]
  },
  "xref_read": {
    "count": 13,
    "refs": [
      {"class": "Lcom/example/Foo;", "field": "suggest", "offset": 666},
      ...
    ]
  },
  "xref_write": {
    "count": 17,
    "refs": [
      {"class": "Lcom/example/Foo;", "field": "textView", "offset": 502},
      ...
    ]
  },
  "xref_new_instance": {
    "count": 4,
    "refs": [
      {"class": "Ljava/util/ArrayList;", "offset": 298},
      ...
    ]
  },
  "xref_const_class": {"count": 0, "refs": []}
}
```

**6 类 xref 说明：**

| 类别 | 含义 | 数据结构 |
|------|------|---------|
| `xref_from` | 谁调用了此方法 | `list of (ClassAnalysis, MethodAnalysis, offset)` |
| `xref_to` | 此方法调用了谁 | `list of (ClassAnalysis, MethodAnalysis, offset)` |
| `xref_read` | 此方法读了哪些字段 | `list of (ClassAnalysis, FieldAnalysis, offset)` |
| `xref_write` | 此方法写了哪些字段 | `list of (ClassAnalysis, FieldAnalysis, offset)` |
| `xref_new_instance` | 此方法 new 了哪些类 | `list of (ClassAnalysis, offset)` |
| `xref_const_class` | 此方法引用了哪些类字面量 | `list of (ClassAnalysis, offset)` |

每类返回 `{count, refs}`，`refs` 中每项含 `class`、引用对象名（`method`/`field`）、`offset`（指令偏移）。`xref_to` 中同一方法多次调用会出现多条（不同 offset），这是真实的多次调用。

**使用场景：**
- 入口点分析：`xref_from` 为空表示此方法是入口点（如 `onCreate` 被 Framework 调用）
- 数据流追踪：`xref_read`/`xref_write` 定位某方法操作的字段，配合 `field-analysis` 查字段全量引用
- 对象创建追踪：`xref_new_instance` 查方法内实例化了哪些类（如反序列化、反射场景）
- 调用链分析：`xref_to` 是方法调用的全量目标，配合 `call-graph` 做图分析

### `analysis method-summary <class> <method> [--descriptor]`

**聚合方法全貌**——单条命令返回方法的完整分析视图：元信息（access/length/is_external/is_android_api）+ 6 类 xref 统计与摘要引用 + 基本块数 + 异常处理块数 + 反编译 Java 源码。省去串调 `method-detail` / `method-xrefs-detail` / `method-basic-blocks` / `method-exceptions` / `decompile method` 五个命令。

```bash
# 基本用法（不传 descriptor，取类内首个同名方法）
androguard-skills analysis method-summary Lcom/example/Foo; onCreate --apk-path test.apk

# 指定 descriptor 精确匹配重载
androguard-skills analysis method-summary Lcom/example/Foo; readFile --descriptor "()V" --apk-path test.apk

# 不含反编译源码（更快）
androguard-skills analysis method-summary Lcom/example/Foo; onCreate --no-source --apk-path test.apk

# 每类 xref 返回前 5 条引用（默认 10），0 表示全量
androguard-skills analysis method-summary Lcom/example/Foo; onCreate --xref-limit 5 --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `class_name`（位置） | 类名（Dalvik 格式） |
| `method_name`（位置） | 方法名 |
| `--descriptor` | 方法描述符（可选，不传则取类内首个同名方法） |
| `--no-source` | 不包含反编译源码 |
| `--xref-limit` | 每类 xref 引用返回上限（默认 10，`0` 返回全量） |

**输出：**
```json
{
  "class": "Lorg/billthefarmer/editor/Editor;",
  "method": "onCreate",
  "descriptor": "(Landroid/os/Bundle;)V",
  "full_name": "Lorg/billthefarmer/editor/Editor; onCreate (Landroid/os/Bundle;)V",
  "access_flags": "protected",
  "is_external": false,
  "is_android_api": false,
  "length": 570,
  "basic_blocks_count": 61,
  "exception_blocks_count": 0,
  "xrefs": {
    "xref_from": {"count": 0, "returned": 0, "refs": []},
    "xref_to": {"count": 75, "returned": 3, "refs": [{"class": "...", "method": "...", "descriptor": "...", "offset": 258}, ...]},
    "xref_read": {"count": 13, "returned": 3, "refs": [{"class": "...", "field": "...", "offset": 666}, ...]},
    "xref_write": {"count": 17, "returned": 3, "refs": [...]},
    "xref_new_instance": {"count": 4, "returned": 3, "refs": [{"class": "...", "offset": 298}, ...]},
    "xref_const_class": {"count": 0, "returned": 0, "refs": []}
  },
  "source": "protected void onCreate(android.os.Bundle p8) {\n    super.onCreate(p8);\n    ..."
}
```

**字段说明：**

| 字段 | 说明 |
|------|------|
| `access_flags`/`length`/`is_external`/`is_android_api` | 方法元信息 |
| `basic_blocks_count` | 基本块（CFG 节点）数 |
| `exception_blocks_count` | 含 try/catch 的基本块数（与 `method-exceptions` 的 `total` 一致） |
| `xrefs.<类>.count` | 该类 xref 的**全量**引用数 |
| `xrefs.<类>.returned` | 实际返回的引用数（受 `--xref-limit` 限制） |
| `xrefs.<类>.refs` | 摘要引用列表（每项含 class + 引用对象 + offset） |
| `source` | 反编译 Java 源码（`--no-source` 时不返回） |

**与原子命令的区别：** 本命令是聚合视图，xref 引用默认限制前 10 条便于概览；需某类的**全量引用**时用 `method-xrefs-detail`，需完整基本块/异常详情时用 `method-basic-blocks`/`method-exceptions`。

**使用场景：**
- **快速方法审计**：一眼看清方法的访问标志、代码长度、调用规模、字段读写、是否含异常处理、反编译源码
- **入口点识别**：`xref_from.count=0` + `is_android_api=false` 通常是应用入口（生命周期方法）
- **复杂度评估**：`length` + `basic_blocks_count` + `exception_blocks_count` 反映方法复杂度，高值方法优先深入分析
- **异常处理定位**：`exception_blocks_count>0` 时配合 `method-exceptions` 看 catch 流向（反调试/混淆常藏于此）

### `analysis method-reachable <class> <method> [--descriptor]`

**方法可达性分析**——从指定方法出发，递归展开 `xref_to`（被调用方）到 `--max-depth` 层，返回可达方法子图（含层级）。

与 `analysis call-graph`（全量 networkx 调用图，无方向性溯源）和 `method-summary`（单方法 xref 摘要，仅 1 跳）的区别：本命令从单一方法出发做**有向可达性**——回答"这个方法能触达哪些方法"，用于调用链追溯、污点传播路径、危险入口的 sink 可达性。

```bash
# 从 onCreate 出发，递归 3 层（默认只内部方法）
androguard-skills analysis method-reachable "Lcom/example/Foo;" onCreate --descriptor "(Landroid/os/Bundle;)V" --apk-path test.apk

# 包含外部 API 方法（深度应小，避免爆炸）
androguard-skills analysis method-reachable "Lcom/example/Foo;" execCommand --max-depth 2 --include-external --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--descriptor` | 方法描述符（可选，类内重载时需指定；省略取首个同名方法） |
| `--max-depth` | 递归深度上限（默认 3） |
| `--include-external` | 也递归外部/API 方法（默认 False；启用时深度应小） |
| `--max-nodes` | 节点数上限防爆（默认 5000） |

**输出：**
```json
{
  "start": {"class": "Lcom/example/Foo;", "method": "onCreate", "descriptor": "(Landroid/os/Bundle;)V", "full_name": "..."},
  "max_depth": 2,
  "include_external": false,
  "truncated": false,
  "node_count": 28,
  "edge_count": 166,
  "internal_count": 28,
  "external_count": 0,
  "max_depth_reached": 2,
  "nodes": [
    {"class": "Lcom/example/Foo;", "method": "onCreate", "descriptor": "...", "full_name": "...", "is_external": false, "depth": 0},
    {"class": "Lcom/example/Foo;", "method": "readFile", "descriptor": "...", "full_name": "...", "is_external": false, "depth": 1},
    ...
  ],
  "edges": [{"from": "Lcom/example/Foo;->onCreate...", "to": "Lcom/example/Foo;->readFile...", "depth": 0}]
}
```

| 字段 | 说明 |
|------|------|
| `nodes[].depth` | 距起点的跳数（0 = 起点本身，1 = 直接被调，2 = 2 跳...） |
| `nodes[].is_external` | 是否外部/API 方法 |
| `edges` | 调用边（from → to），含循环边 |
| `truncated` | 是否因 `--max-nodes` 截断 |
| `internal_count`/`external_count` | 内部/外部方法节点数 |

> 底层 API：`Analysis.create_xref()` + `MethodAnalysis.get_xref_to()`（返回 `(ClassAnalysis, MethodAnalysis, offset)`）BFS 递归。默认只递归内部方法（`is_external()==False`）避免 API 调用链爆炸；`--include-external` 时深度应 ≤2。`truncated=true` 表示触达 `--max-nodes` 上限，需减小深度或加过滤。配 `analysis method-callers` 看反向（谁调用本方法）。

### `analysis method-callers <class> <method> [--descriptor]`

**方法反向可达性（调用方溯源）**——与 `method-reachable` **方向相反**：从指定方法递归展开 `xref_from`（调用方）到 `--max-depth` 层，回答"**哪些方法/入口最终会调用到此方法**"。

用途：危险 sink 溯源（某敏感 API 被哪些入口触达）、污点源定位（从 sink 反推到用户可控入口）、影响面评估（hook/修改某方法会影响哪些上层调用方）、攻击路径反向构建。

```bash
# 溯源：哪些方法能到达 exec（危险 sink 反查）
androguard-skills analysis method-callers "Ljava/lang/Runtime;" exec --apk-path test.apk

# 从加密方法反查调用方，深度 4
androguard-skills analysis method-callers "Lcom/example/Crypto;" decrypt --max-depth 4 --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--descriptor` | 方法描述符（可选，类内重载时需指定） |
| `--max-depth` | 反向递归深度上限（默认 3） |
| `--include-external` | 也递归外部方法（默认 False；外部方法无实现体通常无上溯意义） |
| `--max-nodes` | 节点数上限防爆（默认 5000） |

**输出：**
```json
{
  "target": {"class": "Lcom/example/Crypto;", "method": "decrypt", "descriptor": null, "full_name": "..."},
  "max_depth": 3,
  "node_count": 70,
  "edge_count": 141,
  "internal_count": 70,
  "max_depth_reached": 3,
  "entry_point_count": 11,
  "entry_points": [{"class": "...", "method": "tryStart", "depth": 1, "...": "..."}],
  "frontier_count": 42,
  "frontier": [{"class": "...", "method": "...", "depth": 3, "...": "..."}],
  "nodes": [...],
  "edges": [{"from": "caller_key", "to": "callee_key", "depth": 0}]
}
```

| 字段 | 说明 |
|------|------|
| `edges[].from → to` | 边方向为**真实调用方向**（caller → callee），与遍历方向相反 |
| `entry_points` | **调用链源头**——被完整展开（depth<max_depth）却无内部调用方的节点（典型：框架回调的生命周期方法、`Thread.run`、静态初始化等外部触发入口） |
| `frontier` | 因触达 `--max-depth` 未继续上溯的边界节点（可能还有更上层调用方，加深度可展开） |
| `nodes[].depth` | 距目标的反向跳数（0 = 目标本身，1 = 直接调用者，N = N 跳外调用者） |

> 底层 API：镜像 `method-reachable` 但用 `MethodAnalysis.get_xref_from()` 替代 `get_xref_to()`（`xref_from` 同样返回 `(ClassAnalysis, MethodAnalysis, offset)`，方向为"谁调用了此方法"）。`entry_points` 判定在 BFS 展开期完成（展开且内部调用方数==0），环图安全。危险 sink（exec/loadLibrary/Cipher/反射）的 `entry_points` 若落在导出组件生命周期方法上，即构成可外部触发的攻击路径——配 `apk attack-surface` 做正向交叉验证。

### `analysis method-block-instructions <class> <method> [--descriptor]`

**按基本块反汇编方法指令**——每个 BasicBlock 的完整指令流（CFG 节点级视图）。

与 `analysis method-basic-blocks`（块元信息：名/范围/nb/last/childs，**不含块内指令**）和 `analysis method-instructions`（整方法平铺指令流，无块边界）的区别：本命令按 CFG 基本块组织指令，每块含其全部指令 + 后继/前继块名。用于控制流敏感分析（按分支块定位指令）、反调试/混淆检测（异常块、死块、特殊跳转）、路径分析（沿 `next` 追踪执行路径指令）。

```bash
androguard-skills analysis method-block-instructions "Lcom/example/Foo;" bar --descriptor "()V" --apk-path test.apk

# 每块限 10 条指令（避免大方法全量输出）
androguard-skills analysis method-block-instructions "Lcom/example/Foo;" bigMethod --ins-limit 10 --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--descriptor` | 方法描述符（可选） |
| `--ins-limit` | 每块返回指令上限（0 = 全部，默认全部；大方法建议设限） |

**输出：**
```json
{
  "class": "Lcom/example/Foo;", "method": "bar", "descriptor": "()V",
  "full_name": "...",
  "block_count": 61,
  "total_instructions": 258,
  "blocks": [
    {
      "name": "bar-BB@0x0", "start": 0, "end": 238, "nb_instructions": 60,
      "instructions": [
        {"name": "invoke-super", "output": "v7, v8, Landroid/app/Activity;->onCreate...", "op_value": 16, "hex": "6ee8...", "length": 6},
        ...
      ],
      "truncated": false,
      "next": [{"start": 234, "end": 238, "name": "bar-BB@0xee"}, {"start": 234, "end": 298, "name": "bar-BB@0x12a"}],
      "prev": [],
      "exception": null
    },
    ...
  ]
}
```

| 字段 | 说明 |
|------|------|
| `blocks[].instructions` | 块内完整指令流（含 name/output/op_value/hex/length） |
| `blocks[].next`/`prev` | 后继/前驱块（含 start/end/name，对应 CFG 边） |
| `blocks[].truncated` | 是否因 `--ins-limit` 截断本块指令 |
| `blocks[].exception` | 异常分析（catch 块的异常类型） |

> 底层 API：`MethodAnalysis.get_basic_blocks().get()` 返回 `list[DEXBasicBlock]` → 每块 `get_instructions()` 取指令 + `get_next()`/`get_prev()`（返回 `list[(start, end, DEXBasicBlock)]`）取 CFG 边。块 `start`/`end` 是字节范围（与 `method-instructions-idx` 的 offset 对应）。配 `method-basic-blocks` 看块元信息（last_instruction/notes/childs），本命令补块内指令。

### `analysis method-switch-payloads <class> <method> [--descriptor]`

**解析 switch 分支表与 fill-array-data 数组 payload**——还原 `packed-switch`/`sparse-switch` 的 **case 值 → 分支目标偏移** 映射，以及 `fill-array-data` 的数组初始化字节。

与 `analysis method-block-instructions`/`method-instructions`（switch/array payload 仅以原始 `hex`/`output` 呈现，case→目标不可读）的区别：本命令识别 payload 伪指令（`packed-switch-payload`/`sparse-switch-payload`/`fill-array-data-payload`），调用 `get_keys()`/`get_targets()`/`get_data()` 结构化解码。switch 语句在字节码里被拆成「分支指令 + 独立 payload 表」两部分，常规反汇编只见分支指令不见表，本命令补齐这张表。

```bash
androguard-skills analysis method-switch-payloads "Lcom/example/Foo;" onCreate --descriptor "(Landroid/os/Bundle;)V" --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--descriptor` | 方法描述符（可选，重载时指定） |

**输出：**
```json
{
  "class": "Lcom/example/Foo;", "method": "onCreate", "descriptor": "(Landroid/os/Bundle;)V",
  "full_name": "...",
  "switch_count": 3,
  "array_data_count": 0,
  "branch_site_count": 3,
  "switches": [
    {
      "block": "onCreate-BB@0x40c",
      "type": "packed-switch",
      "name": "packed-switch-payload",
      "case_count": 6,
      "cases": [
        {"key": 1, "target": 46}, {"key": 2, "target": 42},
        {"key": 3, "target": 25}, {"key": 6, "target": 4}
      ],
      "length": 32
    },
    {
      "block": "onCreate-BB@0x...",
      "type": "sparse-switch",
      "case_count": 5,
      "cases": [{"key": -1173683121, "target": 49}, ...]
    }
  ],
  "array_data": [
    {"block": "<clinit>-BB@0x14", "name": "fill-array-data-payload", "data_length": 52, "data_hex": "0000027f0100027f...", "length": 60}
  ],
  "branch_sites": [
    {"block": "onCreate-BB@0x12a", "instruction": "packed-switch", "output": "v1, +0000155c", "op_value": 43}
  ]
}
```

| 字段 | 说明 |
|------|------|
| `switches[].type` | `packed-switch`（连续 case 值）/ `sparse-switch`（离散 case 值） |
| `switches[].cases` | case 表，`key` 是 case 值（sparse 可为任意 int，常是状态码/opcode/hashCode），`target` 是相对分支偏移（单位 16-bit code unit，从对应 switch 指令地址起算） |
| `array_data[].data_hex` | fill-array-data 数组原始字节（小端序），`data_length` 为字节数 |
| `branch_sites` | 引用 payload 的分支指令位置（`packed-switch`/`sparse-switch`/`fill-array-data`），`output` 含操作数寄存器 + payload 相对偏移 |

**使用场景：**
- **还原 switch 语义**：case 键值直接决定分支逻辑，逆向状态机/命令分发/消息处理时必须（如 `onKeyDown` 按 keyCode 分支、`handleMessage` 按 what 分支）
- **控制流完整性**：`method-block-instructions` 看到 switch 指令后，用本命令补出每个 case 的跳转目标，构建完整 CFG
- **常量数组提取**：`fill-array-data` 常初始化硬编码密钥/查找表/字节数组，`data_hex` 直接给出内容
- **sparse-switch 键值分析**：sparse 键常是 `String.hashCode()` 值（编译器把 `switch(String)` 降级为 hashCode sparse-switch），据此反推原始字符串常量

> 底层 API：`MethodAnalysis.get_basic_blocks()` 遍历 → `DEXBasicBlock.get_instructions()` 中的 `PackedSwitch`/`SparseSwitch`（`get_keys()`/`get_targets()`）与 `FillArrayData`（`get_data()`）payload 类。注意 payload 伪指令（op `0x100`/`0x200`/`0x300`）与分支指令（op `0x2b`/`0x2c`/`0x26`）是**两条独立指令**，本命令同时收集。无 switch/数组的方法三个 count 均为 0。

## 字符串命令

### `analysis strings-overwritten`

获取被覆盖的字符串（混淆/加固场景下，原始字符串值被替换）。

```bash
androguard-skills analysis strings-overwritten
```

**输出：**
```json
{
  "total_strings": 2575,
  "overwritten_count": 0,
  "strings": []
}
```

未混淆的 APK `overwritten_count` 为 0。混淆后的 APK 会列出被覆盖字符串的 `value`（当前值）和 `orig_value`（原始值）。

> 底层 API：`StringAnalysis.is_overwritten` / `get_orig_value()`。

### `analysis string-info <value>`

按精确字符串值查询单个字符串的**完整分析详情**（原始值/当前值/是否覆盖 + 全部引用位置）。

与 `strings-overwritten`（仅列出被覆盖字符串清单）和 `find-strings`（正则搜索 + 简要 used_in）的区别：本命令按精确 `value` 取单个 `StringAnalysis`，返回 `is_overwritten`/`orig_value`/`current_value` 三者对照（混淆检测：运行时被覆写的字符串 orig_value 与 current_value 不同），以及带方法描述符的完整 `xref_from` 引用列表，用于追踪单个敏感字符串（密钥、URL、密文、命令等）的全部使用位置。

```bash
androguard-skills analysis string-info "BLOCKS" --apk-path test.apk

# 限制 xref 返回数量
androguard-skills analysis string-info "https://api.example.com" --xref-limit 10 --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `value`（位置） | 字符串精确值（DEX 字符串池中的字面值） |
| `--xref-limit` | xref_from 引用返回上限（默认全部） |

**输出：**
```json
{
  "value": "BLOCKS",
  "is_overwritten": false,
  "orig_value": "BLOCKS",
  "current_value": "BLOCKS",
  "xref_from": {
    "count": 1,
    "returned": 1,
    "refs": [
      {"class": "Lorg/commonmark/parser/IncludeSourceSpans;", "method": "<clinit>", "descriptor": "()V"}
    ]
  }
}
```

| 字段 | 说明 |
|------|------|
| `is_overwritten` | 字符串是否被运行时覆写（混淆特征） |
| `orig_value` | 原始值（未被覆写时与 value 相同） |
| `current_value` | 当前值（`get_value()`，通常与 value 相同） |
| `xref_from.count` | 该字符串被引用的总次数 |
| `xref_from.refs` | 引用列表（class/method/descriptor），受 `--xref-limit` 截断 |

> 字符串不存在时返回 `{"value": "...", "error": "String not found in DEX string pool"}`。混淆检测：若 `is_overwritten=true` 且 `orig_value != current_value`，说明字符串在运行时被解密/替换——可结合 `dex method-instructions` 反编译引用方法定位解密逻辑。底层 API：`Analysis.get_strings_analysis()[value]` → `StringAnalysis`，其 `is_overwritten()`/`get_orig_value()`/`get_value()`/`get_xref_from(with_offset=True)`。

## 相关命令

- [`analysis-lookup`](analysis-lookup.md) — 类存在性/方法精确分析/全量字符串分析
- [`analysis-xrefs`](analysis-xrefs.md) — 类与方法交叉引用
- [`dex-disassemble`](dex-disassemble.md) — DEX 字节码反汇编
- [`visualize`](visualize.md) — 方法 CFG 可视化导出
