"""Shared helpers for Nornir Infrahub plugins."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from infrahub_sdk import InfrahubClientSync
    from nornir.core.task import Task


def get_client(task: Task) -> InfrahubClientSync:
    """Return the ``InfrahubClientSync`` attached to the Nornir host by the inventory plugin."""
    return task.host.data["InfrahubNode"]._client
