import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
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
            mock.patch.object(serve, "start_server", side_effect=lambda *_: observed.append(os.environ["HF_HOME"]) or 0),
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
            mock.patch.object(serve.subprocess, "call", return_value=0) as run,
        ):
            self.assertEqual(serve.main(), 0)
        execute.assert_not_called()
        args = run.call_args.args[0]
        server_env = run.call_args.kwargs["env"]
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
                try:
                    with target.open("ab") as output:
                        output.write(b"cache-path-control")
                    self.assertEqual(target.read_bytes(), b"cache-path-control")
                finally:
                    # Cleanup must use the extended path too when the machine
                    # has its ordinary long-path policy disabled.
                    target.unlink(missing_ok=True)


class ServerStartTests(unittest.TestCase):
    def test_unix_keeps_exec_handoff(self):
        with (
            mock.patch.object(serve.sys, "platform", "linux"),
            mock.patch.object(serve.os.path, "exists", return_value=True),
            mock.patch.object(serve.os, "execvpe") as execute,
            mock.patch.object(serve.subprocess, "call") as run,
        ):
            serve.start_server("fixture/repo:Q4_K_M", "cpu")
        run.assert_not_called()
        self.assertEqual(execute.call_args.args[0], os.path.join("bin", "llama-server"))
        self.assertEqual(execute.call_args.args[1][:3], [os.path.join("bin", "llama-server"), "-hf", "fixture/repo:Q4_K_M"])

    def test_main_reports_windows_start_failure(self):
        with (
            mock.patch.object(serve.sys, "platform", "win32"),
            mock.patch.object(serve.sys, "argv", [str(SOURCE)]),
            mock.patch.object(serve, "prepare_cache_home"),
            mock.patch.object(serve, "ensure_model_cached"),
            mock.patch.object(serve.os.path, "exists", return_value=True),
            mock.patch.object(serve.subprocess, "call", side_effect=OSError("synthetic start failure")),
            mock.patch.object(serve, "status") as status,
        ):
            self.assertEqual(serve.main(), 1)
        self.assertIn("ERROR: synthetic start failure", [c.args[0] for c in status.call_args_list])


def wait_fixture(path):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            return json.loads(path.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            time.sleep(0.02)
    raise AssertionError(f"fixture did not become ready: {path.name}")


@unittest.skipUnless(os.name == "nt", "real Windows launcher/process-tree control")
class WindowsServerLifetimeTests(unittest.TestCase):
    def test_launcher_stays_owned_until_tree_stop_and_preserves_other_process(self):
        import ctypes
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handles = []
        launcher = peer = None
        with tempfile.TemporaryDirectory(prefix="llama-lifetime-") as directory:
            ready = Path(directory) / "server.json"
            peer_ready = Path(directory) / "peer.json"
            with (Path(directory) / "output.txt").open("w") as output:
                try:
                    peer = subprocess.Popen([sys.executable, __file__, "--lifetime-leaf", str(peer_ready)], stdout=output, stderr=output)
                    wait_fixture(peer_ready)
                    launcher = subprocess.Popen([sys.executable, __file__, "--lifetime-launcher", str(ready), "hold"], stdout=output, stderr=output)
                    identities = wait_fixture(ready)
                    for pid in (identities["server"], identities["child"]):
                        handle = kernel.OpenProcess(0x101001, False, pid)
                        self.assertTrue(handle, f"fixture PID {pid} must be alive before Stop")
                        handles.append(handle)
                        self.assertEqual(kernel.WaitForSingleObject(handle, 0), 258)
                    with self.assertRaises(subprocess.TimeoutExpired, msg="Windows launcher exited while its server was still alive"):
                        launcher.wait(timeout=0.5)
                    # The same OS tree-stop operation used by Collab, applied
                    # only to the fixture root. Held child handles prove exit.
                    subprocess.run(["taskkill", "/T", "/F", "/PID", str(launcher.pid)], check=True, stdout=output, stderr=output)
                    launcher.wait(timeout=10)
                    for handle in handles:
                        self.assertEqual(kernel.WaitForSingleObject(handle, 10000), 0, "owned descendant survived tree Stop")
                    self.assertIsNone(peer.poll(), "tree Stop affected an unrelated process")
                finally:
                    # Handles retain exact fixture identities even if the old
                    # launcher exited, so pre-fix failures cannot leak a child.
                    for handle in handles:
                        if kernel.WaitForSingleObject(handle, 0) == 258:
                            kernel.TerminateProcess(handle, 1)
                            kernel.WaitForSingleObject(handle, 10000)
                        kernel.CloseHandle(handle)
                    for process in (launcher, peer):
                        if process is not None:
                            if process.poll() is None:
                                process.kill()
                            process.wait(timeout=10)

    def test_main_returns_actual_server_exit_status(self):
        for code in (0, 23):
            with self.subTest(code=code), tempfile.TemporaryDirectory() as directory:
                result = subprocess.run([sys.executable, __file__, "--lifetime-launcher", str(Path(directory) / "unused.json"), str(code)], capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, code, result.stdout + result.stderr)


def lifetime_fixture():
    mode, ready = sys.argv[1], Path(sys.argv[2])
    if mode == "--lifetime-launcher":
        outcome = sys.argv[3]
        # Replace only executable discovery/arguments and network preparation.
        # The production main/start_server and real Windows handoff run intact.
        serve.ensure_model_cached = lambda *_: None
        serve.server_binary = lambda: sys.executable
        serve.server_args = lambda *_: [sys.executable, __file__, "--lifetime-server", str(ready), outcome]
        sys.argv = [str(SOURCE), "--backend", "cpu"]
        return serve.main()
    if mode == "--lifetime-server":
        if sys.argv[3] != "hold":
            return int(sys.argv[3])
        child_ready = ready.with_suffix(".child.json")
        child = subprocess.Popen([sys.executable, __file__, "--lifetime-leaf", str(child_ready)])
        try:
            wait_fixture(child_ready)
            ready.write_text(json.dumps({"server": os.getpid(), "child": child.pid}))
            print("synthetic server ready", flush=True)
            time.sleep(60)
        finally:
            child.terminate()
            child.wait(timeout=10)
        return 0
    if mode == "--lifetime-leaf":
        ready.write_text(json.dumps({"pid": os.getpid()}))
        time.sleep(60)
        return 0
    raise ValueError("unknown lifetime fixture mode")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].startswith("--lifetime-"):
        sys.exit(lifetime_fixture())
    unittest.main()
