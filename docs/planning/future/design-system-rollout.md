---
title: Design-System-Rollout — Material 3 + Bundestag CD vervollständigen
status: future
owner: ma3u
updated: 2026-06-14
adr: ["0016", "0015"]
---

# Design-System-Rollout — Material 3 + Bundestag CD vervollständigen

Das Design-System (ADR-0016) ist als helles Material-Theme im Bundestag-Blau angelegt. Offene
Schritte, damit es klar „Material 3" und authentisch Bundestag wirkt.

**Source:** ADR-0016.

## Done (2026-06-14)
- [x] Helles Material-Theme, Bundestag-blaue App-Bar, weiße Karten mit Elevation, Pill-Buttons.
- [x] Roboto selbst gehostet (ADR-0015).
- [x] Graph: Auswahl-Highlight in Gold + gedimmte Nachbarschaft; Knotengröße nach Bedeutung.

## Rollout gestartet (2026-06-14)
- [x] **Wort-/Bildmarke** in der App-Bar: originaler **Reichstagskuppel-Glyph** (inline SVG) +
      Wortmarke „graph·protokoll" / „Deutscher Bundestag …" — beide Seiten. Bewusst **nicht** der
      offizielle Bundestagsadler (Staatswappen / Nutzungsrechte), sondern eine eigene Marke.
- [x] **Gold-Akzent** (`--gold #c8a44d`): App-Bar-Unterkante + Marke (CD-Cue).
- [x] **Material Type Scale** begonnen (`--ts-title`/`--ts-sub`), App-Bar darauf umgestellt.
- [x] **Press-State** auf Buttons/Tabs (`:active`).

## Offen
- [ ] **Offizielle Bundestag-CD-Werte** prüfen/übernehmen (exaktes Blau/Gold, Raster, vollständige Typo).
- [ ] **Material Type Scale** auf alle Ebenen ausweiten (display/headline/title/body/label).
- [x] **State Layers** (Hover/Focus/Press via `::after`, adaptiv currentColor) + **Fokus-Ringe
      flächendeckend** (`:focus-visible`, Blau im Body / Weiß auf der App-Bar) — beide Seiten.
      Offen bleibt nur echtes **Ripple** (braucht JS).
- [ ] Optional **FAB** für die Primäraktion (z. B. „▶ Video der Sitzung").
- [ ] **Motion** (Material-Easing) bei Panel-/Overlay-Wechseln.
- [x] **WCAG-AA-Audit** (axe-core 4.10, wcag2a/2aa/21a/21aa) → **index 0, aggregate 0 Verstöße**.
      Behoben: grünes `.fakt`/`--ok` auf AA-Kontrast gedunkelt (#1a7a34), Badge-Text-Amber
      entkoppelt (#8a5a12), scrollbare Tabellen tastatur-fokussierbar (`tabindex=0`, role/aria).
