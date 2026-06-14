"""
YouTube-Clip-Discovery über die offizielle **YouTube Data API v3** (ADR-0013).

Ersetzt das brüchige Titel-Scraping in `youtube_clips.collect_session` (yt-dlp `--flat-playlist`)
durch die amtliche API: `channels.list(forHandle=bundestag)` → Uploads-Playlist →
`playlistItems.list` (paginiert). Gibt dieselbe Struktur zurück wie `youtube_clips.collect_session`
(`{video_id, top, topic, url}`), ist also ein direkter Ersatz für die Discovery.

Produktivpfad: offizielle Data API (Schlüssel `YOUTUBE_API_KEY` aus der Umgebung/`.env`,
GCP-Projekt mit aktivierter `youtube.googleapis.com`). Nur Stdlib (`urllib`) — kein pip nötig,
aber Netz + Schlüssel.
Demopfad: keiner — Discovery braucht Netz. Der dep-freie Demo nutzt mitgelieferte VTTs
(`data/sample`/`data/real`); die Untertitel-Texte holt weiterhin `youtube_clips._caption`
(yt-dlp), da `captions.download` nur für eigene Videos erlaubt ist.

Quota: `playlistItems.list` kostet 1 Einheit/Seite (≤50 Items), `search.list` 100 — daher
Playlist-Weg. Standardkontingent ≈ 10 000 Einheiten/Tag.

  python -m pipeline.youtube_api 83        # Clips der Sitzung 83 (Selbsttest)
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

from .youtube_clips import _NR, _TOP  # identische Titel-Regex wiederverwenden (DRY)

_API = "https://www.googleapis.com/youtube/v3/"
_HANDLE = "bundestag"  # @bundestag


def _get(method: str, api_key: str, **params) -> dict:
    """Ein Data-API-Aufruf → JSON. Schlüssel wird in Fehlertexten nie durchgereicht."""
    params["key"] = api_key
    url = _API + method + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=30) as r:  # noqa: S310 (feste API-URL)
            return json.load(r)
    except urllib.error.HTTPError as e:  # noqa: PERF203
        body = e.read().decode("utf-8", "replace").replace(api_key, "<KEY>")
        raise RuntimeError(f"YouTube Data API {method} → HTTP {e.code}: {body[:300]}") from None


def uploads_playlist(api_key: str) -> tuple[str, str]:
    """@bundestag → (channel_id, uploads_playlist_id)."""
    data = _get("channels", api_key, part="contentDetails,snippet", forHandle=_HANDLE)
    items = data.get("items") or []
    if not items:
        raise RuntimeError("Kanal @bundestag nicht gefunden (forHandle).")
    it = items[0]
    return it["id"], it["contentDetails"]["relatedPlaylists"]["uploads"]


def collect_session(nr, *, api_key: str | None = None, max_pages: int = 40) -> list[dict]:
    """Clips EINER Sitzung [{video_id, top, topic, url}] — amtliche API statt yt-dlp.

    Struktur identisch zu `youtube_clips.collect_session`, daher dort eintauschbar.
    """
    nr = int(nr)
    api_key = api_key or os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        raise RuntimeError("YOUTUBE_API_KEY fehlt (.env) — für die YouTube Data API nötig.")

    _, uploads = uploads_playlist(api_key)
    clips: list[dict] = []
    page_token, pages = None, 0
    while pages < max_pages:
        params = dict(part="snippet", playlistId=uploads, maxResults=50)
        if page_token:
            params["pageToken"] = page_token
        data = _get("playlistItems", api_key, **params)
        for item in data.get("items", []):
            sn = item["snippet"]
            title = sn.get("title", "")
            m = _NR.search(title)
            # nur Titel der gesuchten Sitzung mit erkennbarer TOP/ZP-Struktur
            if not m or int(m.group(1)) != nr:
                continue
            if "Sitzung vom" not in title and ", TOP" not in title and ". TOP" not in title:
                continue
            mt = _TOP.search(title)
            top = mt.group(1).strip() if mt else "TOP"
            topic = mt.group(2).strip() if mt else title.split(".")[-1].strip()
            vid = sn["resourceId"]["videoId"]
            clips.append({"video_id": vid, "top": top, "topic": topic,
                          "url": f"https://www.youtube.com/watch?v={vid}"})
        page_token = data.get("nextPageToken")
        pages += 1
        if not page_token:
            break
    # Feed ist neueste→älteste; Clips einer Sitzung in TOP-Reihenfolge umdrehen
    clips.reverse()
    return clips


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        sys.exit("Aufruf: python -m pipeline.youtube_api <sitzungsnummer>")
    rows = collect_session(sys.argv[1])
    print(f"{len(rows)} Clips für Sitzung {sys.argv[1]}:")
    for c in rows:
        print(f"  {c['top']:<12} {c['topic'][:60]:<60} {c['url']}")
