"""
Test Script for Master/Client Sync

This script tests the data synchronization between Master and Client nodes.
Run this on the CLIENT PC after configuring it to connect to a Master.

Usage:
    uv run python tests/test_sync.py

Requirements:
    - Master PC must be running and accessible
    - Client must be configured (database/sync_config.json has is_destination=false and remote_url set)
"""
import asyncio
import json
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.data_process.sync.proxy import (
    is_client_mode, 
    get_master_url, 
    proxy_get, 
    upload_folder_to_master
)
from backend.config import PROJECT_ROOT

# Test results
results = []

def log_result(test_name: str, success: bool, details: str = ""):
    status = "✅ PASS" if success else "❌ FAIL"
    results.append((test_name, success, details))
    print(f"{status}: {test_name}")
    if details:
        print(f"       {details}")


async def test_1_check_client_mode():
    """Test 1: Verify this PC is in Client mode"""
    is_client = is_client_mode()
    master_url = get_master_url()
    
    if is_client and master_url:
        log_result("Check Client Mode", True, f"Master URL: {master_url}")
        return True
    else:
        log_result("Check Client Mode", False, 
                   "Not in client mode. Check database/sync_config.json")
        return False


async def test_2_check_master_connectivity():
    """Test 2: Check if we can reach the Master"""
    master_url = get_master_url()
    if not master_url:
        log_result("Master Connectivity", False, "No master URL configured")
        return False
    
    import httpx
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{master_url}/api/system/info")
            if response.status_code == 200:
                data = response.json()
                log_result("Master Connectivity", True, 
                           f"Master PC: {data.get('pc_name', 'Unknown')}")
                return True
            else:
                log_result("Master Connectivity", False, 
                           f"HTTP {response.status_code}")
                return False
    except Exception as e:
        log_result("Master Connectivity", False, str(e))
        return False


async def test_3_check_file_sync_endpoint():
    """Test 3: Check if Master's file sync endpoint is available"""
    master_url = get_master_url()
    if not master_url:
        log_result("File Sync Endpoint", False, "No master URL")
        return False
    
    import httpx
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{master_url}/api/sync/files/health")
            if response.status_code == 200:
                data = response.json()
                log_result("File Sync Endpoint", True, 
                           f"Available: {data.get('available', False)}")
                return True
            else:
                log_result("File Sync Endpoint", False, 
                           f"HTTP {response.status_code}")
                return False
    except Exception as e:
        log_result("File Sync Endpoint", False, str(e))
        return False


async def test_4_proxy_get_history():
    """Test 4: Test proxy GET for history data"""
    result = await proxy_get("/api/history")
    
    if result is not None:
        count = len(result) if isinstance(result, list) else 0
        log_result("Proxy GET History", True, f"Received {count} records")
        return True
    else:
        log_result("Proxy GET History", False, "No response from master")
        return False


async def test_5_proxy_get_registered_cars():
    """Test 5: Test proxy GET for registered cars"""
    result = await proxy_get("/api/registered_cars")
    
    if result is not None:
        count = len(result) if isinstance(result, list) else 0
        log_result("Proxy GET Registered Cars", True, f"Received {count} cars")
        return True
    else:
        log_result("Proxy GET Registered Cars", False, "No response from master")
        return False


async def test_6_upload_test_folder():
    """Test 6: Test folder upload to Master"""
    # Create a temporary folder with test files
    temp_dir = Path(tempfile.mkdtemp())
    date_folder = datetime.now().strftime("%d-%m-%Y")
    test_folder_name = f"test_sync_{datetime.now().strftime('%H-%M-%S')}"
    
    test_folder = temp_dir / date_folder / test_folder_name
    test_folder.mkdir(parents=True, exist_ok=True)
    
    # Create test files
    (test_folder / "test_image.jpg").write_bytes(b"fake image data for testing")
    (test_folder / "test_status.json").write_text(json.dumps({
        "test": True,
        "timestamp": datetime.now().isoformat()
    }))
    
    try:
        # Upload the folder
        result = await upload_folder_to_master(test_folder)
        
        if result and result.get("success"):
            master_path = result.get("folder_path", "Unknown")
            file_count = result.get("file_count", 0)
            log_result("Upload Test Folder", True, 
                       f"Uploaded to Master: {master_path} ({file_count} files)")
            return True
        else:
            log_result("Upload Test Folder", False, 
                       "Upload failed or returned no result")
            return False
    except Exception as e:
        log_result("Upload Test Folder", False, str(e))
        return False
    finally:
        # Cleanup temp folder
        shutil.rmtree(temp_dir, ignore_errors=True)


async def test_7_sync_receive_endpoint():
    """Test 7: Test sync receive endpoint (record sync)"""
    master_url = get_master_url()
    if not master_url:
        log_result("Sync Receive Endpoint", False, "No master URL")
        return False
    
    import httpx
    try:
        payload = {
            "type": "test",
            "action": "ping",
            "data": {"test": True},
            "timestamp": datetime.now().isoformat()
        }
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{master_url}/api/sync/receive",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 200:
                log_result("Sync Receive Endpoint", True, "Ping successful")
                return True
            else:
                log_result("Sync Receive Endpoint", False, 
                           f"HTTP {response.status_code}")
                return False
    except Exception as e:
        log_result("Sync Receive Endpoint", False, str(e))
        return False


async def run_all_tests():
    print("\n" + "="*60)
    print("🔄 CamMana Master/Client Sync Test")
    print("="*60 + "\n")
    
    # Check sync config
    config_file = PROJECT_ROOT / "database" / "sync_config.json"
    if config_file.exists():
        with open(config_file) as f:
            config = json.load(f)
        print(f"📋 Current Config:")
        print(f"   is_destination (Master): {config.get('is_destination', True)}")
        print(f"   remote_url: {config.get('remote_url', 'Not set')}")
        print()
    else:
        print("⚠️  No sync_config.json found. Using defaults (Master mode).\n")
    
    # Run tests
    await test_1_check_client_mode()
    await test_2_check_master_connectivity()
    await test_3_check_file_sync_endpoint()
    await test_4_proxy_get_history()
    await test_5_proxy_get_registered_cars()
    await test_6_upload_test_folder()
    await test_7_sync_receive_endpoint()
    
    # Summary
    print("\n" + "="*60)
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    print(f"📊 Results: {passed}/{total} tests passed")
    print("="*60 + "\n")
    
    if passed < total:
        print("💡 If tests failed, check:")
        print("   1. Is the Master PC running?")
        print("   2. Is the firewall allowing port 8000?")
        print("   3. Is sync_config.json correctly configured?")
        print()


if __name__ == "__main__":
    asyncio.run(run_all_tests())
