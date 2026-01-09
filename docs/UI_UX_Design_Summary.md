# UI/UX Design Summary - CamMana

This document serves as a comprehensive reference for the UI/UX design system implemented in the CamMana application.

## 1. Design Philosophy
*   **Aesthetic**: Minimalist, Industrial, Professional.
*   **Domain Context**: Construction & Building Management (reflected in icons and color scheme).
*   **Theme Strategy**: High-contrast Dual Theme (Dark Mode Default / Light Mode Supported).
*   **Typography**: Clean sans-serif system font stack (Inter/System UI).

## 2. Color System
The application uses CSS variables to handle theming dynamically.

| Semantic Role | Dark Mode Value | Light Mode Value | Usage |
| :--- | :--- | :--- | :--- |
| **Primary Background** | `#121212` | `#ffffff` | Main window, inputs |
| **Secondary Background** | `#1e1e1e` | `#f4f4f5` | Sidebar, Cards |
| **Tertiary Background** | `#2d2d2d` | `#e4e4e7` | Table headers, Hover states |
| **Accent (Main)** | `#eab308` | `#EAB308` | Primary Actions, Active States, Highlights |
| **Text Primary** | `#fafafa` | `#18181b` | Main Content |
| **Text Secondary** | `#a1a1aa` | `#52525b` | Labels, Meta info |
| **Success** | `#22c55e` | `#16a34a` | "In" Status, Verified Matches |
| **Danger** | `#ef4444` | `#dc2626` | "Disconnected", Errors |

## 3. UI Layout & Navigation

### Sidebar
*   **Header**: Displays "CamMana" with a **Construction** icon (Hammer/Wrench), anchoring the industry context.
*   **Navigation Menu**:
    *   Vertical list of views ("Xem Camera", "Lịch trình").
    *   **Active State**: Highlighted with Sidebar Tertiary background and Accent color text/icon.
*   **Theme Toggle**:
    *   Custom-built toggle switch.
    *   Visual indicators: Sun Icon (Light) / Moon Icon (Dark).
    *   Yellow accent color when active (Light mode).

### Icons
*   **Library**: `Material UI Icons` (@mui/icons-material) used exclusively for consistency.
*   **Sizing**: Uniform `fontSize="small"` for UI elements, larger for specific controls.

## 4. Key Views & Components

### A. Camera Management (Live View)
*   **Camera Grid**:
    *   Card-based layout.
    *   Status Badge: Green (Connected) / Red (Disconnected).
    *   **Overlay Controls**: "Stop" and "Capture" buttons appear over the video feed on hover.
    *   **Video Overlay Style**: Uses `.btn-overlay` class—semi-transparent backdrop that inverts based on theme (Dark/Light) to ensure visibility against video content.
*   **PTZ Controls (Sidebar)**:
    *   Directional Pad: Up/Down/Left/Right arrows.
    *   Center Action: Capture button.
    *   Zoom Controls: Dedicated "+ Zoom" and "- Zoom" buttons.
    *   Speed Control: Range slider with numeric indicator.

### B. Schedule Dashboard
*   **Data Table**:
    *   **Headers**: Sticky positioning, Vietnamese localized texts.
    *   **Row Highlighting**:
        *   **Matched**: Green tint background + Green left border.
        *   **Verified**: Dark/Light grey tint + Grey left border.
    *   **Status Column**:
        *   **Đã vào (Checked In)**: Green text + `ArrowDownward` icon.
        *   **Đã ra (Checked Out)**: Accent text + `ArrowUpward` icon.
        *   **Chưa đến (Scheduled)**: Muted text + `HourglassEmpty` icon.
*   **Action Toolbar**:
    *   **Refresh**: Reloads data from server.
    *   **Import Excel**: Hidden file input triggered by a styled button (`FileUpload` icon).
*   **Stats Cards**: Top summary cards showing "Total Vehicles" and "Checked-in Count".

## 5. User Workflows

### Vehicle Verification Flow
1.  **Selection**: User selects a camera from the grid.
2.  **Action**: User clicks **"🔍 Kiểm tra xe"** in the sidebar.
3.  **Process**: 
    - App captures snapshot.
    - Sends to ALPR API.
    - Matches license plate against Schedule Data.
4.  **Feedback**:
    - **Success**: Green Toast notification + Auto-switch to Dashboard + Highlight matched row.
    - **Failure**: Red/Yellow Toast notification (No plate found / Not in schedule).

### Data Management Flow
1.  **Upload**: User clicks "Nhập Excel".
2.  **Processing**: File uploaded to backend -> Backend normalizes columns (Robust mapping) -> File Saved.
3.  **Update**: Dashboard auto-refreshes to show new data.
