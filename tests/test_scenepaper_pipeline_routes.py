"""
Local test harness for functions/scenepaper_pipeline (Advanced I/O) and
functions/scenepaper_pipeline_job (Job function) -- issue #8, Phase 1
tasklist item "Local curl test harness + sample payloads".

This is NOT part of either deployed function (it lives outside functions/,
which is catalyst.json's declared function source root, so it is never
bundled on `catalyst deploy`). It exercises the routing/validation logic
directly by calling `handler()` with lightweight fake Request / job_request
/ context objects -- no live Catalyst auth or network needed.

The real zcatalyst_sdk module is replaced with a FakeCatalystSdk in
pipeline_main's namespace (see setup below) so NoSQL calls hit an in-memory
store instead of the real Catalyst project. The job_scheduling() path still
raises (matching deployed behavior outside a real Catalyst runtime), so the
POST /generate test correctly expects 502.

Run it with:
    python3.9 -m venv /tmp/scenepaper_venv
    /tmp/scenepaper_venv/bin/pip install flask==2.2.5 zcatalyst-sdk==1.3.0
    /tmp/scenepaper_venv/bin/python tests/test_scenepaper_pipeline_routes.py

--------------------------------------------------------------------------
Alternative: real `catalyst serve` + curl (exercises the actual Catalyst
local dev server instead of calling handler() directly -- requires
`catalyst login` to already be active in this project).

KNOWN BLOCKER (confirmed this session, do not re-attempt without fixing
this first): `catalyst serve` fails immediately with
    Error: The APIG rules file .../catalyst-user-rules.json is not found.
because catalyst.json has "apig": {"enabled": true} but no rules file
exists yet. This is the same API Gateway route-wiring gap issue #8 already
flags as blocked this session (an earlier MCP-tool bug on route creation --
try the console UI or CLI directly). Until that's resolved, use the
standalone script above; the commands below are correct once serve works:

    catalyst serve
    # in another terminal, against whatever port `serve` prints, e.g. 3000:
    curl -s http://localhost:3000/scenepaper_pipeline/ | python3 -m json.tool
    curl -s -X POST http://localhost:3000/scenepaper_pipeline/ideate \
      -H 'Content-Type: application/json' -d '{"topic": "a comeback story"}'
    curl -s -X POST http://localhost:3000/scenepaper_pipeline/generate \
      -H 'Content-Type: application/json' \
      -d '{"topic": "a comeback story", "candidate": {"one_liner": "x"}}'
    curl -s http://localhost:3000/scenepaper_pipeline/paper/fixture-paper-1
    curl -s -X PUT http://localhost:3000/scenepaper_pipeline/paper/fixture-paper-1 \
      -H 'Content-Type: application/json' -d '{"title": "Updated title"}'
    curl -s -X DELETE http://localhost:3000/scenepaper_pipeline/paper/fixture-paper-1

    # Job functions have no HTTP surface -- `catalyst serve` explicitly only
    # covers Basic I/O / Advanced I/O / AppSail / client (confirmed via
    # `catalyst serve --help` this session). Job functions are "Non-Http"
    # functions, invoked instead via:
    catalyst functions:execute scenepaper_pipeline_job \
      --input functions/scenepaper_pipeline_job/catalyst-inputs.json
--------------------------------------------------------------------------
"""

import json
import os
import sys
from zcatalyst_sdk.nosql.types import TypeDeserializer as _NoSqlTypeDeserializer

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Both function directories contain a file literally named main.py, so
# neither is added to sys.path -- both are loaded via importlib from their
# exact file path instead, to avoid one shadowing the other in sys.modules.
import importlib.util


def _load_module_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pipeline_main = _load_module_from_path(
    "scenepaper_pipeline_main",
    os.path.join(REPO_ROOT, "functions", "scenepaper_pipeline", "main.py"),
)

# job_main imports `from backend.orchestrator import ...` -- the `backend`
# package lives inside the job function directory (bundled for Catalyst deploy).
# Temporarily add that directory to sys.path so the import resolves without
# a live Catalyst runtime.
_JOB_FUNC_DIR = os.path.join(REPO_ROOT, "functions", "scenepaper_pipeline_job")
if _JOB_FUNC_DIR not in sys.path:
    sys.path.insert(0, _JOB_FUNC_DIR)

job_main = _load_module_from_path(
    "scenepaper_pipeline_job_main",
    os.path.join(_JOB_FUNC_DIR, "main.py"),
)


# --------------------------------------------------------------------------
# Fakes -- duck-type just the surface main.py actually calls
# --------------------------------------------------------------------------

class FakeRequest:
    def __init__(self, method, path, json_body=None, args=None):
        self.method = method
        self.path = path
        self._json_body = json_body
        # Mirrors Flask's request.args. The Gateway can't carry a path id, so
        # /paper takes ?id=<paper_id> -- see the note in handler().
        self.args = dict(args or {})

    def get_json(self, silent=False):
        return self._json_body


class FakeJobRequest:
    def __init__(self, params):
        self._params = params

    def get_all_job_params(self):
        return dict(self._params)

    def get_job_param(self, key):
        return self._params.get(key)


class FakeContext:
    def __init__(self):
        self.closed_with = None

    def close_with_success(self):
        self.closed_with = "success"

    def close_with_failure(self):
        self.closed_with = "failure"


# --------------------------------------------------------------------------
# Fake zcatalyst_sdk -- in-memory NoSQL store, no network needed
# --------------------------------------------------------------------------

FIXTURE_PAPER_ID = "fixture-paper-1"
FIXTURE_PAPER = {
    "id": FIXTURE_PAPER_ID,
    "paper_number": "001",
    "title": "Fixture paper for local routing tests",
    "category": "curious",
    "dek": "Not a real ScenePaper -- returned only by the fake DB layer.",
    "verification_status": "unverified",
    "media_status": "pending",
    "export_status": "locked",
}


class _FakeNoSQLResponse:
    """Mirrors the attribute surface of zcatalyst_sdk.nosql.transfom.NoSqlResponse."""
    def __init__(self, operation, items):
        self.operation = operation
        # Items in each list match NoSqlItemResponse.to_dict() shape: {'item': <dict>}
        self.get = items if operation == 'get' else None
        self.create = items if operation == 'create' else None
        self.update = items if operation == 'update' else None
        self.delete = items if operation == 'delete' else None


class _FakeNoSQLTable:
    def __init__(self, store):
        self._store = store  # shared dict[id -> item]

    def insert_items(self, *args):
        # args[0]['item'] is DynamoDB-encoded; decode to Python before storing
        encoded = args[0]['item']
        item = _NoSqlTypeDeserializer().deserialize({'M': encoded})
        self._store[item['id']] = item
        return _FakeNoSQLResponse('create', [{'item': item}])

    def fetch_item(self, input_data):
        # key value is DynamoDB-encoded, e.g. {'S': paper_id}
        raw_id = input_data['keys'][0]['id']
        paper_id = _NoSqlTypeDeserializer().deserialize(raw_id)
        item = self._store.get(paper_id)
        if item is None:
            return _FakeNoSQLResponse('get', [])
        return _FakeNoSQLResponse('get', [{'item': dict(item)}])

    def update_items(self, *args):
        req = args[0]
        raw_id = req['keys']['id']
        paper_id = _NoSqlTypeDeserializer().deserialize(raw_id)
        update_attrs = req.get('update_attributes', [])
        item = self._store.get(paper_id)
        if item:
            _deser = _NoSqlTypeDeserializer()
            for attr in update_attrs:
                key = attr['attribute_path'][0] if attr.get('attribute_path') else None
                if key and attr.get('operation_type') == 'PUT':
                    # update_value is DynamoDB-encoded; decode before storing
                    item[key] = _deser.deserialize(attr['update_value'])
        return _FakeNoSQLResponse('update', [])

    def delete_items(self, *args):
        raw_id = args[0]['keys']['id']
        paper_id = _NoSqlTypeDeserializer().deserialize(raw_id)
        self._store.pop(paper_id, None)
        return _FakeNoSQLResponse('delete', [])


class _FakeNoSQLService:
    def __init__(self, store):
        self._store = store

    def get_table(self, name):
        return _FakeNoSQLTable(self._store)


class _FakeCacheSegment:
    def get_value(self, key):
        return None  # no keys seeded in tests; _seed_api_keys_from_cache swallows None


class _FakeCacheService:
    def segment(self, seg_id=None):
        return _FakeCacheSegment()


class _FakeApp:
    def __init__(self, store):
        self._store = store

    def nosql(self):
        return _FakeNoSQLService(self._store)

    def cache(self):
        return _FakeCacheService()

    def job_scheduling(self):
        # Raises so POST /generate falls through to the 502 path, matching
        # behavior outside a real Catalyst runtime.
        raise Exception("job_scheduling unavailable outside Catalyst runtime")


class _FakeCatalystSdk:
    def __init__(self):
        self._store = {}

    def initialize(self, name=None, scope=None, req=None):
        return _FakeApp(self._store)


# Patch pipeline_main before any test runs: replace zcatalyst_sdk with the
# fake and pre-seed the NoSQL store with the fixture paper.
_fake_sdk = _FakeCatalystSdk()
_fake_sdk._store[FIXTURE_PAPER_ID] = dict(FIXTURE_PAPER)
pipeline_main.zcatalyst_sdk = _fake_sdk

# Patch job_main: share the same fake NoSQL store so writes from the job
# show up in the same store the pipeline tests read from.
job_main.zcatalyst_sdk = _fake_sdk

# Patch generate_scene_paper in job_main to avoid real Gemini API calls.
# Returns a minimal dict with the fields _stage_write_scenepaper expects.
def _fake_generate_scene_paper(topic, candidate, profile_md_text=None, **kw):
    return {
        "title": f"[fake] {topic}",
        "category": "curious",
        "dek": "fake dek",
        "verification_status": "unverified",
        "hooks": [],
        "scenes": [],
        "delivery_notes": [],
        "sources": [],
        "cta_text": "",
        "profile_warnings": [],
        "profile_dropped_sections": [],
        "profile_truncated_fields": {},
    }

job_main.generate_scene_paper = _fake_generate_scene_paper


# --------------------------------------------------------------------------
# Test runner
# --------------------------------------------------------------------------

_failures = []


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}" + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        _failures.append(label)


def response_status(resp):
    # Flask's make_response(jsonify(...), status) returns a Response object
    # whose .status_code is the int status.
    return resp.status_code


def response_json(resp):
    return json.loads(resp.get_data(as_text=True))


def run_pipeline_route_tests():
    print("\n--- functions/scenepaper_pipeline (Advanced I/O) routing ---")

    # /ideate now runs REAL ideation (SearXNG + Gemini). Stub it here so this
    # harness stays fully offline and costs no API quota -- the ideation
    # pipeline itself is covered by scenepaper-api's own tests.
    pipeline_main._run_ideation_search = lambda topic: [
        {"one_liner": f"stubbed candidate {n} for '{topic}'",
         "confidence_score": None, "flags": [], "sources": []}
        for n in ("A", "B", "C")
    ]

    # /paper?id=<id> -- the only form that survives the API Gateway, which
    # rewrites each rule to a fixed target path and so cannot carry a
    # per-request id in the path.
    resp = pipeline_main.handler(
        FakeRequest("GET", "/paper", args={"id": FIXTURE_PAPER_ID})
    )
    check("GET /paper?id=<known> returns 200", response_status(resp) == 200)

    resp = pipeline_main.handler(FakeRequest("GET", "/paper", args={"id": "nope"}))
    check("GET /paper?id=<unknown> returns 404", response_status(resp) == 404)

    resp = pipeline_main.handler(FakeRequest("GET", "/paper"))
    check("GET /paper with no id returns 400", response_status(resp) == 400)

    # The path form must keep working for direct/local invocation.
    resp = pipeline_main.handler(FakeRequest("GET", f"/paper/{FIXTURE_PAPER_ID}"))
    check("GET /paper/<id> (path form) still returns 200", response_status(resp) == 200)

    # Catalyst rejects job_name longer than 20 chars with INVALID_INPUT,
    # failing the ENTIRE job submission. This is invisible in the SDK (it
    # just POSTs whatever it is given) and cost a live 502 to find, so it is
    # pinned here rather than left to be rediscovered.
    import uuid as _uuid
    _sample = f"sp_gen_{_uuid.uuid4().hex[:10]}"
    check(
        "generated job_name fits Catalyst's 20-char cap",
        len(_sample) <= 20,
        f"{_sample!r} is {len(_sample)} chars",
    )

    resp = pipeline_main.handler(FakeRequest("GET", "/"))
    check("GET / returns 200", response_status(resp) == 200)

    resp = pipeline_main.handler(FakeRequest("POST", "/ideate", {"topic": "underdog comeback"}))
    body = response_json(resp)
    check("POST /ideate (valid topic) returns 200", response_status(resp) == 200)
    check("POST /ideate returns 3 candidates", len(body.get("candidates", [])) == 3, body)

    resp = pipeline_main.handler(FakeRequest("POST", "/ideate", {}))
    check("POST /ideate (missing topic) returns 400", response_status(resp) == 400)

    # The fake SDK's job_scheduling() raises, so the route falls through to
    # the 502 path -- matching behavior outside a real Catalyst runtime.
    # On the real deployed function this should return 202.
    resp = pipeline_main.handler(
        FakeRequest(
            "POST",
            "/generate",
            {"topic": "underdog comeback", "candidate": {"one_liner": "x"}},
        )
    )
    check(
        "POST /generate (job submission attempted, fails outside real Catalyst runtime) returns 502",
        response_status(resp) == 502,
        response_json(resp),
    )

    resp = pipeline_main.handler(FakeRequest("POST", "/generate", {"topic": "x"}))
    check("POST /generate (missing candidate) returns 400", response_status(resp) == 400)

    resp = pipeline_main.handler(FakeRequest("GET", "/paper/fixture-paper-1"))
    check("GET /paper/fixture-paper-1 returns 200", response_status(resp) == 200)

    resp = pipeline_main.handler(FakeRequest("GET", "/paper/does-not-exist"))
    check("GET /paper/does-not-exist returns 404", response_status(resp) == 404)

    resp = pipeline_main.handler(
        FakeRequest("PUT", "/paper/fixture-paper-1", {"title": "Updated via test"})
    )
    body = response_json(resp)
    check("PUT /paper/fixture-paper-1 returns 200", response_status(resp) == 200)
    check(
        "PUT /paper/fixture-paper-1 applies the update",
        body.get("paper", {}).get("title") == "Updated via test",
        body,
    )

    resp = pipeline_main.handler(FakeRequest("PUT", "/paper/fixture-paper-1", {}))
    check("PUT /paper/fixture-paper-1 (empty body) returns 400", response_status(resp) == 400)

    resp = pipeline_main.handler(FakeRequest("PUT", "/paper/does-not-exist", {"title": "x"}))
    check("PUT /paper/does-not-exist returns 404", response_status(resp) == 404)

    resp = pipeline_main.handler(FakeRequest("DELETE", "/paper/fixture-paper-1"))
    check("DELETE /paper/fixture-paper-1 returns 200", response_status(resp) == 200)

    resp = pipeline_main.handler(FakeRequest("DELETE", "/paper/does-not-exist"))
    check("DELETE /paper/does-not-exist returns 404", response_status(resp) == 404)

    resp = pipeline_main.handler(FakeRequest("POST", "/paper/fixture-paper-1"))
    check("POST /paper/:id (wrong method) returns 405", response_status(resp) == 405)

    resp = pipeline_main.handler(FakeRequest("GET", "/nope"))
    check("GET /nope (unknown route) returns 404", response_status(resp) == 404)



def run_job_function_tests():
    print("\n--- functions/scenepaper_pipeline_job (Job function) ---")

    new_paper_id = "job-test-paper-1"
    ctx = FakeContext()
    job_request = FakeJobRequest(
        {
            "paper_id": new_paper_id,
            "topic": "underdog comeback",
            "candidate": json.dumps({"one_liner": "scrappy startup beats odds"}),
            "user_id": "",
        }
    )
    job_main.handler(job_request, ctx)
    check("Job function closes with success on valid params", ctx.closed_with == "success")
    written = _fake_sdk._store.get(new_paper_id)
    check(
        "Job function writes ScenePaper to NoSQL",
        written is not None,
        f"store keys: {list(_fake_sdk._store.keys())}",
    )
    check(
        "Written ScenePaper has correct paper_id",
        written is not None and written.get("id") == new_paper_id,
        written,
    )
    check(
        "Written ScenePaper has export_status=locked",
        written is not None and written.get("export_status") == "locked",
        written,
    )
    check(
        "Written ScenePaper has title from fake orchestrator",
        written is not None and written.get("title") == "[fake] underdog comeback",
        written,
    )

    # sources[].confidence_score arrives as a float from Call A (VerificationResult).
    # TypeSerializer raises on floats -- _floats_to_decimal() must convert them
    # to Decimal before to_nosql(). This is the exact failure that blocked the
    # first live end-to-end run (38.5s job that wrote nothing).
    float_paper_id = "job-test-paper-float"
    _original_gen = job_main.generate_scene_paper

    def _gen_with_float(topic, candidate, **kw):
        return {
            "title": f"[fake] {topic}",
            "category": "curious",
            "dek": "fake dek",
            "verification_status": "unverified",
            "hooks": [],
            "scenes": [],
            "delivery_notes": [],
            "sources": [
                {
                    "title": "Test source",
                    "confidence_score": 7.0,  # float -- triggers TypeError without Decimal fix
                    "verified": True,
                    "flags": [],
                }
            ],
            "cta_text": "",
            "profile_warnings": [],
            "profile_dropped_sections": [],
            "profile_truncated_fields": {},
        }

    job_main.generate_scene_paper = _gen_with_float
    ctx = FakeContext()
    job_main.handler(
        FakeJobRequest({"paper_id": float_paper_id, "topic": "float test",
                        "candidate": json.dumps({"one_liner": "x"}), "user_id": ""}),
        ctx,
    )
    job_main.generate_scene_paper = _original_gen
    check(
        "Job with float confidence_score succeeds (Decimal conversion works)",
        ctx.closed_with == "success",
        f"closed_with={ctx.closed_with!r}",
    )
    from decimal import Decimal
    written_float = _fake_sdk._store.get(float_paper_id)
    check(
        "sources[].confidence_score stored as Decimal after float conversion",
        written_float is not None
        and written_float.get("sources", [{}])[0].get("confidence_score") == Decimal("7.0"),
        written_float,
    )

    ctx = FakeContext()
    job_request = FakeJobRequest({"topic": "underdog comeback"})  # missing paper_id/candidate
    job_main.handler(job_request, ctx)
    check("Job function closes with failure on missing params", ctx.closed_with == "failure")

    ctx = FakeContext()
    job_request = FakeJobRequest(
        {"paper_id": "fixture-paper-1", "topic": "x", "candidate": "not valid json"}
    )
    job_main.handler(job_request, ctx)
    check("Job function closes with failure on invalid candidate JSON", ctx.closed_with == "failure")

    # ------------------------------------------------------------------
    # Round-trip type checks -- write via job function, read via GET handler,
    # assert the JSON response carries bool and number (not string "true"/"8.5").
    #
    # Two degradations confirmed against live Catalyst NoSQL (paper 9da2d576):
    #   - Decimal("8.5") → Flask._default → str "8.5"  (N type / number fields)
    #   - {"BOOL": "true"} from Catalyst API → TypeDeserializer passes string
    #     through unchanged → JavaScript Boolean("false") === true
    # Both are fixed by _normalize_nosql_item in _get_scenepaper.
    # ------------------------------------------------------------------
    _rt_paper_id = "roundtrip-type-test"
    _orig_gen = job_main.generate_scene_paper

    def _gen_with_typed_fields(topic, candidate, **kw):
        return {
            "title": "[fake] type round-trip",
            "category": "curious",
            "dek": "fake",
            "verification_status": "unverified",
            "hooks": [
                {
                    "label": "H1",
                    "type": "direct",
                    "text": [
                        {"text": "Sourced claim.", "verified": True},
                        {"text": " Dramatized color.", "verified": False},
                    ],
                }
            ],
            "scenes": [],
            "delivery_notes": [],
            "sources": [
                {
                    "title": "Test source",
                    "type": "web",
                    "tag": "solid",
                    "confidence_score": 7.5,   # float -> Decimal("7.5") after _floats_to_decimal
                    "verified": True,
                    "suppressed": False,
                    "flags": [],
                }
            ],
            "cta_text": "",
            "profile_warnings": [],
            "profile_dropped_sections": [],
            "profile_truncated_fields": {},
        }

    job_main.generate_scene_paper = _gen_with_typed_fields
    ctx = FakeContext()
    job_main.handler(
        FakeJobRequest({
            "paper_id": _rt_paper_id,
            "topic": "type test",
            "candidate": json.dumps({"one_liner": "x"}),
            "user_id": "",
        }),
        ctx,
    )
    job_main.generate_scene_paper = _orig_gen

    check(
        "Round-trip: job succeeds",
        ctx.closed_with == "success",
        f"closed_with={ctx.closed_with!r}",
    )

    resp = pipeline_main.handler(FakeRequest("GET", "/paper", args={"id": _rt_paper_id}))
    check("Round-trip: GET /paper returns 200", response_status(resp) == 200)
    body = response_json(resp)
    paper = body.get("paper", {})

    hook_span_0 = (paper.get("hooks") or [{}])[0].get("text", [{}])[0]
    hook_span_1 = (paper.get("hooks") or [{}])[0].get("text", [{}, {}])[1]
    src = (paper.get("sources") or [{}])[0]

    check(
        "Round-trip: hooks[0].text[0].verified is bool True (not str 'true')",
        hook_span_0.get("verified") is True,
        f"got {type(hook_span_0.get('verified')).__name__!r}: {hook_span_0.get('verified')!r}",
    )
    check(
        "Round-trip: hooks[0].text[1].verified is bool False (not str 'false')",
        hook_span_1.get("verified") is False,
        f"got {type(hook_span_1.get('verified')).__name__!r}: {hook_span_1.get('verified')!r}",
    )
    check(
        "Round-trip: sources[0].verified is bool True",
        src.get("verified") is True,
        f"got {type(src.get('verified')).__name__!r}: {src.get('verified')!r}",
    )
    check(
        "Round-trip: sources[0].confidence_score is a number (not str '7.5')",
        isinstance(src.get("confidence_score"), (int, float)),
        f"got {type(src.get('confidence_score')).__name__!r}: {src.get('confidence_score')!r}",
    )

    # Simulate the live Catalyst BOOL quirk: the API may return {"BOOL": "true"}
    # (JSON string, not JSON boolean) -- TypeDeserializer passes it through as
    # the Python string "true". Plant that string directly in the fake store so
    # we can verify _normalize_nosql_item corrects it without a live API call.
    _fake_sdk._store["bool-quirk-sim"] = {
        "id": "bool-quirk-sim",
        "hooks": [{"label": "H", "text": [
            {"text": "A claim", "verified": "true"},   # string, not bool
            {"text": " Color", "verified": "false"},
        ]}],
        "sources": [{"title": "S", "type": "web", "verified": "false"}],
    }
    resp = pipeline_main.handler(FakeRequest("GET", "/paper", args={"id": "bool-quirk-sim"}))
    body = response_json(resp)
    paper = body.get("paper", {})
    qs0 = (paper.get("hooks") or [{}])[0].get("text", [{}])[0]
    qs1 = (paper.get("hooks") or [{}])[0].get("text", [{}, {}])[1]
    check(
        "Catalyst BOOL quirk: str 'true' normalized to bool True in GET response",
        qs0.get("verified") is True,
        f"got {type(qs0.get('verified')).__name__!r}: {qs0.get('verified')!r}",
    )
    check(
        "Catalyst BOOL quirk: str 'false' normalized to bool False in GET response",
        qs1.get("verified") is False,
        f"got {type(qs1.get('verified')).__name__!r}: {qs1.get('verified')!r}",
    )


if __name__ == "__main__":
    # main.py's jsonify()/make_response() need a Flask application context
    # to resolve current_app -- on the real Catalyst runtime this is
    # provided by the platform's own Flask app wrapping the deployed
    # function (the same imports work in the already-deployed "hello
    # world" version of this function). Standing up a throwaway Flask app
    # here just recreates that context for local testing.
    from flask import Flask

    _test_app = Flask(__name__)
    with _test_app.app_context():
        run_pipeline_route_tests()
        run_job_function_tests()

    print()
    if _failures:
        print(f"{len(_failures)} check(s) FAILED:")
        for label in _failures:
            print(f"  - {label}")
        sys.exit(1)
    else:
        print("All checks passed.")
