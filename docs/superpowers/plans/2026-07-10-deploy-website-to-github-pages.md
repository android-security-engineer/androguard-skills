# 部署 Website 到 GitHub Pages 并更新仓库 URL Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:subagent-driven-development`
> Steps use checkbox (`- [ ]`) syntax.

**Goal:** 把 `website/` VitePress 文档站通过现有 GitHub Action 部署到 GitHub Pages（`https://android-security-engineer.github.io/androguard-skills/`），并把仓库内所有 website 相关的 URL/链接从误指上游 `androguard/androguard` 修正为指向本仓库 `android-security-engineer/androguard-skills` + Pages 真实地址。

**Architecture:** 数据流：push 到 master 触发 `deploy_docs.yml` → build job 装依赖+内省重生成命令文档+sed 覆盖 base+`pnpm docs:build` → upload-pages-artifact → deploy job `deploy-pages` 发布到 Pages site。关键改动分三类：(1) config.ts 把 nav/socialLinks/editLink 从上游 `androguard/androguard` 改指本仓库；(2) installation.md 的两处 git clone 改指本仓库；(3) 用 `gh api` 创建从未启用过的 Pages site（build_type=workflow），让 deploy job 有落点。base 默认值固化为本仓库 repo 名 `/androguard-skills/`（CI 的 sed 也产出同值，但固化后即使 sed 失败本地/CI 都对）。

**Tech Stack:** GitHub Actions（actions/checkout@v4, setup-node@v4, pnpm/action-setup@v4, setup-python@v5, configure-pages@v5, upload-pages-artifact@v3, deploy-pages@v4）, VitePress 1.6.4, pnpm 10, Node 22, Python 3.12, gh CLI 2.94

**Risks:**
- Pages 从未启用（API 返回 404），`deploy-pages` job 会在 site 不存在时失败 → 缓解：Task 4 Step 1 先 `gh api -X POST .../pages` 创建 site（build_type=workflow），再触发 CI
- config.ts 默认 base 与 CI sed 产物恰好一致是巧合，sed 若失败则站点路径错 → 缓解：Task 1 把默认 base 固化为 `/androguard-skills/`，消除对 sed 的硬依赖（sed 仍保留作 CI 自适应）
- `installation.md:3` 的 `pip install androguard` 仍指 PyPI 包名（正确，包就叫 androguard），不能误改成仓库 URL → 缓解：只改 git clone 两行，不动 pip 行
- editLink pattern 的分支名必须与本仓库默认分支一致 → 已确认 `master`，pattern 保持 `master`
- 修正链接后需 commit + push 才能触发 CI，push 是 outward-facing 动作 → 缓解：在独立 commit 中完成，push 前已自检构建

---

### Task 1: 修正 config.ts 仓库链接与固化 base 默认值

**Depends on:** None
**Files:**
- Modify: `website/docs/.vitepress/config.ts:11-15`（repo + base 常量区块）
- Modify: `website/docs/.vitepress/config.ts:78`（nav GitHub 链接）
- Modify: `website/docs/.vitepress/config.ts:201`（socialLinks）
- Modify: `website/docs/.vitepress/config.ts:205-208`（footer copyright）
- Modify: `website/docs/.vitepress/config.ts:235-238`（editLink pattern）

- [ ] **Step 1: 修正 repo/base 常量与注释 — 固化部署 base 为本仓库 repo 名**

文件: `website/docs/.vitepress/config.ts:11-15`（仓库信息注释 + repo/base 常量区块）

```typescript
// 仓库信息 —— 用于 GitHub Pages 部署的 base 路径与编辑链接
// 本仓库：https://github.com/android-security-engineer/androguard-skills
// 部署到 https://android-security-engineer.github.io/androguard-skills/
// CI（deploy_docs.yml）会根据 GITHUB_REPOSITORY 再次覆盖此 base 值（自适应仓库名）；
// 这里默认值固化为本仓库 repo 名，保证本地预览与 CI 一致，即使 sed 失败也不致路径错乱。
const repo = 'android-security-engineer/androguard-skills'
const repoUrl = `https://github.com/${repo}`
const pagesUrl = `https://android-security-engineer.github.io/androguard-skills/`
const base = `/androguard-skills/`
```

- [ ] **Step 2: 修正 nav GitHub 链接 — 指向本仓库而非上游**

文件: `website/docs/.vitepress/config.ts:78`（nav 数组最后一项 GitHub 链接）

```typescript
      { text: 'GitHub', link: repoUrl },
```

- [ ] **Step 3: 修正 socialLinks — 导航栏 GitHub 图标指向本仓库**

文件: `website/docs/.vitepress/config.ts:199-202`（socialLinks 区块）

```typescript
    // 社交链接（导航栏右侧图标）
    socialLinks: [
      { icon: 'github', link: repoUrl },
    ],
```

- [ ] **Step 4: 修正 footer copyright — 更新年份与归属为本仓库**

文件: `website/docs/.vitepress/config.ts:204-208`（footer 区块）

```typescript
    // 页脚
    footer: {
      message: '基于 Apache-2.0 协议发布 · 文档站部署于 GitHub Pages',
      copyright: 'Copyright © 2024 Androguard Skills',
    },
```

- [ ] **Step 5: 修正 editLink pattern — 编辑链接指向本仓库 master 分支**

文件: `website/docs/.vitepress/config.ts:234-238`（editLink 区块）

```typescript
    // 编辑此页链接
    editLink: {
      pattern: `${repoUrl}/edit/master/website/docs/:path`,
      text: '在 GitHub 上编辑此页',
    },
```

- [ ] **Step 6: 验证 config.ts 无上游仓库残留且所有链接指向本仓库**

验证两件事：(a) 文件里不再出现上游 `androguard/androguard` 字样；(b) `repoUrl`/`pagesUrl` 等新常量已就位。

Run: `cd website && (! grep -q "androguard/androguard" docs/.vitepress/config.ts && echo "CLEAN: 无上游残留" || echo "STILL HAS 上游链接") && grep -nE "repoUrl|pagesUrl|android-security-engineer/androguard-skills" docs/.vitepress/config.ts`
Expected:
  - Exit code: 0
  - Output contains: "CLEAN: 无上游残留"
  - Output contains: "android-security-engineer/androguard-skills"（新常量/链接就位）

- [ ] **Step 7: 验证 VitePress 构建通过**
Run: `cd website && pnpm docs:build`
Expected:
  - Exit code: 0
  - Output contains: "build complete"
  - Output does NOT contain: "error"（小写、非 Error 级别的依赖警告可忽略）

- [ ] **Step 8: 提交**
Run: `git add website/docs/.vitepress/config.ts && git commit -m "fix(docs): point website links to this repo + fix base path for GitHub Pages"`

---

### Task 2: 修正 installation.md 的 git clone 地址为本仓库

**Depends on:** None
**Files:**
- Modify: `website/docs/guide/installation.md:40`（方式二 git clone）
- Modify: `website/docs/guide/installation.md:52`（方式三 git clone）

- [ ] **Step 1: 修正方式二的 git clone — 从源码安装指向本仓库**

文件: `website/docs/guide/installation.md:39-43`（方式二代码块）

```bash
git clone https://github.com/android-security-engineer/androguard-skills.git
cd androguard-skills
pip install -e .
```

- [ ] **Step 2: 修正方式三的 git clone — Poetry 安装指向本仓库**

文件: `website/docs/guide/installation.md:51-57`（方式三代码块）

```bash
git clone https://github.com/android-security-engineer/androguard-skills.git
cd androguard-skills
poetry install
poetry shell   # 进入虚拟环境
androguard-skills --help
```

- [ ] **Step 3: 验证 installation.md 无上游仓库 git clone 残留**
Run: `grep -n "github.com/androguard/androguard.git" website/docs/guide/installation.md; test $? -eq 1 && echo "CLEAN" || echo "STILL HAS"`
Expected:
  - Exit code: 0
  - Output contains: "CLEAN"

- [ ] **Step 4: 提交**
Run: `git add website/docs/guide/installation.md && git commit -m "docs(guide): fix git clone URLs to point to this repo"`

---

### Task 3: 核对并加固 CI workflow

**Depends on:** None
**Files:**
- Modify: `.github/workflows/deploy_docs.yml:69-82`（base sed 步骤，加幂等性说明注释）
- Verify: `website/pnpm-lock.yaml`（已确认存在，frozen-lockfile 安全）

- [ ] **Step 1: 核对 workflow 现状 — 确认逻辑完整无遗漏**

只读核对，不改文件。逐项确认：
1. `on.push.paths` 含 `website/**` 与 workflow 自身 ✅
2. `permissions` 含 `pages: write` + `id-token: write` ✅
3. build job 装依赖 + 内省重生成 + sed base + build + upload ✅
4. deploy job 用 `deploy-pages@v4` ✅
5. artifact path = `website/docs/.vitepress/dist` ✅

Run: `grep -E "upload-pages-artifact|deploy-pages|pages: write|id-token: write|paths:" .github/workflows/deploy_docs.yml`
Expected:
  - Exit code: 0
  - Output contains: "upload-pages-artifact" and "deploy-pages" and "pages: write" and "id-token: write"

- [ ] **Step 2: 加固 base sed 步骤的幂等性注释 — 让 sed 逻辑意图清晰可维护**

文件: `.github/workflows/deploy_docs.yml:69-82`（Configure base path 步骤）

```yaml
      - name: Configure base path for GitHub Pages
        working-directory: website
        # 根据仓库名动态设置 base：部署到 https://<user>.github.io/<repo>/
        # 若是用户/组织站点 (<user>.github.io)，base 应为 '/'
        # config.ts 默认 base 已固化为 /androguard-skills/（本仓库 repo 名），
        # 本步骤按 GITHUB_REPOSITORY 再次覆盖，使同一份 workflow 可移植到任意仓库名。
        run: |
          REPO="${GITHUB_REPOSITORY##*/}"
          if [ "$REPO" = "${GITHUB_REPOSITORY%%/*}.github.io" ]; then
            BASE="/"
          else
            BASE="/${REPO}/"
          fi
          echo "部署 base = $BASE"
          sed -i "s|const base = \`/androguard-skills/\`|const base = \`${BASE}\`|" docs/.vitepress/config.ts
          grep -n "const base" docs/.vitepress/config.ts
```

- [ ] **Step 3: 验证 workflow YAML 语法合法**
Run: `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/deploy_docs.yml')); print('YAML OK')"`
Expected:
  - Exit code: 0
  - Output contains: "YAML OK"

- [ ] **Step 4: 提交**
Run: `git add .github/workflows/deploy_docs.yml && git commit -m "ci(docs): clarify base path sed portability comment"`

---

### Task 4: 启用 GitHub Pages 并触发首次部署 + 更新 README 文档站链接

**Depends on:** Task 1, Task 2, Task 3
**Files:**
- Modify: `website/README.md:57`（部署 URL 占位符替换为真实地址）
- Modify: `README.md`（根 README 新增文档站章节）
- Operations: `gh api` 创建 Pages site + push 触发 CI + 轮询 workflow 状态 + 验证 Pages URL 可访问

- [ ] **Step 1: 启用 GitHub Pages site — 用 workflow 作为构建源**

从未启用过（API 404）。用 gh 创建 Pages site，build_type=workflow 表示由 Actions 构建部署，而非从某分支直接 serve。

Run: `gh api -X POST repos/android-security-engineer/androguard-skills/pages -f build_type=workflow -f source[branch]=master`
Expected:
  - Exit code: 0
  - Output contains: `"build_type": "workflow"` and `"status"`（返回 site JSON，status 可能是 null/built）

- [ ] **Step 2: 更新 website/README.md 部署 URL — 替换占位符为真实地址**

文件: `website/README.md:50-57`（GitHub Pages 部署章节）

```markdown
`.github/workflows/deploy_docs.yml` 在 push 到 master（触及 `website/`）时自动：

1. 安装 androguard + 内省重生成命令文档。
2. 根据 `GITHUB_REPOSITORY` 动态设置 `base` 路径。
3. 构建 VitePress。
4. 部署到 GitHub Pages。

部署 URL：https://android-security-engineer.github.io/androguard-skills/
```

- [ ] **Step 3: 在根 README.md 新增文档站章节 — 让访客一眼看到文档地址**

文件: `README.md`（在 `## Documentation` 章节内追加本仓库文档站链接，紧接 ReadTheDocs 行之后插入）

```markdown
**Documentation contains outdated information - In progress of updating**

The [Github Pages Documentation](http://androguard.github.io/androguard/) is the most up to date source.

> 📖 **Androguard Skills 文档站**：本仓库自带的 VitePress 文档站已部署到
> https://android-security-engineer.github.io/androguard-skills/ ——
> 覆盖 219 个 CLI 命令、daemon 模式、19 域安全审计、代码模块参考，可只看文档站学会整个项目。

Additional documentation that contains outdated information is available at [ReadTheDocs](http://androguard.readthedocs.io/en/latest/).
```

- [ ] **Step 4: 提交 README 改动并 push 触发 CI 部署**
Run: `git add website/README.md README.md && git commit -m "docs: publish GitHub Pages URL in README" && git push origin master`
Expected:
  - Exit code: 0
  - Output contains: "master -> master"（push 成功）

- [ ] **Step 5: 确认 CI workflow 被触发并运行**
Run: `sleep 5 && gh run list --workflow=deploy_docs.yml --limit 1`
Expected:
  - Exit code: 0
  - Output contains: "deploy_docs.yml"（最新一次 run 出现，status 为 queued/in_progress/completed）

- [ ] **Step 6: 轮询等待 workflow 完成（build+deploy 双 job）**
Run: `gh run watch $(gh run list --workflow=deploy_docs.yml --limit 1 --json databaseId --jq '.[0].databaseId') --exit-status`
Expected:
  - Exit code: 0
  - Output contains: "success" 或无 failure 字样（--exit-status 在失败时返回非 0）

- [ ] **Step 7: 验证 Pages site 已部署且可访问**
Run: `curl -sI -o /dev/null -w "%{http_code}" https://android-security-engineer.github.io/androguard-skills/`
Expected:
  - Exit code: 0
  - Output contains: "200"（首次部署可能有几十秒延迟，若得 404 则 sleep 20 重试）

- [ ] **Step 8: 验证 Pages site 状态为 built**
Run: `gh api repos/android-security-engineer/androguard-skills/pages --jq '.status, .html_url'`
Expected:
  - Exit code: 0
  - Output contains: "built" and "android-security-engineer.github.io/androguard-skills"

