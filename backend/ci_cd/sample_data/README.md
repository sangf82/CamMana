# Sample Data for CI/CD Testing

This folder contains sample data that mirrors the structure of the `database/` folder.
It is used for CI/CD testing purposes only.

## Structure

```
sample_data/
├── backgrounds/           # Background images for volume detection
├── calibration/           # Camera calibration files
│   ├── calib_side.json
│   └── calib_topdown.json
├── captured_img/          # Temporary captured images
├── car_history/           # Car check-in/out history with images
│   └── 27-01-2026/
│       └── test-car-001_08-00-00/
├── csv_data/              # CSV database files
│   ├── cameras.csv
│   ├── camtypes.csv
│   ├── history_27-01-2026.csv
│   ├── locations.csv
│   ├── registered_cars_27-01-2026.csv
│   └── user.csv
├── logs/                  # Application logs
├── report/                # Daily reports
│   └── report_27-01-2026.json
└── sync_config.json       # Sync configuration
```

## Usage

This sample data can be used in tests by setting the `CAMMANA_DATA_DIR` environment variable
to point to this folder, or by copying specific files to the test environment.

## Test Images

For API testing, place test images in:
- `car_history/*/` - Car images for plate, color, wheel detection
- `backgrounds/` - Background images for volume detection

Note: Actual test images are not included in git. Add your own test images or copy from the real database.
