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

from . import (bundestag_xml, graph_build, export, dashboard, accessible, factcheck,
               subtitles, protocol_html, mediathek)
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
        "yt_name": f"yt_{wp}_{nnn}", "amt_name": f"amt_{wp}_{nnn}", "md_name": f"md_{wp}_{nnn}",
        "yt_prefix": f"yt_{wp}_{nnn}", "amt_prefix": f"amt_{wp}_{nnn}", "md_prefix": f"md_{wp}_{nnn}",
        "sid_yt": f"sitzung_yt_{wp}_{nnn}", "sid_amt": f"sitzung_amt_{wp}_{nnn}",
        "sid_md": f"sitzung_md_{wp}_{nnn}",
        "pdf": DSERVER_PDF.format(wp=wp, nnn=nnn), "xml": DSERVER_XML.format(wp=wp, nnn=nnn),
    }


import re as _re
from collections import defaultdict as _dd

_TITLES = _re.compile(r"\b(dr|prof|h\.?c|mdb|bundesminister(in)?|staatsminister(in)?|"
                      r"parl|staatssekretär(in)?)\b\.?", _re.I)


def _norm_name(s: str) -> str:
    s = _TITLES.sub("", s or "")
    s = _re.sub(r"[^a-zäöüß ]", " ", s.lower())
    return " ".join(s.split())


def _attach_video_links(p, clips) -> int:
    """Mediathek-Clips (Sprecher→Clip-URL) den XML-Redebeiträgen zuordnen (Name, in Reihenfolge).

    Verschmilzt die zwei amtlichen Quellen: das XML liefert Struktur/Volltext/Saalreaktionen,
    die Mediathek den Video-Deeplink JE REDE (r['video_url'] → dbtg.tv/fvid). Best-effort über
    normalisierten Namen (mit Nachnamen-Fallback). Gibt die Trefferzahl zurück.
    """
    q = _dd(list)
    for c in clips:
        q[_norm_name(c["speaker"])].append(c["url"])
    matched = 0
    for r in p.redebeitraege:
        key = _norm_name(r["person"])
        if q.get(key):
            r["video_url"] = q[key].pop(0)
            matched += 1
            continue
        surn = key.split()[-1] if key.split() else ""
        for k2 in list(q):  # Nachnamen-Fallback (XML „Dr. X" ↔ Mediathek „X")
            if q[k2] and k2.split() and k2.split()[-1] == surn:
                r["video_url"] = q[k2].pop(0)
                matched += 1
                break
    return matched


def _structural(graph: dict) -> dict:
    """Pages-Projektion: ohne Transkriptsegment-Knoten (Provenienz bleibt vollständig in Neo4j).

    Macht den committeten Graph klein UND zeigt die offizielle Struktur sauber (Sitzung→TOP→
    Redebeitrag→Person/Fraktion + Saalreaktion + Faktencheck) statt eines Provenienz-Halos.
    """
    drop = {n["id"] for n in graph["nodes"] if n["type"] == "Transkriptsegment"}
    nodes = [n for n in graph["nodes"] if n["id"] not in drop]
    rels = [r for r in graph["relationships"]
            if r["source_id"] not in drop and r["target_id"] not in drop]
    md = dict(graph["metadata"])
    md["node_count"], md["relationship_count"] = len(nodes), len(rels)
    md["pages_projektion"] = "ohne Transkriptsegmente (Provenienz vollständig in Neo4j)"
    return {"metadata": md, "nodes": nodes, "relationships": rels}


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


def mediathek_protocol(clips, *, wp, nr):
    """Mediathek-Clips (mit clip['text']) → Protocol (SPRECHER-attribuiert) + Deeplinks je Rede.

    Jede Rede ist ein eigener Clip → ein Redebeitrag + eine Utterance; der Deeplink ist die
    Clip-URL (dbtg.tv/fvid/<id>), kein Sekunden-Offset. Liefert (Protocol, rede_links:
    {utterance_index: clip_url}).
    """
    p = extract_protocol()
    datum = clips[0]["datum"] if clips else ""
    p.meeting = {"gremium": "Deutscher Bundestag (Mediathek-Mitschnitt)", "datum": datum,
                 "wahlperiode": str(wp), "sitzung_nr": str(int(nr)), "ort": "Berlin"}
    top_nr: dict[str, int] = {}
    rede_links: dict[int, str] = {}
    for i, c in enumerate(clips):
        if c["top"] not in top_nr:
            top_nr[c["top"]] = len(top_nr) + 1
        tn = top_nr[c["top"]]
        p.utterances.append(Utterance(
            start=float(i), end=float(i), speaker_label=c["fvid"], speaker_name=c["speaker"],
            rolle=c["role"], fraktion=c["fraktion"], text=c["text"], herkunft="protokoll"))
        p.redebeitraege.append({"person": c["speaker"], "fraktion": c["fraktion"],
                                "top_nummer": tn, "timecode": c["uhr"], "start": 0.0,
                                "quelle_utterances": [i]})
        rede_links[i] = c["url"]
    p.tops = [{"nummer": n, "titel": t, "quelle_utterances": [i for i, c in enumerate(clips)
                                                              if top_nr[c["top"]] == n]}
              for t, n in top_nr.items()]
    return p, rede_links


def llm_factcheck_mediathek(p, *, model, base_url, api_key, max_passages: int = 16):
    """LLM extrahiert+prüft echte Claims aus den Reden; Aussagen tragen den echten Sprecher."""
    n = len(p.utterances)
    step = max(1, n // max_passages)
    passages = [{"text": " ".join(u.text for u in p.utterances[i:i + step])[:6000],
                 "utt_index": i, "start": 0.0} for i in range(0, n, step)]
    res = factcheck.factcheck_transcript_llm(
        passages, model=model, base_url=base_url, api_key=api_key, max_passages=max_passages)
    p.aussagen, checks = [], []
    for i, r in enumerate(res):
        ui = r["utt_index"]
        u = p.utterances[ui] if 0 <= ui < n else None
        person = u.speaker_name if u else "Redner:in"
        fraktion = u.fraktion if u else None
        p.aussagen.append({"text": r["aussage"], "person": person, "fraktion": fraktion,
                           "top_nummer": 1, "quelle_utterances": [ui]})
        checks.append(factcheck.FactCheck(
            aussage_index=i, text=r["aussage"], person=person, fraktion=fraktion,
            top_nummer=1, verdikt=r["verdikt"], begruendung=r["begruendung"], quelle=r["quelle"],
            quelle_utterances=[ui], score=0.0))
    return checks


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
                    write_web_graph=False, mediathek_match=False, neo4j=None) -> dict:
    """Offizieller Graph: amtliches XML (Struktur/Volltext/Saalreaktionen/Faktencheck) +
    optional Mediathek-Video-Deeplink je Rede. Vollgraph (mit Provenienz) → Neo4j/output;
    schlanke strukturelle Projektion → web/ (Pages)."""
    ids = _ids(wp, nr)
    p = official_protocol(xml_path)
    matched = 0
    if mediathek_match:
        try:
            matched = _attach_video_links(p, mediathek.collect_session(nr))  # nur Sprecher+URL
        except Exception:
            matched = 0
    if factchecks is not None:
        checks = factchecks
    elif az:
        checks = llm_factcheck_official(p, **az)
    else:
        checks = []
    graph = graph_build.build_graph(p, audio_file=Path(xml_path).name,
                                    sitzung_id=ids["sid_amt"], factchecks=checks)
    _decorate(graph, herkunft="amtlich", quelle_typ="amtlich", quelle_url=ids["pdf"],
              quelle_label=f"Bundestag Open Data — Plenarprotokoll {wp}/{int(nr)}"
                           + (f" · Mediathek-Video je Rede ({matched})" if matched else ""),
              official_pdf=ids["pdf"], official_xml=ids["xml"],
              disclaimer=_FC_DISCLAIMER if checks else None)
    graph["metadata"]["mediathek_verlinkt"] = matched
    OUT.mkdir(parents=True, exist_ok=True)
    export.write_json(graph, OUT / f"{ids['amt_name']}_graph_data.json")  # Vollgraph (Provenienz)
    WEB.mkdir(parents=True, exist_ok=True)
    export.write_json(dashboard.compute_dashboard(p, checks), WEB / f"{ids['amt_name']}_dashboard.json")
    if write_web_graph:  # Pages: strukturelle Projektion (klein, ohne Segment-Halo)
        export.write_json(_structural(graph), WEB / f"{ids['amt_name']}.json")
        rede_links = {r["quelle_utterances"][0]: r["video_url"] for r in p.redebeitraege
                      if r.get("video_url") and r.get("quelle_utterances")}
        html = protocol_html.render(
            p, factchecks=checks, quelle_url=ids["pdf"], rede_links=rede_links,
            quelle_label=f"amtliches Plenarprotokoll {wp}/{int(nr)}",
            official_pdf=ids["pdf"], official_xml=ids["xml"],
            disclaimer=_FC_DISCLAIMER if checks else None,
            title=f"Deutscher Bundestag — {int(nr)}. Sitzung, {p.meeting.get('datum','')} "
                  f"(amtliches Protokoll + Mediathek-Video)")
        (WEB / f"{ids['amt_name']}_protokoll.html").write_text(html, encoding="utf-8")
        (WEB / f"{ids['amt_name']}_barrierefrei.txt").write_text(
            accessible.summarize(p, checks), encoding="utf-8")
    if neo4j is not None or load:
        to_neo4j(graph, prefix=ids["amt_prefix"], load=load, **(neo4j or {}))  # Vollgraph
    return {"name": ids["amt_name"], "nodes": graph["metadata"]["node_count"],
            "rels": graph["metadata"]["relationship_count"], "datum": p.meeting.get("datum", ""),
            "reden": len(p.redebeitraege), "aussagen": len(p.aussagen),
            "saalreaktionen": len(p.kommentare), "checks": len(checks), "mediathek_verlinkt": matched,
            "has_graph": write_web_graph, "quelle_url": ids["pdf"], "protocol": p}


def ingest_mediathek(*, wp, nr, az=None, load=False, write_web=True, neo4j=None,
                     max_pages: int = 60) -> dict | None:
    """Komplett: Mediathek-Clips → SPRECHER-attribuiertes Protocol → Graph + web/ + Neo4j (md_).

    Füllt YouTube-Lücken mit korrigierten amtlichen Untertiteln; Deeplink je Rede (dbtg.tv).
    Gibt None zurück, wenn die Sitzung (noch) keine Clips/Untertitel hat.
    """
    ids = _ids(wp, nr)
    clips = mediathek.fetch_srts(mediathek.collect_session(nr, max_pages=max_pages))
    if not clips:
        return None
    p, rede_links = mediathek_protocol(clips, wp=wp, nr=nr)
    checks = llm_factcheck_mediathek(p, **az) if az else []
    graph = graph_build.build_graph(p, audio_file=f"mediathek_{wp}_{ids['nnn']}",
                                    sitzung_id=ids["sid_md"], factchecks=checks)
    quelle_url = clips[0]["url"]
    _decorate(graph, herkunft="mediathek", quelle_typ="mediathek", quelle_url=quelle_url,
              quelle_label=f"Bundestag-Mediathek — {nr}. Sitzung ({p.meeting['datum']}), korrigierte Untertitel",
              official_pdf=ids["pdf"], official_xml=ids["xml"],
              disclaimer=_FC_DISCLAIMER if checks else None)
    OUT.mkdir(parents=True, exist_ok=True)
    export.write_json(graph, OUT / f"{ids['md_name']}_graph_data.json")
    if write_web:
        WEB.mkdir(parents=True, exist_ok=True)
        export.write_json(graph, WEB / f"{ids['md_name']}.json")
        export.write_json(dashboard.compute_dashboard(p, checks), WEB / f"{ids['md_name']}_dashboard.json")
        html = protocol_html.render(
            p, factchecks=checks, quelle_url=quelle_url, rede_links=rede_links,
            quelle_label="Bundestag-Mediathek (korrigierte Untertitel)",
            official_pdf=ids["pdf"], official_xml=ids["xml"],
            disclaimer=_FC_DISCLAIMER if checks else None,
            title=f"Deutscher Bundestag — {nr}. Sitzung, {p.meeting['datum']} (Mediathek)")
        (WEB / f"{ids['md_name']}_protokoll.html").write_text(html, encoding="utf-8")
        (WEB / f"{ids['md_name']}_barrierefrei.txt").write_text(
            accessible.summarize(p, checks), encoding="utf-8")
    if neo4j is not None or load:
        to_neo4j(graph, prefix=ids["md_prefix"], load=load, **(neo4j or {}))
    return {"name": ids["md_name"], "nodes": graph["metadata"]["node_count"],
            "rels": graph["metadata"]["relationship_count"], "reden": len(clips),
            "datum": p.meeting["datum"], "tops": len(p.tops), "checks": len(checks),
            "quelle_url": quelle_url, "protocol": p}
