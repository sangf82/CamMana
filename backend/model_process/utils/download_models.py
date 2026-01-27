"""
CamMana Model Downloader

Downloads required AI model weights to backend/model_process/models/
"""
import asyncio
import httpx
import sys
from pathlib import Path

# Model paths - in backend/model_process/models folder
def get_models_base() -> Path:
    """Get models directory path"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS) / "backend" / "model_process" / "models"  # type: ignore[attr-defined]
    # Development: models in backend/model_process/models
    return Path(__file__).parent.parent / "models"

MODELS_BASE = get_models_base()

# Only YOLO model is required now (inpainting/masking removed)
MODELS = {
    "car_detect/yolo11n.pt": "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt"
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
