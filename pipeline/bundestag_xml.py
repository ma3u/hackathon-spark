"""
Parser für das amtliche Bundestags-Plenarprotokoll-XML (DTD `dbtplenarprotokoll`,
gültig ab WP19). Erzeugt dasselbe `Protocol` wie der ASR-Pfad — d. h. ein
Plenarprotokoll lässt sich mit demselben Graph-Builder, Faktencheck und
Neo4j-Loader verarbeiten wie ein Audiomitschnitt.

Schema-Kernpunkte (aus der offiziellen DTD):
  dbtplenarprotokoll[@wahlperiode,@sitzung-nr,@sitzung-datum]
    └ sitzungsverlauf
        └ tagesordnungspunkt[@top-id] (top-titel, rede*, name?, kommentar*)
            └ rede[@id] : p[@klasse="redner"]/redner[@id]/name(vorname,nachname,
                          fraktion,rolle) + p(Redetext) + kommentar(Publikum)
  <kommentar> trägt amtlich die Saalreaktionen: (Beifall …), (Zuruf …),
  (Lachen …), (Widerspruch …) — also Jubel/Buhrufe direkt aus der Quelle.

Quelle DTD: https://www.bundestag.de/resource/blob/575720/.../dbtplenarprotokoll.dtd
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from .align import Utterance
from .extract import Protocol, _split_sentences, _is_checkable

# Saalreaktion -> Ereignistyp (für AkustischesEreignis/Kommentar-Knoten)
_KOMMENTAR_TYP = [
    ("beifall", "Beifall"), ("heiterkeit", "Heiterkeit"), ("lachen", "Lachen"),
    ("widerspruch", "Widerspruch"), ("zuruf", "Zwischenruf"), ("gegenruf", "Zwischenruf"),
    ("buh", "Missfallen"), ("unruhe", "Unruhe"),
]

# Blöcke unter <sitzungsverlauf>, die Reden/Saalreaktionen tragen. Reden hängen NICHT nur an
# Tagesordnungspunkten, sondern auch an Zusatzpunkten und am Sitzungsbeginn (Geschäftsordnung,
# Aktuelle Stunde, Reaktionen vor TOP 1). top-id ist frei und nicht eindeutig numerisch.
_TOP_BLOCKS = ("sitzungsbeginn", "tagesordnungspunkt", "zusatzpunkt", "sitzungsende")
_BLOCK_TITEL = {"sitzungsbeginn": "Sitzungseröffnung", "sitzungsende": "Sitzungsende"}


def _text(el: ET.Element | None) -> str:
    return "".join(el.itertext()).strip() if el is not None else ""


def _speaker_from_redner(redner: ET.Element) -> dict:
    name = redner.find("name")
    if name is None:
        return {"name": "Unbekannt", "rolle": "Redner", "fraktion": None}
    def t(tag):
        e = name.find(tag)
        return e.text.strip() if e is not None and e.text else ""
    titel, vorname, nachname = t("titel"), t("vorname"), t("nachname")
    fraktion = t("fraktion") or None
    rolle_el = name.find("rolle")
    rolle = _text(rolle_el.find("rolle_lang")) if rolle_el is not None else ""
    voll = " ".join(p for p in [titel, vorname, nachname] if p).strip() or "Unbekannt"
    return {"name": voll, "rolle": rolle or "Abgeordneter", "fraktion": fraktion}


def _classify_kommentar(text: str) -> tuple[str, str | None]:
    low = text.lower()
    typ = next((label for key, label in _KOMMENTAR_TYP if key in low), "Kommentar")
    m = re.search(r"(?:bei|von|der)\s+(?:der|dem)?\s*([A-ZÄÖÜ][\wäöüß .-]+?)(?:[:)]|$)", text)
    urheber = m.group(1).strip() if m else None
    return typ, urheber


def parse_plenarprotokoll(xml_path: str | Path) -> Protocol:
    root = ET.parse(xml_path).getroot()
    wp = root.get("wahlperiode", "")
    nr = root.get("sitzung-nr", "")
    p = Protocol()
    p.meeting = {
        "gremium": "Deutscher Bundestag",
        "datum": root.get("sitzung-datum", ""),
        "ort": root.get("sitzung-ort", "Berlin"),
        "wahlperiode": wp,
        "sitzung_nr": nr,
        "beschlussfaehig": "",
        "quelle": f"Plenarprotokoll {wp}/{nr}",
    }
    u_index = 0  # laufende Utterance-Nummer (Provenienz-Segment-Index)

    def add_utterance(person: dict, text: str) -> int:
        nonlocal u_index
        p.utterances.append(Utterance(
            start=0.0, end=0.0, speaker_label=f"R{u_index}", speaker_name=person["name"],
            rolle=person["rolle"], fraktion=person.get("fraktion"), text=text,
            herkunft="protokoll"))
        idx = u_index
        u_index += 1
        return idx

    # In Dokumentreihenfolge über die inhaltstragenden Blöcke des Sitzungsverlaufs gehen.
    # Wir vergeben eine laufende, kollisionsfreie TOP-Nummer (top-id ist frei/mehrdeutig:
    # "Tagesordnungspunkt 1", "Zusatzpunkt 5", "Zur Geschäftsordnung" → früher kollidiert).
    verlauf = root.find("sitzungsverlauf")
    blocks = list(verlauf) if verlauf is not None else list(root.iter("tagesordnungspunkt"))
    top_nr = 0
    for block in blocks:
        if block.tag not in _TOP_BLOCKS:
            continue
        if block.find("rede") is None and block.find("kommentar") is None:
            continue  # leerer Rahmenblock (z. B. reines <sitzungsende>) → kein TOP
        top_nr += 1
        cur = top_nr
        titel = _text(block.find("top-titel")) or block.get("top-id", "") \
            or _BLOCK_TITEL.get(block.tag, "")
        p.tops.append({"nummer": cur, "titel": titel, "quelle_utterances": []})

        rede_index = -1
        for child in list(block):
            if child.tag == "rede":
                redner = child.find(".//redner")
                person = _speaker_from_redner(redner) if redner is not None else \
                    {"name": "Unbekannt", "rolle": "Redner", "fraktion": None}
                # Redetext = alle <p> außer dem Redner-Kopf
                paras = [_text(pp) for pp in child.findall("p") if pp.get("klasse") != "redner"]
                speech = " ".join(t for t in paras if t)
                idx = add_utterance(person, speech)
                rede_index = idx
                p.redebeitraege.append({
                    "person": person["name"], "fraktion": person.get("fraktion"),
                    "top_nummer": cur, "start": 0.0, "timecode": "Prot.",
                    "quelle_utterances": [idx]})
                # prüfbare Aussagen für den Faktencheck
                for sent in _split_sentences(speech):
                    if _is_checkable(sent) and "frage" not in sent.lower():
                        p.aussagen.append({"text": sent, "person": person["name"],
                                           "fraktion": person.get("fraktion"),
                                           "top_nummer": cur, "quelle_utterances": [idx]})
                # Kommentare innerhalb der Rede (Saalreaktionen)
                for kom in child.findall("kommentar"):
                    _add_kommentar(p, _text(kom), cur, rede_index)
            elif child.tag == "kommentar":
                _add_kommentar(p, _text(child), cur, rede_index)
            elif child.tag == "name":  # Sitzungsleitung (Präsident:in)
                txt = _text(child).rstrip(":")
                if txt:
                    add_utterance({"name": txt, "rolle": "Sitzungsleitung", "fraktion": None}, "")
    return p


def _add_kommentar(p: Protocol, text: str, top_nr: int, rede_index: int) -> None:
    if not text:
        return
    typ, urheber = _classify_kommentar(text)
    p.kommentare.append({"typ": typ, "text": text, "urheber": urheber,
                         "top_nummer": top_nr, "rede_index": rede_index})
