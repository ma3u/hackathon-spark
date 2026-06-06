"""
Sitzungs-Dashboard — aggregierte Kennzahlen je Sitzung aus dem Protocol.

Liefert die Datengrundlage für ein Dashboard pro Sitzung:
  • Top-Themen (Tagesordnungspunkte nach Redevolumen)
  • Sprachanteil pro Fraktion (Wortanteil)
  • Stimmung/Feedback je Thema und je Fraktion aus den amtlichen Saalreaktionen
    (Beifall = positiv; Widerspruch/Zwischenruf/Missfallen/Unruhe = negativ)
  • Faktencheck-Bilanz (Verdikte)

Alles deterministisch aus dem bereits extrahierten Protokoll — keine Modelle nötig.
"""

from __future__ import annotations

from collections import Counter, defaultdict

POSITIV = {"Beifall", "Heiterkeit"}
NEGATIV = {"Widerspruch", "Zwischenruf", "Missfallen", "Unruhe"}


def compute_dashboard(protocol, factchecks=None) -> dict:
    fc = factchecks or []
    u = protocol.utterances
    uwords = {i: len(x.text.split()) for i, x in enumerate(u)}
    ufrak = {i: x.fraktion for i, x in enumerate(u)}

    # Sprachanteil pro Fraktion (Wortanteil)
    words_by_frak: Counter = Counter()
    for i, x in enumerate(u):
        if x.fraktion:
            words_by_frak[x.fraktion] += uwords[i]
    total = sum(words_by_frak.values()) or 1
    sprachanteil = [
        {"fraktion": f, "woerter": w, "prozent": round(100 * w / total, 1)}
        for f, w in words_by_frak.most_common()
    ]

    # Top-Themen: TOPs nach Redevolumen (Wörter unter dem TOP), Top 30
    top_titel = {t["nummer"]: t["titel"] for t in protocol.tops}
    words_by_top: Counter = Counter()
    for r in protocol.redebeitraege:
        for idx in r.get("quelle_utterances", []):
            words_by_top[r["top_nummer"]] += uwords.get(idx, 0)
    themen = [
        {"top": n, "titel": top_titel.get(n, ""), "woerter": w}
        for n, w in words_by_top.most_common(30)
    ]

    # Feedback aus Saalreaktionen — je Thema, je gebender Fraktion, je beredeter Fraktion
    stim_top = defaultdict(lambda: {"positiv": 0, "negativ": 0})
    stim_geber = defaultdict(lambda: {"positiv": 0, "negativ": 0})   # wer reagiert
    stim_empf = defaultdict(lambda: {"positiv": 0, "negativ": 0})    # wessen Rede löst aus
    for k in protocol.kommentare:
        pol = "positiv" if k["typ"] in POSITIV else ("negativ" if k["typ"] in NEGATIV else None)
        if not pol:
            continue
        stim_top[k["top_nummer"]][pol] += 1
        if k.get("urheber"):
            stim_geber[k["urheber"]][pol] += 1
        empf_frak = ufrak.get(k.get("rede_index", -1))
        if empf_frak:
            stim_empf[empf_frak][pol] += 1

    def _flat(d, key):
        return [{key: k, **v} for k, v in sorted(d.items(), key=lambda i: -(i[1]["positiv"] + i[1]["negativ"]))]

    # Faktencheck-Bilanz
    fc_bilanz = dict(Counter(c.verdikt for c in fc))

    return {
        "sitzung": {
            "gremium": protocol.meeting.get("gremium", ""),
            "datum": protocol.meeting.get("datum", ""),
            "wahlperiode": protocol.meeting.get("wahlperiode", ""),
            "sitzung_nr": protocol.meeting.get("sitzung_nr", ""),
        },
        "kennzahlen": {
            "reden": len(protocol.redebeitraege),
            "woerter": sum(uwords.values()),
            "tops": len(protocol.tops),
            "saalreaktionen": len(protocol.kommentare),
            "geprüfte_aussagen": len(fc),
        },
        "top_themen": themen,
        "sprachanteil_fraktion": sprachanteil,
        "feedback_je_thema": [
            {"top": n, "titel": top_titel.get(n, ""), **v} for n, v in
            sorted(stim_top.items(), key=lambda i: -(i[1]["positiv"] + i[1]["negativ"]))
        ],
        "feedback_gegeben_fraktion": _flat(stim_geber, "fraktion"),
        "feedback_erhalten_fraktion": _flat(stim_empf, "fraktion"),
        "faktencheck_bilanz": fc_bilanz,
    }
