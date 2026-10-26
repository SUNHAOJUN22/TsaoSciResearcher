from __future__ import annotations

import copy
import io
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest
import yaml

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/cleanup-branches.yml"
API_ROOT = "/repos/SUNHAOJUN22/TsaoSciResearcher"


class LocalGitHubAPI:
    """In-memory HTTP substitute; no request is sent to a network endpoint."""

    def __init__(self, names: list[str], *, default_branch: str = "main") -> None:
        self.default_branch = default_branch
        self.branches = [
            {"name": name, "commit": {"sha": ("a" if name == "main" else "b") * 40}} for name in names
        ]
        self.pulls = [{"number": 7, "state": "open", "head": {"ref": "unmerged/work"}}]
        self.calls: list[tuple[str, str]] = []
        self.branch_payload: object | None = None
        self.http_error: int | None = None

    def urlopen(self, request: urllib.request.Request, *, timeout: int) -> io.BytesIO:
        assert timeout == 30
        url = urllib.parse.urlsplit(request.full_url)
        assert url.scheme == "https" and url.netloc == "api.github.com"
        assert url.path.startswith(API_ROOT)
        path = url.path[len(API_ROOT) :]
        method = request.get_method()
        self.calls.append((method, path + ("?" + url.query if url.query else "")))
        if self.http_error is not None:
            raise urllib.error.HTTPError(request.full_url, self.http_error, "fixture", {}, None)
        query = urllib.parse.parse_qs(url.query)
        page = int(query.get("page", ["1"])[0])
        size = int(query.get("per_page", ["100"])[0])
        if method == "GET" and path == "":
            value: object = {"default_branch": self.default_branch}
        elif method == "GET" and path == "/branches":
            value = (
                self.branch_payload
                if self.branch_payload is not None
                else self.branches[(page - 1) * size : page * size]
            )
        elif method == "GET" and path == "/pulls":
            value = self.pulls[(page - 1) * size : page * size]
        elif method == "PATCH" and path == "/pulls/7":
            self.pulls[0]["state"] = "closed"
            value = self.pulls[0]
        elif method == "DELETE" and path.startswith("/git/refs/heads/"):
            name = urllib.parse.unquote(path.removeprefix("/git/refs/heads/"))
            self.branches = [branch for branch in self.branches if branch["name"] != name]
            value = None
        else:
            raise AssertionError(f"Unexpected fixture API call: {method} {path}")
        return io.BytesIO(json.dumps(value).encode())


def run_inline(monkeypatch: pytest.MonkeyPatch, api: LocalGitHubAPI) -> None:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["cleanup"]["steps"]
    assert len(steps) == 1
    script = steps[0]["run"]
    match = re.fullmatch(r"python - <<'PY'\n(.*)\nPY\n?", script, re.DOTALL)
    assert match is not None, "Execute the complete inline Python body, not a selected fragment"
    monkeypatch.setenv("GITHUB_TOKEN", "local-http-fixture-only")
    monkeypatch.setenv("GITHUB_REPOSITORY", "SUNHAOJUN22/TsaoSciResearcher")
    monkeypatch.setattr(urllib.request, "urlopen", api.urlopen)
    exec(compile(match.group(1), str(WORKFLOW), "exec"), {"__name__": "__main__"})


def assert_read_only(api: LocalGitHubAPI) -> None:
    assert api.calls
    assert {method for method, _ in api.calls} == {"GET"}
    assert all(not path.startswith("/pulls") for _, path in api.calls)


def test_main_only_does_not_close_an_open_pull_request(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    api = LocalGitHubAPI(["main"])
    original = copy.deepcopy(api.pulls)
    run_inline(monkeypatch, api)
    assert "PASS" in capsys.readouterr().out
    assert api.pulls == original
    assert_read_only(api)


def test_unmerged_branch_and_pull_request_are_preserved(monkeypatch: pytest.MonkeyPatch) -> None:
    api = LocalGitHubAPI(["main", "unmerged/work"])
    original = copy.deepcopy((api.branches, api.pulls))
    # The extra ref names a distinct, unreviewed commit. The workflow has no
    # authority to discard it or close its PR while checking the branch policy.
    with pytest.raises(SystemExit, match="unmerged/work"):
        run_inline(monkeypatch, api)
    assert (api.branches, api.pulls) == original
    assert_read_only(api)


def test_paginated_extra_branches_fail_without_mutation(monkeypatch: pytest.MonkeyPatch) -> None:
    names = ["main", *(f"work-{number}" for number in range(100))]
    api = LocalGitHubAPI(names)
    original = copy.deepcopy(api.branches)
    with pytest.raises(SystemExit, match="work-99"):
        run_inline(monkeypatch, api)
    assert api.branches == original
    assert any("page=2" in path for _, path in api.calls)
    assert_read_only(api)


def test_non_main_default_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    api = LocalGitHubAPI(["main"], default_branch="legacy")
    with pytest.raises(SystemExit, match="default branch is not main"):
        run_inline(monkeypatch, api)
    assert_read_only(api)


def test_missing_main_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    api = LocalGitHubAPI([])
    with pytest.raises(SystemExit, match="main"):
        run_inline(monkeypatch, api)
    assert_read_only(api)


def test_non_list_branch_response_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    api = LocalGitHubAPI(["main"])
    api.branch_payload = {"message": "incomplete response"}
    with pytest.raises(RuntimeError, match="expected list response"):
        run_inline(monkeypatch, api)
    assert_read_only(api)


def test_api_access_failure_is_not_reported_as_success(monkeypatch: pytest.MonkeyPatch) -> None:
    api = LocalGitHubAPI(["main"])
    api.http_error = 403
    with pytest.raises(urllib.error.HTTPError) as raised:
        run_inline(monkeypatch, api)
    assert raised.value.code == 403
    assert_read_only(api)
