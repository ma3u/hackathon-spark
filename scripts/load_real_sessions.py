#!/usr/bin/env python3
"""
Lädt mehrere ECHTE Plenarprotokolle **vollständig** und **kollisionsfrei** in EIN
lokales Neo4j — die Grundlage, um reale Sitzungen automatisiert abzufragen/zu prüfen.

  • Jede Sitzung wird vollständig geparst (Reden, Saalreaktionen, schriftliche Anlagen,
    Provenienz-Segmente) und über `namespace_graph` sitzungs-eindeutig gemacht.
  • Personen/Fraktionen/Normen/Quellen bleiben GLOBAL → sitzungsübergreifende Abfragen.
  • Faktencheck ist AUS — keine automatischen Verdikte über reale, namentliche Personen.

Lokal entwickeln (eigenes, isoliertes Neo4j auf Port 7688):
  NEO4J_HTTP_PORT=7475 NEO4J_BOLT_PORT=7688 docker compose -f docker-compose.neo4j.yml up -d
  NEO4J_URI=bolt://localhost:7688 python scripts/load_real_sessions.py
  NEO4J_URI=bolt://localhost:7688 python scripts/load_real_sessions.py --dry-run
  python scripts/load_real_sessions.py data/real/plenarprotokoll-21-081.xml   # gezielt
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from pipeline import bundestag_xml, graph_build, neo4j_loader  # noqa: E402

DEFAULT_XMLS = sorted((REPO / "data" / "real").glob("plenarprotokoll-21-*.xml"))


def load(xmls: list[Path], *, dry_run: bool = False) -> dict:
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    print(f"Neo4j: {uri}  ·  Faktencheck: AUS (keine Verdikte über reale Personen)\n")
    total = {"nodes": 0, "relationships": 0, "sessions": 0}
    for xml in xmls:
        p = bundestag_xml.parse_plenarprotokoll(xml)
        m = p.meeting
        sid = f"sitzung_bt_{m.get('wahlperiode', 'x')}_{m.get('sitzung_nr', 'x')}"
        # factchecks=None ⇒ keine Faktencheck-/Quelle-Knoten über reale Personen.
        graph = graph_build.build_graph(p, audio_file=xml.name, sitzung_id=sid, factchecks=None)
        graph = neo4j_loader.namespace_graph(graph, sid)
        spoken = sum(1 for r in p.redebeitraege if not r.get("schriftlich"))
        schr = sum(1 for r in p.redebeitraege if r.get("schriftlich"))
        print(f"▶ {sid}  ({m.get('datum')}): {len(p.tops)} TOPs, {spoken} Reden + {schr} schriftl., "
              f"{len(p.kommentare)} Saalreaktionen")
        res = neo4j_loader.load_graph(graph, dry_run=dry_run)
        print(f"   {'[dry-run] ' if dry_run else '✓ '}{res['nodes']} Knoten, "
              f"{res['relationships']} Beziehungen\n")
        total["nodes"] += res["nodes"]
        total["relationships"] += res["relationships"]
        total["sessions"] += 1
    print(f"Σ {total['sessions']} Sitzungen · {total['nodes']} Knoten · "
          f"{total['relationships']} Beziehungen "
          f"{'(dry-run, nichts geschrieben)' if dry_run else 'in Neo4j'}.")
    return total


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    args = [Path(a) for a in sys.argv[1:] if not a.startswith("--")]
    xmls = args or DEFAULT_XMLS
    if not xmls:
        sys.exit("Keine Plenarprotokoll-XML gefunden (data/real/plenarprotokoll-21-*.xml).")
    load(xmls, dry_run=dry)
