#!/usr/bin/env bash
set -euo pipefail

# Install this skill for local agents. SKILL.md is a cross-agent standard:
#   Claude Code discovers skills in ~/.claude/skills/<name>/
#   Codex CLI discovers skills in ~/.codex/skills/<name>/  (CODEX_HOME aware)
# WorkBuddy / claude.ai use the zip from package.sh instead.

root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root"

python3 scripts/validate_skill_package.py --keep-staging
name=$(basename "$(find skill -mindepth 1 -maxdepth 1 -type d | head -1)")
staged="$root/.skill-package-staging/$name"

installed=0
for home in "$HOME/.claude" "${CODEX_HOME:-$HOME/.codex}"; do
  if [[ ! -d "$home" ]]; then
    echo "[skip] $home does not exist (tool not installed?)"
    continue
  fi
  target="$home/skills/$name"
  mkdir -p "$home/skills"
  rm -rf "$target"
  cp -R "$staged" "$target"
  echo "[ok] installed -> $target"
  installed=1
done

if [[ "$installed" -eq 0 ]]; then
  echo "[error] no agent home directory found (~/.claude or ~/.codex)." >&2
  exit 1
fi
