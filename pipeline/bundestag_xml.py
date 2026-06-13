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
import unicodedata
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


# Amts-/Sitzungsleitungs-Anreden, die im <name>-Feld der Sitzungsleitung dem Namen
# vorangestellt werden ("Präsidentin Julia Klöckner") — gehören NICHT zum Namen und
# erzeugen sonst Personen-Dubletten ggü. dem Redner-Pfad ("Julia Klöckner"). Entity-
# Resolution beginnt an der Quelle: Anrede strippen + NBSP/Unicode normalisieren (der
# akademische Titel Dr./Prof. bleibt Teil des Anzeigenamens). Siehe scripts/entity_resolution.py.
_ANREDE = re.compile(
    r"^\s*(alters|vize)?präsident(in)?\b|^\s*schriftführer(in)?\b", re.IGNORECASE)


def _canon_person_name(name: str) -> str:
    name = unicodedata.normalize("NFC", (name or "").replace(" ", " "))
    prev = None
    while prev != name:  # mehrfach: "Vizepräsidentin Dr. …" → Titel bleibt, Anrede weg
        prev = name
        name = _ANREDE.sub("", name).strip()
    return " ".join(name.split())


def _speaker_from_redner(redner: ET.Element) -> dict:
    name = redner.find("name")
    if name is None:
        return {"name": "Unbekannt", "rolle": "Redner", "fraktion": None}
    def t(tag):
        e = name.find(tag)
        return e.text.strip() if e is not None and e.text else ""
    titel, vorname, nachname = t("titel"), t("vorname"), t("nachname")
    fraktion = _canon_fraktion(t("fraktion"))
    rolle_el = name.find("rolle")
    rolle = _text(rolle_el.find("rolle_lang")) if rolle_el is not None else ""
    voll = _canon_person_name(" ".join(p for p in [titel, vorname, nachname] if p)) or "Unbekannt"
    return {"name": voll, "rolle": rolle or "Abgeordneter", "fraktion": fraktion}


def _classify_kommentar(text: str) -> tuple[str, str | None]:
    low = text.lower()
    typ = next((label for key, label in _KOMMENTAR_TYP if key in low), "Kommentar")
    m = re.search(r"(?:bei|von|der)\s+(?:der|dem)?\s*([A-ZÄÖÜ][\wäöüß .-]+?)(?:[:)]|$)", text)
    urheber = m.group(1).strip() if m else None
    return typ, urheber


def _norm_label(s: str) -> str:
    """top-id / ivz-block-titel auf eine vergleichbare Form bringen (NBSP, Doppelpunkt)."""
    return unicodedata.normalize("NFC", s.replace("\xa0", " ")).strip().rstrip(":").strip()


# Fraktionsnamen kanonisieren → exakt die Schlüssel der Frontend-Farbtabelle (sonst kein
# grüner Balken: das XML liefert „BÜNDNIS<NBSP>90/DIE GRÜNEN" mit geschütztem Leerzeichen
# bzw. unterschiedlicher Unicode-Form → Lookup scheitert).
_FRAK_CANON = [
    ("cdu", "CDU/CSU"), ("csu", "CDU/CSU"),
    ("bündnis 90", "BÜNDNIS 90/DIE GRÜNEN"), ("grüne", "BÜNDNIS 90/DIE GRÜNEN"),
    ("alternative für", "AfD"), ("afd", "AfD"),
    ("sozialdemokrat", "SPD"), ("spd", "SPD"),
    ("freie demokrat", "FDP"), ("fdp", "FDP"),
    ("die linke", "Die Linke"), ("linke", "Die Linke"),
    ("bsw", "BSW"), ("sahra wagenknecht", "BSW"),
    ("fraktionslos", "fraktionslos"),
]


def _canon_fraktion(s: str | None) -> str | None:
    if not s:
        return None
    norm = unicodedata.normalize("NFC", re.sub(r"\s+", " ", s.replace("\xa0", " "))).strip()
    low = norm.lower()
    for pat, canon in _FRAK_CANON:
        if pat in low:
            return canon
    return norm or None


def _clean_ws(s: str, *, limit: int = 200) -> str:
    s = re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()
    return s[: limit - 1].rstrip() + "…" if len(s) > limit else s


def _ivz_titles(root: ET.Element) -> dict[str, str]:
    """Inhaltsverzeichnis → {top-id-Label: beschreibender Titel}.

    Der <tagesordnungspunkt> trägt selbst keinen Titel; die Sachbeschreibung steht im
    <inhaltsverzeichnis> (vorspann). Der erste <ivz-eintrag> OHNE <redner> ist die
    Beschreibung (Einträge MIT <redner> sind nur die Rednerliste des TOP).
    """
    out: dict[str, str] = {}
    ivz = root.find(".//inhaltsverzeichnis")
    if ivz is None:
        return out
    for blk in ivz.findall("ivz-block"):
        t = blk.find("ivz-block-titel")
        label = _norm_label(_text(t)) if t is not None else ""
        if not label:
            continue
        for e in blk.findall("ivz-eintrag"):
            if e.find(".//redner") is not None:
                continue
            inhalt = e.find("ivz-eintrag-inhalt")
            desc = _clean_ws(_text(inhalt)) if inhalt is not None else ""
            if desc:
                out[label] = desc
                break
    return out


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

    def add_utterance(person: dict, text: str, herkunft: str = "protokoll") -> int:
        nonlocal u_index
        p.utterances.append(Utterance(
            start=0.0, end=0.0, speaker_label=f"R{u_index}", speaker_name=person["name"],
            rolle=person["rolle"], fraktion=person.get("fraktion"), text=text,
            herkunft=herkunft))
        idx = u_index
        u_index += 1
        return idx

    def ingest_rede(rede: ET.Element, top_nr: int, *, herkunft: str = "protokoll") -> int:
        """Ein <rede>-Element → Utterance + Redebeitrag (+ Aussagen + Saalreaktionen)."""
        redner = rede.find(".//redner")
        person = _speaker_from_redner(redner) if redner is not None else \
            {"name": "Unbekannt", "rolle": "Redner", "fraktion": None}
        paras = [_text(pp) for pp in rede.findall("p") if pp.get("klasse") != "redner"]
        speech = " ".join(t for t in paras if t)
        idx = add_utterance(person, speech, herkunft)
        p.redebeitraege.append({
            "person": person["name"], "fraktion": person.get("fraktion"),
            "top_nummer": top_nr, "start": 0.0, "timecode": "Prot.",
            "schriftlich": herkunft == "anlage", "quelle_utterances": [idx]})
        for sent in _split_sentences(speech):
            if _is_checkable(sent) and "frage" not in sent.lower():
                p.aussagen.append({"text": sent, "person": person["name"],
                                   "fraktion": person.get("fraktion"),
                                   "top_nummer": top_nr, "quelle_utterances": [idx]})
        for kom in rede.findall("kommentar"):  # Saalreaktionen innerhalb der Rede
            _add_kommentar(p, _text(kom), top_nr, idx)
        return idx

    # In Dokumentreihenfolge über die inhaltstragenden Blöcke des Sitzungsverlaufs gehen.
    # Wir vergeben eine laufende, kollisionsfreie TOP-Nummer (top-id ist frei/mehrdeutig:
    # "Tagesordnungspunkt 1", "Zusatzpunkt 5", "Zur Geschäftsordnung" → früher kollidiert).
    ivz_titel = _ivz_titles(root)
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
        # Titel: beschreibende Sachüberschrift aus dem Inhaltsverzeichnis (echte Protokolle),
        # sonst <top-titel> (Sample), sonst die top-id, sonst der Blocktyp.
        titel = ivz_titel.get(_norm_label(block.get("top-id", ""))) \
            or _text(block.find("top-titel")) or block.get("top-id", "") \
            or _BLOCK_TITEL.get(block.tag, "")
        p.tops.append({"nummer": cur, "titel": titel, "quelle_utterances": []})

        rede_index = -1
        for child in list(block):
            if child.tag == "rede":
                rede_index = ingest_rede(child, cur)
            elif child.tag == "kommentar":
                _add_kommentar(p, _text(child), cur, rede_index)
            elif child.tag == "name":  # Sitzungsleitung (Präsident:in)
                txt = _canon_person_name(_text(child).rstrip(":"))  # Anrede weg → keine Dublette
                if txt:
                    add_utterance({"name": txt, "rolle": "Sitzungsleitung", "fraktion": None}, "")

    # Schriftliche Beiträge in den <anlagen>: "zu Protokoll gegebene Reden" und
    # Erklärungen nach §31 GO — echte, namentliche Beiträge, die NICHT mündlich gehalten
    # wurden. Eigener TOP + herkunft="anlage", damit Auswertungen sie von gesprochenen
    # Redebeiträgen trennen können (keine Saalreaktionen, kein Sprachanteil).
    anlagen = root.find("anlagen")
    anlagen_reden = list(anlagen.iter("rede")) if anlagen is not None else []
    if anlagen_reden:
        top_nr += 1
        p.tops.append({"nummer": top_nr, "titel": "Schriftliche Beiträge zu Protokoll (Anlagen)",
                       "quelle_utterances": []})
        for rede in anlagen_reden:
            ingest_rede(rede, top_nr, herkunft="anlage")
    return p


def _add_kommentar(p: Protocol, text: str, top_nr: int, rede_index: int) -> None:
    if not text:
        return
    typ, urheber = _classify_kommentar(text)
    p.kommentare.append({"typ": typ, "text": text, "urheber": urheber,
                         "top_nummer": top_nr, "rede_index": rede_index})
