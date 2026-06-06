# Fragenkatalog für die Bundestags-Kolleg:innen (Stenografischer Dienst / IT / Verwaltung)

Ziel: die Challenge **konkretisieren** — verstehen, **wo der Prozess heute steht**,
**wo die Herausforderungen** liegen, und **woran Erfolg gemessen** wird. Pro Block
eine kurze Hypothese (unser Stand) + die offenen Fragen.

---

## A) Heutiger Prozess — Ist-Aufnahme

> Hypothese: 16 Stenograf:innen, Wechsel alle 5 Min, Kurzschrift→Volltext mit
> Schreibkraft; teils bereits ASR; vorläufiges Protokoll am Sitzungstag,
> endgültig am Folgewerktag; Redner-Korrekturrecht.

1. Welche Schritte vom gesprochenen Wort bis zum endgültigen Plenarprotokoll —
   und welche sind heute schon werkzeuggestützt (ASR, Makros, Terminologie-DB)?
2. Wo genau wird **bereits automatische Spracherkennung** eingesetzt, mit welcher
   Engine und welcher gemessenen **Wortfehlerrate (WER)**?
3. Wie lange dauern vorläufiges vs. endgültiges Protokoll heute (Durchlaufzeit)?
4. Wie werden **Zwischenrufe, Beifall, Zurufe** erfasst und zugeordnet
   (manuell? nach Gehör? aus dem Saalmikrofon)?
5. Wie wird der **Redner** technisch identifiziert (Rednerliste, Saalmikrofon,
   Präsidium) — und wie oft gibt es Verwechslungen?

## B) Datenzugang & Formate

6. Können wir die **amtlichen XML** (`dbtplenarprotokoll`) der Testsitzungen
   sowie die zugehörigen **Audio-/Videodateien** unter klarer Lizenz nutzen?
7. Welche **Lizenz/Nutzungsbedingungen** gelten für Mediathek- und
   YouTube-Inhalte zur Weiterverarbeitung (ASR, Forschung, Pilot)?
8. Gibt es eine **zeitsynchrone** Verknüpfung Video ↔ Protokollabschnitt
   (Timecodes), oder müssen wir sie selbst herstellen?
9. Ist DIP-API-Zugang (Vorgänge, Drucksachen, Antworten der Bundesregierung)
   für den Faktencheck-Korpus möglich?

## C) Qualität, Korrektur & Verbindlichkeit

10. Wie ist das **Korrekturrecht** der Redner:innen ausgestaltet, und wie sollen
    KI-Entwurf vs. autorisierte Endfassung unterschieden werden (Diff/Versionierung)?
11. Welche **Fehlerklassen** sind heute am teuersten (Eigennamen, Zahlen,
    Fachbegriffe, Dialekt, Schnellsprecher, Überlappung)?
12. Welche **WER/Genauigkeit** wäre als Entwurf akzeptabel, ab wann spart es real
    Arbeit (Akzeptanzschwelle)?

## D) Recht, Datenschutz, Barrierefreiheit

13. Bewertung von **Stimme/Gesicht als biometrische Daten** (Art. 9 DSGVO) im
    Kontext öffentlicher Amtsträger — Rahmen für Diarisierung/AVSR?
14. Anforderungen an **On-prem/digitale Souveränität** (kein Cloud-Versand)?
15. Synergie mit **Untertitel/Barrierefreiheit** (Live-Caption) — gemeinsame Pipeline?

## E) Multimodalität (Saalreaktionen, Lautstärke)

16. Mehrwert einer automatischen Erkennung von **Beifall/Widerspruch/Lautstärke**
    (Sound-Event-Detection) — ist das für Auswertung/Statistik gewünscht?
17. Gibt es **Mehrkanal-/Saalmikrofon-Audio**, das Zwischenrufe besser trennt?

## F) Akzeptanzkriterien & Pilot

18. Welche **Auswertungen** wären am nützlichsten (unser Dashboard-Vorschlag:
    Top-Themen, Sprachanteil pro Fraktion, Stimmung je Thema, Faktencheck-Bilanz)?
19. Welche **natürlichsprachigen Fragen** sollen Mitarbeitende an den Graphen
    stellen können (für Text2Cypher-Beispiele)?
20. Wie sähe ein **Pilot** aus (Sitzungen, Beteiligte, Erfolgskriterien, Frist)?

## G) Betrieb

21. Ziel-Infrastruktur (Hardware/GPU, Kubernetes, Neo4j vorhanden)?
22. Wer **betreibt** die Lösung später (Stenografischer Dienst, IT-Referat)?

---

### Was wir mitbringen (Diskussionsgrundlage)
Lauffähiger Prototyp: amtliches XML → Neo4j-Graph → GraphRAG (Text2Cypher) →
Dashboard, Faktencheck **immer mit Quelle**, plus ein **Gap-Analyse-Tool**
(Protokoll ↔ Video-ASR: WER, Reaktions-Recall, Sprecher-/Inhalts-Lücken) für
einen gemeinsamen, datenbasierten Soll-Ist-Vergleich.
