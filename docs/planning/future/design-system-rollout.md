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

## Offen
- [ ] **Offizielle Bundestag-CD-Werte** prüfen/übernehmen (exaktes Blau, Gold, Abstände, Typo).
- [ ] **Bundestagsadler / Wortmarke** dezent in die App-Bar (inline SVG, klein).
- [ ] **Material Type Scale** (display/headline/title/body/label) statt Ad-hoc-Größen.
- [ ] **State Layers / Ripple** + sichtbare Fokus-Ringe auf allen interaktiven Flächen.
- [ ] Optional **FAB** für die Primäraktion (z. B. „▶ Video der Sitzung").
- [ ] **Motion** (Material-Easing) bei Panel-/Overlay-Wechseln.
- [ ] **WCAG-AA-Kontrast-Audit** des hellen Themes (axe-core), wie schon für die alte UI.
