---
type: api
title: Bundestag Open Data (plenary XML)
description: Official plenary-protocol XML — the gemeinfrei golden source.
resource: pipeline/bundestag_xml.py
tags: [api, bundestag, opendata, xml, gemeinfrei]
timestamp: 2026-06-14
---

# Bundestag Open Data — plenary XML

The authoritative, gemeinfrei (§5 UrhG) source for real sessions; no audio needed.

- **Stable URL pattern:** `https://dserver.bundestag.de/btp/<wp>/<wp><nnn>.xml` (DTD
  `dbtplenarprotokoll`, WP19+). All WP21 sessions available.
- Parsed by [[bundestag-xml]]; fetched by `scripts/fetch-session.sh` / `sync_sessions.py
  --official`.
- Real data lives in `data/real/` (real & gemeinfrei); `data/sample/*.xml` is fictional.
- Fact-check on real content is LLM-based with disclaimer (ADR-0007), never the fictional
  corpus.

**Source:** `README.md:195-216,258-262`; `docs/quellen.md`. Skill: `bundestag-ingestion`.
