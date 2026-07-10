# Python API

> 🐍 不想走 CLI？直接在 Python 里调用 Skills。CLI 命令与 API 方法几乎一一对应。

## 入口类

```python
from androguard.skills import AndroguardSkillsMain
```

`AndroguardSkillsMain` 是核心类，CLI 的 `entry_point` 内部就是持有一个全局单例（`_get_skills()`）。每个 CLI 命令 `androguard-skills <group> <sub>` 对应一个 `skills.<method>()` 方法。

## 基本用法

```python
from androguard.skills import AndroguardSkillsMain
import json

skills = AndroguardSkillsMain()

# 加载 APK（等价于 CLI: load）
skills.load_apk("/path/to/app.apk")

# 查询（等价于 CLI: apk info / apk permissions）
print(json.dumps(skills.apk_info(), indent=2, ensure_ascii=False))
print(json.dumps(skills.apk_permissions(), indent=2, ensure_ascii=False))

# DEX 查询
print(json.dumps(skills.dex_classes(filter_regex="Activity"), indent=2, ensure_ascii=False))

# 安全报告
report = skills.apk_security_report()
print(report["risk_score"], report["summary"])
```

## 方法命名规则

CLI 命令名 → API 方法名的转换：

| CLI | API 方法 |
|-----|---------|
| `apk info` | `apk_info()` |
| `apk intent-filters` | `apk_intent_filters(component_name=...)` |
| `dex method-instructions` | `dex_method_instructions(class_name, method_name, limit=...)` |
| `analysis call-graph` | `analysis_call_graph(limit=, external=)` |
| `apk security-report` | `apk_security_report(per_type_limit=20)` |

规则：组名 + `_` + 子命令（连字符转下划线）。参数名与 skills 模块函数签名一致（蛇形），CLI 的 `--filter` 等 option 内部 dest 即此参数名。

## 参数传递

API 用关键字参数，与 skills 函数签名一致：

```python
# CLI: dex classes --filter "Activity"
skills.dex_classes(filter_regex="Activity")

# CLI: analysis method-callers Lcom/Foo; bar --max-depth 5 --include-external
skills.analysis_method_callers(
    class_name="Lcom/Foo;",
    method_name="bar",
    max_depth=5,
    include_external=True,
)

# CLI: apk security-report --limit 50
skills.apk_security_report(per_type_limit=50)
```

各方法的精确签名见 [代码模块文档](../modules/) 里对应模块的方法表。

## 显式加载对象

`load_apk` 是便捷方法，内部构建 `APK` / `DEX` / `Analysis` 并缓存。你也可以直接传入已有对象（高级用法，用于复用外部已解析的对象）——详见 `apk_skills.py` 等模块的函数签名，它们接受 `apk_obj` / `dex_list` / `analysis_obj` 作为第一参数。

## daemon 与 API 的关系

- **单进程内**：直接 `AndroguardSkillsMain()` 调用，对象在同一进程，最快。
- **跨进程**：CLI → daemon → `getattr(skills, method)` 反射调用——daemon 进程内的 `AndroguardSkillsMain` 单例。

API 适合**单进程内的复杂分析流程**；daemon 适合**多客户端/多 agent 共享**。

## JSON 序列化

API 方法返回纯 Python `dict`/`list`，可直接 `json.dumps`（编码器已处理特殊类型）：

```python
import json
result = skills.apk_info()
print(json.dumps(result, indent=2, ensure_ascii=False))
```

## 异常处理

API 不像 CLI 会把异常包成 `{"error": ...}`——它**直接抛异常**。需要自己 try/except：

```python
try:
    skills.dex_class(class_name="Lcom/Nonexistent;")
except Exception as e:
    print(f"查询失败: {e}")
```

::: tip CLI vs API 错误模型
CLI 的 `_SkillsCliGroup` 把异常转成 JSON error。API 没有这层包装——你要么自己 catch，要么让程序崩溃。这是设计上的差异：API 给你更细的控制权。
:::

## 完整示例：自动化审计脚本

```python
from androguard.skills import AndroguardSkillsMain
import json, sys

skills = AndroguardSkillsMain()
skills.load_apk(sys.argv[1])

report = skills.apk_security_report()

print(f"风险评分: {report['risk_score']}/100")
for finding in report.get("findings", []):
    if finding["severity"] in ("high", "critical"):
        print(f"  ⚠️ [{finding['severity']}] {finding['title']}")
        print(f"     {finding.get('detail', '')}")
```

## 相关文档

- [代码模块总览](../modules/) — 每个模块的方法签名表
- [Daemon 模式](./daemon-mode) — 跨进程复用
- [常见工作流](./workflows) — 更多脚本示例

---

👈 [资源 ID 体系](./resource-ids) · [常见工作流 →](./workflows) 👉
