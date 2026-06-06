#!/usr/bin/env python3
"""
Lückentest: amtliches Plenarprotokoll (Goldstandard) vs. ASR aus dem Video.

  python compare_protocol_video.py                 # Selbsttest (simuliertes ASR)
  python compare_protocol_video.py --xml P.xml --asr asr.json
       asr.json = {"text": "...", "speakers": ["..."], "sed_erkannt": 0}

Für echte Daten: scripts/fetch-session.sh lädt XML (Open Data) + Video-Audio
(YouTube/Mediathek); den ASR-Pfad liefert run_demo.py --audio … (Whisper).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline import bundestag_xml, gap_analysis

HERE = Path(__file__).parent
SAMPLE_XML = HERE / "data" / "sample" / "plenarprotokoll-21-081-sample.xml"


def main() -> None:
    ap = argparse.ArgumentParser(description="Protokoll ↔ Video-ASR Gap-Analyse")
    ap.add_argument("--xml", type=Path, default=SAMPLE_XML)
    ap.add_argument("--asr", type=Path, help="ASR-JSON {text, speakers, sed_erkannt}")
    args = ap.parse_args()

    protocol = bundestag_xml.parse_plenarprotokoll(args.xml)
    if args.asr:
        a = json.loads(args.asr.read_text(encoding="utf-8"))
        asr_text, speakers, sed = a.get("text", ""), set(a.get("speakers", [])), a.get("sed_erkannt", 0)
    else:
        print("ℹ️  Selbsttest: simuliertes ASR aus dem amtlichen XML.")
        asr_text, speakers = gap_analysis.simulate_asr(protocol)
        sed = 0

    report = gap_analysis.analyze_gaps(protocol, asr_text, asr_speakers=speakers, sed_erkannt=sed)

    print("\n══ Gap-Report: Protokoll ↔ Video-ASR ══")
    w = report["wer"]
    print(f"WER: {w['wer']:.1%}  (S {w['subst']} / I {w['ins']} / D {w['del']}, "
          f"{w['ref_woerter']} Ref-Wörter)")
    r = report["reaktionen"]
    print(f"Saalreaktionen: {r['asr_erkannt']}/{r['amtlich']} erkannt (Recall {r['recall']:.0%}) — {r['hinweis']}")
    print(f"Sprecher fehlend im ASR: {report['sprecher']['fehlend_in_asr'] or 'keine'}")
    if report["inhalts_luecken"]:
        print("Inhalts-Lücken:")
        for l in report["inhalts_luecken"]:
            print(f"  • [{l['abdeckung']:.0%}] {l['sprecher']}: {l['satz']} …")
    print("\nBewertung:")
    for b in report["bewertung"]:
        print(f"  – {b}")

    out = HERE / "output" / "gap_report.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n→ {out}")


if __name__ == "__main__":
    main()
