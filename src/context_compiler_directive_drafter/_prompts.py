"""Converter prompt accessors for directive-drafter integrations."""

from dataclasses import dataclass
from functools import lru_cache
from types import MappingProxyType

from context_compiler.grammar import (
    CanonicalDirective,
    DirectiveKind,
    DirectiveMetadata,
    get_directive_metadata,
)

from .constants import _PREPROCESSOR_NO_DIRECTIVE_SENTINEL


def _placeholder(name: str) -> str:
    return f"<{name.replace('_', ' ')}>"


def _sample_operand(name: str) -> str:
    return f"sample {name.replace('_', ' ')}"


def _render_canonical_form(metadata: DirectiveMetadata) -> str:
    sample_operands = MappingProxyType(
        {name: _sample_operand(name) for name in metadata.operand_names}
    )
    rendered = CanonicalDirective(kind=metadata.kind, operands=sample_operands).text
    for name, sample in sample_operands.items():
        rendered = rendered.replace(sample, _placeholder(name))
    return rendered


def _canonical_operation(kind: DirectiveKind) -> str:
    metadata = next(metadata for metadata in get_directive_metadata() if metadata.kind is kind)
    canonical_form = _render_canonical_form(metadata)
    operation = canonical_form.removesuffix(f" {_placeholder(metadata.operand_names[0])}")
    if kind in {DirectiveKind.SET_PREMISE, DirectiveKind.CHANGE_PREMISE}:
        operation = operation.removesuffix(" to")
    return operation


def _render_directive(kind: DirectiveKind, operand_values: tuple[str, ...]) -> str:
    metadata = next(metadata for metadata in get_directive_metadata() if metadata.kind is kind)
    operands = MappingProxyType(dict(zip(metadata.operand_names, operand_values, strict=True)))
    return CanonicalDirective(kind=kind, operands=operands).text


_USE_OPERATION = f"`{_canonical_operation(DirectiveKind.USE_ITEM)}`"
_PROHIBIT_OPERATION = f"`{_canonical_operation(DirectiveKind.PROHIBIT_ITEM)}`"
_SET_PREMISE_OPERATION = f"`{_canonical_operation(DirectiveKind.SET_PREMISE)}`"
_CHANGE_PREMISE_OPERATION = f"`{_canonical_operation(DirectiveKind.CHANGE_PREMISE)}`"

_DIRECTIVE_CATEGORY_LINES = """Directive categories:
- Premise directives record contextual or background state that is not naturally
  represented as a policy choice.
- Policy directives manage named policy items.
- Administrative directives change compiler-managed state."""

_PREMISE_POLICY_GUIDANCE = (
    f"""What premise vs policy means:
- Prefer policy when the user's state can be faithfully represented as {_USE_OPERATION},
  {_PROHIBIT_OPERATION}, removal, replacement, or another policy operation.
- User-facing preferences and constraints are policies even when they are
  persistent, behavioral, stylistic, or user-specific.
- Use premise only for governing context that cannot naturally be represented
  as policy without distorting the user's meaning, such as `the intended
  audience is senior management`. Do not use premise merely for arbitrary
  facts, observations, evaluations, external rules, or third-party conditions.
- Do not infer {_SET_PREMISE_OPERATION} or {_CHANGE_PREMISE_OPERATION} casually from natural-"""
    f"""language
  preferences. {_CHANGE_PREMISE_OPERATION} should be uncommon.
- Declarative statements about user-owned wants, preferences, needs,
  requirements, constraints, or equipment may establish policy when {_USE_OPERATION} or
  {_PROHIBIT_OPERATION} naturally preserves their meaning.
- Clear user-owned `need`, `require`, and `must have` statements should
  normally become {_USE_OPERATION} or {_PROHIBIT_OPERATION} when that preserves their meaning;
  ownership and semantic role still matter.
- Declarative requirements, preferences, and constraints may establish policy;
  imperative wording or explicit persistence language is not required.
- This applies to the user's own policy, not to another person's preference or
  constraint, an external rule, or a general observation or evaluation.
- Descriptive or evaluative wording such as `would be better`, `is easier`, or
  `is prohibited` does not by itself establish the user's policy.
- If the input is already a valid canonical directive, preserve the operation
  explicitly selected by the user. Do not remap it to another operation."""
)


@dataclass(frozen=True)
class _AcquisitionExample:
    kind: DirectiveKind
    user_input: str
    operand_values: tuple[str, ...]


@dataclass(frozen=True)
class _ScopePayloadContrast:
    kind: DirectiveKind
    user_input: str
    operand_values: tuple[str, ...]
    truncated_operand_values: tuple[str, ...]


_SCOPE_PAYLOAD_CONTRASTS: tuple[_ScopePayloadContrast, ...] = (
    _ScopePayloadContrast(
        kind=DirectiveKind.USE_ITEM,
        user_input="Oat milk is required for this recipe",
        operand_values=("oat milk for this recipe",),
        truncated_operand_values=("oat milk",),
    ),
    _ScopePayloadContrast(
        kind=DirectiveKind.PROHIBIT_ITEM,
        user_input="Scented candles are prohibited in this building",
        operand_values=("scented candles in this building",),
        truncated_operand_values=("scented candles",),
    ),
)


_USE_DOCKER = _render_directive(DirectiveKind.USE_ITEM, ("docker",))
_PROHIBIT_PEANUTS = _render_directive(DirectiveKind.PROHIBIT_ITEM, ("peanuts",))
_USE_ALMONDS = _render_directive(DirectiveKind.USE_ITEM, ("almonds",))

_BEHAVIOR_EXAMPLES = f"""Examples of ordinary conversation that must not become directives:
User: can you help with lunch?
        Output: {_PREPROCESSOR_NO_DIRECTIVE_SENTINEL}

User: Docker seems popular in this repo.
Output: {_PREPROCESSOR_NO_DIRECTIVE_SENTINEL}

User: What does clear state do?
Output: {_PREPROCESSOR_NO_DIRECTIVE_SENTINEL}

Examples of directive discussion or unresolved multi-directive input where you must not guess:
User: {_USE_DOCKER}?
Output: {_PREPROCESSOR_NO_DIRECTIVE_SENTINEL}

User: He said "{_USE_DOCKER}".
Output: {_PREPROCESSOR_NO_DIRECTIVE_SENTINEL}

User: {_PROHIBIT_PEANUTS} and {_USE_ALMONDS}
Output: {_PREPROCESSOR_NO_DIRECTIVE_SENTINEL}"""

_PROMPT_SUFFIX = f"""Your task:
- Read one user message.
- If the message clearly establishes one state change that can be represented
  by a canonical directive, produce exactly one candidate directive in
  canonical form.
- This is a non-authoritative draft: propose a plausible single candidate when
  the meaning is naturally representable, but do not guess unsupported intent.
- Otherwise output exactly `{_PREPROCESSOR_NO_DIRECTIVE_SENTINEL}`.

Output contract:
- A single candidate directive line in canonical form, or
- exactly `{_PREPROCESSOR_NO_DIRECTIVE_SENTINEL}`

Output rules:
- Output exactly one line.
- Do not explain.
- Do not add quotes, labels, markdown, JSON, or extra text.
- Do not output multiple directives.

Conversion rules:
- Only encode information explicitly present in the user request.
- Prefer a policy operation when it faithfully represents a user preference,
  requirement, constraint, or requested replacement.
- Create the smallest valid directive payload that preserves every explicit
  operand, qualifier, polarity, and scope in the request.
- If you select a directive operation, preserve the complete semantic payload
  exactly, including all qualifiers and scope. Remove only acquisition framing
  required to express the canonical operation; never drop or generalize the
  remaining source text.
- Preserve the user's semantic nouns and wording as faithfully as possible.
- Do not paraphrase, substitute synonyms, invent alternatives, generalize
  scope, drop meaningful qualifiers, or change the operation merely to make
  the output canonical. If one canonical directive cannot preserve the
  meaning, abstain instead of omitting or broadening the lost content.
- A positive requirement that naturally maps to {_USE_OPERATION} must remain positive;
  do not invent an antonym, opposite property, or unstated alternative to
  express it as {_PROHIBIT_OPERATION}.
- For replacement or prohibition requests, preserve all stated operands and
  the requested operation; narrowing is exceptional and allowed only when a
  specific acquisition rule authorizes it.
- Do not guess missing intent, omitted items, hidden context, or unstated replacements.
- Do not infer semantic intent from directive payload contents.
- Do not require imperative wording or explicit persistence language when a
  declarative preference, requirement, or constraint clearly establishes policy.
- Use a bounded rewrite when one clear natural-language request maps to one
  canonical policy operation without changing its meaning; literal canonical
  syntax is not required for that case.
- Use premise only for contextual or factual background that is not naturally
  expressible as policy; do not use it merely for persistent or stylistic
  behavior, or for arbitrary facts, observations, evaluations, external rules,
  or third-party conditions.
- Another person's preference, constraint, capability, or condition does not
  automatically become the user's policy.
- Preserve the operation in an already valid canonical directive, even if another
  operation might seem semantically preferable.
- Do not invent directives from ordinary conversation.
- If the input is ordinary conversation, quoted or reported directive text,
  directive discussion, or a mixed request you cannot safely reduce to one
  directive, do not extract only the directive-looking fragment; output
  `{_PREPROCESSOR_NO_DIRECTIVE_SENTINEL}`.
- Do not combine independent payloads joined by `and` into one broader
  directive. If a request contains multiple state changes or a state change
  plus a separate explanation, lookup, comparison, or other task, abstain.
- Do not reinterpret a comparison, explanation, lookup, or analysis as a
  replacement. Use `instead of` only when the input actually expresses
  replacement, such as switching or replacing one item with another.
- Treat `maybe`, `perhaps`, `might`, and similarly tentative or evaluative
  wording as unresolved when they do not clearly establish a user-owned
  policy. Do not promote a tentative suggestion merely because its payload
  could be rendered canonically; this does not override clear `like`, `want`,
  `need`, `hate`, or `would rather` preferences.
- Do not resolve an unstated referent such as `that`, `it`, or `the other one`
  into a policy payload. If the policy item is not identified by the input,
  abstain.

When to output `{_PREPROCESSOR_NO_DIRECTIVE_SENTINEL}`:
- Ordinary conversation, questions, explanations, or comments.
- Requests that do not ask to change compiler-managed behavior.
- Questions or discussion about directives rather than a request to change behavior.
- Requests that remain too ambiguous to draft as one directive.
- Inputs containing multiple directive requests.
- Quoted, cited, reported, example, or discussed directive text rather than a direct request."""

_STRUCTURED_PROMPT_SUFFIX = f"""Your task:
- Read one user message.
- Classify it as `directive` only when it clearly establishes one atomic state
  change that can be represented by a canonical directive.
- If it is a directive, put exactly one canonical directive candidate in
  `output`.
- Otherwise classify it as `rejected` and set `output` to null.

Conversion rules:
- This is a non-authoritative draft. Propose a plausible single candidate when
  the meaning is naturally representable, but do not guess unsupported intent.
- Prefer a policy operation when it faithfully represents a user preference,
  requirement, constraint, or requested replacement.
- Preserve every explicit operand, qualifier, polarity, modifier, and scope;
  preserve semantic nouns and wording as faithfully as possible.
- If you select a directive operation, preserve the complete semantic payload
  exactly, including all qualifiers and scope. Remove only acquisition framing
  required to express the canonical operation; never drop or generalize the
  remaining source text.
- Do not paraphrase, substitute synonyms, invent alternatives, generalize
  scope, drop meaningful qualifiers, change operations, or lose replacement
  operands. If one canonical directive cannot preserve the meaning, reject it.
- A positive requirement that naturally maps to {_USE_OPERATION} remains positive; do not
  invent an antonym or unstated alternative for {_PROHIBIT_OPERATION}.
- Do not infer missing intent, unstated replacements, or unresolved referents.
- Clear user-owned preferences, wants, needs, requirements, and constraints may
  become policy; third-party preferences or constraints do not become the
  user's policy automatically.
- Use premise only for governing context that cannot naturally be represented
  as policy. It is not a catch-all for facts, observations, evaluations,
  external rules, or third-party conditions.
- Use bounded natural-language rewrites when one clear policy candidate exists.
- Do not reject a clear bounded request merely because it uses ordinary wording
  such as `provide`, `keep`, `avoid`, `replace`, or `switch`; when it maps
  faithfully to one policy operation, draft that candidate.
- Do not extract a directive fragment from mixed intent, combine independent
  payloads, or reinterpret comparison, explanation, lookup, or analysis as
  replacement. Preserve clear replacement semantics.
- Treat tentative language as unresolved when it does not clearly establish
  user-owned policy. Reject incomplete payloads and unresolved deictic terms.
- Preserve the operation of an already valid canonical directive.

Reject ordinary conversation, questions, directive discussion, quoted or
reported directive text, multiple state changes, mixed requests that cannot be
represented faithfully as one directive, and any request whose meaning would
be lost by canonicalization."""


_DIRECTIVE_KIND_TO_CATEGORY: dict[DirectiveKind, str] = {
    DirectiveKind.SET_PREMISE: "Premise",
    DirectiveKind.CHANGE_PREMISE: "Premise",
    DirectiveKind.USE_ITEM: "Policy",
    DirectiveKind.PROHIBIT_ITEM: "Policy",
    DirectiveKind.REMOVE_POLICY: "Policy",
    DirectiveKind.REPLACE_USE: "Policy",
    DirectiveKind.CLEAR_PREMISE: "Administrative",
    DirectiveKind.RESET_POLICIES: "Administrative",
    DirectiveKind.CLEAR_STATE: "Administrative",
}

_POSITIVE_ACQUISITION_EXAMPLES: tuple[_AcquisitionExample, ...] = (
    _AcquisitionExample(
        kind=DirectiveKind.USE_ITEM,
        user_input="please use docker",
        operand_values=("docker",),
    ),
    _AcquisitionExample(
        kind=DirectiveKind.REPLACE_USE,
        user_input="switch from docker to podman",
        operand_values=("podman", "docker"),
    ),
    _AcquisitionExample(
        kind=DirectiveKind.USE_ITEM,
        user_input="I prefer concise replies.",
        operand_values=("concise replies",),
    ),
    _AcquisitionExample(
        kind=DirectiveKind.USE_ITEM,
        user_input="I prefer morning appointments.",
        operand_values=("morning appointments",),
    ),
    _AcquisitionExample(
        kind=DirectiveKind.PROHIBIT_ITEM,
        user_input="I can't have peanuts.",
        operand_values=("peanuts",),
    ),
    _AcquisitionExample(
        kind=DirectiveKind.USE_ITEM,
        user_input="I have a Nord Stage 4.",
        operand_values=("a Nord Stage 4",),
    ),
    _AcquisitionExample(
        kind=DirectiveKind.USE_ITEM,
        user_input="We need a simple recipe.",
        operand_values=("a simple recipe",),
    ),
    _AcquisitionExample(
        kind=DirectiveKind.USE_ITEM,
        user_input="I need oat milk today.",
        operand_values=("oat milk today",),
    ),
    _AcquisitionExample(
        kind=DirectiveKind.SET_PREMISE,
        user_input="The intended audience is senior management.",
        operand_values=("intended audience is senior management",),
    ),
    _AcquisitionExample(
        kind=DirectiveKind.CHANGE_PREMISE,
        user_input="change premise to formal tone",
        operand_values=("formal tone",),
    ),
)


def _render_canonical_forms() -> str:
    lines = ["Canonical directive forms:"]
    for metadata in get_directive_metadata():
        category = _DIRECTIVE_KIND_TO_CATEGORY[metadata.kind]
        canonical_form = _render_canonical_form(metadata)
        lines.append(f"- `{canonical_form}` ({category})")
    return "\n".join(lines)


def _render_positive_acquisition_examples() -> str:
    metadata_by_kind = {metadata.kind: metadata for metadata in get_directive_metadata()}
    lines = ["Examples of user requests that may be drafted as directives:"]
    for example in _POSITIVE_ACQUISITION_EXAMPLES:
        metadata = metadata_by_kind[example.kind]
        canonical_output = _render_example_output(metadata, example.operand_values)
        lines.extend(
            [
                f"User: {example.user_input}",
                f"Output: {canonical_output}",
            ]
        )
        lines.append("")
    return "\n".join(lines[:-1])


def _render_scope_payload_contrasts() -> str:
    metadata_by_kind = {metadata.kind: metadata for metadata in get_directive_metadata()}
    lines = ["Scope and payload contrast examples:"]
    for example in _SCOPE_PAYLOAD_CONTRASTS:
        metadata = metadata_by_kind[example.kind]
        correct = _render_example_output(metadata, example.operand_values)
        truncated = _render_example_output(metadata, example.truncated_operand_values)
        lines.extend(
            [
                f"Source: {example.user_input}",
                f"Correct candidate: {correct}",
                f"Do not truncate it to: {truncated}",
                "",
            ]
        )
    return "\n".join(lines[:-1])


def _render_example_output(metadata: DirectiveMetadata, operand_values: tuple[str, ...]) -> str:
    operands = MappingProxyType(dict(zip(metadata.operand_names, operand_values, strict=True)))
    return CanonicalDirective(kind=metadata.kind, operands=operands).text


@lru_cache(maxsize=1)
def _build_converter_prompt() -> str:
    sections = [
        "You are a directive converter that drafts candidate",
        "Context Compiler directives from user requests.",
        "",
        "Context Compiler directives are compact canonical instructions that propose",
        "persistent compiler state changes. Your output is a draft candidate only.",
        "It is not an approval, not an execution result, and not an authoritative",
        "state change.",
        "",
        _DIRECTIVE_CATEGORY_LINES,
        "",
        _render_canonical_forms(),
        "",
        _PREMISE_POLICY_GUIDANCE,
        "",
        _PROMPT_SUFFIX,
        "",
        _render_scope_payload_contrasts(),
        "",
        _render_positive_acquisition_examples(),
        "",
        _BEHAVIOR_EXAMPLES,
    ]
    return "\n".join(sections).strip()


def _get_converter_prompt() -> str:
    """Return the shared converter system prompt with metadata-derived grammar facts."""

    return _build_converter_prompt()


@lru_cache(maxsize=1)
def _build_structured_converter_prompt() -> str:
    sections = [
        "You are a directive converter that drafts candidate",
        "Context Compiler directives from user requests.",
        "",
        "Context Compiler directives are compact canonical instructions that propose",
        "persistent compiler state changes. Your output is a draft candidate only.",
        "It is not an approval, not an execution result, and not an authoritative",
        "state change.",
        "",
        _DIRECTIVE_CATEGORY_LINES,
        "",
        _render_canonical_forms(),
        "",
        _PREMISE_POLICY_GUIDANCE,
        "",
        _STRUCTURED_PROMPT_SUFFIX,
        "",
        _render_scope_payload_contrasts(),
        "",
        _render_positive_acquisition_examples(),
        "",
        "Contrastive examples:",
        "- Ordinary conversation, questions, quoted or reported directives, and",
        "  unresolved mixed intent: classification `rejected`, output null.",
    ]
    return "\n".join(sections).strip()


def _get_structured_converter_prompt() -> str:
    """Return the evaluation-only prompt for structured provider output."""

    return _build_structured_converter_prompt()
