# 权限使用追踪 & API 使用分析

追踪权限在代码中的实际使用位置，以及 Android API 的使用情况。

## 权限使用追踪

查看指定权限在代码中的使用位置：

```bash
androguard-skills analysis permission-usage android.permission.INTERNET --apk-path test.apk
```

输出示例：

```json
{
  "permission": "android.permission.INTERNET",
  "usage_count": 3,
  "usages": [
    {
      "class": "Lcom/example/app/NetworkClient;",
      "method": "sendData",
      "descriptor": "([B)V"
    },
    {
      "class": "Lcom/example/app/NetworkClient;",
      "method": "fetchData",
      "descriptor": "(Ljava/lang/String;)[B"
    },
    {
      "class": "Lcom/example/app/Analytics;",
      "method": "reportEvent",
      "descriptor": "(Ljava/lang/String;)V"
    }
  ]
}
```

## 常用权限追踪

| 权限 | 关注点 |
|------|--------|
| `android.permission.INTERNET` | 网络通信 |
| `android.permission.READ_CONTACTS` | 读取通讯录 |
| `android.permission.ACCESS_FINE_LOCATION` | 精确位置 |
| `android.permission.CAMERA` | 摄像头 |
| `android.permission.RECORD_AUDIO` | 录音 |
| `android.permission.READ_SMS` | 读取短信 |
| `android.permission.WRITE_EXTERNAL_STORAGE` | 写外部存储 |

## Android API 使用分析

查看应用使用的所有 Android API：

```bash
androguard-skills analysis api-usage --apk-path test.apk
```

输出示例：

```json
{
  "total": 15,
  "android_api_usage": [
    {
      "class": "Landroid/telephony/TelephonyManager;",
      "method": "getDeviceId",
      "descriptor": "()Ljava/lang/String;"
    },
    {
      "class": "Landroid/telephony/SmsManager;",
      "method": "sendTextMessage",
      "descriptor": "(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Landroid/app/PendingIntent;Landroid/app/PendingIntent;)V"
    }
  ]
}
```

## 使用场景

- 权限最小化审计：检查声明的权限是否都有实际使用
- 隐私合规：追踪敏感权限（位置、通讯录等）的具体使用位置
- API 风险评估：发现使用了危险 API（如 `getDeviceId`、`sendTextMessage`）
- 动态分析规划：确定需要 Hook 的 API 方法

## 安全关注点

| API | 风险 |
|-----|------|
| `TelephonyManager.getDeviceId()` | 获取设备 IMEI，隐私风险 |
| `SmsManager.sendTextMessage()` | 发送短信，可能产生费用 |
| `Runtime.exec()` | 执行系统命令，命令注入风险 |
| `WebView.addJavascriptInterface()` | JS 接口注入，RCE 风险 |
| `Cipher.getInstance("DES")` | 使用弱加密算法 |
| `Socket()` | 直接网络通信，可能绕过安全检查 |
