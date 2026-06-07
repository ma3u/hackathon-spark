#!/usr/bin/env python3
"""
Graph Data Science (GDS) auf den echten Sitzungen — Algorithmen für Einsichten, die reine
Cypher-Abfragen nicht liefern: zentrale Sprecher (PageRank), Sprecher-Communities (Louvain),
Aktivität (Degree). Läuft gegen das lokale Neo4j mit GDS-Plugin (siehe docker-compose).

  NEO4J_URI=bolt://localhost:7688 .venv/bin/python scripts/gds_analysis.py

Projektion: monopartiter „Mitsprache-Graph" — zwei Abgeordnete sind verbunden, wenn sie unter
demselben Tagesordnungspunkt gesprochen haben (Kantengewicht = Anzahl gemeinsamer TOPs).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
try:
    from dotenv import load_dotenv
    load_dotenv(REPO / ".env")
except Exception:
    pass

from graphdatascience import GraphDataScience  # noqa: E402

URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", "healthdataspace"))
GRAPH = "speakers"

NODE_Q = "MATCH (p:Person) RETURN id(p) AS id"
REL_Q = (
    "MATCH (p1:Person)-[:HAT_REDEBEITRAG]->(:Redebeitrag)-[:ZU_TOP]->(t:Tagesordnungspunkt)"
    "<-[:ZU_TOP]-(:Redebeitrag)<-[:HAT_REDEBEITRAG]-(p2:Person) "
    "WHERE id(p1) < id(p2) "
    "RETURN id(p1) AS source, id(p2) AS target, count(DISTINCT t) AS weight"
)


def main() -> int:
    gds = GraphDataScience(URI, auth=AUTH)
    print(f"GDS {gds.version()}  ·  {URI}\n")
    labels = {int(r["id"]): r["label"] for _, r in
              gds.run_cypher("MATCH (p:Person) RETURN id(p) AS id, p.label AS label").iterrows()}

    if gds.graph.exists(GRAPH)["exists"]:
        gds.graph.drop(GRAPH)
    G, _ = gds.graph.project.cypher(GRAPH, NODE_Q, REL_Q)
    print(f"Mitsprache-Graph: {G.node_count()} Abgeordnete, {G.relationship_count()} Kanten\n")

    print("① PageRank — zentralste Sprecher (wer mit vielen/aktiven anderen Themen teilt):")
    pr = (gds.pageRank.stream(G, relationshipWeightProperty="weight")
          .sort_values("score", ascending=False).head(10))
    for _, r in pr.iterrows():
        print(f"   {labels.get(int(r['nodeId']), '?'):28} {r['score']:.3f}")

    print("\n② Degree — aktivste Vernetzung (meiste Mitsprache-Partner):")
    deg = (gds.degree.stream(G).sort_values("score", ascending=False).head(10))
    for _, r in deg.iterrows():
        print(f"   {labels.get(int(r['nodeId']), '?'):28} {int(r['score'])} Partner")

    print("\n③ Louvain — Sprecher-Communities (Themen-/Fraktions-Cluster):")
    lou = gds.louvain.stream(G, relationshipWeightProperty="weight")
    sizes = lou.groupby("communityId").size().sort_values(ascending=False)
    print(f"   {lou['communityId'].nunique()} Communities; größte:")
    for cid, n in sizes.head(5).items():
        members = [labels.get(int(r["nodeId"]), "?") for _, r in
                   lou[lou["communityId"] == cid].head(4).iterrows()]
        print(f"     #{cid}: {n} Mitglieder — z. B. {', '.join(members)}")

    gds.graph.drop(GRAPH)
    gds.close()
    print("\n✓ GDS-Analyse fertig (Projektion wieder gelöscht).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
