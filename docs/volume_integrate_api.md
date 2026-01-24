# Cargo Volume Estimation API Documentation

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
