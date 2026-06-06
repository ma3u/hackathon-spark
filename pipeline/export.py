"""
Export — Graph-Dict -> JSON, CSV (nodes/relationships), Neo4j-Cypher.

Formatgleich zu den Schwester-Prototypen (input/<case>_graph_data.json,
<case>_nodes.csv, <case>_relationships.csv, <case>_neo4j_import.cypher),
damit das vorhandene React-Frontend (react-force-graph-3d) und ein Neo4j
denselben Datensatz lesen können.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

_RESERVED = {"id", "label", "type", "subtype", "source_id", "target_id", "relationship_type"}


def write_json(graph: dict, path: str | Path) -> None:
    Path(path).write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(graph: dict, nodes_path: str | Path, rels_path: str | Path) -> None:
    node_cols = _columns(graph["nodes"], ("id", "label", "type", "subtype"))
    with open(nodes_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=node_cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(graph["nodes"])

    rel_cols = _columns(graph["relationships"], ("source_id", "target_id", "relationship_type"))
    with open(rels_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rel_cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(graph["relationships"])


def write_cypher(graph: dict, path: str | Path) -> None:
    lines: list[str] = [
        "// ================================================",
        "// Gemeinderat Musterbach — Protokoll-Graph (Neo4j Import)",
        "// Generiert von graph-protokoll (SPARK Challenge 2)",
        "// ================================================",
        "",
        "// CONSTRAINTS",
    ]
    for ntype in sorted({n["type"] for n in graph["nodes"]}):
        lines.append(f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{ntype}) REQUIRE n.id IS UNIQUE;")
    lines += ["", "// === NODES ==="]
    for n in graph["nodes"]:
        props = _props(n)
        lines.append(f'MERGE (n:{n["type"]} {{id: {_q(n["id"])}}}) SET n += {{{props}}};')
    lines += ["", "// === RELATIONSHIPS ==="]
    for r in graph["relationships"]:
        extra = {k: v for k, v in r.items() if k not in _RESERVED}
        prop_str = f" {{{_props_dict(extra)}}}" if extra else ""
        lines.append(
            f'MATCH (a {{id: {_q(r["source_id"])}}}), (b {{id: {_q(r["target_id"])}}}) '
            f'MERGE (a)-[:{r["relationship_type"]}{prop_str}]->(b);'
        )
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _columns(rows: list[dict], lead: tuple[str, ...]) -> list[str]:
    cols = list(lead)
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    return cols


def _q(v) -> str:
    return '"' + str(v).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _props(n: dict) -> str:
    items = {k: v for k, v in n.items() if k != "id"}
    return _props_dict(items)


def _props_dict(items: dict) -> str:
    return ", ".join(f"{k}: {_q(v)}" for k, v in items.items())
