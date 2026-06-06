---
name: bundestag-ingestion
description: >-
  Use when working with official Bundestag data in graph-protokoll: parsing plenary-protocol
  XML (dbtplenarprotokoll DTD), Saalreaktionen from <kommentar>, fetching/resolving sessions
  (Open Data, DIP-API, Mediathek/YouTube), the dashboard/accessible outputs, or the
  protocol↔video gap analysis (WER). Trigger on ingest_bundestag.py, bundestag_xml.py,
  dashboard.py, accessible.py, gap_analysis.py, scripts/fetch-session.sh, *.xml tasks.
---

# Bundestag ingestion (official XML → graph → dashboard / accessibility / gap analysis)

The no-audio front: real Bundestag plenary data needs no ASR — the **official protocol XML**
is parsed directly and flows through the *same* `build_graph`, `factcheck`, and `neo4j_loader`
as the audio path. Entry point: `python3 ingest_bundestag.py [--xml prot.xml] [--load]`.

## Components

| File | Concern |
| ---- | ------- |
| `pipeline/bundestag_xml.py` | Parse `dbtplenarprotokoll` (WP19+) → `Protocol`. Reuses `extract._split_sentences`/`_is_checkable` for Aussagen. `<kommentar>` → Saalreaktionen (Beifall/Zuruf/Lachen/Widerspruch/Missfallen) via `_KOMMENTAR_TYP`. `herkunft="protokoll"`. |
| `pipeline/dashboard.py` | Per-session KPIs: Top-Themen by Redevolumen, Sprachanteil pro Fraktion, positive/negative Feedback (from Saalreaktionen: `POSITIV`/`NEGATIV`), Faktencheck-Bilanz → `web/data/*_dashboard.json`. |
| `pipeline/accessible.py` | Linear, screen-reader/TTS-ready text incl. **verbalized** Saalreaktionen (Beifall = Zustimmung, Widerspruch/Buhrufe = Ablehnung) → `*_barrierefrei.txt`. |
| `pipeline/gap_analysis.py` + `compare_protocol_video.py` | Protocol (gold) ↔ video-ASR gap: WER (Levenshtein S/I/D), Saalreaktions-Recall, speaker & content gaps. `simulate_asr` makes it reproducible without a real video. |
| `scripts/fetch-session.sh` · `scripts/resolve-session.py` | Pull official sources (Open Data XML, DIP-API w/ `DIP_API_KEY`, YouTube/Mediathek subtitles+audio via `yt-dlp`). **Run on the user's machine** — the sandbox has no access to bundestag.de/DIP/YouTube. |

## When editing

- The parser must keep producing a `Protocol` interchangeable with the audio front — same
  fields, same `quelle_utterances` provenance, so downstream code stays shared. Don't fork it.
- `<kommentar>` is the official source of Saalreaktionen; map new reaction wordings in
  `_KOMMENTAR_TYP`, and keep `POSITIV`/`NEGATIV` (dashboard) and `_REAKTION_WORT`
  (accessible) consistent with any new type.
- **Korrekturrecht caveat:** the published protocol is the corrected gold standard, which
  legitimately differs from the spoken word — model protocol↔ASR differences as a *diff*, not
  as ASR being "wrong" (see `docs/challenge-plan.md` risks).
- Accessibility output targets blind/low-vision users — keep it linear, plain-language, and
  TTS-friendly; don't regress it into graph-speak.
- Fetch scripts: don't try to run them in-session (no network). Tell the user to run them
  locally; suggest `! ./scripts/fetch-session.sh 21 81`.
- Real Bundestag protocols are amtliche Werke (§5 UrhG, public domain); Mediathek video
  license + biometrics are open questions (`docs/fragen-bundestag.md`). Demo data stays fictional.

## Real data (`data/real/`)

A real, gemeinfreie official protocol is bundled: `data/real/plenarprotokoll-20-214.xml`
(WP20/214). It produces the `bundestag_real` scenario via:

```bash
python3 ingest_bundestag.py --xml data/real/plenarprotokoll-20-214.xml \
    --name bundestag_real --no-factcheck
```

- `ingest_bundestag.py` flags: `--name <scenario>` (web/data output name) and `--no-factcheck`
  (skip fact-check entirely).
- **Hard policy:** real, named people are ingested with `--no-factcheck` — no automatic
  `Faktencheck`/`Quelle`/`GEPRUEFT_ALS` verdicts on real persons get published. Neutral
  `Aussage` nodes (public speech) and Saalreaktionen are fine. See `[[fact-checking]]` and
  `docs/spark-und-echtdaten.md`.
- Real XML lives in `<sitzungsverlauf>` (`sitzungsbeginn`/`tagesordnungspunkt`/`zusatzpunkt`/
  `sitzungsende`); the parser assigns sequential, collision-free TOP numbers. Written speeches
  in `<anlagen>` ("zu Protokoll gegebene Reden") are a separate, not-yet-ingested category.

## Verify

`python3 ingest_bundestag.py` (fictional sample) · the real command above (`bundestag_real`) ·
`python3 compare_protocol_video.py` (gap self-test). All run on Python 3.11 stdlib.
