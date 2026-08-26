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

from .constants import PREPROCESSOR_NO_DIRECTIVE_SENTINEL

_DIRECTIVE_CATEGORY_LINES = """Directive categories:
- Premise directives change a standing instruction for how the assistant
  should generally behave.
- Policy directives manage named policy items.
- Administrative directives change compiler-managed state."""

_PREMISE_POLICY_GUIDANCE = """What premise vs policy means:
- A premise is a broad standing behavior instruction such as tone, style, or
  ongoing reply guidance.
- A policy is a named item that should be used, prohibited, removed, or replaced.
- Do not infer premise or policy meaning from payload words alone. Only
  encode what the user explicitly requests."""


@dataclass(frozen=True)
class _AcquisitionExample:
    kind: DirectiveKind
    user_input: str
    operand_values: tuple[str, ...]


_BEHAVIOR_EXAMPLES = f"""Examples of ordinary conversation that must not become directives:
User: can you help with lunch?
Output: {PREPROCESSOR_NO_DIRECTIVE_SENTINEL}

User: Docker seems popular in this repo.
Output: {PREPROCESSOR_NO_DIRECTIVE_SENTINEL}

User: What does clear state do?
Output: {PREPROCESSOR_NO_DIRECTIVE_SENTINEL}

Examples of directive discussion or unresolved multi-directive input where you must not guess:
User: use docker?
Output: {PREPROCESSOR_NO_DIRECTIVE_SENTINEL}

User: He said "use docker".
Output: {PREPROCESSOR_NO_DIRECTIVE_SENTINEL}

User: prohibit peanuts and use almonds
Output: {PREPROCESSOR_NO_DIRECTIVE_SENTINEL}"""

_PROMPT_SUFFIX = f"""Your task:
- Read one user message.
- If the user clearly requests one behavior change that can be represented
  by a canonical directive, produce exactly one candidate directive in
  canonical form.
- Otherwise output exactly `{PREPROCESSOR_NO_DIRECTIVE_SENTINEL}`.

Output contract:
- A single candidate directive line in canonical form, or
- exactly `{PREPROCESSOR_NO_DIRECTIVE_SENTINEL}`

Output rules:
- Output exactly one line.
- Do not explain.
- Do not add quotes, labels, markdown, JSON, or extra text.
- Do not output multiple directives.

Conversion rules:
- Only encode information explicitly present in the user request.
- Create the smallest valid directive payload necessary to represent the request.
- Preserve the user's wording for payload text when possible.
- Do not guess missing intent, omitted items, hidden context, or unstated replacements.
- Do not infer semantic intent from directive payload contents.
- Do not invent directives from ordinary conversation.
- If the input is ordinary conversation, quoted or reported directive text,
  directive discussion, or a mixed request you cannot safely reduce to one
  directive, output `{PREPROCESSOR_NO_DIRECTIVE_SENTINEL}`.

When to output `{PREPROCESSOR_NO_DIRECTIVE_SENTINEL}`:
- Ordinary conversation, questions, explanations, or comments.
- Requests that do not ask to change compiler-managed behavior.
- Questions or discussion about directives rather than a request to change behavior.
- Requests that remain too ambiguous to draft as one directive.
- Inputs containing multiple directive requests.
- Quoted, cited, reported, example, or discussed directive text rather than a direct request."""

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
        kind=DirectiveKind.SET_PREMISE,
        user_input="make replies concise from now on",
        operand_values=("concise replies",),
    ),
    _AcquisitionExample(
        kind=DirectiveKind.CHANGE_PREMISE,
        user_input="change the standing premise to formal tone",
        operand_values=("formal tone",),
    ),
    _AcquisitionExample(
        kind=DirectiveKind.SET_PREMISE,
        user_input="set premise to concise replies",
        operand_values=("concise replies",),
    ),
    _AcquisitionExample(
        kind=DirectiveKind.USE_ITEM,
        user_input="allow docker",
        operand_values=("docker",),
    ),
    _AcquisitionExample(
        kind=DirectiveKind.PROHIBIT_ITEM,
        user_input="stop using peanuts",
        operand_values=("peanuts",),
    ),
    _AcquisitionExample(
        kind=DirectiveKind.SET_PREMISE,
        user_input="I prefer concise replies.",
        operand_values=("concise replies",),
    ),
)


def _placeholder(name: str) -> str:
    return f"<{name.replace('_', ' ')}>"


def _format_canonical_form(
    kind: DirectiveKind, canonical_start: str, operand_names: tuple[str, ...]
) -> str:
    if not operand_names:
        return canonical_start

    if kind is DirectiveKind.REPLACE_USE and operand_names == ("new_item", "old_item"):
        return f"{canonical_start} {_placeholder('new_item')} instead of {_placeholder('old_item')}"

    operands = " ".join(_placeholder(name) for name in operand_names)
    return f"{canonical_start} {operands}"


def _render_canonical_forms() -> str:
    lines = ["Canonical directive forms:"]
    for metadata in get_directive_metadata():
        category = _DIRECTIVE_KIND_TO_CATEGORY[metadata.kind]
        canonical_form = _format_canonical_form(
            metadata.kind,
            metadata.canonical_start,
            metadata.operand_names,
        )
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
        "persistent compiler behavior changes. Your output is a draft candidate only.",
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
        _render_positive_acquisition_examples(),
        "",
        _BEHAVIOR_EXAMPLES,
    ]
    return "\n".join(sections).strip()


def get_converter_prompt() -> str:
    """Return the shared converter system prompt with metadata-derived grammar facts."""

    return _build_converter_prompt()
