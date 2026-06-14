#!/usr/bin/env python3
"""
Semantische Suche (Vektor-RAG) über den Sitzungs-Graphen — ergänzt Text2Cypher (struktur)
und Haystack-Volltext (Stichwort) um **Bedeutungsähnlichkeit**.

Schritte (idempotent):
  1) Embeddings (Azure `text-embedding-3-large`, 3072-dim) für alle Transkriptsegmente, die noch
     keins haben, berechnen und als Knoten-Property `embedding` speichern.
  2) Neo4j **native Vektor-Index** (Cosine) auf `Transkriptsegment.embedding` anlegen.
  3) Fragen über **VectorCypherRetriever** (neo4j-graphrag) beantworten: Frage → Query-Embedding
     → ähnlichste Redepassagen → Antwort (Azure Mistral) mit Sprecher-/Sitzungsbeleg.

  .venv/bin/python scripts/vector_search.py                       # Demo-Fragen
  .venv/bin/python scripts/vector_search.py "Was wurde zur Rente gesagt?"
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
from openai import OpenAI  # noqa: E402
from neo4j_graphrag.embeddings import OpenAIEmbeddings  # noqa: E402
from neo4j_graphrag.retrievers import VectorCypherRetriever  # noqa: E402
from neo4j_graphrag.llm import OpenAILLM  # noqa: E402
from neo4j_graphrag.generation import GraphRAG  # noqa: E402

URI = os.environ.get("NEO4J_URI", "bolt://localhost:7688")
AUTH = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", "healthdataspace"))
ENDPOINT = os.environ["AZURE_AI_ENDPOINT"]
KEY = os.environ["AZURE_AI_API_KEY"]
EMB_MODEL = os.environ.get("EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
DIM = int(os.environ.get("EMBEDDING_DIM", "3072"))
INDEX = "seg_embedding"

# Vektor-Treffer mit Sprecher + Sitzung anreichern (Provenienz bleibt erhalten).
RETRIEVAL_QUERY = """
WITH node, score
OPTIONAL MATCH (node)<-[:BELEGT_DURCH]-()-[:ZU_TOP]->(:Tagesordnungspunkt)<-[:HAT_TOP]-(s:Sitzung)
RETURN node.text AS text, node.sprecher AS sprecher,
       coalesce(s.sitzung_nr,'?') AS sitzung, score
"""

QUESTIONS = [
    "Was wurde über die wirtschaftliche Lage und Investitionen gesagt?",
    "Welche Aussagen gab es zu Energie und Versorgungssicherheit?",
]


def embed_missing(driver) -> int:
    client = OpenAI(base_url=ENDPOINT, api_key=KEY)
    with driver.session() as s:
        rows = [(r["id"], r["text"]) for r in s.run(
            "MATCH (n:Transkriptsegment) WHERE n.embedding IS NULL AND n.text <> '' "
            "RETURN id(n) AS id, n.text AS text")]
    if not rows:
        return 0
    print(f"   embedde {len(rows)} Segmente ({EMB_MODEL}) …")
    done = 0
    for i in range(0, len(rows), 64):
        chunk = rows[i:i + 64]
        for attempt in range(4):
            try:
                resp = client.embeddings.create(model=EMB_MODEL, input=[t for _, t in chunk])
                break
            except Exception as e:
                if attempt == 3:
                    raise
                time.sleep(8)  # Rate-Limit → kurz warten
        payload = [{"id": cid, "vec": d.embedding} for (cid, _), d in zip(chunk, resp.data)]
        with driver.session() as s:
            # embedding_model mitschreiben → Embedder-Wechsel erkennbar (ADR-0015, --reembed)
            s.run("UNWIND $rows AS r MATCH (n) WHERE id(n)=r.id "
                  "SET n.embedding = r.vec, n.embedding_model = $m", rows=payload, m=EMB_MODEL)
        done += len(chunk)
    return done


def reembed_stale(driver) -> int:
    """Vektoren eines ANDEREN Embedding-Modells verwerfen → werden neu berechnet (ADR-0015).
    Embeddings sind modell-/dim-gebunden; bei abweichender Dimension zusätzlich den
    Vektor-Index neu anlegen (DROP/CREATE)."""
    with driver.session() as s:
        r = s.run("MATCH (n:Transkriptsegment) WHERE n.embedding IS NOT NULL AND "
                  "coalesce(n.embedding_model,'?') <> $m SET n.embedding = NULL "
                  "RETURN count(n) AS c", m=EMB_MODEL).single()
    return r["c"] if r else 0


def ensure_index(driver) -> None:
    with driver.session() as s:
        s.run(f"CREATE VECTOR INDEX {INDEX} IF NOT EXISTS "
              "FOR (n:Transkriptsegment) ON n.embedding "
              "OPTIONS {indexConfig: {`vector.dimensions`: $dim, "
              "`vector.similarity_function`: 'cosine'}}", dim=DIM)
        # Index online abwarten
        for _ in range(20):
            st = s.run("SHOW INDEXES YIELD name, state WHERE name=$n RETURN state",
                       n=INDEX).single()
            if st and st["state"] == "ONLINE":
                break
            time.sleep(1)


def main() -> int:
    reembed = "--reembed" in sys.argv
    driver = GraphDatabase.driver(URI, auth=AUTH)
    print(f"Neo4j: {URI}  ·  Embedding: {EMB_MODEL} ({DIM}d)\n")
    if reembed:
        stale = reembed_stale(driver)
        print(f"   --reembed: {stale} Embeddings anderer Modelle verworfen → Neuberechnung")
    n = embed_missing(driver)
    ensure_index(driver)
    print(f"✓ {n} neue Embeddings | Vektor-Index '{INDEX}' bereit\n")

    embedder = OpenAIEmbeddings(model=EMB_MODEL, api_key=KEY, base_url=ENDPOINT)
    llm = OpenAILLM(model_name=os.environ.get("MISTRAL_DEPLOYMENT", "Mistral-Large-3"),
                    api_key=KEY, base_url=ENDPOINT,
                    model_params={"temperature": 0.1, "max_tokens": 700})
    retr = VectorCypherRetriever(driver=driver, index_name=INDEX,
                                 retrieval_query=RETRIEVAL_QUERY, embedder=embedder)
    rag = GraphRAG(retriever=retr, llm=llm)

    questions = [a for a in sys.argv[1:] if not a.startswith("--")] or QUESTIONS
    for q in (questions if isinstance(questions, list) else [questions]):
        print("═" * 78 + f"\n❓ {q}\n")
        resp = rag.search(query_text=q, retriever_config={"top_k": 6}, return_context=True)
        print("Antwort (Vektor-RAG, Mistral-Large-3):")
        print(resp.answer.strip()[:700])
        items = resp.retriever_result.items if resp.retriever_result else []
        print(f"\n   Belege ({len(items)} ähnlichste Passagen):")
        for it in items[:3]:
            print(f"     • {str(it.content)[:140]}")
        print()
    driver.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
