"""
Mediathek-Deeplinks für ALLE WP21-Sitzungen ausweiten.

Der Mediathek-Podcast-Feed gibt zwar nur ~5 Sitzungen als YouTube-Stream frei, enthält
aber PRO REDE einen Clip (dbtg.tv/fvid) bis weit zurück (WP21 1–84). Dieses Skript crawlt
den Feed **einmal**, bucketet die Clips je Sitzung und:
  • setzt je Sitzung einen **Sitzungs-Deeplink** (erster Clip = Sitzungsbeginn),
  • ordnet (best-effort über Sprechername) Clips den Redebeiträgen zu (Trefferzahl),
  • patcht die committeten Pages-Graphen (web/data/amt_21_NNN.json) mit `video_url` je Rede,
  • aktualisiert data/real/sessions_state.json + web/data/sessions.json (Mediathek je Sitzung),
  • optional (--load): Neo4j `Redebeitrag.video_url` für ALLE Sitzungen (namespaced, parametrisiert).

Produktivpfad = Demopfad: stdlib + urllib, keine Modelle/GPU. Crawl wird unter
/tmp/mediathek_feed_cache.json gecacht, damit Wiederholläufe ohne Netz auskommen.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from pipeline import mediathek, session_ingest  # noqa: E402
import scripts.sync_sessions as sync  # noqa: E402

WEB = REPO / "web" / "data"
AMT_DIR = REPO / "data" / "real" / "amt"
STATE = REPO / "data" / "real" / "sessions_state.json"
CACHE = Path("/tmp/mediathek_feed_cache.json")

WP = "21"
WP21_MAX = 120  # WP21 hat aktuell ≤84 Sitzungen; ab hier (214,213,…) beginnt der WP20-Schwanz → Crawl-Stopp.


def crawl_feed(*, max_offset: int = 320, use_cache: bool = True) -> dict[int, list[dict]]:
    """Feed einmal von newest→oldest paginieren, Clips je WP21-Sitzung sammeln.

    Stoppt am WP21/WP20-Übergang (erste Sitzungsnummer ≥ WP21_MAX) bzw. bei 2 leeren Seiten.
    """
    if use_cache and CACHE.exists():
        raw = json.loads(CACHE.read_text(encoding="utf-8"))
        return {int(k): v for k, v in raw.items()}
    buckets: dict[int, list[dict]] = {}
    empty = 0
    for off in range(max_offset):
        try:
            items = mediathek._parse_items(mediathek._page(off))
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠ Seite {off}: {type(e).__name__} {e}")
            items = []
        if not items:
            empty += 1
            if empty >= 2:
                print(f"  Feed-Ende bei Offset {off}.")
                break
            continue
        empty = 0
        if any(it["nr"] >= WP21_MAX for it in items):  # WP20-Schwanz erreicht → Schluss
            print(f"  WP20-Grenze bei Offset {off} (Sitzung ≥ {WP21_MAX}) — Crawl beendet.")
            break
        for it in items:
            if 1 <= it["nr"] <= 84:
                buckets.setdefault(it["nr"], []).append(it)
        if off % 20 == 0:
            print(f"  … Offset {off}, {len(buckets)} Sitzungen, {sum(len(v) for v in buckets.values())} Clips")
    for nr in buckets:  # je Sitzung chronologisch
        buckets[nr].sort(key=lambda c: (c["datum"], c["uhr"], c["fvid"]))
    CACHE.write_text(json.dumps({str(k): v for k, v in buckets.items()}, ensure_ascii=False), encoding="utf-8")
    print(f"  Crawl fertig: {len(buckets)} Sitzungen, {sum(len(v) for v in buckets.values())} Clips → Cache.")
    return buckets


def patch_pages_graph(nr: int, links: dict[str, str], matched: int) -> bool:
    """video_url je Redebeitrag in den committeten Struktur-Graphen schreiben (falls vorhanden)."""
    f = WEB / f"amt_{WP}_{nr:03d}.json"
    if not f.exists():
        return False
    g = json.loads(f.read_text(encoding="utf-8"))
    n = 0
    for node in g["nodes"]:
        if node.get("type") == "Redebeitrag" and node["id"] in links:
            node["video_url"] = links[node["id"]]
            n += 1
    g.setdefault("metadata", {})["mediathek_verlinkt"] = matched
    f.write_text(json.dumps(g, ensure_ascii=False, indent=2), encoding="utf-8")
    return n > 0


def neo4j_update(nr: int, links: dict[str, str], cfg: dict) -> int:
    """Redebeitrag.video_url in Neo4j setzen (namespaced id amt_WP_NNN::redebeitrag_X)."""
    from neo4j import GraphDatabase  # lazy: nur im --load-Pfad
    prefix = f"amt_{WP}_{nr:03d}"
    drv = GraphDatabase.driver(cfg["uri"], auth=(cfg["user"], cfg["password"]))
    done = 0
    with drv.session() as s:
        for rid, url in links.items():
            r = s.run("MATCH (n:Redebeitrag {id: $id}) SET n.video_url = $url RETURN count(n) AS c",
                      id=f"{prefix}::{rid}", url=url).single()
            done += (r["c"] if r else 0)
    drv.close()
    return done


def main() -> None:
    ap = argparse.ArgumentParser(description="Mediathek-Deeplinks für alle WP21-Sitzungen")
    ap.add_argument("--from", dest="lo", type=int, default=1)
    ap.add_argument("--to", dest="hi", type=int, default=81)
    ap.add_argument("--load", action="store_true", help="zusätzlich Neo4j Redebeitrag.video_url setzen")
    ap.add_argument("--refresh", action="store_true", help="Feed-Cache ignorieren und neu crawlen")
    args = ap.parse_args()

    print("📺 Mediathek-Deeplinks — Feed crawlen …")
    buckets = crawl_feed(use_cache=not args.refresh)

    st = json.loads(STATE.read_text(encoding="utf-8"))
    cfg = {"uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
           "user": os.getenv("NEO4J_USER", "neo4j"),
           "password": os.getenv("NEO4J_PASSWORD", "neo4j")}
    tot_sess = tot_rede = tot_neo = 0

    for nr in range(args.lo, args.hi + 1):
        clips = buckets.get(nr) or []
        if not clips:
            continue
        key = f"{WP}-{nr:03d}"
        session_url = clips[0]["url"]
        matched, links = 0, {}
        xml = AMT_DIR / f"{WP}{nr:03d}.xml"
        if xml.exists():
            try:
                p = session_ingest.official_protocol(xml)
                matched = session_ingest._attach_video_links(p, list(clips))
                links = {f"redebeitrag_{r['quelle_utterances'][0]}": r["video_url"]
                         for r in p.redebeitraege
                         if r.get("video_url") and r.get("quelle_utterances")}
            except Exception as e:  # noqa: BLE001
                print(f"  ✗ {key}: Match fehlgeschlagen ({type(e).__name__}: {e})")
        patched = patch_pages_graph(nr, links, matched)
        neo = neo4j_update(nr, links, cfg) if (args.load and links) else 0

        ent = st["official"].setdefault(key, {})
        ent["mediathek_url"] = session_url
        ent["mediathek_clips"] = len(clips)
        ent["mediathek_verlinkt"] = matched
        tot_sess += 1
        tot_rede += matched
        tot_neo += neo
        flag = ("📄graph" if patched else "") + (f" 🟢neo4j:{neo}" if neo else "")
        print(f"  ✓ {key}: {len(clips)} Clips, {matched} Reden verlinkt {flag}")

    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
    sync.write_index(st, wp=WP)  # web/data/sessions.json neu schreiben (Mediathek je Sitzung)
    print(f"\nFertig: {tot_sess} Sitzungen mit Mediathek-Deeplink, {tot_rede} Reden verlinkt"
          + (f", {tot_neo} Neo4j-Knoten aktualisiert" if args.load else "") + ".")


if __name__ == "__main__":
    main()
