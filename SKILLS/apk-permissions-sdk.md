# APK 权限分类与 SDK/设备特性

封装第六轮新增的 APK 权限分类、SDK 版本、主 Activity、设备特性、文件类型识别能力。

## 权限命令

### `apk declared-permissions`

获取 APK **声明（自定义）** 的权限——通过 `<permission>` 标签定义的权限（区别于 `<uses-permission>` 请求的权限）。自定义权限的 APK 通常是框架/库，供其他应用调用。

```bash
androguard-skills apk declared-permissions --apk-path test.apk
```

**输出：**
```json
{
  "total": 2,
  "permissions": ["com.example.MY_PERMISSION", "..."],
  "details": {
    "com.example.MY_PERMISSION": {"label": "...", "description": "...", ...}
  }
}
```

### `apk requested-permissions`

获取 APK **请求**的权限，按来源分类（AOSP 系统/第三方/隐含）。

```bash
androguard-skills apk requested-permissions --apk-path test.apk
```

**输出：**
```json
{
  "aosp_permissions": ["android.permission.WRITE_EXTERNAL_STORAGE"],
  "aosp_permissions_count": 1,
  "aosp_permissions_details": ["android.permission.WRITE_EXTERNAL_STORAGE"],
  "third_party_permissions": [],
  "third_party_permissions_count": 0,
  "implied_permissions": [
    {"permission": "android.permission.READ_EXTERNAL_STORAGE", "level": null}
  ],
  "implied_permissions_count": 1
}
```

**字段说明：**
- `aosp_permissions`：请求的 AOSP 系统权限（`android.permission.*`）
- `third_party_permissions`：请求的第三方自定义权限
- `implied_permissions`：**隐含权限**——未显式声明但因其他权限隐含的（如 WRITE_EXTERNAL_STORAGE 隐含 READ）

### `apk details-permissions`

获取 APK 请求权限的**详细信息**（protection_level / label / description）。比 `permissions` 仅列权限名更进一步，附带每个权限的保护级别、用户可见标签和描述，用于权限危险等级评估。

```bash
androguard-skills apk details-permissions --apk-path test.apk
```

**输出：**
```json
{
  "total": 1,
  "permissions": {
    "android.permission.WRITE_EXTERNAL_STORAGE": {
      "protection_level": "dangerous",
      "label": "modify or delete the contents of your SD card",
      "description": "Allows the app to write to the SD card."
    }
  }
}
```

**字段说明：**
- `protection_level`：保护级别（`normal`/`dangerous`/`signature`/`internal`），`dangerous` 需运行时授权
- `label`：权限的用户可见名称
- `description`：权限用途描述

> 底层 API：`APK.get_details_permissions()`，返回 `dict[权限名, [protection_level, label, description]]`。

## SDK 与 Activity 命令

### `apk sdk-versions`

获取 APK 的 SDK 版本信息。

```bash
androguard-skills apk sdk-versions --apk-path test.apk
```

**输出：**
```json
{
  "min_sdk_version": "21",
  "max_sdk_version": null,
  "target_sdk_version": "28",
  "effective_target_sdk_version": 28
}
```

- `min_sdk_version`：最低支持 SDK
- `max_sdk_version`：最高支持 SDK（常为 null）
- `target_sdk_version`：目标 SDK
- `effective_target_sdk_version`：**有效目标 SDK**（target 未设时取 min，用于权限映射分析）

### `apk main-activities`

获取 APK 的主 Activity（启动入口）及别名。

```bash
androguard-skills apk main-activities --apk-path test.apk
```

**输出：**
```json
{
  "main_activity": "org.billthefarmer.editor.Editor",
  "main_activities": ["org.billthefarmer.editor.Editor"],
  "activity_aliases": []
}
```

`main_activities` 是所有标记了 `LAUNCHER` 的 Activity（可能多个），`activity_aliases` 是 `<activity-alias>` 定义的别名。

## 设备特性与文件类型

### `apk device-features`

获取 APK 的设备特性布尔标记。

```bash
androguard-skills apk device-features --apk-path test.apk
```

**输出：**
```json
{
  "is_androidtv": false,
  "is_wearable": false,
  "is_leanback": false,
  "is_multidex": false
}
```

- `is_androidtv` / `is_leanback`：是否为 Android TV / Leanback UI
- `is_wearable`：是否为 Wear OS
- `is_multidex`：是否使用 Multidex（多 DEX）

### `apk files-types`

获取 APK 中所有条目的文件类型识别（基于 `file` 命令）。

```bash
androguard-skills apk files-types --apk-path test.apk
```

**输出：**
```json
{
  "total": 47,
  "files": {
    "classes.dex": "Unknown",
    "META-INF/...": "Unknown",
    ...
  }
}
```

> 注意：`get_files_types` 依赖系统 `file` 命令，识别为 `Unknown` 时表示类型库未覆盖或 `file` 不可用。

## 相关命令

- [`apk permissions`](apk-permissions.md) — 权限列表（基础）
- [`analysis permissions`](analysis-callgraph-permissions.md) — API 方法→权限映射分析
- [`analysis permission-usage`](analysis-permissions.md) — 单权限使用追踪
