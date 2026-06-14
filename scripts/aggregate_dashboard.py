#!/usr/bin/env python3
"""
Aggregat-Dashboard über ALLE Sitzungen → web/data/aggregate_dashboard.json.

Verdichtet die committeten Sitzungsdaten (dep-frei, ohne Neo4j/LLM/Netz):
  • alle web/data/amt_*_dashboard.json  → Themen, Redner:innen, Faktencheck-Bilanz (Trend)
  • die 13 Voll-Graphen web/data/amt_*.json (70–81 + 20/214) → Faktencheck JE PERSON
  • web/data/youtube_completeness.json   → YouTube-Clip-Abdeckung (56/81)

Faktencheck über reale Personen = **KI-Vorschlag (ungeprüft), kein Urteil** (ADR-0007). Sprecher
werden NICHT als „Lügner" etikettiert, sondern Aussagen als faktenbasiert (bestätigt/teilweise)
vs. fragwürdig (irreführend/falsch) gezählt — mit Disclaimer.

  python scripts/aggregate_dashboard.py
"""

from __future__ import annotations

import datetime
import glob
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WEB = REPO / "web" / "data"

FACT = {"bestätigt", "teilweise"}            # faktenbasiert
QUESTIONABLE = {"irreführend", "falsch"}      # fragwürdig
VERDIKTE = ["bestätigt", "teilweise", "irreführend", "falsch", "unbelegt"]
DISCLAIMER = ("Faktencheck automatisch durch KI (Mistral) erzeugt — ungeprüfte Vorschläge, "
              "kein Urteil über reale Personen. Vor Veröffentlichung von Menschen prüfen.")
_DASH = re.compile(r"amt_(\d+)_(\d+)_dashboard\.json$")
_FULL = re.compile(r"amt_(\d+)_(\d+)\.json$")


def _load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def per_session_dashboards() -> list[dict]:
    out = []
    for f in sorted(glob.glob(str(WEB / "amt_*_dashboard.json"))):
        m = _DASH.search(f)
        if m:
            d = _load(f)
            d["_wp"], d["_nr"] = int(m.group(1)), int(m.group(2))
            out.append(d)
    return out


def speaker_factcheck() -> tuple[dict, dict, list]:
    """Aus den Voll-Graphen: Verdikt-Bilanz je Person und je Fraktion (+ Sitzungs-Trend)."""
    per_person: dict[str, Counter] = defaultdict(Counter)
    person_fraktion: dict[str, str] = {}
    per_fraktion: dict[str, Counter] = defaultdict(Counter)
    trend = []
    for f in sorted(glob.glob(str(WEB / "amt_*.json"))):
        if _DASH.search(f) or "_barrierefrei" in f or "_protokoll" in f or not _FULL.search(f):
            continue
        m = _FULL.search(f)
        g = _load(f)
        nodes = {n["id"]: n for n in g["nodes"]}
        frakt = {n["id"]: n["label"] for n in g["nodes"] if n["type"] == "Fraktion"}
        # Person → Fraktion (MITGLIED_VON)
        p2f = {}
        for r in g["relationships"]:
            if r["relationship_type"] == "MITGLIED_VON" and r["target_id"] in frakt:
                src = nodes.get(r["source_id"])
                if src:
                    p2f[src["label"]] = frakt[r["target_id"]]
        # Aussage → Faktencheck (GEPRUEFT_ALS)
        a2v = {}
        for r in g["relationships"]:
            if r["relationship_type"] == "GEPRUEFT_ALS":
                fc = nodes.get(r["target_id"])
                if fc and fc.get("verdikt"):
                    a2v[r["source_id"]] = fc["verdikt"]
        sess = Counter()
        for n in g["nodes"]:
            if n["type"] != "Aussage":
                continue
            v = a2v.get(n["id"])
            if not v:
                continue
            person = (n.get("person") or "").strip() or "Unbekannt"
            per_person[person][v] += 1
            sess[v] += 1
            fr = p2f.get(person)
            if fr:
                person_fraktion[person] = fr
                per_fraktion[fr][v] += 1
        trend.append({"wp": int(m.group(1)), "nr": int(m.group(2)),
                      "datum": g["metadata"].get("title", ""), "verdikte": dict(sess)})
    # serialisieren
    speakers = []
    for name, c in per_person.items():
        total = sum(c.values())
        speakers.append({
            "name": name, "fraktion": person_fraktion.get(name, ""),
            "geprüft": total, "faktenbasiert": c["bestätigt"] + c["teilweise"],
            "fragwürdig": c["irreführend"] + c["falsch"], "unbelegt": c["unbelegt"],
            **{v: c[v] for v in VERDIKTE},
        })
    speakers.sort(key=lambda s: (-s["geprüft"], -s["fragwürdig"]))
    fraktionen = {fr: {v: c[v] for v in VERDIKTE} for fr, c in per_fraktion.items()}
    return {"speakers": speakers}, {"fraktionen": fraktionen}, sorted(trend, key=lambda t: (t["wp"], t["nr"]))


def youtube_factcheck() -> dict:
    """Verdikt-Bilanz der YouTube-Graphen (yt_*.json) — Inhalt geprüft, Sprecher unbekannt
    (Auto-Untertitel ohne Sprecher-Label → keine Personen-Zuordnung)."""
    total = Counter()
    sessions = []
    for f in sorted(glob.glob(str(WEB / "yt_*.json"))):
        if "_dashboard" in f or "_barrierefrei" in f or "_protokoll" in f:
            continue
        g = _load(f)
        c = Counter(n.get("verdikt") for n in g["nodes"]
                    if n["type"] == "Faktencheck" and n.get("verdikt"))
        if not c:
            continue
        m = re.search(r"yt_(\d+)_(\d+)\.json$", f)
        sessions.append({"wp": int(m.group(1)) if m else 0, "nr": int(m.group(2)) if m else 0,
                         "clips": g["metadata"].get("clips"),
                         "verdikte": {v: c[v] for v in VERDIKTE if c[v]}})
        for v in VERDIKTE:
            total[v] += c[v]
    return {"verdikt_gesamt": {v: total[v] for v in VERDIKTE},
            "je_sitzung": sorted(sessions, key=lambda s: (s["wp"], s["nr"]))}


POS_REAK = {"Beifall", "Heiterkeit"}
NEG_REAK = {"Zwischenruf", "Widerspruch", "Unruhe"}


def content_insights():
    """Inhaltsdynamik aus den Voll-Graphen (amtlich): Beifall/Gegenruf je Redner:in und die
    schärfsten Zwischenruf-Hotspots (urheber → Redner:in). Hinweis: `urheber` der Saalreaktion
    ist meist FRAKTIONS-, nicht personenscharf — daher Fraktion→Redner:in, kein Personenduell."""
    applause, heckle, fight, spk_frak = Counter(), Counter(), Counter(), {}
    for f in sorted(glob.glob(str(WEB / "amt_*.json"))):
        if _DASH.search(f) or "_barrierefrei" in f or "_protokoll" in f or not _FULL.search(f):
            continue
        g = _load(f)
        idn = {n["id"]: n for n in g["nodes"]}
        frak = {n["id"]: n["label"] for n in g["nodes"] if n["type"] == "Fraktion"}
        for r in g["relationships"]:
            if r["relationship_type"] == "MITGLIED_VON" and r["target_id"] in frak:
                s = idn.get(r["source_id"])
                if s:
                    spk_frak[s["label"]] = frak[r["target_id"]]
        rb2s = {r["target_id"]: idn[r["source_id"]]["label"]
                for r in g["relationships"]
                if r["relationship_type"] == "HAT_REDEBEITRAG" and r["source_id"] in idn}
        for r in g["relationships"]:
            if r["relationship_type"] != "REAKTION_AUF":
                continue
            a = idn.get(r["source_id"])
            sp = rb2s.get(r["target_id"])
            if not a or not sp:
                continue
            st, urh = a.get("subtype"), (a.get("urheber") or "").strip()
            if st in POS_REAK:
                applause[sp] += 1
            elif st in NEG_REAK:
                heckle[sp] += 1
                if urh:
                    fight[(urh, sp)] += 1
    return applause, heckle, fight, spk_frak


def main() -> int:
    dashes = per_session_dashboards()
    yt = _load(WEB / "youtube_completeness.json") if (WEB / "youtube_completeness.json").exists() else {}

    # Themen (nach Redevolumen über alle Sitzungen)
    themen = Counter()
    for d in dashes:
        for t in d.get("sachthemen", []):
            themen[t["thema"]] += t.get("woerter", 0)
    # Clip-Themen (YouTube)
    clip_topics = Counter()
    for s in (yt.get("sessions") or {}).values():
        for tp in s.get("topics", []):
            clip_topics[tp] += 1

    # Redner:innen (Redevolumen über alle Sitzungen)
    redner = defaultdict(lambda: {"woerter": 0, "reden": 0, "fraktion": ""})
    for d in dashes:
        for r in d.get("redner", []):
            e = redner[r["name"]]
            e["woerter"] += r.get("woerter", 0)
            e["reden"] += r.get("reden", 0)
            e["fraktion"] = r.get("fraktion") or e["fraktion"]
    top_redner = sorted(({"name": k, **v} for k, v in redner.items()),
                        key=lambda x: -x["woerter"])[:25]

    # Faktencheck je Person/Fraktion + Trend (amtlich) + YouTube-Inhalts-Faktencheck
    spk, frk, trend = speaker_factcheck()
    ytfc = youtube_factcheck()

    # Verdikt-Gesamtverteilung
    verdikt_total = Counter()
    for d in dashes:
        for v, n in (d.get("faktencheck_bilanz") or {}).items():
            verdikt_total[v] += n

    # Kennzahlen-Summen
    K = Counter()
    for d in dashes:
        for k, v in (d.get("kennzahlen") or {}).items():
            if isinstance(v, (int, float)):
                K[k] += v

    # Content-Insights + Fun Facts (inhaltlich, strukturiert {kat, text})
    def _max(field):
        best = ("-", 0, "")
        for d in dashes:
            v = (d.get("kennzahlen") or {}).get(field, 0)
            if v > best[1]:
                best = (d["sitzung"].get("sitzung_nr"), v, d["sitzung"].get("datum"))
        return best

    applause, heckle, fight, spk_frak = content_insights()
    yt_sessions = yt.get("sessions") or {}
    most_clips = max(((nr, s.get("clips", 0)) for nr, s in yt_sessions.items()),
                     key=lambda x: x[1], default=("-", 0))
    top_frag = sorted(spk["speakers"], key=lambda s: -s["fragwürdig"])
    facts: list[dict] = []

    def add(kat, text):
        if text:
            facts.append({"kat": kat, "text": text})

    def _de(n):  # 1234567 → 1.234.567
        return f"{n:,}".replace(",", ".")

    add("Überblick", f"{len(dashes)} Sitzungen · {_de(K['reden'])} Reden · "
        f"{_de(K['woerter'])} Wörter · {_de(K['saalreaktionen'])} Saalreaktionen.")
    if applause:
        n, c = applause.most_common(1)[0]
        fr = spk_frak.get(n, "")
        add("Meistbeklatscht", f"{n} — {c} Beifallsbekundungen während der Reden"
            + (f" ({fr})." if fr else "."))
    if heckle:
        n, c = heckle.most_common(1)[0]
        fr = spk_frak.get(n, "")
        add("Meiste Gegenrufe", f"{n} — {c}× Zwischenruf/Widerspruch während der Reden"
            + (f" ({fr})." if fr else "."))
    for (urh, sp), c in fight.most_common(3):
        add("Schlagabtausch", f"„{urh}“ rief am häufigsten bei {sp} dazwischen — {c}× "
            f"(Zwischenruf/Widerspruch).")
    sr, lg, ga = _max("saalreaktionen"), _max("gesamtzeit_min"), _max("geprüfte_aussagen")
    add("Hitzigste Sitzung", f"Sitzung {sr[0]} — {sr[1]} Saalreaktionen ({sr[2]}).")
    add("Längste Sitzung", f"Sitzung {lg[0]} — {lg[1]} Minuten ({lg[2]}).")
    add("Meiste geprüfte Aussagen", f"Sitzung {ga[0]} — {ga[1]} ({ga[2]}).")
    add("Meiste YouTube-Clips", f"Sitzung {most_clips[0]} — {most_clips[1]} Clips.")
    if top_redner:
        add("Vielredner:in", f"{top_redner[0]['name']} — {_de(top_redner[0]['woerter'])} Wörter "
            f"({top_redner[0]['fraktion']}).")
    if top_frag and top_frag[0]["fragwürdig"]:
        t = top_frag[0]
        add("Meiste fragwürdige Aussagen (KI-Vorschlag)",
            f"{t['name']} — {t['fragwürdig']} von {t['geprüft']} geprüft.")
    add("Hinweis", "„Ähnliche Reden“ (semantisch) folgt über den Vektor-Index; der "
        "Zwischenruf-urheber ist meist fraktions-, nicht personenscharf.")
    fun_facts = facts

    out = {
        "meta": {
            "titel": "Bundestag WP21 — Aggregat-Dashboard (alle Sitzungen)",
            "stand": datetime.date.today().isoformat(),
            "quellen": {
                "amtliche_dashboards": len(dashes),
                "voll_graphen_mit_faktencheck": len(trend),
                "youtube_sitzungen_mit_clips": yt.get("sessions_ingested", 0),
                "youtube_clips_gesamt": yt.get("total_clips", 0),
            },
            "disclaimer_faktencheck": DISCLAIMER,
            "hinweis": ("Faktencheck-Bilanzen existieren nur für die per LLM/Retrieval geprüften "
                        "Showcase-Sitzungen (70–81 + 20/214); Themen/Redner:innen über alle "
                        "verfügbaren Dashboards."),
        },
        "kennzahlen": dict(K),
        "themen_nach_redevolumen": [{"thema": t, "woerter": w} for t, w in themen.most_common(15)],
        "youtube_clip_themen": [{"thema": t, "clips": n} for t, n in clip_topics.most_common(15)],
        "top_redner": top_redner,
        "faktencheck": {
            "verdikt_gesamt": {v: verdikt_total.get(v, 0) for v in VERDIKTE},
            "je_fraktion": frk["fraktionen"],
            "je_person": spk["speakers"][:40],
            "trend_je_sitzung": trend,
        },
        "youtube_abdeckung": {
            "ingestiert": yt.get("sessions_ingested", 0),
            "gesamt": yt.get("sessions_total", 0),
            "ohne_clips": yt.get("sessions_without_clips", []),
            "clips_gesamt": yt.get("total_clips", 0),
        },
        "youtube_faktencheck": ytfc,
        "fun_facts": fun_facts,
    }
    out["meta"]["quellen"]["youtube_faktencheck_sitzungen"] = len(ytfc["je_sitzung"])

    WEB.mkdir(parents=True, exist_ok=True)
    (WEB / "aggregate_dashboard.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("✓ web/data/aggregate_dashboard.json")
    print(f"  Sitzungen(Dashboards): {len(dashes)} · Faktencheck-Sitzungen: {len(trend)} · "
          f"YouTube: {out['meta']['quellen']['youtube_sitzungen_mit_clips']}")
    print(f"  Themen: {len(out['themen_nach_redevolumen'])} · Redner: {len(top_redner)} · "
          f"geprüfte Personen: {len(spk['speakers'])}")
    print(f"  Verdikt gesamt: {out['faktencheck']['verdikt_gesamt']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
