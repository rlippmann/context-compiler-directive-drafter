# Directive Drafter English Evaluation Corpus

The English evaluation corpus is reusable data for evaluating heuristic
routing and converter/fallback acquisition. It is intentionally limited to
English-language inputs and does not claim language-neutral coverage.

The corpus proposes evaluation expectations; it does not apply directives or
mutate authoritative state. `context-compiler` remains responsible for grammar
validity, applicability, authorization, contradictions, and state transitions.

## Location and format

The data lives in
[`corpus/english/directive-drafter-en.jsonl`](../corpus/english/directive-drafter-en.jsonl).
Each line is one JSON object. JSONL keeps the data easy to filter by language,
domain, category, or classification without making it executable code.

Required fields:

- `id`: unique stable case identifier;
- `language`: `en` for this initial corpus;
- `classification`: `CONTRACT`, `EVALUATION`, or `BOTH`;
- `input`: one English user message;
- `expected_outcome`: `directive`, `no_directive`, or `unknown`;
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
policies, health, finance, and legal drafting. The domain labels provide
semantic diversity only; they do not give the Drafter authority to diagnose,
recommend treatment or investments, determine legal validity, or infer policy
from domain facts.

## Classifications and paths

`CONTRACT` identifies stable heuristic behavior that another implementation
must match. `EVALUATION` identifies semantic or prompt/fallback quality data
that is not a compatibility promise. `BOTH` is reserved for stable heuristic
anchors that are also useful for converter evaluation.

For evaluation cases, `fallback_expectation` may record a preferred semantic
outcome, preferred canonical candidate, and acceptable abstentions. Fallback
behavior is not treated as a hard contract unless the case is explicitly
promoted.

`no_directive` means the heuristic has positive evidence that the complete
input is confidently non-directive. `unknown` means the heuristic cannot
confidently produce one candidate and cannot confidently classify the input as
non-directive; an eligible host may send it to fallback. Obvious
multi-sentence input remains `no_directive` because sentence segmentation
belongs to the host.

## Conformance relationship

Existing heuristic fixtures under `tests/fixtures/preprocessor/` remain the
executable compatibility authority. A corpus CONTRACT/BOTH case may use
`contract_ref` to name a fixture that adds useful semantic value. Corpus tests
verify that the referenced fixture exists, has the same input, and agrees on
outcome and canonical directive where applicable. The corpus does not mirror
every fixture and does not become a second conformance source.

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
