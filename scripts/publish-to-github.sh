#!/usr/bin/env bash
set -euo pipefail

# Veröffentlicht graph-protokoll als eigenständiges öffentliches GitHub-Repo
# unter deinem Account und aktiviert GitHub Pages (Deploy via Actions).
#
# Voraussetzungen: git, GitHub CLI (`gh auth login` als ma3u).
# Aufruf aus dem Ordner graph-protokoll/ heraus:
#     ./scripts/publish-to-github.sh [repo-name]
#
# Hintergrund: Die Claude-Session konnte das Repo nicht selbst anlegen
# (der Session-Token ist auf ein einziges Repo beschränkt). Dieses Skript
# erledigt den Schritt mit deinen lokalen gh-Rechten.

REPO="${1:-graph-protokoll}"
OWNER="$(gh api user --jq .login)"

echo "→ Hole den autoritativen EUPL-1.2-Volltext (wie BMDS SPARK)…"
if curl -fsSL -o LICENSE \
    "https://gitlab.opencode.de/fitko/docs/portal/-/raw/main/LICENSES/EUPL-1.2.txt"; then
  printf '\nSPDX-License-Identifier: EUPL-1.2\nCopyright (c) 2026 Matthias Buchhorn (ma3u)\n' >> LICENSE
  echo "  ✓ EUPL-1.2-Volltext in LICENSE geschrieben."
else
  echo "  ⚠ Download fehlgeschlagen — LICENSE behält die EUPL-1.2-Notice (Volltext später ergänzen)."
fi

echo "→ Lege öffentliches Repo ${OWNER}/${REPO} an und pushe den aktuellen Ordner…"
git init -q
git add .
git commit -q -m "graph-protokoll: audio meeting/Bundestag protocol analysis with GraphRAG + fact-check"
git branch -M main

gh repo create "${OWNER}/${REPO}" --public --source=. --remote=origin --push \
  --description "SPARK Challenge 2 — Audiomitschnitt → Protokoll-Knowledge-Graph + Faktencheck (GraphRAG)"

echo "→ Aktiviere GitHub Pages (Quelle: GitHub Actions)…"
gh api -X POST "repos/${OWNER}/${REPO}/pages" -f "build_type=workflow" 2>/dev/null \
  || echo "  (Pages ggf. bereits aktiv — der Pages-Workflow deployt beim nächsten Push.)"

echo "✓ Fertig. Seite erscheint unter: https://${OWNER}.github.io/${REPO}/"
echo "  Actions-Lauf abwarten (Tab 'Actions' → 'Deploy GitHub Pages')."
