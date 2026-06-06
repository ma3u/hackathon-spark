"""
ASR — Automatische Spracherkennung (Audio → Wörter mit Zeitstempeln).

Produktivpfad: faster-whisper (CTranslate2-Backend), Modell large-v3, on-prem.
  - DSGVO: läuft vollständig lokal, kein Cloud-Versand von Bürger-/Sitzungsstimmen.
  - Deutsch: language="de" erzwingen, sonst rät Whisper bei kurzen Segmenten falsch.
  - word_timestamps=True liefert Wort-Offsets, die wir später mit den
    Sprecher-Segmenten der Diarisierung zusammenführen (siehe align.py).

Demopfad (ohne Modell/GPU/Netz): Wir reichen einen bereits transkribierten,
diarisierten Beispielmitschnitt durch, damit die Pipeline überall lokal läuft.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Word:
    start: float
    end: float
    text: str


@dataclass
class AsrResult:
    language: str
    duration_sec: float
    words: list[Word] = field(default_factory=list)
    # Im Demomodus tragen wir die fertigen Segmente direkt durch.
    raw_segments: list[dict] | None = None


def transcribe(audio_path: str | Path, *, language: str = "de", model_size: str = "large-v3") -> AsrResult:
    """Echte Transkription via faster-whisper. Nur aufgerufen, wenn das Modell verfügbar ist."""
    from faster_whisper import WhisperModel  # lazy: nur im Produktivpfad importiert

    model = WhisperModel(model_size, device="auto", compute_type="int8")
    segments, info = model.transcribe(
        str(audio_path),
        language=language,
        word_timestamps=True,
        vad_filter=True,  # Voice Activity Detection: Stille/Applaus rausfiltern
    )
    words: list[Word] = []
    for seg in segments:
        for w in seg.words or []:
            words.append(Word(start=w.start, end=w.end, text=w.word.strip()))
    return AsrResult(language=info.language, duration_sec=info.duration, words=words)


def load_pretranscribed(diarized_json: str | Path) -> AsrResult:
    """Demopfad: lädt einen vorab transkribierten + diarisierten Mitschnitt."""
    data = json.loads(Path(diarized_json).read_text(encoding="utf-8"))
    return AsrResult(
        language=data.get("language", "de"),
        duration_sec=float(data.get("duration_sec", 0.0)),
        raw_segments=data["segments"],
    )
