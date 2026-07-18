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
