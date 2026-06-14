# 0009. Parameterized Cypher with `_SAFE` label/type gating

- **Status:** Accepted
- **Date:** 2026-06-14 (records a decision live since Neo4j ingestion)
- **Deciders:** maintainer (ma3u)
- **Source(s):** `pipeline/neo4j_loader.py:18` (`_SAFE`), `:28/:33/:41`;
  `CLAUDE.md` gotcha #5; `.claude/rules/api-conventions.md §4`

## Context

Neo4j labels and relationship types are derived from protocol data (person names, TOP titles,
verdict names). Cypher cannot parameterize labels/rel-types — they must be embedded as text,
which is a classic injection surface. Property *values* can and must be parameters.

## Decision

All data **values** are passed as Cypher **parameters** (`MERGE (n:`Label` {id: $id}) SET
n += $props`) — never string-interpolated. Every label / relationship type is validated against
`_SAFE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")` before being embedded; anything that fails the
regex is dropped. Loads are idempotent: `CREATE CONSTRAINT IF NOT EXISTS … REQUIRE n.id IS
UNIQUE`, then `MERGE` nodes, then `MERGE` rels. Dry-run is the default; real loads need `--load`.

## Consequences

- No Cypher injection from untrusted protocol text.
- A deliberate trade-off: exotic names/titles that don't match `_SAFE` get mangled or dropped
  (labels are domain-controlled, so impact is small).
- The E2E suite asserts `_SAFE` rejects unsafe labels/injection strings
  (`README.md:359`, `tests/test_e2e_negative.py`).

## Alternatives considered

- **String-interpolate labels/values directly** — rejected: Cypher injection.
- **APOC dynamic labels without gating** — rejected: still needs validation; adds a dependency.
