import tempfile
import unittest
from pathlib import Path

from check_security_floors import (
    capability_violations,
    lock_violations,
    manifest_violations,
    parse_package_url,
)

CONDA = "https://conda.anaconda.org/conda-forge"
PYPI = "https://files.pythonhosted.org/packages/00/00"
MANIFEST = '[workspace]\nname = "demo"\nrequires-pixi = ">=0.82.1"\n'


def lock(*urls: str) -> str:
    entries = "".join(f"      - {url}\n" for url in urls)
    return f"version: 7\nenvironments:\n  default:\n    packages:\n{entries}"


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

    def test_git_sources_are_ignored(self) -> None:
        self.assertIsNone(
            parse_package_url("pypi", "git+https://github.com/org/repo.git?rev=abc#abc")
        )


class LockViolationTests(unittest.TestCase):
    def test_fixed_lock_passes(self) -> None:
        self.assertEqual(
            lock_violations(
                lock(
                    f"conda: {CONDA}/noarch/ca-certificates-2026.10.23-hbd8a1cb_0.conda",
                    f"conda: {CONDA}/win-64/python-3.12.16-hb12b558_0_cpython.conda",
                    f"pypi: {PYPI}/certifi-2026.10.23-py3-none-any.whl",
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
        def python(version: str) -> list[str]:
            return lock_violations(
                lock(f"conda: {CONDA}/linux-64/python-{version}-h0_cpython.conda")
            )

        self.assertEqual(python("3.12.16"), [])
        self.assertEqual(python("3.13.18"), [])
        self.assertEqual(python("3.12.15"), ["python 3.12.15 < 3.12.16"])
        self.assertEqual(python("3.14.4"), ["python 3.14.4 < 3.14.10"])
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

    def test_unreadable_downloadable_entries_fail_closed(self) -> None:
        self.assertEqual(
            lock_violations(lock(f"pypi: {PYPI}/certifi-latest.egg")),
            [f"cannot read the package version of {PYPI}/certifi-latest.egg"],
        )
        self.assertEqual(
            lock_violations(lock("pypi: git+https://github.com/org/repo.git#abc")),
            [],
        )

    def test_rust_tools_below_the_rustls_webpki_fix_fail(self) -> None:
        self.assertEqual(
            lock_violations(
                lock(
                    f"pypi: {PYPI}/uv-0.13.4-py3-none-win_amd64.whl",
                    f"conda: {CONDA}/linux-64/hf-xet-1.7.0-py311h30674b1_0.conda",
                )
            ),
            ["hf-xet 1.7.0 < 1.7.1", "uv 0.13.4 < 0.13.5"],
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


if __name__ == "__main__":
    unittest.main()
