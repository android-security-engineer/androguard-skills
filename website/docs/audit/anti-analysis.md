# 反分析与加固

> 🧱 识别 APK 的加固/混淆/反调试特征。

## 相关命令

| 命令 | 关注点 |
|------|--------|
| `analysis anti-analysis` | root / 模拟器 / 调试器 / Frida / Xposed 检测（字符串 + API 双路扫描） |
| `analysis obfuscation-metrics` | 类名长度分布 / 反射密度 / 字符串覆盖 → 0-100 加固评分 |
| `apk manifest-axml` | AXML 加固检测 |
| `analysis dynamic-code` | DexClassLoader / native 加载（脱壳线索） |
| `analysis reflection-targets` | 反射目标还原（反混淆） |
| `analysis strings-overwritten` | 运行时被覆盖的字符串（混淆特征） |

## 工作流：判断是否加固

```bash
androguard-skills load app.apk

# 1. AXML 层面加固检测
androguard-skills apk manifest-axml

# 2. 量化混淆程度（0-100）
androguard-skills analysis obfuscation-metrics

# 3. 反分析特征
androguard-skills analysis anti-analysis

# 4. 动态加载线索（脱壳入口）
androguard-skills analysis dynamic-code
```

## 加固评分

`analysis obfuscation-metrics` 输出一个 0-100 的评分，综合：

- 类名平均长度（短名 = 强混淆）
- 反射调用密度
- 被覆盖字符串比例
- DEX 特征（隐藏 API、native 方法比例）

分数越高，加固/混淆越强。

## 相关

- [analysis anti-analysis 命令](../commands/analysis/anti-analysis)
- [analysis obfuscation-metrics 命令](../commands/analysis/obfuscation-metrics)
- [安全审计总览](./overview)
