"""
Tests for the Call A / Call B structural guarantees in gemini_client.py.

Deliberately does not call the real Gemini API — client is injected as a
fake. These tests check the things that must hold true by construction:
Call A has no profile parameter at all, Call B requires a fixed
VerificationResult input, and both real prompts are present and reachable.
"""

import inspect

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


def test_prompts_are_real_and_nonempty():
    """Drafted collaboratively with the human, 2026-08-07 (issue #9) — see
    the module docstring. Not a placeholder check anymore; a content
    sanity check so an accidental blank-out gets caught."""

    assert isinstance(gemini_client.VERIFICATION_RULES_PROMPT, str)
    assert len(gemini_client.VERIFICATION_RULES_PROMPT) > 100
    assert isinstance(gemini_client.STRUCTURING_PROMPT, str)
    assert len(gemini_client.STRUCTURING_PROMPT) > 100


class _FakeModels:
    def __init__(self, parsed):
        self._parsed = parsed

    def generate_content(self, **_kwargs):
        return type("FakeResponse", (), {"parsed": self._parsed})()


class _FakeClient:
    def __init__(self, parsed):
        self.models = _FakeModels(parsed)


def test_verify_and_score_candidate_runs_past_the_placeholder_guard():
    """Now that VERIFICATION_RULES_PROMPT is real, this must reach Gemini
    (a fake client here) instead of raising NotImplementedError."""

    fake_payload = {
        "overall_confidence_score": 7,
        "overall_tag": "plausible",
        "overall_flags": [],
        "sources": [],
    }
    result = gemini_client.verify_and_score_candidate(
        "a candidate", [], client=_FakeClient(fake_payload)
    )
    assert result.overall_confidence_score == 7


def test_structure_scene_paper_runs_past_the_placeholder_guard():
    """Now that STRUCTURING_PROMPT is real, this must reach Gemini (a fake
    client here) instead of raising NotImplementedError."""

    verification = VerificationResult(
        overall_confidence_score=8,
        overall_tag="solid",
        overall_flags=[],
        sources=[],
    )
    fake_payload = {
        "title": "Test",
        "category": "curious",
        "dek": "dek",
        "runtime_estimate": "57-63s",
        "hook_window": "0-3s",
        "peak_tension_window": "18-30s",
        "payoff_window": "48-55s",
        "hooks": [],
        "scenes": [],
        "delivery_notes": [],
        "cta_text": "Follow for more.",
    }
    result = gemini_client.structure_scene_paper(
        "source text", verification, [], client=_FakeClient(fake_payload)
    )
    assert result["verification_status"] == "solid"
