import pytest
from test_public_api_contracts import _assert_class_contract


def test_forbidden_class_members_are_rejected_by_the_harness() -> None:
    class LegacyResult:
        outcome = "directive"

    with pytest.raises(AssertionError):
        _assert_class_contract(
            "LegacyResult",
            LegacyResult,
            {"kind": "class", "forbidden_members": ["outcome"]},
        )
