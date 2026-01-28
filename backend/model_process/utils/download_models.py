"""
CamMana Model Downloader

Downloads required AI model weights to backend/model_process/models/
Now uses ONNX format for lightweight deployment (no PyTorch required).
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

# ONNX models for lightweight deployment
# Note: YOLO11n ONNX is ~22MB vs PyTorch ~6MB, but avoids 2GB torch dependency!
MODELS = {
    # Primary: ONNX format (no PyTorch required)
    "car_detect/yolo11n.onnx": "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.onnx",
}

# Backup: PyTorch format (only if user has ultralytics installed)
MODELS_PYTORCH = {
    "car_detect/yolo11n.pt": "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt"
}


async def download_model(name: str, url: str) -> bool:
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
                total = int(response.headers.get("content-length", 0))
                downloaded = 0
                with open(path, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            pct = downloaded * 100 // total
                            print(f"\r[...] {name}: {pct}%", end="", flush=True)
                print()  # New line after progress
        print(f"[Success] {name} downloaded.")
        return True
    except Exception as e:
        print(f"[Error] Failed to download {name}: {e}")
        if path.exists():
            path.unlink()  # Remove partial download
        return False


async def main():
    print(f"Downloading ONNX models to: {MODELS_BASE.absolute()}")
    print("=" * 50)
    
    tasks = [download_model(name, url) for name, url in MODELS.items()]
    results = await asyncio.gather(*tasks)
    
    success = sum(results)
    print("=" * 50)
    print(f"Download complete: {success}/{len(MODELS)} models ready.")
    
    if success < len(MODELS):
        print("\n⚠️ Some models failed to download.")
        print("   Try running again or download manually.")


if __name__ == "__main__":
    asyncio.run(main())
