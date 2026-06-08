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
import re
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


# ── LLM-Verifizierer (Azure/OpenAI-kompatibel) ──────────────────────────────────
_LLM_DISCLAIMER = ("Automatische KI-Einschätzung (ungeprüft) — Vorschlag, kein Urteil; "
                   "vor Veröffentlichung von Menschen prüfen.")

_LLM_SYS = (
    "Du bist ein vorsichtiger, neutraler Faktenchecker für quantitative Tatsachenbehauptungen "
    "aus Bundestagsreden. Bewerte NUR überprüfbare Zahlen-/Faktenaussagen, keine Meinungen. "
    "Wenn du keine belastbare Quelle kennst oder unsicher bist, nutze 'unbelegt'. "
    "Verdikt-Skala: bestätigt | teilweise | irreführend | falsch | unbelegt. "
    "Nenne nach Möglichkeit eine amtliche Quelle (z. B. Destatis, Bundesregierung, Drucksache) "
    "mit URL. Antworte AUSSCHLIESSLICH als JSON: "
    '{"verdikt": "...", "begruendung": "...", "quelle_titel": "...", "quelle_url": "..."}')


def _extract_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    return json.loads(m.group(0)) if m else {}


def _extract_json_list(text: str) -> list:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    m = re.search(r"\[.*\]", text, re.DOTALL)
    return json.loads(m.group(0)) if m else []


_EXTRACT_SYS = (
    "Du bist ein vorsichtiger, neutraler Faktenchecker für Bundestagsreden. Finde im folgenden "
    "Redeausschnitt ÜBERPRÜFBARE quantitative Tatsachenbehauptungen (konkrete Zahlen, "
    "Statistiken, Vergleiche, Entwicklungen). IGNORIERE Meinungen, Wertungen, Appelle, Rhetorik "
    "und Verfahrensangaben (Tagesordnungspunkte, Redezeiten). Prüfe jede gefundene Behauptung "
    "nach bestem Wissen. Verdikt: bestätigt | teilweise | irreführend | falsch | unbelegt "
    "('unbelegt', wenn keine belastbare Quelle bekannt). Nenne möglichst eine amtliche Quelle "
    "(Destatis, Bundesregierung, Drucksache) mit URL. Antworte AUSSCHLIESSLICH als JSON-Liste: "
    '[{"aussage":"<wörtlich>","verdikt":"...","begruendung":"...","quelle_titel":"...",'
    '"quelle_url":"..."}]. Keine überprüfbare Behauptung gefunden → [].')


def factcheck_transcript_llm(passages: list[dict], *, model: str, base_url: str,
                             api_key: str, max_passages: int = 14) -> list[dict]:
    """Extrahiert ECHTE prüfbare Behauptungen aus Transkript-Abschnitten UND prüft sie per LLM.

    `passages`: [{text, utt_index, start}] (Abschnitt + Provenienz-Segmentindex/Startzeit).
    Liefert: [{aussage, verdikt, begruendung, quelle{titel,url,stand}, utt_index, start}].
    Verdikte über reale Personen sind KI-Vorschläge (ungeprüft, Disclaimer in begruendung).
    """
    from openai import OpenAI
    client = OpenAI(base_url=base_url, api_key=api_key)
    out: list[dict] = []
    for pas in passages[:max_passages]:
        try:
            resp = client.chat.completions.create(
                model=model, temperature=0, max_tokens=1400,
                messages=[{"role": "system", "content": _EXTRACT_SYS},
                          {"role": "user", "content": pas["text"][:4000]}])
            arr = _extract_json_list(resp.choices[0].message.content or "")
        except Exception:
            arr = []
        for item in arr if isinstance(arr, list) else []:
            claim = (item.get("aussage") or "").strip()
            if not claim:
                continue
            v = item.get("verdikt", "unbelegt")
            out.append({
                "aussage": claim, "verdikt": v if v in VERDIKTE else "unbelegt",
                "begruendung": f"{_LLM_DISCLAIMER} {(item.get('begruendung') or '').strip()}".strip(),
                "quelle": {"titel": item.get("quelle_titel") or "KI-Einschätzung (Mistral), ungeprüft",
                           "url": item.get("quelle_url", "") or "", "stand": ""},
                "utt_index": pas["utt_index"], "start": pas.get("start", 0.0)})
    return out


def factcheck_with_llm(aussagen: list[dict], *, model: str, base_url: str, api_key: str,
                       max_claims: int = 12) -> list["FactCheck"]:
    """Produktivpfad: LLM-Verifizierer (z. B. Azure Mistral-Large-3).

    GRUNDSATZ bleibt: jeder Faktencheck trägt eine Quelle. Über reale Personen sind die
    Verdikte ausdrücklich **KI-Vorschläge (ungeprüft)** mit Disclaimer — kein Urteil.
    """
    from openai import OpenAI
    client = OpenAI(base_url=base_url, api_key=api_key)
    results: list[FactCheck] = []
    for i, a in enumerate(aussagen[:max_claims]):
        try:
            resp = client.chat.completions.create(
                model=model, temperature=0, max_tokens=700,
                messages=[{"role": "system", "content": _LLM_SYS},
                          {"role": "user", "content": f'Aussage: "{a["text"]}"'}])
            data = _extract_json(resp.choices[0].message.content or "")
            verdikt = data.get("verdikt", "unbelegt")
            if verdikt not in VERDIKTE:
                verdikt = "unbelegt"
            quelle = {"titel": data.get("quelle_titel") or "KI-Einschätzung (Mistral), ungeprüft",
                      "url": data.get("quelle_url", "") or "", "stand": ""}
            begr = f"{_LLM_DISCLAIMER} {data.get('begruendung', '').strip()}".strip()
        except Exception as e:  # robuste Degradierung: nie ohne Quelle, nie Crash
            verdikt = "unbelegt"
            quelle = {"titel": "KI-Faktencheck nicht möglich", "url": "", "stand": ""}
            begr = f"{_LLM_DISCLAIMER} Automatische Prüfung fehlgeschlagen ({type(e).__name__})."
        results.append(FactCheck(
            aussage_index=i, text=a["text"], person=a.get("person"), fraktion=a.get("fraktion"),
            top_nummer=a.get("top_nummer"), verdikt=verdikt, begruendung=begr, quelle=quelle,
            quelle_utterances=a.get("quelle_utterances", []), score=0.0))
    assert all(fc.quelle for fc in results), "Faktencheck ohne Quelle — verletzt Grundsatz."
    return results
