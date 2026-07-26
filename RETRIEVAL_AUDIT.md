# Retrieval Quality Audit

Date: 2026-07-26

## Scope

- Read-only sampling through the `qiqi` identity.
- No production memory was edited, relabeled, archived, or created.
- Results in this document are anonymized and contain no memory text or credentials.

## Evidence

Twelve paired queries covered technical facts, procedures, rules, relationships,
events, and reflections. Each pair used a title/tag phrase and a natural-language
paraphrase.

- Technical, relationship, event, and reflection memories were generally
  recoverable after paraphrasing.
- A rule question failed to retrieve the two canonical rule memories and instead
  returned emotionally adjacent memories.
- A procedural question ranked activity and overview memories above the actual
  procedure.
- Exact low-result searches could receive unrelated random surfacing results.

Field traces identified the main ranking defect: tag and domain fields used the
maximum `partial_ratio` across their values. A single short generic value inside a
long question could therefore score 100. Broad metadata then outweighed the more
specific title or content signal.

Legacy metadata amplified the defect:

- Many older titles are opaque bucket identifiers.
- `subject` is useful but sparse in legacy memories.
- `summary` contributed no score in the sampled traces.
- Broad tag expansion produced many weakly discriminative tags.

## Vector Status

The production embedding engine reports enabled with model
`gemini-embedding-001`, but 0 of 471 buckets currently have embeddings. A
read-only vector probe returned no vector results. Vector search is therefore not
contributing to retrieval at present.

Do not backfill embeddings until keyword retrieval is stable and a valid,
budgeted embedding provider is selected. A full backfill would generate vectors
for the existing corpus and should be treated as an explicit cost decision.

## Implemented Locally

1. Tag/domain fuzzy scores are length-adjusted and combined with meaningful query
   token coverage. One short generic item can no longer score 100 for a long
   question.
2. Explicit search no longer appends random memories by default. Associative
   drift remains available through `matching.random_surfacing_on_search`.
3. New-memory prompts request 3-6 discriminative tags and at most 1-2 necessary
   aliases instead of 10-15 broad expansions.
4. New-memory prompts forbid credentials in ordinary memory fields.
5. MCP memory output masks labeled secrets, bearer tokens, and credentials
   embedded in URLs. Stored memory and the human review UI remain unchanged.

## Follow-up

- Deploy and rerun the same paired queries against production.
- Add a read-only self-review queue so each identity can approve metadata changes
  to its own legacy memories.
- Add `memory_kind` and subject coverage reporting before considering any legacy
  metadata cleanup.
- Choose an embedding provider only after measuring the remaining misses that
  lexical retrieval cannot solve.
