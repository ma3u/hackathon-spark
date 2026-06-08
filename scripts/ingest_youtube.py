#!/usr/bin/env python3
"""
YouTube-Mitschnitt → Graph + **LLM-Faktencheck** (Azure Mistral) mit echten
**Zeit-Deeplinks** (`youtube.com/watch?v=…&t=<sek>`).

Im Gegensatz zum amtlichen XML tragen YouTube-Untertitel Zeitstempel → jede Passage und
jede geprüfte Aussage ist sekundengenau im Video belegbar. Der Faktencheck nutzt Mistral
(on-prem/Azure, .env) und ist über reale Personen ausdrücklich ein **KI-Vorschlag
(ungeprüft)** mit Disclaimer — kein Urteil.

Quelle: @bundestag-Untertitel (Auto-Captions; keine Sprecher-Labels) → Provenienz ist der
Zeit-Deeplink ins Video. Erzeugt das Pages-Szenario `bundestag_yt` (LLM-Output wird
committet, da CI keinen Azure-Zugang hat).

  python scripts/ingest_youtube.py   # liest .env (Azure-Key)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from dotenv import load_dotenv  # noqa: E402
load_dotenv(REPO / ".env")

from pipeline import subtitles, extract, factcheck, graph_build, export, dashboard, accessible  # noqa: E402
from pipeline.align import Utterance  # noqa: E402

VTT = REPO / "data" / "real" / "bundestag-yt-21-081-arbeitszeit.de.vtt"
VIDEO_ID = "CPa1rLMiv64"
TITEL = "Arbeitszeitpolitik (ZP 8/9)"
DATUM = "22.05.2026"
MAX_CLAIMS = 12
WEB = REPO / "web" / "data"
OUT = REPO / "output"
NAME = "bundestag_yt"


def build_protocol():
    segs = subtitles.youtube_segments(VTT)
    p = extract.Protocol()
    p.meeting = {"gremium": "Deutscher Bundestag (YouTube-Mitschnitt)", "datum": DATUM,
                 "wahlperiode": "21", "sitzung_nr": "81", "ort": "Berlin"}
    p.tops = [{"nummer": 1, "titel": TITEL, "quelle_utterances": []}]
    for i, s in enumerate(segs):
        p.utterances.append(Utterance(
            start=float(s["start"]), end=float(s["end"]), speaker_label=f"S{i}",
            speaker_name="Sprecher:in (Video)", rolle="Redner:in", fraktion=None,
            text=s["text"], herkunft="audio"))  # herkunft=audio → timecode mm:ss
    return p


def main() -> int:
    if "AZURE_AI_API_KEY" not in os.environ:
        sys.exit("AZURE_AI_API_KEY fehlt (.env) — für den LLM-Faktencheck nötig.")
    p = build_protocol()
    # Transkript in ~14 Abschnitte bündeln; jeder Abschnitt → LLM extrahiert + prüft echte Claims
    n, step = len(p.utterances), max(1, len(p.utterances) // 14)
    passages = [{"text": " ".join(u.text for u in p.utterances[i:i + step]),
                 "utt_index": i, "start": p.utterances[i].start}
                for i in range(0, n, step)]
    print(f"YouTube {VIDEO_ID}: {n} Segmente → {len(passages)} Abschnitte")
    print(f"LLM-Extraktion + Faktencheck via {os.environ.get('MISTRAL_DEPLOYMENT','Mistral-Large-3')} …")
    res = factcheck.factcheck_transcript_llm(
        passages, model=os.environ.get("MISTRAL_DEPLOYMENT", "Mistral-Large-3"),
        base_url=os.environ["AZURE_AI_ENDPOINT"], api_key=os.environ["AZURE_AI_API_KEY"])
    # echte Claims → Aussagen + FactCheck-Objekte (Provenienz: Segment-Index/Startzeit)
    p.aussagen, checks = [], []
    for i, r in enumerate(res):
        p.aussagen.append({"text": r["aussage"], "person": "Sprecher:in (Video)", "fraktion": None,
                           "top_nummer": 1, "quelle_utterances": [r["utt_index"]]})
        checks.append(factcheck.FactCheck(
            aussage_index=i, text=r["aussage"], person="Sprecher:in (Video)", fraktion=None,
            top_nummer=1, verdikt=r["verdikt"], begruendung=r["begruendung"], quelle=r["quelle"],
            quelle_utterances=[r["utt_index"]], score=0.0))
    from collections import Counter
    print(f"   {len(checks)} echte Aussagen geprüft — Verdikte:", dict(Counter(c.verdikt for c in checks)))

    graph = graph_build.build_graph(p, audio_file=f"{VIDEO_ID}.mp4",
                                    sitzung_id="sitzung_bt_yt_21_81", factchecks=checks)
    # Provenienz-Hinweis + Video-ID in die Metadaten (für Deeplinks im Frontend)
    graph["metadata"]["video_id"] = VIDEO_ID
    graph["metadata"]["quelle_url"] = f"https://www.youtube.com/watch?v={VIDEO_ID}"
    graph["metadata"]["factcheck_disclaimer"] = (
        "Faktencheck automatisch durch KI (Mistral) erzeugt — ungeprüfte Vorschläge, kein "
        "Urteil über reale Personen. Untertitel sind Auto-Transkription (Fehler möglich).")

    WEB.mkdir(parents=True, exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)
    export.write_json(graph, WEB / f"{NAME}.json")
    export.write_json(graph, OUT / f"{NAME}_graph_data.json")
    export.write_json(dashboard.compute_dashboard(p, checks), WEB / f"{NAME}_dashboard.json")
    (WEB / f"{NAME}_barrierefrei.txt").write_text(accessible.summarize(p, checks), encoding="utf-8")
    print(f"✓ {graph['metadata']['node_count']} Knoten → web/data/{NAME}.json (+ dashboard, barrierefrei)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
