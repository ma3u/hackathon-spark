# NOTICE — eigenständiges Projekt (getrennt von EHDS)

**`graph-protokoll` ist ein eigenständiges Projekt** und gehört **nicht** zum
EHDS-Gesundheitsdatenraum, in dessen Repository es derzeit nur _ko-lokalisiert_
liegt.

## Klare Trennung

- **Domäne:** SPARK-Hackathon Challenge 2 (Sitzungs-/Plenarprotokoll-Analyse) —
  fachlich getrennt von EHDS (DSP/FHIR/OMOP-Gesundheitsdatenraum).
- **Code:** vollständig in sich geschlossen unter `graph-protokoll/`
  (eigene `LICENSE`, `publiccode.yml`, `requirements.txt`, `web/`, `docs/`,
  `.github/workflows/`). **Keine** Abhängigkeit auf EHDS-Code; **keine** EHDS-Datei
  wird verändert.
- **Lizenz:** EUPL-1.2 (wie BMDS SPARK) — eigenständig, unabhängig von EHDS.
- **Git:** entwickelt auf dem Branch `claude/spark-repo-analysis-J1LmB`. Dieser
  Branch ist **nicht** in den EHDS-`main` gemerged und **soll es auch nicht**.

## Warum liegt es (noch) hier?

Die Arbeits-Session konnte aus Rechte-Gründen **kein separates GitHub-Repo
anlegen** (der Token ist auf das eine Repo beschränkt; `create_repository` → 403).
`graph-protokoll/` ist daher der einzige Ort, der zwischen den Sessions
persistiert.

## So wird es vollständig ausgegründet (eigenes Repo)

```bash
cd graph-protokoll
./scripts/publish-to-github.sh graph-protokoll
# → eigenständiges Repo  https://github.com/<user>/graph-protokoll  mit GitHub Pages
```

Danach kann der Branch `claude/spark-repo-analysis-J1LmB` im EHDS-Repo gelöscht
oder liegen gelassen werden — er gehört nicht in EHDS.
