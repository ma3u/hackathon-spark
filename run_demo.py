#!/usr/bin/env python3
"""
End-to-End-Demo: Sitzungsmitschnitt -> Protokoll-Graph -> Faktencheck -> GraphRAG.

Zwei Szenarien (beide ohne GPU/Modelle/Netz, stdlib only):
  • gemeinderat — kommunale Sitzung (Beschlüsse, Abstimmungen, Befangenheit, Aufgaben)
  • bundestag   — fiktive Plenardebatte (Reden, prüfbare Aussagen, Faktencheck, Frage)

Echtes Audio:  python run_demo.py --audio pfad/zur/sitzung.mp3 --scenario bundestag
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline import asr, align, extract, graph_build, export, factcheck, dashboard, accessible
from pipeline import sound_events
from pipeline.graphrag import GraphRAG

HERE = Path(__file__).parent
SAMPLES = {
    "gemeinderat": HERE / "data" / "sample" / "sitzung_2026-05-12.diarized.json",
    "bundestag": HERE / "data" / "sample" / "bundestag_2026-05-14.diarized.json",
}
DEFAULT_META = {
    "bundestag": {"gremium": "Deutscher Bundestag (fiktiv)", "datum": "14. Mai 2026",
                  "ort": "Plenarsaal (fiktiv)", "beschlussfaehig": ""},
}
EVIDENZ = HERE / "data" / "evidence" / "evidenz.json"
OUT = HERE / "output"
WEB = HERE / "web" / "data"


def build(scenario: str, audio: str | None) -> dict:
    sample = SAMPLES[scenario]
    data = json.loads(sample.read_text(encoding="utf-8"))
    if audio:
        print(f"🎙️  ASR (faster-whisper) … {audio}")
        from pipeline import diarize
        asr_res = asr.transcribe(audio, language="de")
        turns = diarize.diarize(audio)
        utterances = align.align(asr_res, turns, data["speaker_map"])
        audio_file = Path(audio).name
    else:
        print(f"🎧 [{scenario}] {data['audio_file']}  "
              f"({data['duration_sec']:.0f}s, {len(data['segments'])} Segmente)")
        asr_res = asr.load_pretranscribed(sample)
        utterances = align.from_pretranscribed(asr_res.raw_segments, data["speaker_map"])
        audio_file = data["audio_file"]

    protocol = extract.extract_rule_based(utterances)
    if not protocol.meeting and scenario in DEFAULT_META:
        protocol.meeting = dict(DEFAULT_META[scenario])

    # Sound-Event-Detection (PANNs): Beifall/Buhrufe/Lachen + Lautstärke aus Audio.
    # Echtes Audio → sound_events.detect_events(audio); hier: vorab berechnetes Sample.
    sed_file = HERE / "data" / "sample" / f"{scenario}_sound_events.json"
    if sed_file.exists():
        n = sound_events.merge_into_protocol(protocol, sound_events.load_events(sed_file))
        if n:
            print(f"   🔊 {n} Saalreaktionen via PANNs-SED erkannt (Beifall/Buhrufe/Lachen)")

    checks = factcheck.factcheck_rule_based(protocol.aussagen, EVIDENZ) if protocol.aussagen else []
    graph = graph_build.build_graph(protocol, audio_file=audio_file,
                                    sitzung_id=f"sitzung_{scenario}", factchecks=checks)

    OUT.mkdir(parents=True, exist_ok=True)
    WEB.mkdir(parents=True, exist_ok=True)
    export.write_json(graph, OUT / f"{scenario}_graph_data.json")
    export.write_json(graph, WEB / f"{scenario}.json")  # für GitHub Pages
    export.write_csv(graph, OUT / f"{scenario}_nodes.csv", OUT / f"{scenario}_relationships.csv")
    export.write_cypher(graph, OUT / f"{scenario}_neo4j_import.cypher")
    export.write_json(dashboard.compute_dashboard(protocol, checks), WEB / f"{scenario}_dashboard.json")
    (WEB / f"{scenario}_barrierefrei.txt").write_text(accessible.summarize(protocol, checks), encoding="utf-8")
    print(f"   📝 {len(protocol.redebeitraege)} Redebeiträge, {len(protocol.aussagen)} prüfbare Aussagen")
    print(f"   📦 {graph['metadata']['node_count']} Knoten, "
          f"{graph['metadata']['relationship_count']} Beziehungen → output/ + web/data/")
    return graph


def demo_queries(graph: dict, scenario: str) -> None:
    rag = GraphRAG(graph)
    if scenario == "gemeinderat":
        fragen = ["War die Sitzung beschlussfähig?", "Welche Beschlüsse wurden gefasst?",
                  "Wie war die Abstimmung zum Bücherbus?", "Wer war befangen?",
                  "Welche Aufgaben und Fristen wurden vergeben?"]
    else:
        fragen = ["Faktencheck?", "Welche Aufgaben und Fristen wurden vergeben?"]
    print("\n" + "=" * 74 + f"\n🤖 GraphRAG [{scenario}] — Antworten mit Audio-Beleg\n" + "=" * 74)
    for f in fragen:
        print(f"\n❓ {f}\n{rag.ask(f)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="graph-protokoll demo")
    ap.add_argument("--scenario", choices=["gemeinderat", "bundestag", "both"], default="both")
    ap.add_argument("--audio", help="Pfad zu echtem Audio (sonst: Demo-Beispiel)")
    ap.add_argument("--no-queries", action="store_true")
    args = ap.parse_args()
    scenarios = ["gemeinderat", "bundestag"] if args.scenario == "both" else [args.scenario]
    for sc in scenarios:
        g = build(sc, args.audio)
        if not args.no_queries:
            demo_queries(g, sc)
