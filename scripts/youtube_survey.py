#!/usr/bin/env python3
"""
Survey: @bundestag/videos-Clip-Abdeckung ALLER WP21-Sitzungen über die YouTube Data API v3.

EIN Voll-Scan der Uploads-Playlist (günstig), gruppiert nach Sitzungsnummer → Vollständigkeits-
Bericht (welche Sitzung hat wie viele Clips). Schreibt output/youtube_survey.json (gitignored)
und gibt eine Übersicht aus. Grundlage für Bulk-Ingestion + den Aggregat-Dashboard.

  python scripts/youtube_survey.py            # Sitzungen 1..81
  python scripts/youtube_survey.py --to 90
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

from pipeline import youtube_api  # noqa: E402

OUT = REPO / "output"


def main() -> int:
    ap = argparse.ArgumentParser(description="YouTube-Clip-Abdeckung der WP21-Sitzungen")
    ap.add_argument("--wp", type=int, default=21)
    ap.add_argument("--from", dest="frm", type=int, default=1)
    ap.add_argument("--to", type=int, default=81)
    args = ap.parse_args()

    print("Scanne @bundestag-Uploads (ein Durchlauf) …")
    by_session = youtube_api.all_session_clips()
    rng = range(args.frm, args.to + 1)
    sessions = {}
    for nr in rng:
        clips = by_session.get(nr, [])
        tops = sorted({c["top"] for c in clips})
        sessions[nr] = {
            "clips": len(clips), "tops": len(tops),
            "sample_topics": [c["topic"] for c in clips[:3]],
        }
    with_clips = [nr for nr in rng if sessions[nr]["clips"]]
    without = [nr for nr in rng if not sessions[nr]["clips"]]
    total_clips = sum(sessions[nr]["clips"] for nr in rng)

    OUT.mkdir(parents=True, exist_ok=True)
    report = {"wp": args.wp, "range": [args.frm, args.to],
              "total_clips": total_clips, "sessions_with_clips": len(with_clips),
              "sessions_without_clips": without, "sessions": sessions}
    (OUT / "youtube_survey.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nWP{args.wp} Sitzungen {args.frm}–{args.to}:")
    print(f"  mit Clips:   {len(with_clips)}/{len(list(rng))}  ({total_clips} Clips gesamt)")
    print(f"  ohne Clips:  {len(without)}  {without if len(without) <= 30 else str(without[:30]) + ' …'}")
    print(f"  Top-5 Sitzungen nach Clipzahl:")
    for nr in sorted(with_clips, key=lambda n: -sessions[n]["clips"])[:5]:
        print(f"    Sitzung {nr}: {sessions[nr]['clips']} Clips")
    print(f"→ output/youtube_survey.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
