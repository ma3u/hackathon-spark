# Test: heutiges Protokoll ↔ YouTube-Video — Lücken identifizieren

Können wir **selbst** einen belastbaren Soll-Ist-Vergleich fahren? **Ja.** Das
amtliche Plenarprotokoll ist der **Goldstandard**; das öffentliche Video liefert
über ASR die zu prüfende Hypothese. `pipeline/gap_analysis.py` quantifiziert die
Lücken — heute schon auf einem simulierten Beispiel reproduzierbar, ohne echtes
Video.

## Aufbau

```
amtliches XML (Goldstandard) ─┐
                              ├─► gap_analysis ─► Report (WER, Recall, Lücken)
YouTube-Video ─► Whisper-ASR ─┘
```

## Metriken

| Metrik | Misst | Lücke, wenn … |
| ------ | ----- | ------------- |
| **WER** (S/I/D) | Texttreue ASR vs. Protokoll | > 10–20 % → Nachbearbeitung nötig |
| **Reaktions-Recall** | Anteil amtlicher `<kommentar>` (Beifall/Zuruf), den ASR erfasst | reines ASR = 0 % → Sound-Event-Detection nötig |
| **Sprecher-Abdeckung** | Diarisierung vs. Rednerliste | fehlende/verwechselte Sprecher |
| **Inhalts-Lücken** | Protokollsätze ohne ASR-Entsprechung | Auslassungen / Korrekturen der Redner |

## Selbsttest (jetzt lauffähig)

```bash
python compare_protocol_video.py          # simuliertes ASR aus dem amtlichen XML
```

Beispiel-Ausgabe (mitgeliefertes Sample 21/81):

```
WER: 16.9%  (S 1 / I 0 / D 12, 77 Ref-Wörter)
Saalreaktionen: 0/5 erkannt (Recall 0%) — reines ASR erfasst sie nicht → SED nötig
Sprecher fehlend im ASR: ['Jonas Reuter']
Inhalts-Lücke: „Mein Eindruck ist, dass über 40 Prozent der Ladesäulen … defekt …"
```

→ **Identifizierte Lücken**: (1) Zahlendreher/Substitutionen, (2) **keine**
Saalreaktionen ohne SED, (3) Diarisierungsfehler, (4) ausgelassene Passagen.

## Mit echten Daten (81. Sitzung)

```bash
# 1) Quellen ziehen (auf deiner Maschine; Sandbox hat keinen Zugang):
./scripts/fetch-session.sh 21 81 <XML-URL aus Open Data> <YouTube-Sitzungs-URL>

# 2) ASR aus dem Video erzeugen (Whisper):
python run_demo.py --audio data/incoming/21-081/21081.mp3   # liefert Transkript
#    Transkript als asr.json {text, speakers, sed_erkannt} ablegen

# 3) Gap-Report:
python compare_protocol_video.py --xml data/incoming/21-081/21081.xml --asr asr.json
```

## Erwartete Erkenntnisse (Hypothesen, im Test zu prüfen)

1. **Texttreue** ist mit Whisper large-v3 hoch, fällt aber bei Eigennamen,
   Drucksachennummern, Dialekt und Schnellsprechern ab.
2. **Saalreaktionen** sind die größte strukturelle Lücke von reinem ASR →
   Sound-Event-Detection (PANNs/YAMNet) ist der Hebel.
3. **Korrekturrecht**: Abweichungen sind nicht zwingend ASR-Fehler, sondern
   nachträgliche Redaktion — als Diff modellieren, nicht als „falsch".
4. **Diarisierung** ist bei Zwischenrufen/Überlappung der zweite Schwachpunkt.

Diese vier Punkte sind zugleich die Diskussionsgrundlage mit den Bundestags-
Kolleg:innen (siehe `docs/fragen-bundestag.md`).
