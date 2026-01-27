"""
CamMana Model Downloader

Downloads required AI model weights to backend/model_process/models/
"""
import os
import asyncio
import httpx
from pathlib import Path

# Model paths relative to project root (new location)
MODELS_BASE = Path("backend/model_process/models")

MODELS = {
    "inpainting/lama.onnx": "https://github.com/any-shape/simple-lama-inpainting/releases/download/v0.1.0/lama.onnx",
    "masking/u2netp.onnx": "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2netp.onnx"
}

async def download_model(name: str, url: str):
    path = MODELS_BASE / name
    if path.exists():
        print(f"[OK] {name} already exists.")
        return True

    print(f"[...] Downloading {name} from {url}")
    path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            async with client.stream("GET", url, follow_redirects=True) as response:
                response.raise_for_status()
                with open(path, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)
        print(f"[Success] {name} downloaded.")
        return True
    except Exception as e:
        print(f"[Error] Failed to download {name}: {e}")
        return False

async def main():
    print(f"Downloading models to: {MODELS_BASE.absolute()}")
    tasks = [download_model(name, url) for name, url in MODELS.items()]
    results = await asyncio.gather(*tasks)
    
    success = sum(results)
    print(f"\nDownload complete: {success}/{len(MODELS)} models ready.")

if __name__ == "__main__":
    asyncio.run(main())
