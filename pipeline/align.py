"""
Alignment — ASR-Wörter mit Sprecher-Segmenten zusammenführen.

Produktivpfad: WhisperX übernimmt forced alignment + Sprecher-Zuordnung
(jedem Wort wird per maximaler Zeitüberlappung ein Diarisierungs-Turn zugewiesen).
Ergebnis ist eine Liste sprecher-attribuierter Segmente — die kanonische Eingabe
für die Extraktion.

Demopfad: Die Beispiel-JSON enthält bereits sprecher-attribuierte Segmente.
"""

from __future__ import annotations

from dataclasses import dataclass

from .asr import AsrResult, Word
from .diarize import SpeakerTurn, resolve_speaker


@dataclass
class Utterance:
    """Ein zusammenhängender Redebeitrag eines Sprechers mit Audio-Zeitstempeln."""

    start: float
    end: float
    speaker_label: str
    speaker_name: str
    rolle: str
    fraktion: str | None
    text: str
    herkunft: str = "audio"  # "audio" (ASR) oder "protokoll" (amtliches XML)

    @property
    def timecode(self) -> str:
        if self.herkunft != "audio":
            return "Prot."
        m, s = divmod(int(self.start), 60)
        return f"{m:02d}:{s:02d}"


def _speaker_of(word: Word, turns: list[SpeakerTurn]) -> str:
    """Wort -> Sprecher-Label per maximaler Zeitüberlappung."""
    best, best_overlap = "SPEAKER_??", 0.0
    for t in turns:
        overlap = min(word.end, t.end) - max(word.start, t.start)
        if overlap > best_overlap:
            best, best_overlap = t.speaker, overlap
    return best


def align(asr: AsrResult, turns: list[SpeakerTurn], speaker_map: dict[str, dict]) -> list[Utterance]:
    """Produktivpfad: Wörter den Sprechern zuordnen und zu Utterances bündeln."""
    utterances: list[Utterance] = []
    cur_label, buf, c_start, c_end = None, [], 0.0, 0.0
    for w in asr.words:
        label = _speaker_of(w, turns)
        if label != cur_label and buf:
            utterances.append(_flush(cur_label, buf, c_start, c_end, speaker_map))
            buf = []
        if not buf:
            c_start = w.start
        cur_label, c_end = label, w.end
        buf.append(w.text)
    if buf:
        utterances.append(_flush(cur_label, buf, c_start, c_end, speaker_map))
    return utterances


def _flush(label, buf, start, end, speaker_map) -> Utterance:
    p = resolve_speaker(label, speaker_map)
    return Utterance(start, end, label, p["name"], p["rolle"], p.get("fraktion"), " ".join(buf))


def from_pretranscribed(segments: list[dict], speaker_map: dict[str, dict]) -> list[Utterance]:
    """Demopfad: fertige Segmente direkt in Utterances überführen."""
    out: list[Utterance] = []
    for s in segments:
        p = resolve_speaker(s["speaker"], speaker_map)
        out.append(
            Utterance(
                start=float(s["start"]),
                end=float(s["end"]),
                speaker_label=s["speaker"],
                speaker_name=p["name"],
                rolle=p["rolle"],
                fraktion=p.get("fraktion"),
                text=s["text"],
            )
        )
    return out
