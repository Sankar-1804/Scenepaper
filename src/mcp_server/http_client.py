"""
Thin HTTP wrapper around the three live Catalyst Gateway routes.

Base URL is read from SCENEPAPER_API_URL env var so tests can point at a
local fake and production points at the real Gateway without code changes.
"""
import os
import requests

_DEFAULT_BASE = (
    "https://scenepaper-60081628315.development.catalystserverless.in"
)


def _base() -> str:
    return os.environ.get("SCENEPAPER_API_URL", _DEFAULT_BASE).rstrip("/")


def ideate(topic: str) -> dict:
    """POST /ideate — returns {"candidates": [...]}."""
    resp = requests.post(f"{_base()}/ideate", json={"topic": topic}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def generate(topic: str, candidate: dict) -> dict:
    """POST /generate — returns {"job_id": ..., "paper_id": ...} with 202."""
    resp = requests.post(
        f"{_base()}/generate",
        json={"topic": topic, "candidate": candidate},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def get_paper(paper_id: str) -> dict:
    """GET /paper?id=<id> — returns the full ScenePaper document."""
    resp = requests.get(f"{_base()}/paper", params={"id": paper_id}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def update_paper(paper_id: str, fields: dict) -> dict:
    """PUT /paper?id=<id> — returns {"paper": {...}}."""
    resp = requests.put(
        f"{_base()}/paper",
        params={"id": paper_id},
        json=fields,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def delete_paper(paper_id: str) -> dict:
    """DELETE /paper?id=<id> — returns {"deleted": true}."""
    resp = requests.delete(
        f"{_base()}/paper", params={"id": paper_id}, timeout=30
    )
    resp.raise_for_status()
    return resp.json()
