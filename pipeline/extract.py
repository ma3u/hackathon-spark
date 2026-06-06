"""
Extraktion — sprecher-attribuierte Utterances -> strukturiertes Protokoll.

Dies ist der Schritt, an dem aus Rohtext verwertbare Verwaltungsinformation wird:
Tagesordnungspunkte, Anträge, Abstimmungen, Beschlüsse, Befangenheiten, Aufgaben.

Produktivpfad (extract_with_llm): ein lokales/EU-gehostetes LLM mit
Structured-Output (JSON-Schema-Constraint). Der Prompt unten ist der reale Prompt.
Jede extrahierte Aussage trägt die Indizes ihrer Quell-Utterances -> Provenienz
bis zum Audio-Zeitstempel (entscheidend für Rechtsverbindlichkeit/Prüfbarkeit).

Demopfad (extract_rule_based): deterministische Muster-Extraktion ohne LLM,
damit der Prototyp überall reproduzierbar läuft und die Zielstruktur zeigt.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .align import Utterance

EXTRACTION_PROMPT = """\
Du bist Protokollassistent einer deutschen Kommunalverwaltung. Extrahiere aus dem
sprecher-attribuierten Sitzungsmitschnitt ein strukturiertes Protokoll als JSON nach
folgendem Schema. Erfinde nichts; wenn eine Information fehlt, lass das Feld leer.
Gib zu JEDER Entität die `quelle_utterances` (Liste von Segment-Indizes) an.

Schema:
  meeting:        {gremium, datum, ort, beschlussfaehig:bool, rechtsgrundlage}
  tops:           [{nummer:int, titel}]
  antraege:       [{top_nummer:int, steller, text}]
  abstimmungen:   [{top_nummer:int, ja:int, nein:int, enthaltung:int, ergebnis}]
  beschluesse:    [{nummer, top_nummer:int, text}]
  befangenheiten: [{person, top_nummer:int, rechtsgrundlage}]
  aufgaben:       [{beschluss_nummer, text, zustaendig, frist}]

Mitschnitt:
{transcript}
"""


@dataclass
class Protocol:
    meeting: dict = field(default_factory=dict)
    tops: list[dict] = field(default_factory=list)
    antraege: list[dict] = field(default_factory=list)
    abstimmungen: list[dict] = field(default_factory=list)
    beschluesse: list[dict] = field(default_factory=list)
    befangenheiten: list[dict] = field(default_factory=list)
    aufgaben: list[dict] = field(default_factory=list)
    redebeitraege: list[dict] = field(default_factory=list)
    aussagen: list[dict] = field(default_factory=list)   # prüfbare Behauptungen (Faktencheck)
    fragen: list[dict] = field(default_factory=list)      # Fragen an die Bundesregierung
    kommentare: list[dict] = field(default_factory=list)  # Saalreaktionen (Beifall/Zuruf/Lachen)
    utterances: list[Utterance] = field(default_factory=list)


def _is_member(u: Utterance) -> bool:
    """Redner mit Beitragsrecht (kein Sitzungsvorsitz/Schriftführer)."""
    rolle = u.rolle or ""
    return not any(k in rolle for k in ("Vorsitz", "räsident", "Schriftführer", "Sitzungsleitung"))


def _split_sentences(text: str) -> list[str]:
    """Satztrennung, die deutsche Datums-/Ordnungszahlen ('30. Juni') nicht zerreißt."""
    parts = re.split(r"(?<=[.!?])\s+", text)
    merged: list[str] = []
    for part in parts:
        if merged and re.search(r"\b\d{1,2}\.$", merged[-1]):  # vorheriges endet auf "30."
            merged[-1] += " " + part
        else:
            merged.append(part)
    return [m.strip() for m in merged if m.strip()]


def _is_checkable(sentence: str) -> bool:
    """Heuristik: prüfbare Größe vorhanden — aber keine Zusage/Absichtserklärung."""
    s = sentence.lower()
    if re.search(r"vorlegen|vorzulegen|wird .* vorle", s):  # Zusage -> Aufgabe, kein Faktum
        return False
    has_quant = bool(re.search(r"\d", s)) or "prozent" in s or re.search(r"von (drei|vier|fünf)", s)
    return bool(has_quant)


def extract_with_llm(utterances: list[Utterance], *, model: str = "local-llm") -> Protocol:
    """Produktivpfad: LLM-gestützte Extraktion mit erzwungenem JSON-Schema."""
    raise NotImplementedError(
        "Produktivpfad: EXTRACTION_PROMPT an ein lokales LLM (z. B. via Ollama/vLLM) "
        "mit response_format=json_schema senden und das JSON in ein Protocol mappen."
    )


# ── Demopfad: deterministische Muster-Extraktion ────────────────────────────────

_NUM = {
    "null": 0, "keine": 0, "eine": 1, "ein": 1, "zwei": 2, "drei": 3, "vier": 4,
    "fünf": 5, "sechs": 6, "sieben": 7, "acht": 8, "neun": 9, "zehn": 10,
}


def _word_to_int(token: str) -> int | None:
    token = token.lower().strip(".,")
    if token.isdigit():
        return int(token)
    return _NUM.get(token)


def extract_rule_based(utterances: list[Utterance]) -> Protocol:
    p = Protocol(utterances=utterances)
    current_top: int | None = None

    for idx, u in enumerate(utterances):
        t = u.text

        # Eröffnung / Beschlussfähigkeit / Rechtsgrundlage
        if "eröffne" in t.lower() and "sitzung" in t.lower():
            datum = _search(r"am\s+([\d]{1,2}\.\s*\w+\s*\d{4})", t)
            p.meeting.update(
                gremium="Gemeinderat Musterbach",
                datum=datum or "2026-05-12",
                ort="Rathaus Musterbach, Sitzungssaal",
                beschlussfaehig="beschlussfähig" in t.lower(),
                rechtsgrundlage=_search(r"(Paragraph\s+\d+\s+der\s+Gemeindeordnung)", t) or "GemO",
                quelle_utterances=[idx],
            )

        # Tagesordnungspunkt erkennen (Gemeinderat "Tagesordnungspunkt 3: …" und
        # Bundestag "Ich rufe Tagesordnungspunkt 7 auf: …") + als aktuellen TOP merken
        m = re.search(r"Tagesordnungspunkt\s+(\d+)\s*(?:auf)?\s*[:,]?\s*(.*?)(?:\.|$)", t)
        if m:
            current_top = int(m.group(1))
            titel = re.sub(r"^auf[:.]?\s*", "", m.group(2).strip()).split(".")[0]
            if not any(x["nummer"] == current_top for x in p.tops):
                p.tops.append({"nummer": current_top, "titel": titel, "quelle_utterances": [idx]})

        # Redebeitrag (inhaltliche Wortmeldung eines Mitglieds/Regierungsvertreters zu einem TOP)
        if _is_member(u) and current_top is not None:
            p.redebeitraege.append(
                {"person": u.speaker_name, "fraktion": u.fraktion, "top_nummer": current_top,
                 "start": u.start, "timecode": u.timecode, "quelle_utterances": [idx]}
            )

            # Prüfbare Aussagen aus dem Redebeitrag herauslösen (für den Faktencheck)
            for sent in _split_sentences(t):
                if _is_checkable(sent) and "frage" not in sent.lower():
                    p.aussagen.append(
                        {"text": sent, "person": u.speaker_name, "fraktion": u.fraktion,
                         "top_nummer": current_top, "quelle_utterances": [idx]})

            # Frage an die Bundesregierung ("Ich frage die Bundesregierung: …")
            fm = re.search(r"frage die Bundesregierung[:,]?\s*(.*?)(?:$)", t, re.IGNORECASE)
            if fm:
                p.fragen.append(
                    {"steller": u.speaker_name, "fraktion": u.fraktion, "top_nummer": current_top,
                     "text": fm.group(1).strip(), "quelle_utterances": [idx]})

        # Antrag erkennen ("beantrag...")
        if "beantrag" in t.lower() and current_top is not None:
            p.antraege.append(
                {"top_nummer": current_top, "steller": u.fraktion or u.speaker_name,
                 "text": t.strip(), "quelle_utterances": [idx]}
            )

        # Befangenheit (§18 GemO) — nur Selbsterklärung zählt, nicht die Ankündigung
        # durch den Vorsitz ("Herr X nimmt wegen Befangenheit nicht teil").
        tl = t.lower()
        if ("erkläre mich" in tl or "für befangen" in tl) and current_top is not None:
            p.befangenheiten.append(
                {"person": u.speaker_name, "top_nummer": current_top,
                 "rechtsgrundlage": _search(r"(Paragraph\s+\d+\s+der\s+Gemeindeordnung)", t) or "§18 GemO",
                 "quelle_utterances": [idx]}
            )

        # Abstimmungsergebnis ("X Jastimmen, Y Gegenstimmen, Z Enthaltung")
        if "jastimmen" in t.lower() or ("gegenstimme" in t.lower() and "enthaltung" in t.lower()):
            ja = _count_before(t, r"(\w+)\s+Jastimmen?")
            nein = _count_before(t, r"(\w+)\s+(?:Gegenstimmen?|Neinstimmen?)")
            enth = _count_before(t, r"(\w+)\s+Enthaltung")
            ergebnis = "angenommen" if "angenommen" in t.lower() else (
                "abgelehnt" if "abgelehnt" in t.lower() else "offen")
            if current_top is not None:
                p.abstimmungen.append(
                    {"top_nummer": current_top, "ja": ja, "nein": nein, "enthaltung": enth,
                     "ergebnis": ergebnis, "quelle_utterances": [idx]}
                )

        # Beschluss erkennen ("Beschluss 2026-014 ...")
        for bm in re.finditer(r"Beschluss\s+(\d{4}-\d{3})\s*[:,]?\s*(.*?)(?:$)", t):
            nummer = bm.group(1)
            text = re.sub(r"^(?:ist\s+)?gefasst\s*[:.]?\s*", "", bm.group(2).strip(), flags=re.IGNORECASE)
            if not any(b["nummer"] == nummer for b in p.beschluesse):
                p.beschluesse.append(
                    {"nummer": nummer, "top_nummer": current_top, "text": text,
                     "quelle_utterances": [idx]}
                )
            # Aufgabe/Auftrag an die Verwaltung mit Frist im selben Beschluss
            if "beauftragt" in text.lower() or "vorzulegen" in text.lower():
                frist = _search(r"bis zur\s+(Sitzung am\s+[\d]{1,2}\.\s*\w+\s*\d{4})", text) \
                    or _search(r"bis zum\s+([\d]{1,2}\.\s*\w+\s*\d{4})", text)
                zustaendig = _search(r"Zuständig ist (?:das|die|der)\s+([\wäöü]+)", text) or "Verwaltung"
                p.aufgaben.append(
                    {"beschluss_nummer": nummer,
                     "text": "Finanzierungskonzept / beauftragte Vorlage",
                     "zustaendig": zustaendig, "frist": frist or "nächste Sitzung",
                     "quelle_utterances": [idx]}
                )

        # Generische Zusage mit Frist (z. B. Antwort der Bundesregierung "wird … bis
        # zum 30. Juni 2026 … schriftlich vorlegen") — außerhalb formaler Beschlüsse.
        if ("vorlegen" in tl or "vorzulegen" in tl) and not re.search(r"Beschluss\s+\d{4}-\d{3}", t):
            frist = _search(r"bis zum\s+([\d]{1,2}\.\s*\w+\s*\d{4})", t) \
                or _search(r"bis zur\s+(Sitzung am\s+[\d]{1,2}\.\s*\w+\s*\d{4})", t)
            if frist:
                zustaendig = "Bundesregierung" if "bundesregierung" in tl else (
                    u.fraktion or u.speaker_name)
                p.aufgaben.append(
                    {"beschluss_nummer": None, "text": "Zugesagte schriftliche Vorlage",
                     "zustaendig": zustaendig, "frist": frist, "top_nummer": current_top,
                     "quelle_utterances": [idx]})
    return p


def _search(pattern: str, text: str) -> str | None:
    m = re.search(pattern, text)
    return m.group(1).strip() if m else None


def _count_before(text: str, pattern: str) -> int:
    m = re.search(pattern, text, re.IGNORECASE)
    return _word_to_int(m.group(1)) or 0 if m else 0
