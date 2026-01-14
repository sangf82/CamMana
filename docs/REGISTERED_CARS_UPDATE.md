# Registered Cars - Date-Based System Update

## Overview
The registered cars data management has been updated to use date-based file naming (similar to the history system) with smart import logic.

## Changes Made

### 1. **File Naming Format**
- **Old Format**: `registered_cars.csv`
- **New Format**: `registered_cars_dd-mm-yyyy.csv`
- **Example**: 
  - `registered_cars_14-01-2026.csv`
  - `registered_cars_15-01-2026.csv`

### 2. **Test Data Created**

#### History Data (15-01-2026)
Created `history_15_01_2026.csv` with:
- 15 vehicle entries
- Mix of continuing vehicles from 14-01 and new entries
- New vehicles include: `82D-543.21`, `91E-234.56`, `33F-678.90`

#### Registered Cars Data
Created date-specific files:
- `registered_cars_14-01-2026.csv` (2 vehicles)
- `registered_cars_15-01-2026.csv` (3 vehicles, added `82D-543.21`)

### 3. **Backend Logic Updates**

#### New Functions in `csv_storage.py`:

##### `_get_registered_cars_csv_path(date: Optional[str] = None)`
- Returns path to registered cars CSV for a specific date
- Format: `dd-mm-yyyy` (supports both `-` and `_` separators)
- Defaults to today if no date provided

##### `get_registered_cars(date: Optional[str] = None)`
- Get registered cars for a specific date
- **Auto-migration**: If today's file doesn't exist, automatically copies from the most recent previous date and updates `created_at` to today
- Returns empty list if no data exists

##### `save_registered_cars(cars: List[Dict], date: Optional[str] = None)`
- Save registered cars to a date-specific file
- Ensures all cars have unique IDs
- Defaults to today's date if not specified

##### `import_registered_cars(new_cars: List[Dict], date: Optional[str] = None)`
**Smart Merge Logic:**
1. Load existing data for the date
2. Compare with imported data using `plate_number` as key
3. **Keep**: Rows that exist in both (with updated data from import)
4. **Add**: New rows from import
5. **Delete**: Rows that exist in old data but not in import
6. **Update**: `created_at` field to current date for all rows

**Returns statistics:**
```json
{
  "added": 1,
  "updated": 1,
  "deleted": 1,
  "total": 5,
  "added_plates": ["55G-999.88"],
  "updated_plates": ["29A-252.67"],
  "deleted_plates": ["82D-543.21"]
}
```

##### `get_available_registered_cars_dates()`
- Returns list of all dates with registered cars files
- Sorted newest first
- Format: `dd-mm-yyyy`

##### `_get_previous_registered_cars_date()`
- Helper to get the most recent previous date
- Used for auto-migration

### 4. **API Endpoints Updated**

#### `GET /api/cameras/registered_cars?date=dd-mm-yyyy`
- Get registered cars for a specific date
- Optional `date` parameter (defaults to today)

#### `GET /api/cameras/registered_cars/dates`
- Get list of available dates
- Returns: `{"success": true, "dates": ["15-01-2026", "14-01-2026"]}`

#### `POST /api/cameras/registered_cars`
- Save registered cars for a date
- Body: `{"cars": [...], "date": "dd-mm-yyyy"}` (date optional)

#### `POST /api/cameras/registered_cars/import` ⭐ NEW
- Import registered cars with smart merge logic
- Body: `{"cars": [...], "date": "dd-mm-yyyy"}` (date optional)
- Returns import statistics

## Usage Examples

### Example 1: Auto-Migration to New Day
```python
# On 15-01-2026, if no file exists for today
cars = csv_storage.get_registered_cars()
# Automatically copies from 14-01-2026 and updates created_at to 15-01-2026
```

### Example 2: Import New Data (CSV/XLSX)
```python
# User uploads new CSV file with updated data
new_data = [
    {"plate_number": "29A-123.45", "owner": "Sơn", ...},  # Existing - kept
    {"plate_number": "55G-999.88", "owner": "Tân", ...},  # New - added
    # Note: 82D-543.21 is not in this list, so it will be deleted
]

stats = csv_storage.import_registered_cars(new_data, date="15-01-2026")
# Returns: {"added": 1, "updated": 0, "deleted": 1, "total": 2, ...}
```

### Example 3: Get Specific Date
```python
# Get registered cars for a specific historical date
cars = csv_storage.get_registered_cars(date="14-01-2026")
```

### Example 4: List Available Dates
```python
dates = csv_storage.get_available_registered_cars_dates()
# Returns: ["15-01-2026", "14-01-2026"]
```

## Frontend Integration Guide

### Fetching Data
```javascript
// Get current day's registered cars
const response = await fetch('/api/cameras/registered_cars');
const cars = await response.json();

// Get specific date
const response = await fetch('/api/cameras/registered_cars?date=14-01-2026');
const cars = await response.json();

// Get available dates
const response = await fetch('/api/cameras/registered_cars/dates');
const { dates } = await response.json();
```

### Importing CSV/XLSX
```javascript
// After parsing uploaded file
const importData = parsedCsvData.map(row => ({
  plate_number: row.plate,
  owner: row.owner,
  model: row.model,
  color: row.color,
  notes: row.notes,
  box_dimensions: row.dimensions,
  standard_volume: row.volume
}));

const response = await fetch('/api/cameras/registered_cars/import', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ cars: importData })
});

const stats = await response.json();
console.log(`Added: ${stats.added}, Updated: ${stats.updated}, Deleted: ${stats.deleted}`);
```

## Business Logic Flow

### Daily Workflow
1. **Start of Day**: 
   - First call to `get_registered_cars()` without date
   - System auto-migrates from previous day
   - Updates `created_at` to today

2. **No New Data**:
   - Existing data from previous day is preserved
   - Date is updated to current day

3. **New Data Import** (CSV/XLSX):
   - User uploads file
   - System compares with existing data
   - Smart merge: add new, update existing, delete missing
   - All rows get current date in `created_at`

### Import Logic Details
```
OLD DATA (existing in database):
- 29A-123.45: Sơn
- 29A-252.67: Sáng
- 82D-543.21: Minh

NEW DATA (from imported file):
- 29A-123.45: Sơn (same)
- 29A-252.67: Sáng (Updated) (data changed)
- 55G-999.88: Tân (new)

RESULT:
- 29A-123.45: Sơn (kept, same ID)
- 29A-252.67: Sáng (Updated) (kept, same ID, data updated)
- 55G-999.88: Tân (added, new ID)
- 82D-543.21: DELETED (not in import)

STATISTICS:
- added: 1 (55G-999.88)
- updated: 1 (29A-252.67)
- deleted: 1 (82D-543.21)
- total: 3
```

## Migration Notes

### From Old System
- Old file: `registered_cars.csv` (no date)
- Can coexist with new system
- Recommend migrating by copying to `registered_cars_14-01-2026.csv`

### Backward Compatibility
- Old code calling `get_registered_cars()` still works
- Returns today's data with auto-migration
- API endpoints support optional date parameter

## Testing

Run the test script to verify functionality:
```bash
uv run python test_registered_cars.py
```

This will demonstrate:
- Reading date-specific files
- Auto-migration logic
- Import with smart merge
- Available dates listing
- Statistics reporting

## Files Modified
- `backend/data_process/csv_storage.py` - Core logic
- `backend/api.py` - API endpoints
- `database/data/history_15_01_2026.csv` - Test data
- `database/data/registered_cars_14-01-2026.csv` - Test data
- `database/data/registered_cars_15-01-2026.csv` - Test data
- `test_registered_cars.py` - Test script

## Summary
✅ Date-based naming format implemented (dd-mm-yyyy)  
✅ Auto-migration to new day  
✅ Smart import logic (add/update/delete)  
✅ Test data created for 14-01 and 15-01-2026  
✅ API endpoints updated with date support  
✅ Import statistics and reporting  
✅ Backward compatible  
