"""
Sound-Event-Detection (PANNs) — Beifall, Buhrufe, Lachen, Lautstärke aus Audio.

Reines ASR erfasst Saalreaktionen nicht (siehe Gap-Analyse: Recall 0 %). PANNs
(AudioSet, 527 Klassen, frame-weise via Cnn14_DecisionLevelAtt) schließt die
Lücke: erkennt *Applause/Cheering* (Beifall/Jubel), *Booing* (Buhrufe),
*Laughter* (Lachen), *Crowd/Hubbub* (Unruhe) — mit Zeitstempel und, über den
RMS-Pegel, einer **Lautstärke/Intensität**. Das ergänzt den Audio-Pfad genau dort,
wo das amtliche `<kommentar>` fehlt (z. B. wenn nur das Video vorliegt).

Produktivpfad: `detect_events(audio)` mit `panns_inference`.
Demopfad: `load_events(json)` lädt vorab berechnete SED-Ausgaben (ohne Modell/Audio).
"""

from __future__ import annotations

import json
from pathlib import Path

# AudioSet-Klasse -> unser Ereignistyp (passend zu den amtlichen <kommentar>-Typen)
AUDIOSET_MAP = {
    "Applause": "Beifall", "Cheering": "Beifall", "Clapping": "Beifall",
    "Booing": "Missfallen",
    "Laughter": "Lachen", "Giggle": "Lachen", "Chuckle, chortle": "Lachen",
    "Crowd": "Unruhe", "Hubbub, speech noise, speech babble": "Unruhe", "Chatter": "Unruhe",
}


def _intensitaet(db: float) -> str:
    """RMS-Pegel (dBFS) -> Lautstärke-Stufe."""
    if db >= -18:
        return "stark"
    if db >= -30:
        return "mittel"
    return "vereinzelt"


def detect_events(audio_path: str | Path, *, threshold: float = 0.4,
                  sample_rate: int = 32000) -> list[dict]:
    """Echte SED via PANNs. Liefert [{label, typ, start_sec, end_sec, score, db, intensitaet}]."""
    import numpy as np  # lazy
    import librosa
    from panns_inference import SoundEventDetection, labels

    audio, _ = librosa.load(str(audio_path), sr=sample_rate, mono=True)
    sed = SoundEventDetection(checkpoint_path=None, device="cpu")
    framewise = sed.inference(audio[None, :])[0]  # (frames, 527)
    fps = framewise.shape[0] / (len(audio) / sample_rate)
    targets = {i: AUDIOSET_MAP[l] for i, l in enumerate(labels) if l in AUDIOSET_MAP}

    events: list[dict] = []
    for cls_idx, typ in targets.items():
        active = framewise[:, cls_idx] >= threshold
        f = 0
        while f < len(active):
            if active[f]:
                start = f
                while f < len(active) and active[f]:
                    f += 1
                s0, s1 = start / fps, f / fps
                seg = audio[int(s0 * sample_rate):int(s1 * sample_rate)]
                rms = float(np.sqrt(np.mean(seg ** 2)) + 1e-9)
                db = 20.0 * float(np.log10(rms))
                events.append({"label": labels[cls_idx], "typ": typ,
                               "start_sec": round(s0, 1), "end_sec": round(s1, 1),
                               "score": round(float(framewise[start:f, cls_idx].max()), 2),
                               "db": round(db, 1), "intensitaet": _intensitaet(db)})
            else:
                f += 1
    return sorted(events, key=lambda e: e["start_sec"])


def load_events(events_json: str | Path) -> list[dict]:
    """Demopfad: vorab berechnete SED-Ausgaben laden."""
    data = json.loads(Path(events_json).read_text(encoding="utf-8"))
    out = []
    for e in data["events"]:
        e.setdefault("typ", AUDIOSET_MAP.get(e.get("label", ""), "Unruhe"))
        e.setdefault("intensitaet", _intensitaet(e.get("db", -40)))
        out.append(e)
    return out


def merge_into_protocol(protocol, events: list[dict]) -> int:
    """Ordnet SED-Ereignisse per Zeitstempel dem Redebeitrag/TOP zu und hängt sie
    als Saalreaktionen an `protocol.kommentare`. Gibt die Anzahl zurück."""
    # Utterance-Zeitfenster + zugehöriger TOP (aus den Redebeiträgen)
    idx_top = {}
    for r in protocol.redebeitraege:
        for i in r.get("quelle_utterances", []):
            idx_top[i] = r["top_nummer"]
    fenster = [(i, u.start, u.end) for i, u in enumerate(protocol.utterances)]

    n = 0
    for e in events:
        t = e["start_sec"]
        rede_index = next((i for i, s, en in fenster if s <= t < en), None)
        if rede_index is None and fenster:
            rede_index = min(fenster, key=lambda f: abs(f[1] - t))[0]
        top_nr = idx_top.get(rede_index, protocol.tops[0]["nummer"] if protocol.tops else 0)
        protocol.kommentare.append({
            "typ": e["typ"],
            "text": f"({e['typ']}, {e['intensitaet']}; SED {e.get('score','')})",
            "urheber": None, "top_nummer": top_nr, "rede_index": rede_index if rede_index is not None else -1,
            "start_sec": t, "intensitaet": e["intensitaet"], "herkunft": "audio-SED",
        })
        n += 1
    return n
