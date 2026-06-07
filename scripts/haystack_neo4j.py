#!/usr/bin/env python3
"""
Haystack (deepset) ↔ Neo4j — RAG-Pipeline über den echten Sitzungs-Graphen.

Pipeline:  Frage → Neo4jDynamicDocumentRetriever (Volltext über Transkriptsegmente)
                 → PromptBuilder → OpenAIGenerator (Azure Mistral-Large-3)  → Antwort mit Beleg.

So lassen sich die Reden inhaltlich durchsuchen und beantworten — komplementär zum
strukturierten Text2Cypher-GraphRAG (scripts/graphrag_compare.py).

  .venv/bin/python scripts/haystack_neo4j.py "Was wurde zur wirtschaftlichen Lage gesagt?"
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from dotenv import load_dotenv  # noqa: E402
load_dotenv(REPO / ".env")

from neo4j import GraphDatabase  # noqa: E402
from neo4j_haystack import Neo4jClientConfig, Neo4jDynamicDocumentRetriever  # noqa: E402
from haystack import Pipeline  # noqa: E402
from haystack.components.builders import PromptBuilder  # noqa: E402
from haystack.components.generators import OpenAIGenerator  # noqa: E402
from haystack.utils import Secret  # noqa: E402

URI = os.environ.get("NEO4J_URI", "bolt://localhost:7688")
USER = os.environ.get("NEO4J_USER", "neo4j")
PW = os.environ.get("NEO4J_PASSWORD", "healthdataspace")

FT_INDEX = "seg_volltext"
CYPHER = (
    f"CALL db.index.fulltext.queryNodes('{FT_INDEX}', $search_term) YIELD node, score "
    "WHERE node.text <> '' "
    "RETURN node.text AS content, node.sprecher AS sprecher, node.timecode AS timecode, score "
    "ORDER BY score DESC LIMIT $top_k"
)
PROMPT = """Beantworte die Frage AUSSCHLIESSLICH anhand der folgenden Auszüge aus echten
Bundestagsreden. Wenn die Auszüge nicht reichen, sage das. Nenne Sprecher:innen als Beleg.

{% for d in documents %}- ({{ d.meta.sprecher }}) {{ d.content }}
{% endfor %}
Frage: {{ question }}
Antwort:"""


def ensure_fulltext_index() -> None:
    drv = GraphDatabase.driver(URI, auth=(USER, PW))
    with drv.session() as s:
        s.run(f"CREATE FULLTEXT INDEX {FT_INDEX} IF NOT EXISTS "
              "FOR (n:Transkriptsegment) ON EACH [n.text]")
    drv.close()


def lucene_terms(question: str) -> str:
    words = [w for w in re.findall(r"\wäöüÄÖÜß+|\w+", question) if len(w) > 3]
    return " OR ".join(words) or question


def build_pipeline() -> Pipeline:
    cfg = Neo4jClientConfig(URI, database="neo4j", username=USER, password=PW)
    retriever = Neo4jDynamicDocumentRetriever(
        client_config=cfg, compose_doc_from_result=True, verify_connectivity=True)
    generator = OpenAIGenerator(
        api_key=Secret.from_env_var("AZURE_AI_API_KEY"),
        api_base_url=os.environ["AZURE_AI_ENDPOINT"],
        model=os.environ.get("MISTRAL_DEPLOYMENT", "Mistral-Large-3"),
        generation_kwargs={"max_tokens": 700, "temperature": 0.1})
    pipe = Pipeline()
    pipe.add_component("retriever", retriever)
    pipe.add_component("prompt", PromptBuilder(template=PROMPT, required_variables=["question"]))
    pipe.add_component("llm", generator)
    pipe.connect("retriever.documents", "prompt.documents")
    pipe.connect("prompt.prompt", "llm.prompt")
    return pipe


def main() -> int:
    question = " ".join(sys.argv[1:]) or "Was wurde zur wirtschaftlichen Lage und zu Energie gesagt?"
    ensure_fulltext_index()
    pipe = build_pipeline()
    terms = lucene_terms(question)
    print(f"Frage:  {question}\nVolltext-Terme: {terms}\n")
    res = pipe.run({
        "retriever": {"query": CYPHER, "parameters": {"search_term": terms, "top_k": 6}},
        "prompt": {"question": question},
    })
    docs = res.get("retriever", {}).get("documents") if "retriever" in res else None
    ans = res["llm"]["replies"][0]
    print("Antwort (Mistral-Large-3, RAG über Neo4j-Volltext):\n")
    print(ans.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
