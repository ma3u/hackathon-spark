"""
Entity-Resolution für `Person` — Namens-Dubletten in Neo4j zusammenführen.

Dieselbe Person taucht mit mehreren Schreibweisen auf:
  • **Anrede der Sitzungsleitung** im Namen ("Präsidentin Bärbel Bas" vs "Bärbel Bas"),
  • **Titel-Eskalation** ("Dr. Armin Grau" vs "Prof. Dr. Armin Grau"),
  • NBSP/Unicode ("Dr.\xa0Gregor Gysi").
Da `Person` ein SHARED_TYPE mit globaler `id` ist, ergeben unterschiedliche Schreibweisen
unterschiedliche Knoten → unscharfe sitzungsübergreifende Abfragen. Dieses Skript clustert
**konservativ** über den voll-normalisierten Namen (NUR exakte Voll-Namens-Gleichheit nach
Strippen von Anrede + akad. Titel; gleiche Nachnamen verschiedener Personen bleiben getrennt)
und merged je Cluster per `apoc.refactor.mergeNodes` (Relationships werden mitgeführt).

Quellseitige Prävention: `bundestag_xml._canon_person_name` (Anrede/NBSP) — neue Ladeläufe
erzeugen die Anrede-Dubletten gar nicht erst. Dieses Skript räumt den BESTAND auf.

  python scripts/entity_resolution.py            # Dry-Run (zeigt nur den Merge-Plan)
  python scripts/entity_resolution.py --apply     # führt die Merges aus
"""

from __future__ import annotations

import argparse
import collections
import os
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Anrede (Sitzungsleitung) am Namensanfang; akad. Titel überall.
_ANREDE = re.compile(r"^\s*(alters|vize)?präsident(in)?\b|^\s*schriftführer(in)?\b", re.I)
_TITEL = re.compile(r"\b(prof|dr|h\.?\s*c|ing|dipl|rer|nat|phil|jur|med|mdb|ll\.?m)\b\.?", re.I)


def _norm(name: str) -> str:
    """Voll-Normalisierung NUR fürs Clustern (Anrede + Titel + Satzzeichen weg)."""
    n = unicodedata.normalize("NFC", (name or "").replace("\xa0", " "))
    prev = None
    while prev != n:
        prev = n
        n = _ANREDE.sub("", n).strip()
    n = _TITEL.sub("", n.lower())
    n = re.sub(r"[^a-zäöüß ]", " ", n)
    return " ".join(n.split())


def _display(label: str) -> str:
    """Anzeigename: Anrede weg, akad. Titel BLEIBT, NBSP/Unicode normalisiert."""
    n = unicodedata.normalize("NFC", (label or "").replace("\xa0", " "))
    prev = None
    while prev != n:
        prev = n
        n = _ANREDE.sub("", n).strip()
    return " ".join(n.split())


def _has_anrede(label: str) -> bool:
    return bool(_ANREDE.match(unicodedata.normalize("NFC", (label or "").replace("\xa0", " "))))


def plan(rows: list[dict]) -> list[dict]:
    """rows: [{id,label,deg}] → Merge-Cluster (nur echte Voll-Namens-Gleichheit, >1 Knoten)."""
    g: dict[str, list[dict]] = collections.defaultdict(list)
    for r in rows:
        k = _norm(r["label"])
        if len(k.split()) >= 2:  # Vor- UND Nachname nötig (keine Einzeltoken-Merges)
            g[k].append(r)
    clusters = []
    for k, variants in g.items():
        if len(variants) < 2:
            continue
        # Ziel = sauberste id (ohne Anrede), dann höchster Grad → behält die meisten Kanten.
        target = sorted(variants, key=lambda v: (_has_anrede(v["label"]), -v["deg"]))[0]
        others = [v for v in variants if v["id"] != target["id"]]
        best = max((_display(v["label"]) for v in variants), key=len)  # „Prof. Dr." > „Dr."
        clusters.append({"key": k, "target": target, "others": others, "label": best})
    return sorted(clusters, key=lambda c: c["key"])


def patch_pages_graphs() -> None:
    """Committete Struktur-Graphen (web/data/amt_*.json) angleichen: Anrede aus Person-id+label
    strippen, Dubletten je Sitzung mergen, Kanten umhängen + deduplizieren. (Neo4j separat.)"""
    import glob
    import json
    from pathlib import Path
    from pipeline.bundestag_xml import _canon_person_name
    from pipeline.graph_build import _slug

    web = Path(__file__).resolve().parent.parent / "web" / "data"
    total_files = total_merged = total_labels = 0
    for f in sorted(glob.glob(str(web / "amt_*.json"))):
        if "dashboard" in f:
            continue
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        idmap, keep, merged, relabel = {}, {}, 0, 0
        for n in d["nodes"]:
            if n.get("type") != "Person":
                continue
            cid = "person_" + _slug(_canon_person_name(n["label"]))
            idmap[n["id"]] = cid
            disp = _display(n["label"])
            if cid in keep:                      # Dublette → in den Kanon falten
                if len(disp) > len(keep[cid]["label"]):
                    keep[cid]["label"] = disp
                merged += 1
            else:
                if disp != n["label"]:
                    relabel += 1
                n["id"], n["label"] = cid, disp
                keep[cid] = n
        if not merged and not relabel:
            continue
        nodes = [n for n in d["nodes"] if n.get("type") != "Person"] + list(keep.values())
        seen, rels = set(), []
        for r in d["relationships"]:
            a = idmap.get(r["source_id"], r["source_id"])
            b = idmap.get(r["target_id"], r["target_id"])
            key = (a, b, r["relationship_type"])
            if a == b or key in seen:            # Self-Loop/Dublette nach Remap verwerfen
                continue
            seen.add(key)
            r = {**r, "source_id": a, "target_id": b}
            rels.append(r)
        d["nodes"], d["relationships"] = nodes, rels
        d.setdefault("metadata", {})["node_count"] = len(nodes)
        d["metadata"]["relationship_count"] = len(rels)
        Path(f).write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        total_files += 1
        total_merged += merged
        total_labels += relabel
        print(f"  ✓ {Path(f).name}: {merged} Personen gemerged, {relabel} Labels gesäubert")
    print(f"\nPages: {total_files} Graphen gepatcht, {total_merged} Dubletten, {total_labels} Labels.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Person-Entity-Resolution (Neo4j + Pages)")
    ap.add_argument("--apply", action="store_true", help="Neo4j-Merges ausführen (sonst Dry-Run)")
    ap.add_argument("--pages", action="store_true", help="committete web/data/amt_*.json angleichen")
    args = ap.parse_args()
    if args.pages:
        print("📄 Pages-Struktur-Graphen angleichen …")
        patch_pages_graphs()
        if not args.apply:
            return
    from neo4j import GraphDatabase  # lazy

    cfg = (os.getenv("NEO4J_URI", "bolt://localhost:7687"),
           os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "neo4j"))
    drv = GraphDatabase.driver(cfg[0], auth=(cfg[1], cfg[2]))
    with drv.session() as s:
        rows = s.run("MATCH (p:Person) OPTIONAL MATCH (p)-[r]-() "
                     "RETURN p.id AS id, p.label AS label, count(r) AS deg").data()
        before = len(rows)
        clusters = plan(rows)
        print(f"Person-Knoten: {before} · Merge-Cluster: {len(clusters)} · "
              f"zu entfernen: {sum(len(c['others']) for c in clusters)}")
        for c in clusters:
            print(f"  • {c['label']}  ← " +
                  ", ".join(f"{o['label']!r}({o['deg']})" for o in c["others"]) +
                  f"   [Ziel {c['target']['id']}]")
        if not args.apply:
            print("\nDry-Run — mit --apply ausführen.")
            drv.close()
            return
        merged = 0
        for c in clusters:
            ordered = [c["target"]["id"]] + [o["id"] for o in c["others"]]
            s.run(
                "UNWIND $ids AS oid MATCH (n:Person {id: oid}) WITH collect(n) AS ns "
                "CALL apoc.refactor.mergeNodes(ns, {properties:'discard', mergeRels:true}) "
                "YIELD node SET node.label = $label RETURN node.id",
                ids=ordered, label=c["label"])
            merged += len(c["others"])
            print(f"  ✓ {c['label']} ({len(c['others'])} zusammengeführt)")
        # Anrede auch bei Personen säubern, die NUR als Sitzungsleitung vorkommen (kein
        # Redner-Pendant zum Mergen, aber das Label trägt noch „Vizepräsidentin …").
        cleaned = 0
        for r in s.run("MATCH (p:Person) RETURN p.id AS id, p.label AS label").data():
            disp = _display(r["label"])
            if disp and disp != r["label"]:
                s.run("MATCH (p:Person {id:$id}) SET p.label=$l", id=r["id"], l=disp)
                cleaned += 1
        after = s.run("MATCH (p:Person) RETURN count(p) AS c").single()["c"]
        print(f"\nFertig: {merged} Knoten zusammengeführt, {cleaned} Labels gesäubert. "
              f"Person-Knoten {before} → {after}.")
    drv.close()


if __name__ == "__main__":
    sys.exit(main())
