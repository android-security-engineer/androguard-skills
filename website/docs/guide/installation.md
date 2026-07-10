# 安装

> 📦 Androguard Skills 是 `androguard` Python 包的一部分，命令入口为 `androguard-skills`。

## 系统要求

| 依赖 | 版本 |
|------|------|
| Python | ≥ 3.9（4.1.x 要求 `>3.9.0, !=3.9.1, <4.0`） |
| 操作系统 | Linux / macOS / Windows |
| 可选（可视化） | Graphviz（`dot` 命令，用于导出 CFG 图片） |
| 可选（动态分析） | Frida + 真机/模拟器（仅 `pentest` 组需要） |

## 方式一：pip 安装（推荐）

```bash
pip install androguard
```

安装后即获得两个命令：

```bash
androguard          # 原生 AndroGuard CLI
androguard-skills   # 本文档所述的 JSON CLI
```

验证安装：

```bash
androguard-skills --help
```

预期输出顶层命令组：`apk`、`dex`、`analysis`、`decompile`、`pentest`、`resources`、`visualize`、`util`、`session`、`daemon`、`load`、`load-dex`、`unload`。

## 方式二：从源码安装

适用于需要最新未发布特性、或想参与开发的情况。

```bash
git clone https://github.com/android-security-engineer/androguard-skills.git
cd androguard-skills
pip install -e .
```

`-e` 以"可编辑"模式安装，本地代码改动即时生效。

## 方式三：Poetry（开发者）

仓库的 `pyproject.toml` 使用 Poetry：

```bash
git clone https://github.com/android-security-engineer/androguard-skills.git
cd androguard-skills
poetry install
poetry shell   # 进入虚拟环境
androguard-skills --help
```

## 可选依赖

### Graphviz（CFG 图片导出）

仅 `visualize method-image` 命令需要：

```bash
# Debian/Ubuntu
sudo apt install graphviz
# macOS
brew install graphviz
# 验证
dot -V
```

其余 `visualize method-dot` 与 `visualize method-json` 不需要 Graphviz。

### Frida（动态分析）

仅 `pentest trace` / `pentest dump` 需要，且需要连接真机或模拟器：

```bash
pip install frida frida-tools
# 还需在目标设备运行 frida-server
```

::: tip 无 Frida 时也能用
即使没装 Frida，`pentest` 组命令也会优雅降级，返回结构化的"未安装 frida"提示而非崩溃。详见 [pentest 命令组](../commands/pentest/)。
:::

## 文档站本地预览（可选）

如果你想本地预览本套文档站点：

```bash
cd website
pnpm install        # 或 npm install
pnpm docs:dev       # 启动开发服务器
```

默认监听 `http://localhost:5173`。

## 常见安装问题

### `cryptography` 编译失败

`androguard` 依赖 `cryptography`，旧版可能需要 Rust 编译。确保 `pip` 版本较新，会自动拉取预编译 wheel：

```bash
pip install --upgrade pip
pip install androguard
```

### 命令找不到

确认安装的 Python 与当前 shell 的 `PATH` 一致。若用 `pip install --user`，需把用户 bin 目录加入 `PATH`：

```bash
# Linux/macOS
export PATH="$HOME/.local/bin:$PATH"
```

---

👈 [它能解决什么问题](./what-it-solves) · [快速开始 →](./quick-start) 👉
