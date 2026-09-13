# AndroidManifest 属性查询

> 批量/单个提取 manifest 标签属性值，按属性过滤查找标签

## 命令

### `apk manifest-attrs`

批量提取 AndroidManifest.xml 中指定标签的所有属性值。

```bash
# 提取所有 uses-permission 的 name 属性
androguard-skills apk manifest-attrs --tag uses-permission --attribute name --apk-path test.apk

# 提取所有 exported=true 的 activity 的 name
androguard-skills apk manifest-attrs --tag activity --attribute name --filter exported=true --apk-path test.apk
```

| 参数 | 说明 |
|------|------|
| `--tag` | manifest 标签名（如 uses-permission、activity、service） |
| `--attribute` | 属性名（如 name、exported、permission） |
| `--filter key=value` | 额外属性过滤条件（可重复指定多个） |

输出示例：

```json
{
  "tag": "uses-permission",
  "attribute": "name",
  "filter": {},
  "total": 3,
  "values": [
    "android.permission.WRITE_EXTERNAL_STORAGE",
    "android.permission.READ_EXTERNAL_STORAGE",
    "android.permission.INTERNET"
  ]
}
```

### `apk manifest-attr`

提取单个 manifest 属性值（首个匹配）。

```bash
androguard-skills apk manifest-attr --tag application --attribute debuggable --apk-path test.apk
```

输出示例：

```json
{
  "tag": "application",
  "attribute": "debuggable",
  "filter": {},
  "value": "false"
}
```

### `apk manifest-tags`

按属性过滤查找 manifest 标签，返回匹配标签的完整属性。

```bash
androguard-skills apk manifest-tags --tag activity --apk-path test.apk
androguard-skills apk manifest-tags --tag service --filter exported=true --apk-path test.apk
```

输出示例：

```json
{
  "tag": "activity",
  "filter": {},
  "total": 3,
  "tags": [
    {
      "tag": "activity",
      "attributes": {
        "name": "org.example.MainActivity",
        "exported": "true",
        "documentLaunchMode": "2"
      }
    }
  ]
}
```

## 安全分析用途

- **暴露组件发现**：`--filter exported=true` 快速找到所有导出的组件（攻击面）
- **权限枚举**：批量提取申请的权限列表
- **debuggable 检测**：`application` 标签的 `debuggable=true` 是高危配置
- **intent-filter 分析**：配合 `--filter` 定位特定 action/category 的组件
- **provider 权限**：检查 ContentProvider 的 `permission`/`readPermission`/`writePermission`
