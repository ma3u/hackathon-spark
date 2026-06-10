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

# Durchschnittliches Redetempo Plenum (zur Schätzung der Gesamtredezeit aus Wörtern).
WPM = 130

# Themen-Klassifikation per Schlüsselwörtern (deterministisch, offline) — gruppiert TOPs zu
# Sachthemen (Migration, Ukraine, Haushalt …) statt nur „Tagesordnungspunkt 12".
_THEMA = [
    ("Migration & Asyl", ["migration", "asyl", "flücht", "geflücht", "abschieb", "aufenthalt", "einwander"]),
    ("Krieg in der Ukraine", ["ukraine", "russland", "selenskyj", "putin", "waffenlief", "kriegs"]),
    ("Haushalt & Schulden", ["haushalt", "neuverschuld", "schuldenbremse", "etat", "staatsverschuld", "bundeshaushalt"]),
    ("Steuern & Finanzen", ["steuer", "mehrwertsteuer", "finanzpolit", "abgaben"]),
    ("Energie & Klima", ["energie", "klima", "windkraft", "windenerg", "kohle", "heizung", "erneuerbar", "co2"]),
    ("Verteidigung & Bundeswehr", ["bundeswehr", "verteidigung", "nato", "wehrpflicht", "rüstung", "aufrüst"]),
    ("Wirtschaft & Arbeit", ["wirtschaft", "arbeitsmarkt", "mindestlohn", "mittelstand", "industrie", "arbeitszeit"]),
    ("Rente & Soziales", ["rente", "bürgergeld", "grundsicher", "sozialstaat"]),
    ("Gesundheit & Pflege", ["gesundheit", "krankenhaus", "apothek", "pflege", "kranken"]),
    ("Wohnen & Bau", ["wohnen", "miete", "wohnungsbau", "städtebau", "bauland"]),
    ("Innere Sicherheit", ["polizei", "kriminal", "terror", "verfassungsschutz", "extremismus"]),
    ("Europa & EU", ["europäische union", "eu-haushalt", "binnenmarkt", "brüssel"]),
    ("Bildung & Forschung", ["bildung", "schule", "forschung", "wissenschaft", "ausbildung"]),
    ("Digitalisierung", ["digital", "künstliche intelligenz", "cyber", "internet"]),
    ("Verkehr & Mobilität", ["verkehr", "bahn", "autobahn", "mobilität", "luftverkehr"]),
    ("Landwirtschaft & Umwelt", ["landwirt", "umwelt", "tierschutz", "naturschutz"]),
]


def _classify_thema(text: str) -> str | None:
    low = text.lower()
    best, score = None, 0
    for thema, kws in _THEMA:
        s = sum(low.count(k) for k in kws)
        if s > score:
            best, score = thema, s
    return best if score >= 2 else None


def compute_dashboard(protocol, factchecks=None) -> dict:
    fc = factchecks or []
    u = protocol.utterances
    uwords = {i: len(x.text.split()) for i, x in enumerate(u)}
    ufrak = {i: x.fraktion for i, x in enumerate(u)}

    # Sprachanteil pro Fraktion (Wortanteil) — nur GESPROCHENE Beiträge
    # (schriftliche Anlagen, herkunft="anlage", verzerren den Redeanteil nicht).
    words_by_frak: Counter = Counter()
    for i, x in enumerate(u):
        if x.fraktion and x.herkunft != "anlage":
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
        if r.get("schriftlich"):
            continue  # schriftliche Anlagen sind kein gesprochenes Redevolumen
        for idx in r.get("quelle_utterances", []):
            words_by_top[r["top_nummer"]] += uwords.get(idx, 0)
    # Volltext je TOP (Titel + Reden) für die Themen-Klassifikation
    text_by_top: dict[int, list[str]] = defaultdict(list)
    for r in protocol.redebeitraege:
        if r.get("schriftlich"):
            continue
        for idx in r.get("quelle_utterances", []):
            if 0 <= idx < len(u):
                text_by_top[r["top_nummer"]].append(u[idx].text)
    thema_by_top = {n: _classify_thema((top_titel.get(n, "") + " " + " ".join(text_by_top.get(n, []))))
                    for n in top_titel}
    themen = [
        {"top": n, "titel": top_titel.get(n, ""), "thema": thema_by_top.get(n), "woerter": w}
        for n, w in words_by_top.most_common(30)
    ]
    # Aggregiert nach Sachthema (Migration, Ukraine, Haushalt …) — das eigentliche „Top-Thema"
    thema_words: Counter = Counter()
    for n, w in words_by_top.items():
        thema_words[thema_by_top.get(n) or "Sonstige / Verfahren"] += w
    sachthemen = [{"thema": t, "woerter": w} for t, w in thema_words.most_common()]

    # Redner:innen nach gesprochenem Redevolumen (mit Fraktion)
    redner_acc: dict = defaultdict(lambda: {"woerter": 0, "reden": 0, "fraktion": None})
    for r in protocol.redebeitraege:
        if r.get("schriftlich"):
            continue
        e = redner_acc[r["person"]]
        e["fraktion"] = r.get("fraktion")
        e["reden"] += 1
        for idx in r.get("quelle_utterances", []):
            e["woerter"] += uwords.get(idx, 0)
    redner = [{"name": n, **v} for n, v in
              sorted(redner_acc.items(), key=lambda i: -i[1]["woerter"]) if v["woerter"] > 0][:15]

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
            "reden": sum(1 for r in protocol.redebeitraege if not r.get("schriftlich")),
            "schriftliche_beitraege": sum(1 for r in protocol.redebeitraege if r.get("schriftlich")),
            "woerter": (gespr := sum(w for i, w in uwords.items() if u[i].herkunft != "anlage")),
            "gesamtzeit_min": round(gespr / WPM),  # Schätzung aus Wörtern (XML ohne Zeitstempel)
            "tops": len(protocol.tops),
            "saalreaktionen": len(protocol.kommentare),
            "geprüfte_aussagen": len(fc),
        },
        "redner": redner,
        "sachthemen": sachthemen,
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
