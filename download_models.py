
import os
import asyncio
import httpx
from pathlib import Path

MODELS = {
    "models/inpainting/lama.onnx": "https://github.com/any-shape/simple-lama-inpainting/releases/download/v0.1.0/lama.onnx",
    "models/masking/u2netp.onnx": "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2netp.onnx"
}

async def download_model(name, url):
    path = Path(name)
    if path.exists():
        print(f"[OK] {name} already exists.")
        return

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
    except Exception as e:
        print(f"[Error] Failed to download {name}: {e}")

async def main():
    tasks = [download_model(name, url) for name, url in MODELS.items()]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
