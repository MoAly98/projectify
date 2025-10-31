from __future__ import annotations

import runpy
import tempfile
import unittest
from pathlib import Path
from textwrap import dedent

try:
    import yaml  # noqa: F401  # ensure PyYAML is present
except ImportError:  # pragma: no cover
    yaml = None


PROJECTIFY_MODULE_PATH = Path("./projectify.py")


def load_projectify_module() -> dict[str, object]:
    return runpy.run_path(str(PROJECTIFY_MODULE_PATH))


@unittest.skipIf(yaml is None, "PyYAML is required for these tests")
class ProjectifyGeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tempdir.cleanup)
        print(f"Generating test project in {self._tempdir.name}")
        self.destination = Path(self._tempdir.name)
        module = load_projectify_module()
        self.generate = module["generate_from_config"]

    def write_config(self, content: str) -> Path:
        config_path = self.destination / "config.yml"
        config_path.write_text(dedent(content).strip() + "\n", encoding="utf-8")
        return config_path

    def test_generate_scaffold_from_yaml(self) -> None:
        config_path = self.write_config(
            """
            project_name: sample-project
            description: Sample description of the project.
            project_url: https://github.com/MoAly98/sample-project
            authors:
              - name: Mo
                email: mo@example.com
            dependencies:
              - numpy
              - scipy
            dependency_groups:
              test:
                - pytest
              docs:
                - sphinx
                - furo
              examples:
                - rich
            dev_extras:
              - pytest-xdist
            """
        )

        project_path = self.generate(
            config_path=config_path,
            destination=self.destination,
        )

        expected_root = self.destination / "sample-project"
        self.assertEqual(project_path, expected_root.resolve())

        expected_files = [
            "pyproject.toml",
            ".pre-commit-config.yaml",
            ".readthedocs.yaml",
            "LICENSE",
            "README.md",
            ".gitignore",
            ".github/workflows/ci.yml",
            "docs/index.md",
            "docs/introduction.md",
            "docs/quickstart.md",
            "docs/concepts.md",
            "docs/tutorials.md",
            "docs/architecture.md",
            "docs/contributing.md",
            "docs/api/index.md",
            "src/sample_project/__init__.py",
            "tests/test_placeholder.py",
        ]

        for rel_path in expected_files:
            self.assertTrue(
                (expected_root / rel_path).exists(), msg=f"Missing {rel_path}"
            )

        pyproject_contents = (expected_root / "pyproject.toml").read_text(
            encoding="utf-8"
        )
        self.assertIn('name = "sample-project"', pyproject_contents)
        self.assertIn('"numpy"', pyproject_contents)
        self.assertIn('"scipy"', pyproject_contents)
        self.assertIn("Sample description of the project.", pyproject_contents)
        self.assertIn('Homepage = "https://github.com/MoAly98/sample-project"', pyproject_contents)
        self.assertIn('license = "MIT"', pyproject_contents)
        self.assertIn('{ name = "Mo", email = "mo@example.com" }', pyproject_contents)
        self.assertIn('"pytest-xdist"', pyproject_contents)

        readme_contents = (expected_root / "README.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("This is a STUB.", readme_contents)

        docs_intro = (expected_root / "docs" / "introduction.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("This is a STUB.", docs_intro)

        conf_py = (expected_root / "docs" / "conf.py").read_text(encoding="utf-8")
        self.assertIn('source_repository": "https://github.com/MoAly98/sample-project"', conf_py)
        self.assertIn('author = "Mo"', conf_py)

        license_text = (expected_root / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("MIT License", license_text)
        self.assertIn("Mo", license_text)

        init_contents = (
            expected_root / "src" / "sample_project" / "__init__.py"
        ).read_text(encoding="utf-8")
        self.assertIn('__version__ = "0.0.1"', init_contents)


if __name__ == "__main__":
    unittest.main()
