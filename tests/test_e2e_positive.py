"""
POSITIVE E2E-Tests — die echten Bundestagssitzungen sind korrekt importiert und im
Neo4j-Graphen vollständig & belegbar abfragbar. ~140 reale Fälle (Parser + Neo4j).

Voraussetzung Neo4j-Tests: Sitzungen geladen
  (`NEO4J_URI=bolt://localhost:7688 python scripts/load_real_sessions.py`).
"""

from __future__ import annotations

import pytest

import _realdata as R
from conftest import cnt_label, one

SESSIONS = R.sessions()
SPEAKERS = R.speaker_sample(50)          # 50 echte Redner:innen
SPEAKERS_RB = R.speaker_sample(30)       # 30 für Redebeitrag-Provenienz
REACTIONS = R.reaction_sample(15)        # 15 Saalreaktions-Typen (Stichprobe)
EXPECTED_LABELS = ["Sitzung", "Person", "Fraktion", "Tagesordnungspunkt",
                   "Redebeitrag", "Aussage", "AkustischesEreignis", "Transkriptsegment"]

# ── Parser-Ebene (kein Neo4j) ────────────────────────────────────────────────

@pytest.mark.parametrize("name", SPEAKERS)
def test_parser_speaker_has_valid_name(name):
    assert name and "Unbekannt" not in name and len(name) > 2


@pytest.mark.parametrize("typ", REACTIONS)
def test_parser_reaction_type_allowed(typ):
    assert typ in R.ALLOWED_SUBTYPES


@pytest.mark.parametrize("s", SESSIONS, ids=[s["sid"] for s in SESSIONS])
def test_parser_session_nonempty(s):
    assert s["tops"] > 0 and s["reden"] > 0 and s["reaktionen"] > 0


# ── Neo4j-Ebene (echte geladene Daten) ───────────────────────────────────────

@pytest.mark.parametrize("label", EXPECTED_LABELS)
def test_node_type_present(session, label):
    assert cnt_label(session, label) > 0


@pytest.mark.parametrize("s", SESSIONS, ids=[s["nr"] for s in SESSIONS])
def test_session_landed(session, s):
    n = one(session, "MATCH (x:Sitzung {sitzung_nr:$nr}) RETURN count(x)", nr=s["nr"])
    assert n == 1, f"Sitzung {s['nr']} nicht (eindeutig) geladen: {n}"


@pytest.mark.parametrize("s", SESSIONS, ids=[s["nr"] for s in SESSIONS])
def test_session_reden_count(session, s):
    n = one(session, "MATCH (:Sitzung {sitzung_nr:$nr})-[:HAT_TOP]->(:Tagesordnungspunkt)"
                     "<-[:ZU_TOP]-(r:Redebeitrag) RETURN count(DISTINCT r)", nr=s["nr"])
    assert n == s["reden"], f"Sitzung {s['nr']}: Neo4j {n} ≠ Parser {s['reden']}"


@pytest.mark.parametrize("s", SESSIONS, ids=[s["nr"] for s in SESSIONS])
def test_session_reaktionen_count(session, s):
    n = one(session, "MATCH (:Sitzung {sitzung_nr:$nr})-[:HAT_TOP]->(:Tagesordnungspunkt)"
                     "-[:HAT_REAKTION]->(e:AkustischesEreignis) RETURN count(DISTINCT e)", nr=s["nr"])
    assert n == s["reaktionen"], f"Sitzung {s['nr']}: Neo4j {n} ≠ Parser {s['reaktionen']}"


@pytest.mark.parametrize("s", SESSIONS, ids=[s["nr"] for s in SESSIONS])
def test_session_tops_count(session, s):
    n = one(session, "MATCH (:Sitzung {sitzung_nr:$nr})-[:HAT_TOP]->(t:Tagesordnungspunkt) "
                     "RETURN count(t)", nr=s["nr"])
    assert n == s["tops"]


@pytest.mark.parametrize("name", SPEAKERS)
def test_speaker_node_in_neo4j(session, name):
    n = one(session, "MATCH (p:Person {label:$name}) RETURN count(p)", name=name)
    assert n >= 1, f"Person fehlt im Graph: {name}"


@pytest.mark.parametrize("name", SPEAKERS_RB)
def test_speaker_has_redebeitrag_with_provenance(session, name):
    # echte Redner haben ≥1 Redebeitrag, und JEDER Redebeitrag ist bis zum Segment belegt
    total = one(session, "MATCH (p:Person {label:$name})-[:HAT_REDEBEITRAG]->(r:Redebeitrag) "
                         "RETURN count(r)", name=name)
    unbelegt = one(session, "MATCH (p:Person {label:$name})-[:HAT_REDEBEITRAG]->(r:Redebeitrag) "
                            "WHERE NOT (r)-[:BELEGT_DURCH]->(:Transkriptsegment) RETURN count(r)",
                   name=name)
    assert total >= 1 and unbelegt == 0, f"{name}: {total} Reden, davon {unbelegt} ohne Beleg"


def test_embeddings_present(session):
    n = one(session, "MATCH (n:Transkriptsegment) WHERE n.embedding IS NOT NULL RETURN count(n)")
    assert n > 0


def test_embedding_dimension(session):
    dim = one(session, "MATCH (n:Transkriptsegment) WHERE n.embedding IS NOT NULL "
                       "RETURN size(n.embedding) LIMIT 1")
    assert dim == 3072


def test_vector_index_online(session):
    st = one(session, "SHOW INDEXES YIELD name, state WHERE name='seg_embedding' RETURN state")
    assert st == "ONLINE"
