"""
GraphRAG — Beantwortung von Fragen über den Protokoll-Graphen mit Provenienz.

Warum Graph statt flachem Vektor-RAG? Protokollfragen sind mehrhop und strukturiert:
  "Welcher Beschluss entstand aus welcher Abstimmung unter welchem TOP — und wo
   im Audio steht das?" -> Beschluss -[FUEHRT_ZU<-]- Abstimmung -[ENTSCHIEDEN_DURCH<-]- TOP
   und Beschluss -[BELEGT_DURCH]-> Transkriptsegment (Audio-Zeitstempel).
Ein Embedding-Index über Textchunks kann solche Aggregationen/Belege nicht zuverlässig.

Produktivpfad: NL-Frage -> LLM erzeugt Cypher (Schema im Prompt) -> Neo4j -> LLM
synthetisiert Antwort mit Zitaten. Demopfad: deterministischer Intent-Router über
denselben In-Memory-Graphen, jede Antwort mit Audio-Beleg (Timecode).
"""

from __future__ import annotations


class GraphIndex:
    def __init__(self, graph: dict):
        self.nodes = {n["id"]: n for n in graph["nodes"]}
        self.rels = graph["relationships"]
        self._out: dict[str, list[dict]] = {}
        self._in: dict[str, list[dict]] = {}
        for r in self.rels:
            self._out.setdefault(r["source_id"], []).append(r)
            self._in.setdefault(r["target_id"], []).append(r)

    def by_type(self, ntype: str) -> list[dict]:
        return [n for n in self.nodes.values() if n["type"] == ntype]

    def out(self, nid: str, rtype: str | None = None) -> list[dict]:
        return [r for r in self._out.get(nid, []) if rtype is None or r["relationship_type"] == rtype]

    def inc(self, nid: str, rtype: str | None = None) -> list[dict]:
        return [r for r in self._in.get(nid, []) if rtype is None or r["relationship_type"] == rtype]

    def provenance(self, nid: str) -> list[dict]:
        """Transkriptsegmente, die eine Aussage belegen (mit Audio-Timecode)."""
        segs = [self.nodes[r["target_id"]] for r in self.out(nid, "BELEGT_DURCH")]
        return sorted(segs, key=lambda s: s.get("start_sec", 0))


def _cite(segs: list[dict]) -> str:
    if not segs:
        return ""
    s = segs[0]
    return f'  ↳ Audiobeleg [{s.get("timecode")}] {s.get("sprecher")}: „{s.get("text","")[:110]}…"'


class GraphRAG:
    def __init__(self, graph: dict):
        self.g = GraphIndex(graph)

    # ── strukturierte Antworten (jeweils mit Provenienz) ─────────────────────

    def beschluesse(self) -> str:
        out = ["📋 Gefasste Beschlüsse:"]
        for b in self.g.by_type("Beschluss"):
            # Mehrhop: Beschluss <- Abstimmung (Ergebnis) <- TOP
            erg = ""
            for r in self.g.inc(b["id"], "FUEHRT_ZU"):
                v = self.g.nodes[r["source_id"]]
                erg = f' — Abstimmung {v["ja"]}:{v["nein"]}:{v["enthaltung"]} ({v["ergebnis"]})'
            out.append(f'• {b["label"]}: {b.get("text","")}{erg}')
            out.append(_cite(self.g.provenance(b["id"])))
        return "\n".join(x for x in out if x)

    def aufgaben(self) -> str:
        out = ["✅ Aufgaben & Fristen:"]
        for a in self.g.by_type("Aufgabe"):
            quelle = [self.g.nodes[r["source_id"]]["label"] for r in self.g.inc(a["id"], "ERZEUGT_AUFGABE")]
            out.append(f'• {a["label"]} — zuständig: {a.get("zustaendig")}, Frist: {a.get("frist")}'
                       f' (aus {", ".join(quelle)})')
        return "\n".join(out)

    def befangenheiten(self) -> str:
        out = ["⚖️  Befangenheiten:"]
        rels = [r for r in self.g.rels if r["relationship_type"] == "BEFANGEN_BEI"]
        if not rels:
            return "⚖️  Keine Befangenheiten protokolliert."
        for r in rels:
            person = self.g.nodes[r["source_id"]]["label"]
            top = self.g.nodes[r["target_id"]]["label"]
            out.append(f'• {person} ist befangen bei {top} ({r.get("rechtsgrundlage")})')
        return "\n".join(out)

    def beschlussfaehigkeit(self) -> str:
        s = next(iter(self.g.by_type("Sitzung")), None)
        if not s:
            return "Keine Sitzung im Graphen."
        norm = [self.g.nodes[r["target_id"]]["label"] for r in self.g.out(s["id"], "BESCHLUSSFAEHIG_NACH")]
        status = "beschlussfähig" if s.get("beschlussfaehig") == "True" else "NICHT beschlussfähig"
        return f'🏛️  Die Sitzung war {status}' + (f' (Rechtsgrundlage: {", ".join(norm)}).' if norm else ".")

    def abstimmung_zu(self, stichwort: str) -> str:
        """Mehrhop von einem TOP-Stichwort zur Abstimmung + Beschluss + Audiobeleg."""
        hits = [t for t in self.g.by_type("Tagesordnungspunkt") if stichwort.lower() in t["label"].lower()]
        if not hits:
            return f'Kein TOP zu „{stichwort}" gefunden.'
        out = []
        for top in hits:
            out.append(f'🗳️  {top["label"]}')
            for r in self.g.out(top["id"], "ENTSCHIEDEN_DURCH"):
                v = self.g.nodes[r["target_id"]]
                out.append(f'   Abstimmung: {v["ja"]} Ja / {v["nein"]} Nein / {v["enthaltung"]} Enthaltung'
                           f' → {v["ergebnis"]}')
            for r in self.g.out(top["id"], "ERGEBNIS_BESCHLUSS"):
                b = self.g.nodes[r["target_id"]]
                out.append(f'   {b["label"]}: {b.get("text","")}')
                out.append(_cite(self.g.provenance(b["id"])))
        return "\n".join(x for x in out if x)

    def faktencheck(self) -> str:
        """Aussagen mit Verdikt, Begründung, Quelle und Audio-Beleg."""
        checks = self.g.by_type("Faktencheck")
        if not checks:
            return "🔎 Keine prüfbaren Aussagen im Graphen."
        out = ["🔎 Faktencheck der Reden:"]
        for fc in checks:
            # Faktencheck <- Aussage (GEPRUEFT_ALS), Aussage -> Person, Aussage -> Segment
            aussage = next((self.g.nodes[r["source_id"]] for r in self.g.inc(fc["id"], "GEPRUEFT_ALS")), None)
            if not aussage:
                continue
            quelle = [self.g.nodes[r["target_id"]] for r in self.g.out(fc["id"], "BELEGT_MIT")]
            out.append(f'• [{fc["verdikt"]}] „{aussage.get("text","")}"'
                       f' — {aussage.get("person","")}')
            out.append(f'    {fc.get("begruendung","")}')
            if quelle:
                out.append(f'    Quelle: {quelle[0]["label"]} (Stand {quelle[0].get("stand","")})')
            out.append(_cite(self.g.provenance(aussage["id"])))
        return "\n".join(x for x in out if x)

    # ── einfacher Intent-Router (Demo-Ersatz für NL->Cypher via LLM) ─────────

    def ask(self, frage: str) -> str:
        q = frage.lower()
        if "faktencheck" in q or "fakten" in q or "stimmt das" in q or "geprüft" in q:
            return self.faktencheck()
        if "beschlussfähig" in q or "beschlussfaehig" in q:
            return self.beschlussfaehigkeit()
        if "befangen" in q:
            return self.befangenheiten()
        if "aufgabe" in q or "frist" in q or "auftrag" in q:
            return self.aufgaben()
        if "abstimmung" in q or "abgestimmt" in q or "bücherbus" in q or "buecherbus" in q:
            kw = "bücherbus" if "bus" in q else ("terminvergabe" if "termin" in q else "TOP")
            return self.abstimmung_zu(kw)
        if "beschl" in q or "beschlossen" in q or "gefasst" in q:
            return self.beschluesse()
        return ("Frage nicht erkannt (Demo-Router). Produktiv: NL→Cypher via LLM. "
                "Versuche: Beschlüsse? · Aufgaben/Fristen? · Befangenheiten? · "
                "War die Sitzung beschlussfähig? · Abstimmung zum Bücherbus?")
