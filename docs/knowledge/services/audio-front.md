---
type: service
title: Audio front (asr · diarize · align)
description: Audio → speaker-attributed Utterances; one of the two input fronts.
resource: pipeline/align.py
tags: [service, audio, asr, diarization, alignment, produktivpfad, demopfad]
timestamp: 2026-06-14
---

# Audio front — asr · diarize · align

Turns a recording into speaker-attributed `Utterance`s that feed extraction.

| Module | Produktivpfad | Demopfad |
| ------ | ------------- | -------- |
| `asr.py` | `transcribe` — faster-whisper large-v3, `language="de"`, word timestamps, VAD | `load_pretranscribed` |
| `diarize.py` | `diarize` — pyannote/speaker-diarization-3.1 | `load_diarized` |
| `align.py` | `align` — WhisperX forced alignment → `Utterance`s | `from_pretranscribed` |

## Notes

- Diarisierung ≠ Identifikation: anonymous `SPEAKER_xx` → real person via Voice-Enrollment /
  Rednerliste (`speaker_map`). Voice embeddings are biometric (Art. 9 DSGVO) — store only with a
  legal basis, else discard per session.
- Sound events: `sound_events.py` (`detect_events` PANNs/AudioSet ↔ `load_events`).
- Skill: `audio-transcription`. **Source:** `README.md:60-109`; `.claude/rules/code-style.md`.
