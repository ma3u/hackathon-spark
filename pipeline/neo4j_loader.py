"""
Neo4j-Import — Graph-Dict (`{nodes, relationships}`) idempotent nach Neo4j laden.

Nutzt den offiziellen `neo4j`-Driver mit **parametrisierten** Cypher-Statements
(kein String-Interpolieren von Daten) und `MERGE` (mehrfaches Laden ist sicher).
Knoten-Label = `type`; Relationstyp = `relationship_type`.

Dry-Run (Default): zählt/plant ohne Verbindung — überall lauffähig.
Echt:  load_graph(graph, uri, auth, dry_run=False) gegen ein laufendes Neo4j.
"""

from __future__ import annotations

import os

# zulässige Label-/Reltyp-Zeichen (Cypher-Injection über Typnamen verhindern)
import re as _re
_SAFE = _re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _props_only(d: dict, reserved: set[str]) -> dict:
    return {k: v for k, v in d.items() if k not in reserved}


def build_statements(graph: dict) -> list[tuple[str, dict]]:
    """(cypher, params)-Paare: erst Constraints, dann Knoten, dann Kanten."""
    stmts: list[tuple[str, dict]] = []
    labels = sorted({n["type"] for n in graph["nodes"] if _SAFE.match(n["type"])})
    for lbl in labels:
        stmts.append((f"CREATE CONSTRAINT IF NOT EXISTS "
                      f"FOR (n:`{lbl}`) REQUIRE n.id IS UNIQUE", {}))
    for n in graph["nodes"]:
        if not _SAFE.match(n["type"]):
            continue
        props = _props_only(n, {"id"})
        stmts.append((f"MERGE (n:`{n['type']}` {{id: $id}}) SET n += $props",
                      {"id": n["id"], "props": props}))
    reserved = {"source_id", "target_id", "relationship_type"}
    for r in graph["relationships"]:
        rtype = r["relationship_type"]
        if not _SAFE.match(rtype):
            continue
        props = _props_only(r, reserved)
        stmts.append((
            f"MATCH (a {{id: $src}}), (b {{id: $tgt}}) "
            f"MERGE (a)-[rel:`{rtype}`]->(b) SET rel += $props",
            {"src": r["source_id"], "tgt": r["target_id"], "props": props}))
    return stmts


def load_graph(graph: dict, *, uri: str | None = None, user: str | None = None,
               password: str | None = None, database: str = "neo4j",
               dry_run: bool = True) -> dict:
    stmts = build_statements(graph)
    n_nodes = len(graph["nodes"])
    n_rels = len(graph["relationships"])
    if dry_run:
        print(f"[dry-run] {len(stmts)} Statements vorbereitet "
              f"({n_nodes} Knoten, {n_rels} Beziehungen). Echt laden: --load")
        return {"statements": len(stmts), "nodes": n_nodes, "relationships": n_rels, "loaded": False}

    from neo4j import GraphDatabase  # lazy: nur im echten Lauf benötigt
    uri = uri or os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = user or os.environ.get("NEO4J_USER", "neo4j")
    password = password or os.environ.get("NEO4J_PASSWORD", "healthdataspace")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session(database=database) as session:
            for cypher, params in stmts:
                session.run(cypher, **params)
        print(f"✓ Geladen nach {uri}/{database}: {n_nodes} Knoten, {n_rels} Beziehungen.")
    finally:
        driver.close()
    return {"statements": len(stmts), "nodes": n_nodes, "relationships": n_rels, "loaded": True}
