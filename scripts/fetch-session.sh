#!/usr/bin/env bash
set -euo pipefail

# Lädt die offiziellen Quellen einer Bundestagssitzung für die Ingestion.
#   ./scripts/fetch-session.sh <wahlperiode> <sitzung-nr> [xml-url] [youtube-url]
# Beispiel (81. Sitzung der laufenden, letzten Wahlperiode 21):
#   ./scripts/fetch-session.sh 21 81        # oder: ./scripts/fetch-session.sh "" 81
#
# Hinweis: Aus der Claude-Sandbox sind bundestag.de/dip/YouTube gesperrt — dieses
# Skript läuft auf DEINER Maschine mit normalem Internetzugang.

WP="${1:-21}"   # letzte/laufende Wahlperiode als Default
NR="${2:?Sitzungsnummer fehlt, z. B. 81}"
XML_URL="${3:-}"
YT_URL="${4:-}"
OUT="data/incoming/${WP}-$(printf '%03d' "$NR")"
mkdir -p "$OUT"
PAD=$(printf '%03d' "$NR")

echo "── Bekannte Einstiegspunkte (WP ${WP}, Sitzung ${NR}) ─────────────────"
echo "  Open Data:     https://www.bundestag.de/services/opendata"
echo "  Protokolle:    https://www.bundestag.de/dokumente/protokolle/plenarprotokolle"
echo "  DIP-Deeplink:  https://dip.bundestag.de/  (Plenarprotokoll ${WP}/${NR})"
echo "  Tagesordnung:  https://www.bundestag.de/parlament/plenum/tagesordnungen"
echo "  YouTube-Kanal: https://www.youtube.com/@bundestag"
echo "  XML-Konvention: ${WP}${PAD}.xml  (Blob-ID nicht ableitbar → Resolver nutzen)"
echo "  Datum/Fundstelle auflösen:  DIP_API_KEY=… python scripts/resolve-session.py ${WP} ${NR}"
echo

echo "── 1) Plenarprotokoll-XML (Bundestag Open Data) ───────────────────────"
if [ -n "$XML_URL" ]; then
  curl -fSL -o "$OUT/${WP}${PAD}.xml" "$XML_URL" && echo "  ✓ $OUT/${WP}${PAD}.xml"
else
  echo "  Keine XML-URL übergeben. So findest du sie:"
  echo "    1. python scripts/resolve-session.py ${WP} ${NR}   (Datum + Fundstelle)"
  echo "    2. Open Data → 'Plenarprotokolle' → ${WP}${PAD}.xml → Link kopieren"
  echo "    3. ./scripts/fetch-session.sh ${WP} ${NR} <XML-URL>"
fi

echo "── 2) DIP-API: Metadaten + Volltext (API-Key nötig) ───────────────────"
if [ -n "${DIP_API_KEY:-}" ]; then
  base="https://search.dip.bundestag.de/api/v1"
  curl -fsS "${base}/plenarprotokoll?f.wahlperiode=${WP}&f.dokumentnummer=${WP}/${NR}&apikey=${DIP_API_KEY}" \
    -o "$OUT/dip-metadata.json" && echo "  ✓ $OUT/dip-metadata.json"
  curl -fsS "${base}/plenarprotokoll-text?f.wahlperiode=${WP}&f.dokumentnummer=${WP}/${NR}&apikey=${DIP_API_KEY}" \
    -o "$OUT/dip-volltext.json" && echo "  ✓ $OUT/dip-volltext.json"
else
  echo "  DIP_API_KEY nicht gesetzt. Öffentlichen Key holen:"
  echo "    https://dip.bundestag.de/über-dip/hilfe/api  →  export DIP_API_KEY=..."
fi

echo "── 3) Video: Audio + UNTERTITEL (YouTube-Kanal des Bundestages, letzte WP) ──"
# Offizieller Kanal der laufenden Wahlperiode: https://www.youtube.com/@bundestag
if command -v yt-dlp >/dev/null 2>&1; then
  url="${YT_URL:-https://www.youtube.com/@bundestag/videos}"
  echo "  Quelle: $url"
  # (a) Untertitel = fertige Transkription (oft schneller/genauer als eigenes ASR)
  yt-dlp --write-subs --write-auto-subs --sub-langs "de.*" --convert-subs vtt \
         --skip-download -o "$OUT/${WP}${PAD}.%(ext)s" "$url" \
    && echo "  ✓ Untertitel (.vtt) in $OUT/  → python ingest-from-subs nutzt sie direkt" \
    || echo "  ⚠ Keine Untertitel gefunden — dann Audio-Pfad (b)."
  # (b) Audiospur für eigenes ASR (Whisper), falls keine Untertitel
  yt-dlp -x --audio-format mp3 -o "$OUT/${WP}${PAD}.%(ext)s" "$url" \
    && echo "  ✓ Audio (.mp3) in $OUT/" \
    || echo "  ⚠ Audio-Download fehlgeschlagen — konkrete Sitzungs-URL als 4. Argument übergeben."
else
  echo "  yt-dlp nicht installiert (pip install yt-dlp). Offizieller Kanal:"
  echo "    https://www.youtube.com/@bundestag  ·  Mediathek: https://www.bundestag.de/mediathek"
fi

echo
echo "Fertig. Weiter mit:"
echo "  # Variante 1: amtliches XML → Graph → Neo4j"
echo "  python ingest_bundestag.py --xml $OUT/${WP}${PAD}.xml --load"
echo "  # Variante 2: Transkription aus den Video-Untertiteln"
echo "  python -c \"from pipeline import subtitles,json; print(json.dumps(subtitles.to_diarized('$OUT/${WP}${PAD}.de.vtt')))\" > $OUT/diarized.json"
echo "  # Variante 3: eigenes ASR aus dem Audio (Whisper) + Sound-Event-Detection"
echo "  python run_demo.py --audio $OUT/${WP}${PAD}.mp3"
