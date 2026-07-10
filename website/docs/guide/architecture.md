# 架构总览

> 🏗️ Androguard Skills 是一个三层结构：**CLI 层** → **Skills 业务层** → **AndroGuard 引擎层**，外加一个 **Daemon 进程间通信层**横跨其间。

## 三层架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     用户 / Agent / CI                         │
│         (命令行 / Python API / JSON-RPC 客户端)              │
└───────────────┬───────────────────────────┬─────────────────┘
                │ 单次模式                    │ daemon 模式
                ▼                            ▼
┌───────────────────────────┐   ┌─────────────────────────────┐
│      CLI 层 (main.py)      │   │     Daemon 层 (daemon.py)    │
│  click 命令组 + 参数解析    │   │  DaemonServer (TCP/JSON-RPC) │
│  _try_daemon_call 探测      │◄──┤  DaemonClient (RPC 客户端)   │
│  _output_json 输出          │   │  _dispatch 动态路由          │
└───────────────┬───────────┘   └──────────────┬──────────────┘
                │                               │
                │      （两者都调用）            │
                ▼                               ▼
┌─────────────────────────────────────────────────────────────┐
│              Skills 业务层 (androguard/skills/*)              │
│  apk_skills · dex_skills · analysis_skills · decompiler_    │
│  skills · resource_skills · session_skills · util_skills ·  │
│  visualize_skills · pentest_skills                           │
│  （模块级函数：apk_info() / dex_classes() / ... 返回 dict）  │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│          AndroGuard 引擎层 (androguard.core / decompiler)     │
│   APK · DalvikVMFormat · Analysis · DAD 反编译器 · ARSC      │
└─────────────────────────────────────────────────────────────┘
```

## 第 1 层：CLI 层（`main.py`）

- **职责**：定义 219 个 `click` 命令，解析参数，决定走 daemon 还是本地。
- **入口**：`androguard-skills = androguard.skills.main:entry_point`（见 `setup.py` / `pyproject.toml`）。
- **关键机制**：
  - `_try_daemon_call(method, params)`：探测 daemon 是否在线，在线则发 JSON-RPC，离线则 fallback 本地调用。
  - `_output_json(data)`：统一用 `SkillsJSONEncoder` 序列化输出，处理 AndroGuard 不可直接序列化的类型（frozenset、generator 等）。
  - `_SkillsCliGroup`：自定义 click Group，统一捕获 `RuntimeError` 转成结构化 `{"error": ...}`。
  - 公共加载器 `_apk_loader` / `_dex_loader` / `_analysis_loader` / `_audit_loader`：统一"未加载则自动 load"逻辑。

::: tip CLI ≈ API
CLI 命令 `androguard-skills apk info` 几乎等价于 `AndroguardSkillsMain().apk_info()`——参数名、返回结构一致。文档里每个命令页都会标注对应的 skills 方法。
:::

## 第 2 层：Skills 业务层（`androguard/skills/*_skills.py`）

- **职责**：纯业务逻辑——接收引擎对象（APK/DEX/Analysis），调用 AndroGuard API，把结果组装成纯 Python `dict`/`list`。
- **特点**：模块级函数，不持有 CLI 上下文，**可独立用于 Python API**。
- **模块地图**：

| 模块 | 公开方法数 | 对应命令组 |
|------|-----------|-----------|
| `apk_skills.py` | 53 | `apk` |
| `dex_skills.py` | 44 | `dex` |
| `analysis_skills.py` | 62 | `analysis` |
| `decompiler_skills.py` | 6 | `decompile` |
| `resource_skills.py` | 20 | `resources` |
| `session_skills.py` | 8 | `session` |
| `util_skills.py` | 8 | `util` |
| `visualize_skills.py` | 3 | `visualize` |
| `pentest_skills.py` | 2 | `pentest` |

> 详见 [代码模块总览](../modules/)。

## 第 3 层：AndroGuard 引擎层

底层引擎，Skills 不重写，只封装：

- `androguard.core.apk.APK` — APK 解析
- `androguard.core.dex.DEX` / `DalvikVMFormat` — DEX 字节码
- `androguard.core.analysis.Analysis` — 交叉引用与分析
- `androguard.decompiler.DAD` — 反编译器
- `androguard.core.bytecodes.axml` / `arsc` — AXML 与资源

## 第 4 层：Daemon 通信层（`daemon.py`）

横跨在 CLI 与 Skills 之间，提供进程间复用：

- `DaemonServer`：TCP 服务器，监听 `127.0.0.1:8899`（可配），持有 `AndroguardSkillsMain` 单例。
- `DaemonClient`：CLI 侧的 RPC 封装，`call(method, params)` → JSON-RPC。
- `_dispatch` / `_dispatch_single`：把 JSON-RPC 的 `method` 字段通过 `getattr(skills, method_name)` 动态路由到 skills 方法——**daemon 不重复实现业务，只做转发**。

```
CLI 命令 → _try_daemon_call → DaemonClient.call → TCP → DaemonServer._dispatch
                                                            → getattr(skills, method)
                                                            → skills.<method>()
                                                            → JSON 响应
```

::: warning daemon 不持有你的代码
daemon 通过反射调用 skills 方法，所以你**不能**让 daemon 执行自定义 Python 函数——只能调用 219 个内置命令对应的方法。要跑自定义逻辑，请用 Python API 单进程内调用。
:::

## 数据流：一次 `apk info` 的旅程

**单次模式**：
```
androguard-skills apk info --apk-path t.apk
  → main.py: apk info 命令
  → _try_daemon_call("apk_info", {...})  探测 daemon → 不在线
  → fallback: _apk_loader() 自动 load_apk("t.apk")
  → skills.apk_info()  →  返回 dict
  → _output_json(dict)  →  stdout
```

**daemon 模式**：
```
androguard-skills apk info  (已 daemon start + load 过)
  → main.py: apk info 命令
  → _try_daemon_call("apk_info", {})  探测 daemon → 在线
  → DaemonClient.call("apk_info", {})
  → TCP → DaemonServer._dispatch_single → getattr(skills,"apk_info")()
  → skills.apk_info()  (复用已缓存 APK)  →  返回 dict
  → JSON-RPC 响应 → CLI → _output_json → stdout
```

两条路径对用户完全透明——输出 JSON 一致。

## 设计要点回顾

1. **CLI 与 Skills 解耦**：CLI 只管参数与输出，业务在 skills 模块，可被 Python 直接复用。
2. **Daemon 是可选加速层**：不改变命令语义，只改变"是否复用解析缓存"。
3. **反射路由**：daemon 用 `getattr` 转发，无需为每个命令写分发样板。
4. **统一 JSON 出口**：`SkillsJSONEncoder` + `_output_json` 保证输出格式恒定。

---

👈 [快速开始](./quick-start) · [单次执行模式 →](./standalone-mode) 👉
