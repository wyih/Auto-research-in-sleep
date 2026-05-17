# ARIS Business Codex Skills 安装与使用指南

这套 skill 面向商科、会计、金融、管理、经济学论文工作流。它只安装 business 相关 skill 和必要依赖文件，保留 R/Stata 分析、论文写作、数字审计、source-claim 审计；ML/GPU 论文流水线不会安装到你的商科项目里。

## 1. 准备 ARIS 分支

在保存 ARIS business skills 的工作树里保持这个分支最新：

```bash
cd /Users/wyih/Projects/ARIS-business-skills
git fetch origin
git switch codex/business-research-skills
git pull --ff-only
```

日常安装时不需要每次切到目标论文项目的分支。关键是 `--aris-repo` 指向这个已经在 `codex/business-research-skills` 分支上的 ARIS 工作树。

## 2. 安装到论文项目

把 `/path/to/paper-project` 换成你的论文项目目录：

```bash
bash /Users/wyih/Projects/ARIS-business-skills/tools/install_business_codex_skills.sh \
  /path/to/paper-project \
  --aris-repo /Users/wyih/Projects/ARIS-business-skills
```

安装器会创建：

```text
/path/to/paper-project/.agents/skills/<skill-name> -> /Users/wyih/Projects/ARIS-business-skills/skills/skills-codex/<skill-name>
/path/to/paper-project/.aris/installed-business-skills-codex.txt
/path/to/paper-project/AGENTS.md 里的 ARIS Business Codex 管理块
```

## 3. 安装内容

安装器会安装 18 个条目：

```text
business-research-suite
business-lit-review
business-idea-creator
business-novelty-check
business-run-passport
empirical-design-plan
data-analysis-bridge
r-analysis-bridge
stata-analysis-bridge
evidence-to-claim
business-number-audit
business-claim-source-audit
business-paper-plan
business-author-style-profile
business-paper-writing
business-rebuttal
business-research-pipeline
shared-references
```

`shared-references` 是依赖文件目录，包含 handoff schemas、mode registry、run passport、repro lock、style calibration、claim-source audit 等共享协议。

## 4. 验证安装

```bash
ls /path/to/paper-project/.agents/skills
cat /path/to/paper-project/.aris/installed-business-skills-codex.txt
```

你应该能看到 `business-research-suite`、`r-analysis-bridge`、`stata-analysis-bridge`、`business-number-audit`、`business-claim-source-audit` 等条目。

## 5. 更新、重装、卸载

更新本地 ARIS 分支后，在论文项目上 reconcile：

```bash
cd /Users/wyih/Projects/ARIS-business-skills
git pull --ff-only

bash /Users/wyih/Projects/ARIS-business-skills/tools/install_business_codex_skills.sh \
  /path/to/paper-project \
  --reconcile \
  --aris-repo /Users/wyih/Projects/ARIS-business-skills
```

卸载 business-only skill 链接：

```bash
bash /Users/wyih/Projects/ARIS-business-skills/tools/install_business_codex_skills.sh \
  /path/to/paper-project \
  --uninstall
```

卸载只移除 manifest 记录的 business-only symlink，保留你项目里的本地文件。

## 6. 日常使用方式

在 Codex 里打开目标论文项目目录后，优先从总入口开始：

```text
/business-research-suite "我想做一篇关于 AI disclosure 和 analyst forecast 的会计论文，现在只有大概方向"
```

`business-research-suite` 默认是轻 router：只判断当前阶段，加载一个 focused skill。完整 pipeline 需要明确写 `full pipeline`、`end-to-end`、`all stages`。

常用入口：

| 场景 | 调用 |
|---|---|
| 只有大方向 | `/business-research-suite "topic"` |
| 文献和定位 | `/business-lit-review "topic"` |
| 生成研究问题 | `/business-idea-creator "direction"` |
| 查 novelty | `/business-novelty-check "idea"` |
| 设计实证方案 | `/empirical-design-plan "idea"` |
| R 跑回归 | `/r-analysis-bridge "plan or data"` |
| Stata 跑回归 | `/stata-analysis-bridge "plan or do files"` |
| 判断结果能支持什么 claim | `/evidence-to-claim "results"` |
| 查论文里的数字是否对得上表 | `/business-number-audit "paper"` |
| 查文字 claim 和引用是否有来源支持 | `/business-claim-source-audit "paper"` |
| 写 paper outline | `/business-paper-plan "context"` |
| 按你的写作风格校准 | `/business-author-style-profile "samples"` |
| 写正文 | `/business-paper-writing "plan"` |
| 回复审稿意见 | `/business-rebuttal "reviews"` |
| 明确要全流程 | `/business-research-pipeline "full pipeline: topic"` |

## 7. 推荐项目顺序

早期保持开放：

```text
/business-research-suite "我想做 ESG disclosure 和 debt contracting 的研究，先帮我收敛问题"
/business-lit-review "ESG disclosure debt contracting accounting"
/business-idea-creator "基于上面的 literature map 生成 5 个可执行 idea"
```

中期固定设计：

```text
/business-novelty-check "选中的 idea"
/empirical-design-plan "选中的 idea + 可用数据"
```

分析阶段按后端走：

```text
/r-analysis-bridge "根据 empirical-design/RESEARCH_DESIGN.md 和 TABLE_SHELLS.md 跑主回归"
```

或：

```text
/stata-analysis-bridge "根据 do/ 和 data/final/*.dta 生成主表和 logs"
```

写作前做 claim gate：

```text
/evidence-to-claim "analysis/output/RESULTS_SUMMARY.md"
/business-number-audit "paper/"
/business-claim-source-audit "paper/"
```

写作阶段：

```text
/business-paper-plan "CLAIMS_FROM_EVIDENCE.md + BUSINESS_LIT_REVIEW.md"
/business-author-style-profile "我的旧论文样本 + 目标期刊文章"
/business-paper-writing "BUSINESS_PAPER_PLAN.md"
```

## 8. Toy 项目

公开数据 R 示例在：

```text
examples/r-ff-industry-toy/
```

它展示了从 business lit review、idea、design、R 分析、claims、number audit、source-claim audit 到最终结果的完整商科链路。最终结果看：

```text
examples/r-ff-industry-toy/FINAL_ANALYSIS_RESULTS.md
examples/r-ff-industry-toy/BUSINESS_RUN_PASSPORT.md
examples/r-ff-industry-toy/SOURCE_CLAIM_AUDIT.md
```

## 9. 常见问题

### 安装器提示 full Codex install manifest exists

目标项目已经装过完整 Codex skill 套件。建议换一个干净项目目录，或先卸载完整套件后再装 business-only 套件。

### 修改 ARIS 分支后项目里 skill 没更新

项目里装的是 symlink，通常会随 ARIS 工作树更新。如果新增或删除了 skill 条目，跑一次 `--reconcile`。

### 想让它一次跑完整论文流程

明确写 full pipeline：

```text
/business-research-pipeline "full pipeline: topic ..."
```

默认局部调用会只处理当前阶段，避免过早加载太多 checklist 限制模型发挥。

## 建议

日常用 `business-research-suite` 起步；有明确阶段时直接调用对应 skill；投稿前固定跑 `business-number-audit` 和 `business-claim-source-audit`。
