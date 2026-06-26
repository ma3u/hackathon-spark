#!/usr/bin/env bash
# agentic-init — Claude-Code-nativer Kontroll-Stack + Token-Disziplin (RTK + caveman).
#
# Idempotent: installiert fehlende Werkzeuge, prüft den Stack und fährt den dep-freien
# Smoke-Test. Macht dieses Repo zu einem Agentic-AI-Projekt im Claude-Code-Sinn.
# Prompt/Quelle: https://gist.github.com/ma3u/09e76d3b604d132673bc4a59b092709a
#
#   bash scripts/agentic-init.sh           # fehlende Tools installieren + alles prüfen
#   bash scripts/agentic-init.sh --check   # NUR prüfen, nichts installieren
set -euo pipefail
cd "$(dirname "$0")/.."
CHECK_ONLY=0; [ "${1:-}" = "--check" ] && CHECK_ONLY=1
ok()   { printf "  \033[32m✓\033[0m %s\n" "$1"; }
miss() { printf "  \033[31m✗\033[0m %s\n" "$1"; FAIL=1; }
FAIL=0

echo "▸ Token-Disziplin (lokal, nur Dev — nie in CI)"
# RTK (INPUT-Seite): komprimiert Tool-Ausgaben 60–90 % vor dem Kontext, via PreToolUse-Hook.
if command -v rtk >/dev/null 2>&1; then
  ok "RTK $(rtk --version 2>/dev/null | awk '{print $2}') ($(which rtk))"
elif [ "$CHECK_ONLY" = 1 ]; then
  miss "RTK fehlt — install: brew install rtk  (oder cargo install --git https://github.com/rtk-ai/rtk)"
else
  echo "  installiere RTK …"
  brew install rtk 2>/dev/null || cargo install --git https://github.com/rtk-ai/rtk
  rtk init -g || true   # PreToolUse-Hook global einhängen
fi
# caveman (OUTPUT-Seite): Claude-Code-Skill, strippt Prosa (~65 %), Code/Commands bleiben exakt.
if [ -e "$HOME/.claude/.caveman-active" ] || ls "$HOME/.claude/hooks/"caveman* >/dev/null 2>&1; then
  ok "caveman installiert/aktiv"
elif [ "$CHECK_ONLY" = 1 ]; then
  miss "caveman fehlt — install: npx -y skills add JuliusBrussee/caveman"
else
  echo "  installiere caveman …"; npx -y skills add JuliusBrussee/caveman || true
fi

echo "▸ Kontroll-Stack (Claude-Code-nativ)"
need() { if [ -e "$1" ]; then ok "$2"; else miss "$2 — fehlt: $1"; fi; }
cnt() { ls $1 2>/dev/null | wc -l | tr -d ' '; }
need CLAUDE.md                 "CLAUDE.md (@rules-Imports: $(grep -c '^@.claude/rules' CLAUDE.md))"
need .claude/settings.json     "settings.json (Permissions + PreToolUse-Hook)"
need .claude/hooks/guard.sh    "Guard-Hook (deny/ask destruktiv + Secret-Reads)"
need .claude/rules             "rules/ ($(cnt '.claude/rules/*.md'))"
need .claude/commands          "commands/ ($(cnt '.claude/commands/*.md'): review·fix-issue·deploy-check·plan)"
need .claude/agents            "agents/ ($(cnt '.claude/agents/*.md'): architect·implementer·reviewer·tester·…)"
need .claude/skills            "skills/ ($(ls -d .claude/skills/*/ 2>/dev/null | wc -l | tr -d ' '))"
need docs/adr/index.md         "ADRs ($(cnt 'docs/adr/0*.md'), Nygard, immutabel) + Index"
need docs/diagrams             "diagrams ($(cnt 'docs/diagrams/*'), Mermaid)"
need docs/planning/index.md    "Planung future/current/done ($(find docs/planning -name '*.md' | wc -l | tr -d ' '))"
need docs/knowledge/index.md   "OKF-Wissensbasis ($(find docs/knowledge -name '*.md' | wc -l | tr -d ' ') Konzepte)"

echo "▸ Smoke-Test (dep-frei, nur Python-Stdlib — wie CI)"
if python3 run_demo.py --no-queries >/dev/null 2>&1; then ok "run_demo.py --no-queries (exit 0)"; else miss "run_demo.py fehlgeschlagen"; fi

echo "▸ RTK-Ersparnis (Beleg, dass die Tools genutzt werden)"
rtk gain 2>/dev/null | grep -E "Total commands|Tokens saved|Efficiency" | sed 's/^/  /' || echo "  (rtk gain n/v)"

[ "$FAIL" = 0 ] && echo "✓ agentic-init OK." || { echo "✗ agentic-init: offene Punkte oben."; exit 1; }
