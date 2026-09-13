# mcp

> Run as an MCP stdio server (JSON-RPC line-framed on stdin/stdout).

    Suitable for use with Claude Desktop, Claude Code, and any MCP-compatible
    client. Each request is one JSON line; each response is one JSON line.

    Example Claude Code config (~/.claude/settings.json)::

        { "mcpServers": { "androguard": { "command": "androguard-skills", "args": ["mcp"] } } }

## 用法

```bash
androguard-skills mcp
```

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `--with-ui` | flag | — | `False` | Also expose UI control tools (ui.snapshot, ui.action, etc.) |

## 说明

Run as an MCP stdio server (JSON-RPC line-framed on stdin/stdout).

    Suitable for use with Claude Desktop, Claude Code, and any MCP-compatible
    client. Each request is one JSON line; each response is one JSON line.

    Example Claude Code config (~/.claude/settings.json)::

        { "mcpServers": { "androguard": { "command": "androguard-skills", "args": ["mcp"] } } }

## 相关

- [命令索引](./)
