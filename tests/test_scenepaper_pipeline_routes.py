"""
Local test harness for functions/scenepaper_pipeline (Advanced I/O) and
functions/scenepaper_pipeline_job (Job function) -- issue #8, Phase 1
tasklist item "Local curl test harness + sample payloads".

This is NOT part of either deployed function (it lives outside functions/,
which is catalyst.json's declared function source root, so it is never
bundled on `catalyst deploy`). It exercises the routing/validation logic
directly by calling `handler()` with lightweight fake Request / job_request
/ context objects -- no live Catalyst auth or network needed, which matters
since the real NoSQL table (issue #1) and job pool (see
functions/scenepaper_pipeline/main.py's _submit_pipeline_job docstring)
don't exist yet.

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
job_main = _load_module_from_path(
    "scenepaper_pipeline_job_main",
    os.path.join(REPO_ROOT, "functions", "scenepaper_pipeline_job", "main.py"),
)


# --------------------------------------------------------------------------
# Fakes -- duck-type just the surface main.py actually calls
# --------------------------------------------------------------------------

class FakeRequest:
    def __init__(self, method, path, json_body=None):
        self.method = method
        self.path = path
        self._json_body = json_body

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

    resp = pipeline_main.handler(FakeRequest("GET", "/"))
    check("GET / returns 200", response_status(resp) == 200)

    resp = pipeline_main.handler(FakeRequest("POST", "/ideate", {"topic": "underdog comeback"}))
    body = response_json(resp)
    check("POST /ideate (valid topic) returns 200", response_status(resp) == 200)
    check("POST /ideate returns 3 candidates", len(body.get("candidates", [])) == 3, body)

    resp = pipeline_main.handler(FakeRequest("POST", "/ideate", {}))
    check("POST /ideate (missing topic) returns 400", response_status(resp) == 400)

    resp = pipeline_main.handler(
        FakeRequest(
            "POST",
            "/generate",
            {"topic": "underdog comeback", "candidate": {"one_liner": "x"}},
        )
    )
    check(
        "POST /generate (job pool not configured yet) returns 503",
        response_status(resp) == 503,
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

    ctx = FakeContext()
    job_request = FakeJobRequest(
        {
            "paper_id": "fixture-paper-1",
            "topic": "underdog comeback",
            "candidate": json.dumps({"one_liner": "x"}),
            "user_id": "",
        }
    )
    job_main.handler(job_request, ctx)
    check("Job function closes with success on valid params", ctx.closed_with == "success")

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
