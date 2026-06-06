# Öffentliche Quellen

Vollständige Sammlung der für `graph-protokoll` genutzten öffentlichen Quellen.
Hinweis: In der Claude-Web-Sandbox sind `bundestag.de`, `dip.bundestag.de` und
`youtube.com` netzgesperrt (HTTP 403) — die Pipeline lädt diese Quellen auf der
Maschine der Nutzer:innen. GitHub ist erreichbar (DTD/Korpora geklont).

## 1. Amtliche Bundestagsquellen

| Quelle | Inhalt | URL |
| ------ | ------ | --- |
| Open Data | Plenarprotokolle & Drucksachen (XML/JSON), MdB-Stammdaten | https://www.bundestag.de/services/opendata |
| Plenarprotokolle | endgültige Protokolle (PDF/XML) | https://www.bundestag.de/dokumente/protokolle/plenarprotokolle |
| Tagesaktuelles Protokoll | vorläufiges Protokoll am Sitzungstag | https://www.bundestag.de/dokumente/protokolle/vorlaeufig |
| DIP | Vorgänge, Personen, Drucksachen, Protokolle | https://dip.bundestag.de/ |
| DIP-API (Hilfe/Key) | REST-API (API-Key) | https://dip.bundestag.de/über-dip/hilfe/api |
| Mediathek / Parlamentsfernsehen | Video/Audio der Sitzungen (Download) | https://www.bundestag.de/mediathek |
| YouTube-Kanal | vollständige Plenardebatten | https://www.youtube.com/@bundestag |
| Stenografen/Verfahren | Beschreibung des heutigen Prozesses | https://www.bundestag.de/webarchiv/textarchiv/2018/kw31-stenografen-565088 |

## 2. XML-Schema (amtlich)

| Quelle | Inhalt | URL |
| ------ | ------ | --- |
| DTD `dbtplenarprotokoll` (ab WP19) | Strukturdefinition der Protokoll-XML | https://www.bundestag.de/resource/blob/575720/.../dbtplenarprotokoll.dtd |
| DTD-Dokumentation (PDF) | kommentierte Felderläuterung | https://www.bundestag.de/resource/blob/577234/dbtplenarprotokoll_kommentiert.pdf |
| DTD-Spiegel (GitHub) | maschinell genutzte DTD | https://github.com/demokratie-live/scapacra-bt |

## 3. Forschungskorpora (Test/Goldstandard)

| Quelle | Inhalt | URL |
| ------ | ------ | --- |
| Open Discourse | Korpus aller Plenardebatten ab 1949 | https://github.com/open-discourse/open-discourse |
| GermaParl (PolMine) | TEI-XML-Korpus 1949–2021 (+ Mini-Subset) | https://polmine.github.io/GermaParl/ · https://github.com/PolMine/GermaParlTEI |
| Korpus Plenarprotokolle 1949–2025 (S. Fobbe) | bereinigte Volltexte (Zenodo) | https://zenodo.org/records/4542662 |
| VideoTranscriptGenerator | zeitbasierte Transkripte aus Open Data | https://github.com/OpenHypervideo/VideoTranscriptGenerator |

## 4. Sprach-/Audio-Technik (Open Source)

| Quelle | Zweck | URL |
| ------ | ----- | --- |
| faster-whisper | ASR (CTranslate2) | https://github.com/SYSTRAN/faster-whisper |
| WhisperX | ASR + Wort-Alignment | https://github.com/m-bain/whisperX |
| pyannote.audio | Sprecher-Diarisierung | https://github.com/pyannote/pyannote-audio |
| PANNs (AudioSet) | Sound-Event-Detection (Beifall/Buhrufe) | https://github.com/qiuqiangkong/audioset_tagging_cnn |
| YAMNet | Audio-Event-Klassifikation | https://www.tensorflow.org/hub/tutorials/yamnet |
| AV-HuBERT | audiovisuelle ASR / Lippenlesen | https://github.com/facebookresearch/av_hubert |
| Auto-AVSR (Apache-2.0) | Lippenlesen (VSR) | https://github.com/mpc001/auto_avsr |

## 5. Graph & GraphRAG

| Quelle | Zweck | URL |
| ------ | ----- | --- |
| Neo4j 5 Community | Knowledge Graph | https://neo4j.com/ |
| neo4j-graphrag (offiziell) | GraphRAG / Text2Cypher | https://github.com/neo4j/neo4j-graphrag-python |

## 6. SPARK / Lizenz / openCode

| Quelle | Zweck | URL |
| ------ | ----- | --- |
| BMDS SPARK Workflow | Referenz-KI-Module (Lizenz EUPL-1.2) | https://gitlab.opencode.de/bmds/planungs-und-genehmigungsbeschleunigung/spark-workflow |
| openCode Standardlizenzen | Lizenzrahmen Public Money–Public Code | https://opencode.de/en/knowledge/general-conditions/standardised-open-source-licenses |
| EUPL-1.2 Volltext (Spiegel) | Lizenztext | https://gitlab.opencode.de/fitko/docs/portal/-/blob/main/LICENSES/EUPL-1.2.txt |
| heise: Public Money, Public Code | Hintergrund zur Veröffentlichung | https://www.heise.de/en/news/Public-Money-Public-Code-Federal-government-releases-AI-modules-11243619.html |

---

> Verwendung amtlicher Protokolle: amtliche Werke sind nach § 5 UrhG gemeinfrei.
> Für Video-/Mediathek-Inhalte ist die Nutzungslizenz vor produktivem Einsatz zu
> klären (siehe Fragenkatalog `docs/fragen-bundestag.md`, Block B).
