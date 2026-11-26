"""Check the result types that a type checker reads from the task annotations.

`assert_type` does nothing at runtime. `invoke lint-ty` checks this file.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from nornir.core.task import AggregatedResult
from nornir_infrahub.plugins.tasks import (
    FileObjectDownload,
    adownload_file_object,
    agenerate_artifacts,
    aget_artifact,
    aregenerate_host_artifact,
    aupload_file_object,
    download_file_object,
    generate_artifacts,
    get_artifact,
    regenerate_host_artifact,
    upload_file_object,
)
from typing_extensions import assert_type

if TYPE_CHECKING:
    from nornir.core import Nornir


def check_sync_tasks(nr: Nornir) -> None:
    assert_type(nr.run(task=regenerate_host_artifact, artifact="startup-config"), AggregatedResult[None])
    assert_type(nr.run(task=generate_artifacts, artifact="startup-config"), AggregatedResult[None])
    assert_type(nr.run(task=get_artifact, artifact="startup-config"), AggregatedResult[Any])
    assert_type(nr.run(task=upload_file_object, kind="NetworkContract"), AggregatedResult[str])

    downloads = nr.run(task=download_file_object, kind="NetworkContract", hfid=["contract-2026"])
    assert_type(downloads, AggregatedResult[FileObjectDownload])
    assert_type(downloads["edge1"].result.file_name, str)


async def check_async_tasks(nr: Nornir) -> None:
    assert_type(await nr.arun(task=aregenerate_host_artifact, artifact="startup-config"), AggregatedResult[None])
    assert_type(await nr.arun(task=agenerate_artifacts, artifact="startup-config"), AggregatedResult[None])
    assert_type(await nr.arun(task=aget_artifact, artifact="startup-config"), AggregatedResult[Any])
    assert_type(await nr.arun(task=aupload_file_object, kind="NetworkContract"), AggregatedResult[str])

    downloads = await nr.arun(task=adownload_file_object, kind="NetworkContract", hfid=["contract-2026"])
    assert_type(downloads, AggregatedResult[FileObjectDownload])
    assert_type(downloads["edge1"].result.file_name, str)


def test_the_typed_tasks_are_importable() -> None:
    assert callable(check_sync_tasks)
    assert callable(check_async_tasks)
