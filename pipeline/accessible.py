"""
Barrierefreie Zusammenfassung — Sitzung als screen-reader-/TTS-tauglicher Text.

Für **blinde und sehbehinderte Menschen** ist der 3D-Graph nutzlos; sie brauchen
eine **lineare, vorgelesene** Darstellung. Dieses Modul erzeugt aus dem Protokoll
eine klare Textfassung in einfacher Sprache — inklusive **verbalisierter
Saalreaktionen** (Beifall = Zustimmung, Widerspruch/Buhrufe = Ablehnung), damit
auch die Stimmung im Saal hörbar wird. Der Text ist direkt TTS-tauglich
(z. B. mit der ElevenLabs-/Piper-Sprachausgabe der Schwester-Prototypen).
"""

from __future__ import annotations

# Saalreaktion -> verständliche Beschreibung (für Vorlesen)
_REAKTION_WORT = {
    "Beifall": "Beifall (Zustimmung)",
    "Heiterkeit": "Heiterkeit",
    "Lachen": "Lachen",
    "Widerspruch": "Widerspruch (Ablehnung)",
    "Zwischenruf": "Zwischenruf",
    "Missfallen": "Missfallen, also Buhrufe (Ablehnung)",
    "Unruhe": "Unruhe im Saal",
    "Kommentar": "eine Saalreaktion",
}

_VERDIKT_WORT = {
    "bestätigt": "ist bestätigt", "teilweise": "ist teilweise zutreffend",
    "irreführend": "ist irreführend", "falsch": "ist falsch",
    "unbelegt": "ist nicht belegt",
}


def summarize(protocol, factchecks=None) -> str:
    fc = factchecks or []
    m = protocol.meeting
    L: list[str] = []
    kopf = f"{m.get('gremium','Sitzung')}"
    if m.get("wahlperiode"):
        kopf += f", Wahlperiode {m['wahlperiode']}, Sitzung {m.get('sitzung_nr','')}"
    L.append(f"Barrierefreie Zusammenfassung der Sitzung. {kopf}, am {m.get('datum','')}.")
    L.append("")

    woerter = sum(len(u.text.split()) for u in protocol.utterances if u.text)
    L.append(f"Überblick: Es gab {len(protocol.redebeitraege)} Redebeiträge zu "
             f"{len(protocol.tops)} Tagesordnungspunkten, insgesamt rund {woerter} Wörter "
             f"und {len(protocol.kommentare)} Saalreaktionen.")
    L.append("")

    L.append("Tagesordnung:")
    for t in protocol.tops:
        L.append(f"- Tagesordnungspunkt {t['nummer']}: {t['titel']}.")
    L.append("")

    if protocol.redebeitraege:
        L.append("Redebeiträge:")
        for r in protocol.redebeitraege:
            frak = f", {r['fraktion']}" if r.get("fraktion") else ""
            L.append(f"- {r['person']}{frak} sprach zu Tagesordnungspunkt {r['top_nummer']}.")
        L.append("")

    if protocol.kommentare:
        L.append("Stimmung im Saal, in Worten:")
        for k in protocol.kommentare:
            wort = _REAKTION_WORT.get(k["typ"], "eine Saalreaktion")
            urh = f" von {k['urheber']}" if k.get("urheber") else ""
            laut = f", {k['intensitaet']}" if k.get("intensitaet") else ""
            L.append(f"- Bei Tagesordnungspunkt {k['top_nummer']}: {wort}{urh}{laut}.")
        L.append("")

    if fc:
        L.append("Faktencheck der Aussagen — jeweils mit Quelle:")
        for c in fc:
            satz = _VERDIKT_WORT.get(c.verdikt, f"hat das Ergebnis {c.verdikt}")
            quelle = f" Quelle: {c.quelle['titel']}." if c.quelle else ""
            L.append(f"- Die Aussage von {c.person}: „{c.text}“ {satz}. "
                     f"{c.begruendung}{quelle}")
        L.append("")

    if protocol.beschluesse:
        L.append("Beschlüsse:")
        for b in protocol.beschluesse:
            L.append(f"- Beschluss {b['nummer']}: {b['text']}")
        L.append("")
    if protocol.aufgaben:
        L.append("Aufgaben und Fristen:")
        for a in protocol.aufgaben:
            L.append(f"- Zuständig {a['zustaendig']}, Frist {a['frist']}.")
        L.append("")

    L.append("Ende der Zusammenfassung.")
    return "\n".join(L)
