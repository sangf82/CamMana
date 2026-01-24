# Cargo Volume Estimation API Documentation

## Overview & Logic Flow

This API estimates cargo volume using two camera views:

- **Side view**: Used to extract the height profile of the cargo along its length.
- **Top-down view**: Used to extract the width profile of the cargo along the same length.

**Processing pipeline:**
1. **Upload images and calibration files:**
  - `image`: Side view image of the cargo.
  - `img_bg`: Top-down background image (no cargo/truck).
  - `img_fg`: Top-down foreground image (with cargo/truck).
  - `calib_side`: Calibration file for the side view camera (JSON).
  - `calib_topdown`: Calibration file for the top-down camera (JSON).
2. **Height profile extraction:**
  - The side view image and its calibration are used to detect the cargo region and extract a height profile $h(x)$ (height at each position along the cargo length).
3. **Width profile extraction:**
  - The top-down images (background and foreground) and their calibration are used to extract a width profile $w(x)$ (width at each position along the cargo length).
4. **Volume integration:**
  - The API computes the volume by integrating $h(x) \times w(x)$ along the cargo length using numerical methods.

**Calibration files:**
- Each camera (side and top-down) must have its own calibration file (`calib_side.json`, `calib_topdown.json`).
- Calibration files must be in the following format:
  - `K`: 3x3 intrinsic matrix
  - `dist`: Distortion coefficients
  - `rvec`: Rotation vector (extrinsic)
  - `tvec`: Translation vector (extrinsic)
  - `floor_z`: Z coordinate of the ground plane (usually 0.0)
- Example provided below.

**Note:** Calibration must be accurate and correspond to the correct camera and physical setup. Do not swap or reuse calibration files between different cameras/views.

This API provides endpoints for estimating cargo volume from images using computer vision pipelines. It is designed for deployment on Modal or any FastAPI-compatible server.


## Endpoints


###  `/estimate_volume`
Estimate cargo volume directly from images and calibration files (no manual profile upload).

- **Method:** POST
- **Consumes:** multipart/form-data
- **Parameters:**
    - `image`: (file, required) Side view image (for height profile)
    - `calib_side`: (file, required) Calibration file for side view (JSON)
    - `img_bg`: (file, required) Top-down background image (no truck)
    - `img_fg`: (file, required) Top-down foreground image (with truck)
    - `calib_topdown`: (file, required) Calibration file for top-down view (JSON)
    - `dx`: (float, optional, default=0.05) Integration step size in meters
    - `threshold`: (int, optional, default=30) Threshold for background subtraction
    - `step_px`: (int, optional, default=5) Step size in pixels for sampling columns
- **Returns:**
    - `{ "volume": <float> }` (volume in cubic meters)
- **Notes:**
    - This endpoint will automatically extract both height and width profiles from the provided images and their respective calibration files, then compute the volume. No need to upload profile files.

---

## Example Usage

### Using `curl`

#### Extract width profile
```
curl -X POST "http://localhost:8000/extract_width_profile" \
  -F "img_bg=@/path/to/bg.jpg" \
  -F "img_fg=@/path/to/fg.jpg" \
  -F "calib=@/path/to/calib.json" \
  -F "threshold=30" \
  -F "step_px=5"
```

#### Estimate volume
```
curl -X POST "http://localhost:8000/estimate_volume" \
  -F "image=@/path/to/side.jpg" \
  -F "calib_side=@/path/to/calib_side.json" \
  -F "img_bg=@/path/to/bg.jpg" \
  -F "img_fg=@/path/to/fg.jpg" \
  -F "calib_topdown=@/path/to/calib_topdown.json" \
  -F "dx=0.05"
```

## Data Formats

### Calibration File (JSON)
```
{
  "K": [[fx, 0, cx], [0, fy, cy], [0, 0, 1]],
  "dist": [k1, k2, p1, p2, k3],
  "rvec": [r1, r2, r3],
  "tvec": [t1, t2, t3],
  "floor_z": 0.0
}
```



## OpenAPI/Swagger UI
Visit `/docs` on your deployed server to interact with the API using a web interface.

## Notes
- All endpoints return JSON.
- For best results, ensure calibration files and images are correct and correspond to the same camera setup.
