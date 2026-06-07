"""
NEGATIVE E2E-Tests — der Import wehrt ungültige Eingaben ab, verletzt keine Invarianten und
liefert bei nicht vorhandenen Daten leere Ergebnisse (kein „Erfinden"). ~80 Fälle.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

import _realdata as R  # noqa: F401  (stellt sys.path + REPO sicher)
from conftest import cnt_label, one
from pipeline.neo4j_loader import _SAFE, namespace_graph
from pipeline.diarize import resolve_speaker

# ── 1) Cypher-Sicherheit: _SAFE lässt nur saubere Label-/Reltyp-Namen durch ───
BAD_LABELS = [
    "", " ", "1Label", "Label-1", "Label Space", "Label;", "Label`", "a b",
    "Person DROP", "öä", "Label.Name", "Label/x", "MATCH(n)", "`inj`", 'Label"',
    "Label'", "Label{}", "Label()", "123", "-x", "x-", "DROP TABLE", "Über",
    "Label\nINJECT", "Label\t",
]
GOOD_LABELS = ["Person", "Tagesordnungspunkt", "AkustischesEreignis", "_private", "Node123"]


@pytest.mark.parametrize("bad", BAD_LABELS)
def test_safe_rejects_unsafe_label(bad):
    assert _SAFE.match(bad) is None, f"_SAFE ließ unsicheres Label durch: {bad!r}"


@pytest.mark.parametrize("good", GOOD_LABELS)
def test_safe_accepts_valid_label(good):
    assert _SAFE.match(good) is not None


# ── 2) Namespacing: sitzungsspezifische IDs präfixt, geteilte Entitäten global ─
_G = {"metadata": {}, "nodes": [
    {"id": "person_x", "type": "Person", "label": "X"},
    {"id": "fraktion_y", "type": "Fraktion", "label": "Y"},
    {"id": "norm_1", "type": "Norm", "label": "N"},
    {"id": "top_1", "type": "Tagesordnungspunkt", "label": "T"},
    {"id": "redebeitrag_0", "type": "Redebeitrag", "label": "R"},
    {"id": "segment_0", "type": "Transkriptsegment", "label": "S"},
    {"id": "ereignis_0", "type": "AkustischesEreignis", "label": "E"},
], "relationships": [
    {"source_id": "person_x", "target_id": "redebeitrag_0", "relationship_type": "HAT_REDEBEITRAG"},
    {"source_id": "redebeitrag_0", "target_id": "segment_0", "relationship_type": "BELEGT_DURCH"},
]}
_NS = namespace_graph(_G, "SID")
_IDMAP = {o["id"]: n["id"] for o, n in zip(_G["nodes"], _NS["nodes"])}


@pytest.mark.parametrize("old_id", ["person_x", "fraktion_y", "norm_1"])
def test_namespace_keeps_shared_global(old_id):
    assert _IDMAP[old_id] == old_id  # Person/Fraktion/Norm bleiben sitzungsübergreifend gleich


@pytest.mark.parametrize("old_id", ["top_1", "redebeitrag_0", "segment_0", "ereignis_0"])
def test_namespace_prefixes_session_nodes(old_id):
    assert _IDMAP[old_id] == f"SID::{old_id}"


def test_namespace_rewires_relationship_targets():
    rel = next(r for r in _NS["relationships"] if r["relationship_type"] == "BELEGT_DURCH")
    assert rel["source_id"] == "SID::redebeitrag_0" and rel["target_id"] == "SID::segment_0"


def test_namespace_rel_from_shared_to_session():
    rel = next(r for r in _NS["relationships"] if r["relationship_type"] == "HAT_REDEBEITRAG")
    assert rel["source_id"] == "person_x" and rel["target_id"] == "SID::redebeitrag_0"


# ── 3) Keine automatischen Faktencheck-Verdikte über reale Personen ───────────
def test_no_faktencheck_nodes(session):
    assert cnt_label(session, "Faktencheck") == 0


def test_no_quelle_nodes(session):
    assert cnt_label(session, "Quelle") == 0


def test_no_geprueft_als_edges(session):
    n = one(session, "MATCH ()-[r]->() WHERE type(r)='GEPRUEFT_ALS' RETURN count(r)")
    assert n == 0


# ── 4) Nicht vorhandene Daten → leeres Ergebnis (kein Halluzinieren) ──────────
ABSENT_NAMES = [
    "Nonexistent Persona", "Foo Bar McTest", "Erika Mustermann", "Max Niemand",
    "Captain Nemo", "Sherlock Holmes", "Donald Duck", "John Doe", "Jane Roe",
    "Zzz Qqq", "Test User", "Niemand Hier", "Kein Abgeordneter", "Frau X", "Herr Y",
]
ABSENT_TERMS = ["zzzqqq", "xyzzyabc", "qwertzuiopx", "asdfghjklx", "mnbvcxyx",
                "flumpwozzle", "blarghxyz", "zzxxccvvbb", "qpwoeiruty", "lkjhgfdsax"]


@pytest.mark.parametrize("name", ABSENT_NAMES)
def test_absent_person_returns_empty(session, name):
    assert one(session, "MATCH (p:Person {label:$name}) RETURN count(p)", name=name) == 0


@pytest.mark.parametrize("term", ABSENT_TERMS)
def test_absent_fulltext_returns_empty(session, term):
    n = one(session, "CALL db.index.fulltext.queryNodes('seg_volltext', $t) YIELD node "
                     "RETURN count(node)", t=term)
    assert n == 0


# ── 5) Robuste XML-Verarbeitung ───────────────────────────────────────────────
MALFORMED = ["", "kein xml", "<a>", "<a><b></a>", "<<>>", "{json:true}"]
EMPTY_BUT_VALID = [
    '<?xml version="1.0"?><dbtplenarprotokoll wahlperiode="21" sitzung-nr="99"/>',
    '<?xml version="1.0"?><dbtplenarprotokoll wahlperiode="21" sitzung-nr="99">'
    '<sitzungsverlauf></sitzungsverlauf></dbtplenarprotokoll>',
    '<?xml version="1.0"?><dbtplenarprotokoll wahlperiode="21" sitzung-nr="99">'
    '<sitzungsverlauf><tagesordnungspunkt top-id="X"></tagesordnungspunkt></sitzungsverlauf>'
    '</dbtplenarprotokoll>',
    '<?xml version="1.0"?><dbtplenarprotokoll wahlperiode="21" sitzung-nr="99">'
    '<anlagen></anlagen></dbtplenarprotokoll>',
]


@pytest.mark.parametrize("content", MALFORMED)
def test_malformed_xml_raises_cleanly(tmp_path, content):
    from pipeline import bundestag_xml
    f = tmp_path / "bad.xml"
    f.write_text(content, encoding="utf-8")
    with pytest.raises(ET.ParseError):  # sauberer Parserfehler, kein undefinierter Absturz
        bundestag_xml.parse_plenarprotokoll(f)


@pytest.mark.parametrize("content", EMPTY_BUT_VALID)
def test_empty_valid_xml_yields_empty_protocol(tmp_path, content):
    from pipeline import bundestag_xml
    f = tmp_path / "empty.xml"
    f.write_text(content, encoding="utf-8")
    p = bundestag_xml.parse_plenarprotokoll(f)
    assert len(p.redebeitraege) == 0 and len(p.tops) == 0


# ── 6) Unbekanntes Sprecher-Label → sauberer Fallback (kein Crash) ────────────
def test_resolve_unknown_speaker_empty_map():
    r = resolve_speaker("SPEAKER_99", {})
    assert r["name"] == "Unbekannt (SPEAKER_99)" and r["fraktion"] is None


def test_resolve_unknown_speaker_other_map():
    r = resolve_speaker("SPEAKER_99", {"SPEAKER_00": {"name": "A", "rolle": "x", "fraktion": None}})
    assert "Unbekannt" in r["name"]


# ── 7) Leere Segmente werden nicht embeddet ───────────────────────────────────
def test_empty_segments_have_no_embedding(session):
    n = one(session, "MATCH (n:Transkriptsegment) WHERE n.text='' AND n.embedding IS NOT NULL "
                     "RETURN count(n)")
    assert n == 0
