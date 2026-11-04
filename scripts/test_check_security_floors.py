import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import check_security_floors
from check_security_floors import (
    capability_violations,
    lock_violations,
    lock_warnings,
    manifest_violations,
    parse_package_url,
)

CONDA = "https://conda.anaconda.org/conda-forge"
PYPI = "https://files.pythonhosted.org/packages/00/00"
MANIFEST = '[workspace]\nname = "demo"\nrequires-pixi = ">=0.82.1"\n'
FIXED_CA = f"conda: {CONDA}/noarch/ca-certificates-2026.10.23-hbd8a1cb_0.conda"


def lock(*entries: str) -> str:
    """Build a lock in Pixi's layout: environments reference the URLs, and the
    top-level `packages:` list holds one entry per package. An entry may carry
    extra field lines after a newline, e.g. "pypi: <url>\\nname: x"."""
    environment, packages = [], []
    for entry in entries:
        head, *fields = entry.split("\n")
        environment.append(f"      - {head}\n")
        packages.append(f"- {head}\n" + "".join(f"  {field}\n" for field in fields))
    return (
        "version: 7\nenvironments:\n  default:\n    packages:\n"
        + "".join(environment)
        + "packages:\n"
        + "".join(packages)
    )


class ParsePackageUrlTests(unittest.TestCase):
    def test_conda_package_formats(self) -> None:
        self.assertEqual(
            parse_package_url(
                "conda", f"{CONDA}/noarch/ca-certificates-2026.10.23-hbd8a1cb_0.conda"
            ),
            ("ca-certificates", "2026.10.23"),
        )
        self.assertEqual(
            parse_package_url(
                "conda", f"{CONDA}/linux-64/git-2.53.0-pl5321h6d3_0.tar.bz2"
            ),
            ("git", "2.53.0"),
        )

    def test_pypi_wheel_and_sdist_names_are_normalized(self) -> None:
        self.assertEqual(
            parse_package_url("pypi", f"{PYPI}/hf_xet-1.8.0-cp37-abi3-win_amd64.whl"),
            ("hf-xet", "1.8.0"),
        )
        self.assertEqual(
            parse_package_url("pypi", f"{PYPI}/Some_Package-2.0.tar.gz"),
            ("some-package", "2.0"),
        )
        self.assertEqual(
            parse_package_url("pypi", "./wheels/certifi-2020.6.20-py3-none-any.whl"),
            ("certifi", "2020.6.20"),
        )

    def test_git_urls_have_no_filename_version(self) -> None:
        self.assertIsNone(
            parse_package_url("pypi", "git+https://github.com/org/repo.git?rev=abc#abc")
        )


class LockViolationTests(unittest.TestCase):
    def test_fixed_lock_passes(self) -> None:
        self.assertEqual(
            lock_violations(
                lock(
                    FIXED_CA,
                    f"conda: {CONDA}/win-64/python-3.12.16-hb12b558_0_cpython.conda",
                    f"pypi: {PYPI}/certifi-2026.10.23-py3-none-any.whl\n"
                    "name: certifi\nversion: 2026.10.23",
                    f"pypi: {PYPI}/uv-0.13.6-py3-none-win_amd64.whl",
                    f"conda: {CONDA}/linux-64/openssl-3.6.2-h35e630c_0.conda",
                )
            ),
            [],
        )

    def test_old_root_bundles_fail(self) -> None:
        self.assertEqual(
            lock_violations(
                lock(
                    f"conda: {CONDA}/noarch/ca-certificates-2026.6.17-hbd8a1cb_0.conda",
                    f"pypi: {PYPI}/certifi-2026.6.17-py3-none-any.whl",
                )
            ),
            [
                "ca-certificates 2026.6.17 < 2026.10.19",
                "certifi 2026.6.17 < 2026.10.19",
            ],
        )

    def test_python_floor_depends_on_minor(self) -> None:
        def python(version: str, name: str = "python") -> list[str]:
            return lock_violations(
                lock(f"conda: {CONDA}/linux-64/{name}-{version}-h0_cpython.conda")
            )

        self.assertEqual(python("3.12.16"), [])
        self.assertEqual(python("3.13.18"), [])
        self.assertEqual(python("3.12.15"), ["python 3.12.15 < 3.12.16"])
        self.assertEqual(python("3.14.4"), ["python 3.14.4 < 3.14.10"])
        self.assertEqual(python("3.12.13", "cpython"), ["cpython 3.12.13 < 3.12.16"])
        self.assertEqual(
            python("3.10.22"),
            [
                "python 3.10.22: no release of this minor version has the fix; "
                "use 3.11.18 or later"
            ],
        )
        self.assertEqual(python("3.16.0"), [])

    def test_pre_releases_rank_below_their_final_release(self) -> None:
        def hf_xet(version: str) -> list[str]:
            return lock_violations(
                lock(f"conda: {CONDA}/linux-64/hf-xet-{version}-py311h0_0.conda")
            )

        self.assertEqual(hf_xet("1.7.1rc0"), ["hf-xet 1.7.1rc0 < 1.7.1"])
        self.assertEqual(hf_xet("1.7.1.dev2"), ["hf-xet 1.7.1.dev2 < 1.7.1"])
        self.assertEqual(hf_xet("1.7.1.0"), [])
        self.assertEqual(hf_xet("1.8.0rc0"), [])

    def test_rust_tools_below_the_rustls_webpki_fix_fail(self) -> None:
        self.assertEqual(
            lock_violations(
                lock(
                    f"pypi: {PYPI}/uv-0.13.4-py3-none-win_amd64.whl",
                    f"conda: {CONDA}/linux-64/hf-xet-1.7.0-py311h30674b1_0.conda",
                    f"conda: {CONDA}/noarch/pip-26.2.1-pyh145f28c_0.conda",
                )
            ),
            ["hf-xet 1.7.0 < 1.7.1", "pip 26.2.1 < 26.2.2", "uv 0.13.4 < 0.13.5"],
        )


class LockParsingFailsClosedTests(unittest.TestCase):
    def test_git_and_path_sources_are_checked_by_their_recorded_version(self) -> None:
        self.assertEqual(
            lock_violations(
                lock(
                    "pypi: git+https://github.com/org/certifi.git#abc\n"
                    "name: certifi\nversion: 2020.6.20",
                    "pypi: ./wheels/pip-20.0-py3-none-any.whl",
                )
            ),
            ["certifi 2020.6.20 < 2026.10.19", "pip 20.0 < 26.2.2"],
        )

    def test_quoted_urls_and_fields_are_read(self) -> None:
        self.assertEqual(
            lock_violations(
                lock(
                    f"conda: '{CONDA}/noarch/ca-certificates-2020.1.1-h0_0.conda'",
                    f'pypi: "{PYPI}/x.whl"\nname: "certifi"\nversion: \'2020.6.20\'',
                )
            ),
            ["ca-certificates 2020.1.1 < 2026.10.19", "certifi 2020.6.20 < 2026.10.19"],
        )

    def test_unreadable_entries_fail(self) -> None:
        self.assertEqual(
            lock_violations(lock(f"pypi: {PYPI}/certifi-latest.egg")),
            [f"cannot read the package name and version of {PYPI}/certifi-latest.egg"],
        )
        self.assertEqual(
            lock_violations(lock("pypi: git+https://github.com/org/repo.git#abc")),
            [
                "cannot read the package name and version of "
                "git+https://github.com/org/repo.git#abc"
            ],
        )
        self.assertEqual(
            lock_violations(
                lock(f"pypi: {PYPI}/x.whl\nname: certifi\nversion: latest")
            ),
            ["cannot parse the version 'latest' of certifi"],
        )

    def test_lock_without_packages_fails(self) -> None:
        self.assertEqual(
            lock_violations("version: 7\nenvironments: {}\n"),
            ["no packages found in pixi.lock"],
        )


class KnownIssueWarningTests(unittest.TestCase):
    def test_polars_1x_warns_without_failing(self) -> None:
        text = lock(
            FIXED_CA,
            f"conda: {CONDA}/linux-64/polars-runtime-32-1.39.3-py310h0_1.conda",
            f"conda: {CONDA}/noarch/polars-2.1.0-pyh0_0.conda",
        )
        self.assertEqual(lock_violations(text), [])
        self.assertEqual(
            lock_warnings(text),
            [
                "polars-runtime-32 1.39.3 < 2.1.0: known issue, no fixed release "
                "this capability can use yet"
            ],
        )

    def test_only_windows_git_warns(self) -> None:
        text = lock(
            FIXED_CA,
            f"conda: {CONDA}/win-64/git-2.53.0-h57928b3_0.conda",
            f"conda: {CONDA}/linux-64/git-2.53.0-pl5321h6d3cee1_0.conda",
        )
        self.assertEqual(lock_violations(text), [])
        self.assertEqual(
            lock_warnings(text),
            [
                "git 2.53.0 (win-64): known issue, no conda-forge build of a "
                "fixed Git for Windows yet"
            ],
        )


class ManifestViolationTests(unittest.TestCase):
    def test_requires_pixi_floor(self) -> None:
        self.assertEqual(manifest_violations(MANIFEST), [])
        self.assertEqual(
            manifest_violations(MANIFEST.replace(">=0.82.1", ">=0.82.1,<1")), []
        )
        self.assertRegex(
            manifest_violations(MANIFEST.replace(">=0.82.1", ">=0.44"))[0],
            "older than 0.82.1",
        )
        self.assertRegex(
            manifest_violations(MANIFEST.replace(">=0.82.1", "==0.82.1"))[0],
            "no >= lower bound",
        )
        # Either alternative of an "|" spec is enough, so each needs the floor.
        self.assertRegex(
            manifest_violations(MANIFEST.replace(">=0.82.1", ">=0.82.1|>=0.40"))[0],
            "older than 0.82.1",
        )
        self.assertRegex(
            manifest_violations(MANIFEST.replace(">=0.82.1", ">=0.82.1|==0.40"))[0],
            "no >= lower bound",
        )
        self.assertEqual(
            manifest_violations(MANIFEST.replace(">=0.82.1", ">=0.82.1|>=0.83")), []
        )
        self.assertRegex(
            manifest_violations('[workspace]\nname = "demo"\n')[0], "missing"
        )

    def test_capability_without_a_lock_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            capability = Path(directory)
            (capability / "pixi.toml").write_text(MANIFEST, encoding="utf-8")
            self.assertEqual(
                capability_violations(capability), ["pixi.lock is missing"]
            )


class MainTests(unittest.TestCase):
    def run_main(self, capabilities: Path) -> tuple[int, str]:
        output = io.StringIO()
        argv = ["check_security_floors.py", str(capabilities)]
        with mock.patch("sys.argv", argv), redirect_stdout(output):
            code = check_security_floors.main()
        return code, output.getvalue()

    def write_capability(self, root: Path, lock_text: str) -> None:
        capability = root / "demo"
        capability.mkdir()
        (capability / "pixi.toml").write_text(MANIFEST, encoding="utf-8")
        (capability / "pixi.lock").write_text(lock_text, encoding="utf-8")

    def test_missing_or_empty_directory_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            code, output = self.run_main(Path(directory) / "no-such-dir")
        self.assertEqual(code, 1)
        self.assertIn("nothing checked", output)

    def test_exit_codes_follow_violations_not_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_capability(
                root,
                lock(FIXED_CA, f"conda: {CONDA}/win-64/git-2.53.0-h57928b3_0.conda"),
            )
            code, output = self.run_main(root)
        self.assertEqual(code, 0)
        self.assertIn("demo: OK (1 known-issue warning(s))", output)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_capability(
                root,
                lock(f"conda: {CONDA}/noarch/ca-certificates-2026.6.17-h0_0.conda"),
            )
            code, output = self.run_main(root)
        self.assertEqual(code, 1)
        self.assertIn("demo: FAILED", output)


if __name__ == "__main__":
    unittest.main()
