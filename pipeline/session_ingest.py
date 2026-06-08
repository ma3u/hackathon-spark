"""
Sitzungs-Ingestion — eine Bundestagssitzung in den Graphen, aus ECHTEN Quellen.

Zwei klar getrennte Graphen pro Sitzung, beide mit gemerkter Quelle:
  • herkunft='youtube'  (Präfix yt_<wp>_<nr>)  — Mitschnitt @bundestag, Zeit-Deeplinks
  • herkunft='amtlich'  (Präfix amt_<wp>_<nr>) — Open-Data-Plenarprotokoll-XML (dserver)
Person/Fraktion/Norm/Quelle bleiben global (SHARED_TYPES) → derselbe Mensch in beiden
Graphen, aber Segmente/Reden/Aussagen sind sitzungs- und quellenspezifisch.

Produktivpfad: LLM-Faktencheck (Azure Mistral, .env) über reale Aussagen — ausdrücklich
KI-Vorschläge mit Disclaimer (kein Urteil), Quelle Pflicht. Faktencheck läuft IMMER gegen
reale Inhalte, nie gegen den fiktiven Demo-Korpus.
Demopfad: ohne --load (Neo4j dry-run) und/oder ohne Faktencheck.
"""

from __future__ import annotations

from pathlib import Path

from . import bundestag_xml, graph_build, export, dashboard, accessible, factcheck, subtitles, protocol_html
from .align import Utterance

REPO = Path(__file__).resolve().parent.parent
WEB = REPO / "web" / "data"
OUT = REPO / "output"

DSERVER_PDF = "https://dserver.bundestag.de/btp/{wp}/{wp}{nnn}.pdf"
DSERVER_XML = "https://dserver.bundestag.de/btp/{wp}/{wp}{nnn}.xml"


def _ids(wp, nr) -> dict:
    """Namens-/Quellen-Bausteine für eine Sitzung (wp, nr → Präfixe, URLs)."""
    nnn = f"{int(nr):03d}"
    return {
        "wp": str(wp), "nr": str(int(nr)), "nnn": nnn,
        "yt_name": f"yt_{wp}_{nnn}", "amt_name": f"amt_{wp}_{nnn}",
        "yt_prefix": f"yt_{wp}_{nnn}", "amt_prefix": f"amt_{wp}_{nnn}",
        "sid_yt": f"sitzung_yt_{wp}_{nnn}", "sid_amt": f"sitzung_amt_{wp}_{nnn}",
        "pdf": DSERVER_PDF.format(wp=wp, nnn=nnn), "xml": DSERVER_XML.format(wp=wp, nnn=nnn),
    }


# ── Protokoll-Konstruktion ──────────────────────────────────────────────────────

def youtube_protocol(vtt_path, *, wp, nr, video_id, titel, datum,
                     lines_per_seg: int = 30):
    """YouTube-Untertitel (.vtt) → Protocol (utterances mit Startsekunden für Deeplinks)."""
    segs = subtitles.youtube_segments(vtt_path, lines_per_seg=lines_per_seg)
    p = extract_protocol()
    p.meeting = {"gremium": "Deutscher Bundestag (YouTube-Mitschnitt)", "datum": datum,
                 "wahlperiode": str(wp), "sitzung_nr": str(int(nr)), "ort": "Berlin"}
    for i, s in enumerate(segs):
        p.utterances.append(Utterance(
            start=float(s["start"]), end=float(s["end"]), speaker_label=f"S{i}",
            speaker_name="Sprecher:in (Video)", rolle="Redner:in", fraktion=None,
            text=s["text"], herkunft="audio"))  # herkunft=audio → timecode mm:ss, Deeplinks
    # TOP provenance = ALLE Segmente → BELEGT_DURCH-Kanten, sonst hängen die Segmente
    # ohne Untertitel-Sprecherlabel im Graphen lose herum (jedes Segment am TOP belegt).
    p.tops = [{"nummer": 1, "titel": titel, "quelle_utterances": list(range(len(p.utterances)))}]
    return p


def official_protocol(xml_path):
    """Amtliches Plenarprotokoll-XML → Protocol."""
    return bundestag_xml.parse_plenarprotokoll(Path(xml_path))


def extract_protocol():
    from .extract import Protocol
    return Protocol()


# ── Faktencheck (immer reale Inhalte; LLM = Vorschlag mit Disclaimer) ────────────

def llm_factcheck_youtube(p, *, model, base_url, api_key, max_passages: int = 16):
    """LLM extrahiert echte Claims aus dem Transkript und prüft sie. Setzt p.aussagen."""
    n = len(p.utterances)
    step = max(1, n // max_passages)
    passages = [{"text": " ".join(u.text for u in p.utterances[i:i + step]),
                 "utt_index": i, "start": p.utterances[i].start}
                for i in range(0, n, step)]
    res = factcheck.factcheck_transcript_llm(
        passages, model=model, base_url=base_url, api_key=api_key, max_passages=max_passages)
    p.aussagen, checks = [], []
    for i, r in enumerate(res):
        p.aussagen.append({"text": r["aussage"], "person": "Sprecher:in (Video)", "fraktion": None,
                           "top_nummer": 1, "quelle_utterances": [r["utt_index"]]})
        checks.append(factcheck.FactCheck(
            aussage_index=i, text=r["aussage"], person="Sprecher:in (Video)", fraktion=None,
            top_nummer=1, verdikt=r["verdikt"], begruendung=r["begruendung"], quelle=r["quelle"],
            quelle_utterances=[r["utt_index"]], score=0.0))
    return checks


def llm_factcheck_official(p, *, model, base_url, api_key, max_claims: int = 12):
    """Prüft die aus dem amtlichen XML extrahierten realen Aussagen per LLM (Disclaimer)."""
    if not p.aussagen:
        return []
    return factcheck.factcheck_with_llm(
        p.aussagen, model=model, base_url=base_url, api_key=api_key, max_claims=max_claims)


# ── Graph + Ausgaben ────────────────────────────────────────────────────────────

def _decorate(graph, *, herkunft, quelle_url, quelle_label, quelle_typ,
              video_id=None, official_pdf=None, official_xml=None, disclaimer=None):
    md = graph["metadata"]
    md["herkunft"] = herkunft
    md["quelle_typ"] = quelle_typ
    md["quelle_url"] = quelle_url
    md["quelle_label"] = quelle_label
    if video_id:
        md["video_id"] = video_id
    if official_pdf:
        md["amtliches_pdf"] = official_pdf
    if official_xml:
        md["amtliches_xml"] = official_xml
    if disclaimer:
        md["factcheck_disclaimer"] = disclaimer
    return graph


def to_neo4j(graph, *, prefix, load, uri=None, user=None, password=None):
    """Graph sitzungs-namespaced nach Neo4j (dry-run, wenn load=False)."""
    from . import neo4j_loader
    ns = neo4j_loader.namespace_graph(graph, prefix)
    neo4j_loader.load_graph(ns, dry_run=not load, uri=uri, user=user, password=password)
    return ns


_FC_DISCLAIMER = ("Faktencheck automatisch durch KI (Mistral) erzeugt — ungeprüfte "
                  "Vorschläge, kein Urteil über reale Personen.")


def ingest_youtube(vtt_path, *, wp, nr, video_id, titel, datum, az=None, factchecks=None,
                   load=False, write_web=True, neo4j=None, lines_per_seg: int = 30) -> dict:
    """Komplett: YouTube-VTT → Protocol → (LLM-Faktencheck) → Graph → web/ + Neo4j (yt_)."""
    ids = _ids(wp, nr)
    p = youtube_protocol(vtt_path, wp=wp, nr=nr, video_id=video_id, titel=titel,
                         datum=datum, lines_per_seg=lines_per_seg)
    # Faktencheck am SELBEN Protokoll (setzt p.aussagen) — sonst gehen die Aussage-/
    # Faktencheck-Knoten verloren, weil build_graph p.aussagen liest.
    if factchecks is not None:
        checks = factchecks
    elif az:
        checks = llm_factcheck_youtube(p, **az)
    else:
        checks = []
    graph = graph_build.build_graph(p, audio_file=f"{video_id}.mp4",
                                    sitzung_id=ids["sid_yt"], factchecks=checks)
    yt_url = f"https://www.youtube.com/watch?v={video_id}"
    _decorate(graph, herkunft="youtube", quelle_typ="youtube", quelle_url=yt_url,
              quelle_label=f"YouTube @bundestag — {titel} ({nr}. Sitzung, {datum})",
              video_id=video_id, official_pdf=ids["pdf"], official_xml=ids["xml"],
              disclaimer=_FC_DISCLAIMER if checks else None)
    OUT.mkdir(parents=True, exist_ok=True)
    export.write_json(graph, OUT / f"{ids['yt_name']}_graph_data.json")
    if write_web:
        WEB.mkdir(parents=True, exist_ok=True)
        export.write_json(graph, WEB / f"{ids['yt_name']}.json")
        export.write_json(dashboard.compute_dashboard(p, checks), WEB / f"{ids['yt_name']}_dashboard.json")
        html = protocol_html.render(
            p, factchecks=checks, quelle_url=yt_url, video_id=video_id,
            quelle_label=f"YouTube @bundestag — {titel}", official_pdf=ids["pdf"],
            official_xml=ids["xml"], disclaimer=_FC_DISCLAIMER if checks else None,
            title=f"Deutscher Bundestag — {nr}. Sitzung, {datum} (YouTube-Mitschnitt)")
        (WEB / f"{ids['yt_name']}_protokoll.html").write_text(html, encoding="utf-8")
        (WEB / f"{ids['yt_name']}_barrierefrei.txt").write_text(
            accessible.summarize(p, checks), encoding="utf-8")
    if neo4j is not None or load:
        to_neo4j(graph, prefix=ids["yt_prefix"], load=load, **(neo4j or {}))
    return {"name": ids["yt_name"], "nodes": graph["metadata"]["node_count"],
            "rels": graph["metadata"]["relationship_count"], "segmente": len(p.utterances),
            "checks": len(checks), "video_id": video_id, "quelle_url": yt_url,
            "protocol": p}


def ingest_official(xml_path, *, wp, nr, az=None, factchecks=None, load=False,
                    write_web_graph=False, neo4j=None) -> dict:
    """Komplett: amtliches XML → Protocol → (LLM-Faktencheck) → Dashboard(web) + Neo4j (amt_)."""
    ids = _ids(wp, nr)
    p = official_protocol(xml_path)
    if factchecks is not None:
        checks = factchecks
    elif az:
        checks = llm_factcheck_official(p, **az)
    else:
        checks = []
    graph = graph_build.build_graph(p, audio_file=Path(xml_path).name,
                                    sitzung_id=ids["sid_amt"], factchecks=checks)
    _decorate(graph, herkunft="amtlich", quelle_typ="amtlich", quelle_url=ids["pdf"],
              quelle_label=f"Bundestag Open Data — Plenarprotokoll {wp}/{int(nr)}",
              official_pdf=ids["pdf"], official_xml=ids["xml"],
              disclaimer=_FC_DISCLAIMER if checks else None)
    OUT.mkdir(parents=True, exist_ok=True)
    export.write_json(graph, OUT / f"{ids['amt_name']}_graph_data.json")
    WEB.mkdir(parents=True, exist_ok=True)
    # Dashboards (klein) für ALLE amtlichen Sitzungen committen; Vollgraph nur in Neo4j/output.
    export.write_json(dashboard.compute_dashboard(p, checks), WEB / f"{ids['amt_name']}_dashboard.json")
    if write_web_graph:
        export.write_json(graph, WEB / f"{ids['amt_name']}.json")
    if neo4j is not None or load:
        to_neo4j(graph, prefix=ids["amt_prefix"], load=load, **(neo4j or {}))
    return {"name": ids["amt_name"], "nodes": graph["metadata"]["node_count"],
            "rels": graph["metadata"]["relationship_count"], "datum": p.meeting.get("datum", ""),
            "reden": len(p.redebeitraege), "aussagen": len(p.aussagen),
            "saalreaktionen": len(p.kommentare), "checks": len(checks),
            "quelle_url": ids["pdf"], "protocol": p}
