"""
Artifact management plugin
"""

import json
from typing import Optional

from nornir.core.task import Result, Task


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
        from nornir.core.plugins.inventory import InventoryPluginRegister
        from nornir_infrahub.plugins.inventory.infrahub import InfrahubInventory
        from nornir_infrahub.plugins.tasks import regenerate_host_artifact

        from nornir_utils.plugins.functions import print_result


        def main():
            InventoryPluginRegister.register("InfrahubInventory", InfrahubInventory)
            nr = InitNornir(inventory=...)

            eos_devices = nr.filter(platform="eos")

            # regenerate an artifact for a host
            print_result(eos_devices.run(task=regenerate_host_artifact, artifact="startup-config"))

            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
        ```
    """
    node = task.host.data["InfrahubNode"]
    node.artifact_generate(name=artifact)

    return Result(host=task.host, failed=False)


def generate_artifacts(task: Task, artifact: str, timeout: int = 10) -> Result:  # pylint: disable=unused-argument
    """
    Generates an artifact for a given task.

    This function retrieves the artifact definition from the InfrahubNode and triggers
    its generation through the Infrahub SDK.

    Args:
        task (Task): The task instance containing host-related data.
        artifact (str): The name of the artifact to generate.
        timeout (int, optional): Retained for backwards compatibility. The SDK now manages
            request timeouts via its client configuration, so this argument is ignored.

    Returns:
        Result: An object representing the outcome of the operation, indicating success or failure.

    Raises:
        Exception: Propagates any error raised by the Infrahub SDK if the artifact cannot be generated.

    Example:
        Example generating artifacts

        ```python
        from nornir import InitNornir
        from nornir.core.plugins.inventory import InventoryPluginRegister
        from nornir_infrahub.plugins.inventory.infrahub import InfrahubInventory
        from nornir_infrahub.plugins.tasks import generate_artifacts


        def main():
            InventoryPluginRegister.register("InfrahubInventory", InfrahubInventory)
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
    node = task.host.data["InfrahubNode"]
    artifact_definition = node._client.get(kind="CoreArtifactDefinition", artifact_name__value=artifact)
    artifact_definition.generate()

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
        from nornir.core.plugins.inventory import InventoryPluginRegister
        from nornir_infrahub.plugins.inventory.infrahub import InfrahubInventory
        from nornir_infrahub.plugins.tasks import get_artifact
        from nornir_utils.plugins.functions import print_result


        def main():
            InventoryPluginRegister.register("InfrahubInventory", InfrahubInventory)
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
    if (artifact and artifact_id) or not (artifact or artifact_id):
        raise RuntimeError(
            "One of `artifact' or `artifact_id' arguments needs to be provided for the `get_artifact' task."
        )

    node = task.host.data["InfrahubNode"]
    client = node._client

    if artifact:
        artifact_node = client.get(kind="CoreArtifact", name__value=artifact, object__ids=[node.id])
    elif artifact_id:
        artifact_node = client.get(kind="CoreArtifact", ids=[artifact_id])

    content = client.object_store.get(identifier=artifact_node.storage_id.value)

    if artifact_node.content_type.value == "application/json":
        data = json.loads(content)
    else:
        data = content

    return Result(host=task.host, failed=False, content_type=artifact_node.content_type.value, result=data)
