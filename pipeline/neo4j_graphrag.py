"""
Neo4j GraphRAG — Retrieval-Augmented Generation über den Protokoll-Graphen mit
der **offiziellen Neo4j-Bibliothek `neo4j-graphrag`**.

Für unseren strukturierten Property-Graph ist **Text2Cypher** der passende
Retriever: eine natürlichsprachige Frage wird (schema- und beispielgestützt) in
Cypher übersetzt, gegen Neo4j ausgeführt, und die Treffer werden vom LLM zur
Antwort synthetisiert. Das ist der Produktivpfad zu `pipeline/graphrag.py`
(letzteres ist nur der offline-Demo-Router ohne Neo4j/LLM).

On-prem/DSGVO: `OpenAILLM` zeigt per `base_url` auf ein lokales,
OpenAI-kompatibles LLM (Ollama / vLLM) — kein Cloud-Versand.

Abhängigkeiten (nur Produktivpfad):  pip install neo4j-graphrag
"""

from __future__ import annotations

import os

# Schema-Beschreibung für Text2Cypher (Knoten-Labels + Beziehungen unseres Graphen).
NEO4J_SCHEMA = """
Node labels and key properties:
  (:Sitzung {id, gremium, datum, wahlperiode, sitzung_nr})
  (:Tagesordnungspunkt {id, nummer, label})
  (:Person {id, label, subtype /*Rolle*/})
  (:Fraktion {id, label})
  (:Redebeitrag {id, label, timecode})
  (:Aussage {id, text, person})                 // prüfbare Behauptung
  (:Faktencheck {id, verdikt, begruendung})     // verdikt: bestätigt|teilweise|irreführend|falsch|unbelegt
  (:Quelle {id, label, url, stand})
  (:Abstimmung {id, ja, nein, enthaltung, ergebnis})
  (:Beschluss {id, nummer, text})
  (:Aufgabe {id, zustaendig, frist})
  (:Frage {id, text})
  (:AkustischesEreignis {id, subtype /*Beifall|Zwischenruf|Lachen|Widerspruch|Missfallen*/, urheber, text})
  (:Norm {id, label})
  (:Transkriptsegment {id, sprecher, text, start_sec, timecode})

Relationships:
  (:Sitzung)-[:HAT_TOP]->(:Tagesordnungspunkt)
  (:Person)-[:MITGLIED_VON]->(:Fraktion)
  (:Person)-[:HAT_REDEBEITRAG]->(:Redebeitrag)-[:ZU_TOP]->(:Tagesordnungspunkt)
  (:Person)-[:TAETIGT_AUSSAGE]->(:Aussage)-[:GEPRUEFT_ALS]->(:Faktencheck)-[:BELEGT_MIT]->(:Quelle)
  (:Tagesordnungspunkt)-[:ENTSCHIEDEN_DURCH]->(:Abstimmung)-[:FUEHRT_ZU]->(:Beschluss)
  (:Beschluss)-[:ERZEUGT_AUFGABE]->(:Aufgabe)
  (:Tagesordnungspunkt)-[:HAT_REAKTION]->(:AkustischesEreignis)-[:REAKTION_AUF]->(:Redebeitrag)
  (:Person)-[:STELLT_FRAGE]->(:Frage)
  (anything)-[:BELEGT_DURCH]->(:Transkriptsegment)   // Provenienz
"""

# Few-Shot-Beispiele NL -> Cypher (Grundsatz: Faktencheck IMMER mit Quelle zurückgeben).
EXAMPLES = [
    "USER INPUT: 'Welche Aussagen sind falsch oder irreführend — mit Quelle?' "
    "QUERY: MATCH (p:Person)-[:TAETIGT_AUSSAGE]->(a:Aussage)-[:GEPRUEFT_ALS]->(f:Faktencheck)-[:BELEGT_MIT]->(q:Quelle) "
    "WHERE f.verdikt IN ['falsch','irreführend'] "
    "RETURN p.label AS person, a.text AS aussage, f.verdikt AS verdikt, f.begruendung AS begruendung, q.label AS quelle, q.url AS url",

    "USER INPUT: 'Wo gab es Beifall oder Zwischenrufe?' "
    "QUERY: MATCH (t:Tagesordnungspunkt)-[:HAT_REAKTION]->(e:AkustischesEreignis) "
    "OPTIONAL MATCH (e)-[:REAKTION_AUF]->(r:Redebeitrag) "
    "RETURN t.label AS top, e.subtype AS typ, e.urheber AS urheber, e.text AS wortlaut, r.label AS auf_redebeitrag",

    "USER INPUT: 'Welche Beschlüsse wurden mit welchem Ergebnis gefasst?' "
    "QUERY: MATCH (t:Tagesordnungspunkt)-[:ENTSCHIEDEN_DURCH]->(v:Abstimmung)-[:FUEHRT_ZU]->(b:Beschluss) "
    "RETURN b.nummer AS beschluss, b.text AS text, v.ja AS ja, v.nein AS nein, v.enthaltung AS enthaltung",

    "USER INPUT: 'Welche Zusagen mit Frist gibt es?' "
    "QUERY: MATCH (b:Beschluss)-[:ERZEUGT_AUFGABE]->(a:Aufgabe) "
    "RETURN a.zustaendig AS zustaendig, a.frist AS frist, b.nummer AS aus_beschluss",
]


def build_graphrag(*, uri: str | None = None, user: str | None = None,
                   password: str | None = None, llm_model: str | None = None,
                   llm_base_url: str | None = None, api_key: str | None = None):
    """Erzeugt eine GraphRAG-Instanz (Text2Cypher) gegen ein laufendes Neo4j.

    LLM-Defaults kommen aus der Umgebung (.env), OpenAI-kompatibel:
      • Azure AI Foundry: AZURE_AI_ENDPOINT (…/openai/v1) + AZURE_AI_API_KEY + MISTRAL_DEPLOYMENT
      • lokal on-prem:    llm_base_url='http://localhost:11434/v1' (Ollama/vLLM)
    """
    from neo4j import GraphDatabase
    from neo4j_graphrag.retrievers import Text2CypherRetriever
    from neo4j_graphrag.llm import OpenAILLM
    from neo4j_graphrag.generation import GraphRAG

    uri = uri or os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = user or os.environ.get("NEO4J_USER", "neo4j")
    password = password or os.environ.get("NEO4J_PASSWORD", "healthdataspace")
    driver = GraphDatabase.driver(uri, auth=(user, password))

    llm_model = llm_model or os.environ.get("MISTRAL_DEPLOYMENT") or "gpt-4o"
    llm_base_url = llm_base_url or os.environ.get("AZURE_AI_ENDPOINT")
    api_key = api_key or os.environ.get("AZURE_AI_API_KEY")
    llm_kwargs = {}
    if llm_base_url:
        llm_kwargs["base_url"] = llm_base_url
    if api_key:
        llm_kwargs["api_key"] = api_key
    # Kimi-K2.6 ist ein Reasoning-Modell → genug Token-Budget nach dem "Denken" lassen.
    llm = OpenAILLM(model_name=llm_model, model_params={"temperature": 0, "max_tokens": 4096},
                    **llm_kwargs)

    retriever = Text2CypherRetriever(
        driver=driver, llm=llm, neo4j_schema=NEO4J_SCHEMA, examples=EXAMPLES)
    rag = GraphRAG(retriever=retriever, llm=llm)
    return rag, driver


def answer(question: str, **kwargs) -> str:
    """Eine Frage über den Neo4j-GraphRAG beantworten.

    Grundsatz Faktencheck: Antworten zu Aussagen MÜSSEN die Quelle nennen — die
    Beispiele oben geben Verdikt + Quelle/URL zurück, sodass das LLM zitieren kann.
    """
    rag, driver = build_graphrag(**kwargs)
    try:
        resp = rag.search(
            query_text=question,
            retriever_config={"top_k": 25},
            return_context=True,
        )
        return resp.answer
    finally:
        driver.close()


if __name__ == "__main__":
    import sys
    try:  # .env (Azure-Endpoint/-Key, NEO4J_URI) laden, falls vorhanden
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass
    q = " ".join(sys.argv[1:]) or "Welche Aussagen sind falsch oder irreführend — mit Quelle?"
    print(answer(q))
