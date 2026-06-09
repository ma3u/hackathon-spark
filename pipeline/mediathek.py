"""
Bundestag-Mediathek — Redebeitrags-Clips (webtv.bundestag.de) als Transkriptquelle.

Anders als YouTube (nur ~5 Gesamt-Streams, Auto-Captions OHNE Sprecher) liefert die
**amtliche** Mediathek pro Rede einen Clip MIT **korrigiertem** Untertitel (`.srt`) und
Sprecher/Fraktion/TOP im Titel — also einen **sprecher-attribuierten, korrigierten,
zeitgestempelten** Transkript für JEDE Sitzung, mit **Deeplink je Rede** (dbtg.tv/fvid/<id>).
Damit füllt die Mediathek die YouTube-Lücken — und es ist **kein eigenes ASR/Whisper nötig**,
weil die Untertitel bereits vorliegen.

Produktivpfad: Podcast-Feed paginieren, je Clip die `.srt` vom CDN laden → Redebeiträge.
Demopfad: identisch und ohne Modelle/GPU (die Untertitel sind schon da).
"""

from __future__ import annotations

import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor

FEED = ("https://webtv.bundestag.de/player/macros/_v_q_3000_de/_s_podcast_skin/"
        "_x_s-144277506/bttv/podcast.xml")
_UA = {"User-Agent": "graph-protokoll/1.0 (SPARK Challenge 2)"}

_ITEM = re.compile(r"<item>(.*?)</item>", re.DOTALL)
# "Redebeitrag von <Name> (<Rolle/Fraktion>) am 22.05.2026 um 15:11 Uhr (81. Sitzung, TOP …)"
_TITLE = re.compile(
    r"Redebeitrag von (.+?) \((.+?)\) am (\d{2}\.\d{2}\.\d{4}) um (\d{2}:\d{2}) Uhr "
    r"\((\d+)\. Sitzung, TOP (.+?)\)")
_LINK = re.compile(r"<link>https?://dbtg\.tv/fvid/(\d+)</link>")
_ENCL = re.compile(r'<enclosure url="([^"]+)"')
# Fraktion aus dem Rollen-Feld → kanonische Namen (wie die UI-Farbtabelle). Reihenfolge
# zählt: spezifische/Slash-Formen zuerst (CDU/CSU, B90/Grüne enthalten selbst einen Slash).
_FRAK = [("CDU/CSU", "CDU/CSU"), ("B90/Grüne", "BÜNDNIS 90/DIE GRÜNEN"),
         ("BÜNDNIS 90", "BÜNDNIS 90/DIE GRÜNEN"), ("Grüne", "BÜNDNIS 90/DIE GRÜNEN"),
         ("AfD", "AfD"), ("SPD", "SPD"), ("FDP", "FDP"),
         ("Die Linke", "Die Linke"), ("Linke", "Die Linke"), ("BSW", "BSW"),
         ("fraktionslos", "fraktionslos")]


def _fraktion(role_field: str) -> str | None:
    low = role_field.lower()
    for pat, canon in _FRAK:
        if pat.lower() in low:
            return canon
    return None  # Regierungsmitglieder/Präsidium ohne Fraktionsangabe


def _page(offset: int) -> str:
    url = FEED + (f"?pagingOffset={offset}" if offset else "")
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", "ignore")


def _parse_items(xml: str) -> list[dict]:
    out: list[dict] = []
    for block in _ITEM.findall(xml):
        mt, ml, me = _TITLE.search(block), _LINK.search(block), _ENCL.search(block)
        if not (mt and ml and me):
            continue
        speaker, role, datum, uhr, nr, top = mt.groups()
        fvid, mp4 = ml.group(1), me.group(1)
        srt = mp4.rsplit("/", 1)[0] + f"/{fvid}.srt"  # CDN: …/<fvid>/<fvid>.srt
        out.append({"fvid": fvid, "speaker": speaker.strip(), "role": role.strip(),
                    "fraktion": _fraktion(role), "datum": datum, "uhr": uhr,
                    "nr": int(nr), "top": top.strip(), "mp4": mp4, "srt": srt,
                    "url": f"https://dbtg.tv/fvid/{fvid}"})
    return out


def collect_session(nr, *, max_pages: int = 60) -> list[dict]:
    """Alle Redebeitrags-Clips einer Sitzung (Feed newest-first paginiert)."""
    nr = int(nr)
    clips: list[dict] = []
    offset = 0
    while offset < max_pages:
        items = _parse_items(_page(offset))
        if not items:
            break
        clips += [it for it in items if it["nr"] == nr]
        page_nrs = [it["nr"] for it in items]
        if page_nrs and max(page_nrs) < nr:  # an der Zielsitzung vorbei (nur ältere) → fertig
            break
        offset += 1
    clips.sort(key=lambda c: (c["datum"], c["uhr"], c["fvid"]))  # chronologisch
    return clips


def _srt_text(srt_url: str) -> str:
    try:
        req = urllib.request.Request(srt_url, headers=_UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode("utf-8", "ignore")
    except Exception:
        return ""
    lines: list[str] = []
    for block in re.split(r"\n\s*\n", raw):
        if "-->" not in block:
            continue
        for ln in block.splitlines():
            if "-->" in ln or ln.strip().isdigit() or not ln.strip():
                continue
            lines.append(ln.strip())
    return " ".join(lines)


def fetch_srts(clips: list[dict], *, workers: int = 8) -> list[dict]:
    """Lädt je Clip die korrigierte `.srt` (CDN, parallel) → clip['text']."""
    with ThreadPoolExecutor(max_workers=workers) as ex:
        texts = list(ex.map(lambda c: _srt_text(c["srt"]), clips))
    for c, t in zip(clips, texts):
        c["text"] = t
    return [c for c in clips if c.get("text")]  # nur Clips mit Untertitel
