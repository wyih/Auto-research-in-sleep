# Business Research Suite 使用指南(学生版)

这套件把一篇商科论文(会计、金融、管理、经济)的整个流程拆成一串 skill,你在 Kimi Code(或 Codex)里用大白话驱动,它逐步带你走完:

**选题 → 查新 → 研究设计 → 拿数据 → 分析 → 审计 → 写作 → 预审 → 按意见修改**

每个阶段都有明确产出文件,你可以随时停下来检查、改方向、再让它继续。

---

## 1. 开始前准备

**必须有:**

- 一台电脑,装有 `git`:
  - **macOS / Linux**:直接打开终端用下面的命令
  - **Windows**:两条路——Codex 线有原生 PowerShell 安装器(`tools/install_aris.ps1`,用 junction 链接,不需要管理员权限);Kimi 线的安装器是 bash 脚本,请在 **WSL**(Windows 的 Linux 子系统)里运行。PowerShell 里 `git`、`cd`、`mkdir`、`ls` 命令和本文写法一致,只有安装/升级脚本要按你的线选对版本
- 一个宿主环境,二选一:
  - **Kimi Code CLI**(推荐):<https://www.kimi.com/code> 按官方指引安装
  - **Codex CLI**:<https://github.com/openai/codex> 按官方指引安装

**按你的数据来源,可能需要:**

- WRDS 账号(用美股/Compustat/CRSP 数据时)
- CSMAR / CNRDS 账号(用中国数据时,一般走学校图书馆入口)
- CNKI 可访问环境(需要中文文献全文时)
- 浏览器桥(需要从 CSMAR/CNRDS/CNKI 网页导出数据时;复用你浏览器里已登录的会话,套件不会替你登录):
  - Kimi Code 用户装 **Kimi WebBridge** 浏览器扩展
  - Codex 用户用 Codex 自带的 **Control Chrome** 插件(`chrome:control-chrome`;套件侧由 `browser-session-bridge` 自动路由过去,不用单独配置)

没有这些账号也能开始:选题、查新、研究设计、写作、预审都不需要数据账号。

---

## 2. 安装(约 5 分钟)

打开终端,逐条执行:

```bash
# 1. 克隆仓库并切到本 release
git clone https://github.com/wyih/Auto-research-in-sleep.git
cd Auto-research-in-sleep
git checkout business-research-suite-v0.5.0
```

**Kimi Code 用户:**

```bash
# 2. 给你(或学生)的论文项目建个目录,然后装进去
mkdir -p ~/my-thesis
bash tools/install_aris_kimi.sh ~/my-thesis --groups business-research --office-author "你的名字"
```

**Codex 用户:**

```bash
mkdir -p ~/my-thesis
bash tools/install_aris_codex.sh ~/my-thesis --groups business-research --office-author "你的名字"
```

**Windows 用户(PowerShell):**

```powershell
# 同上,先 git clone 并 checkout 到本 release
mkdir $HOME\my-thesis

# Codex 线(原生支持 Windows):
.\tools\install_aris.ps1 -ProjectPath $HOME\my-thesis -Platform codex -Groups business-research -OfficeAuthor "你的名字"

# Kimi 线:请改用 WSL,在 WSL 终端里跑上面的 bash 命令
```

> `--office-author` 只用于 `results-to-docx` 生成 Word 结果包时的署名,填一次即可。

**确认装好了:**

```bash
ls ~/my-thesis/.agents/skills
```

应该看到 26 个条目,其中包括 `business-research-suite`、`business-research-pipeline`、`business-prereview` 等 25 个 skill 加一个 `shared-references`。

> 注意:**一个项目只装一条线**。如果这个项目之前装过 Codex 线,先 `bash tools/install_aris_codex.sh ~/my-thesis --uninstall`,再装 Kimi 线,反之亦然。两条线的卸载互不影响。

---

## 3. 第一次用:从一句话开始

进入项目目录,启动宿主:

```bash
cd ~/my-thesis
kimi        # Kimi Code 用户;Codex 用户用 codex
```

然后直接用自然语言说你要干什么,套件会自己路由到对应 skill。比如:

- 「我是会计专硕,想做 ESG 信息披露方向的实证论文,帮我生成几个选题」
- 「帮我评估一下这个选题:供应链金融与审计费用」
- 「我的初稿在 draft.md,帮我做一次送审前预审」

想显式走完整管线,也可以直接点名:

```
/business-research-pipeline 我要做一篇 MPAcc 学位论文,方向是 ……
```

`/business-research-suite` 是轻量路由(每次只选一个阶段),`/business-research-pipeline` 是显式全流程。

---

## 4. 各阶段说明:你说什么,它产出什么

| 阶段 | 你大概这样说 | 它做的事 | 主要产出 |
|---|---|---|---|
| 选题 | 「帮我围绕 X 生成选题」 | 生成多个研究问题,给出理论路径和数据可得性评估 | 选题清单与排序 |
| 查新 | 「这个选题有人做过吗」 | 对 SSRN/NBER/期刊/工作论文找最近邻,判断增量与风险 | 查新报告 |
| 文献综述 | 「帮我梳理 X 领域的文献」 | 画文献版图、找核心对话;需要全文时走授权渠道获取并逐篇验证 | 综述 + 方法卡 |
| 研究设计 | 「帮我设计实证方案」 | 先分流方法(档案/实验/问卷/实地/案例/设计科学/规范),再做样本、变量、识别策略、模型、表壳和可行性检查 | 设计文档(案例研究会产出 `CASE_PROTOCOL.md`) |
| 拿数据 | 「帮我把数据拉下来」 | 按来源走路由:公开数据走数据源插件;WRDS 走 R/Postgres;CSMAR/CNRDS 走你浏览器登录态导出 | 数据文件 + 来源清单(`DATASOURCE_RECEIPT.json`) |
| 分析 | 「按设计跑回归」 | 用 R / Stata / Python 跑分析,脚本和输出都可复现 | 回归表、描述统计、图 |
| 结果打包 | 「把结果做成 Word」 | 生成独立学术风格 Word 结果包 | `results.docx` |
| 审计 | 「核一遍数字和引用」 | 逐项核对文稿数字 vs 分析输出、来源 vs 主张;裁定每个结论的证据上限 | 审计报告 |
| 写作 | 「按设计写初稿」 | 基于证据和(可选的)目标期刊/作者风格约束写作 | 论文初稿 |
| **预审** | 「帮我预审这篇初稿」/「这篇要投《XX》,帮我审一遍」 | 学位论文:按 MPAcc/硕士评审标准打分、写委员会式评语、给送审结论;期刊稿件:写审稿人报告(主要/次要意见)+ 目标期刊适配判断 | `THESIS_PREREVIEW.md` / `JOURNAL_PREREVIEW.md` |
| 修改 | 按预审的 P0/P1/P2 逐条改 | 每条修改路由回负责的 skill(数据问题回分析、主张越界回审计……) | 修改后的稿子 |
| 回复审稿 | 「帮我回复这些审稿意见」 | 解析意见、规划修订、写回复信 | 回复信 + 修订稿 |

全程有一本"护照"(`BUSINESS_RUN_PASSPORT.md`)记录项目材料、数据权限、阶段进度和验收门状态;AI 的工作分支和你确认过的决定分开记录,换电脑、换会话都能接上。

---

## 5. 数据从哪来(三条路)

1. **公开数据(最简单)**:Kimi Code 下直接用官方数据源插件——Wind、S&P、SEC EDGAR、Yahoo Finance、国家统计局、FRED/IMF/世界银行、天眼查、国标法规、arXiv/Scholar、新华财经/财新。宏观、公告、标准、文献类需求优先走这里。
2. **WRDS**:有账号就配置好 R + Postgres,套件负责抽取、缓存、链接表和来源清单;大任务超时了会自动交接 SAS Cloud 路径。
3. **CSMAR / CNRDS / CNKI 门户**:需要你自己在浏览器里登录(套件不碰你的账号密码)。Kimi Code 用户装 Kimi WebBridge 扩展、Codex 用户启用 Codex 自带的 Control Chrome 插件;套件借用你已登录的会话做检索和导出,下载文件会逐一校验。

---

## 6. 写完初稿:预审闭环

初稿完成后,说「帮我预审这篇论文」。两种稿件两种口径:

**学位论文(答辩/送审前):**

1. 它先读你的初稿和过程材料,按 MPAcc 评审标准(非 MPAcc 用通用硕士标准)逐维度打分,明确标出哪些地方证据不足;
2. 输出 `THESIS_PREREVIEW.md`:委员会式评语(证据 → 判断 → 修改动作)+ 送审结论(可送审 / 大修后送审 / 暂不建议送审);
3. 评语里每条问题都带 P0(必须改)/ P1(应该改)/ P2(可选)优先级,并指明该回哪个 skill 去修。

**期刊稿件(投稿前自查):**

1. 说「这篇要投《XX期刊》,帮我按审稿人标准审一遍」——它会以审稿人口径写 `JOURNAL_PREREVIEW.md`:一段论文摘要、逐条主要意见(问题 → 为什么威胁结论 → 需要什么证据或分析才能解决)、次要意见;
2. 增量贡献不和作者自己说的一致,而是对着查新报告核;
3. 给出投稿建议(可投 / 小修后投 / 大修后投 / 暂不适合该刊),并附期刊适配判断:这篇是否进入目标刊近三五年的对话,不合适的话哪一两个刊物更合适;
4. 修改项同样按 P0/P1/P2 路由回对应 skill。

**修改后复审(两种稿件通用):** 改完说「重新预审」,它会先重跑数字审计和来源审计,再重新评分——P0 没清完,这个循环不关闭。

---

## 7. 以后怎么升级

```bash
cd Auto-research-in-sleep
bash tools/smart_update_kimi.sh --apply --project ~/my-thesis
```

(不加 `--apply` 只看计划不动手。)它会拉取最新 release tag、移动本地仓库、并把新增/移除的 skill 同步进你的项目。Codex 线的受管安装升级用 `git pull` + `install_aris_codex.sh --reconcile`;copy 安装用 `smart_update_codex.sh`。

**Windows 对照:** Codex 线在 PowerShell 里用 `.\tools\smart_update.ps1 -ProjectPath $HOME\my-thesis -TargetSubdir '.agents/skills' -Apply`;Kimi 线在 WSL 里跑上面的 bash 命令。

## 8. 卸载

```bash
bash tools/install_aris_kimi.sh ~/my-thesis --uninstall
```

只删它自己 manifest 里管理的条目,不会碰你自己建的任何文件。

---

## 9. 常见问题

- **安装器报 CONFLICT、什么都不写** → 这个项目已被另一条线管理,先卸载那条线(见第 2 节末尾)。
- **提示要 `--office-author`** → 你选了 `results-to-docx`,补上 `--office-author "你的名字"` 即可。
- **数据下载失败/校验不过** → 先确认你在浏览器里已登录对应平台,且浏览器桥已启用(Kimi 的 WebBridge 扩展 / Codex 的 Control Chrome 插件);仍不行就把报错原样发给宿主,它会按下载验证流程排查。
- **想知道审稿意见可信吗** → 审阅类 skill 默认是同族模型互审,结果诚实标注 `same-family / provisional`;需要跨族复审时,按 `docs/KIMI_ADAPTATION.md` 注册 `mcp-servers/llm-chat`。
