#!/usr/bin/env python3
"""
Inkrementelle Sitzungs-Synchronisation — lädt NOCH NICHT importierte Bundestagssitzungen
in den Graphen. Zwei Quellen, zwei getrennte Graphen, gemerkte Herkunft:

  • YouTube  (@bundestag/streams) — Gesamtmitschnitte mit Zeit-Deeplinks → yt_<wp>_<nr>
  • Amtlich  (dserver.bundestag.de Open-Data-XML, ALLE Sitzungen) → amt_<wp>_<nr>

Status in data/real/sessions_state.json → erneuter Lauf überspringt bereits Importiertes
(--force erzwingt Neuimport). Faktencheck läuft IMMER gegen reale Inhalte (LLM/Mistral,
Disclaimer), nie gegen den fiktiven Demo-Korpus.

  python scripts/sync_sessions.py --youtube --load                 # neue YT-Streams
  python scripts/sync_sessions.py --official --from 1 --to 81 --load
  python scripts/sync_sessions.py --gap                            # YT↔amtlich Lückenanalyse
  python scripts/sync_sessions.py --all --load                     # alles inkrementell
  python scripts/sync_sessions.py --official --to 81 --no-factcheck --load   # ohne LLM
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

try:
    from dotenv import load_dotenv
    load_dotenv(REPO / ".env")
except Exception:
    pass

from pipeline import session_ingest, gap_analysis  # noqa: E402

YT_DIR = REPO / "data" / "real" / "yt"
AMT_DIR = REPO / "data" / "real" / "amt"
WEB = REPO / "web" / "data"
STATE = REPO / "data" / "real" / "sessions_state.json"
CHANNEL_STREAMS = "https://www.youtube.com/@bundestag/streams"
_SITZUNG_NR = re.compile(r"(\d+)\.\s*Sitzung")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_state() -> dict:
    st = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    for k in ("youtube", "official", "mediathek", "gap"):
        st.setdefault(k, {})
    return st


def save_state(st: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")


def neo4j_cfg() -> dict:
    return {"uri": os.environ.get("NEO4J_URI"), "user": os.environ.get("NEO4J_USER"),
            "password": os.environ.get("NEO4J_PASSWORD")}


def azure_cfg(no_factcheck: bool) -> dict | None:
    if no_factcheck or "AZURE_AI_API_KEY" not in os.environ:
        return None
    return {"model": os.environ.get("MISTRAL_DEPLOYMENT", "Mistral-Large-3"),
            "base_url": os.environ["AZURE_AI_ENDPOINT"], "api_key": os.environ["AZURE_AI_API_KEY"]}


# ── YouTube ──────────────────────────────────────────────────────────────────────

def list_streams() -> list[dict]:
    """@bundestag/streams → [{video_id, nr, title}] (nur erkennbare 'NN. Sitzung')."""
    try:
        out = subprocess.run(
            ["yt-dlp", "--flat-playlist", "--print", "%(id)s\t%(title)s", CHANNEL_STREAMS],
            capture_output=True, text=True, timeout=120, check=True).stdout
    except Exception as e:  # noqa: BLE001
        print(f"⚠ yt-dlp Streams-Liste fehlgeschlagen: {e}")
        return []
    rows = []
    for line in out.splitlines():
        if "\t" not in line:
            continue
        vid, title = line.split("\t", 1)
        mnr = _SITZUNG_NR.search(title)
        if mnr:
            rows.append({"video_id": vid.strip(), "nr": int(mnr.group(1)), "title": title.strip()})
    return rows


def video_date(video_id: str) -> str:
    """Sitzungsdatum aus den Video-Metadaten (upload_date YYYYMMDD → DD.MM.YYYY)."""
    try:
        out = subprocess.run(
            ["yt-dlp", "--skip-download", "--print", "%(upload_date)s",
             f"https://www.youtube.com/watch?v={video_id}"],
            capture_output=True, text=True, timeout=120, check=True).stdout.strip()
        if len(out) == 8 and out.isdigit():
            return f"{out[6:8]}.{out[4:6]}.{out[0:4]}"
    except Exception:
        pass
    return ""


def ensure_vtt(wp: str, nr: int, video_id: str) -> Path | None:
    out = YT_DIR / f"{wp}-{nr:03d}"
    vtt = out.with_suffix(".de.vtt")
    if vtt.exists():
        return vtt
    YT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  ↓ Untertitel {wp}-{nr:03d} ({video_id}) …")
    try:
        subprocess.run(
            ["yt-dlp", "--write-auto-subs", "--sub-langs", "de", "--convert-subs", "vtt",
             "--skip-download", "-o", f"{out}.%(ext)s",
             f"https://www.youtube.com/watch?v={video_id}"],
            capture_output=True, text=True, timeout=600, check=True)
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠ Download fehlgeschlagen: {e}")
        return None
    return vtt if vtt.exists() else None


def sync_youtube(st, *, wp, load, az, force, limit) -> None:
    print("── YouTube-Gesamtmitschnitte (@bundestag/streams) ──")
    streams = list_streams()
    if not streams:
        print("  Keine erkennbaren Sitzungs-Streams gefunden.")
        return
    done = 0
    for s in streams:
        nr, vid = s["nr"], s["video_id"]
        key = f"{wp}-{nr:03d}"
        if key in st["youtube"] and not force:
            print(f"  • {key} bereits importiert — übersprungen.")
            continue
        if limit and done >= limit:
            break
        vtt = ensure_vtt(wp, nr, vid)
        if not vtt:
            continue
        datum = video_date(vid)
        titel = f"{nr}. Sitzung (Gesamtmitschnitt)"
        if az:
            print(f"  🔎 LLM-Faktencheck {key} via {az['model']} …")
        try:
            res = session_ingest.ingest_youtube(
                vtt, wp=wp, nr=nr, video_id=vid, titel=titel, datum=datum,
                az=az, load=load, neo4j=neo4j_cfg())
        except Exception as e:  # eine kaputte Sitzung darf den Batch nicht abbrechen
            print(f"  ✗ {key}: Ingest fehlgeschlagen ({type(e).__name__}: {e}) — übersprungen.")
            continue
        st["youtube"][key] = {"video_id": vid, "datum": datum, "titel": titel,
                              "nodes": res["nodes"], "rels": res["rels"],
                              "segmente": res["segmente"], "checks": res["checks"], "ts": _now()}
        save_state(st)
        print(f"  ✓ {key}: {res['nodes']} Knoten, {res['segmente']} Segmente, "
              f"{res['checks']} Faktenchecks → {res['name']}")
        done += 1


# ── Amtlich (Open Data, ALLE Sitzungen) ───────────────────────────────────────────

def fetch_official_xml(wp: str, nr: int) -> Path | None:
    AMT_DIR.mkdir(parents=True, exist_ok=True)
    dest = AMT_DIR / f"{wp}{nr:03d}.xml"
    if dest.exists() and dest.stat().st_size > 1000:
        return dest
    url = session_ingest.DSERVER_XML.format(wp=wp, nnn=f"{nr:03d}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "graph-protokoll/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        if len(data) < 1000 or b"<dbtplenarprotokoll" not in data[:4000]:
            return None
        dest.write_bytes(data)
        return dest
    except Exception:
        return None


def sync_official(st, *, wp, lo, hi, load, az, force, limit, web_graph=False, retrieval=False) -> None:
    print(f"── Amtliche Plenarprotokolle (dserver, WP {wp}, {lo}–{hi}) ──")
    done = 0
    for nr in range(lo, hi + 1):
        key = f"{wp}-{nr:03d}"
        if key in st["official"] and not force:
            continue
        if limit and done >= limit:
            break
        xml = fetch_official_xml(wp, nr)
        if not xml:
            print(f"  • {key}: kein XML (noch nicht veröffentlicht?) — übersprungen.")
            continue
        if az:
            print(f"  🔎 LLM-Faktencheck {key} (max 12 Aussagen) …")
        try:
            res = session_ingest.ingest_official(
                xml, wp=wp, nr=nr, az=az, load=load, write_web_graph=web_graph,
                mediathek_match=web_graph, retrieval=retrieval, neo4j=neo4j_cfg())
        except Exception as e:  # eine kaputte Sitzung darf den Batch nicht abbrechen
            print(f"  ✗ {key}: Ingest fehlgeschlagen ({type(e).__name__}: {e}) — übersprungen.")
            continue
        st["official"][key] = {"datum": res["datum"], "nodes": res["nodes"], "rels": res["rels"],
                               "reden": res["reden"], "aussagen": res["aussagen"],
                               "saalreaktionen": res["saalreaktionen"], "checks": res["checks"],
                               "has_graph": res.get("has_graph", False),
                               "mediathek_verlinkt": res.get("mediathek_verlinkt", 0), "ts": _now()}
        save_state(st)
        print(f"  ✓ {key} ({res['datum']}): {res['nodes']} Knoten, {res['reden']} Reden, "
              f"{res['saalreaktionen']} Saalreaktionen, {res['mediathek_verlinkt']} Video-Deeplinks → {res['name']}")
        done += 1


# ── Mediathek (Bundestag-Clips: korrigierte Untertitel, sprecher-attribuiert) ──────

def sync_mediathek(st, *, wp, lo, hi, load, az, force, limit) -> None:
    print(f"── Bundestag-Mediathek (korrigierte Untertitel, WP {wp}, {lo}–{hi}) ──")
    done = 0
    # neueste zuerst (Feed ist newest-first → wenig Paging für aktuelle Sitzungen)
    for nr in range(hi, lo - 1, -1):
        key = f"{wp}-{nr:03d}"
        if key in st["mediathek"] and not force:
            continue
        if limit and done >= limit:
            break
        if az:
            print(f"  🔎 {key}: Clips holen + LLM-Faktencheck …")
        try:
            res = session_ingest.ingest_mediathek(wp=wp, nr=nr, az=az, load=load, neo4j=neo4j_cfg())
        except Exception as e:
            print(f"  ✗ {key}: fehlgeschlagen ({type(e).__name__}: {e}) — übersprungen.")
            continue
        if not res:
            print(f"  • {key}: keine Mediathek-Clips/Untertitel (zu alt im Feed?) — übersprungen.")
            continue
        st["mediathek"][key] = {"datum": res["datum"], "nodes": res["nodes"], "rels": res["rels"],
                                "reden": res["reden"], "tops": res["tops"], "checks": res["checks"],
                                "quelle_url": res["quelle_url"], "ts": _now()}
        save_state(st)
        print(f"  ✓ {key} ({res['datum']}): {res['reden']} Reden, {res['nodes']} Knoten, "
              f"{res['checks']} Faktenchecks → {res['name']}")
        done += 1


# ── Gap-Analyse YouTube ↔ amtlich ─────────────────────────────────────────────────

def sync_gap(st, *, wp, force) -> None:
    print("── Gap-Analyse (YouTube-Transkript ↔ amtliches Protokoll) ──")
    common = sorted(set(st["youtube"]) & set(st["official"]))
    if not common:
        print("  Keine Sitzung mit BEIDEN Quellen — erst --youtube und --official laufen lassen.")
        return
    for key in common:
        if key in st["gap"] and not force:
            continue
        wp_, nr = key.split("-")
        nr = int(nr)
        xml = AMT_DIR / f"{wp_}{nr:03d}.xml"
        vtt = YT_DIR / f"{wp_}-{nr:03d}.de.vtt"
        if not (xml.exists() and vtt.exists()):
            continue
        p_amt = session_ingest.official_protocol(xml)
        p_yt = session_ingest.youtube_protocol(vtt, wp=wp_, nr=nr, video_id="", titel="", datum="")
        asr_text = " ".join(u.text for u in p_yt.utterances if u.text)
        report = gap_analysis.analyze_gaps(p_amt, asr_text, asr_speakers=None, sed_erkannt=0)
        report["sitzung"] = {"wp": wp_, "nr": nr, "datum": p_amt.meeting.get("datum", "")}
        report["quellen"] = {
            "amtlich": session_ingest.DSERVER_PDF.format(wp=wp_, nnn=f"{nr:03d}"),
            "youtube": f"https://www.youtube.com/watch?v={st['youtube'][key]['video_id']}"}
        WEB.mkdir(parents=True, exist_ok=True)
        (WEB / f"gap_{wp_}_{nr:03d}.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        st["gap"][key] = {"wer": report["wer"]["wer"], "ref_woerter": report["wer"]["ref_woerter"],
                          "reaktionen": report["reaktionen"]["amtlich"], "ts": _now()}
        save_state(st)
        print(f"  ✓ {key}: WER {report['wer']['wer']:.1%}, "
              f"{report['reaktionen']['amtlich']} Saalreaktionen amtlich → gap_{wp_}_{nr:03d}.json")


# ── Index für die UI ──────────────────────────────────────────────────────────────

def write_index(st, *, wp) -> None:
    keys = sorted(set(st["youtube"]) | set(st["official"]),
                  key=lambda k: int(k.split("-")[1]), reverse=True)
    sessions = []
    for key in keys:
        wp_, nr_s = key.split("-")
        nr = int(nr_s)
        yt = st["youtube"].get(key)
        amt = st["official"].get(key)
        gap = st["gap"].get(key)
        entry = {"wp": wp_, "nr": nr, "datum": (yt or amt or {}).get("datum", "")}
        if yt:
            entry["youtube"] = {"name": f"yt_{wp_}_{nr:03d}", "video_id": yt["video_id"],
                                "url": f"https://www.youtube.com/watch?v={yt['video_id']}",
                                "protokoll": f"yt_{wp_}_{nr:03d}_protokoll.html",
                                "nodes": yt["nodes"], "checks": yt["checks"]}
        if amt:
            a = {"name": f"amt_{wp_}_{nr:03d}",
                 "pdf": session_ingest.DSERVER_PDF.format(wp=wp_, nnn=f"{nr:03d}"),
                 "xml": session_ingest.DSERVER_XML.format(wp=wp_, nnn=f"{nr:03d}"),
                 "dashboard": f"amt_{wp_}_{nr:03d}_dashboard.json", "nodes": amt["nodes"]}
            if amt.get("has_graph"):  # strukturgraph + Protokoll-HTML auf Pages vorhanden
                a["graph"] = f"amt_{wp_}_{nr:03d}.json"
                a["protokoll"] = f"amt_{wp_}_{nr:03d}_protokoll.html"
            # Mediathek-Deeplink je Sitzung (für ALLE, auch ohne committeten Graphen):
            # Sitzungs-Einstieg (erster Clip) + Trefferzahl der reden-genauen Verlinkung.
            if amt.get("mediathek_url"):
                a["mediathek"] = amt["mediathek_url"]
                a["mediathek_clips"] = amt.get("mediathek_clips", 0)
            if amt.get("has_graph") or amt.get("mediathek_url"):
                a["mediathek_verlinkt"] = amt.get("mediathek_verlinkt", 0)
            entry["amtlich"] = a
        if gap:
            entry["gap"] = {"file": f"gap_{wp_}_{nr:03d}.json", "wer": gap["wer"],
                            "typ": gap.get("typ", "youtube")}  # youtube=ASR-Gap, mediathek=Korrektur-Gap
        sessions.append(entry)
    WEB.mkdir(parents=True, exist_ok=True)
    (WEB / "sessions.json").write_text(json.dumps(
        {"generated": _now(), "wahlperiode": wp, "count": len(sessions), "sessions": sessions},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"→ web/data/sessions.json ({len(sessions)} Sitzungen)")


def main() -> int:
    ap = argparse.ArgumentParser(description="Inkrementelle Bundestags-Sitzungs-Ingestion")
    ap.add_argument("--youtube", action="store_true", help="neue YouTube-Streams importieren")
    ap.add_argument("--mediathek", action="store_true",
                    help="Bundestag-Mediathek (korrigierte Untertitel, sprecher-attribuiert)")
    ap.add_argument("--official", action="store_true", help="amtliche XML importieren")
    ap.add_argument("--gap", action="store_true", help="Gap-Analyse YT↔amtlich")
    ap.add_argument("--all", action="store_true", help="youtube + mediathek + official + gap")
    ap.add_argument("--wp", default="21", help="Wahlperiode (Default 21)")
    ap.add_argument("--from", dest="lo", type=int, default=1, help="erste Sitzungsnr (official)")
    ap.add_argument("--to", dest="hi", type=int, default=81, help="letzte Sitzungsnr (official)")
    ap.add_argument("--limit", type=int, default=0, help="max. neue Sitzungen pro Lauf (0=alle)")
    ap.add_argument("--load", action="store_true", help="echt nach Neo4j laden (sonst dry-run)")
    ap.add_argument("--no-factcheck", action="store_true", help="ohne LLM-Faktencheck")
    ap.add_argument("--web-graph", action="store_true",
                    help="amtlich: strukturellen Graph + Protokoll-HTML + Mediathek-Deeplinks für Pages schreiben")
    ap.add_argument("--retrieval", action="store_true",
                    help="Faktencheck mit Quellen-Retrieval (Wikipedia) statt LLM-only → belastbare Verdikte")
    ap.add_argument("--force", action="store_true", help="bereits importierte neu importieren")
    args = ap.parse_args()

    if not (args.youtube or args.mediathek or args.official or args.gap or args.all):
        ap.error("Mindestens eine Aktion: --youtube / --mediathek / --official / --gap / --all")

    st = load_state()
    az = azure_cfg(args.no_factcheck)
    if az is None and not args.no_factcheck:
        print("ℹ️  AZURE_AI_API_KEY fehlt — Faktencheck wird übersprungen (--no-factcheck implizit).")

    if args.youtube or args.all:
        sync_youtube(st, wp=args.wp, load=args.load, az=az, force=args.force, limit=args.limit)
    if args.mediathek or args.all:
        sync_mediathek(st, wp=args.wp, lo=args.lo, hi=args.hi, load=args.load, az=az,
                       force=args.force, limit=args.limit)
    if args.official or args.all:
        sync_official(st, wp=args.wp, lo=args.lo, hi=args.hi, load=args.load, az=az,
                      force=args.force, limit=args.limit, web_graph=args.web_graph,
                      retrieval=args.retrieval)
    if args.gap or args.all:
        sync_gap(st, wp=args.wp, force=args.force)

    write_index(st, wp=args.wp)
    print("Fertig.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
