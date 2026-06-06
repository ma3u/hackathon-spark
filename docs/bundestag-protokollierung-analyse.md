# Bundestag: Protokollierung, parlamentarische Fragen & Faktencheck

Analyse der Herausforderungen und wie `graph-protokoll` sie adressiert.
Bezug: SPARK-Hackathon Challenge 2 „Da geht noch mehr!" — Übertragung der
KI-Module auf eine neue Verwaltungs-/Parlamentsleistung jenseits von Planung
und Genehmigung.

---

## 1. Wie der Bundestag heute protokolliert

Jede Plenarsitzung wird wörtlich mitgeschrieben und als **Plenarprotokoll
(Stenografischer Bericht)** veröffentlicht — seit 1949 lückenlos, jedes
gesprochene Wort. Die Protokolle erscheinen i. d. R. am Folgewerktag als
**PDF und XML**; zusammen mit den **Drucksachen** (u. a. Anträge, Kleine/Große
Anfragen, Antworten der Bundesregierung) sind sie als **Open Data** (XML/JSON)
sowie über die **DIP-API** maschinenlesbar abrufbar.

**Das ist Gold für einen Knowledge Graph** — aber drei Lücken bleiben:

| Lücke | Heute | Mit `graph-protokoll` |
| ----- | ----- | --------------------- |
| **Vom Audio zum Text** | manuelle Stenografie, Veröffentlichung am Folgetag | ASR + Diarisierung liefern einen Rohentwurf in (nahezu) Echtzeit |
| **Vom Text zur Struktur** | Protokoll ist Fließtext (PDF/XML) | Extraktion von Reden, Aussagen, Anträgen, Abstimmungen, Fragen → Graph |
| **Von der Aussage zum Beleg** | keine Verknüpfung Aussage ↔ Quelle | Faktencheck-Kante Aussage → Verdikt → Quelle, plus Audio-Zeitstempel |

> `graph-protokoll` will die amtliche Stenografie **nicht ersetzen**, sondern
> einen **strukturierten, prüfbaren Zwischenlayer** liefern: schneller
> durchsuchbar, verknüpfbar, faktenprüfbar — mit Mensch-im-Loop für die
> rechtsverbindliche Endfassung.

## 2. Herausforderungen der Protokollierung (und die Antworten im Prototyp)

1. **Sprecheridentifikation.** Diarisierung liefert nur anonyme Labels.
   Im Plenum hilft die **Rednerliste/das Präsidium** als Enrollment-Quelle
   (`speaker_map`). Zwischenrufe sind das schwierige Long-Tail-Problem (kurze,
   überlappende Segmente) → bewusst als offener Punkt markiert.
2. **Fachsprache & Eigennamen.** Drucksachennummern, Paragrafen, Gremien.
   → Whisper mit Domänen-Prompt/Glossar; Normbezüge als eigene `Norm`-Knoten.
3. **Rechtsverbindlichkeit.** Ein KI-Protokoll ist nur dann nutzbar, wenn jede
   Aussage **zur Sekunde im Audio belegbar** ist → `BELEGT_DURCH`-Provenienz.
4. **Datenschutz/Hoheit.** On-prem-Betrieb (Whisper + pyannote + lokales LLM);
   Stimmprofile sind biometrische Daten (Art. 9 DSGVO).

## 3. Parlamentarische Fragen als eigener Graph-Zweig

„Die Fragen an den Bundestag" sind formalisierte Instrumente — und ideal für
einen Graphen, weil sie **Frage → Antwort → Frist → Zuständigkeit** verknüpfen:

| Instrument | Charakter | Modellierung im Graph |
| ---------- | --------- | --------------------- |
| **Kleine Anfrage** | schriftlich, Fraktion → Bundesregierung | `Frage → Antwort (Drucksache) → Frist` |
| **Große Anfrage** | mit Plenardebatte | `Frage → Aussprache (TOP) → Reden` |
| **Fragestunde / mündliche Frage** | im Plenum | `Frage → mündliche Antwort (Audio-Segment)` |
| **Schriftliche Einzelfrage** | Abgeordnete:r → Regierung | `Frage → Antwort → Frist` |

Im Demo-Szenario fragt eine (fiktive) Abgeordnete nach einem Ausbauplan; die
Bundesregierung **sagt eine schriftliche Vorlage bis zum 30. Juni 2026 zu** —
abgebildet als `Frage`-Knoten plus `Aufgabe` mit `Frist` und Zuständigkeit
(`Bundesregierung`). So wird **Nachhalten von Zusagen** maschinell möglich
(„Welche Antwortfristen laufen diese Woche ab?").

## 4. Faktencheck — Konzept, Verdikte, Grenzen

Politische Reden enthalten **quantitative Behauptungen**, die gegen amtliche
Quellen geprüft werden müssen. Der Prototyp macht das in vier Schritten:

```
Aussage erkennen → Evidenz finden → verifizieren → Verdikt + Quelle anhängen
   (extract)        (retrieval)       (NLI/LLM)      (Graph: GEPRUEFT_ALS→Quelle)
```

**Verdikt-Skala:** `bestätigt` · `teilweise` · `irreführend` · `falsch` ·
`unbelegt`. **Grundsatz: jeder Faktencheck trägt IMMER eine Quelle.** Auch ein
`unbelegt` verweist nachvollziehbar auf den **geprüften Korpus** (mit Stand) —
„unbelegt" heißt „gegen Quelle X bis Datum Y nicht belegbar", nicht „keine
Prüfung". Im Code ist das als Invariante abgesichert (`assert` in
`factcheck.py`); im Graph entsteht zu jedem `Faktencheck` zwingend
`–BELEGT_MIT→ Quelle`. Zusätzlich trägt jede Aussage über `BELEGT_DURCH` den
**Audio-Zeitstempel** der Originalrede (Primärbeleg).

**Demo-Ergebnis (fiktive Debatte):**

| Aussage | Verdikt |
| ------- | ------- |
| „über 150.000 öffentliche Ladepunkte" | 🟠 irreführend (belegt: ~121.000) |
| „drei von vier Ladevorgänge zu Hause" | ✅ bestätigt |
| „seit 2021 nicht erhöht" | ❌ falsch (mehr als verdoppelt) |
| „über 40 % der Ladesäulen defekt" | ⚪ unbelegt (keine Quelle) |

**Architektur produktiv (`pipeline/factcheck.py`):** Dense Retrieval über einen
Korpus amtlicher Quellen (Destatis, Antworten der Bundesregierung, Drucksachen
via DIP-API), dann LLM-Verifizierer im **NLI-Stil** (entailment / contradiction
/ neutral) mit **Zitatpflicht**.

**Bewusste Grenzen (Hackathon-ehrlich):**
- **Meinung ≠ Faktum.** Nur quantifizierbare Tatsachenbehauptungen werden
  geprüft; Wertungen bleiben außen vor.
- **Neutralität & Anfechtbarkeit.** Ein automatisches Verdikt ist ein
  **Vorschlag mit Quelle**, kein Urteil — immer mit Mensch-im-Loop und
  Widerspruchspfad.
- **„unbelegt" ≠ „falsch".** Fehlende Evidenz wird klar getrennt von Widerlegung.
- **Aktualität der Evidenz.** Quellen tragen einen `stand`; veraltete Belege
  werden gekennzeichnet.

## 5. Was das für die SPARK-Module heißt

`graph-protokoll` zeigt, dass der SPARK-Baukasten (Dokument-/Sprachverarbeitung
+ Knowledge Graph + GraphRAG) sich von Planungs-/Genehmigungsakten auf
**Gremien- und Parlamentsprotokolle** übertragen lässt — mit zwei neuen,
generisch nützlichen Bausteinen: **ASR-Eingabe** (statt nur TTS-Ausgabe) und
**Faktencheck mit Quellen-Provenienz**.

## 6. Wie wird heute protokolliert? (Bundestag, Status quo)

Pro Sitzungstag sind **16 Parlamentsstenografinnen/-stenografen** im Einsatz,
Ablösung alle **fünf Minuten**. Im Anschluss übertragen sie ihre Kurzschrift
mit einer Schreibkraft in Volltext; Unklares wird recherchiert. Sie erfassen
bis zu **500 Silben/Minute** — und **nicht nur Reden, sondern auch jeden
Zwischenruf, jede Zwischenfrage und Beifall**. Protokolle entstehen
stenografisch oder, „inzwischen teilweise üblich", **mit automatischer
Spracherkennung**. Rednerinnen/Redner haben ein **Korrekturrecht** vor
Veröffentlichung (Korrekturen dürfen den Sinn nicht ändern). Ein **vorläufiges**
Protokoll erscheint am Sitzungstag, das **endgültige** am Folgewerktag als
PDF/XML. → `graph-protokoll` setzt genau am ASR-/Strukturierungsschritt an und
liefert zusätzlich Faktencheck + Graph + Provenienz.

## 7. Automatische Transkription — wie genau?

```
Audio → VAD → ASR (Wörter+Zeit) → Diarisierung → Alignment → Sprecher-Utterances
```

| Baustein | Empfohlenes Tool | Hinweis |
| -------- | ---------------- | ------- |
| ASR | **faster-whisper** large-v3 (CTranslate2) / **WhisperX** | `language=de`, Wort-Zeitstempel, VAD; Domänen-Prompt/Glossar für Drucksachen-Nrn., Paragrafen, Eigennamen |
| Diarisierung | **pyannote** speaker-diarization-3.1 | anonyme Labels → Personen via **Rednerliste/Präsidium** (Enrollment) |
| Alignment | **WhisperX** | Wort↔Sprecher per Zeitüberlappung |
| Deutsch-Feintuning | Whisper-de-Fine-Tunes | senkt WER bei Dialekt/Schnellsprechern |

## 8. Multimodal: Buhrufe/Jubel, Lautstärke, Lippenlesen, Körpersprache

**a) Akustische Ereignisse (Beifall, Zwischenrufe, Lachen, Buhrufe) — ja, gut machbar.**
**Sound Event Detection** mit **PANNs** oder **YAMNet** (trainiert auf
**AudioSet**, 527 Klassen inkl. *Applause, Cheering, Booing, Laughter*),
frame-weise (`Cnn14_DecisionLevelAtt`). **Lautstärke/Intensität** über
RMS-/LUFS-Pegel je Segment → „Beifall (stark)" vs. „vereinzelt". Das bildet
exakt nach, was Stenografen heute klammern: „(Beifall bei …)", „(Lachen)",
„(Widerspruch)". → Im Graph als `AkustischesEreignis {typ, intensitaet, start_sec}`,
verknüpft mit TOP/Redebeitrag und Provenienz.

**b) Lippenlesen / audiovisuelle ASR (AVSR) — als Ergänzung, nicht solo.**
**AV-HuBERT** (Meta) und **Auto-AVSR** (Apache-2.0). Realität: rein visuell
~**20 % WER** vs. ~**1 % audio** (LRS3). Lippenlesen **allein** ist also schwach,
verbessert aber AVSR **bei Lärm/Überlappung/Zwischenrufen** spürbar. Hürde im
Plenum: frontale Gesichts-Crops je Sprecher (Kameraregie liefert die nicht
durchgängig). Empfehlung: optionaler Robustheits-Layer, nicht Kern.

**c) Körpersprache/Gestik — bewusst zurückhaltend.**
Pose-Estimation (MediaPipe/OpenPose) kann grobe **Ereignisse** liefern
(„Person verlässt den Platz" → Befangenheit, wie im Demo). **Interpretierende**
KI über Körpersprache von Abgeordneten ist rechtlich/ethisch heikel
(Persönlichkeitsrecht) und fehleranfällig → nur faktische Ereignisse, keine
Deutung von Mimik/Haltung.

## 9. Können wir echte Bundestagssitzungen analysieren?

**Ja.** Plenarsitzungen sind öffentlich; Protokolle sind **amtliche Werke**
(§ 5 UrhG, gemeinfrei) und als **Open Data (XML/JSON)** + über die **DIP-API**
abrufbar; die **Mediathek** bietet Video/Audio zum Ansehen/Download. Zu klären:
Nutzungslizenz der Mediathek-Videos und DSGVO bei biometrischen Merkmalen
(Stimme/Gesicht) — entschärft durch den öffentlichen Amtsträger-Kontext und
On-prem-Betrieb. Für ASR-Tests: offizielle Audio/Video + Open-Data-Protokoll als
**Goldstandard** zum WER-Messen.

## 10. NotebookLM — geeignet?

Ehrliche Einordnung: **NotebookLM** (Google) ist stark für **exploratives Q&A**
und „Audio Overviews" über hochgeladene Dokumente, **mit Quellenzitaten** — gut
für eine schnelle Demo. **Aber** für eine Behördenlösung ungeeignet als Kern:
Cloud (Datenhoheit/DSGVO), **keine** Diarisierung/Sound-Event-Erkennung/
Strukturierung, **kein** Knowledge Graph, nicht reproduzierbar/auditierbar,
kein On-prem. → NotebookLM = schneller Prototyp für Dokument-Q&A;
`graph-protokoll` = das **on-prem, strukturierte, prüf- und auditierbare**
Gegenstück mit Graph + Provenienz.

## 11. Test-Quellen (echte Daten)

| Quelle | Inhalt | Nutzung |
| ------ | ------ | ------- |
| **Bundestag Open Data** | Plenarprotokolle/Drucksachen (XML/JSON) | Goldstandard-Text für WER |
| **DIP-API** | Vorgänge, Personen, Protokolle (API-Key) | Metadaten, Drucksachen |
| **Bundestag Mediathek** | Video/Audio der Sitzungen | ASR-/SED-Eingabe |
| **Open Discourse** (GitHub) | Korpus aller Plenardebatten ab 1949 | strukturierte Reden/Sprecher |
| **GermaParl / GermaParlTEI** (PolMine) | TEI-XML-Korpus 1949–2021, Mini-Subset | annotiertes Testset |
| **Korpus Plenarprotokolle 1949–2025** (S. Fobbe, Zenodo) | bereinigte Volltexte | großer Trainings-/Testpool |
| **ParlaMint** | multinationale Parlamentskorpora | Cross-Lingual-Vergleich |
| **VideoTranscriptGenerator** (OpenHypervideo) | zeitbasierte Transkripte aus Open Data | Video↔Protokoll-Mapping |

---

### Quellen (öffentlich)

- Deutscher Bundestag — Open Data: <https://www.bundestag.de/services/opendata>
- DIP — Parlamentsmaterialien & API: <https://dip.bundestag.de/> · <https://dip.bundestag.de/über-dip/hilfe/api>
- Bundestag — Stenografen/Verfahren: <https://www.bundestag.de/webarchiv/textarchiv/2018/kw31-stenografen-565088>
- Bundestag — Mediathek: <https://www.bundestag.de/mediathek>
- Open Discourse: <https://github.com/open-discourse/open-discourse>
- GermaParl (PolMine): <https://polmine.github.io/GermaParl/> · <https://github.com/PolMine/GermaParlTEI>
- PANNs (AudioSet, Sound Event Detection): <https://github.com/qiuqiangkong/audioset_tagging_cnn>
- AV-HuBERT: <https://github.com/facebookresearch/av_hubert> · Auto-AVSR: <https://github.com/mpc001/auto_avsr>
- VideoTranscriptGenerator (OpenHypervideo): <https://github.com/OpenHypervideo/VideoTranscriptGenerator>

> Alle inhaltlichen Demo-Daten (Personen, Fraktionen, Zahlen, Quellen) sind
> **frei erfunden** und dienen ausschließlich der Demonstration der Pipeline.
