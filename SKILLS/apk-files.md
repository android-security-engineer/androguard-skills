# APK 文件列表

获取 APK 包内的文件列表及其类型和校验信息。

## 命令

```bash
androguard-skills apk files --apk-path test.apk
```

## 输出示例

```json
{
  "total": 42,
  "files": [
    {
      "name": "AndroidManifest.xml",
      "type": "Android's binary XML",
      "crc32": "0x1a2b3c4d"
    },
    {
      "name": "classes.dex",
      "type": "Dalvik dex file",
      "crc32": "0x5e6f7a8b"
    },
    {
      "name": "res/layout/activity_main.xml",
      "type": "Android's binary XML",
      "crc32": "0xc9d0e1f2"
    },
    {
      "name": "lib/armeabi-v7a/libnative.so",
      "type": "ELF shared object",
      "crc32": "0x3a4b5c6d"
    }
  ]
}
```

## 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `total` | int | 文件总数 |
| `files` | list | 文件信息列表 |
| `name` | string | 文件路径 |
| `type` | string | 文件类型（基于 magic 检测） |
| `crc32` | string | CRC32 校验值（十六进制） |

## 使用场景

- 了解 APK 结构和内容
- 检测是否存在 native 库（`.so` 文件）
- 检查资源文件布局
- 发现隐藏文件（如 `.dex` 文件不在默认位置）
- 完整性校验：比对 CRC32 值

## 安全关注点

| 关注点 | 说明 |
|--------|------|
| 多个 DEX 文件 | 可能有动态加载的 DEX |
| `.so` 文件 | 包含 native 代码，需单独分析 |
| assets 目录 | 可能包含加密的 DEX 或配置文件 |
| 非标准文件 | 隐藏的可执行文件或脚本 |
| CRC32 不匹配 | 文件可能被篡改 |
