"""
Tests for the Call A / Call B structural guarantees in gemini_client.py.

Deliberately does not call the real Gemini API (no key is configured
tonight — see .env). These tests check the things that must hold true by
construction: Call A has no profile parameter at all, Call B requires a
fixed VerificationResult input, and neither prompt placeholder has been
silently filled in by anything other than the human.
"""

import inspect

import pytest

from backend.clients import gemini_client
from backend.verification import VerificationResult


def test_call_a_has_no_profile_parameter_at_all():
    """Structural defense: it's not enough that Call A "doesn't use"
    profile.md — there must be no parameter for it to be passed through in
    the first place."""

    signature = inspect.signature(gemini_client.verify_and_score_candidate)
    param_names = set(signature.parameters.keys())
    assert not any("profile" in name for name in param_names)


def test_call_b_requires_verification_as_a_positional_or_required_argument():
    signature = inspect.signature(gemini_client.structure_scene_paper)
    verification_param = signature.parameters["verification"]
    assert verification_param.default is inspect.Parameter.empty


def test_call_b_response_schema_has_no_score_or_flag_fields():
    """Defense in depth: even if Call A's isolation were somehow bypassed,
    Call B's own response_schema has no field that could carry a score,
    confidence, flag, or suppression value."""

    forbidden_substrings = ("score", "confidence", "flag", "suppress", "verified")
    schema_field_names = gemini_client.CALL_B_RESPONSE_SCHEMA.properties.keys()
    for name in schema_field_names:
        for forbidden in forbidden_substrings:
            assert forbidden not in name.lower(), (
                f"CALL_B_RESPONSE_SCHEMA has a field '{name}' that looks like it "
                "could carry a verification signal — Call B must not have any "
                "such field."
            )


def test_prompts_are_still_placeholders():
    """These are reserved for the human to write (see module docstring).
    This test exists so CI fails loudly if a future change accidentally
    fills them in as part of an unrelated commit, rather than as a
    deliberate, reviewed human edit."""

    assert gemini_client.VERIFICATION_RULES_PROMPT is None
    assert gemini_client.STRUCTURING_PROMPT is None


def test_verify_and_score_raises_clearly_while_prompt_is_a_placeholder():
    with pytest.raises(NotImplementedError):
        gemini_client.verify_and_score_candidate("a candidate", [])


def test_structure_scene_paper_raises_clearly_while_prompt_is_a_placeholder():
    verification = VerificationResult(
        overall_confidence_score=8,
        overall_tag="solid",
        overall_flags=[],
        sources=[],
    )
    with pytest.raises(NotImplementedError):
        gemini_client.structure_scene_paper("source text", verification, [])
