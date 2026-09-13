# APK 权限分析

获取 APK 使用的权限及其保护级别详情。

## 命令

```bash
androguard-skills apk permissions --apk-path test.apk
```

## 输出示例

```json
{
  "permissions": [
    "android.permission.ACCESS_NETWORK_STATE",
    "android.permission.INTERNET",
    "android.permission.READ_CONTACTS"
  ],
  "details_permissions": {
    "android.permission.ACCESS_NETWORK_STATE": ["normal"],
    "android.permission.INTERNET": ["normal"],
    "android.permission.READ_CONTACTS": ["dangerous"]
  },
  "uses_implied_permissions": [
    "android.permission.ACCESS_NETWORK_STATE"
  ],
  "requested_aosp_permissions": [
    "android.permission.ACCESS_NETWORK_STATE",
    "android.permission.INTERNET",
    "android.permission.READ_CONTACTS"
  ],
  "requested_third_party_permissions": [],
  "declared_permissions": [],
  "declared_permissions_details": {}
}
```

> 注：所有 list 字段按字母序排序，所有 dict 字段按键名排序——保证同一 APK
> 多次运行输出字节级一致（agent 对接需确定性比对）。

## 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `permissions` | list | 所有声明的权限 |
| `details_permissions` | dict | 权限 → 保护级别映射 |
| `uses_implied_permissions` | list | 隐含使用的权限 |
| `requested_aosp_permissions` | list | AOSP 标准权限 |
| `requested_aosp_permissions_details` | dict | AOSP 权限详情 |
| `requested_third_party_permissions` | list | 第三方自定义权限 |
| `declared_permissions` | list | 应用自定义声明的权限 |
| `declared_permissions_details` | dict | 自定义权限详情 |

## 保护级别

| 级别 | 说明 |
|------|------|
| `normal` | 普通权限，自动授予 |
| `dangerous` | 危险权限，需用户确认 |
| `signature` | 签名权限，同签名应用才能使用 |
| `signature or system` | 签名或系统权限 |
| `internal` | 内部权限 |

## 使用场景

- 安全审计：检查是否申请了过多危险权限
- 隐私分析：识别访问敏感数据的权限（通讯录、位置、相机等）
- 合规检查：确认权限使用是否符合隐私政策
- 检测自定义权限定义（可能存在权限提升风险）

## 权限使用追踪

查看权限在代码中的实际使用位置：

```bash
androguard-skills analysis permission-usage android.permission.INTERNET --apk-path test.apk
```

详见 [analysis-permissions.md](analysis-permissions.md)
