"""
Test script to demonstrate the new registered cars functionality
This shows how the date-based naming and import logic works
"""

from backend.data_process import csv_storage
from datetime import datetime

def test_registered_cars():
    print("=" * 60)
    print("Testing Registered Cars with Date-Based Naming")
    print("=" * 60)
    
    # Test 1: Get registered cars for 14-01-2026
    print("\n1. Getting registered cars for 14-01-2026:")
    cars_14 = csv_storage.get_registered_cars(date="14-01-2026")
    print(f"   Found {len(cars_14)} cars")
    for car in cars_14:
        print(f"   - {car['plate_number']}: {car['owner']} ({car['model']})")
    
    # Test 2: Get registered cars for 15-01-2026
    print("\n2. Getting registered cars for 15-01-2026:")
    cars_15 = csv_storage.get_registered_cars(date="15-01-2026")
    print(f"   Found {len(cars_15)} cars")
    for car in cars_15:
        print(f"   - {car['plate_number']}: {car['owner']} ({car['model']})")
    
    # Test 3: Get available dates
    print("\n3. Available registered cars dates:")
    dates = csv_storage.get_available_registered_cars_dates()
    for date in dates:
        print(f"   - {date}")
    
    # Test 4: Test import logic
    print("\n4. Testing import logic:")
    print("   Scenario: Import new data for 15-01-2026 with:")
    print("   - Keep existing: 29A-123.45, 29A-252.67")
    print("   - Add new: 55G-999.88")
    print("   - Delete: 82D-543.21 (not in import)")
    
    new_import_data = [
        {
            'plate_number': '29A-123.45',
            'owner': 'Sơn',
            'model': 'Huyndai',
            'color': 'Trắng',
            'notes': '4 bánh',
            'box_dimensions': '6.5 x 4.7 x 5.6 m',
            'standard_volume': '15.6 - 20'
        },
        {
            'plate_number': '29A-252.67',
            'owner': 'Sáng (Updated)',  # Updated owner
            'model': 'Tipper',
            'color': 'Vàng',
            'notes': '8 bánh',
            'box_dimensions': '12 x 34 x 12 m',
            'standard_volume': '12 - 33'
        },
        {
            'plate_number': '55G-999.88',
            'owner': 'Tân',
            'model': 'Isuzu',
            'color': 'Đỏ',
            'notes': '6 bánh',
            'box_dimensions': '8.0 x 5.5 x 6.0 m',
            'standard_volume': '20 - 26'
        }
    ]
    
    # Perform import
    stats = csv_storage.import_registered_cars(new_import_data, date="15-01-2026")
    
    print(f"\n   Import Results:")
    print(f"   - Added: {stats['added']} cars {stats['added_plates']}")
    print(f"   - Updated: {stats['updated']} cars {stats['updated_plates']}")
    print(f"   - Deleted: {stats['deleted']} cars {stats['deleted_plates']}")
    print(f"   - Total: {stats['total']} cars")
    
    # Verify the result
    print("\n5. Verifying imported data:")
    cars_15_after = csv_storage.get_registered_cars(date="15-01-2026")
    print(f"   Found {len(cars_15_after)} cars after import")
    for car in cars_15_after:
        print(f"   - {car['plate_number']}: {car['owner']} ({car['model']})")
    
    # Test 5: Test auto-migration to new day
    print("\n6. Testing auto-migration (if today's file doesn't exist):")
    print(f"   Current date: {datetime.now().strftime('%d-%m-%Y')}")
    print("   When you call get_registered_cars() without a date,")
    print("   it will automatically copy from the most recent date")
    print("   and update the created_at field to today.")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    test_registered_cars()
