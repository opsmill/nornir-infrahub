from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parents[2]


def test_general_ci_runs_for_pull_requests_only() -> None:
    workflow = (REPOSITORY_ROOT / ".github/workflows/ci.yml").read_text()
    triggers = workflow.split("on:", maxsplit=1)[1].split("concurrency:", maxsplit=1)[0]

    assert "\n  pull_request:" in triggers
    assert "\n  push:" not in triggers, "general CI still reruns after a pull request is merged"
