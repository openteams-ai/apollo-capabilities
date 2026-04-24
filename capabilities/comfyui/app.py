import os
import urllib.request

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


def hook(count, block_size, total_size):
    got = count * block_size
    if total_size > 0:
        pct = min(100.0, got * 100 / total_size)
        print(f"  {pct:5.1f}%  {got/(1024**3):.2f} / {total_size/(1024**3):.2f} GB", end="\r")


for url, dest in DOWNLOADS:
    if os.path.exists(dest):
        print(f"{dest} already present, skipping.")
        continue
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    print(f"Downloading -> {dest}")
    urllib.request.urlretrieve(url, dest, reporthook=hook)
    print()

print("All default model downloads complete.")
