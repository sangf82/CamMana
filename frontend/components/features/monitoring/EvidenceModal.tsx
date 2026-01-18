import React from "react";
import { Close, PhotoCamera } from "@mui/icons-material";

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
}

interface EvidenceModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentDetection: DetectionResult | null;
  capturedImages: { front?: string; side?: string };
  snapshotUrl: string | null;
  activeTab: "front" | "side";
  setActiveTab: (tab: "front" | "side") => void;
}

export default function EvidenceModal({
  isOpen,
  onClose,
  currentDetection,
  capturedImages,
  snapshotUrl,
  activeTab,
  setActiveTab,
}: EvidenceModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 z-[9999] pointer-events-auto flex items-center justify-center p-4">
      <div className="bg-card border border-border rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-3">
            <PhotoCamera className="text-primary" />
            <h3 className="text-lg font-bold">Bằng chứng</h3>
            {currentDetection?.plate_number && (
              <span className="px-2 py-0.5 bg-primary/20 text-primary rounded text-sm font-mono">
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

        {/* Tabs */}
        <div className="flex border-b border-border">
          <button
            onClick={() => setActiveTab("front")}
            className={`flex-1 py-3 px-4 text-sm font-medium transition-colors ${
              activeTab === "front"
                ? "text-primary border-b-2 border-primary bg-primary/10"
                : "text-muted-foreground hover:bg-muted/50"
            }`}
          >
            📷 Camera Trước (Biển số)
          </button>
          <button
            onClick={() => setActiveTab("side")}
            className={`flex-1 py-3 px-4 text-sm font-medium transition-colors ${
              activeTab === "side"
                ? "text-primary border-b-2 border-primary bg-primary/10"
                : "text-muted-foreground hover:bg-muted/50"
            }`}
          >
            📷 Camera Hông (Màu/Bánh)
          </button>
        </div>

        {/* Image Content */}
        <div className="p-4 bg-black min-h-[400px] flex items-center justify-center">
          {activeTab === "front" ? (
            capturedImages.front || snapshotUrl ? (
              <img
                src={capturedImages.front || snapshotUrl || ""}
                alt="Front camera"
                className="max-w-full max-h-[60vh] object-contain rounded"
              />
            ) : (
              <div className="text-muted-foreground text-center">
                <PhotoCamera className="w-16 h-16 mx-auto mb-2 opacity-50" />
                <p>Chưa có ảnh camera trước</p>
              </div>
            )
          ) : capturedImages.side ? (
            <img
              src={capturedImages.side}
              alt="Side camera"
              className="max-w-full max-h-[60vh] object-contain rounded"
            />
          ) : (
            <div className="text-muted-foreground text-center">
              <PhotoCamera className="w-16 h-16 mx-auto mb-2 opacity-50" />
              <p>Chưa có ảnh camera hông</p>
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
