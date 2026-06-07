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


# Knotentypen, die SITZUNGSÜBERGREIFEND dieselbe Entität bezeichnen: eine Person, eine
# Fraktion, eine Norm, eine Quelle ist in jeder Sitzung dieselbe. Alle übrigen Knoten
# (TOPs, Reden, Aussagen, Segmente, Saalreaktionen …) sind sitzungsspezifisch.
SHARED_TYPES = frozenset({"Person", "Fraktion", "Norm", "Quelle"})


def namespace_graph(graph: dict, prefix: str, *, shared_types=SHARED_TYPES) -> dict:
    """Knoten-IDs pro Sitzung eindeutig machen — Voraussetzung, um MEHRERE Sitzungen
    kollisionsfrei in EIN Neo4j zu laden.

    Sitzungsspezifische IDs werden mit `prefix` versehen; geteilte Entitäten (Person,
    Fraktion, …) behalten ihre globale ID und werden so über `MERGE` sitzungsübergreifend
    zu EINEM Knoten verschmolzen — genau das ermöglicht Abfragen wie „in welchen Sitzungen
    sprach Person X?". Gibt einen neuen Graph-Dict zurück (Original bleibt unverändert).
    """
    idmap = {n["id"]: (n["id"] if n["type"] in shared_types else f"{prefix}::{n['id']}")
             for n in graph["nodes"]}
    nodes = [{**n, "id": idmap[n["id"]]} for n in graph["nodes"]]
    rels = [{**r, "source_id": idmap.get(r["source_id"], r["source_id"]),
             "target_id": idmap.get(r["target_id"], r["target_id"])}
            for r in graph["relationships"]]
    return {"metadata": graph.get("metadata", {}), "nodes": nodes, "relationships": rels}


def load_graph(graph: dict, *, uri: str | None = None, user: str | None = None,
               password: str | None = None, database: str = "neo4j",
               dry_run: bool = True, batch_size: int = 500) -> dict:
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
    # Constraints zuerst (Schema, autocommit), dann Daten in Transaktions-Batches — bei
    # ganzen Sitzungen (zehntausende Statements) deutlich schneller als Autocommit je Statement.
    constraints = [s for s in stmts if s[0].startswith("CREATE CONSTRAINT")]
    writes = [s for s in stmts if not s[0].startswith("CREATE CONSTRAINT")]

    def _run_batch(tx, batch):
        for cypher, params in batch:
            tx.run(cypher, **params)

    try:
        with driver.session(database=database) as session:
            for cypher, params in constraints:
                session.run(cypher, **params)
            for i in range(0, len(writes), batch_size):
                session.execute_write(_run_batch, writes[i:i + batch_size])
        print(f"✓ Geladen nach {uri}/{database}: {n_nodes} Knoten, {n_rels} Beziehungen.")
    finally:
        driver.close()
    return {"statements": len(stmts), "nodes": n_nodes, "relationships": n_rels, "loaded": True}
