# 贡献指南（Contributing）

感谢你愿意为 **AndroGuard Skills** 做贡献。本指南帮助你搭建开发环境、运行测试并提交变更。

## 开发环境

```bash
# 克隆并安装（含 dev 依赖：pytest / black / isort）
pip install poetry
poetry install          # 自动安装 dev 依赖

# 或使用 venv + pip（如无法用 poetry）
python3 -m venv .buildenv
.buildenv/bin/pip install -e . pytest pytest-asyncio black isort
```

## 测试

```bash
# 运行全量测试（约 15-17 分钟，含 daemon 内存/并发等慢测试）
poetry run pytest tests/ -q

# 快速验证核心（CLI / agent 协议 / API 覆盖 / 文档一致性）
poetry run pytest tests/test_cli_smoke.py tests/test_agent_protocol.py \
  tests/test_docs_consistency.py tests/test_api_coverage_matrix.py -q
```

> ⚠️ daemon 类测试（`test_daemon_*`）启动真实进程监听 `127.0.0.1:8899`。
> 若失败并提示 "address already in use"，先清理残留 daemon 进程：
> `ss -ltnp | grep 8899` 找到 PID 后 `kill` 即可，再重跑。

## 代码风格（CI 会强制）

项目统一用 **black + isort**（配置见 `pyproject.toml`，line-length 79）：

```bash
poetry run black androguard/
poetry run isort androguard/
```

提交前请确保：
```bash
poetry run black --check androguard/ && poetry run isort --check-only androguard/
```

## 提交规范

- 用清晰的命令式标题，例如 `feat(agent): 支持 xxx` / `fix(daemon): 修复 xxx` / `docs: 补充 xxx`。
- 若修复了回归，请附上对应测试。
- 新增功能请同步更新文档站（`website/`）与 `CHANGELOG.md`。

## 分支与 PR

- 主要开发分支为 `master`。`push` 到 `master` 或发 PR 会触发 CI（Linux 多 Python 版本 + Mac ARM）。
- 打 `v*` tag 会触发自动发布（构建 → 测试 → 创建 GitHub Release）。详见 `RELEASING.md`。

## 行为准则

保持友善与建设性。任何关于安全漏洞的报告请走 `SECURITY.md` 中的私密渠道，不要发公开 Issue。
