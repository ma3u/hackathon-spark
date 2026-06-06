"""
Faktencheck — prüfbare Aussagen aus Reden gegen eine Evidenzbasis verifizieren.

Genau hier liegt der Mehrwert im Bundestags-Kontext: Plenarreden enthalten
quantitative Behauptungen ("über 150.000 Ladepunkte", "seit 2021 nicht erhöht"),
die gegen amtliche Quellen geprüft werden müssen. Das Ergebnis ist ein Verdikt
(bestätigt / teilweise / irreführend / falsch / unbelegt) MIT Quelle und mit
Rückverweis auf den Audio-Zeitstempel der Aussage.

Produktivpfad (factcheck_with_retrieval): Dense Retrieval über einen Korpus
amtlicher Quellen (Destatis, Antworten der Bundesregierung, Drucksachen via
DIP-API) + LLM-Verifizierer im NLI-Stil (entailment/contradiction) mit Zitaten.

Demopfad (factcheck_rule_based): deterministischer Abgleich gegen eine kleine,
fiktive Evidenz-JSON über Schlüsselbegriff-Überlappung — reproduzierbar ohne Netz.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

VERDIKTE = {
    "bestätigt": "✅ bestätigt",
    "teilweise": "🟡 teilweise zutreffend",
    "irreführend": "🟠 irreführend",
    "falsch": "❌ falsch",
    "unbelegt": "⚪ unbelegt",
}


@dataclass
class FactCheck:
    aussage_index: int
    text: str
    person: str
    fraktion: str | None
    top_nummer: int | None
    verdikt: str
    begruendung: str
    quelle: dict | None
    quelle_utterances: list[int]
    score: float


def factcheck_with_retrieval(aussagen: list[dict], corpus) -> list[FactCheck]:
    """Produktivpfad: Retrieval + LLM-NLI-Verifizierer. Hier als Vertrag dokumentiert."""
    raise NotImplementedError(
        "Produktiv: pro Aussage Top-k Belege retrieven (Embeddings über amtlichen "
        "Korpus), dann LLM-Verifizierer (entailment/contradiction) mit Zitatpflicht."
    )


def factcheck_rule_based(aussagen: list[dict], evidenz_path: str | Path) -> list[FactCheck]:
    doc = json.loads(Path(evidenz_path).read_text(encoding="utf-8"))
    evidenz = doc["evidenz"]
    # Korpus-Referenz: GRUNDSATZ — jeder Faktencheck trägt eine Quelle. Auch ein
    # "unbelegt" verweist nachvollziehbar darauf, WOGEGEN (und mit welchem Stand)
    # geprüft wurde. Eine Aussage ohne Quelle gibt es nicht.
    korpus_quelle = {
        "titel": "Evidenzkorpus durchsucht — kein Beleg gefunden",
        "stand": doc.get("stand", ""),
        "url": doc.get("korpus_url", "https://dip.bundestag.de/"),
    }
    results: list[FactCheck] = []
    for i, a in enumerate(aussagen):
        text = a["text"].lower()
        best, best_score = None, 0.0
        for e in evidenz:
            keys = [k.lower() for k in e["schluesselbegriffe"]]
            score = sum(1 for k in keys if k in text) / max(len(keys), 1)
            if score > best_score:
                best, best_score = e, score
        if best and best_score >= 0.6:
            results.append(FactCheck(
                aussage_index=i, text=a["text"], person=a["person"], fraktion=a.get("fraktion"),
                top_nummer=a.get("top_nummer"), verdikt=best["verdikt"],
                begruendung=best["begruendung"], quelle=best["quelle"],
                quelle_utterances=a.get("quelle_utterances", []), score=round(best_score, 2)))
        else:
            results.append(FactCheck(
                aussage_index=i, text=a["text"], person=a["person"], fraktion=a.get("fraktion"),
                top_nummer=a.get("top_nummer"), verdikt="unbelegt",
                begruendung=(f"Gegen den Evidenzkorpus (Stand {korpus_quelle['stand']}) geprüft; "
                             "kein Beleg gefunden. 'Unbelegt' bedeutet nicht 'falsch'."),
                quelle=korpus_quelle, quelle_utterances=a.get("quelle_utterances", []),
                score=round(best_score, 2)))
    # Invariante absichern: kein Faktencheck ohne Quelle.
    assert all(fc.quelle for fc in results), "Faktencheck ohne Quelle — verletzt Grundsatz."
    return results
