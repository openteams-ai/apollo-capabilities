import argparse
import errno
import os
import re
import shutil
import subprocess
import sys

from huggingface_hub import HfApi, snapshot_download


DEFAULT_MODEL = 'unsloth/gemma-4-E4B-it-GGUF:Q4_K_M'
HF_HOME = 'models'


def status(message):
    print(message, flush=True)


def parse_model_spec(model):
    if ':' not in model:
        return model, None
    repo_id, selector = model.rsplit(':', 1)
    if not repo_id or not selector:
        raise ValueError(f'Invalid model spec: {model}')
    return repo_id, selector


def split_group(filename):
    match = re.match(r'(.+)-\d{5}-of-\d{5}\.gguf$', filename, re.IGNORECASE)
    return match.group(1) if match else None


def is_mmproj(path):
    return 'mmproj' in os.path.basename(path).lower()


def select_model_files(files, selector):
    ggufs = sorted(path for path in files if path.lower().endswith('.gguf'))
    model_ggufs = [path for path in ggufs if not is_mmproj(path)]
    mmproj_ggufs = [path for path in ggufs if is_mmproj(path)]

    if not selector:
        if len(model_ggufs) == 1:
            return model_ggufs + mmproj_ggufs
        raise ValueError(
            'Model selector is required because this repository has multiple GGUF files:\n'
            + '\n'.join(f'  {path}' for path in model_ggufs[:25])
        )

    selector_lower = selector.lower()
    if selector_lower.endswith('.gguf'):
        matches = [
            path for path in model_ggufs
            if path.lower() == selector_lower or os.path.basename(path).lower() == selector_lower
        ]
    else:
        matches = [path for path in model_ggufs if selector_lower in os.path.basename(path).lower()]

    if not matches:
        raise ValueError(
            f'No GGUF file in the repository matched selector {selector!r}. Available GGUF files include:\n'
            + '\n'.join(f'  {path}' for path in model_ggufs[:25])
        )

    groups = {split_group(os.path.basename(path)) for path in matches}
    groups.discard(None)
    if len(matches) > 1 and len(groups) > 1:
        raise ValueError(
            f'Multiple GGUF files matched selector {selector!r}. Use a more specific filename:\n'
            + '\n'.join(f'  {path}' for path in matches[:25])
        )

    return sorted(set(matches + mmproj_ggufs))


def run_with_pty(command, env):
    import pty

    master_fd, slave_fd = pty.openpty()
    try:
        proc = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=slave_fd,
            stderr=slave_fd,
            env=env,
            close_fds=True,
        )
    finally:
        os.close(slave_fd)

    try:
        while True:
            try:
                chunk = os.read(master_fd, 4096)
            except OSError as exc:
                if exc.errno == errno.EIO:
                    break
                raise
            if not chunk:
                break
            sys.stdout.buffer.write(chunk)
            sys.stdout.buffer.flush()
    finally:
        os.close(master_fd)

    return proc.wait()


def run_with_pipes(command, env):
    proc = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        print(line, end='', flush=True)
    return proc.wait()


def stream_command(command, env):
    status(f'Running: {" ".join(command)}')
    if sys.platform != 'win32':
        return run_with_pty(command, env)
    return run_with_pipes(command, env)


def download_with_python(repo_id, files):
    status('hf CLI was not found; using huggingface_hub snapshot_download instead.')
    status('Download progress will still be printed by the Hugging Face Python client when available.')
    cache_dir = os.path.join(os.environ.get('HF_HOME', HF_HOME), 'hub')
    snapshot_download(repo_id=repo_id, allow_patterns=files, cache_dir=cache_dir)


def ensure_model_cached(model):
    repo_id, selector = parse_model_spec(model)
    status(f'Preparing Hugging Face model cache for {model}')
    status(f'Using HF_HOME={os.environ.get("HF_HOME", HF_HOME)}')

    api = HfApi()
    status(f'Checking repository files for {repo_id} ...')
    files = api.list_repo_files(repo_id=repo_id)
    selected_files = select_model_files(files, selector)

    status('Selected model cache files:')
    for path in selected_files:
        status(f'  {path}')

    env = os.environ.copy()
    env.setdefault('HF_HOME', HF_HOME)
    env.setdefault('PYTHONUNBUFFERED', '1')

    hf = shutil.which('hf')
    if not hf:
        download_with_python(repo_id, selected_files)
        status('Model cache is ready.')
        return

    dry_run_command = [hf, 'download', repo_id, *selected_files, '--dry-run']
    status('Checking Hugging Face cache state ...')
    dry_run_code = stream_command(dry_run_command, env)
    if dry_run_code != 0:
        raise RuntimeError(f'Hugging Face dry-run failed with exit code {dry_run_code}')

    download_command = [hf, 'download', repo_id, *selected_files]
    status('Downloading missing model files, if any ...')
    download_code = stream_command(download_command, env)
    if download_code != 0:
        raise RuntimeError(f'Hugging Face download failed with exit code {download_code}')
    status('Model cache is ready.')


def server_binary():
    name = 'llama-server.exe' if sys.platform == 'win32' else 'llama-server'
    return os.path.join('bin', name)


def server_args(model, backend):
    args = [server_binary(), '-hf', model]
    if backend == 'gpu':
        args.extend(['-fa', 'on', '-c', '24000', '--n-gpu-layers', '999'])
    else:
        args.extend(['-c', '8192', '--n-gpu-layers', '0'])

    args.extend(['--top-k', '20', '--top-p', '0.95', '--min-p', '0.0'])
    args.extend(['--jinja', '--temp', '0.7'])
    if backend == 'gpu' and sys.platform in ('linux', 'win32'):
        args.extend(['-mg', '0'])
    args.extend(['-np', '1'])
    return args


def start_server(model, backend):
    binary = server_binary()
    if not os.path.exists(binary):
        raise RuntimeError(f'Expected llama.cpp server binary at {binary}; run download-llamacpp first.')

    args = server_args(model, backend)
    status('Starting llama.cpp server ...')
    status(f'Running: {" ".join(args)}')
    os.execvpe(args[0], args, os.environ.copy())


def main():
    parser = argparse.ArgumentParser(description='Prepare model cache and launch llama.cpp server.')
    parser.add_argument('--model', default=DEFAULT_MODEL)
    parser.add_argument('--backend', choices=['cpu', 'gpu'], default=os.environ.get('LLAMA_BACKEND', 'cpu'))
    args = parser.parse_args()

    os.environ.setdefault('HF_HOME', HF_HOME)
    try:
        ensure_model_cached(args.model)
        start_server(args.model, args.backend)
    except Exception as exc:
        status(f'ERROR: {exc}')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
