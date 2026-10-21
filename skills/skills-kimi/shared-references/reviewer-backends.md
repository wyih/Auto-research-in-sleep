# Kimi Reviewer Backends

Use [reviewer-routing.md](reviewer-routing.md) for the native Agent-tool contract
and the optional cross-family `llm-chat` or Oracle routes. Native reviews use a
fresh subagent at the host's strongest reasoning configuration; model and effort
are controlled by the host. Follow-ups resume the saved subagent.

Select an external reviewer only when requested and its configured tools are
available. Preserve the task's evidence, working directory, fresh-context rules,
review scope, and deterministic checks. Record the returned model identity;
same-family reviews remain provisional. A missing selected route is
`REVIEW_UNAVAILABLE`.
