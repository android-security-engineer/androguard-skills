# APK 基本信息

获取 APK 的包名、版本、SDK 版本等基础信息。

## 命令

```bash
androguard-skills apk info --apk-path test.apk
```

## 输出示例

```json
{
  "package": "com.example.app",
  "app_name": "My App",
  "version_code": "123",
  "version_name": "1.2.3",
  "min_sdk": "21",
  "target_sdk": "33",
  "max_sdk": "",
  "effective_target_sdk": 33,
  "is_multidex": false,
  "is_valid": true,
  "is_wearable": false,
  "is_leanback": false,
  "is_androidtv": false,
  "dex_names": ["classes.dex"],
  "main_activity": "com.example.app.MainActivity"
}
```

## 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `package` | string | 应用包名 |
| `app_name` | string | 应用名称 |
| `version_code` | string | 版本号 |
| `version_name` | string | 版本名 |
| `min_sdk` | string | 最低 SDK 版本 |
| `target_sdk` | string | 目标 SDK 版本 |
| `max_sdk` | string | 最高 SDK 版本 |
| `effective_target_sdk` | int | 实际生效的目标 SDK |
| `is_multidex` | bool | 是否多 DEX |
| `is_valid` | bool | APK 是否有效 |
| `is_wearable` | bool | 是否穿戴设备应用 |
| `is_leanback` | bool | 是否 Leanback 界面 |
| `is_androidtv` | bool | 是否 Android TV 应用 |
| `dex_names` | list | DEX 文件名列表 |
| `main_activity` | string | 主 Activity |

## 使用场景

- 快速了解 APK 基本信息
- 判断 APK 是否有效
- 确认目标 SDK 版本（影响安全分析策略）
- 检测是否为多 DEX 应用

## Manifest 命令

获取完整的 AndroidManifest.xml：

```bash
androguard-skills apk manifest --apk-path test.apk
```

输出：

```json
{
  "manifest": "<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>\n<manifest ...>"
}
```
