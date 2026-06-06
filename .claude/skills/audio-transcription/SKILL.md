---
name: audio-transcription
description: >-
  Use when working on the audio→text front of graph-protokoll: speech recognition (ASR),
  speaker diarization, word/speaker alignment, sound-event detection (Beifall/Buhrufe/Lachen),
  or subtitle/VTT ingestion. Trigger on tasks touching pipeline/asr.py, diarize.py, align.py,
  sound_events.py, subtitles.py, faster-whisper, pyannote, WhisperX, PANNs, or `--audio` runs.
---

# Audio transcription (ASR → Diarisierung → Alignment → SED)

Turns a meeting recording into **speaker-attributed `Utterance`s** — the canonical input the
extraction step consumes. Mirrors the official-XML front (`bundestag_xml.py`), which produces
the same `Utterance`/`Protocol` shape without audio.

## Module map

| File | Concern | Produktivpfad | Demopfad |
| ---- | ------- | ------------- | -------- |
| `pipeline/asr.py` | speech → words+times | `transcribe` (faster-whisper large-v3, `language="de"`, `word_timestamps`, VAD) | `load_pretranscribed` (sample JSON) |
| `pipeline/diarize.py` | who speaks when | `diarize` (pyannote 3.1) → anonymous `SPEAKER_xx` | sample segments; `resolve_speaker` maps label→person |
| `pipeline/align.py` | word↔speaker → `Utterance` | `align` (max time-overlap) | `from_pretranscribed` |
| `pipeline/sound_events.py` | Beifall/Buhrufe/Lachen + loudness | `detect_events` (PANNs/AudioSet, RMS→intensität) | `load_events` |
| `pipeline/subtitles.py` | VTT/SRT → diarized JSON | `parse` / `to_diarized` (stdlib) | same (no model needed) |

Entry point: `python3 run_demo.py --audio path/to.mp3` exercises `transcribe → diarize →
align`; without `--audio` it loads the pre-transcribed sample.

## Key facts to respect

- **Diarisierung ≠ identification.** pyannote yields anonymous labels; the label→person map
  (`speaker_map`) comes from voice enrollment at roll-call or the Rednerliste — never invent
  it. Voice embeddings are **biometric data (Art. 9 DSGVO)**: store only with a legal basis,
  otherwise discard per session. Keep these comments.
- **On-prem only.** ASR + diarization + LLM run locally; no recording leaves the building.
  Don't add cloud calls to this front.
- Heavy deps (`faster_whisper`, `pyannote`, `librosa`, `numpy`, `panns_inference`) stay
  **lazy-imported inside functions**. The sample path must run on stdlib.
- `Utterance.timecode` is `mm:ss` for `herkunft="audio"`, `"Prot."` otherwise. SED events
  merge into `protocol.kommentare` with `herkunft="audio-SED"` and a `start_sec`.
- `AUDIOSET_MAP` maps AudioSet class → German Saalreaktion type (`Beifall`, `Missfallen`,
  `Lachen`, `Unruhe`); align any new mapping with the official `<kommentar>` types.

## Verify

`python3 run_demo.py` (sample path) and `python3 compare_protocol_video.py` (WER /
Saalreaktions-Recall — recall is 0 for plain ASR, which is exactly why SED exists).
