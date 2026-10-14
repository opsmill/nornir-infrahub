"""Tests for the pull request release-label gate."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

CHECKER = Path(__file__).resolve().parents[2] / "scripts/check_release_labels.py"


@pytest.mark.parametrize(
    ("author", "labels", "expected_code"),
    [
        ("opsmill-bot", "[]", 0),
        ("maintainer", "[]", 1),
        ("maintainer", '["changes/patch"]', 0),
    ],
)
def test_release_pr_label_exemption_requires_automation_author(author: str, labels: str, expected_code: int) -> None:
    """A matching branch and title do not exempt a human-authored PR."""
    result = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--labels-json",
            labels,
            "--title",
            "chore(release): v1.2.3",
            "--head-ref",
            "release/v1.2.3",
            "--author-login",
            author,
            "--head-repository",
            "opsmill/nornir-infrahub",
            "--repository",
            "opsmill/nornir-infrahub",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == expected_code
    if expected_code:
        assert "found: none" in result.stderr
    else:
        assert not result.stderr


@pytest.mark.parametrize(
    ("labels", "expected_code"),
    [
        ('["ci/skip-changelog"]', 0),
        ('["ci/skip-changelog", "changes/patch"]', 0),
        ('["ci/skip-changelog", "changes/patch", "changes/minor"]', 1),
        ("[]", 1),
    ],
    ids=["skip-changelog-only", "skip-changelog-and-bump-label", "conflicting-bump-labels", "no-labels"],
)
def test_skip_changelog_stands_in_for_a_bump_label(labels: str, expected_code: int) -> None:
    """A pull request labelled ci/skip-changelog needs no bump label, but may not carry two."""
    result = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--labels-json",
            labels,
            "--title",
            "update Infrahub to version 1.11.6 against stable",
            "--head-ref",
            "stable-1.11.6",
            "--author-login",
            "opsmill-bot",
            "--head-repository",
            "opsmill/nornir-infrahub",
            "--repository",
            "opsmill/nornir-infrahub",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == expected_code
    if expected_code:
        assert "exactly one" in result.stderr
    else:
        assert not result.stderr
