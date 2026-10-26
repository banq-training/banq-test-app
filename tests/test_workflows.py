"""Validate checked-in workflow contracts; these are not live Azure tests."""

import json
from pathlib import Path
import subprocess
import tomllib
from unittest.mock import Mock
from urllib.parse import urlsplit

import pytest
import yaml

from app.site import slot_banner
from scripts import create_attendee_repos


@pytest.mark.parametrize("entries,returncode", [
    ([{"name": ".facilitator"}], 0),
    ([{"name": "RUN-OF-SHOW.private.md"}], 0),
    ([{"name": "NN-NA-Hackathon-2026-10-Engagement-Brief.md"}], 0),
    ({"message": "Not Found"}, 1),
    ({"message": "Unexpected shape"}, 0),
])
def test_attendee_repo_creation_fails_closed(
    entries: object, returncode: int, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Private templates and failed inspections cannot reach repository or team writes."""
    command = Mock(return_value=subprocess.CompletedProcess([], returncode, json.dumps(entries), ""))
    create = Mock()
    grant = Mock()
    monkeypatch.setattr(create_attendee_repos, "run", command)
    monkeypatch.setattr(create_attendee_repos, "create_repo", create)
    monkeypatch.setattr(create_attendee_repos, "grant_team", grant)
    monkeypatch.setattr("sys.argv", ["create_attendee_repos.py", "synthetic-team-01"])

    with pytest.raises(SystemExit):
        create_attendee_repos.main()

    create.assert_not_called()
    grant.assert_not_called()
    assert command.call_count == 1
    assert command.call_args.args[0][1] == "api"


def test_attendee_repos_use_the_explicit_clean_template(monkeypatch: pytest.MonkeyPatch) -> None:
    """An approved clean template is inspected before any copy or team grant."""
    command = Mock(return_value=subprocess.CompletedProcess([], 0, '[{"name":"README.md"}]', ""))
    create = Mock(return_value=True)
    grant = Mock(return_value=True)
    monkeypatch.setattr(create_attendee_repos, "run", command)
    monkeypatch.setattr(create_attendee_repos, "create_repo", create)
    monkeypatch.setattr(create_attendee_repos, "grant_team", grant)
    monkeypatch.setattr("sys.argv", [
        "create_attendee_repos.py", "synthetic-team-01", "--template", "synthetic/clean-template",
    ])

    assert create_attendee_repos.main() == 0
    assert command.call_args.args[0][-1] == "repos/synthetic/clean-template/contents"
    create.assert_called_once_with("synthetic-team-01", template="synthetic/clean-template")
    grant.assert_called_once_with("synthetic-team-01")


def test_python_environments_use_the_lockfile() -> None:
    """Local, cloud-agent, deployment and CI dependencies must agree."""
    for path in Path(".github/workflows").glob("*.yml"):
        text = path.read_text(encoding="utf-8")
        workflow = yaml.load(text, Loader=yaml.BaseLoader)
        assert "jobs" in workflow
        if all("uses" in job for job in workflow["jobs"].values()):
            continue  # It only calls a reusable workflow, which this loop checks on its own.
        assert ("uv sync --locked --extra dev --extra web" in text
                or "--file Dockerfile.website" in text), path
    assert "uv sync --locked" in Path("Dockerfile.website").read_text(encoding="utf-8")
    assert Path("uv.lock").is_file()


def test_lockfile_does_not_depend_on_a_corporate_mirror() -> None:
    """A clean Codespace must not inherit the presenter's package proxy."""
    lock = tomllib.loads(Path("uv.lock").read_text(encoding="utf-8"))
    for package in lock["package"]:
        if "registry" not in package["source"]:
            continue
        assert package["source"]["registry"] == "https://pypi.org/simple"
        artifacts = package.get("wheels", []) + [package["sdist"]]
        assert all(urlsplit(artifact["url"]).hostname == "files.pythonhosted.org" for artifact in artifacts)


def test_dataverse_deployment_is_opt_in_and_uses_secret_references() -> None:
    """Day one needs no Dataverse; day two must configure the actual server."""
    path = Path(".github/workflows/deploy.yml")
    workflow = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)

    assert workflow["on"]["workflow_dispatch"]["inputs"]["connect_dataverse"]["default"] == "false"
    assert "secretref:dataverse-client-secret" in path.read_text(encoding="utf-8")
    assert "Source: Dataverse" in path.read_text(encoding="utf-8")


def test_docker_context_excludes_private_material() -> None:
    """Git ignore rules alone do not protect a remote Docker build context."""
    patterns = Path(".dockerignore").read_text(encoding="utf-8").splitlines()

    assert "*.private.md" in patterns
    assert "NN-NA-Hackathon-2026-10-Engagement-Brief.md" in patterns
    assert "/.facilitator/" in patterns
    assert ".env*" in patterns
    assert ".git" in patterns


def test_ci_builds_both_deliverables() -> None:
    """Hosted CI must exercise packaging and the image, not only Python unit tests."""
    workflow = yaml.load(Path(".github/workflows/ci.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    commands = [step.get("run", "") for step in workflow["jobs"]["test"]["steps"]]

    assert "uv build --wheel" in commands
    assert "docker build --tag workshop-check ." in commands
    assert "docker build --file Dockerfile.website --tag workshop-website-check ." in commands
    tool_commands = [step.get("run", "") for step in workflow["jobs"]["research-tools"]["steps"]]
    assert workflow["jobs"]["research-tools"]["runs-on"] == "ubuntu-22.04"
    tool_script = "\n".join(tool_commands)
    assert "bash .devcontainer/setup.sh browser" in tool_script
    assert "bash .devcontainer/setup.sh research" in tool_script
    assert ".venv-research/bin/python scripts/check_workshop_mcp.py" in tool_commands


def test_public_deployments_disable_training_writes() -> None:
    """Both creation and redeployment must override any previously enabled training form."""
    workflow = yaml.load(Path(".github/workflows/deploy.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    deploy = next(step for step in workflow["jobs"]["deploy"]["steps"]
                  if step.get("name") == "Deploy to Container Apps")
    assert deploy["run"].count('"WORKSHOP_ALLOW_WRITES=false"') == 2
    assert "WORKSHOP_ALLOW_WRITES=true" not in deploy["run"]


def test_deployment_publishes_exact_revision_evidence_without_attendee_login() -> None:
    """A successful run must yield a verified artifact, not only a printed hostname."""
    text = Path(".github/workflows/deploy.yml").read_text(encoding="utf-8")
    workflow = yaml.load(text, Loader=yaml.BaseLoader)
    inputs = workflow["on"]["workflow_dispatch"]["inputs"]
    assert inputs["expected_sha"]["default"] == ""
    assert inputs["rehearsal_id"]["default"] == ""
    assert "inputs.rehearsal_id" in workflow["run-name"]
    steps = workflow["jobs"]["deploy"]["steps"]
    upload = next(step for step in steps if step.get("uses") == "actions/upload-artifact@v4")
    assert upload["with"]["path"] == "deployment-result.json"
    assert upload["with"]["if-no-files-found"] == "error"
    assert "github.run_id" in upload["with"]["name"]
    assert "github.run_attempt" in upload["with"]["name"]
    assert "--remove-env-vars DATAVERSE_URL" in text
    assert "WORKSHOP_COMMIT=$GITHUB_SHA" in text
    assert "python -m scripts.deployment_result" in text
    assert "az login" not in text


def test_website_target_is_separate_and_validated_before_build() -> None:
    """Only an intentional site folder can enter the Day 1 image."""
    text = Path(".github/workflows/deploy.yml").read_text(encoding="utf-8")
    workflow = yaml.load(text, Loader=yaml.BaseLoader)
    target = workflow["on"]["workflow_dispatch"]["inputs"]["target"]
    assert target["options"] == ["website", "vendor"]
    assert target["default"] == "website"
    assert text.index("python -m app.site --check") < text.index("az acr build")
    dockerfile = Path("Dockerfile.website").read_text(encoding="utf-8")
    assert "COPY site ./site" in dockerfile
    assert "COPY . " not in dockerfile
    assert "app.site:app" in dockerfile
    assert "research" not in dockerfile
    assert "site/**/*.md" in Path(".dockerignore").read_text(encoding="utf-8")
    assert "uv run --no-sync python -m app.site --check" in text
    assert "uv run --no-sync python -m scripts.deployment_result" in text
    assert "uv run --no-sync python -m app.site --check" in Path(".github/workflows/ci.yml").read_text(encoding="utf-8")


PUBLISHER = Path(".github/workflows/website-publisher.yml")
PUBLISHER_REF = "agentic-dev-labs/copilot-hackathon-template/.github/workflows/website-publisher.yml"


def test_website_publisher_signs_in_without_a_secret() -> None:
    """Attendee publishing uses GitHub's signed token, never a stored Azure credential."""
    text = PUBLISHER.read_text(encoding="utf-8")
    workflow = yaml.load(text, Loader=yaml.BaseLoader)
    assert list(workflow["on"]) == ["workflow_call"]
    assert workflow["permissions"] == {"contents": "read"}
    jobs = workflow["jobs"]
    assert jobs["prepare"]["permissions"] == {"contents": "read"}
    assert jobs["publish"]["permissions"] == {"contents": "read", "id-token": "write"}
    assert jobs["show-link"]["permissions"] == {}
    assert "secrets." not in text and "AZURE_CREDENTIALS" not in text and "creds:" not in text
    login = next(step for step in jobs["publish"]["steps"] if step.get("uses", "").startswith("azure/login@"))
    assert set(login["with"]) == {"client-id", "tenant-id", "subscription-id"}


def test_only_trusted_code_runs_next_to_the_azure_sign_in() -> None:
    """The signed-in job builds from the template and receives the attendee's site/ only as data."""
    workflow = yaml.load(PUBLISHER.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    jobs = workflow["jobs"]
    steps = jobs["publish"]["steps"]
    checkout = steps[0]
    assert checkout["uses"].startswith("actions/checkout@")
    assert checkout["with"] == {
        "repository": "agentic-dev-labs/copilot-hackathon-template", "ref": "main", "persist-credentials": "false",
    }
    assert sum(step.get("uses", "").startswith("actions/checkout@") for step in steps) == 1

    def position(predicate: object) -> int:
        return next(index for index, step in enumerate(steps) if predicate(step))

    login = position(lambda step: step.get("uses", "").startswith("azure/login@"))
    assert position(lambda step: "[[ \"$WEBSITE_NAME\" =~" in step.get("run", "")) < login
    assert position(lambda step: step.get("uses", "").startswith("actions/download-artifact@")) < login
    assert position(lambda step: "-m app.site --check" in step.get("run", "")) < login
    prepare_checkout = next(step for step in jobs["prepare"]["steps"]
                            if step.get("uses", "").startswith("actions/checkout@"))
    assert prepare_checkout["with"] == {"ref": "${{ inputs.commit }}", "persist-credentials": "false"}
    assert "The slot is production or feature" in jobs["prepare"]["steps"][0]["run"], "inputs checked first"
    assert {job["runs-on"] for job in jobs.values()} == {"ubuntu-24.04"}, "pinned for a stable workshop week"
    for job in jobs.values():
        for step in job["steps"]:
            assert "${{" not in step.get("run", ""), "untrusted values reach scripts only through env"


def test_publisher_protects_other_websites_and_cost() -> None:
    """A repository can update only its own website, which scales to zero."""
    text = PUBLISHER.read_text(encoding="utf-8")
    assert '"github-repository-id": $owner' in text and '--arg owner "$REPOSITORY_ID"' in text
    assert "already used by another repository" in text
    assert text.count('!= "$REPOSITORY_ID"') == 2
    assert text.index("already used by another repository") < text.index("az rest --method put")
    assert "scale: {minReplicas: $awake, maxReplicas: 1}" in text
    assert yaml.load(text, Loader=yaml.BaseLoader)["env"]["MIN_REPLICAS"] in {"0", "1"}
    assert 'resources: {cpu: 0.25, memory: "0.5Gi"}' in text
    assert "registries: [{server: $registry, identity: $identity}]" in text
    assert "az acr build" not in text and "az containerapp create" not in text
    assert '= "$PUBLISH_COMMIT"' in text and '= "$DIGEST"' in text and '= "$INDEX"' in text
    # Cleaning up a renamed website stays inside one slot: production never removes the feature slot.
    assert '(.slot // "production") == $slot' in text and '"website-slot": $slot' in text


def test_publish_caller_only_calls_the_template_publisher() -> None:
    """The attendee's copy is a short trigger that skips the template itself."""
    workflow = yaml.load(Path(".github/workflows/publish-website.yml").read_text(encoding="utf-8"),
                         Loader=yaml.BaseLoader)
    assert workflow["on"]["push"]["branches"] == ["main"]
    assert set(workflow["on"]["push"]["paths"]) == {"site/**", "config.json"}
    assert "workflow_dispatch" in workflow["on"]
    assert workflow["permissions"] == {"contents": "read", "id-token": "write"}
    job = workflow["jobs"]["publish"]
    assert job["uses"] == f"{PUBLISHER_REF}@main"
    assert job["if"] == "${{ !github.event.repository.is_template }}"


def test_template_ships_without_a_website_name() -> None:
    """Only the template runs CI; it insists on an empty name, which attendees set with /publish-website."""
    workflow = yaml.load(Path(".github/workflows/ci.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    for job in workflow["jobs"].values():
        assert job["if"] == "${{ github.event.repository.is_template }}"
    # A learner-work pull request (the cloud agent's) must not ask the attendee to approve a run.
    assert {"site/**", "config.json", "checks/test_*.py", "checks/*_test.py", "reviews/**"} <= set(
        workflow["on"]["pull_request"]["paths-ignore"])
    assert "paths-ignore" not in (workflow["on"]["push"] or {}), "pushes to main always run the guard"
    steps = workflow["jobs"]["test"]["steps"]
    guard = next(step for step in steps if step.get("name") == "Keep the template free of learner work")
    assert "jq -e '.websiteName == \"\"' config.json" in guard["run"]
    for learner_file in (".github/agents/user-requirements.agent.md", ".github/agents/code-review.agent.md",
                         "'.github/workflows/check-my-website.yml'", "'.github/workflows/deploy-feature-slot.yml'",
                         "'checks/test_*.py'", "'checks/*_test.py'", "reviews", "HANDOFF.md"):
        assert learner_file in guard["run"]


STARTERS = Path(".github/workflow-starters")


def test_check_starter_is_inert_until_the_learner_edits_it() -> None:
    """Day 5: the starter runs only by hand and asks for exactly two edits, triggers and permissions."""
    text = (STARTERS / "check-my-website.yml").read_text(encoding="utf-8")
    workflow = yaml.load(text, Loader=yaml.BaseLoader)
    assert workflow["name"] == "Check my website"
    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert workflow["permissions"] == {"contents": "write"}, "the learner reduces this to read"
    assert "add pull_request" in text and 'Change "write" to "read"' in text
    steps = workflow["jobs"]["check"]["steps"]
    commands = "\n".join(step.get("run", "") for step in steps)
    assert "uv run python -m app.site --check" in commands and "uv run pytest checks" in commands
    assert "secrets." not in text and "id-token" not in text
    assert steps[0]["with"]["persist-credentials"] == "false"
    # After the two documented edits the workflow is a least-privilege pull-request check.
    edited = yaml.load(
        text.replace("on:\n  workflow_dispatch:\n",
                     "on:\n  workflow_dispatch:\n  pull_request:\n  push:\n    branches: [main]\n")
            .replace("contents: write", "contents: read"),
        Loader=yaml.BaseLoader,
    )
    assert {"workflow_dispatch", "pull_request", "push"} == set(edited["on"])
    assert edited["permissions"] == {"contents": "read"}


def test_approval_starter_only_adds_a_gate_before_the_same_publisher() -> None:
    """Day 5 CD: an environment gate in the learner's caller; the trusted publisher is unchanged."""
    current = yaml.load(Path(".github/workflows/publish-website.yml").read_text(encoding="utf-8"),
                        Loader=yaml.BaseLoader)
    text = (STARTERS / "publish-website-with-approval.yml").read_text(encoding="utf-8")
    starter = yaml.load(text, Loader=yaml.BaseLoader)
    for key in ("name", "on", "permissions", "concurrency"):
        assert starter[key] == current[key], key
    approve, publish = starter["jobs"]["approve"], starter["jobs"]["publish"]
    assert approve["environment"] == "production" and "uses" not in approve
    assert approve["if"] == current["jobs"]["publish"]["if"]
    assert publish["needs"] == "approve"
    # The publish job carries no environment, so its OIDC subject stays refs/heads/main.
    assert "environment" not in publish
    # The only other difference: the version learners switched on during Day 4 stays on.
    expected = dict(current["jobs"]["publish"])
    expected["with"] = {**expected["with"], "version": "1.0.${{ github.run_number }}"}
    assert {key: value for key, value in publish.items() if key != "needs"} == expected
    assert "secrets." not in text and "Required reviewers" in text


def test_feature_slot_starter_deploys_checked_pull_requests_from_main() -> None:
    """Day 5: each pull request whose checks pass gets a test copy; Azure's trust is unchanged."""
    text = (STARTERS / "deploy-feature-slot.yml").read_text(encoding="utf-8")
    workflow = yaml.load(text, Loader=yaml.BaseLoader)
    checks = yaml.load((STARTERS / "check-my-website.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    # workflow_run runs main's copy of this file on main, so the OIDC subject is still refs/heads/main.
    assert workflow["on"] == {"workflow_run": {"workflows": [checks["name"]], "types": ["completed"]}}
    assert workflow["permissions"] == {}
    publish, link = workflow["jobs"]["publish"], workflow["jobs"]["link"]
    assert publish["uses"] == f"{PUBLISHER_REF}@main" and "environment" not in publish
    assert publish["permissions"] == {"contents": "read", "id-token": "write"}
    for condition in ("!github.event.repository.is_template", "github.event.workflow_run.event == 'pull_request'",
                      "github.event.workflow_run.conclusion == 'success'"):
        assert condition in publish["if"]
    assert publish["with"] == {
        "website-name": "${{ vars.WEBSITE_NAME }}", "slot": "feature",
        "commit": "${{ github.event.workflow_run.head_sha }}",
        "pull-request": "${{ github.event.workflow_run.pull_requests[0].number }}",
        "version": "1.0.${{ github.run_number }}-feature",
    }
    # Only deploying runs share the slot, so a skipped run for a push to main cancels nothing.
    assert publish["concurrency"] == {"group": "feature-slot", "cancel-in-progress": "true"}
    assert link["permissions"] == {"deployments": "write", "statuses": "write"} and link["needs"] == "publish"
    script = link["steps"][0]["run"]
    # A deployment for the pull request's own commit gives it a View deployment button.
    assert '{ref: $ref, environment: "feature-slot"' in script and "required_contexts: []" in script
    assert "context=\"Feature slot\"" in script and "${{" not in script
    assert "secrets." not in text and "id-token" not in str(link)


def test_publisher_keeps_the_slots_apart() -> None:
    """The feature slot has its own name, image, strip check, and link; production is unchanged."""
    text = PUBLISHER.read_text(encoding="utf-8")
    workflow = yaml.load(text, Loader=yaml.BaseLoader)
    inputs = workflow["on"]["workflow_call"]["inputs"]
    assert inputs["slot"]["default"] == "production"
    assert inputs["commit"]["default"] == "" and inputs["pull-request"]["default"] == ""
    assert workflow["jobs"]["publish"]["env"]["PUBLISH_COMMIT"] == "${{ inputs.commit || github.sha }}"
    assert 'NAME="$(printf \'%s\' "${NAME:0:24}" | sed -E \'s/-+$//\')-feature"' in text, "32 characters at most"
    assert ":feature-$PUBLISH_COMMIT" in text, "waking production never loads a feature build"
    # The publisher looks for the same strip the website server adds.
    assert 'data-workshop-slot="feature"' in text and 'data-workshop-slot="feature"' in slot_banner(
        {"WEBSITE_SLOT": "feature"})
    show_link = workflow["jobs"]["show-link"]
    assert show_link["environment"]["name"] == "${{ inputs.slot == 'feature' && 'feature-slot' || 'website' }}"


def test_day_four_version_line_is_one_hash_away_from_the_publisher() -> None:
    """Day 4: removing one # makes the caller pass its run number as the website version."""
    text = Path(".github/workflows/publish-website.yml").read_text(encoding="utf-8")
    assert "      # version: 1.0.${{ github.run_number }}\n" in text
    # The file's own comment must give the same edit as the guide: the # and the space after it.
    assert "on the next line, delete the # and the space after it" in text
    switched_on = yaml.load(text.replace("      # version:", "      version:"), Loader=yaml.BaseLoader)
    assert switched_on["jobs"]["publish"]["with"]["version"] == "1.0.${{ github.run_number }}"
    publisher = yaml.load(PUBLISHER.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    version_input = publisher["on"]["workflow_call"]["inputs"]["version"]
    assert version_input["required"] == "false" and version_input["default"] == ""


def test_publisher_writes_the_version_as_data_before_the_build() -> None:
    """The version is validated, written by jq from env, and lands in the image it verifies."""
    workflow = yaml.load(PUBLISHER.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    job = workflow["jobs"]["publish"]
    assert job["env"]["WEBSITE_VERSION"] == "${{ inputs.version }}"
    steps = job["steps"]
    stamp = next(index for index, step in enumerate(steps) if "site/version.json" in step.get("run", ""))
    download = next(index for index, step in enumerate(steps)
                    if step.get("uses", "").startswith("actions/download-artifact@"))
    build = next(index for index, step in enumerate(steps) if "docker build" in step.get("run", ""))
    assert download < stamp < build
    assert steps[stamp]["if"] == "${{ inputs.version != '' }}"
    script = steps[stamp]["run"]
    assert '[[ "$WEBSITE_VERSION" =~ ^[0-9A-Za-z][0-9A-Za-z.+_-]{0,39}$ ]]' in script
    assert '--arg version "$WEBSITE_VERSION"' in script and '--argjson build "$GITHUB_RUN_NUMBER"' in script


def test_hosting_trusts_only_the_template_publisher_on_main() -> None:
    """Azure must accept tokens only from the organisation's main branches and this publisher."""
    bicep = Path("infra/website-hosting.bicep").read_text(encoding="utf-8")
    expression = bicep.split("claimsMatchingExpression", 1)[1].split("languageVersion", 1)[0]
    assert "claims[\\'sub\\'] matches \\'repo:${githubOrganization}@${githubOrganizationId}/*:ref:refs/heads/main\\'" in expression
    assert "claims[\\'repository_owner_id\\'] eq \\'${githubOrganizationId}\\'" in expression
    assert "claims[\\'job_workflow_ref\\'] eq \\'${publisherWorkflow}\\'" in expression
    assert f"'{PUBLISHER_REF}@refs/heads/main'" in bicep
    assert "adminUserEnabled: false" in bicep
    assert "'b24988ac-6180-42a0-ab88-20f7382dd24c'" not in bicep  # no broad Contributor role


def test_publish_skill_names_the_hosting_domain() -> None:
    """The skill predicts the same address that the publisher verifies."""
    workflow = yaml.load(PUBLISHER.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    domain = workflow["env"]["WEBSITE_DOMAIN"]
    skill = Path(".github/skills/publish-website/SKILL.md").read_text(encoding="utf-8")
    assert skill.count(f"https://<name>.{domain}") == 2
    assert "disable-model-invocation: true" in skill
    assert "Never add credentials" in skill