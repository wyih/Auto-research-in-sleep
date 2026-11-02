# Business Research Suite 外部来源更新核对

核对日期：2026-11-02。ARIS 与上次同步的 `5854b99` 比较；其他来源与 Suite 已记录的吸收版本或对应目录比较。下表同时区分技能源、转引来源和软件参考。

| 仓库 | 本次核对的版本 | 新增或变化 | 对 Suite 的处理 |
| --- | --- | --- | --- |
| [ARIS](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/tree/c485faa) | `c485faa`，2026-11-01 | 28 个提交；Keenable、Firecrawl 搜索；可选写作模型 worker；模型/API 兼容；Goal Pulse 接入说明 | 同步 Fork main 与商科分支；Keenable 作公共检索备选；外部写作仅在用户或项目明确选定时使用；Goal Pulse 限真实 Goal 生命周期 |
| [Barrios skills](https://github.com/Barrios88/barrios-skills/tree/680c98370381593141bf1d39da4353354958e2f0) | `680c983`，2026-10-13 | 对比 `d50afc6` 新增本地 PDF 解析、增强证据式预审、修正 WRDS 表名拼写、撤下私有文献检索 | 吸收可比量核对、确认性纠错、表格空值及图片核验规则；复用已有 PDF 工具；保留既有文献检索选择 |
| [AI research feedback](https://github.com/claesbackman/AI-research-feedback/tree/4c1aef514cf4aa520937131a54830b4af0e403db) | `4c1aef5`，2026-10-28 | 新增 explorable 网页、Beamer 和 PPTX 报告；已吸收的 `audit-analysis`、`explain-diff` 目录未变 | 给 `business-research-talk` 增加按需读取的逐步展开指导，保持用户指定格式与已有风格 |
| [Reference matcher](https://github.com/mimaowang/econ-reference-matcher/tree/7fd344d7586a4ca6bebaa8bff8367f318d000935) | `7fd344d`，2026-10-21 | 相对 `84678b0` 仅 `.github/workflows/ci.yml` 改变 | 更新核对记录，保留现有 `reference_match` 流程 |
| [Lu Han writing](https://github.com/hanlulong/econ-writing-skill/tree/f2bf7a22c5e3b37921a5e6c73bd1fb380a5e00e8) | `f2bf7a2`，2026-07-19 | 最近提交早于 Suite 的来源吸收日期 | 保留现有可选写作框架 |
| [Lu Han slides](https://github.com/hanlulong/econ-slides-skill/tree/4ac998bfa98bc0b59d4d1776b4ced565b34b802c) | `4ac998b`，2026-07-19 | 最近提交早于 Suite 的来源吸收日期 | 保留现有研究报告与讲稿规则 |
| [HERO](https://github.com/wanshuiyin/HERO-Anti-OverDefense/tree/92686ca5c7dc9f4852cd323e2852219b7e86a8ea) | `92686ca`，2026-11-01 | ARIS 新接入的 Goal Pulse；写作、范围与执行指导 | 核对外部依赖；普通同步任务不创建 Goal 或提醒服务 |
| [Reviewer](https://github.com/Ingar30/reviewer/tree/e6ae89dbab1aa642392d813caebcce197844edff) | `e6ae89d`，2026-10-23 | Barrios 更新后署名的证据审阅来源；本地预处理、质量检查、结构化审阅 | 核对来源；采用经改写的证据原则，继续现有预审入口 |
| [HonestDiD](https://github.com/asheshrambachan/HonestDiD/tree/6813f02ed38f0b63bdca6915604b2eac90491303) | `6813f02`，2026-04-11 | 本轮未见吸收日期之后的新提交 | 保留计量参考，由具体研究项目管理 R 依赖 |

## 实质变化

预审现在更明确地核对主张与具体表格、样本、时期、分母和设定，区分已确认的内部错误、改变结论范围的限定与可选改进。两个比例或均值在口径对齐后再比较；缺失披露不会被写成已证实的代码错误。

PDF 阅读补充了空单元格、提取结果冲突和原页核对规则。现有 `method-harvest` 已提供本地验真、页面保留提取、OCR 判断、图片核验和版本定位，因此复用该路径。

报告新增可选的 explorable 指导：逐步显示机制或比较，使用一致的数据、坐标与样本，为编辑版及静态讲义保留完整论证。它不改变常规研讨会报告的默认风格。

Barrios 修正的 WRDS 拼写是 `ccmxpf_linkhist` → `ccmxpf_lnkhist`；Suite 的既有链接指导使用 `ccmxpf_linktable`，没有该拼写错误，本次保留原有日期有效链接实现。

Kimi 包继续使用其宿主支持的原生 reviewer 契约。外部 API 示例中的具体模型名及 writing-worker 的独立参数按服务契约保留，避免被转换成原生 Kimi 的占位参数。

来源与署名随 [business-source-attribution.md](../skills/shared-references/business-source-attribution.md) 分发。

## 验证

- ARIS 合并及 Kimi 适配后的完整测试：1,339 项通过，51 项依环境跳过，114 项子测试通过。
- 外部模型 API 示例保留的 Kimi 回归检查：13 项通过。
- 外部来源适配后，商科打包、Codex/Kimi 镜像、写作约束与文献综合检查：63 项通过。
- 更新涉及的主线及生成包中，78 个本地 Markdown 引用均可解析；写作与报告入口格式检查通过。
- 项目与用户级 Keenable 安装链接已核验；一次限定 GitHub 域、最多一条结果的公共检索成功返回 Barrios 仓库。
