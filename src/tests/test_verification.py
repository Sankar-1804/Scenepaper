import pytest

from backend.verification import (
    SuppressionReason,
    VerificationFlag,
    VerificationResult,
    VerifiedSource,
    enforce_always_show_top_three,
)


def _source(**overrides):
    defaults = {
        "title": "Example source",
        "type": "news",
        "date": "2024-01-01",
        "verified": True,
        "confidence_score": 7.5,
        "tag": "solid",
        "flags": [],
        "suppressed": False,
        "suppression_reason": None,
    }
    defaults.update(overrides)
    return VerifiedSource(**defaults)


def test_suppressed_source_requires_a_reason():
    with pytest.raises(ValueError):
        _source(suppressed=True, suppression_reason=None)


def test_suppressed_source_with_reason_is_allowed():
    source = _source(suppressed=True, suppression_reason=SuppressionReason.FABRICATION)
    assert source.suppressed
    assert source.suppression_reason == SuppressionReason.FABRICATION


def test_confidence_score_out_of_range_rejected():
    with pytest.raises(ValueError):
        _source(confidence_score=11)
    with pytest.raises(ValueError):
        _source(confidence_score=-1)


def test_flags_are_distinct_from_score():
    source = _source(
        confidence_score=8.0,
        flags=[VerificationFlag.SINGLE_SOURCE_ONLY],
    )
    # A high score with a flag is valid — thinly-sourced != contradicted.
    assert source.confidence_score == 8.0
    assert VerificationFlag.SINGLE_SOURCE_ONLY in source.flags


def test_enforce_always_show_top_three_caps_at_three_not_fewer():
    candidates = [
        VerificationResult(
            overall_confidence_score=score,
            overall_tag="t",
            overall_flags=[],
            sources=[],
        )
        for score in [9, 8, 7, 6, 5]
    ]
    top_three = enforce_always_show_top_three(candidates)
    assert len(top_three) == 3
    assert [c.overall_confidence_score for c in top_three] == [9, 8, 7]


def test_enforce_always_show_top_three_does_not_pad_when_fewer_exist():
    candidates = [
        VerificationResult(
            overall_confidence_score=4,
            overall_tag="t",
            overall_flags=[],
            sources=[],
        )
    ]
    result = enforce_always_show_top_three(candidates)
    assert len(result) == 1
