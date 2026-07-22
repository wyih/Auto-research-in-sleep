# `skills-codex` 说明

这是主线 `skills/` 的 Codex 原生镜像 / 适配层，不是独立主线产品。

## 当前范围

- 基座覆盖：主线 `skills/` 的 `104` 个 skill 全量同步
- 支持目录：`shared-references/`，与主线 `39/39` 名称完整对齐
- 24 个商科实证 skill 由 `tools/sync_business_portable_mirror.py` 从运行时中立的 canonical source 机械同步；Codex 与 Grok 都从 `.agents/skills` 消费同一份内容，浏览器桥在运行时选择适配器。
- reviewer-heavy skill 的默认 reviewer 契约：
  - 首轮：`spawn_agent`
  - 续接：`send_input`
  - 推理强度：`xhigh`
  - 基础 Codex 自审：`review_independence: same-family`、
    `acceptance_status: provisional`
  - Claude/Gemini overlay 或确定性验证：`acceptance_status: accepted`
- 可选 overlay：
  - `skills-codex-claude-review`
  - `skills-codex-gemini-review`

## 推荐安装方式

Codex 默认推荐项目级安装；Grok Build 也会从同一个 `.agents/skills` 项目目录发现这些 skill：

```bash
git clone https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep.git ~/aris_repo
cd ~/your-project

bash ~/aris_repo/tools/install_aris_codex.sh . --office-author "你的姓名"
```

如果是隔离的 Codex/Grok 烟测工作区，不希望更新可选的全局 helper 指针或 AGENTS 管理块：

```bash
bash ~/aris_repo/tools/install_aris_codex.sh . \
  --groups business-research --quiet --office-author "你的姓名" \
  --no-doc --no-global-pointer
grok inspect --json
```

安装后会形成扁平布局：

```text
.agents/skills/<skill-name> -> ~/aris_repo/skills/skills-codex/<skill-name>
.aris/installed-skills-codex.txt
AGENTS.md   # 自动写入 Codex 管理块
```

上游更新后收敛：

```bash
cd ~/aris_repo && git pull
bash ~/aris_repo/tools/install_aris_codex.sh ~/your-project --reconcile \
  --office-author "你的姓名"
```

只卸载受管的 Codex skill：

```bash
bash ~/aris_repo/tools/install_aris_codex.sh ~/your-project --uninstall
```

## 跨机器与团队安装

先发布或选定一个不可变的 release tag，然后每台机器都克隆这个固定版本。
应安装整个 `business-research` 分组，而不是只复制总 Pipeline；该分组是精确的
24 个便携 Skill 加共享契约。

四种运行环境需要分别处理：

| 运行环境 | 安装器 | 仓库和项目应放在 | 受管链接 | 受保护浏览器路径 |
| --- | --- | --- | --- | --- |
| macOS | Bash | macOS 文件系统 | symlink | macOS 原生 Chrome |
| 原生 Linux | Bash | Linux 文件系统 | symlink | Linux 原生 Chrome |
| 原生 Windows | PowerShell | NTFS Windows 路径 | junction | Windows 原生 Chrome |
| WSL 2 | WSL 内的 Bash | WSL Linux 文件系统，优先 `~/...` | symlink | WSLg 内的 Linux Chrome |

macOS 或原生 Linux：

```bash
git clone --branch <release-tag> <repository-url> ~/aris_repo
bash ~/aris_repo/tools/install_aris_codex.sh /absolute/path/to/project \
  --groups business-research --quiet --office-author "你的姓名"
```

Windows PowerShell 5.1 或 PowerShell 7：

```powershell
git clone --branch <release-tag> <repository-url> "$HOME\aris_repo"
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File "$HOME\aris_repo\tools\install_aris.ps1" `
  "C:\absolute\path\to\project" `
  -Platform codex `
  -ArisRepo "$HOME\aris_repo" `
  -Groups business-research `
  -OfficeAuthor "你的姓名" `
  -Quiet
```

WSL 2（所有命令都必须在同一个 WSL distribution 内运行）：

```bash
git clone --branch <release-tag> <repository-url> ~/aris_repo
bash ~/aris_repo/tools/install_aris_codex.sh ~/your-project \
  --groups business-research --quiet --office-author "你的姓名"
```

WSL 应使用 Linux 版 Node.js 和 Codex/Grok，并在该 distribution 内安装
Linux Chrome，通过 WSLg 显示。它的专用 Profile 和 `~/Downloads` 与 Windows
Chrome 完全分开。不建议把仓库放到 `/mnt/c`，因为链接、权限和文件监听语义
不同。本版本不把“WSL 内的 facade 驱动 Windows 宿主 Chrome”列为验收通过的
路径；如果必须复用 Windows Chrome/登录态，应改用原生 Windows PowerShell
安装方式运行。

原生 Windows 安装器创建 junction；macOS、原生 Linux 和 WSL 安装器创建
symlink。所有受支持布局最终都把同一份包暴露到 `.agents/skills`，供 Codex 与
Grok Build 发现。不要把已经安装好的 `.agents/skills` 直接复制到另一台机器，
因为链接仍指向原机器路径。应把 release 克隆或解压到稳定目录，再运行对应
安装器。

浏览器 Profile、cookie、保存的账号密码、WRDS 凭证、授权论文和商业数据库
数据都不进入发行包。每个使用者必须在自己的机器上建立授权 Profile 并登录。
如果缺少兼容的浏览器运行时，本地资料、模型原生 web search、开放来源、设计、
分析和写作仍可使用；受保护获取会明确报告 adapter/access gap。

全文验真和 `method-harvest` 还要求 Poppler 的 `pdfinfo`、`pdftotext` 已加入
`PATH`。macOS 用 Homebrew 安装 `poppler`；Debian/Ubuntu 和 WSL 用发行版包
管理器安装 `poppler-utils`。原生 Windows 应安装可信的 Windows Poppler 发行版
（或 `conda-forge` 的 `poppler` 包），并把它的 `Library\bin`/二进制目录加入
`PATH`。运行 PDF 流程前验证：

```text
pdfinfo -v
pdftotext -v
```

Skill 安装器只管理项目链接，不会替用户安装需要系统权限的 OS 软件包。

## Office 作者身份

分发包不会把维护者姓名作为 Word 作者。安装选择中只要包含
`results-to-docx`，就必须显式传入 `--office-author "你的姓名"`；PowerShell
对应 `-OfficeAuthor "你的姓名"`。安装器把它写入用户本机的
`~/.aris/office-author`（Windows 下位于用户 Profile），不会写进项目或 Git
配置；POSIX 安装器会把文件权限设为 `0600`。

单个产物可用 `--author "另一位作者"` 覆盖安装默认值。若只想临时覆盖当前
shell，可设置：

```bash
# macOS、Linux 和 WSL
export ARIS_OFFICE_AUTHOR="你的姓名"
```

```powershell
# 原生 Windows PowerShell
$env:ARIS_OFFICE_AUTHOR = "你的姓名"
```

解析顺序是产物级 `--author`、`ARIS_OFFICE_AUTHOR`、安装器生成的用户配置。
三者都不存在时生成器会安全停止；它不会继承安装者、维护者、操作系统账号、
Git 身份或模板作者。

## Overlay 安装

先装基座，再选装 overlay：

```bash
bash ~/aris_repo/tools/install_aris_codex.sh ~/your-project --reconcile \
  --with-claude-review-overlay --office-author "你的姓名"
```

```bash
bash ~/aris_repo/tools/install_aris_codex.sh ~/your-project --reconcile \
  --with-gemini-review-overlay --office-author "你的姓名"
```

overlay 只替换 reviewer 路由，不替换基座 mirror，也不改变 executor 语义。

## Copy 安装与更新

如果你明确想用 copy 安装，而不是受管 symlink：

```bash
mkdir -p ~/.codex/skills
cp -a ~/aris_repo/skills/skills-codex/. ~/.codex/skills/
```

更新 copy 安装请使用：

```bash
bash ~/aris_repo/tools/smart_update_codex.sh
bash ~/aris_repo/tools/smart_update_codex.sh --apply
```

项目级 copy 安装则使用：

```bash
bash ~/aris_repo/tools/smart_update_codex.sh --project ~/your-project
bash ~/aris_repo/tools/smart_update_codex.sh --project ~/your-project --apply
```

`smart_update_codex.sh` 会拒绝更新由 `install_aris_codex.sh` 管理的 symlink 安装，并提示改用 `install_aris_codex.sh --reconcile`。

## 不允许降级的 Skill

以下 4 个 skill 不允许静默降级：

- `comm-lit-review`
- `research-lit`
- `paper-poster-html`
- `pixel-art`

如果缺少所需能力，必须明确提示用户去配置，不允许自动改成简化路径继续跑。
