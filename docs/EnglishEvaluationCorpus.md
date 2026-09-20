# Directive Drafter English Evaluation Corpus

The English evaluation corpus is reusable data for evaluating heuristic
routing and converter/fallback acquisition. It is intentionally limited to
English-language inputs and does not claim language-neutral coverage.

It records evaluation expectations. The JSONL file is not itself the
conformance authority: `CONTRACT` and `BOTH` cases identify normative behavior
through their linked conformance fixtures. The data does not apply directives
or mutate state; `context-compiler` remains responsible for grammar, policy,
authorization, contradictions, and execution.

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

Optional fields currently used are:

- `contract_ref`: the linked conformance fixture for a `CONTRACT` or `BOTH`
  case;
- `fallback_expectation`: evaluation guidance for preferred fallback outcomes;
- `notes`: additional case-specific context.

`category` and `domain` provide semantic variety and support filtering. They do
not give the Drafter authority to diagnose, recommend treatment or investments,
determine legal validity, or infer policy from domain facts.

## Classifications and paths

`CONTRACT` identifies stable heuristic behavior that another implementation
must match through a linked conformance fixture. `EVALUATION` contains
semantic or prompt/fallback quality cases, not compatibility promises. `BOTH`
marks fixture-backed contract behavior that is also retained as evaluation data.

For evaluation cases, `fallback_expectation` may record a preferred semantic
outcome, preferred canonical candidate, and acceptable outcomes. It remains
evaluation guidance even for `CONTRACT` and `BOTH` cases: promoting a case does
not make live provider or model output a compatibility requirement.

`rejected` means acquisition is terminal and must not reach fallback. This
includes ordinary prose, questions, quoted or reported commands, incomplete
directives, and compound or malformed directive-shaped input. `unknown` means
semantic interpretation remains plausible but the heuristic cannot confidently
produce one candidate; only this outcome is eligible for fallback.

## Relationship to conformance fixtures

Preprocessor fixtures under `tests/fixtures/preprocessor/` are the executable
compatibility authority. A `CONTRACT` or `BOTH` case may use `contract_ref` to
link to a fixture. Tests verify that the fixture exists, has the same input,
and agrees on outcome and canonical directive where applicable. The evaluation
data does not mirror every fixture or become a second conformance source.

The shared fixture fields are the public outcome and reason vocabulary. A
heuristic rejection fixture may also carry `internal_reason` for the Python
reference implementation, but ports consume `reason` and do not need to
reproduce that diagnostic taxonomy. Contract-marked tests identify the shared
fixture families; Python-only tests may exercise private preprocessing and
normalization entry points.

## Promoting a case to a contract

1. Add the case as `EVALUATION`.
2. Confirm that the behavior is deterministic, atomic, and safe for heuristic
   routing.
3. Add or update the executable conformance fixture.
4. Add `contract_ref` and change the case to `CONTRACT` or `BOTH`.
5. Add property coverage when the case represents a behavior family.
6. Check the acquisition specification and README for ownership-boundary drift.

Promotion makes the linked deterministic, fixture-backed heuristic behavior
stable cross-language behavior. It does not promote fallback expectations into
provider or model contracts. Keep exploratory semantic cases as `EVALUATION`
until that decision is made.

## Live evaluation runner

[`evals/runners/directive_drafter_en.py`](../evals/runners/directive_drafter_en.py)
loads the JSONL data, runs selected cases through the public `DirectiveDrafter`
path with a live fallback, and writes detailed JSONL results. It records the
actual outcome, path, source, fallback calls, and failure category. It is an
evaluation tool, not a conformance test.

The runner uses the OpenAI-compatible transport by default. Pass
`--transport litellm` with a LiteLLM provider/model identifier to use LiteLLM.
Use `--domain`, `--category`, `--case-id`, or `--limit` to select cases. The
transport and model do not change the data's expected outcomes.
