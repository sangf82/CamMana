"""
Test Script for Check-In Processing

This script processes the test data in database/car_history folder
and demonstrates the check-in flow:

1. Reads existing images (front_cam and side_cam)
2. Calls external AI APIs for:
   - Plate detection (ALPR) from front image
   - Color detection from side image
   - Wheel counting from side image (x2 for full vehicle)
3. Saves API results as JSON in each car folder
4. Creates history record with pending status

Usage:
    cd CamMana
    uv run python -m scripts.test_checkin

Or process a specific folder:
    uv run python -m scripts.test_checkin --folder "database/car_history/15-01-2026/984860db-..."
"""
import asyncio
import argparse
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.car_process.core.checkin_service import get_checkin_service


async def process_single_folder(folder_path: Path):
    """Process a single test folder"""
    service = get_checkin_service()
    
    print(f"\n{'='*60}")
    print(f"Processing: {folder_path.name}")
    print(f"{'='*60}")
    
    try:
        result = await service.process_existing_folder(folder_path)
        
        if result:
            print(f"✅ Success!")
            print(f"   UUID:        {result.uuid}")
            print(f"   Plate:       {result.plate_number or 'Not detected'}")
            print(f"   Confidence:  {result.plate_confidence:.2%}")
            print(f"   Color:       {result.color or 'Not detected'}")
            print(f"   Wheels:      {result.wheel_count} (total, both sides)")
            print(f"   Status:      {result.status}")
            print(f"   Folder:      {result.folder_path}")
            return result
        else:
            print(f"❌ Failed: Could not process folder")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


async def process_all_test_data(date_folder: str = None):
    """Process all test data in car_history directory"""
    car_history_dir = Path("database/car_history")
    
    if not car_history_dir.exists():
        print(f"❌ Car history directory not found: {car_history_dir}")
        return
    
    # Find date folders to process
    if date_folder:
        date_folders = [car_history_dir / date_folder]
    else:
        date_folders = sorted([f for f in car_history_dir.iterdir() if f.is_dir()])
    
    print(f"\n{'#'*60}")
    print(f"# Check-In Test Processing")
    print(f"# Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"# Folders to process: {len(date_folders)}")
    print(f"{'#'*60}")
    
    results = []
    errors = []
    skipped = []
    
    for date_dir in date_folders:
        if not date_dir.exists():
            print(f"\n⚠️ Date folder not found: {date_dir.name}")
            continue
        
        print(f"\n📅 Processing date: {date_dir.name}")
        
        # Find car folders
        car_folders = sorted([f for f in date_dir.iterdir() if f.is_dir()])
        print(f"   Found {len(car_folders)} car folders")
        
        for car_folder in car_folders:
            # Check if already processed
            status_file = car_folder / "checkin_status.json"
            if status_file.exists():
                import json
                with open(status_file) as f:
                    existing = json.load(f)
                    if existing.get("plate_number") or existing.get("color"):
                        print(f"\n⏭️ Skipping already processed: {car_folder.name}")
                        skipped.append(car_folder.name)
                        continue
            
            result = await process_single_folder(car_folder)
            
            if result:
                results.append({
                    "folder": car_folder.name,
                    "plate": result.plate_number,
                    "color": result.color,
                    "wheels": result.wheel_count
                })
            else:
                errors.append(car_folder.name)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Processed: {len(results)}")
    print(f"Skipped:   {len(skipped)}")
    print(f"Errors:    {len(errors)}")
    
    if results:
        print(f"\n📊 Detection Results:")
        print(f"{'Folder':<50} {'Plate':<15} {'Color':<10} {'Wheels'}")
        print(f"{'-'*85}")
        for r in results:
            print(f"{r['folder'][:48]:<50} {r['plate'] or 'N/A':<15} {r['color'] or 'N/A':<10} {r['wheels']}")
    
    if errors:
        print(f"\n❌ Failed folders:")
        for e in errors:
            print(f"   - {e}")
    
    # Cleanup
    service = get_checkin_service()
    await service.close()
    
    print(f"\n✅ Test complete!")
    return results


async def verify_result(folder_path: str, plate: str):
    """Verify a detection result with corrected plate number"""
    service = get_checkin_service()
    
    print(f"\n{'='*60}")
    print(f"Verifying: {folder_path}")
    print(f"Plate: {plate}")
    print(f"{'='*60}")
    
    try:
        result = await service.verify_plate(folder_path, plate, approved=True)
        
        if result.get("success"):
            print(f"✅ Verification successful!")
            if result.get("new_path"):
                print(f"   Old path: {result['old_path']}")
                print(f"   New path: {result['new_path']}")
        else:
            print(f"❌ Verification failed: {result.get('error')}")
            
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None
    finally:
        await service.close()


def main():
    parser = argparse.ArgumentParser(description="Test check-in processing with existing data")
    parser.add_argument("--folder", type=str, help="Path to specific folder to process")
    parser.add_argument("--date", type=str, help="Date folder to process (e.g., 15-01-2026)")
    parser.add_argument("--verify", type=str, help="Path to folder to verify")
    parser.add_argument("--plate", type=str, help="Corrected plate number for verification")
    
    args = parser.parse_args()
    
    if args.verify and args.plate:
        # Verification mode
        asyncio.run(verify_result(args.verify, args.plate))
    elif args.folder:
        # Single folder mode
        folder = Path(args.folder)
        asyncio.run(process_single_folder(folder))
    else:
        # Process all test data
        asyncio.run(process_all_test_data(args.date))


if __name__ == "__main__":
    main()
