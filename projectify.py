from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from string import Template
from textwrap import dedent


class ConfigError(RuntimeError):
    """Raised when the project configuration is invalid."""


def normalize_package_name(project_name: str) -> str:
    return project_name.replace("-", "_").replace(" ", "_")


def read_config(config_path: Path) -> dict[str, object]:
    text = config_path.read_text(encoding="utf-8")
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - runtime dependency check
        raise ConfigError(
            "PyYAML is required to parse configuration files. Install it with 'pip install PyYAML'."
        ) from exc

    data = yaml.safe_load(text)
    if data is None:
        raise ConfigError("Configuration file is empty.")
    if not isinstance(data, dict):
        raise ConfigError("Configuration must define a mapping at the top level.")
    return data


@dataclass
class ProjectConfig:
    project_name: str
    description: str
    project_url: str
    authors: list[dict[str, str]]
    dependencies: list[str]
    dependency_groups: dict[str, list[str]]
    dev_extras: list[str]


DEFAULT_DEPENDENCY_GROUPS: dict[str, list[str]] = {
    "test": ["pytest >=7", "pytest-cov >=3", "coverage[toml]"],
    "docs": [
        "sphinx>=7",
        "furo",
        "myst-parser<5",
        "sphinx-design",
        "sphinx-togglebutton",
        "sphinx-copybutton",
        "sphinx-autodoc-typehints",
        "myst-nb",
        "sphinxcontrib-mermaid",
    ],
    "examples": [
        "rich",
        "matplotlib>=3.10.7",
    ],
}

DEV_BASELINE = ["ipython", "ruff", "pre_commit", "mypy"]


def coerce_config(raw: dict[str, object]) -> ProjectConfig:
    try:
        project_name = str(raw["project_name"])
    except KeyError as exc:
        raise ConfigError("Missing 'project_name' in configuration") from exc

    try:
        description = str(raw["description"])
    except KeyError as exc:
        raise ConfigError("Missing 'description' in configuration") from exc
    try:
        project_url = str(raw["project_url"])
    except KeyError as exc:
        raise ConfigError("Missing 'project_url' in configuration") from exc
    try:
        authors_raw = raw["authors"]
    except KeyError as exc:
        raise ConfigError("Missing 'authors' in configuration") from exc
    if not isinstance(authors_raw, list):
        raise ConfigError("'authors' must be a list")
    if not authors_raw:
        raise ConfigError("'authors' must contain at least one entry")
    authors: list[dict[str, str]] = []
    for entry in authors_raw:
        if not isinstance(entry, dict):
            raise ConfigError("Each author entry must be a mapping with name/email")
        try:
            name = str(entry["name"])
            email = str(entry["email"])
        except KeyError as exc:
            raise ConfigError("Author entries require 'name' and 'email'") from exc
        authors.append({"name": name, "email": email})

    try:
        dependencies_raw = raw["dependencies"]
    except KeyError as exc:
        raise ConfigError("Missing 'dependencies' in configuration") from exc
    if not isinstance(dependencies_raw, list):
        raise ConfigError("'dependencies' must be a list")
    dependencies = [str(dep) for dep in dependencies_raw]

    try:
        groups_raw = raw["dependency_groups"]
    except KeyError as exc:
        raise ConfigError("Missing 'dependency_groups' in configuration") from exc
    if not isinstance(groups_raw, dict):
        raise ConfigError("'dependency_groups' must be a mapping")
    dependency_groups = {key: [str(dep) for dep in value] for key, value in DEFAULT_DEPENDENCY_GROUPS.items()}
    for group_name, deps in groups_raw.items():
        if not isinstance(deps, list):
            raise ConfigError(f"Dependency group '{group_name}' must be a list")
        dependency_groups[group_name] = [str(dep) for dep in deps]

    try:
        dev_extras_raw = raw["dev_extras"]
    except KeyError as exc:
        raise ConfigError("Missing 'dev_extras' in configuration") from exc
    if not isinstance(dev_extras_raw, list):
        raise ConfigError("'dev_extras' must be a list")
    dev_extras = [str(dep) for dep in dev_extras_raw]

    return ProjectConfig(
        project_name=project_name,
        description=description,
        project_url=project_url.rstrip("/"),
        authors=authors,
        dependencies=dependencies,
        dependency_groups=dependency_groups,
        dev_extras=dev_extras,
    )


PRE_COMMIT_CONFIG = dedent(
    """\
    ci:
      autoupdate_commit_msg: "chore: update pre-commit hooks"
      autofix_commit_msg: "style: pre-commit fixes"

    repos:
      - repo: https://github.com/pre-commit/pre-commit-hooks
        rev: "v6.0.0"
        hooks:
          - id: check-added-large-files
          - id: check-case-conflict
          - id: check-merge-conflict
          - id: check-symlinks
          - id: check-yaml
          - id: debug-statements
          - id: end-of-file-fixer
          - id: mixed-line-ending
          - id: name-tests-test
            args: ["--pytest-test-first"]
          - id: trailing-whitespace

      - repo: https://github.com/astral-sh/ruff-pre-commit
        rev: "v0.12.9"
        hooks:
          - id: ruff
            args: ["--fix", "--show-fixes"]
          - id: ruff-format

      - repo: https://github.com/pre-commit/mirrors-mypy
        rev: "v1.17.1"
        hooks:
          - id: mypy
            files: src|tests
            args: [--config-file=pyproject.toml]
            additional_dependencies:
              - pytest

      - repo: https://github.com/shellcheck-py/shellcheck-py
        rev: "v0.11.0.1"
        hooks:
          - id: shellcheck

      - repo: https://github.com/adamchainz/blacken-docs
        rev: "1.19.1"
        hooks:
          - id: blacken-docs
            additional_dependencies:
              - black==24.10.0

      - repo: https://github.com/codespell-project/codespell
        rev: v2.4.1
        hooks:
          - id: codespell
            exclude: ^(LICENSE$)

      - repo: https://github.com/henryiii/validate-pyproject-schema-store
        rev: 2025.08.15
        hooks:
          - id: validate-pyproject

      - repo: https://github.com/python-jsonschema/check-jsonschema
        rev: 0.33.3
        hooks:
          - id: check-readthedocs
          - id: check-github-workflows

      - repo: local
        hooks:
          - id: coverage
            name: coverage
            entry: bash -c 'if command -v uv >/dev/null 2>&1; then uv run coverage erase && uv run coverage run -m pytest && uv run coverage report --fail-under=85; else coverage erase && coverage run -m pytest && coverage report --fail-under=85; fi'
            language: system
            types: [python]
            pass_filenames: false
    """
)


READTHEDOCS_CONFIG = dedent(
    """\
    # https://docs.readthedocs.com/platform/stable/build-customization.html#install-dependencies-with-uv

    version: 2

    sphinx:
       configuration: docs/conf.py

    build:
       os: ubuntu-24.04
       tools:
          python: "3.13"
       jobs:
          pre_create_environment:
             - asdf plugin add uv
             - asdf install uv latest
             - asdf global uv latest
          create_environment:
             - uv venv "${READTHEDOCS_VIRTUALENV_PATH}"
          install:
             - UV_PROJECT_ENVIRONMENT="${READTHEDOCS_VIRTUALENV_PATH}" uv sync --group docs
    """
)


LICENSE_TEXT = dedent(
    """\
    MIT License

    Copyright (c) 2024 {copyright_holder}

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
    """
)


README_STUB = "# {project_name}\n\nThis is a STUB.\n"


DOC_STUB = "This is a STUB.\n"


DOC_INDEX_TEMPLATE = """# {project_name} documentation

This is a STUB.

```{{toctree}}
:maxdepth: 1
:caption: User Guide

introduction
quickstart
concepts
tutorials
```

```{{toctree}}
:maxdepth: 1
:caption: Developer Guide

architecture
contributing
```

```{{toctree}}
:maxdepth: 1
:caption: Reference

api/index
```
"""


DOC_API_INDEX = dedent(
    """\
    # API Reference

    The API reference is generated automatically from the source code. Modules are
    listed roughly in the order you will encounter them.

    ```{eval-rst}
    .. toctree::
       :maxdepth: 2
    ```

    This is a STUB.
    """
)


DOC_CONF_TEMPLATE = Template(
    """\
    \"\"\"Sphinx configuration for the $project_name documentation.\"\"\"

    from __future__ import annotations

    import datetime as _dt
    import sys
    from pathlib import Path

    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

    project = "$project_name"
    author = "$author_label"
    copyright = f"{{_dt.datetime.now().year}}, $author_label"

    extensions = [
        "myst_nb",
        "sphinx_design",
        "sphinx.ext.autodoc",
        "sphinx.ext.autosummary",
        "sphinx.ext.napoleon",
        "sphinx.ext.intersphinx",
        "sphinx.ext.viewcode",
        "sphinxcontrib.mermaid",
    ]

    autosummary_generate = True
    autosummary_imported_members = False
    autodoc_typehints = "description"
    napoleon_google_docstring = True
    napoleon_numpy_docstring = True

    autodoc_default_options = {
        "members": True,
        "undoc-members": False,
        "show-inheritance": False,
    }
    autodoc_member_order = "bysource"

    myst_enable_extensions = [
        "colon_fence",
        "deflist",
        "html_image",
    ]

    myst_fence_as_directive = ["mermaid"]

    nb_execution_mode = "off"

    html_theme = "furo"
    html_static_path = ["_static"]
    html_css_files = ["custom.css"]
    html_logo = None
    html_theme_options = {{
        "footer_icons": [
            {{
                "name": "GitHub",
                "url": "$repository_url",
                "html": \"\"\"
                    <svg stroke="currentColor" fill="currentColor" stroke-width="0" viewBox="0 0 16 16">
                        <path fill-rule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z"></path>
                    </svg>
                \"\"\",
                "class": "",
            }},
        ],
        "source_repository": "$repository_url",
        "source_branch": "main",
        "source_directory": "docs/",
    }}

    intersphinx_mapping = {{
        "python": ("https://docs.python.org/3", None),
        "numpy": ("https://numpy.org/doc/stable/", None),
        "jax": ("https://jax.readthedocs.io/en/latest/", None),
    }}

    templates_path = ["_templates"]
    exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "python/"]

    html_title = " "
    html_baseurl = "https://$project_name.readthedocs.io/"
    """
)


DOCS_CUSTOM_CSS = dedent(
    """\
    /* Force left alignment for autosummary tables in API reference */
    table.autosummary {
        margin-left: 0 !important;
        margin-right: auto !important;
    }

    /* Force left alignment for all docutils tables */
    table.docutils {
        margin-left: 0 !important;
        margin-right: auto !important;
    }

    /* Force left alignment for longtable */
    table.longtable {
        margin-left: 0 !important;
        margin-right: auto !important;
    }

    /* Ensure function/class signature blocks are left-aligned */
    dl.py,
    dl.function,
    dl.class,
    dl.method,
    dl.attribute {
        text-align: left !important;
    }

    /* Force left alignment for definition lists */
    dl {
        margin-left: 0 !important;
    }
    """
)


DOCS_MAKEFILE = dedent(
    """\
    # Makefile for Sphinx documentation
    # taken from: https://github.com/cms-cat/order/blob/master/docs/Makefile

    # You can set these variables from the command line.
    SPHINXOPTS  =
    SPHINXBUILD = sphinx-build
    PAPER       =
    BUILDDIR    = _build

    # User-friendly check for sphinx-build
    ifeq ($(shell which $(SPHINXBUILD) >/dev/null 2>&1; echo $$?), 1)
    $(error The '$(SPHINXBUILD)' command was not found. Make sure you have Sphinx installed, then set the SPHINXBUILD environment variable to point to the full path of the '$(SPHINXBUILD)' executable. Alternatively you can add the directory with the executable to your PATH. If you don't have Sphinx installed, grab it from http://sphinx-doc.org/)
    endif

    # Internal variables.
    PAPEROPT_a4     = -D latex_paper_size=a4
    PAPEROPT_letter = -D latex_paper_size=letter
    ALLSPHINXOPTS   = -d $(BUILDDIR)/doctrees $(PAPEROPT_$(PAPER)) $(SPHINXOPTS) .
    # the i18n builder cannot share the environment and doctrees with the others
    I18NSPHINXOPTS  = $(PAPEROPT_$(PAPER)) $(SPHINXOPTS) .

    .PHONY: help clean html

    help:
    	@echo "Please use `make <target>' where <target> is one of"
    	@echo "  clean      to cleanup all build files"
    	@echo "  html       to make standalone HTML files"

    clean:
    	rm -rf $(BUILDDIR)/*

    html:
    	$(SPHINXBUILD) -b html $(ALLSPHINXOPTS) $(BUILDDIR)/html
    	@echo
    	@echo "Build finished. The HTML pages are in $(BUILDDIR)/html."
    """
)


INIT_TEMPLATE = dedent(
    """\
    \"\"\"
    {project_name}: {description}
    \"\"\"

    from __future__ import annotations

    import datetime

    __name__ = "{package_name}"
    __author__ = "{author_label}"
    __copyright__ = f"Copyright {{datetime.datetime.now().year}}, {author_label}"
    __version__ = "0.0.1"

    __all__ = [
        "__version__",
    ]
    """
)


CI_WORKFLOW = dedent(
    """\
    name: CI

    concurrency:
      group: ${{ github.workflow }}-${{ github.ref }}
      cancel-in-progress: true

    on:
      workflow_dispatch:
      pull_request:
      push:
        branches:
          - main

    jobs:
      pre-commit:
        name: Format + lint code
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v5
            with:
              fetch-depth: 0
          - uses: actions/setup-python@v6
            with:
              python-version: "3.13"
          - name: Install uv
            uses: astral-sh/setup-uv@v7
          - name: Sync project dependencies
            run: uv sync --group=dev
          - uses: pre-commit/action@v3.0.1
            with:
              extra_args: --all-files

      checks:
        name: Run tests for Python ${{ matrix.python-version }} on ${{ matrix.runs-on }}
        runs-on: ${{ matrix.runs-on }}
        needs: [pre-commit]
        strategy:
          fail-fast: false
          matrix:
            python-version: ["3.11", "3.12", "3.13"]
            runs-on: [ubuntu-latest]

        steps:
          - uses: actions/checkout@v5
            with:
              fetch-depth: 0

          - uses: actions/setup-python@v6
            with:
              python-version: ${{ matrix.python-version }}
              allow-prereleases: true

          - name: Install uv
            uses: astral-sh/setup-uv@v7

          - name: Sync project + test deps
            run: uv sync --group=test

          - name: Test package
            run: >-
              uv run pytest -ra --cov --cov-report=xml --cov-report=term
              --durations=20

      docs:
        name: Build documentation
        runs-on: ubuntu-latest
        needs: [pre-commit]
        steps:
          - uses: actions/checkout@v5
            with:
              fetch-depth: 0

          - uses: actions/setup-python@v6
            with:
              python-version: "3.13"

          - name: Install uv
            uses: astral-sh/setup-uv@v7

          - name: Sync project + docs deps
            run: uv sync --group=docs

          - name: Build docs
            run: uv run sphinx-build -M html docs docs/_build -W --keep-going
    """
)


GITIGNORE_CONTENT = Path(".gitignore").read_text(encoding="utf-8") if Path(".gitignore").exists() else dedent(
    """\
    __pycache__/
    *.pyc
    """
)


def format_authors(authors: list[dict[str, str]]) -> str:
    if not authors:
        return "    { name = \"Mo\", email = \"todo@example.com\" },"
    lines = []
    for author in authors:
        lines.append(f'    {{ name = "{author["name"]}", email = "{author["email"]}" }},')
    return "\n".join(lines)


def format_string_array(values: list[str], indent: int = 4) -> str:
    if not values:
        return f'{" " * indent}# Add entries here'
    return "\n".join(f'{" " * indent}"{value}",' for value in values)


def format_dependency_groups(groups: dict[str, list[str]], extra_dev: list[str]) -> str:
    output_lines: list[str] = []
    for group_name, deps in groups.items():
        if group_name == "dev":
            continue
        output_lines.append(f"{group_name} = [")
        output_lines.append(format_string_array(deps))
        output_lines.append("]\n")

    include_groups = [name for name in groups.keys() if name != "dev"]
    output_lines.append("dev = [")
    for group in include_groups:
        output_lines.append(f'    {{ include-group = "{group}" }},')
    for dep in DEV_BASELINE + extra_dev:
        output_lines.append(f'    "{dep}",')
    output_lines.append("]")

    return "\n".join(output_lines)


def escape_toml_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def build_author_label(authors: list[dict[str, str]], project_name: str) -> str:
    if not authors:
        return f"{project_name} developers"
    return ", ".join(author["name"] for author in authors)


def build_pyproject(config: ProjectConfig) -> str:
    package_name = normalize_package_name(config.project_name)
    authors_block = format_authors(config.authors)
    dependencies_block = format_string_array(config.dependencies)
    dependency_groups_block = format_dependency_groups(config.dependency_groups, config.dev_extras)
    description = escape_toml_string(config.description)
    homepage = escape_toml_string(config.project_url)
    issues_url = escape_toml_string(f"{config.project_url}/issues")
    discussions_url = escape_toml_string(f"{config.project_url}/discussions")
    releases_url = escape_toml_string(f"{config.project_url}/releases")
    return dedent(
        f"""\
        [build-system]
        requires = ["hatchling"]
        build-backend = "hatchling.build"


        [project]
        name = "{config.project_name}"
        description = "{description}"
        license = "MIT"
        license-files = ["LICENSE"]
        readme = "README.md"
        requires-python = ">=3.11"
        classifiers = [
            "Development Status :: 1 - Planning",
            "Intended Audience :: Science/Research",
            "Intended Audience :: Developers",
            "Operating System :: OS Independent",
            "Programming Language :: Python",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3 :: Only",
            "Programming Language :: Python :: 3.11",
            "Programming Language :: Python :: 3.12",
            "Programming Language :: Python :: 3.13",
            "Topic :: Scientific/Engineering",
            "Typing :: Typed",
        ]
        dynamic = ["version"]
        authors = [
        {authors_block}
        ]
        dependencies = [
        {dependencies_block}
        ]


        [dependency-groups]
        {dependency_groups_block}


        [project.urls]
        Homepage = "{homepage}"
        "Bug Tracker" = "{issues_url}"
        Discussions = "{discussions_url}"
        Changelog = "{releases_url}"


        [tool.hatch]
        version.path = "src/{package_name}/__init__.py"


        [tool.pytest.ini_options]
        minversion = "7"
        xfail_strict = true
        addopts = ["-ra", "--strict-config", "--strict-markers"]
        pythonpath = ["src"]
        filterwarnings = [
            "error",
        ]
        log_cli_level = "INFO"
        testpaths = ["tests"]


        [tool.coverage]
        run.source = ["{package_name}"]
        port.exclude_lines = ['pragma: no cover', '\\.\\.\\.', 'if typing.TYPE_CHECKING:']


        [tool.mypy]
        files = ["src", "tests"]
        python_version = "3.13"
        warn_unreachable = true
        disallow_untyped_defs = false
        disallow_incomplete_defs = false
        check_untyped_defs = true
        enable_error_code = ["ignore-without-code", "redundant-expr", "truthy-bool"]
        strict = false
        ignore_missing_imports = true


        [tool.ruff.lint]
        preview = true
        ignore = [
            "PLR",
            "E501",
            "I002",
            "ISC001",
            "PLC0415",
            "PLW3201",
            "RUF052",
            "F722",
        ]
        select = [
            "E",
            "F",
            "W",
            "B",
            "I",
            "C4",
            "EM",
            "ICN",
            "ISC",
            "G",
            "PGH",
            "PIE",
            "PL",
            "PT",
            "PTH",
            "RET",
            "RUF",
            "SIM",
            "UP",
            "YTT",
            "EXE",
            "E303",
        ]
        unfixable = [
            "F841",
        ]
        flake8-unused-arguments.ignore-variadic-names = true
        isort.required-imports = ["from __future__ import annotations"]
        """
    )


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_file(path: Path, content: str) -> None:
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def generate_from_config(config_path: Path | str, destination: Path | str = ".") -> Path:
    config = coerce_config(read_config(Path(config_path)))
    destination_path = Path(destination).resolve()
    if not destination_path.exists():
        raise FileNotFoundError(f"Destination {destination_path} does not exist")

    project_root = destination_path / config.project_name
    if project_root.exists():
        raise FileExistsError(f"{project_root} already exists")

    package_name = normalize_package_name(config.project_name)
    author_label_value = build_author_label(config.authors, config.project_name)

    directories = [
        project_root / "src" / package_name,
        project_root / "tests",
        project_root / "docs" / "_static",
        project_root / "docs" / "_templates",
        project_root / "docs" / "api",
        project_root / ".github" / "workflows",
        project_root / "examples",
    ]
    for directory in directories:
        ensure_directory(directory)

    write_file(project_root / "pyproject.toml", build_pyproject(config))
    write_file(project_root / ".pre-commit-config.yaml", PRE_COMMIT_CONFIG)
    write_file(project_root / ".readthedocs.yaml", READTHEDOCS_CONFIG)
    write_file(
        project_root / "LICENSE",
        LICENSE_TEXT.format(copyright_holder=author_label_value),
    )
    write_file(project_root / "README.md", README_STUB.format(project_name=config.project_name))
    write_file(project_root / ".gitignore", GITIGNORE_CONTENT)
    write_file(project_root / ".github" / "workflows" / "ci.yml", CI_WORKFLOW)

    write_file(project_root / "docs" / "index.md", DOC_INDEX_TEMPLATE.format(project_name=config.project_name))
    write_file(
        project_root / "docs" / "conf.py",
        DOC_CONF_TEMPLATE.substitute(
            project_name=config.project_name,
            author_label=author_label_value,
            repository_url=config.project_url,
        ),
    )
    write_file(project_root / "docs" / "introduction.md", "# Introduction\n\n" + DOC_STUB)
    write_file(project_root / "docs" / "quickstart.md", "# Quickstart\n\n" + DOC_STUB)
    write_file(project_root / "docs" / "concepts.md", "# Core Concepts\n\n" + DOC_STUB)
    write_file(project_root / "docs" / "tutorials.md", "# Tutorials\n\n" + DOC_STUB)
    write_file(project_root / "docs" / "architecture.md", "# Architecture\n\n" + DOC_STUB)
    write_file(project_root / "docs" / "contributing.md", "# Contributing Guide\n\n" + DOC_STUB)
    write_file(project_root / "docs" / "api" / "index.md", DOC_API_INDEX)
    write_file(project_root / "docs" / "api" / "inference.md", "# Inference API\n\n" + DOC_STUB)
    write_file(project_root / "docs" / "api" / "parameters.md", "# Parameters API\n\n" + DOC_STUB)
    write_file(project_root / "docs" / "api" / "statelib.md", "# Statelib API\n\n" + DOC_STUB)
    write_file(project_root / "docs" / "_static" / "custom.css", DOCS_CUSTOM_CSS)
    write_file(project_root / "docs" / "_templates" / ".gitkeep", "")
    write_file(project_root / "docs" / "Makefile", DOCS_MAKEFILE)

    write_file(
        project_root / "src" / package_name / "__init__.py",
        INIT_TEMPLATE.format(
            project_name=config.project_name,
            description=config.description,
            package_name=package_name,
            author_label=author_label_value,
        ),
    )

    placeholder_test = dedent(
        """\
        from __future__ import annotations


        def test_placeholder() -> None:
            assert True
        """
    )
    write_file(project_root / "tests" / "test_placeholder.py", placeholder_test)
    write_file(project_root / "examples" / ".gitkeep", "")

    return project_root.resolve()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a project scaffold from a YAML config.")
    parser.add_argument("config", help="Path to the YAML configuration file.")
    parser.add_argument(
        "--destination",
        default=".",
        help="Directory where the project should be created (defaults to current directory).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_path = generate_from_config(args.config, args.destination)
    print(f"Created project at {project_path}")


if __name__ == "__main__":
    main()
