"""Test script to verify modular API router structure

This script verifies that all API routers are properly split into modules
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

def test_api_structure():
    print("="*60)
    print("📁 API Module Structure Test")
    print("="*60)
    
    # Check all expected modules exist
    api_dir = Path(__file__).parent / "backend" / "api"
    expected_files = [
        "__init__.py",
        "_shared.py",
        "cameras.py",
        "config.py",
        "detection.py",
        "history.py",
        "schedule.py"
    ]
    
    print("\n📂 Checking API module files...")
    for file in expected_files:
        filepath = api_dir / file
        if filepath.exists():
            size = filepath.stat().st_size
            print(f"  ✓ {file} ({size:,} bytes)")
        else:
            print(f"  ❌ {file} (MISSING)")
    
    # Test imports
    print("\n🔌 Testing router imports...")
    try:
        from backend.api import (
            camera_router, config_router, detection_router,
            history_router, schedule_router
        )
        
        routes_count = {
            'camera': len(camera_router.routes),
            'config': len(config_router.routes),
            'detection': len(detection_router.routes),
            'history': len(history_router.routes),
            'schedule': len(schedule_router.routes)
        }
        
        total_routes = sum(routes_count.values())
        
        for name, count in routes_count.items():
            print(f"  ✓ {name}_router: {count} routes")
        
        print(f"\n  📊 Total routes: {total_routes}")
        print("  ✅ All routers imported successfully!")
        
    except Exception as e:
        print(f"  ❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test server integration
    print("\n🚀 Testing server integration...")
    try:
        from backend.server import create_app
        app = create_app()
        print(f"  ✓ Server created with {len(app.routes)} total routes")
        print("  ✅ Server integration successful!")
    except Exception as e:
        print(f"  ❌ Server creation failed: {e}")
        return False
    
    print("\n" + "="*60)
    print("🎉 All API structure tests passed!")
    print("="*60)
    return True

if __name__ == "__main__":
    success = test_api_structure()
    sys.exit(0 if success else 1)
