# APK Features / Libraries / Icon

> uses-feature、uses-library、应用图标提取

## 命令

### `apk features`

获取 APK 声明的硬件/软件 feature 列表（`<uses-feature>`）。

```bash
androguard-skills apk features --apk-path test.apk
```

输出示例：

```json
{
  "total": 3,
  "features": [
    "android.hardware.touchscreen",
    "android.hardware.camera",
    "android.software.leanback"
  ]
}
```

### `apk libraries`

获取 APK 声明的共享库列表（`<uses-library>`）。

```bash
androguard-skills apk libraries --apk-path test.apk
```

输出示例：

```json
{
  "total": 1,
  "libraries": [
    "com.google.android.maps"
  ]
}
```

### `apk icon`

获取 APK 应用图标信息，包含路径、大小和 base64 编码数据。

```bash
androguard-skills apk icon --apk-path test.apk
androguard-skills apk icon --max-dpi 480 --apk-path test.apk
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--max-dpi` | 65536 | 图标最大 DPI 阈值 |

输出示例：

```json
{
  "icon_path": "res/mipmap-xxxhdpi/ic_launcher.png",
  "size": 15234,
  "base64": "iVBORw0KGgo..."
}
```

## 安全分析用途

- **feature 枚举**：判断目标设备要求（是否需要摄像头、NFC 等）
- **library 检测**：识别依赖的共享库（如 Google Maps 说明可能存在位置功能）
- **图标提取**：用于识别伪造应用（图标对比）
