"""
YouTube-Clips (@bundestag/videos) — pro-Tagesordnungspunkt-Mitschnitte als Quelle.

Ergänzung zu den Gesamt-Streams (/streams, nur die jüngsten ~5): der /videos-Tab enthält
für viele Sitzungen je TOP einen Clip mit dem ECHTEN Thema im Titel
("78. Sitzung vom 08.05.2026. TOP 25: Betriebliche Mitbestimmungsrechte") + Auto-Untertiteln.
So bekommt auch eine Sitzung OHNE Gesamt-Stream einen YouTube-Graphen (TOP-Themen + Auto-
Transkript + Video-Deeplink je TOP). Hinweis: Auto-Captions ohne Sprecher → die Mediathek
(korrigiert, sprecher-attribuiert) bleibt die bessere offizielle Quelle.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import subtitles

CHANNEL = "https://www.youtube.com/@bundestag/videos"
# "78. Sitzung vom 08.05.2026. TOP 25: Betriebliche Mitbestimmungsrechte" /
# "78. Sitzung, TOP 23: Windenergie" / "… ZP 12: …"
_NR = re.compile(r"(\d+)\.\s*Sitzung")
_TOP = re.compile(r"\b((?:TOP|ZP)\s*[\w ]*?\d[\w ]*?):\s*(.+)$")


def collect_session(nr, *, max_items: int = 500) -> list[dict]:
    """@bundestag/videos → Clips EINER Sitzung [{video_id, top, topic, url}] (deutsche Titel)."""
    nr = int(nr)
    try:
        out = subprocess.run(
            ["yt-dlp", "--flat-playlist", "--playlist-end", str(max_items),
             "--print", "%(id)s\t%(title)s", CHANNEL],
            capture_output=True, text=True, timeout=240, check=True).stdout
    except Exception as e:  # noqa: BLE001
        print(f"⚠ yt-dlp /videos fehlgeschlagen: {e}")
        return []
    clips: list[dict] = []
    for line in out.splitlines():
        if "\t" not in line:
            continue
        vid, title = line.split("\t", 1)
        m = _NR.search(title)
        if not m or int(m.group(1)) != nr or "Sitzung vom" not in title and ", TOP" not in title and ". TOP" not in title:
            continue
        mt = _TOP.search(title)
        top = mt.group(1).strip() if mt else "TOP"
        topic = mt.group(2).strip() if mt else title.split(".")[-1].strip()
        clips.append({"video_id": vid.strip(), "top": top, "topic": topic,
                      "url": f"https://www.youtube.com/watch?v={vid.strip()}"})
    # Reihenfolge im Feed ist neueste→älteste; Clips einer Sitzung umdrehen (TOP-Reihenfolge)
    clips.reverse()
    return clips


def _caption(video_id: str) -> str:
    """Auto-Untertitel eines Clips → Text (yt-dlp de, in ein Temp-Verzeichnis)."""
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "c"
        try:
            subprocess.run(
                ["yt-dlp", "--write-auto-subs", "--sub-langs", "de", "--convert-subs", "vtt",
                 "--skip-download", "-o", f"{out}.%(ext)s",
                 f"https://www.youtube.com/watch?v={video_id}"],
                capture_output=True, text=True, timeout=180, check=True)
        except Exception:
            return ""
        vtt = Path(f"{out}.de.vtt")
        if not vtt.exists():
            return ""
        segs = subtitles.youtube_segments(vtt, lines_per_seg=10_000)  # ein Block = ganzer Text
        return " ".join(s["text"] for s in segs)


def fetch_captions(clips: list[dict], *, workers: int = 4) -> list[dict]:
    """Lädt je Clip die Auto-Untertitel (parallel) → clip['text']."""
    with ThreadPoolExecutor(max_workers=workers) as ex:
        texts = list(ex.map(lambda c: _caption(c["video_id"]), clips))
    for c, t in zip(clips, texts):
        c["text"] = t
    return clips
