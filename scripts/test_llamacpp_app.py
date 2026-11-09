"""Checks which llama.cpp archive app.py picks for each platform and backend.

The recorded names are the pinned b9200 release's assets, in the order
GitHub's release API returns them. Nothing is downloaded.
"""
import importlib.util
from pathlib import Path
import unittest
from unittest import mock


SOURCE = Path(__file__).resolve().parents[1] / "capabilities/llamacpp/app.py"
spec = importlib.util.spec_from_file_location("llamacpp_app", SOURCE)
app = importlib.util.module_from_spec(spec)
# Loading only defines the helpers; the download itself runs from main().
spec.loader.exec_module(app)

RELEASE_TAG = "b9200"
# Order matters: selection takes the first name that matches.
ASSET_NAMES = (
    "cudart-llama-bin-win-cuda-12.4-x64.zip",
    "cudart-llama-bin-win-cuda-13.1-x64.zip",
    "llama-b9200-bin-310p-openEuler-aarch64.tar.gz",
    "llama-b9200-bin-310p-openEuler-x86.tar.gz",
    "llama-b9200-bin-910b-openEuler-aarch64-aclgraph.tar.gz",
    "llama-b9200-bin-910b-openEuler-x86-aclgraph.tar.gz",
    "llama-b9200-bin-android-arm64.tar.gz",
    "llama-b9200-bin-macos-arm64-kleidiai.tar.gz",
    "llama-b9200-bin-macos-arm64.tar.gz",
    "llama-b9200-bin-macos-x64.tar.gz",
    "llama-b9200-bin-ubuntu-arm64.tar.gz",
    "llama-b9200-bin-ubuntu-openvino-2026.0-x64.tar.gz",
    "llama-b9200-bin-ubuntu-rocm-7.2-x64.tar.gz",
    "llama-b9200-bin-ubuntu-s390x.tar.gz",
    "llama-b9200-bin-ubuntu-sycl-fp16-x64.tar.gz",
    "llama-b9200-bin-ubuntu-sycl-fp32-x64.tar.gz",
    "llama-b9200-bin-ubuntu-vulkan-arm64.tar.gz",
    "llama-b9200-bin-ubuntu-vulkan-x64.tar.gz",
    "llama-b9200-bin-ubuntu-x64.tar.gz",
    "llama-b9200-bin-win-cpu-arm64.zip",
    "llama-b9200-bin-win-cpu-x64.zip",
    "llama-b9200-bin-win-cuda-12.4-x64.zip",
    "llama-b9200-bin-win-cuda-13.1-x64.zip",
    "llama-b9200-bin-win-hip-radeon-x64.zip",
    "llama-b9200-bin-win-opencl-adreno-arm64.zip",
    "llama-b9200-bin-win-sycl-x64.zip",
    "llama-b9200-bin-win-vulkan-x64.zip",
    "llama-b9200-xcframework.zip",
)


def selected_name(platform, machine, backend, names=ASSET_NAMES, local_cuda=None):
    assets = [{"name": name} for name in names]
    with (
        mock.patch.object(app.sys, "platform", platform),
        mock.patch.object(app.platform, "machine", return_value=machine),
        mock.patch.object(app, "BACKEND", backend),
        mock.patch.object(app, "LLAMACPP_RELEASE_TAG", RELEASE_TAG),
    ):
        asset = app.detect_asset(assets, local_cuda)
    return asset["name"] if asset else None


class DetectAssetTests(unittest.TestCase):
    def test_recorded_names_belong_to_the_pinned_release(self):
        # The cases below patch the tag to RELEASE_TAG, so after a pin bump they
        # would keep passing against b9200's names. A change in asset order
        # between releases is what caused the Linux CPU bug, so fail here instead.
        self.assertEqual(
            app.LLAMACPP_RELEASE_TAG,
            RELEASE_TAG,
            "app.py's llama.cpp pin moved: re-record RELEASE_TAG and ASSET_NAMES "
            "from the new release, in the order GitHub's release API returns them.",
        )

    def test_each_platform_and_backend_gets_its_build(self):
        for platform, machine, backend, local_cuda, expected in (
            ("linux", "x86_64", "cpu", None, "llama-b9200-bin-ubuntu-x64.tar.gz"),
            ("linux", "x86_64", "gpu", None, "llama-b9200-bin-ubuntu-vulkan-x64.tar.gz"),
            ("darwin", "arm64", "cpu", None, "llama-b9200-bin-macos-arm64.tar.gz"),
            ("darwin", "arm64", "gpu", None, "llama-b9200-bin-macos-arm64.tar.gz"),
            ("darwin", "x86_64", "cpu", None, "llama-b9200-bin-macos-x64.tar.gz"),
            ("win32", "amd64", "cpu", None, "llama-b9200-bin-win-cpu-x64.zip"),
            ("win32", "amd64", "gpu", (12, 4), "llama-b9200-bin-win-cuda-12.4-x64.zip"),
            ("win32", "amd64", "gpu", (13, 1), "llama-b9200-bin-win-cuda-13.1-x64.zip"),
        ):
            with self.subTest(platform=platform, machine=machine, backend=backend, local_cuda=local_cuda):
                self.assertEqual(selected_name(platform, machine, backend, local_cuda=local_cuda), expected)

    def test_linux_cpu_finds_nothing_rather_than_another_build(self):
        # Without the plain archive, app.py must report no match and stop,
        # not fall back to a build that needs other hardware or libraries.
        names = [name for name in ASSET_NAMES if name != "llama-b9200-bin-ubuntu-x64.tar.gz"]
        self.assertIsNone(selected_name("linux", "x86_64", "cpu", names=names))


if __name__ == "__main__":
    unittest.main()
