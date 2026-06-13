"""
DIP-Personen-IDs — Person-Knoten mit der amtlichen DIP-Personen-ID anreichern + final mergen.

Entity-Resolution Stufe 2 (nach scripts/entity_resolution.py): statt String-Heuristik die
**autoritative** Identität aus der Bundestags-DIP-API (`DIP_API_KEY`). Pro Person:
  • DIP-`id` + Deeplink (`dip.bundestag.de/person/<id>`) als Property setzen,
  • Knoten, die DIESELBE `dip_id` tragen, zusammenführen — fängt Fälle, die reiner
    Namensabgleich NICHT fängt (z. B. „Ingeborg Gräßle" ↔ amtlich „Inge Gräßle"),
  • Namensgleiche bleiben getrennt (unterschiedliche dip_id).

Auflösung konservativ: Suche per Nachname, Treffer nur bei exaktem Nachnamen; bei mehreren
Kandidaten über Vornamen-Präfix bzw. Fraktion disambiguiert, sonst NICHT geraten (unresolved).

  python scripts/dip_person_ids.py            # Dry-Run (Auflöse-Statistik + Merge-Plan)
  python scripts/dip_person_ids.py --apply     # dip_id/dip_url setzen + dip_id-Dubletten mergen
  python scripts/dip_person_ids.py --pages      # committete web/data/amt_*.json mitziehen
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

_TITEL = re.compile(r"\b(prof|dr|h\.?\s*c|ing|dipl|rer|nat|phil|jur|med|mdb|ll\.?m)\b\.?", re.I)
_ANREDE = re.compile(r"^\s*(alters|vize)?präsident(in)?\b|^\s*schriftführer(in)?\b", re.I)
_DIP = "https://search.dip.bundestag.de/api/v1/person"
CACHE = Path("/tmp/dip_person_cache.json")


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFC", (s or "").replace("\xa0", " "))
    s = re.sub(r"^[^0-9A-Za-zÀ-ÿ]+", "", s)  # führende Satzzeichen (",Vizepräsident …")
    while _ANREDE.match(s):
        s = _ANREDE.sub("", s).strip()
    s = _TITEL.sub("", s.lower())
    return " ".join(re.sub(r"[^a-zäöüß ]", " ", s).split())


def _vor_nach(label: str) -> tuple[str, str]:
    # Nachname HYPHEN-erhaltend ("Mayer-Lay" bleibt ein Token, nicht "lay").
    s = unicodedata.normalize("NFC", (label or "").replace("\xa0", " "))
    s = re.sub(r"^[^0-9A-Za-zÀ-ÿ]+", "", s)
    while _ANREDE.match(s):
        s = _ANREDE.sub("", s).strip()
    s = _TITEL.sub("", s.lower())
    toks = [t for t in re.sub(r"[^a-zäöüß \-]", " ", s).split() if t]
    return (toks[0] if toks else "", toks[-1] if toks else "")


def _vor_kompatibel(a: str, b: str) -> bool:
    """Vornamen kompatibel? (Präfix in beide Richtungen: Inge↔Ingeborg, J.↔Johann)."""
    a, b = _norm(a), _norm(b)
    if not a or not b:
        return False  # ohne Vornamen NICHT bestätigen (sonst Tina→Thorsten Rudolph)
    a0, b0 = a.split()[0], b.split()[0]
    return a0.startswith(b0) or b0.startswith(a0)


class DipResolver:
    def __init__(self, key: str):
        self.key = key
        self.by_surname: dict[str, list[dict]] = json.loads(CACHE.read_text()) if CACHE.exists() else {}

    def _fetch(self, surname: str) -> list[dict]:
        if surname in self.by_surname:
            return self.by_surname[surname]
        u = _DIP + "?" + urllib.parse.urlencode(
            {"apikey": self.key, "f.person": surname, "format": "json"})
        try:
            with urllib.request.urlopen(u, timeout=30) as r:
                docs = json.load(r).get("documents") or []
            time.sleep(0.25)  # DIP höflich behandeln
        except Exception:
            docs = []
        keep = [{"id": d.get("id"), "vorname": d.get("vorname"), "nachname": d.get("nachname"),
                 "titel": d.get("titel"), "wp": d.get("wahlperiode") or [],
                 "fraktionen": [r.get("fraktion") for r in (d.get("person_roles") or []) if r.get("fraktion")]}
                for d in docs]
        self.by_surname[surname] = keep
        return keep

    def resolve(self, label: str, fraktion: str | None) -> dict | None:
        vor, nach = _vor_nach(label)
        if not nach:
            return None
        def nmatch(c):  # Nachname exakt; Hyphen-Token gegen DIP-Nachnamen (auch enthalten)
            cn = _norm((c["nachname"] or "").replace("-", " "))
            return c.get("id") and (cn == nach.replace("-", " ") or nach.replace("-", " ") == cn)
        cands = [c for c in self._fetch(nach) if nmatch(c)]
        wp21 = [c for c in cands if 21 in (c["wp"] or [])]
        cands = wp21 or cands
        # Vorname MUSS kompatibel sein (auch bei nur einem Kandidaten) → keine Falsch-Merges.
        vm = [c for c in cands if _vor_kompatibel(vor, c["vorname"] or "")]
        if len(vm) == 1:
            return vm[0]
        if len(vm) > 1 and fraktion:  # Vor- gleich, dann Fraktion entscheiden
            fn = _norm(fraktion)
            fm = [c for c in vm if any(_norm(f) == fn for f in c["fraktionen"])]
            if len(fm) == 1:
                return fm[0]
        return None

    def save(self):
        CACHE.write_text(json.dumps(self.by_surname, ensure_ascii=False))


def _dip_url(doc: dict) -> str:
    return f"https://dip.bundestag.de/person/{doc['id']}"


def main() -> None:
    ap = argparse.ArgumentParser(description="DIP-Personen-IDs (Neo4j + Pages)")
    ap.add_argument("--apply", action="store_true", help="dip_id/url setzen + dip_id-Dubletten mergen")
    ap.add_argument("--pages", action="store_true", help="committete web/data/amt_*.json mitziehen")
    args = ap.parse_args()
    from neo4j import GraphDatabase  # lazy

    key = os.environ.get("DIP_API_KEY")
    if not key:
        print("DIP_API_KEY fehlt (.env)."); sys.exit(1)
    res = DipResolver(key)
    cfg = (os.getenv("NEO4J_URI", "bolt://localhost:7687"),
           os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "neo4j"))
    drv = GraphDatabase.driver(cfg[0], auth=(cfg[1], cfg[2]))
    with drv.session() as s:
        rows = s.run(
            "MATCH (p:Person) OPTIONAL MATCH (p)-[:MITGLIED_VON]->(f:Fraktion) "
            "OPTIONAL MATCH (p)-[r]-() "
            "RETURN p.id AS id, p.label AS label, f.label AS fraktion, count(r) AS deg").data()
        print(f"Person-Knoten: {len(rows)} — DIP auflösen …")
        resolved = {}
        for r in rows:
            doc = res.resolve(r["label"], r["fraktion"])
            if doc:
                resolved[r["id"]] = {"dip_id": str(doc["id"]), "dip_url": _dip_url(doc),
                                     "label": r["label"], "deg": r["deg"]}
        res.save()
        print(f"  aufgelöst: {len(resolved)}/{len(rows)} ({100*len(resolved)//max(1,len(rows))}%)")
        # Dubletten nach dip_id
        by_dip = collections.defaultdict(list)
        for nid, info in resolved.items():
            by_dip[info["dip_id"]].append((nid, info["label"], info["deg"]))
        merges = {k: sorted(v, key=lambda x: -x[2]) for k, v in by_dip.items() if len(v) > 1}
        print(f"  dip_id-Dubletten: {len(merges)} Cluster, {sum(len(v)-1 for v in merges.values())} Knoten")
        for k, v in merges.items():
            print(f"    • dip {k}: {v[0][1]!r} ← " + ", ".join(repr(l) for _, l, _ in v[1:]))
        if not args.apply:
            print("\nDry-Run — mit --apply ausführen.")
        else:
            for nid, info in resolved.items():
                s.run("MATCH (p:Person {id:$id}) SET p.dip_id=$d, p.dip_url=$u",
                      id=nid, d=info["dip_id"], u=info["dip_url"])
            print(f"  ✓ dip_id/dip_url auf {len(resolved)} Knoten gesetzt.")
            for k, v in merges.items():
                ordered = [x[0] for x in v]
                s.run("UNWIND $ids AS oid MATCH (n:Person {id:oid}) WITH collect(n) AS ns "
                      "CALL apoc.refactor.mergeNodes(ns,{properties:'combine',mergeRels:true}) "
                      "YIELD node RETURN node.id", ids=ordered)
            after = s.run("MATCH (p:Person) RETURN count(p) AS c").single()["c"]
            print(f"  ✓ {sum(len(v)-1 for v in merges.values())} dip-Dubletten gemerged. Person-Knoten → {after}.")
    drv.close()

    if args.pages:
        _patch_pages(resolved, merges)


def _patch_pages(resolved: dict, merges: dict) -> None:
    import glob
    web = Path(__file__).resolve().parent.parent / "web" / "data"
    # id -> canonical id (merge target = höchster Grad, [0] der sortierten Liste)
    canon = {}
    for v in merges.values():
        tgt = v[0][0]
        for nid, _, _ in v[1:]:
            canon[nid] = tgt
    files = 0
    for f in sorted(glob.glob(str(web / "amt_*.json"))):
        if "dashboard" in f:
            continue
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        changed = False
        keep = {}
        for n in d["nodes"]:
            if n.get("type") != "Person":
                continue
            info = resolved.get(n["id"])
            if info and n.get("dip_id") != info["dip_id"]:
                n["dip_id"], n["dip_url"] = info["dip_id"], info["dip_url"]
                changed = True
        # dip-Merge in der Sitzung anwenden
        idmap = {old: c for old, c in canon.items()}
        if any(n["id"] in idmap for n in d["nodes"] if n.get("type") == "Person"):
            nodes = []
            for n in d["nodes"]:
                if n.get("type") == "Person":
                    cid = idmap.get(n["id"], n["id"])
                    if cid in keep:
                        changed = True
                        continue
                    n["id"] = cid
                    keep[cid] = n
                nodes.append(n)
            seen, rels = set(), []
            for r in d["relationships"]:
                a = idmap.get(r["source_id"], r["source_id"])
                b = idmap.get(r["target_id"], r["target_id"])
                k = (a, b, r["relationship_type"])
                if a == b or k in seen:
                    continue
                seen.add(k)
                rels.append({**r, "source_id": a, "target_id": b})
            d["nodes"], d["relationships"] = nodes, rels
            d["metadata"]["node_count"] = len(nodes)
            d["metadata"]["relationship_count"] = len(rels)
        if changed:
            Path(f).write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
            files += 1
    print(f"📄 Pages: {files} Graphen mit dip_id/dip_url angereichert.")


if __name__ == "__main__":
    main()
