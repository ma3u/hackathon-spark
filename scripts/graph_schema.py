#!/usr/bin/env python3
"""
Meta-Graph / Schema-Doku — introspiziert die committeten SPARK-Graphen (web/data/*.json) und
schreibt eine FAKTISCHE Schema-Beschreibung: Knoten-Typen (Label) mit Schicht + Eigenschaften,
Beziehungs-Typen mit Quelle→Ziel-Labelpaaren, sowie die `metadata`-Felder der Graphen.

Erzeugt:
  • docs/knowledge/datamodels/graph-schema.md   (Tabellen + eingebettetes Mermaid-Meta-Diagramm)
  • docs/diagrams/graph-meta-schema.mmd          (generiertes Mermaid des Meta-Graphen)

Dep-frei (nur Stdlib). Quelle der Wahrheit = die echten Graphen, nicht handgepflegte Listen.

  python scripts/graph_schema.py
"""

from __future__ import annotations

import datetime
import glob
import json
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WEB = REPO / "web" / "data"
RESERVED_N = {"id", "label", "type", "subtype", "schicht"}
RESERVED_R = {"source_id", "target_id", "relationship_type"}
SKIP = ("_dashboard", "_barrierefrei", "_protokoll", "aggregate_dashboard",
        "youtube_completeness", "_sound_events")


def graph_files():
    for f in sorted(glob.glob(str(WEB / "*.json"))):
        if any(s in Path(f).name for s in SKIP):
            continue
        yield f


def main() -> int:
    node_props: dict[str, set] = defaultdict(set)
    node_schicht: dict[str, set] = defaultdict(set)
    node_count: Counter = Counter()
    rel_count: Counter = Counter()
    rel_pairs: dict[str, set] = defaultdict(set)
    rel_props: dict[str, set] = defaultdict(set)
    meta_fields: dict[str, set] = defaultdict(set)
    herkuenfte: Counter = Counter()
    n_graphs = 0

    for f in graph_files():
        try:
            g = json.loads(Path(f).read_text(encoding="utf-8"))
        except Exception:
            continue
        if not (isinstance(g, dict) and "nodes" in g and "relationships" in g):
            continue
        n_graphs += 1
        idtype = {n["id"]: n.get("type", "?") for n in g["nodes"]}
        for n in g["nodes"]:
            t = n.get("type", "?")
            node_count[t] += 1
            if n.get("schicht"):
                node_schicht[t].add(n["schicht"])
            node_props[t].update(k for k in n if k not in RESERVED_N)
        for r in g["relationships"]:
            rt = r.get("relationship_type", "?")
            rel_count[rt] += 1
            rel_pairs[rt].add((idtype.get(r.get("source_id"), "?"),
                               idtype.get(r.get("target_id"), "?")))
            rel_props[rt].update(k for k in r if k not in RESERVED_R)
        md = g.get("metadata", {})
        for k, v in md.items():
            meta_fields[k].add(type(v).__name__)
        if md.get("herkunft"):
            herkuenfte[md["herkunft"]] += 1

    # ── Mermaid Meta-Graph (Label -REL-> Label) ──────────────────────────────
    edges = sorted({(s, rt, t) for rt, pairs in rel_pairs.items() for (s, t) in pairs
                    if s != "?" and t != "?"})
    mmd = ["%% graph-protokoll — Meta-Graph (Schema), generiert aus web/data/*.json durch",
           "%% scripts/graph_schema.py. Knoten = Knotentypen (Label), Kanten = Beziehungstypen.",
           "flowchart LR"]
    for s, rt, t in edges:
        mmd.append(f"    {s} -->|{rt}| {t}")
    (REPO / "docs" / "diagrams" / "graph-meta-schema.mmd").write_text(
        "\n".join(mmd) + "\n", encoding="utf-8")

    # ── Markdown ─────────────────────────────────────────────────────────────
    def cell(s):
        return ", ".join(sorted(s)) if s else "—"

    L = []
    L.append("---")
    L.append("type: datamodel")
    L.append("title: Graph schema (Meta-Graph)")
    L.append("description: Faktische Schema-Beschreibung — Knotentypen, Beziehungstypen und "
             "metadata-Felder, introspiziert aus den committeten Graphen.")
    L.append("resource: scripts/graph_schema.py")
    L.append("tags: [datamodel, schema, meta-graph, neo4j, generated]")
    L.append(f"timestamp: {datetime.date.today().isoformat()}")
    L.append("---\n")
    L.append("# Graph schema (Meta-Graph)\n")
    L.append(f"> **Generiert** aus {n_graphs} committeten Graphen (`web/data/*.json`) durch "
             f"`scripts/graph_schema.py` am {datetime.date.today().isoformat()}. Nicht von Hand "
             f"editieren — neu erzeugen. Vertrag/Format: [[spark-graph-format]]; Schichten: "
             f"[[ontologie-5-schichten]]; Provenienz: [[provenienz-belegt-durch]].\n")

    L.append("## Knotentypen (Label)\n")
    L.append("| Typ (Neo4j-Label) | Schicht | Knoten (Σ) | Eigenschaften (außer id/label/type/subtype/schicht) |")
    L.append("| --- | --- | ---: | --- |")
    for t in sorted(node_count, key=lambda x: -node_count[x]):
        L.append(f"| `{t}` | {cell(node_schicht[t])} | {node_count[t]} | {cell(node_props[t])} |")

    L.append("\n## Beziehungstypen\n")
    L.append("| Beziehungstyp | Quelle → Ziel (beobachtet) | Kanten (Σ) | Eigenschaften |")
    L.append("| --- | --- | ---: | --- |")
    for rt in sorted(rel_count, key=lambda x: -rel_count[x]):
        pairs = "; ".join(f"{s}→{t}" for s, t in sorted(rel_pairs[rt]) if s != "?" and t != "?") or "—"
        L.append(f"| `{rt}` | {pairs} | {rel_count[rt]} | {cell(rel_props[rt])} |")

    L.append("\n## `metadata`-Felder (pro Graph)\n")
    L.append("| Feld | Typ(en) |")
    L.append("| --- | --- |")
    for k in sorted(meta_fields):
        L.append(f"| `{k}` | {cell(meta_fields[k])} |")
    L.append(f"\nBeobachtete `herkunft`-Werte: {dict(herkuenfte)}.\n")

    L.append("## Meta-Graph (Schema-Diagramm)\n")
    L.append("```mermaid")
    L.extend(mmd)
    L.append("```\n")
    L.append("> Pflege-Hinweis: Neue Label/Beziehungen müssen in `NEO4J_SCHEMA` "
             "(`pipeline/neo4j_graphrag.py`, Text2Cypher) und im Web-`LAYER` gespiegelt werden "
             "(SPARK-Vertrag, ADR-0003). Diese Seite zeigt den IST-Zustand der Graphen, nicht "
             "den SOLL-Vertrag — Abweichung = Drift, bitte beheben.")

    out = REPO / "docs" / "knowledge" / "datamodels" / "graph-schema.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"✓ {out.relative_to(REPO)}  ({n_graphs} Graphen · {len(node_count)} Knotentypen · "
          f"{len(rel_count)} Beziehungstypen · {len(meta_fields)} metadata-Felder)")
    print(f"✓ docs/diagrams/graph-meta-schema.mmd  ({len(edges)} Meta-Kanten)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
