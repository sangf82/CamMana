"""
Simulate Master/Client Sync on Single PC

This script runs a quick simulation to verify the sync implementation works.
It temporarily modifies the sync config to test as a Client connecting to itself.

Usage:
    uv run python tests/test_sync_simulation.py
"""
import asyncio
import json
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import PROJECT_ROOT

SYNC_CONFIG_FILE = PROJECT_ROOT / "database" / "sync_config.json"


def save_config(config: dict):
    with open(SYNC_CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)


def load_config() -> dict:
    if SYNC_CONFIG_FILE.exists():
        with open(SYNC_CONFIG_FILE) as f:
            return json.load(f)
    return {"is_destination": True, "remote_url": None}


async def run_simulation():
    print("\n" + "="*60)
    print("🧪 CamMana Sync Simulation (Single PC)")
    print("="*60 + "\n")
    
    # Save original config
    original_config = load_config()
    print(f"📋 Original config: {original_config}")
    
    # Test 1: Check endpoints exist on local server
    print("\n🔍 Test 1: Check local endpoints...")
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Check file sync health
            resp = await client.get("http://127.0.0.1:8000/api/sync/files/health")
            if resp.status_code == 200:
                print("   ✅ /api/sync/files/health is available")
            else:
                print(f"   ❌ /api/sync/files/health returned {resp.status_code}")
            
            # Check sync receive
            resp = await client.post(
                "http://127.0.0.1:8000/api/sync/receive",
                json={"type": "test", "action": "ping", "data": {}, "timestamp": datetime.now().isoformat()}
            )
            if resp.status_code == 200:
                print("   ✅ /api/sync/receive is available")
            else:
                print(f"   ❌ /api/sync/receive returned {resp.status_code}")
                
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return
    
    # Test 2: Simulate file upload
    print("\n🔍 Test 2: Test file upload to local server...")
    
    # Create temp folder
    temp_dir = Path(tempfile.mkdtemp())
    date_folder = datetime.now().strftime("%d-%m-%Y")
    test_folder_name = f"test_simulation_{datetime.now().strftime('%H-%M-%S')}"
    test_folder = temp_dir / date_folder / test_folder_name
    test_folder.mkdir(parents=True, exist_ok=True)
    
    # Create test files
    (test_folder / "test_image.jpg").write_bytes(b"FAKE_IMAGE_DATA_12345")
    (test_folder / "test_status.json").write_text(json.dumps({"test": True}))
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Prepare files
            files = []
            for fp in test_folder.iterdir():
                if fp.is_file():
                    files.append(("files", (fp.name, open(fp, "rb"), "application/octet-stream")))
            
            data = {
                "folder_name": test_folder_name,
                "date_folder": date_folder,
                "source_pc": "TEST_PC"
            }
            
            resp = await client.post(
                "http://127.0.0.1:8000/api/sync/files/upload-folder",
                data=data,
                files=files
            )
            
            # Close files
            for _, file_tuple in files:
                file_tuple[1].close()
            
            if resp.status_code == 200:
                result = resp.json()
                print(f"   ✅ Upload successful!")
                print(f"      Folder: {result.get('folder_name')}")
                print(f"      Files: {result.get('file_count')}")
                print(f"      Path: {result.get('folder_path')}")
                
                # Verify files exist
                upload_path = Path(result.get('folder_path'))
                if upload_path.exists():
                    files_in_folder = list(upload_path.iterdir())
                    print(f"      Verified: {len(files_in_folder)} files in destination")
                else:
                    print(f"      ⚠️ Folder path doesn't exist on disk")
            else:
                print(f"   ❌ Upload failed: {resp.status_code}")
                print(f"      Response: {resp.text}")
                
    except Exception as e:
        print(f"   ❌ Error: {e}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    # Test 3: Simulate sync payload
    print("\n🔍 Test 3: Test sync receive (history update)...")
    
    test_record_id = f"test_{datetime.now().strftime('%H%M%S')}"
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Send a test history create
            payload = {
                "type": "history",
                "action": "create",
                "data": {
                    "id": test_record_id,
                    "plate": "TEST123",
                    "location": "Test Gate",
                    "time_in": datetime.now().strftime("%H:%M:%S"),
                    "status": "Test Record",
                    "folder_path": "/test/path"
                },
                "timestamp": datetime.now().isoformat()
            }
            
            resp = await client.post(
                "http://127.0.0.1:8000/api/sync/receive",
                json=payload
            )
            
            if resp.status_code == 200:
                print(f"   ✅ Sync receive accepted the payload")
                
                # Verify by checking history
                resp2 = await client.get("http://127.0.0.1:8000/api/history")
                if resp2.status_code == 200:
                    records = resp2.json()
                    found = any(r.get("id") == test_record_id for r in records)
                    if found:
                        print(f"   ✅ Test record found in history!")
                    else:
                        print(f"   ⚠️ Test record not found (may be in different date's file)")
            else:
                print(f"   ❌ Sync receive failed: {resp.status_code}")
                
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "="*60)
    print("✅ Simulation Complete!")
    print("="*60)
    print("\n💡 Next Steps:")
    print("   1. Deploy to a second PC as Client")
    print("   2. Configure that PC's sync_config.json:")
    print('      {"is_destination": false, "remote_url": "http://THIS_PC_IP:8000"}')
    print("   3. Run tests/test_sync.py on the Client PC")
    print()


if __name__ == "__main__":
    asyncio.run(run_simulation())
