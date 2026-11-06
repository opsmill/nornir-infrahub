"""
Artifact management plugin
"""

import json
from typing import Any, Optional

from nornir.core.task import Result, Task
from nornir_infrahub.utils import get_async_node, get_node


def regenerate_host_artifact(task: Task, artifact: str) -> Result:
    """
    Regenerates a host artifact for a given task.

    This function regenerates the named artifact for the host's InfrahubNode through the Infrahub SDK.

    Args:
        task (Task): The task instance containing host-related data.
        artifact (str): The name of the artifact to regenerate.

    Returns:
        Result: An object representing the outcome of the operation, indicating success or failure.

    Raises:
        Exception: Propagates any error raised by the Infrahub SDK if the artifact cannot be generated.

    Example:
        Regenerate artifact for a given device

        ```python
        from nornir import InitNornir
        from nornir_infrahub.plugins.tasks import regenerate_host_artifact

        from nornir_utils.plugins.functions import print_result


        def main():
            nr = InitNornir(inventory=...)

            eos_devices = nr.filter(platform="eos")

            # regenerate an artifact for a host
            print_result(eos_devices.run(task=regenerate_host_artifact, artifact="startup-config"))

            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
        ```
    """
    node = get_node(task)
    node.artifact_generate(name=artifact)

    return Result(host=task.host, failed=False)


async def aregenerate_host_artifact(task: Task, artifact: str) -> Result:
    """
    Regenerates a host artifact for a given task, without blocking the event loop.

    Asynchronous variant of `regenerate_host_artifact`, for an inventory loaded with
    `AInitNornir` and run with `Nornir.arun`.

    Args:
        task (Task): The task instance containing host-related data.
        artifact (str): The name of the artifact to regenerate.

    Returns:
        Result: An object representing the outcome of the operation, indicating success or failure.

    Raises:
        Exception: Propagates any error raised by the Infrahub SDK if the artifact cannot be generated.

    Example:
        Regenerate artifact for a given device from a running event loop

        ```python
        from nornir import AInitNornir
        from nornir_infrahub.plugins.tasks import aregenerate_host_artifact


        async def main():
            nr = await AInitNornir(runner={"plugin": "asyncio"}, inventory=...)
            result = await nr.filter(platform="eos").arun(task=aregenerate_host_artifact, artifact="startup-config")
        ```
    """
    node = get_async_node(task)
    await node.artifact_generate(name=artifact)

    return Result(host=task.host, failed=False)


def generate_artifacts(task: Task, artifact: str, timeout: int = 10) -> Result:  # pylint: disable=unused-argument
    """
    Generates an artifact for a given task.

    This function retrieves the artifact definition from the InfrahubNode and triggers
    its generation through the Infrahub SDK.

    Args:
        task (Task): The task instance containing host-related data.
        artifact (str): The name of the artifact to generate.
        timeout (int, optional): Retained for compatibility; ignored by the SDK path. Defaults to 10.

    Returns:
        Result: An object representing the outcome of the operation, indicating success or failure.

    Raises:
        Exception: Propagates any error raised by the Infrahub SDK if the artifact cannot be generated.

    Example:
        Example generating artifacts

        ```python
        from nornir import InitNornir
        from nornir_infrahub.plugins.tasks import generate_artifacts


        def main():
            nr = InitNornir(inventory=...)

            # generate_artifacts, generates the artifact for all the targets in the Artifact definition
            # we only need to run this task once, per artifact definition
            run_once = nr.filter(name="jfk1-edge1")
            result = run_once.run(task=generate_artifacts, artifact="startup-config", timeout=20)
            ocfg_result = run_once.run(task=generate_artifacts, artifact="openconfig-interfaces", timeout=20)

            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
        ```
    """
    node = get_node(task)
    artifact_definition = node._client.get(kind="CoreArtifactDefinition", artifact_name__value=artifact)
    artifact_definition.generate()

    return Result(host=task.host, failed=False)


async def agenerate_artifacts(task: Task, artifact: str, timeout: int = 10) -> Result:  # pylint: disable=unused-argument
    """
    Generates an artifact for a given task, without blocking the event loop.

    Asynchronous variant of `generate_artifacts`, for an inventory loaded with
    `AInitNornir` and run with `Nornir.arun`.

    Args:
        task (Task): The task instance containing host-related data.
        artifact (str): The name of the artifact to generate.
        timeout (int, optional): Retained for compatibility; ignored by the SDK path. Defaults to 10.

    Returns:
        Result: An object representing the outcome of the operation, indicating success or failure.

    Raises:
        Exception: Propagates any error raised by the Infrahub SDK if the artifact cannot be generated.

    Example:
        Example generating artifacts from a running event loop

        ```python
        from nornir import AInitNornir
        from nornir_infrahub.plugins.tasks import agenerate_artifacts


        async def main():
            nr = await AInitNornir(runner={"plugin": "asyncio"}, inventory=...)

            # the task generates the artifact for all the targets of the artifact definition,
            # so it only needs to run on one host
            run_once = nr.filter(name="jfk1-edge1")
            result = await run_once.arun(task=agenerate_artifacts, artifact="startup-config")
        ```
    """
    node = get_async_node(task)
    artifact_definition = await node._client.get(kind="CoreArtifactDefinition", artifact_name__value=artifact)
    await artifact_definition.generate()

    return Result(host=task.host, failed=False)


def get_artifact(task: Task, artifact: Optional[str] = None, artifact_id: Optional[str] = None) -> Result:
    """
    Retrieves the specified artifact from the Infrahub storage.

    This function fetches an artifact node associated with the given artifact name or id and
    sends a request to retrieve its stored content. The response is returned as JSON or text,
    depending on the artifact's content type.

    Args:
        task (Task): The task instance containing host-related data.
        artifact (str, optional): The name of the artifact to retrieve.
        artifact_id (str, optional): The id of the artifact to retrieve.

    Returns:
        Result: An object containing the retrieved artifact data, its content type, and
                the success status of the operation.

    Raises:
        RuntimeError: If neither or both of `artifact` and `artifact_id` are provided.
        Exception: Propagates any error raised by the Infrahub SDK if the artifact cannot be retrieved.

    Example:
        Example getting artifacts from Infrahub

        ```python
        from nornir import InitNornir
        from nornir_infrahub.plugins.tasks import get_artifact
        from nornir_utils.plugins.functions import print_result


        def main():
            nr = InitNornir(inventory=...)

            eos_devices = nr.filter(platform="eos")
            # retrieves the artifact for all the hosts in the inventory
            result = eos_devices.run(task=get_artifact, artifact="startup-config")
            print_result(result)

            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
        ```
    """
    _check_artifact_args(artifact, artifact_id, "get_artifact")

    node = get_node(task)
    client = node._client

    if artifact:
        artifact_node = client.get(kind="CoreArtifact", name__value=artifact, object__ids=[node.id])
    else:
        artifact_node = client.get(kind="CoreArtifact", ids=[artifact_id])

    content = client.object_store.get(identifier=artifact_node.storage_id.value)

    return _artifact_result(task, artifact_node, content)


async def aget_artifact(task: Task, artifact: Optional[str] = None, artifact_id: Optional[str] = None) -> Result:
    """
    Retrieves the specified artifact from the Infrahub storage, without blocking the event loop.

    Asynchronous variant of `get_artifact`, for an inventory loaded with `AInitNornir`
    and run with `Nornir.arun`.

    Args:
        task (Task): The task instance containing host-related data.
        artifact (str, optional): The name of the artifact to retrieve.
        artifact_id (str, optional): The id of the artifact to retrieve.

    Returns:
        Result: An object containing the retrieved artifact data, its content type, and
                the success status of the operation.

    Raises:
        RuntimeError: If neither or both of `artifact` and `artifact_id` are provided.
        Exception: Propagates any error raised by the Infrahub SDK if the artifact cannot be retrieved.

    Example:
        Example getting artifacts from Infrahub from a running event loop

        ```python
        from nornir import AInitNornir
        from nornir_infrahub.plugins.tasks import aget_artifact
        from nornir_utils.plugins.functions import print_result


        async def main():
            nr = await AInitNornir(runner={"plugin": "asyncio"}, inventory=...)
            result = await nr.filter(platform="eos").arun(task=aget_artifact, artifact="startup-config")
            print_result(result)
        ```
    """
    _check_artifact_args(artifact, artifact_id, "aget_artifact")

    node = get_async_node(task)
    client = node._client

    if artifact:
        artifact_node = await client.get(kind="CoreArtifact", name__value=artifact, object__ids=[node.id])
    else:
        artifact_node = await client.get(kind="CoreArtifact", ids=[artifact_id])

    content = await client.object_store.get(identifier=artifact_node.storage_id.value)

    return _artifact_result(task, artifact_node, content)


def _check_artifact_args(artifact: Optional[str], artifact_id: Optional[str], task_name: str) -> None:
    if (artifact and artifact_id) or not (artifact or artifact_id):
        raise RuntimeError(
            f"One of `artifact' or `artifact_id' arguments needs to be provided for the `{task_name}' task."
        )


def _artifact_result(task: Task, artifact_node: Any, content: str) -> Result:
    if artifact_node.content_type.value == "application/json":
        data = json.loads(content)
    else:
        data = content

    return Result(host=task.host, failed=False, content_type=artifact_node.content_type.value, result=data)
