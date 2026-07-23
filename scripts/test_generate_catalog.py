import tempfile
import unittest
from pathlib import Path

from generate_catalog import active_repositories, build_catalog


class GenerateCatalogTests(unittest.TestCase):
    def test_only_active_capabilities_are_discoverable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            capabilities = Path(directory)
            self.write_manifest(capabilities, "active-op")
            self.write_manifest(capabilities, "retired-op", status="retired")

            self.assertEqual(
                active_repositories(capabilities),
                [
                    {
                        "namespace": "openteams_capabilities",
                        "name": "active-op",
                    }
                ],
            )

    def test_catalog_has_a_versioned_shape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(
                build_catalog(Path(directory)),
                {"schemaVersion": 1, "repositories": []},
            )

    def test_repository_name_must_match_workspace_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            capabilities = Path(directory)
            self.write_manifest(
                capabilities, "repository-name", workspace_name="other-name"
            )

            with self.assertRaisesRegex(ValueError, "workspace.name"):
                active_repositories(capabilities)

    def test_definitions_in_one_repository_cannot_mix_statuses(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            capabilities = Path(directory)
            self.write_manifest(capabilities, "mixed-status")
            manifest = capabilities / "mixed-status" / "pixi.toml"
            manifest.write_text(
                manifest.read_text(encoding="utf-8")
                + "\n[tool.nebi.capability.openteams.retired]\n"
                + 'catalog = { status = "retired" }\n',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "same catalog status"):
                active_repositories(capabilities)

    @staticmethod
    def write_manifest(
        capabilities: Path,
        name: str,
        status: str | None = None,
        workspace_name: str | None = None,
    ) -> None:
        capability_dir = capabilities / name
        capability_dir.mkdir()
        catalog = f'catalog = {{ status = "{status}" }}\n' if status else ""
        (capability_dir / "pixi.toml").write_text(
            "[workspace]\n"
            f'name = "{workspace_name or name}"\n\n'
            "[tool.nebi.capability]\n"
            'spec-version = "0.1.0"\n\n'
            f"[tool.nebi.capability.openteams.{name}]\n"
            f"{catalog}",
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
