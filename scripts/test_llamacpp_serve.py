import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock


SOURCE = Path(__file__).resolve().parents[1] / "capabilities/llamacpp/serve.py"
spec = importlib.util.spec_from_file_location("llamacpp_serve", SOURCE)
serve = importlib.util.module_from_spec(spec)
# These tests exercise launcher path preparation, not the network client.
# No model or Hugging Face setup is imported or executed.
dependency = types.ModuleType("huggingface_hub")
dependency.HfApi = mock.Mock(side_effect=AssertionError("unexpected network client"))
dependency.snapshot_download = mock.Mock(side_effect=AssertionError("unexpected download"))
with mock.patch.dict(sys.modules, {"huggingface_hub": dependency}):
    spec.loader.exec_module(serve)


class CacheHomeTests(unittest.TestCase):
    def test_main_passes_same_extended_cache_to_download_and_server(self):
        cache = "C:\\" + "x" * 120 + "\\models"
        observed = []
        with (
            mock.patch.dict(os.environ, {"HF_HOME": cache}),
            mock.patch.object(serve.sys, "platform", "win32"),
            mock.patch.object(serve.sys, "argv", [str(SOURCE)]),
            mock.patch.object(serve, "ensure_model_cached", side_effect=lambda *_: observed.append(os.environ["HF_HOME"])),
            mock.patch.object(serve, "start_server", side_effect=lambda *_: observed.append(os.environ["HF_HOME"])),
        ):
            self.assertEqual(serve.main(), 0)
        self.assertEqual(observed, ["\\\\?\\" + cache] * 2)

    def test_windows_server_consumes_prepared_cache_offline(self):
        observed = []
        api = mock.Mock()
        api.list_repo_files.return_value = ["Q4_K_M/model-Q4_K_M-00001-of-00002.gguf", "Q4_K_M/model-Q4_K_M-00002-of-00002.gguf"]
        with (
            mock.patch.dict(os.environ, {"HF_HOME": r"C:\work\models"}, clear=True),
            mock.patch.object(serve.sys, "platform", "win32"),
            mock.patch.object(serve.sys, "argv", [str(SOURCE)]),
            mock.patch.object(serve, "HfApi", return_value=api),
            mock.patch.object(serve.shutil, "which", return_value=None),
            mock.patch.object(serve, "snapshot_download", side_effect=lambda **kw: observed.append(kw)),
            mock.patch.object(serve.os.path, "exists", return_value=True),
            mock.patch.object(serve.os, "execvpe") as execute,
        ):
            self.assertEqual(serve.main(), 0)
        args = execute.call_args.args[1]
        server_env = execute.call_args.args[2]
        self.assertIn("--offline", args)
        self.assertEqual(args[1:3], ["-hf", serve.DEFAULT_MODEL])
        self.assertEqual(server_env["LLAMA_CACHE"], r"\\?\C:\work\models\hub")
        self.assertEqual(observed[0]["cache_dir"], server_env["LLAMA_CACHE"])
        self.assertEqual(observed[0]["allow_patterns"], api.list_repo_files.return_value)

    def test_windows_explicit_cache_precedence_is_shared_by_both_clients(self):
        for values, expected in (
            ({"LLAMA_CACHE": r"D:\llama", "HF_HUB_CACHE": r"E:\hf"}, r"\\?\D:\llama"),
            ({"HF_HUB_CACHE": r"E:\hf"}, r"\\?\E:\hf"),
            ({"HUGGINGFACE_HUB_CACHE": r"F:\legacy"}, r"\\?\F:\legacy"),
        ):
            with self.subTest(values=values), mock.patch.dict(os.environ, {"HF_HOME": r"C:\models", **values}, clear=True), mock.patch.object(serve.sys, "platform", "win32"):
                serve.prepare_cache_home()
                for variable in ("LLAMA_CACHE", "HF_HUB_CACHE", "HUGGINGFACE_HUB_CACHE"):
                    self.assertEqual(os.environ[variable], expected)

    def test_windows_unc_and_extended_cache_paths(self):
        for value, expected in (
            (r"\\server\share\models", r"\\?\UNC\server\share\models"),
            (r"\\?\C:\cache\models", r"\\?\C:\cache\models"),
            (r"\\?\UNC\server\share\models", r"\\?\UNC\server\share\models"),
            (r"C:/cache/nested/../models", r"\\?\C:\cache\models"),
        ):
            with self.subTest(value=value), mock.patch.dict(os.environ, {"HF_HOME": value}), mock.patch.object(serve.sys, "platform", "win32"):
                serve.prepare_cache_home()
                self.assertEqual(os.environ["HF_HOME"], expected)

    def test_windows_default_and_relative_paths_retain_cache_location(self):
        for value in (None, "models", r"nested\..\models"):
            environment = {} if value is None else {"HF_HOME": value}
            with self.subTest(value=value), mock.patch.dict(os.environ, environment, clear=True), mock.patch.object(serve.sys, "platform", "win32"), mock.patch.object(serve.os, "getcwd", return_value=r"C:\work"):
                serve.prepare_cache_home()
                self.assertEqual(os.environ["HF_HOME"], r"\\?\C:\work\models")

    def test_other_platforms_preserve_default_and_explicit_cache(self):
        for value in (None, "models", "/tmp/model cache", ""):
            environment = {} if value is None else {"HF_HOME": value}
            with self.subTest(value=value), mock.patch.dict(os.environ, environment, clear=True), mock.patch.object(serve.sys, "platform", "linux"):
                serve.prepare_cache_home()
                self.assertEqual(os.environ["HF_HOME"], "models" if value is None else value)
                self.assertNotIn("HF_HUB_CACHE", os.environ)
                self.assertNotIn("--offline", serve.server_args(serve.DEFAULT_MODEL, "cpu"))

    def test_windows_device_cache_is_rejected_and_display_paths_are_usable(self):
        with self.assertRaisesRegex(ValueError, "device paths"):
            serve.windows_cache_path(r"\\.\C:\models")
        self.assertEqual(serve.display_path(r"\\?\C:\cache\hub"), r"C:\cache\hub")
        self.assertEqual(serve.display_path(r"\\?\UNC\host\share\hub"), r"\\host\share\hub")

    @unittest.skipUnless(os.name == "nt", "real Windows filesystem control")
    def test_windows_long_cache_can_open_incomplete_blob(self):
        with tempfile.TemporaryDirectory() as directory:
            leaf = "a" * 64 + ".incomplete"
            padding = 266 - len(directory) - len(leaf) - 2
            self.assertGreater(padding, 0)
            cache = Path(directory) / ("p" * padding)
            cache.mkdir()
            with mock.patch.dict(os.environ, {"HF_HOME": str(cache)}, clear=True):
                serve.prepare_cache_home()
                self.assertTrue(os.environ["HF_HOME"].startswith("\\\\?\\"))
                target = Path(os.environ["HF_HOME"]) / leaf
                with target.open("ab") as output:
                    output.write(b"cache-path-control")
                self.assertEqual(target.read_bytes(), b"cache-path-control")


if __name__ == "__main__":
    unittest.main()
