# 发布指南（Release Guide）

本项目采用 **GitHub Release + 可选 PyPI** 双轨发布。流程尽量自动化。

## 一、常规发版（打 tag 自动发布）

整个流程通过 `.github/workflows/pythonpublish.yml` 自动化：**只要推一个 `v*` 格式的 tag，CI 就会自动** 跑全量测试 → 构建 wheel+sdist → 创建 GitHub Release 并上传包。

1. **更新版本号**（3 处保持一致）：
   - `androguard/__init__.py` → `__version__ = "X.Y.Z"`
   - `pyproject.toml` → `version = "X.Y.Z"`
   - `setup.py` 从 `__init__` 自动读取，无需改
2. **更新 `CHANGELOG.md`**，把新版本写到顶部。
3. **提交并打 tag**：
   ```bash
   git add -A
   git commit -m "release: vX.Y.Z"
   git tag vX.Y.Z
   git push origin master
   git push origin vX.Y.Z
   ```
4. 在 GitHub 的 **Actions** 页查看 `Publish Release` 工作流自动运行；成功后 **Releases** 页会有对应版本。
5. （可选）本地手动构建验证：
   ```bash
   python3 -m venv .buildenv
   .buildenv/bin/pip install build
   .buildenv/bin/python -m build --outdir dist
   ```
   > ⚠️ 不要用 `python setup.py sdist`：本项目是 Poetry 结构（`[tool.poetry]` 无 `[project]` 段），setuptools 会报错，必须走 PEP 517 的 `python -m build`（poetry-core 后端）。

## 二、发到 PyPI（可选）

### 名字冲突说明
上游 androguard 已占用 PyPI 上的 `androguard` 名。若要发 PyPI，应使用 **`androguard-skills`** 作为发行名。这**不影响** `import androguard`（导入名由包目录决定，与发行名无关），只影响 `pip install` 时写的名字。

### 配置 token（一次性）
在 GitHub 仓库 **Settings → Secrets and variables → Actions** 添加：
- `PYPI_API_TOKEN`：在 [PyPI](https://pypi.org/manage/account/token/) 创建的 API token（用于 `twine upload`）。

配好后，下一次打 `v*` tag 时，`pythonpublish.yml` 会自动执行 `twine upload`。

### 手动发布（不依赖 CI）
```bash
python3 -m venv .buildenv
.buildenv/bin/pip install build twine
.buildenv/bin/python -m build --outdir dist
.buildenv/bin/twine upload dist/*
```

## 三、发版前自检清单

- [ ] 全量测试通过：`pytest tests/ -q`
- [ ] 代码格式：`black --check androguard/`、`isort --check-only androguard/`
- [ ] `CHANGELOG.md` 已更新
- [ ] 3 处版本号一致
- [ ] 构建产物齐全（`.whl` + `.tar.gz`）
