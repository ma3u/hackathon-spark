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
- [ ] **State Layers / Ripple** + sichtbare Fokus-Ringe flächendeckend.
- [ ] Optional **FAB** für die Primäraktion (z. B. „▶ Video der Sitzung").
- [ ] **Motion** (Material-Easing) bei Panel-/Overlay-Wechseln.
- [ ] **WCAG-AA-Kontrast-Audit** des hellen Themes (axe-core), wie schon für die alte UI.
