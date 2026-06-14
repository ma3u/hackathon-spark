#!/usr/bin/env python3
"""
Bulk-Ingestion ALLER WP21-Sitzungen mit @bundestag/videos-Clips → yt_-Strukturgraphen.

EIN Data-API-Scan (youtube_api.all_session_clips), dann je Sitzung mit Clips ein
Strukturgraph (TOP-Themen + Video-Deeplink je Clip; Personen global). Untertitel + LLM-
Faktencheck sind hier bewusst AUS (Kosten/Zeit) — Discovery/Struktur „komplettiert" alle
verfügbaren Sitzungen. Vollgraphen → output/ (gitignored); kompakte Vollständigkeits-
Übersicht → web/data/youtube_completeness.json (committet, treibt Tracker + Dashboard).

  python scripts/ingest_all_youtube_clips.py           # Sitzungen 1..81
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
try:
    from dotenv import load_dotenv
    load_dotenv(REPO / ".env")
except ModuleNotFoundError:
    pass

from pipeline import youtube_api, session_ingest, graph_build, export  # noqa: E402

OUT = REPO / "output"
WEB = REPO / "web" / "data"


def main() -> int:
    ap = argparse.ArgumentParser(description="Bulk YouTube-Clip-Ingestion (Struktur) WP21")
    ap.add_argument("--wp", type=int, default=21)
    ap.add_argument("--from", dest="frm", type=int, default=1)
    ap.add_argument("--to", type=int, default=81)
    args = ap.parse_args()

    print("Scanne @bundestag-Uploads (ein Durchlauf) …")
    by = youtube_api.all_session_clips()
    OUT.mkdir(parents=True, exist_ok=True)
    WEB.mkdir(parents=True, exist_ok=True)

    sessions, ok, total_nodes = {}, 0, 0
    for nr in range(args.frm, args.to + 1):
        clips = by.get(nr, [])
        nnn = f"{nr:03d}"
        if not clips:
            sessions[nr] = {"clips": 0, "status": "keine_clips"}
            continue
        p, _ = session_ingest.clips_protocol(clips, wp=args.wp, nr=nr)
        g = graph_build.build_graph(p, audio_file=f"yt_clips_{args.wp}_{nnn}",
                                    sitzung_id=f"sitzung_yt_{args.wp}_{nnn}")
        g["metadata"].update(herkunft="youtube", quelle_typ="youtube",
                             clips=len(clips), discovery="youtube_data_api_v3")
        export.write_json(g, OUT / f"yt_{args.wp}_{nnn}_graph_data.json")  # gitignored Vollgraph
        sessions[nr] = {"clips": len(clips), "tops": len(p.tops),
                        "nodes": g["metadata"]["node_count"],
                        "rels": g["metadata"]["relationship_count"],
                        "topics": [c["topic"] for c in clips], "status": "ingested"}
        ok += 1
        total_nodes += g["metadata"]["node_count"]

    summary = {
        "generated_for": f"WP{args.wp} {args.frm}-{args.to}",
        "sessions_total": args.to - args.frm + 1,
        "sessions_ingested": ok,
        "sessions_without_clips": sorted(nr for nr in sessions if sessions[nr]["clips"] == 0),
        "total_clips": sum(s["clips"] for s in sessions.values()),
        "total_nodes": total_nodes,
        "sessions": sessions,
    }
    (WEB / "youtube_completeness.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✓ {ok}/{summary['sessions_total']} Sitzungen mit Clips strukturell ingestiert "
          f"({summary['total_clips']} Clips, {total_nodes} Knoten)")
    print(f"  ohne Clips: {len(summary['sessions_without_clips'])} "
          f"{summary['sessions_without_clips']}")
    print(f"  → output/yt_{args.wp}_*_graph_data.json (Vollgraphen, gitignored)")
    print(f"  → web/data/youtube_completeness.json (committet)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
