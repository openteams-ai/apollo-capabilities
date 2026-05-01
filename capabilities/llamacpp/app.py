import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.error
import urllib.request
import zipfile

BIN_DIR = 'bin'
MARKER = os.path.join(BIN_DIR, '.llamacpp_version')
SERVER_BINARY = os.path.join(BIN_DIR, 'llama-server.exe' if sys.platform == 'win32' else 'llama-server')
BACKEND = os.environ.get('LLAMA_BACKEND', 'cpu')


def parse_cuda_ver(name):
    m = re.search(r'cuda-(\d+)\.(\d+)', name)
    return tuple(int(x) for x in m.groups()) if m else (0, 0)


def detect_local_cuda():
    ov = os.environ.get('CONDA_OVERRIDE_CUDA')
    if ov:
        p = ov.strip().split('.')
        try:
            return (int(p[0]), int(p[1]) if len(p) > 1 else 0)
        except ValueError:
            pass
    try:
        out = subprocess.check_output(['nvidia-smi'], text=True, stderr=subprocess.DEVNULL)
        m = re.search(r'CUDA Version:\s*(\d+)\.(\d+)', out)
        if m:
            return (int(m.group(1)), int(m.group(2)))
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    return None


def pick_cuda_asset(assets, local_cuda, prefix='win', suffix='.zip'):
    cands = [a for a in assets if prefix in a['name'] and 'cuda' in a['name'] and 'x64' in a['name'] and a['name'].endswith(suffix) and 'cudart' not in a['name']]
    if not cands:
        return None
    if local_cuda is not None:
        compat = [a for a in cands if parse_cuda_ver(a['name']) <= local_cuda]
        if compat:
            compat.sort(key=lambda a: parse_cuda_ver(a['name']), reverse=True)
            return compat[0]
        print(f'WARNING: Local CUDA is {local_cuda[0]}.{local_cuda[1]} but no compatible build found.')
        for a in cands:
            v = parse_cuda_ver(a['name'])
            n = a['name']
            print(f'  {n}  (requires CUDA {v[0]}.{v[1]})')
        print('Try the cpu environment instead.')
        sys.exit(1)
    cands.sort(key=lambda a: parse_cuda_ver(a['name']))
    n = cands[0]['name']
    print(f'WARNING: Could not detect local CUDA version, using conservative pick: {n}')
    return cands[0]


def pick_cudart(assets, selected):
    tv = parse_cuda_ver(selected['name'])
    cands = [a for a in assets if 'cudart' in a['name'] and a['name'].endswith('.zip')]
    for a in cands:
        if parse_cuda_ver(a['name']) == tv:
            return a
    compat = [a for a in cands if parse_cuda_ver(a['name']) <= tv]
    if compat:
        compat.sort(key=lambda a: parse_cuda_ver(a['name']), reverse=True)
        return compat[0]
    return cands[0] if cands else None


def detect_asset(assets, local_cuda=None):
    plat = sys.platform
    arch = platform.machine().lower()

    def first(pred):
        return next((a for a in assets if pred(a['name'])), None)

    if plat == 'linux':
        if BACKEND == 'gpu':
            return first(lambda n: 'ubuntu' in n and 'vulkan' in n and 'x64' in n and n.endswith('.tar.gz'))
        return first(lambda n: 'ubuntu' in n and 'x64' in n and 'vulkan' not in n and 'openvino' not in n and 'rocm' not in n and n.endswith('.tar.gz'))
    if plat == 'darwin':
        if 'arm' in arch or 'aarch64' in arch:
            return first(lambda n: 'macos' in n and 'arm64' in n and 'kleidiai' not in n and n.endswith('.tar.gz'))
        return first(lambda n: 'macos' in n and 'x64' in n and n.endswith('.tar.gz'))
    if plat == 'win32':
        if BACKEND == 'gpu':
            return pick_cuda_asset(assets, local_cuda)
        return first(lambda n: 'win' in n and 'cpu' in n and 'x64' in n and n.endswith('.zip'))
    print(f'ERROR: Unsupported platform {plat}/{arch}')
    sys.exit(1)


def download_file(url, dest):
    print(f'Downloading {os.path.basename(dest)} ...')
    urllib.request.urlretrieve(url, dest, reporthook=lambda c, bs, ts: print(f'  {c*bs/(1024**2):.1f} MB', end='\r') if ts > 0 else None)
    print()


def extract(archive, dest_dir):
    print('Extracting...')
    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir)
    os.makedirs(dest_dir, exist_ok=True)
    if archive.endswith('.tar.gz'):
        with tarfile.open(archive) as tf:
            tf.extractall(dest_dir)
    elif archive.endswith('.zip'):
        with zipfile.ZipFile(archive, 'r') as zf:
            zf.extractall(dest_dir)
    os.remove(archive)
    entries = os.listdir(dest_dir)
    subdirs = [d for d in entries if os.path.isdir(os.path.join(dest_dir, d))]
    if len(subdirs) == 1 and len(entries) == 1:
        sub = os.path.join(dest_dir, subdirs[0])
        for item in os.listdir(sub):
            shutil.move(os.path.join(sub, item), os.path.join(dest_dir, item))
        os.rmdir(sub)


def make_executable(dest_dir):
    if sys.platform == 'win32':
        return
    for f in os.listdir(dest_dir):
        fp = os.path.join(dest_dir, f)
        if os.path.isfile(fp):
            os.chmod(fp, 0o755)


def installed_version_key():
    if not os.path.exists(MARKER) or not os.path.exists(SERVER_BINARY):
        return None
    with open(MARKER) as f:
        version_key = f.read().strip()
    if version_key.endswith(f'-{BACKEND}'):
        return version_key
    return None


def release_metadata():
    print('Checking latest llama.cpp release...')
    req = urllib.request.Request(
        'https://api.github.com/repos/ggml-org/llama.cpp/releases/latest',
        headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'apollo-desktop'},
    )
    return json.loads(urllib.request.urlopen(req, timeout=10).read())


try:
    data = release_metadata()
except (TimeoutError, urllib.error.URLError) as exc:
    version_key = installed_version_key()
    if version_key:
        version = version_key.rsplit('-', 1)[0]
        print(f'WARNING: Could not check latest llama.cpp release: {exc}')
        print(f'Using cached llama.cpp {version} ({BACKEND}) from {BIN_DIR}/.')
        sys.exit(0)
    print(f'ERROR: Could not download llama.cpp release metadata: {exc}')
    print('Connect to the internet for the first run, then retry offline after the binary is cached.')
    sys.exit(1)
tag = data['tag_name']
local_cuda = None
if sys.platform == 'win32' and BACKEND == 'gpu':
    local_cuda = detect_local_cuda()
    if local_cuda:
        print(f'Detected local CUDA: {local_cuda[0]}.{local_cuda[1]}')
version_key = f'{tag}-{BACKEND}'
if installed_version_key() == version_key:
    print(f'llama.cpp {tag} ({BACKEND}) already downloaded, skipping.')
    sys.exit(0)
asset = detect_asset(data['assets'], local_cuda)
if not asset:
    print(f'ERROR: No matching asset for {sys.platform}/{platform.machine()}/{BACKEND}')
    for a in data['assets']:
        n = a['name']
        print(f'  {n}')
    sys.exit(1)
aname = asset['name']
print(f'Selected: {aname}  (platform={sys.platform}, backend={BACKEND})')
download_file(asset['browser_download_url'], aname)
extract(aname, BIN_DIR)
make_executable(BIN_DIR)
with open(MARKER, 'w') as f:
    f.write(version_key)
print(f'llama.cpp {tag} ({BACKEND}) ready in {BIN_DIR}/')
if sys.platform == 'win32' and BACKEND == 'gpu':
    crt = pick_cudart(data['assets'], asset)
    if crt:
        cn = crt['name']
        print(f'Also downloading CUDA runtime: {cn}')
        download_file(crt['browser_download_url'], cn)
        with zipfile.ZipFile(cn, 'r') as zf:
            zf.extractall(BIN_DIR)
        os.remove(cn)
