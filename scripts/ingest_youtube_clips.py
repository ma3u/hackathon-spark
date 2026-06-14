#!/usr/bin/env python3
"""
@bundestag/videos-Clips je TOP → yt_-Graph (Discovery via YouTube Data API v3, ADR-0013).

Für Sitzungen OHNE Gesamt-Stream: die offizielle API listet die Clips (TOP-Thema + Deeplink),
yt-dlp holt optional die Auto-Untertitel. Erzeugt web/data/yt_<wp>_<nr>.* (+ Neo4j mit --load).

  python scripts/ingest_youtube_clips.py 83                  # Discovery + Untertitel → Graph
  python scripts/ingest_youtube_clips.py 83 --no-captions    # nur Struktur (schnell, ohne yt-dlp)
  python scripts/ingest_youtube_clips.py 83 --yt-dlp         # Discovery per yt-dlp statt Data API
  python scripts/ingest_youtube_clips.py 83 --load           # zusätzlich nach Neo4j (yt_)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
try:
    from dotenv import load_dotenv  # optional: nur um .env zu lesen
    load_dotenv(REPO / ".env")
except ModuleNotFoundError:
    pass

from pipeline import session_ingest  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="YouTube-Clips je TOP → yt_-Graph (Data API v3)")
    ap.add_argument("nr", type=int, help="Sitzungsnummer (WP21)")
    ap.add_argument("--wp", type=int, default=21, help="Wahlperiode (default 21)")
    ap.add_argument("--no-captions", action="store_true",
                    help="ohne Auto-Untertitel (nur Struktur — schnell, kein yt-dlp)")
    ap.add_argument("--yt-dlp", dest="yt_dlp", action="store_true",
                    help="Discovery per yt-dlp statt YouTube Data API")
    ap.add_argument("--load", action="store_true", help="zusätzlich nach Neo4j (yt_) laden")
    ap.add_argument("--no-web", dest="no_web", action="store_true", help="keine web/data-Ausgaben")
    ap.add_argument("--factcheck", action="store_true", help="LLM-Faktencheck (Azure, .env)")
    args = ap.parse_args()

    az = None
    if args.factcheck:
        if "AZURE_AI_API_KEY" not in os.environ:
            sys.exit("AZURE_AI_API_KEY fehlt (.env) — für --factcheck nötig.")
        az = {"model": os.environ.get("MISTRAL_DEPLOYMENT", "Mistral-Large-3"),
              "base_url": os.environ["AZURE_AI_ENDPOINT"], "api_key": os.environ["AZURE_AI_API_KEY"]}

    if not args.yt_dlp and "YOUTUBE_API_KEY" not in os.environ:
        sys.exit("YOUTUBE_API_KEY fehlt (.env) — für die Data-API-Discovery. Alternativ --yt-dlp.")

    disc = "yt-dlp" if args.yt_dlp else "YouTube Data API v3"
    print(f"Discovery via {disc} → Sitzung {args.wp}/{args.nr} …")
    res = session_ingest.ingest_youtube_clips(
        wp=args.wp, nr=args.nr, az=az, load=args.load, write_web=not args.no_web,
        use_api=not args.yt_dlp, captions=not args.no_captions)
    if res is None:
        print(f"⚠ keine Clips für Sitzung {args.wp}/{args.nr} gefunden.")
        return 1
    print(f"✓ {res['name']}: {res['clips']} Clips → {res['tops']} TOPs, "
          f"{res['nodes']} Knoten / {res['rels']} Beziehungen, {res['checks']} Faktenchecks "
          f"(Discovery: {res['discovery']})")
    if not args.no_web:
        print(f"  → web/data/{res['name']}.json (+ _dashboard.json, _protokoll.html, _barrierefrei.txt)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
