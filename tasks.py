import sys
from pathlib import Path
from typing import Any

from invoke import Context, task

MAIN_DIRECTORY_PATH = Path(__file__).parent

CURRENT_DIRECTORY = Path(__file__).resolve()
DOCUMENTATION_DIRECTORY = CURRENT_DIRECTORY.parent / "docs"
NORNIR_DOCUMENTATION_DIRECTORY = DOCUMENTATION_DIRECTORY / "docs"

PLUGIN_TYPES: dict[str, str] = {"inventory": "inventory", "tasks": "tasks"}
PLUGINS_DIRECTORY = Path("nornir_infrahub/plugins")


@task(name="format")
def ruff_format(context: Context):
    """Run RUFF to format all Python files."""

    exec_cmds = ["ruff format .", "ruff check . --fix"]
    with context.cd(MAIN_DIRECTORY_PATH):
        for cmd in exec_cmds:
            context.run(cmd)


@task
def lint_yaml(context: Context):
    """Run Linter to check all Python files."""
    print(" - Check code with yamllint")
    exec_cmd = "yamllint ."
    with context.cd(MAIN_DIRECTORY_PATH):
        context.run(exec_cmd)


@task
def lint_mypy(context: Context):
    """Run Linter to check all Python files."""
    print(" - Check code with mypy")
    exec_cmd = "mypy --show-error-codes nornir_infrahub"
    with context.cd(MAIN_DIRECTORY_PATH):
        context.run(exec_cmd)


@task
def lint_ruff(context: Context):
    """Run Linter to check all Python files."""
    print(" - Check code with ruff")
    exec_cmd = "ruff check ."
    with context.cd(MAIN_DIRECTORY_PATH):
        context.run(exec_cmd)


@task
def lint_pylint(context: Context):
    """Run Linter to check all Python files."""
    print(" - Check code with pylint")
    exec_cmd = "pylint nornir_infrahub *.py"
    with context.cd(MAIN_DIRECTORY_PATH):
        context.run(exec_cmd)


@task(name="lint")
def lint_all(context: Context):
    """Run all linters."""
    lint_yaml(context)
    lint_ruff(context)
    lint_pylint(context)
    lint_mypy(context)


@task(name="docs")
def docs_build(context: Context) -> None:
    """Build documentation website."""
    exec_cmd = "npm run build"

    with context.cd(DOCUMENTATION_DIRECTORY):
        output = context.run(exec_cmd)

    if output.exited != 0:
        sys.exit(-1)


# ----------------------------------------------------------------------------
# Documentation tasks
# ----------------------------------------------------------------------------
def find_plugin_files() -> dict[str, list[Path]]:
    """
    Find all plugin files excluding __init__.py.

    Returns:
        dict mapping plugin types to list of plugin files
    """
    plugin_files: dict[str, list[Path]] = {}

    for plugin_type in PLUGIN_TYPES:
        plugin_dir = PLUGINS_DIRECTORY / plugin_type
        if plugin_dir.exists():
            files = [f for f in plugin_dir.glob("**/*.py") if f.name != "__init__.py"]
            if files:
                plugin_files[plugin_type] = files
    return plugin_files


def extract_docstrings(file_path):
    import ast  # pylint: disable=C0415

    from docstring_parser import parse  # pylint: disable=C0415

    with open(file_path, "r", encoding="utf-8") as file:
        tree = ast.parse(file.read(), filename=file_path)

    docstrings = {}

    # Get module-level docstring
    if ast.get_docstring(tree):
        docstrings["module"] = ast.get_docstring(tree)

    # Extract docstrings from classes and functions
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            docstring = ast.get_docstring(node)
            if docstring:
                docstrings[node.name] = parse(docstring)

    return docstrings


@task(
    help={
        "debug": "Enable debug output",
        "plugin_type": f"Generate docs for specific plugin type ({', '.join(PLUGIN_TYPES.keys())})",
    }
)
def generate_docs(context: Context, debug: bool = False, plugin_type: str | None = None) -> None:  # noqa: ARG001 pylint: disable=W0613
    import jinja2  # pylint: disable=C0415

    template_dir = DOCUMENTATION_DIRECTORY / "_templates"
    environment = jinja2.Environment(
        autoescape=False,  # noqa: S701
        trim_blocks=False,
        lstrip_blocks=True,
    )

    plugin_template = environment.from_string((template_dir / "plugin.mdx.j2").read_text())
    readme_template = environment.from_string((template_dir / "readme.mdx.j2").read_text())

    # Process plugins
    plugin_files = find_plugin_files()
    if plugin_type:
        if plugin_type not in PLUGIN_TYPES:
            print(f"Invalid plugin type. Choose from: {', '.join(PLUGIN_TYPES.keys())}")
            sys.exit(-1)
        plugin_files = {plugin_type: plugin_files.get(plugin_type, [])}

    # Store processed plugins for landing page
    processed_plugins: dict[str, list[dict[str, Any]]] = {p_type: [] for p_type in PLUGIN_TYPES}

    # Generate individual plugin pages
    for p_type, files in plugin_files.items():
        if debug:
            print(f"\nProcessing {p_type} plugins...")

        for plugin_file in files:
            file_name = f"{plugin_file.stem}_{PLUGIN_TYPES[p_type]}.mdx"
            output_file = NORNIR_DOCUMENTATION_DIRECTORY / "references" / "plugins" / file_name

            try:
                plugin_doc: dict = {}
                docstrings = extract_docstrings(plugin_file)
                plugin_doc["module"] = docstrings.pop("module", None)
                plugin_doc["functions"] = docstrings
                rendered_file = plugin_template.render(**plugin_doc)

                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_file.write_text(rendered_file, encoding="utf-8")
                print(f"✓ {output_file.name}")
                plugin_doc["file_name"] = file_name

                processed_plugins[p_type].append(plugin_doc)

            except Exception:  # pylint: disable=W0718
                print(f"✗ Error processing {plugin_file.name}")
                if debug:
                    import traceback  # pylint: disable=C0415

                    print(traceback.format_exc())

    # Generate landing page
    readme_file = NORNIR_DOCUMENTATION_DIRECTORY / "readme.mdx"
    readme_content = readme_template.render(
        plugins=processed_plugins,
    )
    readme_file.write_text(readme_content)
    print(f"✓ {readme_file.name}")
