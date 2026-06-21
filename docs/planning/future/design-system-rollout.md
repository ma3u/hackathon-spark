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

## Rollout-Schritt 2 (2026-06-21)
- [x] **CD-Blau übernommen** (`--accent #0b3e7a`, beide Seiten) — **Näherung**: die offizielle
      Bundestag-CD-Spezifikation (HKS/Pantone-Hex) ließ sich nicht verifizieren (Suche/Live-Probe
      ohne Treffer). Token zentral → bei Vorlage des CD-Handbuchs 1:1 austauschbar. Gold `#c8a44d`.
- [x] **FAB** (Material Extended FAB) „▶ Video der Sitzung" unten rechts — nur in der Graph-Ansicht
      mit verfügbarem Video; YouTube eingebettet, Mediathek im Tab. Nutzt den `playVideo`-Pfad.
- [x] **Motion**: Modal-Scale-in (`@keyframes modalIn`, Material-Easing), FAB-Hover-Lift,
      `prefers-reduced-motion` respektiert.
- [x] **WCAG-AA-Audit** nach Farbwechsel erneut: **index 0, aggregate 0 Verstöße** (axe-core 4.10).

## Offen
- [ ] **Exakte offizielle CD-Werte** übernehmen, sobald das Bundestag-CD-Handbuch vorliegt.
- [ ] **Material Type Scale** auf alle Ebenen ausweiten (display/headline/title/body/label).
- [ ] Echtes **Ripple** (braucht JS).
- [x] **State Layers** + **Fokus-Ringe** flächendeckend (s. o.).
- [x] **WCAG-AA-Audit** (axe-core 4.10) → index 0, aggregate 0.
      Behoben: grünes `.fakt`/`--ok` auf AA-Kontrast gedunkelt (#1a7a34), Badge-Text-Amber
      entkoppelt (#8a5a12), scrollbare Tabellen tastatur-fokussierbar (`tabindex=0`, role/aria).
