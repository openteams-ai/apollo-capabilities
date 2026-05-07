import os
import sys
import urllib.request

if sys.platform == 'win32':
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, 'reconfigure', None)
        if reconfigure is not None:
            reconfigure(encoding='utf-8', errors='replace')

DOWNLOADS = [
    (
        "https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/diffusion_models/z_image_turbo_bf16.safetensors",
        "ComfyUI/models/diffusion_models/z_image_turbo_bf16.safetensors",
    ),
    (
        "https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/text_encoders/qwen_3_4b.safetensors",
        "ComfyUI/models/text_encoders/qwen_3_4b.safetensors",
    ),
    (
        "https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/vae/ae.safetensors",
        "ComfyUI/models/vae/ae.safetensors",
    ),
]


PROGRESS_INTERVAL_MB = 100


def make_hook():
    last_mb = [0.0]

    def hook(count, block_size, total_size):
        if total_size <= 0:
            return
        got = count * block_size
        mb = got / (1024 ** 2)
        if mb - last_mb[0] >= PROGRESS_INTERVAL_MB or got >= total_size:
            pct = min(100.0, got * 100 / total_size)
            print(f"  {pct:5.1f}%  {got/(1024**3):.2f} / {total_size/(1024**3):.2f} GB", flush=True)
            last_mb[0] = mb

    return hook


for url, dest in DOWNLOADS:
    if os.path.exists(dest):
        print(f"{dest} already present, skipping.")
        continue
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    print(f"Downloading -> {dest}")
    urllib.request.urlretrieve(url, dest, reporthook=make_hook())
    print()

print("All default model downloads complete.")
