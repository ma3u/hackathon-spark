"""
Mensch-im-Loop — exportierte Faktencheck-Korrekturen in den Datenbestand zurückspielen.

Die Pages-App lässt Reviewer:innen KI-Faktencheck-Vorschläge freigeben/ablehnen/korrigieren
und als `korrekturen_<sitzung>.json` exportieren (Audit-Record). Dieses Skript spielt so
eine Datei zurück: es annotiert die `Faktencheck`-Knoten in Neo4j (und optional im committeten
Pages-Graphen) mit der menschlichen Entscheidung — als **Freigabe-/Korrektur-Audit-Trail**.

Wichtig (Invarianten): die **Quelle bleibt** unangetastet (BELEGT_MIT). Das KI-Verdikt bleibt
als `verdikt` (KI-Vorschlag) erhalten; die menschliche Entscheidung kommt SEPARAT dazu
(`review_status`, `verdikt_mensch`, `geprueft_von`, `geprueft_am`, `review_notiz`,
`menschlich_geprueft=true`). So bleibt nachvollziehbar, was die KI vorschlug und was der Mensch
entschied (Neutralität/Transparenz, kein stilles Überschreiben).

  python scripts/apply_corrections.py korrekturen_amt_21_081.json            # Dry-Run
  python scripts/apply_corrections.py korrekturen_amt_21_081.json --apply     # Neo4j schreiben
  python scripts/apply_corrections.py korrekturen_amt_21_081.json --apply --pages  # + Pages-Graph
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
WEB = REPO / "web" / "data"
_SAFE = re.compile(r"^[A-Za-z0-9_]+$")  # Knoten-Suffix wie faktencheck_3

_PROPS = ("menschlich_geprueft", "review_status", "verdikt_mensch", "geprueft_von",
          "geprueft_am", "review_notiz")


def _record(k: dict, *, von: str, stand: str) -> dict:
    """Eine Korrektur → zu setzende Knoten-Properties (KI-Verdikt bleibt erhalten)."""
    return {"menschlich_geprueft": True, "review_status": k.get("status"),
            "verdikt_mensch": k.get("verdikt_neu") if k.get("status") == "korrigiert" else None,
            "geprueft_von": von, "geprueft_am": k.get("stand") or stand,
            "review_notiz": k.get("notiz") or ""}


def apply_neo4j(prefix: str, korr: list[dict], rec, *, cfg) -> int:
    from neo4j import GraphDatabase  # lazy
    drv = GraphDatabase.driver(cfg["uri"], auth=(cfg["user"], cfg["password"]))
    done = 0
    with drv.session() as s:
        for k in korr:
            fid = k.get("faktencheck_id", "")
            if not _SAFE.match(fid):
                continue
            r = s.run("MATCH (n:Faktencheck {id:$id}) SET n += $props RETURN count(n) AS c",
                      id=f"{prefix}::{fid}", props=rec(k)).single()
            done += (r["c"] if r else 0)
    drv.close()
    return done


def apply_pages(sitzung: str, korr: list[dict], rec) -> int:
    f = WEB / f"{sitzung}.json"
    if not f.exists():
        return 0
    g = json.loads(f.read_text(encoding="utf-8"))
    by_id = {n["id"]: n for n in g["nodes"]}
    n = 0
    for k in korr:
        node = by_id.get(k.get("faktencheck_id"))
        if node and node.get("type") == "Faktencheck":
            node.update({kk: vv for kk, vv in rec(k).items() if vv is not None})
            n += 1
    if n:
        f.write_text(json.dumps(g, ensure_ascii=False, indent=2), encoding="utf-8")
    return n


def main() -> None:
    ap = argparse.ArgumentParser(description="Mensch-im-Loop-Korrekturen zurückspielen")
    ap.add_argument("datei", help="korrekturen_<sitzung>.json (Export aus der Pages-App)")
    ap.add_argument("--apply", action="store_true", help="Neo4j schreiben (sonst Dry-Run)")
    ap.add_argument("--pages", action="store_true", help="zusätzlich den committeten Pages-Graphen annotieren")
    args = ap.parse_args()

    d = json.loads(Path(args.datei).read_text(encoding="utf-8"))
    sitzung = d.get("sitzung", "")
    korr = d.get("korrekturen", [])
    von = d.get("geprueft_von", "Reviewer")
    stand = d.get("stand", "")
    if not re.match(r"^amt_\d+_\d+$", sitzung):
        print(f"Unerwartete Sitzungs-ID {sitzung!r} — erwartet amt_<wp>_<nnn>."); sys.exit(1)
    rec = lambda k: _record(k, von=von, stand=stand)

    print(f"Sitzung {sitzung} · {len(korr)} Korrektur(en) von {von}:")
    for k in korr:
        extra = f" → {k['verdikt_neu']}" if k.get("status") == "korrigiert" else ""
        print(f"  • {k.get('faktencheck_id')}: {k.get('status')}{extra}  ({(k.get('person') or '')[:30]})")
    if not args.apply:
        print("\nDry-Run — mit --apply schreiben.")
        return

    cfg = {"uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
           "user": os.getenv("NEO4J_USER", "neo4j"), "password": os.getenv("NEO4J_PASSWORD", "neo4j")}
    n_neo = apply_neo4j(sitzung, korr, rec, cfg=cfg)
    print(f"  ✓ Neo4j: {n_neo} Faktencheck-Knoten annotiert (Quelle unangetastet).")
    if args.pages:
        n_pg = apply_pages(sitzung, korr, rec)
        print(f"  ✓ Pages-Graph: {n_pg} Knoten annotiert ({sitzung}.json).")


if __name__ == "__main__":
    main()
