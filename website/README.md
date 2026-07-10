# Androguard Skills 文档站

基于 [VitePress](https://vitepress.dev) 构建的文档站，覆盖 219 个 CLI 命令、代码模块、安全审计套件。

## 本地开发

```bash
cd website
pnpm install
pnpm docs:dev      # 启动开发服务器（http://localhost:5173）
```

## 构建

```bash
pnpm docs:build    # 产物输出到 docs/.vitepress/dist
pnpm docs:preview  # 预览构建产物
```

## 文档结构

```
website/
├── docs/                      # VitePress srcDir
│   ├── index.md               # 首页（hero + features）
│   ├── guide/                 # 核心导览（15 篇）
│   ├── commands/              # 命令参考（230 篇：1 索引 + 3 顶层 + 10 组×各命令）
│   ├── modules/               # 代码模块参考（12 篇）
│   ├── audit/                 # 安全审计专题（6 篇）
│   ├── public/                # 静态资源（logo svg）
│   └── .vitepress/config.ts   # VitePress 配置（导航/侧边栏/搜索）
└── scripts/                   # 文档生成脚本
    ├── introspect_commands.py # 从 click 命令树内省 → commands.json
    ├── gen_command_docs.py    # 基于 commands.json 生成命令文档页
    ├── gen_sidebar.py         # （备用）生成侧边栏片段
    └── commands.json          # 权威命令清单（生成器产物，勿手改）
```

## 命令文档如何保持与代码同步

命令文档由脚本从源码内省生成，**不要手改 `docs/commands/<group>/*.md`**。流程：

1. `python scripts/introspect_commands.py > scripts/commands.json` —— 从 `androguard.skills.main.entry_point` 的 click 命令树提取全部命令、参数、help、对应 skills 方法。
2. `python scripts/gen_command_docs.py` —— 基于 JSON 生成每命令一个 Markdown 页 + 各组 index 页。

CI（`.github/workflows/deploy_docs.yml`）在部署前会自动重跑这两步，保证文档与代码一致。

## GitHub Pages 部署

`.github/workflows/deploy_docs.yml` 在 push 到 master（触及 `website/`）时自动：

1. 安装 androguard + 内省重生成命令文档。
2. 根据 `GITHUB_REPOSITORY` 动态设置 `base` 路径。
3. 构建 VitePress。
4. 部署到 GitHub Pages。

部署 URL：https://android-security-engineer.github.io/androguard-skills/
