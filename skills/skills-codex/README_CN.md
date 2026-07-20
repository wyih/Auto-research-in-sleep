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

bash ~/aris_repo/tools/install_aris_codex.sh .
```

如果是隔离的 Codex/Grok 烟测工作区，不希望更新可选的全局 helper 指针或 AGENTS 管理块：

```bash
bash ~/aris_repo/tools/install_aris_codex.sh . \
  --groups business-research --quiet --no-doc --no-global-pointer
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
bash ~/aris_repo/tools/install_aris_codex.sh ~/your-project --reconcile
```

只卸载受管的 Codex skill：

```bash
bash ~/aris_repo/tools/install_aris_codex.sh ~/your-project --uninstall
```

## 跨机器与团队安装

先发布或选定一个不可变的 release tag，然后每台机器都克隆这个固定版本。
应安装整个 `business-research` 分组，而不是只复制总 Pipeline；该分组是精确的
24 个便携 Skill 加共享契约。

macOS 或 Linux：

```bash
git clone --branch <release-tag> <repository-url> ~/aris_repo
bash ~/aris_repo/tools/install_aris_codex.sh /absolute/path/to/project \
  --groups business-research --quiet
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
  -Quiet
```

Windows 安装器创建 junction，macOS/Linux 安装器创建 symlink；两者最终都把
同一份包暴露到 `.agents/skills`，供 Codex 与 Grok Build 发现。不要把已经安装
好的 `.agents/skills` 直接复制到另一台机器，因为链接仍指向原机器路径。应把
release 克隆或解压到稳定目录，再运行对应安装器。

浏览器 Profile、cookie、保存的账号密码、WRDS 凭证、授权论文和商业数据库
数据都不进入发行包。每个使用者必须在自己的机器上建立授权 Profile 并登录。
如果缺少兼容的浏览器运行时，本地资料、模型原生 web search、开放来源、设计、
分析和写作仍可使用；受保护获取会明确报告 adapter/access gap。

## Overlay 安装

先装基座，再选装 overlay：

```bash
bash ~/aris_repo/tools/install_aris_codex.sh ~/your-project --reconcile --with-claude-review-overlay
```

```bash
bash ~/aris_repo/tools/install_aris_codex.sh ~/your-project --reconcile --with-gemini-review-overlay
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
