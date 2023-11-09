import os
from pathlib import Path
from invoke import Context, task

MAIN_DIRECTORY_PATH = Path(__file__).parent


@task
def format(context: Context):
    """Run RUFF to format all Python files."""

    exec_cmd = "ruff format ."
    with context.cd(MAIN_DIRECTORY_PATH):
        context.run(exec_cmd)


@task
def lint_ruff(context: Context):
    """Run Linter to check all Python files."""

    exec_cmd = "ruff check ."
    with context.cd(MAIN_DIRECTORY_PATH):
        context.run(exec_cmd)


@task
def lint(context: Context):
    """Run all linters."""

    lint_ruff(context=context)
