"""Exercise GitHub-only dispatch, provenance matching, and duplicate protection."""

import json
from pathlib import Path

import pytest

from rehearsal import deploy

COMMIT = "a" * 40
REPOSITORY = "synthetic/rehearsal"
CORRELATION = "b" * 32


@pytest.fixture
def request_record() -> dict:
    """Represent one approved, pushed synthetic rehearsal deployment."""
    return {
        "repository": REPOSITORY, "ref": "rehearsal", "commit": COMMIT,
        "display_name": "Synthetic Rehearsal abc123", "app_name": "synthetic-rehearsal-abc123",
        "connect_dataverse": True, "rehearsal_id": CORRELATION,
        "run_title": f"Deploy my app [{CORRELATION}]",
    }


@pytest.fixture
def run_record(request_record: dict) -> dict:
    """Represent the GitHub run that actually corresponds to that request."""
    return {
        "displayTitle": request_record["run_title"], "headSha": COMMIT,
        "headBranch": "rehearsal", "event": "workflow_dispatch", "databaseId": 123,
        "attempt": 1, "status": "completed", "conclusion": "success",
    }


def test_selects_exact_dispatch_not_latest_run(request_record: dict, run_record: dict) -> None:
    """Runs for the same commit need independent correlation IDs."""
    unrelated = {**run_record, "displayTitle": "Deploy my app [another-run]"}
    assert deploy.select_run([unrelated, run_record], request_record) == run_record
    assert deploy.select_run([unrelated], request_record) is None
    assert deploy.select_run([{**run_record, "headSha": "c" * 40}], request_record) is None
    with pytest.raises(ValueError, match="Multiple runs"):
        deploy.select_run([run_record, run_record], request_record)


def test_result_provenance_must_match(request_record: dict, run_record: dict) -> None:
    """Do not accept another run's successful health response or data source."""
    result = {
        "schema_version": 1, "repository": REPOSITORY, "commit": COMMIT,
        "display_name": request_record["display_name"], "app_name": request_record["app_name"],
        "connect_dataverse": True, "run_id": "123", "run_attempt": "1", "source": "Dataverse",
        "health_status": 200, "page_status": 200,
        "run_url": f"https://github.com/{REPOSITORY}/actions/runs/123",
        "url": "https://synthetic-rehearsal-abc123.example.azurecontainerapps.io",
    }
    deploy.validate_result(result, request_record, run_record)
    for key, value in (("commit", "c" * 40), ("source", "samples"), ("run_id", "999"),
                       ("connect_dataverse", "true"), ("run_attempt", "2")):
        with pytest.raises(ValueError):
            deploy.validate_result({**result, key: value}, request_record, run_record)


def test_dispatch_requires_approval_before_writes(tmp_path: Path) -> None:
    """No implicit infrastructure usage from running the helper with defaults."""
    with pytest.raises(ValueError, match="approve-deploy"):
        deploy.dispatch(REPOSITORY, "rehearsal", tmp_path / "request.json", dataverse=False, approved=False)
    assert not list(tmp_path.iterdir())


def test_dispatch_is_github_only_and_records_unique_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No Azure login, credential download, or 'latest run' heuristic is needed."""
    calls = []

    def invoke(command: list[str], **kwargs: object) -> str:
        calls.append(command)
        assert command[0] in {"gh", "git"}
        if command[:3] == ["gh", "repo", "view"]:
            return json.dumps({"nameWithOwner": REPOSITORY, "isTemplate": False,
                               "visibility": "PRIVATE", "viewerPermission": "WRITE"})
        if command[:3] == ["git", "branch", "--show-current"]:
            return "rehearsal"
        if command[:2] == ["gh", "api"]:
            return json.dumps({"sha": COMMIT})
        return ""

    monkeypatch.setattr(deploy, "invoke", invoke)
    monkeypatch.setattr(deploy, "git_state", lambda: {"commit": COMMIT, "dirty": False})
    monkeypatch.setattr(deploy, "load", lambda: {
        "displayName": "Synthetic Rehearsal abc123", "appName": "synthetic-rehearsal-abc123",
    })
    target = tmp_path / "request.json"
    request = deploy.dispatch(REPOSITORY, "rehearsal", target, dataverse=True, approved=True)
    assert request["dispatch_state"] == "accepted"
    dispatch_call = calls[-1]
    assert "expected_sha=" + COMMIT in dispatch_call
    assert "rehearsal_id=" + request["rehearsal_id"] in dispatch_call
    assert "connect_dataverse=true" in dispatch_call
    assert "target=vendor" in dispatch_call
    before = len(calls)
    with pytest.raises(ValueError, match="already exists"):
        deploy.dispatch(REPOSITORY, "rehearsal", target, dataverse=True, approved=True)
    assert len(calls) == before


def test_source_template_cannot_be_deployed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the teaching template from becoming the completed exercise app."""
    monkeypatch.setattr(deploy, "invoke", lambda *args, **kwargs: json.dumps({
        "nameWithOwner": REPOSITORY, "isTemplate": True,
    }))
    with pytest.raises(ValueError, match="source template"):
        deploy.dispatch(REPOSITORY, "main", tmp_path / "request.json", dataverse=False, approved=True)


def test_pending_run_does_not_pass_or_redispatch(
    request_record: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An accepted request with no visible run remains resumable, not successful."""
    target = tmp_path / "request.json"
    target.write_text(json.dumps(request_record), encoding="utf-8")
    calls = []

    def invoke(command: list[str], **kwargs: object) -> str:
        calls.append(command)
        return "[]"

    monkeypatch.setattr(deploy, "invoke", invoke)
    assert deploy.collect(target, wait=False) == 2
    assert len(calls) == 1
    assert calls[0][:3] == ["gh", "run", "list"]


def test_failed_workflow_cannot_pass(
    request_record: dict, run_record: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not download artifacts or report endpoints after a failed deployment."""
    target = tmp_path / "request.json"
    target.write_text(json.dumps(request_record), encoding="utf-8")
    monkeypatch.setattr(deploy, "invoke", lambda *args, **kwargs: json.dumps([
        {**run_record, "conclusion": "failure"},
    ]))
    with pytest.raises(ValueError, match="did not succeed"):
        deploy.collect(target, wait=False)


def test_collect_downloads_exact_artifact_and_rechecks_endpoint(
    request_record: dict, run_record: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise the full successful collection path without contacting Azure or GitHub."""
    target = tmp_path / "request.json"
    target.write_text(json.dumps(request_record), encoding="utf-8")
    result = {
        "schema_version": 1, "repository": REPOSITORY, "commit": COMMIT,
        "display_name": request_record["display_name"], "app_name": request_record["app_name"],
        "connect_dataverse": True, "run_id": "123", "run_attempt": "1", "source": "Dataverse",
        "health_status": 200, "page_status": 200,
        "run_url": f"https://github.com/{REPOSITORY}/actions/runs/123",
        "url": "https://synthetic-rehearsal-abc123.example.azurecontainerapps.io",
    }
    calls = []

    def invoke(command: list[str], **kwargs: object) -> str:
        calls.append(command)
        if command[:3] == ["gh", "run", "list"]:
            return json.dumps([run_record])
        assert command[:4] == ["gh", "run", "download", "123"]
        assert command[command.index("--name") + 1] == "deployment-result-123-1"
        directory = Path(command[command.index("--dir") + 1])
        (directory / "deployment-result.json").write_text(json.dumps(result), encoding="utf-8")
        return ""

    def verify(url: str, **kwargs: object) -> dict:
        assert url == result["url"]
        assert kwargs == {"label": request_record["display_name"], "commit": COMMIT, "dataverse": True}
        return {"url": url, "commit": COMMIT, "source": "Dataverse"}

    monkeypatch.setattr(deploy, "invoke", invoke)
    monkeypatch.setattr(deploy, "verify", verify)
    assert deploy.collect(target, wait=False) == 0
    assert len(calls) == 2
    assert json.loads((tmp_path / "deployment-result-123-1.json").read_text(encoding="utf-8")) == result
    assert (tmp_path / "endpoint-123-1.json").is_file()


def test_website_result_requires_target_and_fingerprints(request_record: dict, run_record: dict) -> None:
    """An old vendor artifact or an edited website must not satisfy Monday's request."""
    request = {**request_record, "target": "website", "connect_dataverse": False,
               "app_name": "synthetic-web", "expected_site": {"digest": "c" * 64, "index_sha256": "d" * 64}}
    result = {
        "schema_version": 1, "repository": REPOSITORY, "commit": COMMIT,
        "display_name": request["display_name"], "app_name": "synthetic-web",
        "target": "website", "connect_dataverse": False, "run_id": "123", "run_attempt": "1",
        "source": "website", "health_status": 200, "page_status": 200,
        "run_url": f"https://github.com/{REPOSITORY}/actions/runs/123",
        "url": "https://synthetic-web.example.azurecontainerapps.io",
        "site_digest": "c" * 64, "index_sha256": "d" * 64,
    }
    deploy.validate_result(result, request, run_record)
    for key in ("target", "site_digest", "index_sha256"):
        with pytest.raises(ValueError):
            deploy.validate_result({**result, key: "wrong"}, request, run_record)


def test_website_cannot_request_dataverse(tmp_path: Path) -> None:
    """Reject a conflicting target before making GitHub calls or writing a request."""
    with pytest.raises(ValueError, match="website without Dataverse"):
        deploy.dispatch(REPOSITORY, "main", tmp_path / "request.json",
                        dataverse=True, approved=True, deployment_target="website")
    assert not list(tmp_path.iterdir())