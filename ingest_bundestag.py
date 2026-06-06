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


def run(xml_path: Path, *, load: bool, name: str = "bundestag_xml",
        factcheck_on: bool = True) -> dict:
    print(f"📄 Parse amtliches Plenarprotokoll: {xml_path.name}")
    protocol = bundestag_xml.parse_plenarprotokoll(xml_path)
    m = protocol.meeting
    print(f"   {m.get('gremium')} — WP {m.get('wahlperiode')}, Sitzung {m.get('sitzung_nr')}, "
          f"{m.get('datum')}")
    print(f"   {len(protocol.redebeitraege)} Reden, {len(protocol.aussagen)} prüfbare Aussagen, "
          f"{len(protocol.kommentare)} Saalreaktionen, {len(protocol.tops)} TOPs")

    # Faktencheck nur auf dem fiktiven Demo-Korpus: bei ECHTEN Sitzungen abschaltbar, damit
    # keine automatischen Verdikte über reale, namentlich genannte Personen veröffentlicht
    # werden (Persönlichkeitsrecht; der Demo-Checker ist dafür sachlich nicht belastbar).
    checks = factcheck.factcheck_rule_based(protocol.aussagen, EVIDENZ) \
        if (factcheck_on and protocol.aussagen) else []
    sid = f"sitzung_bt_{m.get('wahlperiode','x')}_{m.get('sitzung_nr','x')}"
    graph = graph_build.build_graph(protocol, audio_file=xml_path.name, sitzung_id=sid,
                                    factchecks=checks)

    OUT.mkdir(parents=True, exist_ok=True)
    WEB.mkdir(parents=True, exist_ok=True)
    export.write_json(graph, OUT / f"{name}_graph_data.json")
    export.write_json(graph, WEB / f"{name}.json")
    export.write_csv(graph, OUT / f"{name}_nodes.csv", OUT / f"{name}_relationships.csv")
    export.write_cypher(graph, OUT / f"{name}_neo4j_import.cypher")
    export.write_json(dashboard.compute_dashboard(protocol, checks), WEB / f"{name}_dashboard.json")
    (WEB / f"{name}_barrierefrei.txt").write_text(accessible.summarize(protocol, checks), encoding="utf-8")
    print(f"   📦 {graph['metadata']['node_count']} Knoten, "
          f"{graph['metadata']['relationship_count']} Beziehungen → output/ + web/data/ ({name})")
    print(f"   📊 Dashboard + ♿ barrierefreie Fassung → web/data/")
    if not factcheck_on:
        print("   ⚠️  Faktencheck deaktiviert — keine automatischen Verdikte über reale Personen.")

    print("🗄️  Neo4j-Import:")
    neo4j_loader.load_graph(graph, dry_run=not load)
    return graph


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Bundestag-Plenarprotokoll → Neo4j")
    ap.add_argument("--xml", type=Path, default=SAMPLE_XML, help="Plenarprotokoll-XML")
    ap.add_argument("--load", action="store_true", help="echt nach Neo4j laden (sonst dry-run)")
    ap.add_argument("--name", default="bundestag_xml",
                    help="Ausgabename/Szenario in web/data (z. B. bundestag_real)")
    ap.add_argument("--no-factcheck", action="store_true",
                    help="Faktencheck überspringen (echte Sitzung: keine Verdikte über reale Personen)")
    args = ap.parse_args()
    run(args.xml, load=args.load, name=args.name, factcheck_on=not args.no_factcheck)
