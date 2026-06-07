# data/real — echte amtliche Quelldaten

Im Gegensatz zu `data/sample/` (frei erfunden) liegen hier **echte** Daten.

## `plenarprotokoll-20-214.xml`

Amtliches **Plenarprotokoll** des Deutschen Bundestags, **WP 20, 214. Sitzung,
18.03.2025** (DTD `dbtplenarprotokoll`).

- **Quelle:** Bundestag Open Data — `https://www.bundestag.de/resource/blob/1057624/20214.xml`
  (gefunden über die Plenarprotokoll-Liste, siehe `docs/spark-und-echtdaten.md` Teil C).
- **Lizenz/Recht:** Amtliche Werke sind nach **§ 5 UrhG gemeinfrei** — Nutzung unbedenklich.
- **Verarbeitung:**
  ```bash
  python3 ingest_bundestag.py --xml data/real/plenarprotokoll-20-214.xml \
      --name bundestag_real --no-factcheck
  ```
  Ergibt `web/data/bundestag_real{,_dashboard.json,_barrierefrei.txt}` (Szenario
  „Bundestag (echt)" im Pages-UI): 4 TOPs, 45 gesprochene Reden + 38 schriftliche
  Beiträge (Anlagen, `herkunft="anlage"`), 643 amtliche Saalreaktionen. Die TOP-Titel
  stammen aus dem `<inhaltsverzeichnis>`; schriftliche Beiträge zählen nicht zum Sprachanteil.

> **`--no-factcheck` ist Absicht.** Über reale, namentlich genannte Personen werden
> **keine** automatischen Faktencheck-Verdikte erzeugt/veröffentlicht (Persönlichkeitsrecht;
> der Demo-Checker prüft nur gegen den fiktiven `data/evidence/evidenz.json` und ist dafür
> sachlich nicht belastbar). Der Faktencheck-Mechanismus wird weiterhin am **fiktiven**
> Szenario `bundestag` gezeigt. Details: `docs/spark-und-echtdaten.md` Teil D.
