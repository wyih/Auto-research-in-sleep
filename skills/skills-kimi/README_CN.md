# `skills-kimi`

ARIS skill 集合的 Kimi Code CLI 原生包 —— 第三条发行线，与
`skills/skills-codex/` 平级。完整说明见 [README.md](README.md)。

- 覆盖 `skills/` 主线全部 `106` 个 skill 与 `40/40` 个 shared-references。
- 24 个 business portable skill 与 9 个 portable reference 与 canonical
  `skills/` 字节一致；其余内容由 `tools/build_skills_kimi.py` 从
  `skills/skills-codex/` 机械转换（幂等，`--check` 校验）。
- 默认审稿契约:Kimi Code `Agent` 工具子代理（首轮 `kimi_subagent`，续轮
  `kimi_subagent_continue` + `resume`),same-family / provisional。
- 跨族升级路径：在 Kimi Code 配置中注册中性的 `llm-chat` MCP server
  (`mcp-servers/llm-chat/`)→ cross-family / accepted。详见
  `docs/KIMI_ADAPTATION.md`。

安装（详见英文 README 与 `docs/KIMI_ADAPTATION.md`):

```bash
bash tools/install_aris_kimi.sh ~/your-project --office-author "Your Name"
```

清单文件：`.aris/installed-skills-kimi.txt`。
