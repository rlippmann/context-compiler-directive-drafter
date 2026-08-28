# Directive Drafter English Evaluation Corpus

The English evaluation corpus is reusable data for evaluating heuristic
routing and converter/fallback acquisition. It is intentionally limited to
English-language inputs and does not claim language-neutral coverage.

The corpus proposes evaluation expectations; it does not apply directives or
mutate authoritative state. `context-compiler` remains responsible for grammar
validity, applicability, authorization, contradictions, and state transitions.

## Location and format

The data lives in
[`evals/corpus/english/directive-drafter-en.jsonl`](../evals/corpus/english/directive-drafter-en.jsonl).
Each line is one JSON object. JSONL keeps the data easy to filter by language,
domain, category, or classification without making it executable code.

Required fields:

- `id`: unique stable case identifier;
- `language`: `en` for this initial corpus;
- `classification`: `CONTRACT`, `EVALUATION`, or `BOTH`;
- `input`: one English user message;
- `expected_outcome`: `directive`, `rejected`, or `unknown`;
- `expected_directive`: canonical directive text, or `null`;
- `expected_path`: `heuristic`, `fallback`, or `either`;
- `category` and `domain`;
- `rationale`.

`expected_directive` contains canonical text only. Tests derive its grammar
kind and operands through Core rather than duplicating those fields in the
corpus.

Optional metadata supports later review and human-in-the-loop workflows:
`notes`, `contract_ref`, `tags`, `source`, `requires_context`,
`review_status`, `fallback_expectation`, `provenance`, and `hitl_accepted`.

The current English corpus spans software development, food preferences,
writing style, project workflow, travel planning, everyday preferences and
policies, health, finance, legal drafting, household and home life, education
and learning, accessibility, communication etiquette, shopping and product
preferences, scheduling and time management, media and content preferences,
and family and social planning. The domain labels provide semantic diversity
only; they do not give the Drafter authority to diagnose, recommend treatment
or investments, determine legal validity, or infer policy from domain facts.

## Classifications and paths

`CONTRACT` identifies stable heuristic behavior that another implementation
must match. `EVALUATION` identifies semantic or prompt/fallback quality data
that is not a compatibility promise. `BOTH` is reserved for stable heuristic
anchors that are also useful for converter evaluation.

For evaluation cases, `fallback_expectation` may record a preferred semantic
outcome, preferred canonical candidate, and acceptable abstentions. Fallback
behavior is not treated as a hard contract unless the case is explicitly
promoted.

`rejected` means acquisition is terminal and must not reach fallback. This
includes ordinary prose, questions, quoted or reported commands, incomplete
directives, and compound or malformed directive-shaped input. `unknown` means
semantic interpretation remains plausible but the heuristic cannot confidently
produce one candidate; only this outcome is eligible for fallback.

## Conformance relationship

Existing heuristic fixtures under `tests/fixtures/preprocessor/` remain the
executable compatibility authority. A corpus CONTRACT/BOTH case may use
`contract_ref` to name a fixture that adds useful semantic value. Corpus tests
verify that the referenced fixture exists, has the same input, and agrees on
outcome and canonical directive where applicable. The corpus does not mirror
every fixture and does not become a second conformance source.

The shared fixture fields are the public outcome and reason vocabulary. A
heuristic rejection fixture may also carry `internal_reason` for the Python
reference implementation, but ports consume `reason` and do not need to
reproduce that diagnostic taxonomy. Contract-marked tests identify the shared
fixture families; Python-only tests may exercise private preprocessing and
normalization entry points.

## Promotion workflow

1. Add a new behavior as `EVALUATION`.
2. Review whether it is deterministic, atomic, and safe for heuristic routing.
3. If promoted, implement the heuristic behavior and add or update the
   executable conformance fixture.
4. Add `contract_ref` and promote the corpus case to `CONTRACT` or `BOTH`.
5. Add property coverage when the case represents a behavior family.
6. Review the acquisition specification and README for ownership-boundary
   drift.

Promotion makes the heuristic outcome public cross-language behavior. The
corpus therefore keeps exploratory semantic cases separate from stable
fixture-backed behavior.
