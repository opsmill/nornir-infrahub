"""Shared helpers for Nornir Infrahub plugins."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from infrahub_sdk.node import InfrahubNode, InfrahubNodeSync

if TYPE_CHECKING:
    from infrahub_sdk import InfrahubClient, InfrahubClientSync
    from nornir.core.task import Task


def get_node(task: Task) -> Any:
    """Return the host's `InfrahubNodeSync`, loaded by `InitNornir`.

    Raises:
        TypeError: The host holds an asynchronous `InfrahubNode`, loaded by `AInitNornir`.
    """
    node = task.host.data["InfrahubNode"]
    if isinstance(node, InfrahubNode):
        raise TypeError(
            f"Host '{task.host.name}' was loaded with AInitNornir and holds an asynchronous InfrahubNode; "
            "run the asynchronous variant of this task (prefixed with 'a') with Nornir.arun"
        )
    return node


def get_async_node(task: Task) -> Any:
    """Return the host's asynchronous `InfrahubNode`, loaded by `AInitNornir`.

    Raises:
        TypeError: The host holds an `InfrahubNodeSync`, loaded by `InitNornir`.
    """
    node = task.host.data["InfrahubNode"]
    if isinstance(node, InfrahubNodeSync):
        raise TypeError(
            f"Host '{task.host.name}' was loaded with InitNornir and holds a synchronous InfrahubNodeSync; "
            "load the inventory with AInitNornir to run asynchronous tasks"
        )
    return node


def get_client(task: Task) -> InfrahubClientSync:
    """Return the ``InfrahubClientSync`` attached to the Nornir host by the inventory plugin."""
    return get_node(task)._client


def get_async_client(task: Task) -> InfrahubClient:
    """Return the ``InfrahubClient`` attached to the Nornir host by the inventory plugin."""
    return get_async_node(task)._client
