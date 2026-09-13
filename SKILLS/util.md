# 工具能力（文件检测 / AOSP 权限）

封装第五轮新增的 `androguard.util` 和 `androguard.core.androconf` 工具能力。这些命令**不依赖已加载的 APK**，可独立调用。

## 命令

### `util detect <filename>`

检测文件的 Android 类型（APK/DEX/ODEX/ELF 等）。

```bash
androguard-skills util detect test.apk
```

**输出：**
```json
{
  "filename": "test.apk",
  "type": "APK"
}
```

`type` 取值：`APK`/`DEX`/`ODEX`/`ELF`/`UNKNOWN` 等。

> 底层 API：`androconf.is_android(filename)`。

### `util permissions <apilevel>`

加载指定 API level 的 AOSP 权限定义。

```bash
androguard-skills util permissions 35
```

**输出：**
```json
{
  "apilevel": "35",
  "total": 1016,
  "permissions": {
    "android.permission.READ_CONTACTS": {
      "description": "...",
      "label": "...",
      ...
    },
    ...
  }
}
```

返回权限名 → 权限元数据（描述、标签等）的映射。用于查询某 API level 下某权限的官方定义。

> 底层 API：`androconf.load_permissions(apilevel)`。数据位于 `androguard/core/api_specific_resources/aosp_permissions/`。

### `util permission-mappings <apilevel>`

加载指定 API level 的「方法签名 → 所需权限」映射。

```bash
androguard-skills util permission-mappings 23
```

**输出：**
```json
{
  "apilevel": "23",
  "total": 1429,
  "mappings": {
    "Landroid/app/ActivityManager;->getRunningAppProcesses ()Ljava/util/List;": [
      "android.permission.GET_TASKS"
    ],
    ...
  }
}
```

key 是方法签名（`类;->方法 描述符`），value 是该方法所需权限列表。用于静态权限检查时判断调用某 API 是否需要某权限。

> 底层 API：`androconf.load_permission_mappings(apilevel)`。数据位于 `api_specific_resources/api_permission_mappings/`。

### `util api-levels`

列出本地可用的权限数据 API level。

```bash
androguard-skills util api-levels
```

**输出：**
```json
{
  "permissions": [4, 5, 6, ..., 36],
  "permission_mappings": [16, 17, ..., 25]
}
```

- `permissions`：AOSP 权限定义可用的 API level（4-36）
- `permission_mappings`：方法-权限映射可用的 API level（16-25）

调用 `util permissions`/`util permission-mappings` 前可用此命令确认某 level 是否有数据。

### `util format <value> [--to]`

Dalvik/Java/Python 类名与描述符格式双向转换。逆向分析中常需在三种格式间转换：Dalvik（`Lcom/foo/Bar;`，DEX/分析命令输出）、Java（`com.foo.Bar`，可读）、Python（`com_foo_Bar`，标识符安全）。

> 不依赖已加载 APK，可独立调用。

```bash
# Dalvik → Java（默认）
androguard-skills util format "Lcom/foo/Bar;"
# → com.foo.Bar

# Java → Dalvik
androguard-skills util format "com.foo.Bar" --to dalvik
# → Lcom/foo/Bar;

# Dalvik → Python 标识符
androguard-skills util format "Lcom/foo/Bar;" --to python
# → com_foo_Bar
```

| 参数 | 说明 |
|------|------|
| `value`（位置参数） | 待转换的类名或描述符 |
| `--to` | 目标格式（`java`/`dalvik`/`python`，默认 `java`） |

**输出：**
```json
{
  "input": "Lcom/foo/Bar;",
  "to": "java",
  "output": "com.foo.Bar"
}
```

自动识别输入格式：含 `L`/`;` 为 Dalvik，含 `.` 为 Java，含 `/` 为路径。描述符（如 `(Landroid/os/Bundle;)V`）转 python 时 `/`→`_`，java/dalvik 同形（附 note）。

> 不使用 AndroGuard 内置的 `FormatClassToJava`/`FormatClassToPython`（其 Python 版有截断 bug、`FormatNameToPython` 不转换），本命令自实现清晰的格式转换。

## 相关命令

- [`analysis permission-usage`](analysis-permissions.md) — 权限使用追踪（基于已加载 APK）
- [`analysis permissions-map`](analysis-field-xrefs.md) — APK 实际使用的权限映射
