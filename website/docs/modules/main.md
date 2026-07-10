# 模块：main.py · CLI 入口

> 📌 Androguard Skills 的 CLI 入口，定义全部 219 个 click 命令

## 概述

`androguard/skills/main.py`（6947 行）是整个工具链的 **CLI 层**，承担五类职责：

| 职责 | 承载者 | 说明 |
|------|--------|------|
| 🔣 命令组与命令定义 | `entry_point` + 10 个 `@entry_point.group` 子组 + 各 `@<group>.command` | 共 213 个子命令 + 3 个顶层命令 + 3 个 daemon 子命令 = **219** |
| 🔧 参数解析 | `click` 装饰器 `@click.argument` / `@click.option` | `--apk-path` 普遍支持 `ANDROGUARD_APK_PATH` 环境变量 |
| 🔌 daemon 探测与 fallback | `_try_daemon_call(method, params)` | daemon 在跑→RPC；不在跑→单次执行；慢命令 600s timeout |
| 📦 统一 JSON 输出 | `_output_json(data)` + `_SkillsJsonEncoder` | 处理 `frozenset`/`bytes`/`filter`/`map`/`generator` 等不可直接序列化类型 |
| 🛡️ 错误捕获 | `_SkillsCliGroup`（自定义 `click.Group`） | 捕获 `RuntimeError` 转 `{"error": "..."}`，吞掉 Python traceback |

此外，`main.py` 还定义了核心类 `AndroguardSkillsMain`（行 31–2476）——它持有 `_apk`/`_dex_list`/`_analysis`/`_session` 状态对象，把 `androguard.core` 引擎能力封装为全部返回 `dict` 的可程序化方法。CLI 命令函数体只做"daemon 优先 → fallback 单次执行 → JSON 输出"的薄封装，业务逻辑全部下沉到 `AndroguardSkillsMain` 方法与 `*_skills.py` 模块级函数。

## 命令组结构

`entry_point`（行 2587）是顶层 `click.Group`，下挂 10 个命令组 + 3 个顶层命令：

| 组名 | 命令数 | help 文本 | 定义行 |
|------|--------|-----------|--------|
| `daemon` | 3 | Manage the daemon process | 2610 |
| `apk` | 56 | APK information commands | 2697 |
| `dex` | 44 | DEX information commands | 3683 |
| `analysis` | 69 | Static analysis commands | 4520 |
| `decompile` | 6 | Decompilation commands | 6003 |
| `pentest` | 2 | Dynamic analysis / pentest commands | 6151 |
| `resources` | 20 | Android resource parsing commands | 6192 |
| `visualize` | 3 | Method visualization / CFG export commands | 6671 |
| `util` | 5 | Utility commands (file detection, AOSP permissions) | 6752 |
| `session` | 8 | Session commands (multi-APK/DEX correlation analysis) | 6817 |
| **（顶层）** | 3 | `load` / `unload` / `load-dex`（直接挂在 `entry_point`） | 2656 / 2672 / 6938 |

合计 **219**（213 子命令 + 3 daemon 子命令 + 3 顶层命令）。命令清单由 `scripts/introspect_commands.py` 从 click 命令树内省生成，见 [`/commands/`](../commands/)。

## 关键机制

### 🧬 `_get_skills()` — 全局单例（行 2480）

```python
_skills_instance = None  # 行 2477，模块级全局

def _get_skills() -> AndroguardSkillsMain:
    global _skills_instance
    if _skills_instance is None:
        _skills_instance = AndroguardSkillsMain()
    return _skills_instance
```

单次执行模式下，所有命令共享同一个 `AndroguardSkillsMain` 实例，故 `load` 之后 `apk info` 能拿到已加载的 `_apk`。daemon 模式下则由 `DaemonServer._get_skills()` 在 daemon 进程内维护自己的单例（见 [daemon.py](./daemon)）。

### 🔌 `_try_daemon_call(method, params)` — daemon 探测 + fallback（行 2533）

核心调度函数，返回值三态：

| 情形 | 返回值 | CLI 行为 |
|------|--------|----------|
| daemon 在跑且方法成功 | 结果 `dict` | `_output_json(result)` 直接输出 |
| daemon 在跑但方法报错 | `{"error": "..."}` | `_output_json` 输出，**不 fallback** |
| daemon 未运行 / 连不上 | `None` | 触发单次执行 fallback |

关键区分（行 2542–2545）：daemon 在跑 + 方法报错（如未 load APK、APK 损坏）应直接返回结构化 error，而非返回 `None` 触发 fallback——否则 fallback 单次执行会因同样原因再崩一次 traceback，且对 agent 来说 error 不是合法 JSON 无法自恢复。

慢命令 600s timeout（行 2551–2553）：

```python
slow_methods = {"load_apk", "load_dex", "session_analyze_apk",
                "session_add_apk", "session_add_dex"}
client_timeout = 600.0 if method in slow_methods else 30.0
```

解析大 APK/DEX 可能耗时数十秒到数分钟，默认 30s timeout 会把正常的大 APK load 误判超时→fallback 重新解析一遍（更慢，且 daemon 那边仍在解析）。对这类命令用 600s 长 timeout。

异常分流（行 2558–2570）：`ConnectionError`/`OSError`（含 `socket.timeout`、`ConnectionRefusedError`）→ daemon 连不上 → 返回 `None` fallback；`RuntimeError`（`DaemonClient.call` 对 JSON-RPC error 抛出）→ daemon 在跑但报错 → 返回 `{"error": ...}` 不 fallback，并剥去 `"Daemon error:"` 前缀。

### 📦 `_output_json(data)` + `_SkillsJsonEncoder` — 统一输出（行 2488 / 2512）

```python
def _output_json(data: dict):
    print(json.dumps(data, indent=2, ensure_ascii=False, cls=_SkillsJsonEncoder))
```

`_SkillsJsonEncoder.default()` 处理 AndroGuard 返回的不可直接序列化类型（行 2495–2509）：

- `set` / `frozenset` → `list`（AndroGuard 权限集合等用 `frozenset`）
- `bytes` / `bytearray` → `obj.hex()`
- `filter` / `map` / `zip` / `range` → `list`
- 任意 `generator`（`hasattr(obj, "__next__")`）→ `list`（兜底，明确具名类型优先）

`ensure_ascii=False` 保留中文，`indent=2` 美化输出。daemon 侧有同步的 `_DaemonJsonEncoder`（见 [daemon.py](./daemon)），逻辑一致但保持独立以避免模块级导入循环。

### 🛡️ `_SkillsCliGroup` — 自定义 click Group（行 2578）

```python
class _SkillsCliGroup(click.Group):
    def invoke(self, ctx):
        try:
            return super().invoke(ctx)
        except RuntimeError as e:
            _output_json({"error": str(e)})
            ctx.exit(0)
```

统一捕获 skills 执行异常，输出结构化 error JSON 而非 Python traceback。单次 fallback 路径下，APK 无效/未加载等 `RuntimeError` 会被转成 `{"error": "..."}`，agent 可解析自恢复。daemon 路径的 `_dispatch` 已自行捕获（返回 JSON-RPC error），不经过这里。Click 自身的参数错误（缺参数等）是 `ClickException` 子类，交回 Click 处理，不被吞。

### 🔄 公共加载器

无参/单参命令的 fallback 路径复用以下加载器，避免重复样板：

| 加载器 | 行号 | 用途 |
|--------|------|------|
| `_apk_loader(apk_path)` | 3340 | `apk` 组命令：未加载时按 `--apk-path` 自动 `load_apk`，无路径则输出 `{"error": "No APK loaded..."}` |
| `_dex_loader(apk_path)` | 4126 | `dex` 组命令：同上 |
| `_analysis_class_loader(class_name, apk_path)` | 5140 | `analysis` 组单参数类命令（如 `class-hierarchy-info`）：同上 |
| `_analysis_audit_cli(method_name, per_type_limit, apk_path)` | 5754 | 漏洞审计类命令共享执行体：daemon 优先 → fallback → `getattr(skills, method_name)(per_type_limit)` 委托 |

加载器模式统一为：`_get_skills()` 取单例 → 检查 `is_loaded` → 未加载则按 `--apk-path` 加载或报错。

### 🚪 `entry_point` — 顶层 group（行 2587）

```python
@click.group(cls=_SkillsCliGroup, help="AndroGuard Skills - Android 逆向工程能力 CLI")
@click.version_option(version="4.1.4")
@click.option("--verbose", "--debug", "verbosity", flag_value="verbose",
              help="Print more information")
def entry_point(verbosity):
    if verbosity is None:
        logger.remove()
        logger.add(sys.stderr, level="ERROR")
    else:
        logger.remove()
        logger.add(sys.stderr, level="INFO")
```

`--verbose` / `--debug` 是 flag_value 选项（默认 `None`）。默认移除 loguru 默认 handler 并降到 `ERROR` 级别（避免 AndroGuard 大量 INFO 日志刷屏）；传入则升到 `INFO`。这是 console.py 入口点 `androguard-skills` 注册的 `console_scripts` 目标。

## 命令→方法映射

CLI 命令函数体遵循统一模式（以 `apk declared-permissions` 为例，行 3351–3361）：

```python
@apk.command(name="declared-permissions")
@click.option("--apk-path", envvar="ANDROGUARD_APK_PATH", help="APK file path")
def apk_declared_permissions_cmd(apk_path):
    """Get permissions declared (custom <permission> tags) by the APK"""
    result = _try_daemon_call("apk_declared_permissions")          # ① daemon 优先
    if result is not None:
        _output_json(result)                                        # ② daemon 成功/报错→输出
        return
    skills = _apk_loader(apk_path)                                  # ③ fallback 单次执行
    if skills is not None:
        _output_json(skills.apk_declared_permissions())             # ④ 调 skills.method()
```

命令名（连字符）与 `AndroguardSkillsMain` 方法名（下划线）一一对应，转换规则为 `name.replace("-", "_")`。`_try_daemon_call` 的 `method` 参数即下划线形式方法名，`params` 为参数字典。

顶层命令 `load`（行 2656）与 `unload`（行 2672）同样 daemon 优先；`load-dex`（行 6938）因 DEX 加载无 daemon 缓存语义，直接单次执行。`AndroguardSkillsMain.load_apk`（行 73）对不存在文件抛 `RuntimeError(f"File not found: {apk_path}")`，由 `_SkillsCliGroup` 统一捕获；`unload`（行 120）在释放 Python 引用 + `gc.collect()` 后，还通过 `ctypes.CDLL("libc.so.6").malloc_trim(0)` 让 glibc 归还空闲 arena 给 OS，降低 daemon 长跑 RSS 高位。

## 相关

- 📚 [代码模块总览](./) — 全部模块地图与分层关系
- 🏗️ [架构总览](../guide/architecture) — CLI / daemon / 业务 / 引擎四层
- 🗂️ [命令参考](../commands/) — 219 个命令的完整清单（按组索引）
- 📡 [daemon.py 模块](./daemon) — 对应的进程管理与 RPC 通道
- 🔌 [Daemon 模式](../guide/daemon-mode) / [JSON-RPC 协议](../guide/jsonrpc-protocol)
- 🧠 [内存管理](../guide/memory-management) — `unload` 的 `malloc_trim` 机制
