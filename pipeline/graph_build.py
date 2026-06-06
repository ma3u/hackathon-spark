"""
Graph-Aufbau — strukturiertes Protokoll -> Knowledge Graph (SPARK-Format).

Ausgabeschema (kompatibel zu graph-insurance / graph-investigation / graph-eAkte):
    {metadata, nodes:[{id,label,type,subtype,...}], relationships:[{source_id,target_id,relationship_type,...}]}

Vier-Schichten-Ontologie (wie in den Schwester-Prototypen):
  L1 Normativ   — Norm (GemO §37 Beschlussfähigkeit, GemO §18 Befangenheit)
  L2 Zeitlich   — Sitzung (Datum), Fristen an Aufgaben
  L3 Prozedural — TOP -> Antrag -> Abstimmung -> Beschluss -> Aufgabe
  L4 Fallbezug  — Person, Fraktion, Redebeitrag
  + Provenienz  — Transkriptsegment (Audio start/end) BELEGT jede Aussage
"""

from __future__ import annotations

import re

from .extract import Protocol


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def build_graph(p: Protocol, *, audio_file: str, sitzung_id: str, factchecks=None) -> dict:
    nodes: list[dict] = []
    rels: list[dict] = []
    seen: set[str] = set()

    def node(nid, label, ntype, subtype="", **props):
        if nid in seen:
            return nid
        seen.add(nid)
        nodes.append({"id": nid, "label": label, "type": ntype, "subtype": subtype, **props})
        return nid

    def rel(src, tgt, rtype, **props):
        rels.append({"source_id": src, "target_id": tgt, "relationship_type": rtype, **props})

    # ── L2: Sitzung ──────────────────────────────────────────────────────────
    m = p.meeting
    node(sitzung_id, f"Sitzung {m.get('datum','')}", "Sitzung", "Öffentliche Gemeinderatssitzung",
         gremium=m.get("gremium", ""), datum=m.get("datum", ""), ort=m.get("ort", ""),
         beschlussfaehig=str(m.get("beschlussfaehig", "")), audio_file=audio_file)

    # ── L1: Normen (referenziert aus Beschlussfähigkeit + Befangenheit) ──────
    norm_bf = node("gemo_37", "GemO §37 Beschlussfähigkeit", "Norm", "Gemeindeordnung",
                   schicht="normativ")
    if m.get("beschlussfaehig"):
        rel(sitzung_id, norm_bf, "BESCHLUSSFAEHIG_NACH")

    # ── L4: Personen + Fraktionen (aus Sprechern der Utterances) ─────────────
    persons: dict[str, dict] = {}
    for u in p.utterances:
        persons.setdefault(u.speaker_name, {"rolle": u.rolle, "fraktion": u.fraktion})
    for name, info in persons.items():
        pid = "person_" + _slug(name)
        node(pid, name, "Person", info["rolle"])
        if info["fraktion"]:
            fid = "fraktion_" + _slug(info["fraktion"])
            node(fid, info["fraktion"], "Fraktion", "Ratsfraktion", schicht="fallbezug")
            rel(pid, fid, "MITGLIED_VON")
        if "Vorsitz" in (info["rolle"] or ""):
            rel(sitzung_id, pid, "GELEITET_VON")
        if "Schriftführer" in (info["rolle"] or ""):
            rel(sitzung_id, pid, "PROTOKOLLIERT_VON")

    def person_id(name: str) -> str:
        return "person_" + _slug(name)

    # ── L3: TOPs ─────────────────────────────────────────────────────────────
    top_id = {}
    for top in p.tops:
        tid = f"top_{top['nummer']}"
        top_id[top["nummer"]] = node(tid, f"TOP {top['nummer']}: {top['titel']}",
                                     "Tagesordnungspunkt", "", nummer=top["nummer"], schicht="prozedural")
        rel(sitzung_id, tid, "HAT_TOP")

    # ── L3: Anträge ──────────────────────────────────────────────────────────
    for i, a in enumerate(p.antraege):
        aid = f"antrag_t{a['top_nummer']}_{i}"
        node(aid, f"Antrag ({a['steller']})", "Antrag", a["steller"], text=a["text"][:240],
             schicht="prozedural")
        if a["top_nummer"] in top_id:
            rel(top_id[a["top_nummer"]], aid, "BEHANDELT_ANTRAG")

    # ── L3: Abstimmungen ─────────────────────────────────────────────────────
    abst_by_top = {}
    for v in p.abstimmungen:
        vid = f"abstimmung_t{v['top_nummer']}"
        abst_by_top[v["top_nummer"]] = node(
            vid, f"Abstimmung TOP {v['top_nummer']} ({v['ja']}:{v['nein']}:{v['enthaltung']})",
            "Abstimmung", v["ergebnis"], ja=v["ja"], nein=v["nein"], enthaltung=v["enthaltung"],
            ergebnis=v["ergebnis"], schicht="prozedural")
        if v["top_nummer"] in top_id:
            rel(top_id[v["top_nummer"]], vid, "ENTSCHIEDEN_DURCH")

    # ── L3: Beschlüsse + Aufgaben ────────────────────────────────────────────
    for b in p.beschluesse:
        bid = "beschluss_" + b["nummer"]
        node(bid, f"Beschluss {b['nummer']}", "Beschluss", "", nummer=b["nummer"],
             text=b["text"][:300], schicht="prozedural")
        if b["top_nummer"] in abst_by_top:
            rel(abst_by_top[b["top_nummer"]], bid, "FUEHRT_ZU")
        if b["top_nummer"] in top_id:
            rel(top_id[b["top_nummer"]], bid, "ERGEBNIS_BESCHLUSS")
    for i, t in enumerate(p.aufgaben):
        gid = f"aufgabe_{i}"
        node(gid, "Aufgabe: " + t["text"], "Aufgabe", t["zustaendig"], frist=t["frist"],
             zustaendig=t["zustaendig"], schicht="prozedural")
        if t.get("beschluss_nummer"):
            rel("beschluss_" + t["beschluss_nummer"], gid, "ERZEUGT_AUFGABE")
        elif t.get("top_nummer") in top_id:
            rel(top_id[t["top_nummer"]], gid, "ERZEUGT_AUFGABE")

    # ── L1+L4: Befangenheiten ────────────────────────────────────────────────
    norm_bef = None
    for bf in p.befangenheiten:
        if norm_bef is None:
            norm_bef = node("gemo_18", "GemO §18 Befangenheit", "Norm", "Gemeindeordnung",
                            schicht="normativ")
        pid = person_id(bf["person"])
        if bf["top_nummer"] in top_id:
            rel(pid, top_id[bf["top_nummer"]], "BEFANGEN_BEI", rechtsgrundlage=bf["rechtsgrundlage"])
        rel(pid, norm_bef, "BEFANGENHEIT_NACH")

    # ── L4: Redebeiträge (ID stabil am Utterance-Index, damit Reaktionen passen) ──
    def rede_id(r):
        q = r.get("quelle_utterances") or [0]
        return f"redebeitrag_{q[0]}"
    for r in p.redebeitraege:
        rid = rede_id(r)
        node(rid, f"Redebeitrag {r['person']} (TOP {r['top_nummer']}, {r['timecode']})",
             "Redebeitrag", r.get("fraktion") or "", timecode=r["timecode"],
             start_sec=r["start"], schicht="fallbezug")
        rel(person_id(r["person"]), rid, "HAT_REDEBEITRAG")
        if r["top_nummer"] in top_id:
            rel(rid, top_id[r["top_nummer"]], "ZU_TOP")

    # ── Fragen an die Bundesregierung ────────────────────────────────────────
    for i, fr in enumerate(p.fragen):
        fid = f"frage_{i}"
        node(fid, f"Frage an die Bundesregierung ({fr['steller']})", "Frage", fr.get("fraktion") or "",
             text=fr["text"][:240], schicht="prozedural")
        rel(person_id(fr["steller"]), fid, "STELLT_FRAGE")
        if fr["top_nummer"] in top_id:
            rel(fid, top_id[fr["top_nummer"]], "ZU_TOP")

    # ── L4 + Faktencheck: Aussagen, Verdikte, Quellen ────────────────────────
    fc_by_idx = {fc.aussage_index: fc for fc in (factchecks or [])}
    for i, a in enumerate(p.aussagen):
        aid = f"aussage_{i}"
        node(aid, f"Aussage: {a['text'][:60]}…", "Aussage", a.get("fraktion") or "",
             text=a["text"][:300], person=a["person"], schicht="fallbezug")
        rel(person_id(a["person"]), aid, "TAETIGT_AUSSAGE")
        if a["top_nummer"] in top_id:
            rel(aid, top_id[a["top_nummer"]], "ZU_TOP")

        fc = fc_by_idx.get(i)
        if fc:
            cid = f"faktencheck_{i}"
            node(cid, f"Faktencheck: {fc.verdikt}", "Faktencheck", fc.verdikt,
                 verdikt=fc.verdikt, begruendung=fc.begruendung[:400], schicht="faktencheck")
            rel(aid, cid, "GEPRUEFT_ALS", verdikt=fc.verdikt)
            # Grundsatz: JEDER Faktencheck hat eine Quelle (auch 'unbelegt' → Korpus-Referenz).
            q = fc.quelle or {"titel": "Quelle fehlt", "stand": "", "url": ""}
            qid = "quelle_" + _slug(q.get("titel", "quelle"))
            node(qid, q.get("titel", "Quelle"), "Quelle", q.get("stand", ""),
                 url=q.get("url", ""), stand=q.get("stand", ""), schicht="faktencheck")
            rel(cid, qid, "BELEGT_MIT")

    # ── Saalreaktionen aus dem amtlichen XML: Beifall/Zwischenruf/Lachen ─────
    # (Antwort auf "Buhrufe/Jubel" — hier direkt aus der <kommentar>-Quelle.)
    for i, k in enumerate(p.kommentare):
        kid = f"ereignis_{i}"
        label = k["typ"] + (f" ({k['intensitaet']})" if k.get("intensitaet") else "") \
            + (f" — {k['urheber']}" if k.get("urheber") else "")
        node(kid, label, "AkustischesEreignis", k["typ"], text=k["text"][:240],
             urheber=k.get("urheber") or "", intensitaet=k.get("intensitaet") or "",
             start_sec=k.get("start_sec", ""), herkunft=k.get("herkunft", "protokoll"),
             schicht="fallbezug")
        if k["top_nummer"] in top_id:
            rel(top_id[k["top_nummer"]], kid, "HAT_REAKTION")
        if k.get("rede_index", -1) >= 0:
            rel(kid, f"redebeitrag_{k['rede_index']}", "REAKTION_AUF")
            rel(kid, f"segment_{k['rede_index']}", "BELEGT_DURCH")  # Audio-Provenienz

    # ── Provenienz: Transkriptsegmente (Audio-Zeitstempel) ───────────────────
    for idx, u in enumerate(p.utterances):
        sid = f"segment_{idx}"
        node(sid, f"Segment {u.timecode} ({u.speaker_name})", "Transkriptsegment", u.speaker_name,
             start_sec=u.start, end_sec=u.end, timecode=u.timecode, sprecher=u.speaker_name,
             text=u.text[:500], audio_file=audio_file, schicht="provenienz")

    # Provenienz-Kanten: jede extrahierte Aussage -> ihre Quell-Segmente
    def belegt(entity_id: str, src_list):
        for s_idx in src_list or []:
            rel(entity_id, f"segment_{s_idx}", "BELEGT_DURCH")

    for top in p.tops:
        belegt(f"top_{top['nummer']}", top.get("quelle_utterances"))
    for b in p.beschluesse:
        belegt("beschluss_" + b["nummer"], b.get("quelle_utterances"))
    for v_i, v in enumerate(p.abstimmungen):
        belegt(f"abstimmung_t{v['top_nummer']}", v.get("quelle_utterances"))
    for r in p.redebeitraege:
        belegt(rede_id(r), r.get("quelle_utterances"))
    for i, a in enumerate(p.aussagen):
        belegt(f"aussage_{i}", a.get("quelle_utterances"))

    metadata = {
        "title": "Protokoll-Knowledge-Graph — Gemeinderatssitzung Musterbach",
        "source_audio": audio_file,
        "generated_by": "graph-protokoll pipeline (SPARK Challenge 2 prototype)",
        "ontology_layers": ["normativ", "zeitlich", "prozedural", "fallbezug", "provenienz"],
        "node_count": len(nodes),
        "relationship_count": len(rels),
    }
    return {"metadata": metadata, "nodes": nodes, "relationships": rels}
