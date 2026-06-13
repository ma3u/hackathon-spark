"""
WER-Benchmark über mehrere Sitzungen — gesprochenes Wort ↔ amtliches Protokoll.

Echtes ASR-Transkript (YouTube-Auto-Caption) gibt es nur für 2 Sitzungen (Gesamt-Streams).
Für ALLE Showcase-Sitzungen liegt aber das **gesprochene Wort** als korrigierter Mediathek-
Untertitel vor (`.srt` je Rede). Dieses Skript misst je Sitzung die **Wortabweichung
(WER) zwischen Mediathek-Untertitel und amtlichem Protokoll** — also den **Korrektur-Gap**
(Redaktion/Korrekturrecht der Redner:innen), NICHT rohen ASR-Fehler.

Effizient + aussagekräftig: pro **Rede** ausgerichtet (Sprecher-Match wie bei den Video-
Deeplinks) statt Gesamt-Bag → kleine Levenshtein-DPs, kein 40k×40k-Speicher. Aggregiert:
Σ Editieroperationen / Σ Referenzwörter.

  python scripts/wer_benchmark.py --from 70 --to 81     # Mediathek-WER je Sitzung + Aggregat
  python scripts/wer_benchmark.py --refresh             # SRT-Cache neu laden

Produktivpfad = Demopfad: stdlib + urllib (Untertitel liegen vor, kein eigenes ASR/GPU).
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from pipeline import gap_analysis, mediathek, session_ingest  # noqa: E402
from pipeline.session_ingest import _norm_name  # gleiche Sprecher-Normalisierung wie Video-Match

WEB = REPO / "web" / "data"
AMT = REPO / "data" / "real" / "amt"
FEED_CACHE = Path("/tmp/mediathek_feed_cache.json")
SRT_CACHE = Path("/tmp/mediathek_srt_cache.json")
WP = "21"


def _load_feed() -> dict[int, list[dict]]:
    if FEED_CACHE.exists():
        return {int(k): v for k, v in json.loads(FEED_CACHE.read_text()).items()}
    raise SystemExit("Feed-Cache fehlt — erst scripts/mediathek_links.py laufen lassen.")


def _srt_texts(clips: list[dict], cache: dict) -> list[dict]:
    """Untertiteltext je Clip (gecacht über die fvid)."""
    todo = [c for c in clips if c["fvid"] not in cache]
    if todo:
        for c in mediathek.fetch_srts(todo):
            cache[c["fvid"]] = c.get("text", "")
        for c in todo:  # auch Leertreffer markieren
            cache.setdefault(c["fvid"], "")
    return [{**c, "text": cache.get(c["fvid"], "")} for c in clips]


def _wer(ref: list[str], hyp: list[str]) -> dict:
    """WER per difflib-Wort-Opcodes (C-beschleunigt, speicherschonend statt 40k×40k-DP)."""
    sm = difflib.SequenceMatcher(None, ref, hyp, autojunk=False)
    sub = ins = dele = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "replace":
            sub += max(i2 - i1, j2 - j1)
        elif tag == "delete":
            dele += i2 - i1
        elif tag == "insert":
            ins += j2 - j1
    n = len(ref)
    return {"wer": round((sub + ins + dele) / max(1, n), 3),
            "subst": sub, "ins": ins, "del": dele, "ref_woerter": n}


def _diff_segments(ref_text: str, hyp_text: str, *, ctx: int = 4, max_seg: int = 90) -> list:
    """Wort-Diff Protokoll(ref) ↔ gesprochen(hyp) auf ORIGINALtext (Vergleich normalisiert).

    Segmente: ["=",text] gleich · ["p",text] nur im Protokoll (redaktionell ergänzt) ·
    ["g",text] nur gesprochen (redaktionell entfernt, z. B. Füllwörter) · ["r",prot,gespr] ersetzt.
    Lange Gleich-Läufe werden auf etwas Kontext um die Änderungen gekürzt.
    """
    rt, ht = re.findall(r"\S+", ref_text), re.findall(r"\S+", hyp_text)
    key = lambda w: re.sub(r"[^0-9a-zäöüß]", "", w.lower())
    rk, hk = [key(w) for w in rt], [key(w) for w in ht]
    sm = difflib.SequenceMatcher(None, rk, hk, autojunk=False)
    ops = sm.get_opcodes()
    segs = []
    for n, (tag, i1, i2, j1, j2) in enumerate(ops):
        if tag == "equal":
            words = rt[i1:i2]
            if len(words) > 2 * ctx + 1:  # langen Gleich-Lauf kürzen (Kontext vorn/hinten)
                head = words[:ctx] if n > 0 else []
                tail = words[-ctx:] if n < len(ops) - 1 else []
                words = head + (["…"] if (head or tail) else []) + tail
            if words:
                segs.append(["=", " ".join(words)])
        elif tag == "delete":
            segs.append(["p", " ".join(rt[i1:i2])])
        elif tag == "insert":
            segs.append(["g", " ".join(ht[j1:j2])])
        else:
            segs.append(["r", " ".join(rt[i1:i2]), " ".join(ht[j1:j2])])
    return segs[:max_seg]


def benchmark(nr: int, clips: list[dict], srt_cache: dict) -> dict | None:
    xml = AMT / f"{WP}{nr:03d}.xml"
    if not xml.exists():
        return None
    p = session_ingest.official_protocol(xml)
    clips = [c for c in _srt_texts(clips, srt_cache) if c["text"]]
    if not clips:
        return None
    # Sprecher → seine Untertitel-Clips (Wortlisten). Zuordnung Rede↔Clip per BESTER
    # Übereinstimmung (nicht Reihenfolge: ein Sprecher hat oft mehrere Reden/Clips), mit
    # Übergrößen-Schutz (gelegentlich ist ein Clip ein ganzer TOP-Block, kein Einzelbeitrag).
    by_spk: dict[str, list[dict]] = defaultdict(list)
    for c in clips:
        by_spk[_norm_name(c["speaker"])].append(
            {"words": gap_analysis._norm(c["text"]), "text_orig": c["text"], "used": False})
    tot_ref = tot_edit = matched = 0
    divergenzen = []
    for r in p.redebeitraege:
        ref_text = " ".join(p.utterances[i].text for i in (r.get("quelle_utterances") or [])
                            if i < len(p.utterances) and p.utterances[i].text)
        ref = gap_analysis._norm(ref_text)
        if len(ref) < 20:  # zu kurz → statistisch verrauscht
            continue
        key = _norm_name(r["person"])
        pool = by_spk.get(key)
        if not pool:  # Nachnamen-Fallback (wie _attach_video_links)
            sur = key.split()[-1] if key.split() else ""
            for k2, lst in by_spk.items():
                if k2.split() and k2.split()[-1] == sur:
                    pool = lst
                    break
        if not pool:
            continue
        cap = 3 * len(ref) + 50  # Clips, die viel länger als die Rede sind → Block, überspringen
        cands = [c for c in pool if not c["used"] and 0 < len(c["words"]) <= cap]
        if not cands:
            continue
        best = max(cands, key=lambda c: difflib.SequenceMatcher(None, ref, c["words"], autojunk=False).quick_ratio())
        best["used"] = True
        w = _wer(ref, best["words"])
        edits = w["subst"] + w["ins"] + w["del"]
        tot_ref += w["ref_woerter"]
        tot_edit += edits
        matched += 1
        divergenzen.append({"sprecher": r["person"], "rede_wer": round(edits / max(1, w["ref_woerter"]), 3),
                            "ref_woerter": w["ref_woerter"], "top": r.get("top_nummer"),
                            "_ref": ref_text, "_hyp": best["text_orig"]})
    if not tot_ref:
        return None
    wer_val = round(tot_edit / tot_ref, 3)
    divergenzen.sort(key=lambda d: -d["rede_wer"])
    # Diff nur für die auffälligsten Reden mit echtem Änderungsanteil (Anzeige in der UI).
    diffs = []
    for d in divergenzen:
        if len(diffs) >= 6 or d["rede_wer"] < 0.02:
            break
        diffs.append({"sprecher": d["sprecher"], "top": d["top"], "rede_wer": d["rede_wer"],
                      "ref_woerter": d["ref_woerter"], "segmente": _diff_segments(d["_ref"], d["_hyp"])})
    for d in divergenzen:  # Rohtexte nicht in den Report schreiben
        d.pop("_ref", None)
        d.pop("_hyp", None)
    return {
        "sitzung": {"wp": WP, "nr": nr, "datum": p.meeting.get("datum", "")},
        "vergleich": "Mediathek-Untertitel (gesprochenes Wort) ↔ amtliches Protokoll",
        "wer": {"wer": wer_val, "ref_woerter": tot_ref, "editieroperationen": tot_edit},
        "reden": {"verglichen": matched, "gesamt": len(p.redebeitraege)},
        "reaktionen": {"amtlich": len(p.kommentare), "im_untertitel": 0,
                       "hinweis": "Untertitel erfassen Saalreaktionen nicht — separat via XML/SED."},
        "groesste_divergenzen": divergenzen[:8],
        "diffs": diffs,
        "bewertung": [
            f"Korrektur-Gap (WER) {wer_val:.1%} — Abweichung Protokoll ↔ gesprochenes Wort "
            + ("gering" if wer_val < 0.15 else "mittel" if wer_val < 0.3 else "hoch"),
            f"{matched}/{len(p.redebeitraege)} Reden ausgerichtet verglichen.",
            "Kein Faktenfehler: Differenz = redaktionelle Korrektur (Korrekturrecht), als Diff modelliert.",
        ],
        "quellen": {"amtlich": session_ingest.DSERVER_PDF.format(wp=WP, nnn=f"{nr:03d}"),
                    "mediathek": clips[0]["url"]},
        "quelle_typ": "mediathek",
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="WER-Benchmark (Mediathek ↔ amtlich) über Sitzungen")
    ap.add_argument("--from", dest="lo", type=int, default=70)
    ap.add_argument("--to", dest="hi", type=int, default=81)
    ap.add_argument("--refresh", action="store_true", help="SRT-Cache verwerfen")
    args = ap.parse_args()

    feed = _load_feed()
    srt_cache = {} if args.refresh else (json.loads(SRT_CACHE.read_text()) if SRT_CACHE.exists() else {})
    state_path = REPO / "data" / "real" / "sessions_state.json"
    st = json.loads(state_path.read_text())

    results, summary = [], []
    for nr in range(args.lo, args.hi + 1):
        key = f"{WP}-{nr:03d}"
        if key in st.get("youtube", {}):  # echte ASR-Gap (YouTube) behalten, nicht überschreiben
            print(f"  • {nr}: hat YouTube-ASR-Gap — Mediathek-WER übersprungen.")
            continue
        clips = feed.get(nr) or []
        if not clips:
            print(f"  • {nr}: keine Mediathek-Clips — übersprungen.")
            continue
        rep = benchmark(nr, clips, srt_cache)
        SRT_CACHE.write_text(json.dumps(srt_cache, ensure_ascii=False))
        if not rep:
            print(f"  • {nr}: kein Vergleich möglich — übersprungen.")
            continue
        (WEB / f"gap_{WP}_{nr:03d}.json").write_text(
            json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
        st.setdefault("gap", {})[key] = {"wer": rep["wer"]["wer"],
                                         "ref_woerter": rep["wer"]["ref_woerter"],
                                         "reaktionen": rep["reaktionen"]["amtlich"],
                                         "typ": "mediathek", "ts": st.get("gap", {}).get(key, {}).get("ts", "")}
        results.append(rep)
        summary.append({"nr": nr, "wer": rep["wer"]["wer"], "reden": rep["reden"]["verglichen"],
                        "ref_woerter": rep["wer"]["ref_woerter"]})
        print(f"  ✓ {nr}: WER {rep['wer']['wer']:.1%}  "
              f"({rep['reden']['verglichen']}/{rep['reden']['gesamt']} Reden, {rep['wer']['ref_woerter']} Wörter)")

    if results:
        ws = [r["wer"]["wer"] for r in results]
        agg = {"sessions": len(results), "wer_mittel": round(sum(ws) / len(ws), 3),
               "wer_min": min(ws), "wer_max": max(ws),
               "ref_woerter_gesamt": sum(r["wer"]["ref_woerter"] for r in results),
               "vergleich": "Mediathek-Untertitel ↔ amtliches Protokoll (Korrektur-Gap)",
               "sitzungen": summary}
        (WEB / "wer_benchmark.json").write_text(json.dumps(agg, ensure_ascii=False, indent=2), encoding="utf-8")
        state_path.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            import scripts.sync_sessions as sync
            sync.write_index(st, wp=WP)
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠ Index nicht neu geschrieben: {e}")
        print(f"\nAggregat: {agg['sessions']} Sitzungen · WER Ø {agg['wer_mittel']:.1%} "
              f"(min {agg['wer_min']:.1%}, max {agg['wer_max']:.1%}) · "
              f"{agg['ref_woerter_gesamt']} Referenzwörter → web/data/wer_benchmark.json")


if __name__ == "__main__":
    main()
