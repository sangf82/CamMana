# CamMana - ONVIF Camera Manager

A modern desktop application for controlling ONVIF-compatible IP cameras with PTZ (Pan-Tilt-Zoom) functionality.

![CamMana Screenshot](https://via.placeholder.com/800x500/0f1419/00d4aa?text=CamMana+Camera+Manager)

## 🏗️ Architecture

```
CamMana/
├── backend/           # Python FastAPI server
│   ├── camera.py      # ONVIF camera manager
│   ├── streamer.py    # RTSP to MJPEG converter
│   └── server.py      # FastAPI endpoints
├── frontend/          # Next.js application
│   └── app/
│       ├── layout.js  # Root layout
│       ├── page.js    # Main page component
│       └── globals.css # Styling
├── app.py             # PyWebView desktop launcher
├── build.py           # Build script for Windows exe
└── main.py            # Legacy Streamlit app
```

## 🚀 Quick Start

### Development Mode

1. **Install Python dependencies:**
   ```bash
   uv sync
   ```

2. **Install frontend dependencies:**
   ```bash
   cd frontend
   npm install
   ```

3. **Start the backend server:**
   ```bash
   uv run python -m backend.server
   ```

4. **Start the frontend (in another terminal):**
   ```bash
   cd frontend
   npm run dev
   ```

5. **Open in browser:** http://localhost:3000

### Desktop App Mode (Development)

Run the PyWebView desktop application:
```bash
# Make sure both backend and frontend are running first
uv run python app.py
```

## 📦 Building Windows Executable

### Option 1: Using the Build Script (Recommended)

```bash
uv run python build.py
```

This will:
1. Build the Next.js frontend to static files
2. Package everything with PyInstaller
3. Create `dist/CamMana.exe`

### Option 2: Manual Build

1. **Build the frontend:**
   ```bash
   cd frontend
   npm run build
   ```

2. **Package with PyInstaller:**
   ```bash
   uv run pyinstaller --name=CamMana --onefile --windowed --add-data="frontend/out;frontend/out" app.py
   ```

3. **Run the executable:**
   ```bash
   dist\CamMana.exe
   ```

## 🎮 Features

- **Live Video Streaming** - MJPEG stream from RTSP source (~30 FPS)
- **PTZ Controls** - Pan, Tilt, Zoom with adjustable speed
- **Image Capture** - Save current frame to disk
- **Modern UI** - Dark theme with smooth animations
- **Desktop App** - Native Windows application via PyWebView
- **Next.js** - Server-side rendering and optimized builds
- **Single Executable** - No installation required

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Connection status |
| `/api/connect` | POST | Connect to camera |
| `/api/disconnect` | POST | Disconnect |
| `/api/stream/start` | POST | Start streaming |
| `/api/stream/stop` | POST | Stop streaming |
| `/api/stream/video` | GET | MJPEG video feed |
| `/api/capture` | POST | Capture current frame |
| `/api/ptz/{direction}` | POST | PTZ movement |

## ⚙️ Camera Configuration

Default settings (configurable in UI):
- **IP:** 192.168.5.159
- **ONVIF Port:** 8899
- **Username:** admin
- **Password:** (empty)

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.12, FastAPI, OpenCV, ONVIF-zeep |
| Frontend | Next.js 16, React 19 |
| Desktop | PyWebView |
| Packaging | PyInstaller |
| Styling | Custom CSS (dark theme) |

## 📝 License

MIT License
