# Projectify

Reusable scaffold generator for Python projects that follow the mirrorball/everwillow conventions.

## Requirements

- Python 3.11+
- [PyYAML](https://pyyaml.org/) (`pip install PyYAML`)

## Getting started

Clone this repository and install dependencies:

```bash
uv sync --group dev
```

## Usage

1. Duplicate `example_config.yml` and edit the fields:
   - `project_name`, `description`, `project_url`
   - `authors`: list of `{ name, email }` entries
   - `dependencies`, `dependency_groups`, `dev_extras`
2. Run the generator from the repository root:

   ```bash
   python projectify.py path/to/config.yml --destination /path/to/output
   ```

   This creates `/path/to/output/<project_name>/` populated with:
   - Hatch-based `pyproject.toml`
   - MIT `LICENSE`
   - Stub README and documentation pages
   - Pre-commit hooks, CI workflow, tests layout, examples folder

3. Initialize git within the generated project, install dependencies, and follow the stub CONTRIBUTING guide.

## Development

Run tests before committing changes:

```bash
python3 -m unittest discover tests
```

Linting and formatting are handled via the repo’s pre-commit hooks.
