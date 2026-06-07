"""pytest-Fixtures für die E2E-Tests gegen das lokale Neo4j mit den echten Sitzungen."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
try:
    from dotenv import load_dotenv
    load_dotenv(REPO / ".env")
except Exception:
    pass

from neo4j import GraphDatabase  # noqa: E402

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7688")
AUTH = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", "healthdataspace"))


@pytest.fixture(scope="session")
def driver():
    try:
        d = GraphDatabase.driver(NEO4J_URI, auth=AUTH)
        d.verify_connectivity()
    except Exception as e:  # Neo4j nicht da → Neo4j-Tests überspringen (nicht failen)
        pytest.skip(f"Neo4j nicht erreichbar unter {NEO4J_URI}: {e}")
    yield d
    d.close()


@pytest.fixture
def session(driver):
    with driver.session() as s:
        yield s


def cnt_label(session, label: str) -> int:
    """Knoten mit Label zählen — über labels(n), damit Neo4j nicht 'label does not exist' warnt."""
    return session.run("MATCH (n) WHERE $l IN labels(n) RETURN count(n) AS c", l=label).single()["c"]


def one(session, cypher: str, **params):
    rec = session.run(cypher, **params).single()
    return rec[0] if rec else None
