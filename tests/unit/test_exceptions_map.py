# ABOUTME: Unit tests for the SDK-error dispatch table in _exceptions_map.
# ABOUTME: Tripwire fails when anthropic ships an unmapped APIError subclass.
"""SDK → domain dispatch tests."""

from __future__ import annotations

import anthropic

from app.infrastructure.llm._exceptions_map import (
    _SDK_DISPATCH,
    mapped_sdk_types,
)


def _all_concrete_api_error_subclasses() -> set[type[anthropic.APIError]]:
    """Recursively collect concrete (non-abstract-base) APIError subclasses.

    Skips the intermediate ``APIStatusError`` which exists only as a
    shared-state base for every HTTP-status-carrying subclass — it is
    not raised directly by the SDK, so it does not need its own
    dispatch entry.
    """
    abstract_bases = {anthropic.APIStatusError}

    def walk(cls: type) -> set[type]:
        out = set()
        for sub in cls.__subclasses__():
            out.add(sub)
            out |= walk(sub)
        return out

    return {c for c in walk(anthropic.APIError) if c not in abstract_bases}


def test_every_anthropic_api_error_subclass_is_mapped() -> None:
    """Tripwire: fail when the SDK adds an APIError subclass we ignore.

    Walks ``anthropic.APIError``'s concrete subclass tree and asserts
    that every subclass is covered by ``_SDK_DISPATCH`` — either
    because the class itself is a dispatch row, or because one of its
    base classes is (``isinstance`` in ``wrap_sdk_error`` catches it).

    When this test fails, a future SDK bump has added an error type
    we have not consciously taxonomised. Don't silence it — decide
    which domain class the new subclass maps to, append a row to
    ``_SDK_DISPATCH`` (and a ``_wrap_*`` helper if needed), then
    re-run.
    """
    mapped = mapped_sdk_types()
    unmapped = {
        cls
        for cls in _all_concrete_api_error_subclasses()
        if not any(issubclass(cls, m) for m in mapped)
    }
    assert not unmapped, (
        "anthropic SDK ships APIError subclasses not covered by "
        "_SDK_DISPATCH: "
        f"{sorted(c.__name__ for c in unmapped)}"
    )


def test_dispatch_ordering_puts_subclasses_before_superclasses() -> None:
    """Every dispatch row's class must not be a superclass of a later row.

    ``wrap_sdk_error`` walks ``_SDK_DISPATCH`` top-to-bottom and takes
    the first ``isinstance`` match. If a superclass appears before
    its subclass, the subclass row is dead code — the superclass
    would catch every subclass instance first.
    """
    classes = [cls for cls, _ in _SDK_DISPATCH]
    for i, earlier in enumerate(classes):
        for later in classes[i + 1 :]:
            assert not issubclass(later, earlier) or later is earlier, (
                f"dispatch ordering bug: {later.__name__} is a subclass "
                f"of earlier row {earlier.__name__}; swap their positions "
                "so the subclass matches first."
            )


def test_mapped_sdk_types_reflects_dispatch_table() -> None:
    """`mapped_sdk_types()` matches the first column of _SDK_DISPATCH."""
    assert mapped_sdk_types() == {cls for cls, _ in _SDK_DISPATCH}
