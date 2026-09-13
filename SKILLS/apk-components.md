# APK 四大组件

获取 APK 的 Activity、Service、Receiver、Provider 列表及其 Intent Filter。

## Activity

```bash
androguard-skills apk activities --apk-path test.apk
```

输出示例：

```json
{
  "activities": [
    "com.example.app.MainActivity",
    "com.example.app.SettingsActivity"
  ],
  "main_activities": ["com.example.app.MainActivity"],
  "activity_aliases": [],
  "intent_filters": {
    "com.example.app.MainActivity": {
      "action": ["android.intent.action.MAIN"],
      "category": ["android.intent.category.LAUNCHER"]
    }
  }
}
```

> 注：组件列表（activities/services/receivers/providers）按字母序排序，
> intent_filters 字典按键名排序——保证同一 APK 多次运行输出字节级一致。

## Service

```bash
androguard-skills apk services --apk-path test.apk
```

输出示例：

```json
{
  "services": [
    "com.example.app.BackgroundService"
  ],
  "intent_filters": {}
}
```

## BroadcastReceiver

```bash
androguard-skills apk receivers --apk-path test.apk
```

输出示例：

```json
{
  "receivers": [
    "com.example.app.BootReceiver"
  ],
  "intent_filters": {
    "com.example.app.BootReceiver": {
      "action": ["android.intent.action.BOOT_COMPLETED"]
    }
  }
}
```

## ContentProvider

```bash
androguard-skills apk providers --apk-path test.apk
```

输出示例：

```json
{
  "providers": [
    "com.example.app.DataProvider"
  ],
  "intent_filters": {}
}
```

## 指定组件的 Intent Filter

```bash
androguard-skills apk intent-filters com.example.app.MainActivity --apk-path test.apk
```

输出示例：

```json
{
  "component": "com.example.app.MainActivity",
  "type": "activity",
  "intent_filters": {
    "action": ["android.intent.action.MAIN"],
    "category": ["android.intent.category.LAUNCHER"]
  }
}
```

## 组件安全属性详情

### `apk component-details`

**所有组件的安全属性详情**——列出每个 Activity/Service/Receiver/Provider 的完整安全属性（exported/enabled/permission/process + 各类型特有属性），推断 exported 默认值，标记暴露风险。

与 `apk activities`/`services`/`receivers`/`providers`（返回名称列表 + intent-filter）和 `apk security-overview`（仅统计导出数）的区别：本命令聚焦**每个组件的完整属性 + 风险标记**——`exported_effective` 推断 None 的默认值（有 intent-filter 默认 true，即隐式导出），`risk=exposed` 标记导出且无 permission 保护的组件。

```bash
androguard-skills apk component-details --apk-path test.apk
```

**输出：**
```json
{
  "summary": {
    "total_components": 13,
    "exposed_unprotected": 7,
    "exposed_by_type": {"activities": 5, "activity_aliases": 0, "services": 0, "receivers": 1, "providers": 1},
    "total_by_type": {"activities": 10, "activity_aliases": 0, "services": 0, "receivers": 2, "providers": 1}
  },
  "activities": [
    {"name": "com.example.PostLogin", "exported": "true", "exported_effective": true, "exported_inferred": false, "enabled": null, "permission": null, "process": null, "has_intent_filter": true, "risk": "exposed", "launchMode": null, ...},
    {"name": "com.example.LoginActivity", "exported": null, "exported_effective": true, "exported_inferred": true, "permission": null, "risk": "exposed", ...}
  ],
  "providers": [
    {"name": "com.example.TrackUserContentProvider", "exported": "true", "permission": null, "authorities": "...", "readPermission": null, "writePermission": null, "risk": "exposed", ...}
  ],
  "services": [...], "receivers": [...], "activity_aliases": [...]
}
```

| 字段 | 说明 |
|------|------|
| `exported` | manifest 显式值（null 表示未设置） |
| `exported_effective` | 推断后的实际生效值（null 时按 intent-filter 推断：有则 true） |
| `exported_inferred` | 是否为推断值（true 表示 manifest 未显式设 exported，需重点关注——开发者常误以为 false） |
| `permission` | 组件保护权限（null 表示无保护） |
| `risk` | `exposed`（导出且无 permission 保护）/ `safe` |

**各类型特有属性：**
- Activity：`launchMode`/`taskAffinity`/`noHistory`/`configChanges`/`screenOrientation`/`windowSoftInputMode`/`theme`
- Service：`foregroundServiceType`/`isolatedProcess`
- Provider：`authorities`/`grantUriPermissions`/`readPermission`/`writePermission`/`uriPermissionPatterns`（provider 风险综合 permission/readPermission/writePermission 判定）
- Activity-alias：`targetActivity`/`launchMode`/`taskAffinity`/`noHistory`

> 底层 API：`APK.get_activities()`/`get_services()`/`get_receivers()`/`get_providers()`/`get_activity_aliases()` + `get_attribute_value(tag, attr, name=name)` 逐属性读取。exported 推断规则：显式值优先；None 时有 intent-filter（`get_intent_filters()` 非空）默认 true（隐式导出，Android <31 行为），无则 false。InsecureBankv2 典型输出 7 个暴露无保护组件（含 1 个 LoginActivity 隐式导出），是组件劫持/越权访问的典型攻击面。

## 使用场景

- 入口点分析：找到主 Activity 和启动入口
- 攻击面分析：导出组件（exported）可能被外部调用
- 动态分析规划：确定 Frida Hook 的目标组件
- Intent 注入测试：分析 Intent Filter 的攻击面

## 安全关注点

| 关注点 | 说明 |
|--------|------|
| 导出的 Activity | 可能被外部应用启动 |
| 导出的 Service | 可能被外部应用绑定/启动 |
| 导出的 Receiver | 可能接收到恶意广播 |
| 导出的 Provider | 可能泄露数据 |
| 动态注册的 Receiver | 运行时注册，更难检测 |
| alias | Activity 别名可能隐藏真实入口 |
