![banner](https://raw.githubusercontent.com/androguard/androguard/master/assets/web/androguardwithname.jpg)

# Androguard

[![PyPI Upload](https://github.com/androguard/androguard/actions/workflows/pythonpublish.yml/badge.svg)](https://github.com/androguard/androguard/actions/workflows/pythonpublish.yml)
![PyPI - Version](https://img.shields.io/pypi/v/androguard)
![Static Badge](https://img.shields.io/badge/Documentation-InProgress-red)

Do you think your phone has been pwned ? please check [IsMyPhonePwned](https://github.com/IsMyPhonePwned)

New tool: Goauld [Dynamic injection tool for Linux/Android ](https://github.com/androguard/goauld)

See the new version of Androguard: https://github.com/androguard/androguard/tree/ng

## Installation

本项目在 GitHub Release 上发布（`.whl` 包），通过 `pip` 即可安装，依赖会自动拉取。

### 方式一：从 GitHub Release 安装（推荐）

```bash
pip install "androguard @ https://github.com/android-security-engineer/androguard-skills/releases/download/v4.2.0/androguard-4.2.0-py3-none-any.whl"
```

### 方式二：从 git 仓库 + 指定版本 tag 安装

```bash
pip install "git+https://github.com/android-security-engineer/androguard-skills.git@v4.2.0"
```

> 最新开发版可用 `pip install "androguard @ git+https://github.com/android-security-engineer/androguard-skills"`。

### 验证是否装好

```bash
# 三个命令入口都应可用
androguard --version
androguard-skills --help
androguard-mcp --help
```

### 给 AI Agent 用（MCP 接入）

装好后自带 `androguard-mcp` 命令，可直接在 Claude Desktop / Claude Code 的 MCP 配置中注册：

```json
{
  "mcpServers": {
    "androguard": { "command": "androguard-mcp" }
  }
}
```

完整接入与命令说明见下节文档站。

> [!IMPORTANT]
> 本仓库是经过定制的 **AndroGuard Skills** 增强版（新增 MCP / skills 命令系统 / daemon 模式）。它 `from` 上游 androguard 演进而来，但安装命令**不要**照搬上游的 `pip install androguard`（那会装到上游原版，不含本仓库的 AI Agent 能力）。请使用本节的 GitHub 安装命令。

## Documentation
**Documentation contains outdated information - In progress of updating**

The [Github Pages Documentation](http://androguard.github.io/androguard/) is the most up to date source.

> 📖 **Androguard Skills 文档站**：本仓库自带的 VitePress 文档站已部署到
> https://android-security-engineer.github.io/androguard-skills/ ——
> 覆盖 219 个 CLI 命令、daemon 模式、19 域安全审计、代码模块参考，可只看文档站学会整个项目。

Additional documentation that contains outdated information is available at [ReadTheDocs](http://androguard.readthedocs.io/en/latest/).


## Features

Androguard is a full python tool to play with Android files.

* DEX, ODEX
* APK
* Android's binary xml
* Android resources
* Disassemble DEX/ODEX bytecodes
* Basic Decompiler for DEX/ODEX files
* Frida support for easy dynamic analysis
* SQLite database to save the session

## Authors: Androguard Team

Androguard + tools: Anthony Desnos (desnos at t0t0.fr).

DAD (DAD is A Decompiler): Geoffroy Gueguen (geoffroy dot gueguen at gmail dot com)

## Projects using Androguard
In alphabetical order

* [AndroPyTool](https://github.com/alexMyG/AndroPyTool)
* [AppKnox](http://appknox.com)
* [Cuckoo Sandbox](https://cuckoosandbox.org)
* [Deckard](https://github.com/hrkfdn/deckard)
* [Droidbot](https://github.com/honeynet/droidbot)
* [Droidstatx](https://github.com/integrity-sa/droidstatx)
* [εxodus](https://github.com/Exodus-Privacy/exodus)
* [F-Droid Server](https://gitlab.com/fdroid/fdroidserver)
* [gplaycli](https://github.com/matlink/gplaycli)
* [Koodous](https://koodous.com)
* [MobSF](https://github.com/MobSF/Mobile-Security-Framework-MobSF)
* [qiew](https://github.com/mtivadar/qiew)
* [Quark-Engine](https://github.com/quark-engine/quark-engine)
* [Virustotal](https://virustotal.readme.io/reference/androguard)
* [Viper Framework](https://github.com/viper-framework/viper)
* ... and many more!

You are using Androguard and are not listed here? Just create a [ticket](https://github.com/androguard/androguard/issues) or send us a [pull request](https://github.com/androguard/androguard/pulls) with your project!

## Licenses

### Androguard

Copyright (C) 2012 - 2024, Anthony Desnos (desnos at t0t0.fr)
All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS-IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

### DAD

Copyright (C) 2012 - 2016, Geoffroy Gueguen (geoffroy dot gueguen at gmail dot com)
All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS-IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
