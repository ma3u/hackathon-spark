"""Geteilte Echtdaten-Basis für die E2E-Tests: parst die echten WP21-Protokolle EINMAL und
liefert deterministische Stichproben für die Parametrisierung (keine Zufallswerte → reproduzierbar).
"""

from __future__ import annotations

import functools
import glob
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from pipeline import bundestag_xml  # noqa: E402
# Die in Neo4j geladenen echten Sitzungen (load_real_sessions.py lädt plenarprotokoll-21-*.xml):
WP21_XML = sorted(glob.glob(str(REPO / "data" / "real" / "plenarprotokoll-21-*.xml")))
ALL_XML = sorted(glob.glob(str(REPO / "data" / "real" / "plenarprotokoll-*.xml")))

# Erlaubte Saalreaktions-Typen (aus bundestag_xml._KOMMENTAR_TYP + Fallback "Kommentar")
ALLOWED_SUBTYPES = {"Beifall", "Heiterkeit", "Lachen", "Widerspruch",
                    "Zwischenruf", "Missfallen", "Unruhe", "Kommentar"}


@functools.lru_cache(maxsize=None)
def protocols() -> dict:
    """{sitzung_id: (xml_path, Protocol)} für die WP21-Sitzungen (= die in Neo4j geladenen)."""
    out = {}
    for x in WP21_XML:
        p = bundestag_xml.parse_plenarprotokoll(x)
        sid = f"sitzung_bt_{p.meeting.get('wahlperiode','x')}_{p.meeting.get('sitzung_nr','x')}"
        out[sid] = (x, p)
    return out


def sessions() -> list[dict]:
    res = []
    for sid, (_x, p) in protocols().items():
        res.append({"sid": sid, "nr": p.meeting.get("sitzung_nr", ""),
                    "datum": p.meeting.get("datum", ""), "tops": len(p.tops),
                    "reden": len(p.redebeitraege), "reaktionen": len(p.kommentare)})
    return res


def _evenly(items: list, n: int) -> list:
    """Deterministische, gleichmäßig verteilte Stichprobe von n Elementen."""
    if not items:
        return []
    step = max(1, len(items) // n)
    return items[::step][:n]


def speaker_sample(n: int) -> list[str]:
    names = sorted({r["person"] for _sid, (_x, p) in protocols().items()
                    for r in p.redebeitraege if r.get("person")})
    return _evenly(names, n)


def reaction_sample(n: int) -> list[str]:
    typ = [k["typ"] for _sid, (_x, p) in protocols().items() for k in p.kommentare]
    return _evenly(typ, n)
