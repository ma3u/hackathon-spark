"""
Diarisierung — "wer spricht wann?" (Audio → Sprecher-Segmente).

Produktivpfad: pyannote.audio (pyannote/speaker-diarization-3.1).
  - Liefert anonyme Sprecher-Labels (SPEAKER_00, SPEAKER_01, ...) je Zeitfenster.
  - Die Zuordnung Label -> echte Person erfolgt NICHT durch das Modell, sondern
    über ein Voice-Enrollment beim Sitzungsbeginn (Namensaufruf/Anwesenheit) oder
    über die Rednerliste. Wir kapseln das in `speaker_map`.
  - DSGVO-Hinweis: Stimmprofile sind biometrische Daten (Art. 9 DSGVO). Enrollment-
    Embeddings nur mit Rechtsgrundlage speichern, sonst pro Sitzung verwerfen.

Demopfad: speaker_map und Segmente liegen im Beispiel bereits vor.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class SpeakerTurn:
    start: float
    end: float
    speaker: str  # anonymes Label, z. B. "SPEAKER_02"


def diarize(audio_path: str | Path, *, num_speakers: int | None = None) -> list[SpeakerTurn]:
    """Echte Diarisierung via pyannote. Nur im Produktivpfad aufgerufen."""
    from pyannote.audio import Pipeline  # lazy import

    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")
    diarization = pipeline(str(audio_path), num_speakers=num_speakers)
    turns: list[SpeakerTurn] = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        turns.append(SpeakerTurn(start=turn.start, end=turn.end, speaker=speaker))
    return turns


def resolve_speaker(label: str, speaker_map: dict[str, dict]) -> dict:
    """Anonymes Label -> Person/Rolle/Fraktion. Fällt sauber auf 'Unbekannt' zurück."""
    return speaker_map.get(
        label,
        {"name": f"Unbekannt ({label})", "rolle": "unbekannt", "fraktion": None},
    )
