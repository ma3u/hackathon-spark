# 0010. On-prem-capable LLM via an OpenAI-compatible endpoint

- **Status:** Accepted
- **Date:** 2026-06-14 (records a decision live since project start)
- **Deciders:** maintainer (ma3u)
- **Source(s):** `README.md:107-109,293,311-340`; `pipeline/neo4j_graphrag.py` (`llm_base_url`);
  `.env.example`; `docs/spark-und-echtdaten.md`; `docs/neo4j-echtsitzungen.md`

## Context

Session audio and voices are biometric data (Art. 9 DSGVO); citizen/parliamentary content must
not leak to a public cloud by default ("On-prem statt Cloud", `README.md:107-109`). The
reference SPARK Workflow uses LiteLLM/vLLM behind an OpenAI-compatible API.

## Decision

All LLM access goes through an **OpenAI-compatible endpoint** configured via `.env`
(`NEVER` committed). On-prem deployments point it at Ollama / vLLM; the hackathon used **Azure
AI Foundry** (Mistral-Large-3, Kimi-K2.6) as a bridge, and `text-embedding-3-large` (3072-d,
multilingual) for the native Neo4j vector index. Whisper + pyannote + the local LLM can run
entirely inside the Behördennetz; voice embeddings are created only with a legal basis and
otherwise discarded per session.

## Consequences

- Swapping cloud ↔ on-prem is a config change, not a code change.
- Secrets stay in `.env` (gitignored; guarded by `settings.json` deny/ask + the PreToolUse
  hook); no hardcoded keys.
- Model choice is comparable: `scripts/graphrag_compare.py` benchmarks Mistral-Large-3 vs.
  Kimi-K2.6 over the same graph.

## Alternatives considered

- **Hardwire a single cloud SDK** — rejected: breaks on-prem/DSGVO posture and the SPARK
  alignment.
- **No LLM (rules only)** — rejected for real content: rule-based checking is unreliable on real
  speech (ADR-0007).
