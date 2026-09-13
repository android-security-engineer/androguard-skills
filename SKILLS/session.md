# Session 会话分析（多 APK/DEX 关联）

封装第五轮新增的 `androguard.misc.Session` 能力。Session 支持**多 APK/DEX 关联分析**，可按类定位其所属文件、统计全局字符串、列出所有类。

## 何时用 Session

`load` 命令走的是 `AnalyzeAPK` 单 APK 流程；Session 是**独立的加载路径**，适合：

- 多 APK/DEX 关联分析（同一类出现在哪个文件、digest 去重）
- 按类反查其所属的 APK 文件名和摘要
- 全局字符串统计（跨 DEX 去重）

> **跨命令持久**：`create`/`add-apk`/`info` 等命令操作的 Session 对象需跨命令复用。**单次模式**下每个 CLI 调用是新进程，Session 无法跨命令持久——请用 **daemon 模式**（`daemon start` 后 Session 持久在 daemon 进程中）。单次场景用 `analyze-apk` 一步到位。

## 命令

### `session analyze-apk <apk_path>`

用 Session 完整分析一个 APK（内部自动创建 Session、`addAPK` 加载 APK 及其所有 DEX）。**单次模式可用**——无需预创建 Session，一步完成分析并返回概要。

```bash
androguard-skills session analyze-apk test.apk
```

**输出：**
```json
{
  "is_open": true,
  "apk_count": 1,
  "dex_count": 1,
  "nb_strings": 2575,
  "apks": [
    {"digest": "349d2f4d...", "package": "org.billthefarmer.editor"}
  ],
  "dexes": [
    {"digest": "c6d83e18..."}
  ],
  "status": "analyzed",
  "path": "test.apk",
  "main_digest": "349d2f4d...",
  "dex_names": ["classes.dex"]
}
```

| 字段 | 说明 |
|------|------|
| `nb_strings` | 去重后的字符串总数 |
| `apks` | 加载的 APK（digest + 包名） |
| `dexes` | 加载的 DEX（按 DEX 内容的 SHA256 摘要标识） |
| `main_digest` | APK 文件的 SHA256 |

> 底层 API：`Session().addAPK(filename, data)`（内部自动 `addDEX` 所有 DEX，无需手动调用）。

### `session create`

创建一个新的空 Session 并持有（供后续 `add-apk`/`info` 等命令复用）。**需 daemon 模式**（单次模式下 Session 随进程结束丢失）。

```bash
androguard-skills daemon start           # 先启动 daemon
androguard-skills session create
```

### `session add-apk <apk_path>` / `session add-dex <dex_path>`

向当前 Session 添加 APK/DEX（多文件关联分析）。可多次调用添加多个文件，建立多 APK/DEX 关联。

```bash
androguard-skills session add-apk a.apk
androguard-skills session add-apk b.apk
androguard-skills session add-dex standalone.dex   # 添加独立 DEX
```

### `session info`

获取当前 Session 概要（APK/DEX 计数 + 跨文件去重字符串数）。

```bash
androguard-skills session info
```

**输出：**
```json
{
  "is_open": true,
  "apk_count": 2,
  "dex_count": 2,
  "nb_strings": 22412,
  "apks": [
    {"digest": "349d2f4d...", "package": "org.billthefarmer.editor"},
    {"digest": "a1b2c3...", "package": "sg.vantagepoint.helloworldjni"}
  ],
  "dexes": [{"digest": "c6d83e18..."}, {"digest": "..."}]
}
```

> `nb_strings` 是跨所有 DEX 去重后的字符串总数（单 APK 各自的字符串数之和会大于此值，因有去重）。

### `session filename-by-class <class_name>`

查询类在 Session 中**所属的文件名/摘要**——多 APK/DEX 关联定位的核心：给定一个类名，找出它定义在哪个文件里。

```bash
androguard-skills session filename-by-class "Lorg/billthefarmer/editor/Editor;"
```

**输出：**
```json
{
  "class": "Lorg/billthefarmer/editor/Editor;",
  "total": 1,
  "results": [
    {"class": "...", "dex_digest": "c6d83e18...", "session_filename": "editor.apk", "digest": "349d2f4d...", "format": "DEX"}
  ]
}
```

> `session_filename` 是类首次出现的文件名（APK 场景下返回 APK 文件名而非 DEX 文件名）。底层 API：`Session.get_filename_by_class(cls)`/`get_digest_by_class(cls)`/`get_format(cls)`。

### `session strings [--limit]`

获取 Session 各 DEX 的字符串分析（跨文件字符串统计，每个 DEX 一个条目，含每个字符串的 xref 计数）。

```bash
androguard-skills session strings --limit 50
```

| 参数 | 说明 |
|------|------|
| `--limit` | 每个 DEX 返回的字符串数量上限 |

**输出：**
```json
{
  "dex_count": 2,
  "dexes": [
    {"digest": "...", "filename": "editor.apk", "total": 2575, "returned": 50, "strings": [{"value": "http://...", "xref_count": 3}]}
  ]
}
```

> 底层 API：`Session.get_strings()` 返回 `(digest, filename, dict[str, StringAnalysis])`。与 `analysis strings-analysis`（单 APK）的区别：本命令跨 Session 内所有 DEX。

### `session classes [--limit]`

获取 Session 中所有类，按 DEX 分组。

```bash
androguard-skills session classes --limit 10
```

| 参数 | 说明 |
|------|------|
| `--limit` | 返回 DEX 分组数量上限 |

**输出：**
```json
{
  "total": 2,
  "returned": 2,
  "dexes": [
    {"index": 0, "filename": "editor.apk", "digest": "...", "class_count": 294, "classes": ["Lorg/billthefarmer/editor/Editor;", ...]}
  ]
}
```

> 底层 API：`Session.get_classes()` 返回 `(idx, filename, digest, class_list)`。用于跨文件类清单比对、重复类检测。

## 相关命令

- [`load`](README.md) — 单 APK 标准加载（AnalyzeAPK 流程）
- [`analysis find-strings`](dex-strings.md) — 单 APK 字符串搜索
- [`daemon`](README.md) — Session 跨命令持久需 daemon 模式
