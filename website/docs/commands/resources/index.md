# 🎨 resources · 资源解析

> ARSC 资源表解析：包/locale/类型/配置变体、strings.xml、public.xml、ids.xml、资源 ID 双向查询。共 20 个命令。

共 **20** 个命令。

## 命令列表

| 命令 | 说明 |
|------|------|
| [`bool`](./bool) | Get boolean resources for a package |
| [`color`](./color) | Get color resources for a package |
| [`configs`](./configs) | Get all configurations for a resource ID |
| [`dimen`](./dimen) | Get dimension resources for a package |
| [`get-string`](./get-string) | Get a single string resource value by package+key+locale |
| [`id`](./id) | Bidirectional resource ID lookup (ID&lt;-&gt;name) |
| [`id-resources`](./id-resources) | Get ids.xml (id-type resource list) |
| [`integer`](./integer) | Get integer resources for a package |
| [`locales`](./locales) | List supported locales for a resource package |
| [`packages`](./packages) | List resource packages |
| [`public`](./public) | Get public.xml (full type/name/id resource mapping) |
| [`res-configs`](./res-configs) | List config variants (locale/density, raw entry) for a specific resource ID |
| [`resolved-strings`](./resolved-strings) | Get all resolved string resources (package-&gt;locale-&gt;rid-&gt;value) |
| [`string-resources`](./string-resources) | Get string resources (strings.xml) for a package+locale |
| [`strings`](./strings) | Get all resolved string resources |
| [`strings-all`](./strings-all) | Get all string resources (full strings.xml across packages) |
| [`type-configs`](./type-configs) | List config variants for a resource type (all locales/densities) |
| [`types`](./types) | List resource types for a resource package |
| [`value`](./value) | Resolve a resource ID to its typed value (string/bool/color/dimen/integer/style/id) |
| [`xml-name`](./xml-name) | Resolve a resource ID to its XML reference name (@pkg:type/name) |

## 用法示例

```bash
androguard-skills resources --help    # 查看本组所有命令
androguard-skills resources <子命令> --help
```

- [命令索引](../)
