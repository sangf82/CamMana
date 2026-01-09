# API Endpoints Documentation

## Tổng quan
Các API dưới đây phục vụ cho các tác vụ: ước lượng thể tích, nhận diện màu, nhận diện biển số (ALPR), đếm bánh xe. Tất cả endpoint đều nhận ảnh qua HTTP POST (multipart/form-data) và trả về JSON.

**BaseURL:**  https://thpttl12t1--truck-api-fastapi-app.modal.run

---

## 1. Health Check
- **Method:** GET
- **Path:** `/health`
- **Mô tả:** Kiểm tra server còn hoạt động.
- **Response:**
```json
{
  "status": "ok"
}
```

---

## 2. Ước lượng thể tích

- Chưa hoàn thiện, tạm bỏ qua.
- **Method:** POST
- **Path:** `/estimate_volume`
- **Input:**
  - `file`: Ảnh xe tải (image/*)
- **Response:**
```json
{
  "volume": 12.3,
  "unit": "m3"
}
```
- **Lỗi:**
```json
{
  "detail": "Lỗi xử lý ảnh"
}
```

---

## 3. Nhận diện màu
- **Method:** POST
- **Path:** `/detect_colors`
- **Input:**
  - `file`: Ảnh xe (image/*)
- **Response:**
```json
{
    "detections": [
        {
            "bbox": [
                1,
                107,
                464,
                282
            ],
            "confidence": 0.897,
            "class_id": 7,
            "color": "Black"
        },
        {
            "bbox": [
                461,
                195,
                479,
                218
            ],
            "confidence": 0.4378,
            "class_id": 2,
            "color": "Gray"
        }
    ]
}
```
- **Lỗi:**
```json
{
  "detail": "Invalid image"
}
```

---

## 4. Nhận diện biển số (ALPR)
- **Method:** POST
- **Path:** `/alpr`
- **Input:**
  - `file`: Ảnh xe (image/*)
- **Response:**
```json
{
    "plates": [
        "19A79179"
    ],
    "count": 1,
    "raw_results": "[ALPRResult(detection=DetectionResult(label='License Plate', confidence=0.8766680955886841, bounding_box=BoundingBox(x1=1193, y1=539, x2=1638, y2=814)), ocr=OcrResult(text='19A79179', confidence=0.9998746514320374))]"
}
```
- **Lỗi:**
```json
{
  "detail": "Lỗi xử lý ảnh"
}
```

---

## 5. Đếm bánh xe
- **Method:** POST
- **Path:** `/count_wheels`
- **Input:**
  - `file`: Ảnh xe (image/*)
- **Response:**
```json
{
    "wheel_count": 4,
    "detections": [
        {
            "bbox": [
                152,
                223,
                214,
                281
            ],
            "confidence": 0.8851915597915649
        },
        {
            "bbox": [
                309,
                220,
                371,
                279
            ],
            "confidence": 0.8842544555664062
        },
        {
            "bbox": [
                50,
                222,
                116,
                282
            ],
            "confidence": 0.8780447840690613
        },
        {
            "bbox": [
                376,
                219,
                439,
                277
            ],
            "confidence": 0.8748044371604919
        }
    ]
}
```
- **Lỗi:**
```json
{
  "detail": "Invalid image"
}
```

---

## Lưu ý
- Tất cả endpoint trả về JSON.
- Đảm bảo gửi ảnh đúng định dạng (jpg/png).
- Nếu lỗi, response sẽ có trường `detail`.

---
