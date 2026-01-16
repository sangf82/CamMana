# Location Tags - Quick Reference Card

## 📋 Quick Tag Reference

| Tag | Purpose | Models | Capture | Use Case |
|-----|---------|--------|---------|----------|
| **check-in** | Entry gate | car → plate → color → wheels | continuous | Detect incoming vehicles |
| **check-out** | Exit gate | car → plate → color → wheels | verify_and_match | Match & update exit status |
| **volume-estimate** | Weighing station | truck → dimensions → volume → plate | multi_angle | Calculate cargo volume |
| **general** | Monitoring | car → plate | on_motion | Basic surveillance |

## 🔧 Common Code Snippets

### Get Detection Config
```python
from backend.detection import get_detection_config

config = get_detection_config("check-in")
# Returns: DetectionConfig with sequence, strategy, tolerance
```

### Get Camera Group by Tag
```python
from backend.detection import group_cameras_by_tag
from backend.data_process import get_cameras, get_locations

grouped = group_cameras_by_tag(get_cameras(), get_locations())
checkin_cameras = grouped.get('check-in', [])
```

### Check Volume Tolerance
```python
from backend.detection import get_volume_tolerance

tolerance = get_volume_tolerance("volume-estimate")  # Returns 0.05 (5%)

if measured_volume < standard * (1 - tolerance):
    status = "UNDER_LOADED"
elif measured_volume > standard * (1 + tolerance):
    status = "OVER_LOADED"
else:
    status = "NORMAL"
```

## 🌐 API Quick Reference

```bash
# Get all locations with tags
GET /api/cameras/locations

# Save location with tag
POST /api/cameras/locations
{
  "name": "Gate A",
  "tag": "check-in",
  "description": "Main entrance"
}

# Get cameras grouped by tag
GET /api/cameras/locations/grouped

# Get config for a tag
GET /api/cameras/locations/tags/check-in/config

# Get all tag configs
GET /api/cameras/locations/tags/all/configs
```

## 📊 Frontend Components

### LocationItem Interface
```typescript
interface LocationItem {
    id: string | number
    name: string
    tag?: string  // "check-in" | "check-out" | "volume-estimate" | "general"
    description?: string
}
```

### Tag Badge Component
```tsx
<span className="px-2 py-0.5 bg-primary/10 text-primary rounded">
    {tag === 'check-in' ? 'Check-in' : 
     tag === 'check-out' ? 'Check-out' : 
     tag === 'volume-estimate' ? 'Volume' : 
     'General'}
</span>
```

## 🗂️ File Structure

```
CamMana/
├── backend/
│   ├── detection/
│   │   ├── __init__.py          ← Exports
│   │   └── detection_config.py  ← Main config
│   ├── data_process/
│   │   └── _common.py           ← Updated headers
│   └── api/
│       └── config.py            ← New endpoints
├── database/csv_data/
│   └── locations.csv            ← Updated with tags
├── frontend/app/(dashboard)/
│   └── cameras/
│       └── page.tsx             ← Enhanced UI
├── docs/
│   ├── LOCATION_TAGS.md         ← Full guide
│   ├── IMPLEMENTATION_SUMMARY.md ← Summary
│   └── ARCHITECTURE.md          ← Visual diagram
└── tests/
    └── test_location_tags.py    ← Test script
```

## ✅ Testing Checklist

- [ ] Run test: `uv run python tests/test_location_tags.py`
- [ ] Open cameras page and add new location with tag
- [ ] Edit existing location's tag
- [ ] Test API: `GET /api/cameras/locations/grouped`
- [ ] Verify CSV has tag and description columns
- [ ] Check detection config in Python REPL

## 🔍 Troubleshooting

**Tag not showing in UI?**
→ Check if location has `tag` field in database

**Detection config not found?**
→ Verify tag name matches enum values (check-in, check-out, volume-estimate, general)

**Cameras not grouping correctly?**
→ Ensure cameras have `location_id` that matches a location's `id`

**Volume tolerance not working?**
→ Only `volume-estimate` tag has tolerance, others return `None`

## 📚 Related Documentation

- **Full Guide**: `docs/LOCATION_TAGS.md`
- **Architecture**: `docs/ARCHITECTURE.md`
- **Implementation**: `docs/IMPLEMENTATION_SUMMARY.md`

## 💡 Next Steps

1. Integrate with detection service
2. Implement capture strategies
3. Add volume validation logic
4. Create history matching for check-out
5. Build tag-based dashboard

---

**Last Updated**: 2026-01-15
**Version**: 1.0
