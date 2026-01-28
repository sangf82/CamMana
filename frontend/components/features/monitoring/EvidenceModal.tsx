import { X, Camera, Video } from "lucide-react";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";

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
    <div className="fixed inset-0 bg-black/80 z-[9999] pointer-events-auto flex items-center justify-center p-4 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-card border border-border rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col animate-in zoom-in-95 duration-300">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border bg-muted/20">
          <div className="flex items-center gap-3">
            <Camera className="w-5 h-5 text-amber-500" />
            <h3 className="text-lg font-bold">Bằng chứng</h3>
            {currentDetection?.plate_number && (
              <span className="px-2 py-0.5 bg-primary/20 text-amber-500 border border-primary/20 rounded text-sm font-mono font-bold tracking-wider">
                {currentDetection.plate_number}
              </span>
            )}
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="rounded-full h-8 w-8 hover:bg-destructive/10 hover:text-destructive transition-colors"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>

        {/* Dynamic Camera Tabs */}
        <div className="flex border-b border-border bg-muted/10">
          {displayCameras.map((cam, index) => (
            <button
              key={cam.id}
              onClick={() => setActiveTabIndex(index)}
              className={`flex-1 py-3 px-4 text-sm font-medium transition-all flex items-center justify-center gap-2 border-b-2 ${
                activeTabIndex === index
                  ? "text-amber-500 border-amber-500 bg-amber-500/10"
                  : "text-muted-foreground border-transparent hover:bg-muted/50 hover:text-foreground"
              }`}
            >
              <Video className="w-4 h-4" /> {cam.name}
            </button>
          ))}
          {displayCameras.length === 0 && (
            <div className="flex-1 py-3 px-4 text-sm text-muted-foreground text-center">
              Không có camera
            </div>
          )}
        </div>

        {/* Image Content */}
        <div className="p-4 bg-black/95 flex-1 min-h-[400px] flex items-center justify-center relative overflow-hidden group">
          {activeImage ? (
            <img
              src={activeImage}
              alt={activeCamera?.name || "Camera"}
              className="max-w-full max-h-[60vh] object-contain rounded shadow-lg transition-transform duration-300 group-hover:scale-[1.01]"
            />
          ) : (
            <div className="text-muted-foreground text-center flex flex-col items-center">
              <Camera className="w-16 h-16 mb-4 opacity-20" />
              <p className="opacity-60">Chưa có ảnh {activeCamera?.name || "camera"}</p>
            </div>
          )}
        </div>

        {/* Detection Info Footer */}
        {currentDetection && (
          <div className="p-4 border-t border-border bg-muted/30">
            <div className="grid grid-cols-4 gap-4 text-center divide-x divide-border/50">
              <div className="px-2">
                <span className="block text-xs text-muted-foreground uppercase tracking-wider mb-1">
                  Biển số
                </span>
                <span className="font-mono font-bold text-lg">
                  {currentDetection.plate_number || "---"}
                </span>
              </div>
              <div className="px-2">
                <span className="block text-xs text-muted-foreground uppercase tracking-wider mb-1">
                  Màu xe
                </span>
                <span className="font-medium">
                  {currentDetection.color || "---"}
                </span>
              </div>
              <div className="px-2">
                <span className="block text-xs text-muted-foreground uppercase tracking-wider mb-1">
                  Số bánh
                </span>
                <span className="font-medium">
                  {currentDetection.wheel_count || "---"}
                </span>
              </div>
              <div className="px-2">
                <span className="block text-xs text-muted-foreground uppercase tracking-wider mb-1">
                  Trạng thái
                </span>
                <span
                  className={`font-bold ${
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
