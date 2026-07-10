# JSON-RPC 协议

> 🔌 daemon 通过 TCP 承载 **JSON-RPC 2.0** 协议。这一页描述请求/响应结构、批量请求与错误模型。

## 传输层

- **协议**：TCP，行分隔（每条 JSON-RPC 消息以 `\n` 结尾）。
- **地址**：默认 `127.0.0.1:8899`（仅本机，`daemon start --port` 可改）。
- **编码**：UTF-8 JSON。

`DaemonServer._handle_client` 按 `\n` 缓冲累积——支持**大请求不截断**、**分片重组**、**流水线**（一个连接内连续发多个请求，服务端顺序处理）。

## 单请求

```json
{"jsonrpc": "2.0", "method": "apk_info", "params": {}, "id": 1}
```

响应：

```json
{"jsonrpc": "2.0", "result": {"package": "com.example", ...}, "id": 1}
```

字段说明：

| 字段 | 必填 | 说明 |
|------|------|------|
| `jsonrpc` | ✅ | 固定 `"2.0"` |
| `method` | ✅ | skills 方法名，如 `apk_info`、`dex_classes`（下划线形式，非连字符） |
| `params` | 可选 | 对象形式 `{}`，对应方法参数 |
| `id` | ✅ | 请求标识，响应里原样回传 |

## method 命名规则

CLI 命令 `androguard-skills apk info` 对应的 `method` 是 **`apk_info`**（组名_子命令，下划线连接，连字符转下划线）。

| CLI 命令 | JSON-RPC method |
|----------|-----------------|
| `apk info` | `apk_info` |
| `apk intent-filters <c>` | `apk_intent_filters` |
| `dex method-instructions` | `dex_method_instructions` |
| `analysis call-graph` | `analysis_call_graph` |
| `apk security-report` | `apk_security_report` |

::: tip 反射路由
daemon 用 `getattr(skills, method_name)` 动态查找方法，所以 method 名必须与 `AndroguardSkillsMain` 的方法名精确匹配。
:::

## params 命名规则

`params` 用**关键字参数**形式，键名是 skills 方法的参数名（蛇形）：

```bash
# CLI: dex classes --filter "Activity"
# 等价 RPC:
{"jsonrpc":"2.0","method":"dex_classes","params":{"filter_regex":"Activity"},"id":1}
```

注意 CLI 的 `--filter` 选项内部 dest 是 `filter_regex`——RPC 用后者。各命令的 params 键名见对应命令文档。

## 加载类方法

`load_apk` / `unload` / `load_dex` 也可通过 RPC 调用：

```json
{"jsonrpc":"2.0","method":"load_apk","params":{"apk_path":"/path/to/app.apk"},"id":1}
```

`daemon status` 等基础设施命令走的是 `DaemonClient.status`，不经过 `_dispatch`。

## 批量请求

JSON-RPC 2.0 允许一个请求体是**数组**：

```bash
echo '[
  {"jsonrpc":"2.0","method":"status","params":{},"id":1},
  {"jsonrpc":"2.0","method":"apk_info","params":{},"id":2},
  {"jsonrpc":"2.0","method":"apk_permissions","params":{},"id":3}
]' | nc 127.0.0.1 8899
```

响应也是数组，顺序与请求一致：

```json
[
  {"jsonrpc":"2.0","result":{"running":true},"id":1},
  {"jsonrpc":"2.0","result":{"package":"com.example",...},"id":2},
  {"jsonrpc":"2.0","result":{"permissions":[...]},"id":3}
]
```

**单个请求失败不影响其余**——失败的项返回 error 对象，其余正常返回 result。

## 错误响应

方法执行抛异常时，返回 JSON-RPC error：

```json
{"jsonrpc":"2.0","error":{"code":-32603,"message":"class not found: Lcom/Foo;"},"id":1}
```

| code | 含义 |
|------|------|
| `-32600` | 无效请求（非合法 JSON-RPC） |
| `-32601` | method 不存在（getattr 找不到） |
| `-32603` | 内部错误（方法执行抛异常） |

## 慢命令与超时

某些命令（如 `load_apk` 解析大 APK、`analysis call-graph` 构建全图）较慢。`DaemonClient` 对普通命令有 30s 超时，但对已知慢命令（`load_apk` 等）放宽到 **600s**，避免误杀。

::: warning 不要用超短的客户端超时
自己写 RPC 客户端时，`load_apk` 大 APK 可能需要数十秒——超时设太短会误判失败。建议对 `load_apk` 单独设 600s。
:::

## Python 客户端示例

```python
import socket, json

def call(method, params=None, id=1, port=8899):
    req = {"jsonrpc": "2.0", "method": method, "params": params or {}, "id": id}
    with socket.create_connection(("127.0.0.1", port), timeout=600) as s:
        s.sendall((json.dumps(req) + "\n").encode())
        data = b""
        while b"\n" not in data:
            data += s.recv(65536)
        return json.loads(data.decode())

print(call("apk_info"))
print(call("dex_classes", {"filter_regex": "Activity"}))
```

## 相关文档

- [Daemon 模式](./daemon-mode)
- [daemon 命令组](../commands/daemon/)
- [输出格式规范](./output-format)

---

👈 [内存管理](./memory-management) · [输出格式规范 →](./output-format) 👉
