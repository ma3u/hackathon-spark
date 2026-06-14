#!/usr/bin/env python3
"""
Erzeugt eine KURZE Hackathon-Bewerbung (Challenge 2) per Azure-LLM (Mistral-Large-3, .env),
faktenbasiert: warum der GraphRAG-Ansatz besser ist als SPARKs Vektor-RAG.

Schreibt docs/bewerbung-challenge2-graphrag.md (KI-Entwurf — vor Einreichung von Menschen
prüfen; Fakten unten werden dem Modell vorgegeben, nichts erfinden lassen).

  python scripts/gen_bewerbung.py            # nutzt AZURE_AI_ENDPOINT/_API_KEY + MISTRAL_DEPLOYMENT
"""

from __future__ import annotations

import os
import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(REPO / ".env")
except ModuleNotFoundError:
    pass

FAKTEN = """
Projekt: graph-protokoll (SPARK-Hackathon Challenge 2 „Da geht noch mehr!").
Neue Verwaltungs-/Parlamentsleistung jenseits Planung/Genehmigung:
Gremien-/Plenarprotokoll oder Sitzungsmitschnitt -> prüfbarer Knowledge Graph + Faktencheck + Dashboard.
Echtdaten: ALLE 81 WP21-Plenarprotokolle + WP20/214 in Neo4j (~136.000 Knoten / ~361.000 Beziehungen).
56/81 Sitzungen zusätzlich mit YouTube-Clips über die offizielle YouTube Data API v3 (377 Clips).
Aggregat-Dashboard über alle Sitzungen: Themen, Redner:innen, Faktencheck-Bilanz, Trends, Fun Facts.
Retrieval: Neo4j GraphRAG (Text2Cypher) + Graph Data Science (PageRank/Louvain) + Haystack-Volltext + Vektor-Suche
  -> drei komplementäre Wege über DENSELBEN Graphen.
Provenienz bis zur Audio-Sekunde: jede Aussage/jeder Beschluss -> BELEGT_DURCH -> Transkriptsegment.start_sec
  -> im Streitfall per Klick nachhörbar (Rechtsverbindlichkeit). Bei amtlichem XML zusätzlich Mediathek-Video-Deeplink je Rede.
Faktencheck: Verdikt-Skala bestätigt/teilweise/irreführend/falsch/unbelegt; JEDER Faktencheck trägt eine Quelle;
  „unbelegt" ist nicht „falsch". Über reale Personen ausdrücklich KI-Vorschlag (ungeprüft) mit Disclaimer + Mensch-im-Loop.
On-prem/DSGVO: Whisper + Diarisierung + LLM im Behördennetz (Stimmen = biometrische Daten, Art. 9 DSGVO); LLM über OpenAI-kompatiblen Endpoint.
Barrierefreiheit: lineare Vorlesefassung (Screenreader/TTS) inkl. verbalisierter Saalreaktionen. Lizenz EUPL-1.2 (Public Money - Public Code).
Dep-freie Demo (nur Python-Stdlib) für CI/Offline; schwerer Produktivpfad lazy.

SPARK Workflow (BMDS): Python/FastAPI, Temporal, Postgres, MinIO/S3, Elasticsearch, Qdrant (= Vektor-RAG),
  Docling (PDF/DOCX), LiteLLM/vLLM. KEIN Knowledge Graph, KEIN Neo4j, KEIN GraphRAG, KEINE Ontologie (geprüft).
Verhältnis: keine Code-Abhängigkeit; geteilt werden Mission, Lizenz, On-prem-LLM-Muster.

Warum GraphRAG hier besser ist als reines Vektor-RAG:
- Protokollfragen sind MEHRHOP und STRUKTURIERT, z. B. „Welcher Beschluss mit welchem Abstimmungsergebnis?"
  (Beschluss -FUEHRT_ZU-> Abstimmung), „Wer war befangen nach welcher Norm?" (Person -BEFANGEN_BEI-> TOP, -BEFANGENHEIT_NACH-> Norm).
  Ein Embedding-Index über Textchunks kann solche Beziehungspfade nicht traversieren.
- Graph liefert exakte, erklärbare Pfade + Provenienz bis zur Audiosekunde statt unscharfer Chunk-Ähnlichkeit.
- Über denselben Graphen zusätzlich Vektor- und Volltext-Retrieval + Graph-Analytik (GDS).
- graph-protokoll ergänzt den SPARK-Baukasten um zwei generische Bausteine: ASR-als-Eingabe und Graph+Faktencheck-mit-Provenienz.
"""

SYSTEM = ("Du bist ein präziser technischer Autor für eine deutsche Behörden-Hackathon-Jury (BMDS SPARK). "
          "Schreibe sachlich, konkret, ohne Marketing-Floskeln und ohne Übertreibung. Nutze AUSSCHLIESSLICH "
          "die gelieferten Fakten, erfinde nichts (keine erfundenen Zahlen/Namen). Deutsch.")
USER = ("Schreibe eine KURZE Hackathon-Bewerbung (max. ~380 Wörter) für die SPARK Challenge 2 "
        "„Da geht noch mehr!\". Struktur: (1) Problem & Leistung in 2-3 Sätzen, (2) Lösung "
        "graph-protokoll, (3) Abschnitt „Warum GraphRAG besser ist als SPARKs Vektor-RAG\" mit "
        "2-3 konkreten Mehrhop-Beispielen, (4) ein Satz Verhältnis zu SPARK (Ergänzung, nicht "
        "Konkurrenz), (5) Schlusssatz. Markdown, knappe Überschriften, keine Code-Fences ums Ganze. "
        "Fakten:\n" + FAKTEN)


def main() -> int:
    from openai import OpenAI  # lazy: Produktivpfad
    base = os.environ["AZURE_AI_ENDPOINT"]
    key = os.environ["AZURE_AI_API_KEY"]
    model = os.environ.get("MISTRAL_DEPLOYMENT", "Mistral-Large-3")
    client = OpenAI(base_url=base, api_key=key)
    resp = client.chat.completions.create(
        model=model, temperature=0.4, max_tokens=1400,
        messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": USER}])
    text = resp.choices[0].message.content.strip().strip("`")
    out = REPO / "docs" / "bewerbung-challenge2-graphrag.md"
    header = (f"<!-- KI-Entwurf: erzeugt mit Azure AI Foundry ({model}) via .env, "
              f"scripts/gen_bewerbung.py. Faktenbasiert — vor Einreichung von Menschen prüfen. -->\n\n")
    out.write_text(header + text + "\n", encoding="utf-8")
    print(f"✓ {out.relative_to(REPO)}  (Modell {model}, {len(text)} Zeichen)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
