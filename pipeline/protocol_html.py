"""
Protokoll-HTML — Sitzung als lesbares Plenarprotokoll (wie das amtliche PDF), aber
aus den **YouTube-Untertiteln** erzeugt: mit korrekten Umlauten und **Zeit-Deeplinks**
ins Video (`watch?v=…&t=<sek>s`), Quellenangabe und Faktencheck.

Produktivpfad: amtliches XML → identischer Renderer (Quelle = Open-Data-PDF/-XML; ohne
Sekunden-Deeplink, da das amtliche Protokoll keine Zeitstempel trägt → Link aufs PDF).
Demopfad/Hauptfall: YouTube-Mitschnitt → jede Passage sekundengenau im Video belegbar.

Wichtig: die Seite trägt `<meta charset="utf-8">`. Das behebt die „BÃœNDNIS"-Mojibake,
die entsteht, wenn ein UTF-8-`.txt` ohne Charset-Header ausgeliefert und vom Browser als
Latin-1 interpretiert wird — eine HTML-Seite deklariert ihre Kodierung selbst.
"""

from __future__ import annotations

import html


def _esc(s) -> str:
    return html.escape(str(s or ""))


def _mmss(sec) -> str:
    sec = int(sec or 0)
    return f"{sec // 60:02d}:{sec % 60:02d}"


def _deeplink(video_id: str | None, sec) -> str:
    if not video_id:
        return ""
    t = int(sec or 0)
    return f"https://www.youtube.com/watch?v={video_id}&t={t}s"


# Verdikt → Farbe (gleiche Skala wie Frontend/Dashboard)
_VERDICT_COLOR = {
    "bestätigt": "#1e7d34", "teilweise": "#9a6b00", "irreführend": "#9a6b00",
    "falsch": "#c0392b", "unbelegt": "#5a636e",
}


def render(protocol, *, factchecks=None, quelle_url: str | None = None,
           quelle_label: str | None = None, video_id: str | None = None,
           rede_links: dict | None = None, official_pdf: str | None = None,
           official_xml: str | None = None, disclaimer: str | None = None,
           title: str | None = None) -> str:
    """Protocol → eigenständige HTML-Seite (PDF-ähnliches Plenarprotokoll).

    Deeplink-Modus: `video_id` → ein Video, `&t=`-Sekundenlinks (YouTube). `rede_links`
    ({utterance_index: clip_url}) → ein Video PRO Rede (Mediathek, dbtg.tv/fvid).
    """
    rede_links = rede_links or {}
    m = protocol.meeting
    fc = factchecks or []
    kopf = title or (f"{m.get('gremium', 'Sitzung')}"
                     + (f" — {m.get('wahlperiode')}. WP, {m.get('sitzung_nr')}. Sitzung"
                        if m.get("wahlperiode") else "")
                     + (f", {m.get('datum')}" if m.get("datum") else ""))

    # Provenienz: Aussage-Index → Startsekunde (für Faktencheck-Deeplinks)
    start_of_utt = {i: u.start for i, u in enumerate(protocol.utterances)}

    L: list[str] = []
    L.append("<!doctype html><html lang=\"de\"><head><meta charset=\"utf-8\">")
    L.append('<meta name="viewport" content="width=device-width, initial-scale=1">')
    L.append(f"<title>{_esc(kopf)}</title>")
    L.append("""<style>
:root{--bg:#fbfbfa;--fg:#1a1a1a;--muted:#5a636e;--accent:#0b5fff;--line:#e2e2dd;--panel:#fff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 Georgia,"Times New Roman",serif;
  -webkit-font-smoothing:antialiased}
.wrap{max-width:820px;margin:0 auto;padding:32px 22px 80px}
header{border-bottom:3px double var(--line);padding-bottom:16px;margin-bottom:8px}
h1{font-size:24px;margin:0 0 6px}
.sub,.src{font-family:system-ui,sans-serif;font-size:13px;color:var(--muted)}
.src{margin-top:8px} .src a{color:var(--accent)}
h2{font-size:18px;margin:30px 0 10px;border-bottom:1px solid var(--line);padding-bottom:4px}
h3{font:600 14px/1.4 system-ui,sans-serif;margin:22px 0 2px}
.toc{font-family:system-ui,sans-serif;font-size:14px;background:var(--panel);border:1px solid var(--line);
  border-radius:8px;padding:12px 16px;margin:14px 0}
.toc a{color:var(--accent);text-decoration:none} .toc li{margin:3px 0}
.rede{margin:14px 0;padding-left:12px;border-left:3px solid var(--line)}
.meta{font-family:system-ui,sans-serif;font-size:12px;color:var(--muted);margin-bottom:2px}
.t{font-family:system-ui,sans-serif;font-size:12px;text-decoration:none;color:var(--accent);
  background:#eef3ff;border:1px solid #d4e0ff;border-radius:5px;padding:0 6px;margin-right:6px;white-space:nowrap}
.reak{font-family:system-ui,sans-serif;font-size:13px;color:var(--muted);font-style:italic;margin:4px 0}
.fc{font-family:system-ui,sans-serif;font-size:13.5px;border-left:4px solid var(--line);
  background:var(--panel);padding:8px 12px;margin:10px 0;border-radius:0 6px 6px 0}
.fc .v{font-weight:700;text-transform:uppercase;font-size:12px}
.fc .q{color:var(--muted);font-size:12px} .fc a{color:var(--accent)}
.warn{font-family:system-ui,sans-serif;font-size:12.5px;background:#fff7e6;border:1px solid #ffd591;
  border-radius:6px;padding:8px 12px;margin:12px 0;color:#7a4d00}
footer{margin-top:40px;border-top:1px solid var(--line);padding-top:12px;
  font-family:system-ui,sans-serif;font-size:12px;color:var(--muted)}
@media print{.t{border:none;background:none}body{background:#fff}}
</style></head><body><div class="wrap">""")

    # ── Kopf + Quelle ────────────────────────────────────────────────────────
    L.append("<header>")
    L.append(f"<h1>Plenarprotokoll (Transkript)</h1>")
    L.append(f'<div class="sub">{_esc(kopf)}</div>')
    quellen = []
    if quelle_url:
        quellen.append(f'<a href="{_esc(quelle_url)}" target="_blank" rel="noopener">'
                       f'{_esc(quelle_label or quelle_url)}</a>')
    if official_pdf:
        quellen.append(f'amtliches PDF: <a href="{_esc(official_pdf)}" target="_blank" rel="noopener">'
                       f'dserver.bundestag.de</a>')
    if official_xml:
        quellen.append(f'amtliches XML: <a href="{_esc(official_xml)}" target="_blank" rel="noopener">'
                       f'Open Data</a>')
    if quellen:
        L.append('<div class="src">Quelle: ' + " · ".join(quellen) + "</div>")
    L.append("</header>")

    if disclaimer:
        L.append(f'<div class="warn">⚠️ {_esc(disclaimer)}</div>')

    # ── Tagesordnung ─────────────────────────────────────────────────────────
    if protocol.tops:
        L.append('<div class="toc"><b>Tagesordnung</b><ul>')
        for t in protocol.tops:
            L.append(f'<li><a href="#top{t["nummer"]}">TOP {t["nummer"]}: {_esc(t["titel"])}</a></li>')
        L.append("</ul></div>")

    # Reaktionen nach Redebeitrag-Index gruppieren (REAKTION_AUF nutzt rede_index)
    reak_by_rede: dict[int, list] = {}
    for k in protocol.kommentare:
        reak_by_rede.setdefault(k.get("rede_index", -1), []).append(k)

    # ── Transkript nach TOP → Redebeiträgen ──────────────────────────────────
    reden_by_top: dict[int, list] = {}
    for r in protocol.redebeitraege:
        reden_by_top.setdefault(r.get("top_nummer"), []).append(r)

    L.append("<h2>Wortprotokoll</h2>")
    if not protocol.redebeitraege:
        # YouTube-Untertitel ohne Sprecher-Labels: Transkript als zeitgestempelte Absätze
        L.append('<div class="rede">')
        for i, u in enumerate(protocol.utterances):
            if not u.text:
                continue
            dl = _deeplink(video_id, u.start)
            tag = (f'<a class="t" href="{dl}" target="_blank" rel="noopener">▶ {_mmss(u.start)}</a>'
                   if dl else f'<span class="t">{_esc(u.timecode)}</span>')
            L.append(f"<p>{tag}{_esc(u.text)}</p>")
        L.append("</div>")
    else:
        for t in protocol.tops:
            L.append(f'<h3 id="top{t["nummer"]}">TOP {t["nummer"]}: {_esc(t["titel"])}</h3>')
            for r in reden_by_top.get(t["nummer"], []):
                q = (r.get("quelle_utterances") or [None])[0]
                clip = rede_links.get(q) if q is not None else None
                sec = start_of_utt.get(q) if q is not None else None
                frak = f' · {_esc(r["fraktion"])}' if r.get("fraktion") else ""
                if clip:  # Mediathek: ein Video pro Rede
                    tag = f'<a class="t" href="{_esc(clip)}" target="_blank" rel="noopener">▶ Video</a>'
                elif video_id and sec is not None:  # YouTube: ein Video, Sekunden-Deeplink
                    tag = f'<a class="t" href="{_deeplink(video_id, sec)}" target="_blank" rel="noopener">▶ {_mmss(sec)}</a>'
                else:
                    tag = ""
                L.append('<div class="rede">')
                L.append(f'<div class="meta">{tag}{_esc(r["person"])}{frak}</div>')
                # Text der zugehörigen Utterances
                for ui in (r.get("quelle_utterances") or []):
                    if 0 <= ui < len(protocol.utterances):
                        L.append(f"<p>{_esc(protocol.utterances[ui].text)}</p>")
                # Saalreaktionen auf diesen Redebeitrag
                for k in reak_by_rede.get(ui if r.get("quelle_utterances") else -1, []):
                    L.append(f'<div class="reak">({_esc(k.get("text") or k.get("typ"))})</div>')
                L.append("</div>")

    # ── Faktencheck ──────────────────────────────────────────────────────────
    if fc:
        L.append("<h2>🔎 Faktencheck</h2>")
        for c in fc:
            col = _VERDICT_COLOR.get(c.verdikt, "#5a636e")
            q = (c.quelle_utterances or [None])[0]
            clip = rede_links.get(q) if q is not None else None
            sec = start_of_utt.get(q) if q is not None else None
            if clip:
                deep = f' · <a href="{_esc(clip)}" target="_blank" rel="noopener">▶ zum Redebeitrag (Video)</a>'
            elif video_id and sec is not None:
                deep = f' · <a href="{_deeplink(video_id, sec)}" target="_blank" rel="noopener">▶ im Video [{_mmss(sec)}]</a>'
            else:
                deep = ""
            quelle = ""
            if c.quelle:
                qt = _esc(c.quelle.get("titel", "Quelle"))
                qu = c.quelle.get("url", "")
                quelle = (f' · Quelle: <a href="{_esc(qu)}" target="_blank" rel="noopener">{qt}</a>'
                          if qu else f" · Quelle: {qt}")
            L.append(f'<div class="fc" style="border-color:{col}">'
                     f'<span class="v" style="color:{col}">{_esc(c.verdikt)}</span> — '
                     f'{_esc(c.person or "")}<br>„{_esc(c.text)}"<br>'
                     f'<span class="q">{_esc(c.begruendung)}{quelle}{deep}</span></div>')

    # ── Saalreaktionen-Übersicht (falls vorhanden) ───────────────────────────
    if protocol.kommentare:
        L.append(f'<footer>{len(protocol.kommentare)} protokollierte Saalreaktionen · '
                 f'{len(protocol.redebeitraege)} Redebeiträge · {len(protocol.utterances)} Transkriptsegmente.</footer>')

    L.append('<footer>Erzeugt von graph-protokoll (SPARK Challenge 2). '
             'Transkript automatisch (Fehler möglich); Faktencheck KI-gestützt, ungeprüft.</footer>')
    L.append("</div></body></html>")
    return "\n".join(L)
