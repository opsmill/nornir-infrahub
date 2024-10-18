import httpx
from nornir.core.task import Result, Task


def regenerate_host_artifact(task: Task, artifact: str) -> Result:
    node = task.host.data["InfrahubNode"]
    node.artifact_generate(name=artifact)
    return Result(host=task.host, failed=False)


def generate_artifacts(task: Task, artifact: str, timeout: int = 10) -> Result:
    node = task.host.data["InfrahubNode"]
    artifact_definition = node._client.get(kind="CoreArtifactDefinition", artifact_name__value=artifact)
    artifact_definition.generate()
    return Result(host=task.host, failed=False)


def get_artifact(task: Task, artifact: str) -> Result:
    data = task.host.data["InfrahubNode"].artifact_fetch(name=artifact)
    return Result(host=task.host, failed=False, content_type=artifact_node.content_type.value, result=data)
