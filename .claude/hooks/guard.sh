#!/usr/bin/env bash
# PreToolUse guard for graph-protokoll — defense-in-depth over .claude/settings.json.
# Wired under settings.json hooks.PreToolUse with a "Bash" matcher.
# Reads the tool-call JSON on stdin and emits a PreToolUse permission decision as JSON:
#   - DENY  catastrophic commands outright (root/home/system wipes, fork bomb, force-push);
#   - ASK   other destructive ops (recursive delete of a real path, hard reset, infra
#           teardown, Neo4j volume removal) and reads/exfil of secret/credential files.
# Catches patterns that glob-based settings rules miss (e.g. `rm -rf` mid-pipeline,
# `cat .env`). Classification is done in Python for precision (bash globbing over-matches
# substrings like a leading "/"). The hook's stdin is handed to Python via $GUARD_INPUT so the
# heredoc can stay the program source. Rules: CLAUDE.md gotcha #5 + settings.json ask/deny.
set -euo pipefail

export GUARD_INPUT="$(cat)"

python3 - <<'PY'
import os, sys, json, re

try:
    cmd = (json.loads(os.environ.get("GUARD_INPUT") or "{}")
           .get("tool_input", {}).get("command", "") or "")
except Exception:
    sys.exit(0)   # unparseable → allow (never block on our own failure)

if not cmd.strip():
    sys.exit(0)

def decide(kind, reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": kind,            # "deny" | "ask"
        "permissionDecisionReason": reason,
    }}))
    sys.exit(0)

# ── recursive force `rm` detection (handles -rf, -fr, -r -f, --recursive --force) ──
has_rm  = re.search(r"\brm\b", cmd)
recurse = re.search(r"-[A-Za-z]*r|--recursive", cmd)
force   = re.search(r"-[A-Za-z]*f|--force", cmd)
rm_rf   = bool(has_rm and recurse and force)

# Catastrophic delete targets: root, home, or a top-level system dir.
CATASTROPHIC = re.compile(
    r"(?:^|\s)(?:-\S+\s+)*"
    r"(?:/|~|\$\{?HOME\}?|"
    r"/(?:bin|boot|dev|etc|home|lib|proc|root|sbin|sys|usr|var|System|Users|Library|Applications)\b)"
    r"\s*(?:/?\*)?\s*(?:$|[;&|])"
)

# ── DENY: catastrophic ────────────────────────────────────────────────────────
if rm_rf and CATASTROPHIC.search(cmd):
    decide("deny", "Blocked: recursive force-delete of a root/home/system path.")
if ":(){" in cmd and "|:&" in cmd:
    decide("deny", "Blocked: fork-bomb pattern.")
if re.search(r"\bgit\s+push\b.*(--force\b|\s-f\b)", cmd) or re.search(r"\bgit\s+push\s+(-f|--force)\b", cmd):
    decide("deny", "Blocked: force-push rewrites remote history — do this only by explicit human action.")

# ── ASK: other destructive ops ────────────────────────────────────────────────
if rm_rf:
    decide("ask", "Recursive force-delete — confirm the path is intended.")
if re.search(r"\bgit\s+reset\s+--hard\b", cmd) or re.search(r"\bgit\s+clean\s+-\w*f", cmd):
    decide("ask", "Irreversibly discards working-tree changes.")
if re.search(r"\bterraform\s+destroy\b|\bkubectl\s+delete\b|\bhelm\s+uninstall\b", cmd):
    decide("ask", "Destroys infrastructure / cluster resources.")
if re.search(r"docker\s+volume\s+rm|docker\s+system\s+prune|docker\s+compose.*\bdown\b", cmd):
    decide("ask", "Removes the local Neo4j data/volumes.")

# ── ASK: secret/credential reads (gated on read/copy/exfil verbs) ─────────────
SECRET = re.compile(r"\.env\b|\.pem\b|\.key\b|\.p12\b|\.pfx\b|id_rsa|id_ed25519|credentials|/\.ssh/|/\.aws/|secrets/")
SAFE_TEMPLATE = re.compile(r"\.env\.(example|sample|template)\b")
READ_VERB = re.compile(r"\b(cat|less|head|tail|more|cp|scp|rsync|curl|nc|base64|xxd|strings)\b")
if SECRET.search(cmd) and not SAFE_TEMPLATE.search(cmd) and READ_VERB.search(cmd):
    decide("ask", "Reading/copying a secret or credential file.")

sys.exit(0)   # default: allow
PY
