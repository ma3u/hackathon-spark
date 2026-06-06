#!/usr/bin/env python3
"""
Ingestion-Pipeline: amtliches Bundestags-Plenarprotokoll-XML -> Graph -> Neo4j.

    python ingest_bundestag.py                      # Demo: mitgeliefertes Sample (dry-run)
    python ingest_bundestag.py --xml prot.xml       # eigene amtliche XML
    python ingest_bundestag.py --xml prot.xml --load # echt nach Neo4j laden

Für echte Sitzungsdaten (z. B. 21/81) zuerst die Quellen ziehen:
    ./scripts/fetch-session.sh 21 81
Lädt Plenarprotokoll-XML (Open Data), DIP-Metadaten und – optional – das
YouTube/Mediathek-Audio (yt-dlp) für den ASR-Pfad.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline import bundestag_xml, factcheck, graph_build, export, neo4j_loader, dashboard, accessible

HERE = Path(__file__).parent
SAMPLE_XML = HERE / "data" / "sample" / "plenarprotokoll-21-081-sample.xml"
EVIDENZ = HERE / "data" / "evidence" / "evidenz.json"
OUT = HERE / "output"
WEB = HERE / "web" / "data"


def run(xml_path: Path, *, load: bool) -> dict:
    print(f"📄 Parse amtliches Plenarprotokoll: {xml_path.name}")
    protocol = bundestag_xml.parse_plenarprotokoll(xml_path)
    m = protocol.meeting
    print(f"   {m.get('gremium')} — WP {m.get('wahlperiode')}, Sitzung {m.get('sitzung_nr')}, "
          f"{m.get('datum')}")
    print(f"   {len(protocol.redebeitraege)} Reden, {len(protocol.aussagen)} prüfbare Aussagen, "
          f"{len(protocol.kommentare)} Saalreaktionen")

    checks = factcheck.factcheck_rule_based(protocol.aussagen, EVIDENZ) if protocol.aussagen else []
    sid = f"sitzung_bt_{m.get('wahlperiode','x')}_{m.get('sitzung_nr','x')}"
    graph = graph_build.build_graph(protocol, audio_file=xml_path.name, sitzung_id=sid,
                                    factchecks=checks)

    OUT.mkdir(parents=True, exist_ok=True)
    WEB.mkdir(parents=True, exist_ok=True)
    export.write_json(graph, OUT / "bundestag_xml_graph_data.json")
    export.write_json(graph, WEB / "bundestag_xml.json")
    export.write_csv(graph, OUT / "bundestag_xml_nodes.csv", OUT / "bundestag_xml_relationships.csv")
    export.write_cypher(graph, OUT / "bundestag_xml_neo4j_import.cypher")
    export.write_json(dashboard.compute_dashboard(protocol, checks), WEB / "bundestag_xml_dashboard.json")
    (WEB / "bundestag_xml_barrierefrei.txt").write_text(accessible.summarize(protocol, checks), encoding="utf-8")
    print(f"   📦 {graph['metadata']['node_count']} Knoten, "
          f"{graph['metadata']['relationship_count']} Beziehungen → output/ + web/data/")
    print(f"   📊 Dashboard + ♿ barrierefreie Fassung → web/data/")

    print("🗄️  Neo4j-Import:")
    neo4j_loader.load_graph(graph, dry_run=not load)
    return graph


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Bundestag-Plenarprotokoll → Neo4j")
    ap.add_argument("--xml", type=Path, default=SAMPLE_XML, help="Plenarprotokoll-XML")
    ap.add_argument("--load", action="store_true", help="echt nach Neo4j laden (sonst dry-run)")
    args = ap.parse_args()
    run(args.xml, load=args.load)
