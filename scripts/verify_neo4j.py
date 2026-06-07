#!/usr/bin/env python3
"""
Automatische Prüfung der echten Sitzungen im Neo4j-Graphen.

Drei reale Szenarien, die zeigen, dass die Pipeline echte Bundestagssitzungen
korrekt UND sitzungsübergreifend abfragbar macht:

  1) Vollständigkeit & Provenienz   — jede Sitzung vollständig geladen; jeder
     Redebeitrag ist bis zum Quell-Segment belegt; KEINE Verdikte über reale Personen.
  2) Saalreaktions-Analyse          — Beifall/Zwischenrufe je Typ und je Fraktion
     über alle Sitzungen (das, was Stenografen als „(Beifall bei …)" festhalten).
  3) Sitzungsübergreifende Personen — welche Abgeordneten in allen geladenen
     Sitzungen sprachen (beweist die geteilten Person-Knoten).

Exit-Code 0 = alle Prüfungen bestanden, sonst 1.

  NEO4J_URI=bolt://localhost:7688 python scripts/verify_neo4j.py
"""

from __future__ import annotations

import os
import sys

from neo4j import GraphDatabase

URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
USER = os.environ.get("NEO4J_USER", "neo4j")
PW = os.environ.get("NEO4J_PASSWORD", "healthdataspace")

_checks: list[tuple[bool, str]] = []


def check(ok: bool, msg: str) -> None:
    _checks.append((ok, msg))
    print(f"  {'✅' if ok else '❌'} {msg}")


def rows(session, cypher, **kw):
    return [r.data() for r in session.run(cypher, **kw)]


def main() -> int:
    drv = GraphDatabase.driver(URI, auth=(USER, PW))
    with drv.session() as s:
        sitzungen = rows(s, "MATCH (x:Sitzung) RETURN x.sitzung_nr AS nr, x.datum AS datum "
                            "ORDER BY nr")
        total = s.run("MATCH (n) RETURN count(n) AS c").single()["c"]
        print(f"Neo4j: {URI}  ·  {len(sitzungen)} Sitzungen  ·  {total} Knoten gesamt\n")

        # ── Szenario 1: Vollständigkeit & Provenienz ──────────────────────────
        print("Szenario 1 — Vollständigkeit & Provenienz")
        per = rows(s, """
            MATCH (x:Sitzung)-[:HAT_TOP]->(t:Tagesordnungspunkt)
            OPTIONAL MATCH (t)<-[:ZU_TOP]-(r:Redebeitrag)
            OPTIONAL MATCH (t)-[:HAT_REAKTION]->(e:AkustischesEreignis)
            RETURN x.sitzung_nr AS nr, x.datum AS datum,
                   count(DISTINCT t) AS tops, count(DISTINCT r) AS reden,
                   count(DISTINCT e) AS reaktionen ORDER BY nr""")
        for r in per:
            print(f"     Sitzung {r['nr']} ({r['datum']}): {r['tops']} TOPs, "
                  f"{r['reden']} Reden, {r['reaktionen']} Saalreaktionen")
        check(len(sitzungen) >= 3, f"mindestens 3 echte Sitzungen geladen ({len(sitzungen)})")
        check(all(r["tops"] > 0 and r["reden"] > 0 for r in per),
              "jede Sitzung hat TOPs und Redebeiträge")
        ohne_beleg = s.run("MATCH (r:Redebeitrag) WHERE NOT (r)-[:BELEGT_DURCH]->(:Transkriptsegment) "
                           "RETURN count(r) AS c").single()["c"]
        check(ohne_beleg == 0, f"jeder Redebeitrag ist per BELEGT_DURCH belegt (ohne Beleg: {ohne_beleg})")
        # ohne festes Label, damit Neo4j nicht "label does not exist" warnt (genau das ist gewollt)
        verdikte = s.run("MATCH (f) WHERE 'Faktencheck' IN labels(f) RETURN count(f) AS c").single()["c"]
        check(verdikte == 0, f"keine automatischen Faktencheck-Verdikte über reale Personen ({verdikte})")
        seg = s.run("MATCH (n:Transkriptsegment) RETURN count(n) AS c").single()["c"]
        check(seg > 0, f"Provenienz-Segmente vorhanden ({seg})")

        # ── Szenario 2: Saalreaktions-Analyse ─────────────────────────────────
        print("\nSzenario 2 — Saalreaktionen (über alle Sitzungen)")
        by_typ = rows(s, "MATCH (e:AkustischesEreignis) RETURN e.subtype AS typ, count(*) AS n "
                         "ORDER BY n DESC")
        print("     nach Typ: " + ", ".join(f"{r['typ']} {r['n']}" for r in by_typ))
        beifall = rows(s, "MATCH (e:AkustischesEreignis) WHERE e.subtype='Beifall' AND e.urheber<>'' "
                          "RETURN e.urheber AS fraktion, count(*) AS n ORDER BY n DESC LIMIT 8")
        for r in beifall:
            print(f"     Beifall von {r['fraktion']}: {r['n']}")
        check(sum(r["n"] for r in by_typ) > 0, "Saalreaktionen wurden extrahiert und sind abfragbar")
        check(len(beifall) > 0, "Beifall ist einer gebenden Fraktion zugeordnet")

        # ── Szenario 3: Sitzungsübergreifende Personenverfolgung ──────────────
        print("\nSzenario 3 — Abgeordnete, die in ALLEN geladenen Sitzungen sprachen")
        n_sess = len(sitzungen)
        cross = rows(s, """
            MATCH (p:Person)-[:HAT_REDEBEITRAG]->(:Redebeitrag)-[:ZU_TOP]->
                  (:Tagesordnungspunkt)<-[:HAT_TOP]-(x:Sitzung)
            WITH p, count(DISTINCT x) AS sitzungen, count(*) AS reden
            WHERE sitzungen >= $n RETURN p.label AS person, sitzungen, reden
            ORDER BY reden DESC LIMIT 12""", n=n_sess)
        for r in cross:
            print(f"     {r['person']}: {r['reden']} Reden in {r['sitzungen']} Sitzungen")
        check(len(cross) > 0, f"Personen sprechen sitzungsübergreifend (geteilte Person-Knoten, {len(cross)})")
        shared = s.run("MATCH (p:Person) RETURN count(p) AS c").single()["c"]
        print(f"     (insgesamt {shared} eindeutige Personen über alle Sitzungen)")

    drv.close()
    passed = sum(1 for ok, _ in _checks if ok)
    print(f"\n{'='*60}\nErgebnis: {passed}/{len(_checks)} Prüfungen bestanden.")
    return 0 if passed == len(_checks) else 1


if __name__ == "__main__":
    sys.exit(main())
