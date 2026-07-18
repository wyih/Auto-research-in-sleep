# Portable Business Skill Helper Resolution

Business skills are authored under `skills/<name>` and packaged under `skills/skills-codex/<name>`, but Codex and Grok normally consume project-local symlinks at `.agents/skills/<name>`. Never assume the current working directory is the ARIS repository.

Before invoking a bundled script, resolve and validate its skill directory:

```bash
resolve_business_skill_dir() {
  skill_name="$1"
  for candidate in \
    ".agents/skills/$skill_name" \
    "skills/$skill_name" \
    "${ARIS_REPO:-}/skills/skills-codex/$skill_name" \
    "${ARIS_REPO:-}/skills/$skill_name" \
    "${HOME}/.agents/skills/$skill_name" \
    "${HOME}/.codex/skills/$skill_name" \
    "${HOME}/.grok/skills/$skill_name"
  do
    if [ -f "$candidate/SKILL.md" ]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  if [ -f "${HOME}/.aris/repo" ]; then
    repo_root="$(sed -n '1p' "${HOME}/.aris/repo")"
    for candidate in \
      "$repo_root/skills/skills-codex/$skill_name" \
      "$repo_root/skills/$skill_name"
    do
      if [ -f "$candidate/SKILL.md" ]; then
        printf '%s\n' "$candidate"
        return 0
      fi
    done
  fi

  return 1
}
```

Then bind a task-specific variable, for example:

```bash
BRIDGE_SKILL_DIR="$(resolve_business_skill_dir browser-session-bridge)" || {
  echo "browser-session-bridge helper directory not found" >&2
  exit 2
}
```

Rules:

- Validate `SKILL.md` before using a candidate; never execute a same-named script from an unverified directory.
- Do not print environment contents, credentials, or the contents of the global pointer.
- Use a task-specific variable such as `WRDS_SKILL_DIR`; do not overwrite `HOME`, `ARIS_REPO`, or another system option.
- Project-local `.agents/skills` takes precedence so Codex and Grok execute the exact installed package selected for that project.
