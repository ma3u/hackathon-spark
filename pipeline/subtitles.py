"""
Untertitel-Transkription — VTT/SRT aus dem Video als Transkriptquelle.

„Findet ihr hier auch die Transkription?" — Ja: Bundestags-Videos (YouTube/
Mediathek) tragen **Untertitel**. yt-dlp lädt sie (`--write-subs
--write-auto-subs --sub-lang de`), und dieser Parser macht daraus
sprecher-segmentierten Text — oft schneller/genauer als eigenes ASR und ohne GPU.

Hinweis: Untertitel haben i. d. R. **keine** Sprecher-Labels. Die Zuordnung kommt
wie sonst aus Diarisierung oder der amtlichen Rednerliste; sind im Untertitel
„Name:"-Präfixe vorhanden, werden sie übernommen.
"""

from __future__ import annotations

import re
from pathlib import Path

_TS = re.compile(r"(\d{1,2}):(\d{2}):(\d{2})[.,](\d{3})")
_NAME = re.compile(r"^([A-ZÄÖÜ][\w.\- ]{2,40}?):\s+")


def _sec(h, m, s, ms) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def parse(path: str | Path) -> list[dict]:
    """VTT oder SRT -> [{start, end, speaker, text}] (speaker default 'UNBEKANNT')."""
    raw = Path(path).read_text(encoding="utf-8", errors="ignore")
    blocks = re.split(r"\n\s*\n", raw)
    segments: list[dict] = []
    for block in blocks:
        ts = [m for m in _TS.finditer(block)]
        if len(ts) < 2:
            continue
        start = _sec(*ts[0].groups())
        end = _sec(*ts[1].groups())
        # Textzeilen = alles nach der Zeitstempelzeile, ohne Cue-Settings/Index
        lines = []
        for ln in block.splitlines():
            if "-->" in ln or ln.strip().isdigit() or ln.strip().upper() == "WEBVTT":
                continue
            ln = re.sub(r"<[^>]+>", "", ln).strip()  # VTT-Inline-Tags entfernen
            if ln:
                lines.append(ln)
        if not lines:
            continue
        text = " ".join(lines)
        speaker = "UNBEKANNT"
        mn = _NAME.match(text)
        if mn:
            speaker = mn.group(1).strip()
            text = text[mn.end():]
        segments.append({"start": round(start, 2), "end": round(end, 2),
                         "speaker": speaker, "text": text})
    return _merge_same_speaker(segments)


def _merge_same_speaker(segs: list[dict]) -> list[dict]:
    """Aufeinanderfolgende Cues desselben Sprechers zu Redebeiträgen bündeln."""
    out: list[dict] = []
    for s in segs:
        if out and out[-1]["speaker"] == s["speaker"]:
            out[-1]["end"] = s["end"]
            out[-1]["text"] += " " + s["text"]
        else:
            out.append(dict(s))
    return out


def to_diarized(path: str | Path, *, audio_file: str = "video.mp3") -> dict:
    """Untertitel -> dieselbe Struktur wie ein diarisierter Mitschnitt (für die Pipeline)."""
    segs = parse(path)
    speakers = sorted({s["speaker"] for s in segs})
    speaker_map = {s: {"name": s, "rolle": "Redner", "fraktion": None} for s in speakers}
    # Sprecher-Label je Segment auf speaker_map-Schlüssel setzen
    for s in segs:
        s["speaker"] = s["speaker"]
    return {
        "audio_file": audio_file, "language": "de",
        "duration_sec": segs[-1]["end"] if segs else 0.0,
        "asr_model": "YouTube/Mediathek-Untertitel (kein eigenes ASR)",
        "diarization_model": "Untertitel-Sprecherpräfix / extern",
        "speaker_map": speaker_map, "segments": segs,
    }
