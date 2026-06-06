#!/usr/bin/env python3
"""
Löst eine Bundestagssitzung über die DIP-API auf: Datum + Fundstellen (PDF/XML).

    DIP_API_KEY=… python scripts/resolve-session.py 21 81

Gibt das Sitzungsdatum, die DIP-Fundstelle (PDF) und die zu erwartende
Open-Data-XML (Dateiname-Konvention `WP+NNN.xml`, z. B. 21081.xml) aus.
Läuft auf deiner Maschine (die Sandbox hat keinen Netzzugang zu dip.bundestag.de).

DIP-API-Key (öffentlich, rate-limitiert): https://dip.bundestag.de/über-dip/hilfe/api
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request

DIP = "https://search.dip.bundestag.de/api/v1"


def main() -> int:
    if len(sys.argv) < 3:
        print("Aufruf: DIP_API_KEY=… python scripts/resolve-session.py <wp> <nr>")
        return 2
    wp, nr = sys.argv[1], sys.argv[2]
    key = os.environ.get("DIP_API_KEY")
    if not key:
        print("DIP_API_KEY nicht gesetzt — Key: https://dip.bundestag.de/über-dip/hilfe/api")
        return 2

    q = urllib.parse.urlencode({
        "f.wahlperiode": wp, "f.dokumentnummer": f"{wp}/{nr}",
        "format": "json", "apikey": key})
    url = f"{DIP}/plenarprotokoll?{q}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            data = json.load(r)
    except Exception as e:  # noqa: BLE001
        print(f"DIP-Abfrage fehlgeschlagen: {e}")
        return 1

    docs = data.get("documents", [])
    if not docs:
        print(f"Keine Sitzung {wp}/{nr} in DIP gefunden.")
        return 1
    d = docs[0]
    datum = d.get("datum", "?")
    fund = d.get("fundstelle", {}) or {}
    pdf = fund.get("pdf_url", "—")
    pad = f"{int(nr):03d}"

    print(f"Sitzung {wp}/{nr}")
    print(f"  Datum:           {datum}")
    print(f"  Titel:           {d.get('titel','')}")
    print(f"  PDF (DIP):       {pdf}")
    print(f"  XML (Open Data): Dateiname {wp}{pad}.xml  —  Link von")
    print(f"                   https://www.bundestag.de/services/opendata (Bereich Plenarprotokolle)")
    print()
    print("Weiter:")
    print(f"  ./scripts/fetch-session.sh {wp} {nr} <XML-URL aus Open Data> "
          f"\"https://www.youtube.com/@bundestag/search?query={datum}\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
