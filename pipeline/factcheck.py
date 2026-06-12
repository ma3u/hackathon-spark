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


_STOP = set((
    "der die das den dem des ein eine einer und oder aber auch ist sind war hat haben wird werden "
    "für von mit auf in im an als nicht sich seit über unter bei zu zur zum vom durch dass weil wenn "
    "dann hier wir sie er es ich man dieser diese dieses wie noch nur schon sehr mehr immer heute"
).split())


_last_call = [0.0]          # globale Drossel: das Azure-Deployment ist RPM-limitiert →
_MIN_INTERVAL = 1.1         # höchstens ~1 LLM-Call/Sekunde, sonst 429 im Burst


def _chat_retry(client, *, tries: int = 5, **kw):
    """LLM-Call mit globaler Drossel + exponentiellem Backoff (429/Timeout robust)."""
    import time
    last = None
    for k in range(tries):
        wait = _MIN_INTERVAL - (time.time() - _last_call[0])
        if wait > 0:
            time.sleep(wait)
        try:
            r = client.chat.completions.create(**kw)
            _last_call[0] = time.time()
            return r
        except Exception as e:  # noqa: BLE001
            last = e
            _last_call[0] = time.time()
            time.sleep(min(30, 2 ** k))  # 1,2,4,8,16 s
    raise last


def _query_terms(text: str, k: int = 8) -> str:
    """Aus einer Aussage eine Stichwort-Suchanfrage bauen (Nomen/Eigennamen + Zahlen) —
    Volltext-Sätze liefern bei Wikipedia kaum Treffer, Stichwörter dagegen gut."""
    words = re.findall(r"[A-Za-zÄÖÜäöüß][\wÄÖÜäöüß-]+", text)
    terms = [w for w in words if (w[0].isupper() and w.lower() not in _STOP) or any(c.isdigit() for c in w)]
    if len(terms) < 3:
        terms = [w for w in words if w.lower() not in _STOP]
    return " ".join(terms[:k])


def _wiki_search(query: str, *, lang: str = "de", n: int = 3) -> list[dict]:
    """Retrieval-Quelle (ohne API-Key): Wikipedia-Suche → Intro-Auszug + URL je Treffer.

    Prototyp-Korpus. Produktiv durch amtliche Quellen ersetzen (Destatis-GENESIS, DIP-API,
    Antworten der Bundesregierung) — die LLM-Verifikation gegen Belege bleibt identisch.
    """
    import urllib.request
    import urllib.parse
    base = f"https://{lang}.wikipedia.org/w/api.php?"
    hdr = {"User-Agent": "graph-protokoll/1.0 (SPARK Challenge 2 factcheck)"}

    def _get(params):
        req = urllib.request.Request(base + urllib.parse.urlencode(params), headers=hdr)
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)

    try:
        hits = _get({"action": "query", "list": "search", "srsearch": query[:300],
                     "format": "json", "srlimit": n})["query"]["search"]
    except Exception:
        return []
    out: list[dict] = []
    for h in hits:
        title = h["title"]
        try:
            # mehr als nur die Intro (exchars) — sonst fehlen die konkreten Zahlen/Jahre, gegen
            # die die Aussage geprüft werden soll
            pages = _get({"action": "query", "prop": "extracts", "exchars": 1500, "explaintext": 1,
                          "titles": title, "format": "json", "redirects": 1})["query"]["pages"]
            extract = next(iter(pages.values())).get("extract", "") or ""
        except Exception:
            extract = ""
        out.append({"titel": title, "extract": extract[:1500],
                    "url": f"https://{lang}.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))})
    return out


def _web_search(query: str, *, n: int = 3) -> list[dict]:
    """Allgemeine Web-Recherche als Beleg-Quelle (am besten für aktuelle Zahlen/Fakten).
    Nutzt BRAVE_API_KEY (api.search.brave.com) oder SERPER_API_KEY (google.serper.dev),
    falls in .env gesetzt; sonst leer. Liefert [{titel, extract, url}]."""
    import os
    import urllib.request
    import urllib.parse
    brave, serper = os.environ.get("BRAVE_API_KEY"), os.environ.get("SERPER_API_KEY")
    try:
        if brave:
            u = "https://api.search.brave.com/res/v1/web/search?" + urllib.parse.urlencode(
                {"q": query, "count": n})
            req = urllib.request.Request(u, headers={"X-Subscription-Token": brave,
                                                     "Accept": "application/json"})
            r = json.load(urllib.request.urlopen(req, timeout=20))
            return [{"titel": w.get("title", ""), "extract": (w.get("description") or "")[:600],
                     "url": w.get("url", "")} for w in r.get("web", {}).get("results", [])[:n]]
        if serper:
            data = json.dumps({"q": query, "num": n}).encode()
            req = urllib.request.Request("https://google.serper.dev/search", data=data,
                                         headers={"X-API-KEY": serper, "Content-Type": "application/json"})
            r = json.load(urllib.request.urlopen(req, timeout=20))
            return [{"titel": w.get("title", ""), "extract": (w.get("snippet") or "")[:600],
                     "url": w.get("link", "")} for w in r.get("organic", [])[:n]]
    except Exception:
        return []
    return []


def _dip_search(query: str, *, n: int = 2) -> list[dict]:
    """Amtliche Retrieval-Quelle: DIP-API (Vorgänge) per DIP_API_KEY → parlamentarischer Kontext
    (welcher Gesetzentwurf/Antrag, Beratungsstand) als Beleg. Leer ohne Key."""
    import os
    import urllib.request
    import urllib.parse
    key = os.environ.get("DIP_API_KEY")
    if not key:
        return []

    def _srch(term):
        u = "https://search.dip.bundestag.de/api/v1/vorgang?" + urllib.parse.urlencode(
            {"apikey": key, "f.titel": term, "format": "json"})
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "gp/1.0"}),
                                        timeout=20) as r:
                return json.load(r).get("documents", [])
        except Exception:
            return []

    docs = _srch(query)
    if not docs:  # Fallback: längste Einzel-Stichwörter (f.titel ist "enthält")
        for t in sorted(query.split(), key=len, reverse=True)[:2]:
            docs = _srch(t)
            if docs:
                break
    deeplink = "https://dip.bundestag.de/suche?term=" + urllib.parse.quote(query[:60])
    return [{"titel": "DIP-Vorgang: " + (d.get("titel", "")[:120]),
             "extract": (d.get("abstract") or d.get("titel", "") or "")[:600], "url": deeplink}
            for d in docs[:n]]


_RETRIEVAL_SYS = (
    "Du bist ein neutraler Faktenchecker. Bewerte die AUSSAGE primär anhand der bereitgestellten "
    "BELEGE (Web/DIP/Wikipedia) — die Belege sind oft nur kurze Suchausschnitte; ergänze sie mit "
    "deinem Allgemeinwissen, um zu einer Einschätzung zu kommen. Verdikt: bestätigt (Beleg/Wissen "
    "stützt) | teilweise (im Kern richtig, Zahl/Detail weicht ab) | irreführend (richtig, aber "
    "verzerrt) | falsch (widerlegt) | unbelegt (nur wenn KEINE Einschätzung möglich). Wähle als "
    "Quelle den am besten passenden BELEG (Titel + echte URL aus der Liste). Antworte NUR JSON: "
    '{"verdikt":"...","begruendung":"... (mit Bezug auf den Beleg)","quelle_titel":"...","quelle_url":"..."}')


def factcheck_with_retrieval(aussagen: list[dict], *, model: str, base_url: str, api_key: str,
                             max_claims: int = 12, lang: str = "de") -> list[FactCheck]:
    """Produktivpfad: Retrieval (Wikipedia) + LLM-Verifizierer GEGEN die Belege, mit Zitatpflicht.

    Anders als `factcheck_with_llm` (LLM ohne Quellen → meist 'unbelegt') werden hier pro Aussage
    echte Belege geholt und das Verdikt daraus abgeleitet → belastbare Verdikte MIT echter Quelle.
    Über reale Personen weiterhin KI-Vorschlag (Disclaimer); Grundsatz: jede Quelle ist real.
    """
    from openai import OpenAI
    client = OpenAI(base_url=base_url, api_key=api_key)
    results: list[FactCheck] = []
    for i, a in enumerate(aussagen[:max_claims]):
        terms = _query_terms(a["text"])
        # Web-Suche (aktuelle Fakten) + DIP (parlamentarisch) + Wikipedia (allgemein)
        belege = (_web_search(terms) + _dip_search(terms) + _wiki_search(terms, lang=lang))[:5]
        if not belege:
            results.append(FactCheck(
                aussage_index=i, text=a["text"], person=a.get("person"), fraktion=a.get("fraktion"),
                top_nummer=a.get("top_nummer"), verdikt="unbelegt",
                begruendung=f"{_LLM_DISCLAIMER} Kein Beleg in den durchsuchten Quellen (Web, DIP-API, Wikipedia {lang}).",
                quelle={"titel": "Web + DIP-API + Wikipedia durchsucht — kein Treffer", "url":
                        "https://dip.bundestag.de/", "stand": ""},
                quelle_utterances=a.get("quelle_utterances", []), score=0.0))
            continue
        kontext = "\n\n".join(f"[{b['titel']}] ({b['url']})\n{b['extract']}" for b in belege)
        try:
            resp = _chat_retry(client, model=model, temperature=0, max_tokens=700, messages=[
                {"role": "system", "content": _RETRIEVAL_SYS},
                {"role": "user", "content": f'AUSSAGE: "{a["text"]}"\n\nBELEGE:\n{kontext}'}])
            data = _extract_json(resp.choices[0].message.content or "")
            verdikt = _as_text(data.get("verdikt"), "unbelegt")
            verdikt = verdikt if verdikt in VERDIKTE else "unbelegt"
            quelle = {"titel": _as_text(data.get("quelle_titel"), belege[0]["titel"]),
                      "url": _as_text(data.get("quelle_url"), belege[0]["url"]), "stand": ""}
            begr = f"{_LLM_DISCLAIMER} {_as_text(data.get('begruendung'))}".strip()
        except Exception as e:  # robuste Degradierung: nie ohne Quelle
            verdikt, begr = "unbelegt", f"{_LLM_DISCLAIMER} Prüfung fehlgeschlagen ({type(e).__name__})."
            quelle = {"titel": belege[0]["titel"], "url": belege[0]["url"], "stand": ""}
        results.append(FactCheck(
            aussage_index=i, text=a["text"], person=a.get("person"), fraktion=a.get("fraktion"),
            top_nummer=a.get("top_nummer"), verdikt=verdikt, begruendung=begr, quelle=quelle,
            quelle_utterances=a.get("quelle_utterances", []), score=0.0))
    assert all(fc.quelle for fc in results), "Faktencheck ohne Quelle — verletzt Grundsatz."
    return results


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


def _as_text(v, default: str = "") -> str:
    """LLM-Felder robust zu Text machen — das Modell liefert quelle_titel/-url/begruendung
    gelegentlich als Liste/Zahl statt String; sonst crasht z. B. der Slug im graph_build."""
    if isinstance(v, list):
        return ", ".join(str(x) for x in v if x)
    return str(v) if v not in (None, "") else default


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
            resp = _chat_retry(
                client, model=model, temperature=0, max_tokens=1400,
                messages=[{"role": "system", "content": _EXTRACT_SYS},
                          {"role": "user", "content": pas["text"][:4000]}])
            arr = _extract_json_list(resp.choices[0].message.content or "")
        except Exception:
            arr = []
        for item in arr if isinstance(arr, list) else []:
            claim = (item.get("aussage") or "").strip()
            if not claim:
                continue
            v = _as_text(item.get("verdikt"), "unbelegt")
            out.append({
                "aussage": claim, "verdikt": v if v in VERDIKTE else "unbelegt",
                "begruendung": f"{_LLM_DISCLAIMER} {_as_text(item.get('begruendung'))}".strip(),
                "quelle": {"titel": _as_text(item.get("quelle_titel"), "KI-Einschätzung (Mistral), ungeprüft"),
                           "url": _as_text(item.get("quelle_url")), "stand": ""},
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
            resp = _chat_retry(
                client, model=model, temperature=0, max_tokens=700,
                messages=[{"role": "system", "content": _LLM_SYS},
                          {"role": "user", "content": f'Aussage: "{a["text"]}"'}])
            data = _extract_json(resp.choices[0].message.content or "")
            verdikt = _as_text(data.get("verdikt"), "unbelegt")
            if verdikt not in VERDIKTE:
                verdikt = "unbelegt"
            quelle = {"titel": _as_text(data.get("quelle_titel"), "KI-Einschätzung (Mistral), ungeprüft"),
                      "url": _as_text(data.get("quelle_url")), "stand": ""}
            begr = f"{_LLM_DISCLAIMER} {_as_text(data.get('begruendung'))}".strip()
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
