#!/usr/bin/env python3
"""
GraphRAG-Modellvergleich: **Mistral-Large-3** vs. **Kimi-K2.6** (Azure AI Foundry) über die
offizielle **neo4j-graphrag**-Bibliothek (Text2Cypher) gegen den echten Sitzungs-Graphen.

Jede natürliche Frage wird vom LLM in Cypher übersetzt, gegen Neo4j ausgeführt und zur Antwort
synthetisiert. Verglichen werden je Modell: erzeugtes Cypher, Trefferzahl, Antwort, Laufzeit.

  .venv/bin/python scripts/graphrag_compare.py            # liest .env (Azure-Key, NEO4J_URI)
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from dotenv import load_dotenv  # noqa: E402
load_dotenv(REPO / ".env")

from neo4j import GraphDatabase  # noqa: E402
from neo4j_graphrag.retrievers import Text2CypherRetriever  # noqa: E402
from neo4j_graphrag.llm import OpenAILLM  # noqa: E402
from neo4j_graphrag.generation import GraphRAG  # noqa: E402
from pipeline.neo4j_graphrag import NEO4J_SCHEMA, EXAMPLES  # noqa: E402

# Zusätzliche, sitzungsübergreifende Few-Shots (für beide Modelle identisch → fairer Vergleich)
CROSS_EXAMPLES = EXAMPLES + [
    "USER INPUT: 'Welche Abgeordneten sprachen in mehreren Sitzungen?' "
    "QUERY: MATCH (p:Person)-[:HAT_REDEBEITRAG]->(:Redebeitrag)-[:ZU_TOP]->(:Tagesordnungspunkt)"
    "<-[:HAT_TOP]-(s:Sitzung) WITH p, count(DISTINCT s) AS sitzungen, count(*) AS reden "
    "WHERE sitzungen > 1 RETURN p.label AS person, sitzungen, reden ORDER BY reden DESC LIMIT 10",
    "USER INPUT: 'Wie viele Saalreaktionen gab es pro Sitzung?' "
    "QUERY: MATCH (s:Sitzung)-[:HAT_TOP]->(:Tagesordnungspunkt)-[:HAT_REAKTION]->(e:AkustischesEreignis) "
    "RETURN s.sitzung_nr AS sitzung, count(e) AS reaktionen ORDER BY sitzung",
]

QUESTIONS = [
    "Welche Abgeordneten sprachen in allen drei Sitzungen? Top 5 nach Anzahl Reden.",
    "Wie viele Saalreaktionen gab es pro Sitzung?",
    "Welche Fraktion erhielt den meisten Beifall auf ihre Redebeiträge?",
]


def make_rag(driver, deployment: str):
    llm = OpenAILLM(
        model_name=deployment,
        api_key=os.environ["AZURE_AI_API_KEY"],
        base_url=os.environ["AZURE_AI_ENDPOINT"],
        model_params={"temperature": 0, "max_tokens": 4096},  # Kimi denkt → genug Budget
    )
    retr = Text2CypherRetriever(driver=driver, llm=llm,
                                neo4j_schema=NEO4J_SCHEMA, examples=CROSS_EXAMPLES)
    return GraphRAG(retriever=retr, llm=llm)


def main() -> int:
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7688")
    driver = GraphDatabase.driver(
        uri, auth=(os.environ.get("NEO4J_USER", "neo4j"), os.environ["NEO4J_PASSWORD"]))
    models = {"Mistral-Large-3": os.environ.get("MISTRAL_DEPLOYMENT", "Mistral-Large-3"),
              "Kimi-K2.6": os.environ.get("KIMI_DEPLOYMENT", "Kimi-K2.6")}
    print(f"Neo4j: {uri}  ·  Azure: {os.environ['AZURE_AI_ENDPOINT']}\n")

    for q in QUESTIONS:
        print("═" * 78)
        print(f"❓ {q}\n")
        for label, dep in models.items():
            rag = make_rag(driver, dep)
            t = time.time()
            try:
                resp = rag.search(query_text=q, return_context=True)
                rr = resp.retriever_result
                cypher = (rr.metadata or {}).get("cypher", "—") if rr else "—"
                n = len(rr.items) if rr else 0
                print(f"── {label}  ({time.time()-t:.1f}s, {n} Treffer)")
                print(f"   Cypher: {' '.join(cypher.split())[:240]}")
                print(f"   Antwort: {resp.answer.strip()[:360]}\n")
            except Exception as e:
                print(f"── {label}: ❌ {repr(e)[:220]}\n")
    driver.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
