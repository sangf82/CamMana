import { Close, PhotoCamera, Videocam } from "@mui/icons-material";
import { useState, useEffect } from "react";

interface DetectionResult {
  plate_number: string | null;
  color: string | null;
  wheel_count: number;
  confidence: number;
  matched: boolean;
  registered_info?: {
    owner: string;
    model: string;
    standard_volume: string;
  };
  snapshot_url?: string;
  folder_path?: string;
  uuid?: string;
  volume?: number | null;
}

interface Camera {
  id: string;
  name: string;
  type?: string;
  location?: string;
}

// Map camera ID to image URL
interface CameraImages {
  [cameraId: string]: string | null;
}

interface EvidenceModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentDetection: DetectionResult | null;
  // Dynamic camera list from current location
  cameras: Camera[];
  // Map of camera ID to captured image URL
  cameraImages: CameraImages;
  snapshotUrl: string | null;
}

export default function EvidenceModal({
  isOpen,
  onClose,
  currentDetection,
  cameras,
  cameraImages,
  snapshotUrl,
}: EvidenceModalProps) {
  const [activeTabIndex, setActiveTabIndex] = useState(0);

  // Reset tab when modal opens or cameras change
  useEffect(() => {
    if (isOpen) {
      setActiveTabIndex(0);
    }
  }, [isOpen, cameras]);

  if (!isOpen) return null;

  // Use cameras from props (filtered by current location)
  const displayCameras = cameras.length > 0 ? cameras : [];
  const activeCamera = displayCameras[activeTabIndex];
  
  // Get image for current active camera
  const getActiveImage = () => {
    if (!activeCamera) return snapshotUrl;
    return cameraImages[activeCamera.id] || (activeTabIndex === 0 ? snapshotUrl : null);
  };

  const activeImage = getActiveImage();

  return (
    <div className="fixed inset-0 bg-black/80 z-[9999] pointer-events-auto flex items-center justify-center p-4">
      <div className="bg-card border border-border rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-3">
            <PhotoCamera className="text-[#f59e0b]" />
            <h3 className="text-lg font-bold">Bằng chứng</h3>
            {currentDetection?.plate_number && (
              <span className="px-2 py-0.5 bg-primary/20 text-[#f59e0b] rounded text-sm font-mono">
                {currentDetection.plate_number}
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-muted rounded-full transition-colors"
          >
            <Close />
          </button>
        </div>

        {/* Dynamic Camera Tabs */}
        <div className="flex border-b border-border">
          {displayCameras.map((cam, index) => (
            <button
              key={cam.id}
              onClick={() => setActiveTabIndex(index)}
              className={`flex-1 py-3 px-4 text-sm font-medium transition-colors flex items-center justify-center gap-2 ${
                activeTabIndex === index
                  ? "text-[#f59e0b] border-b-2 border-[#f59e0b] bg-[#f59e0b]/10"
                  : "text-muted-foreground hover:bg-muted/50"
              }`}
            >
              <Videocam fontSize="small" /> {cam.name}
            </button>
          ))}
          {displayCameras.length === 0 && (
            <div className="flex-1 py-3 px-4 text-sm text-muted-foreground text-center">
              Không có camera
            </div>
          )}
        </div>

        {/* Image Content */}
        <div className="p-4 bg-black min-h-[400px] flex items-center justify-center">
          {activeImage ? (
            <img
              src={activeImage}
              alt={activeCamera?.name || "Camera"}
              className="max-w-full max-h-[60vh] object-contain rounded shadow-lg"
            />
          ) : (
            <div className="text-muted-foreground text-center">
              <PhotoCamera className="w-16 h-16 mx-auto mb-2 opacity-30" />
              <p>Chưa có ảnh {activeCamera?.name || "camera"}</p>
            </div>
          )}
        </div>

        {/* Detection Info Footer */}
        {currentDetection && (
          <div className="p-4 border-t border-border bg-muted/30">
            <div className="grid grid-cols-4 gap-4 text-center">
              <div>
                <span className="block text-xs text-muted-foreground">
                  Biển số
                </span>
                <span className="font-mono font-bold">
                  {currentDetection.plate_number || "---"}
                </span>
              </div>
              <div>
                <span className="block text-xs text-muted-foreground">
                  Màu xe
                </span>
                <span className="font-medium">
                  {currentDetection.color || "---"}
                </span>
              </div>
              <div>
                <span className="block text-xs text-muted-foreground">
                  Số bánh
                </span>
                <span className="font-medium">
                  {currentDetection.wheel_count || "---"}
                </span>
              </div>
              <div>
                <span className="block text-xs text-muted-foreground">
                  Trạng thái
                </span>
                <span
                  className={`font-medium ${
                    currentDetection.matched
                      ? "text-green-400"
                      : "text-amber-400"
                  }`}
                >
                  {currentDetection.matched ? "Khớp ĐK" : "Xe lạ"}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
