# 输出格式规范

> 📋 所有命令输出统一为 JSON。这一页定义成功与错误的结构，以及编码器对特殊类型的处理。

## 成功输出

命令成功时，stdout 输出一个 **JSON 对象**（`{...}`）或有时是 JSON 数组（`[...]`），具体结构因命令而异。每个命令文档都会给出输出 schema 与示例。

通用形态：

```json
{
  "field1": "value1",
  "field2": ["a", "b"],
  "field3": {"nested": true}
}
```

## 错误输出

命令失败时，输出统一结构：

```json
{"error": "错误信息字符串"}
```

- 永远只有一个 `error` 键，值是可读的错误描述。
- 进程退出码非零，便于 shell 脚本判断。
- **不会**把 Python traceback 直接打到 stdout——由 `_SkillsCliGroup` 统一捕获 `RuntimeError` 转成结构化 error。

```bash
$ androguard-skills dex class Lcom/Nonexistent;
{"error": "class not found: Lcom/Nonexistent;"}
```

## 编码器：`SkillsJSONEncoder`

AndroGuard 内部对象有许多不能直接 `json.dumps` 的类型（frozenset、generator、自定义类）。Skills 用自定义 `SkillsJSONEncoder` 统一处理：

| 原始类型 | JSON 化为 |
|---------|----------|
| `frozenset` | `list`（排序） |
| `generator` / `set` | `list` |
| `bytes` | base64 字符串（多数二进制字段，如 `apk file`、`apk raw`） |
| `datetime` | ISO 字符串 |
| 其他自定义对象 | 取其 `__dict__` 或预定义序列化方法 |

::: tip 这意味着
你不必担心拿到不可序列化的对象——任何命令的输出都能直接 `json.loads`。二进制字段会以 base64 出现，文档里会标注。
:::

## base64 二进制字段

涉及原始字节提取的命令会把二进制编码为 base64：

```bash
androguard-skills apk file AndroidManifest.xml --apk-path app.apk | jq -r '.content' | base64 -d > manifest.xml
```

这类命令包括：`apk file`、`apk raw`、`apk dex-data`、`apk axml`（部分）、`apk certificates-der`、`apk native-libraries --include-data` 等。

## 大输出与 limit

许多命令有 `--limit N` 选项，限制返回条数（避免巨型 JSON）：

```bash
# 只返回前 50 个类
androguard-skills dex classes --limit 50   # 注：classes 用 --filter，部分命令有 --limit
```

默认值因命令而异，详见各命令文档。需要全量时设大数或不传。

## 与 jq 配合

JSON 输出天然适配 `jq`：

```bash
# 取所有权限名
androguard-skills apk permissions --apk-path app.apk | jq '.permissions[].name'

# 统计类数量
androguard-skills dex classes --apk-path app.apk | jq '.classes | length'

# 提取安全报告的高危项
androguard-skills apk security-report --apk-path app.apk | \
  jq '.findings[] | select(.severity == "high")'
```

## 空结果

查询无结果时返回空容器，而非 error：

```bash
$ androguard-skills dex strings --filter "zzz_nonexistent" --apk-path app.apk
{"strings": []}
```

`error` 仅用于**执行失败**（文件找不到、类不存在、解析异常等），不用于"查到了但为空"。

---

👈 [JSON-RPC 协议](./jsonrpc-protocol) · [类名与描述符 →](./class-descriptors) 👉
