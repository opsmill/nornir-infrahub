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
