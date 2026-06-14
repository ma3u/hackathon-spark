#!/usr/bin/env python3
"""
Anbieter-Eval (Provider-Unabhängigkeit, ADR-0015) — prüft den AKTUELL konfigurierten
LLM-Anbieter über den portablen Teilumfang, damit ein Wechsel evidenzbasiert erfolgt.

Misst gegen den `.env`-Anbieter (Azure/Ollama/vLLM/OpenRouter/LiteLLM …):
  • Chat-JSON: Faktencheck-artiger Prompt → valides JSON? (Verdikt aus der erlaubten Skala)
  • Text2Cypher: erzeugt Cypher mit MATCH/RETURN?
  • Embeddings: Dimension == konfiguriertes EMBEDDING_DIM?
  + Latenzen. Kein Neo4j nötig.

  python scripts/llm_provider_eval.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
try:
    from dotenv import load_dotenv
    load_dotenv(REPO / ".env")
except ModuleNotFoundError:
    pass

from pipeline import llm  # noqa: E402

VERDIKTE = {"bestätigt", "teilweise", "irreführend", "falsch", "unbelegt"}


def _timed(fn):
    t = time.time()
    try:
        return fn(), None, time.time() - t
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {e}", time.time() - t


def main() -> int:
    cfg = llm.config()
    print(f"Anbieter: {cfg.provider}  ·  base_url: {cfg.base_url}")
    print(f"Chat-Modell: {cfg.chat_model}  ·  Embedding: {cfg.embed_model} ({cfg.embed_dim}d)\n")

    # 1) Chat-JSON (Faktencheck-artig)
    def chat_json():
        txt = llm.chat([
            {"role": "system", "content": "Antworte NUR mit JSON."},
            {"role": "user", "content": 'Bewerte die Aussage "Die Inflation lag 2024 bei 2 %". '
             'Gib JSON {"verdikt": <bestätigt|teilweise|irreführend|falsch|unbelegt>, '
             '"begruendung": "kurz"} zurück.'}],
            temperature=0.0, max_tokens=200, cfg=cfg)
        return json.loads(txt[txt.find("{"): txt.rfind("}") + 1])
    j, jerr, jt = _timed(chat_json)
    json_ok = bool(j) and j.get("verdikt") in VERDIKTE

    # 2) Text2Cypher
    def t2c():
        return llm.chat([
            {"role": "system", "content": "Du bist ein Cypher-Generator. Nur Cypher ausgeben."},
            {"role": "user", "content": "Neo4j-Schema: (:Person)-[:TAETIGT_AUSSAGE]->(:Aussage)"
             "-[:GEPRUEFT_ALS]->(:Faktencheck {verdikt}). Frage: Welche Aussagen sind 'falsch'?"}],
            temperature=0.0, max_tokens=200, cfg=cfg)
    c, cerr, ct = _timed(t2c)
    cypher_ok = bool(c) and "MATCH" in c.upper() and "RETURN" in c.upper()

    # 3) Embeddings
    def emb():
        return llm.embed(["Testsatz für Embedding-Dimension."], cfg=cfg)
    e, eerr, et = _timed(emb)
    dim = len(e[0]) if e else 0
    dim_ok = dim == cfg.embed_dim

    print(f"{'Test':22} {'OK':4} {'Latenz':>8}  Detail")
    print("-" * 64)
    print(f"{'Chat-JSON (Verdikt)':22} {'✓' if json_ok else '✗':4} {jt:7.2f}s  "
          f"{(j.get('verdikt') if j else jerr)}")
    print(f"{'Text2Cypher':22} {'✓' if cypher_ok else '✗':4} {ct:7.2f}s  "
          f"{(c[:50].replace(chr(10),' ') if c else cerr)}")
    print(f"{'Embedding-Dim':22} {'✓' if dim_ok else '✗':4} {et:7.2f}s  "
          f"{dim} (erwartet {cfg.embed_dim})" if not eerr else f"{'Embedding-Dim':22} ✗ {et:7.2f}s  {eerr}")
    ok = json_ok and cypher_ok and dim_ok
    print("\n" + ("✓ Anbieter geeignet (portabler Teilumfang erfüllt)." if ok
                  else "⚠ Mindestens ein Test fehlgeschlagen — vor Umstellung prüfen."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
