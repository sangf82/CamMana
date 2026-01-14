"""Comprehensive Backend Refactoring Test Suite

This script tests all components of the refactored backend:
- Data process modules
- Detection services
- API imports
- Server startup
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

def test_data_process_imports():
    """Test data_process package imports"""
    print("\n📦 Testing data_process package...")
    try:
        from backend import data_process
        
        # Test camera functions
        assert hasattr(data_process, 'get_cameras_config')
        assert hasattr(data_process, 'save_camera')
        print("  ✓ Camera operations available")
        
        # Test registered cars functions
        assert hasattr(data_process, 'get_registered_cars')
        assert hasattr(data_process, 'import_registered_cars')
        print("  ✓ Registered cars operations available")
        
        # Test history functions
        assert hasattr(data_process, 'get_history_data')
        assert hasattr(data_process, 'save_history_record')
        print("  ✓ History operations available")
        
        # Test captured cars functions
        assert hasattr(data_process, 'save_captured_car')
        assert hasattr(data_process, 'log_detection_event')
        print("  ✓ Captured cars operations available")
        
        # Test config functions
        assert hasattr(data_process, 'get_locations')
        assert hasattr(data_process, 'get_cam_types')
        print("  ✓ Configuration operations available")
        
        # Test report module
        assert hasattr(data_process, 'report')
        print("  ✓ Report module available")
        
        print("  ✅ All data_process imports successful!")
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_detection_services():
    """Test detection services"""
    print("\n🔍 Testing detection services...")
    try:
        from backend.detect_car import info_detect, volume_detect
        
        # Test info detection functions
        assert hasattr(info_detect, 'detect_plate')
        assert hasattr(info_detect, 'detect_colors')
        assert hasattr(info_detect, 'count_wheels')
        assert hasattr(info_detect, 'detect_all_info')
        print("  ✓ Info detection functions available")
        
        # Test volume detection functions
        assert hasattr(volume_detect, 'detect_truck_box_dimensions')
        assert hasattr(volume_detect, 'calculate_volume')
        print("  ✓ Volume detection functions available")
        
        print("  ✅ All detection services successful!")
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_routers():
    """Test API routers"""
    print("\n🌐 Testing API routers...")
    try:
        from backend.api import camera_router, schedule_router, detection_router, history_router
        
        assert camera_router is not None
        assert schedule_router is not None
        assert detection_router is not None
        assert history_router is not None
        print("  ✓ All routers imported successfully")
        
        print("  ✅ All API routers successful!")
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_server_creation():
    """Test server creation"""
    print("\n🚀 Testing server creation...")
    try:
        from backend.server import create_app
        
        app = create_app()
        assert app is not None
        print("  ✓ FastAPI app created successfully")
        
        # Check routes are registered
        routes = [route.path for route in app.routes]
        print(f"  ✓ Total routes: {len(routes)}")
        
        # Check for key routes
        assert any('/api/cameras' in route for route in routes)
        print("  ✓ Camera routes registered")
        
        assert any('/api/history' in route for route in routes)
        print("  ✓ History routes registered")
        
        print("  ✅ Server creation successful!")
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_registered_cars_functionality():
    """Test registered cars with the new structure"""
    print("\n🚗 Testing registered cars functionality...")
    try:
        from backend import data_process
        
        # Test getting registered cars
        cars = data_process.get_registered_cars(date="14-01-2026")
        print(f"  ✓ Found {len(cars)} cars for 14-01-2026")
        
        # Test available dates
        dates = data_process.get_available_registered_cars_dates()
        print(f"  ✓ Available dates: {dates}")
        
        print("  ✅ Registered cars functionality works!")
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("="*60)
    print("🧪 Backend Refactoring Test Suite")
    print("="*60)
    
    results = []
    results.append(("Data Process", test_data_process_imports()))
    results.append(("Detection Services", test_detection_services()))
    results.append(("API Routers", test_api_routers()))
    results.append(("Server Creation", test_server_creation()))
    results.append(("Registered Cars", test_registered_cars_functionality()))
    
    print("\n" + "="*60)
    print("📊 Test Results Summary")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {name}")
    
    print(f"\n  Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Backend refactoring successful!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
