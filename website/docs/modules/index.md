# 代码模块总览

> 🧩 Androguard Skills 的代码位于 `androguard/skills/`，分为 **CLI 层**、**业务模块层**、**daemon 基础设施**。

## 模块地图

| 模块 | 职责 | 公开方法数 | 对应命令组 |
|------|------|-----------|-----------|
| [`main.py`](./main) | CLI 入口，219 个 click 命令、参数解析、daemon 探测、JSON 输出 | 221 | 全部 |
| [`apk_skills.py`](./apk-skills) | APK 维度业务逻辑 | 53 | `apk` |
| [`dex_skills.py`](./dex-skills) | DEX 维度业务逻辑 | 44 | `dex` |
| [`analysis_skills.py`](./analysis-skills) | 静态分析与安全审计 | 62 | `analysis` |
| [`decompiler_skills.py`](./decompiler-skills) | 反编译封装 | 6 | `decompile` |
| [`resource_skills.py`](./resource-skills) | ARSC 资源解析 | 20 | `resources` |
| [`session_skills.py`](./session-skills) | 多文件 Session | 8 | `session` |
| [`util_skills.py`](./util-skills) | 工具函数 | 8 | `util` |
| [`visualize_skills.py`](./visualize-skills) | CFG 可视化 | 3 | `visualize` |
| [`pentest_skills.py`](./pentest-skills) | Frida 动态分析 | 2 | `pentest` |
| [`daemon.py`](./daemon) | daemon 进程管理与 JSON-RPC | — | `daemon` |

## 分层关系

```
CLI 层        main.py           (click 命令 + 参数 + 输出)
                │
基础设施层    daemon.py          (可选：常驻进程 + JSON-RPC)
                │
业务层        *_skills.py        (纯函数：引擎对象 → dict)
                │
引擎层        androguard.core    (APK/DEX/Analysis/DAD/ARSC)
```

详见 [架构总览](../guide/architecture)。

## 设计约定

- 业务模块是**模块级函数**（非类），第一参数是引擎对象（`apk_obj` / `dex_list` / `analysis_obj`）。
- 函数返回纯 Python `dict`/`list`，序列化由 CLI 层的 `SkillsJSONEncoder` 统一处理。
- CLI 命令名与 skills 方法名一一对应（连字符↔下划线）。
- 私有辅助函数以 `_` 开头，不构成 CLI 命令。

## 各模块详解

进入上方表格中各模块的子页，查看每个公开方法的签名、参数、docstring 与对应 CLI 命令。
