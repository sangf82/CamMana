import React from "react";
import { GridView, CropFree, PhotoCamera, ControlCamera } from "@mui/icons-material";
import VideoPlayer from "../../../components/features/monitoring/VideoPlayer";
import { toast } from "sonner";

interface Camera {
  id: string | number;
  name: string;
  ip: string;
  location: string;
  location_id?: string;
  status: string;
  type: string;
  tag?: string;
  username?: string;
  password?: string;
  port?: number;
  cam_id?: string;
  brand?: string;
}

interface CameraGridProps {
  viewMode: "focus" | "grid";
  setViewMode: (mode: "focus" | "grid") => void;
  currentGate: string;
  filteredCameras: Camera[];
  isConnecting: (cam: Camera) => boolean;
  getActiveId: (cam: Camera) => string | undefined;
  getStreamUrl: (cam: Camera) => string | undefined;
  mainCamera: Camera | undefined;
  streamInfo: { resolution: string; fps: number } | null;
  addLog: (message: string, type: "success" | "info" | "error" | "warning") => void;
  onPtzClick?: () => void;
  isPtzActive?: boolean;
}


export default function CameraGrid({
  viewMode,
  setViewMode,
  currentGate,
  filteredCameras,
  isConnecting,
  getActiveId,
  getStreamUrl,
  mainCamera,
  streamInfo,
  addLog,
  onPtzClick,
  isPtzActive,
}: CameraGridProps) {
  return (
    <div className="flex-1 flex flex-col gap-1">
      {/* Controls Bar */}
      <div className="flex items-center justify-between bg-card border border-border px-2 py-1 rounded-lg">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-primary px-1 uppercase tracking-wide">
            {currentGate ? `GIÁM SÁT: ${currentGate}` : "CHỌN CỔNG ĐỂ XEM"}
          </span>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => setViewMode("focus")}
            className={`p-1.5 rounded transition-colors ${
              viewMode === "focus"
                ? "bg-accent text-white"
                : "text-muted-foreground hover:bg-muted"
            }`}
            title="Chế độ Tập trung"
          >
            <CropFree />
          </button>
          <button
            onClick={() => setViewMode("grid")}
            className={`p-1.5 rounded transition-colors ${
              viewMode === "grid"
                ? "bg-accent text-white"
                : "text-muted-foreground hover:bg-muted"
            }`}
            title="Chế độ Lưới"
          >
            <GridView />
          </button>
        </div>
      </div>

      {/* Videos */}
      <div
        className={`flex-1 min-h-0 bg-transparent rounded-lg overflow-hidden ${
          viewMode === "grid"
            ? "grid grid-cols-2 grid-rows-2 gap-1"
            : "flex gap-1"
        }`}
      >
        {viewMode === "grid" ? (
          <>
            {Array.from({ length: 4 }).map((_, idx) => {
              const cam = filteredCameras[idx];
              return (
                <div
                  key={cam?.id || `empty-${idx}`}
                  className="relative bg-black rounded-lg border border-border overflow-hidden"
                >
                  {cam ? (
                    <>
                      {isConnecting(cam) && (
                        <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-black/80">
                          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mb-2" />
                          <span className="text-xs text-muted-foreground">
                            Đang kết nối...
                          </span>
                        </div>
                      )}
                      <VideoPlayer
                        label={cam.name}
                        camCode={cam.cam_id}
                        activeId={getActiveId(cam)}
                        className="h-full"
                        src={getStreamUrl(cam)}
                      />
                    </>
                  ) : (
                    <div className="w-full h-full flex flex-col items-center justify-center text-muted-foreground">
                      <span className="text-xs opacity-50">Slot {idx + 1}</span>
                    </div>
                  )}
                </div>
              );
            })}
          </>
        ) : !currentGate ? (
          <div className="w-full h-full flex flex-col items-center justify-center bg-black/50 border border-dashed border-border rounded-lg text-muted-foreground">
            <p>Vui lòng chọn Cổng từ Menu bên trái</p>
          </div>
        ) : filteredCameras.length === 0 ? (
          <div className="w-full h-full flex flex-col items-center justify-center bg-black/50 border border-dashed border-border rounded-lg text-muted-foreground">
            <PhotoCamera className="text-4xl mb-2 opacity-20" />
            <p>Chưa có camera tại {currentGate}</p>
          </div>
        ) : (
          <div className="h-full w-full flex flex-col overflow-hidden">
            <div className="w-full flex-1 min-h-0 relative bg-black rounded-lg overflow-hidden border border-border">
              {mainCamera && isConnecting(mainCamera) && (
                <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-black">
                  <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin mb-4" />
                  <span className="text-sm text-muted-foreground">
                    Đang kết nối {mainCamera.name}...
                  </span>
                </div>
              )}
              <VideoPlayer
                label={mainCamera?.name || "Camera Chính"}
                camCode={mainCamera?.cam_id}
                activeId={mainCamera ? getActiveId(mainCamera) : undefined}
                src={mainCamera ? getStreamUrl(mainCamera) : undefined}
              />
            </div>

            {mainCamera && (
              <div className="shrink-0 mt-1 bg-card border border-border rounded-lg px-3 py-2 flex items-center justify-between w-full">
                <div className="flex items-center gap-4">
                  <div className="flex flex-col">
                    <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
                      Mã Camera
                    </span>
                    <span className="text-sm font-bold text-primary">
                      {mainCamera.cam_id || "N/A"}
                    </span>
                  </div>
                  <div className="w-px h-6 bg-border" />
                  <div className="flex flex-col">
                    <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
                      Độ phân giải
                    </span>
                    <span className="text-sm font-medium text-foreground font-mono">
                      {streamInfo?.resolution || "N/A"}
                    </span>
                  </div>
                  <div className="w-px h-6 bg-border" />
                  <div className="flex flex-col">
                    <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
                      FPS
                    </span>
                    <span className="text-sm font-medium text-foreground font-mono">
                      {streamInfo?.fps || 0}
                    </span>
                  </div>
                  <div className="w-px h-6 bg-border" />
                  <div className="flex flex-col">
                    <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
                      Chức năng
                    </span>
                    <div className="flex gap-1 mt-0.5">
                      {mainCamera.type ? (
                        mainCamera.type.split(",").map((fid) => (
                          <span
                            key={fid}
                            className="px-1 py-0.5 bg-primary/10 text-primary border border-primary/20 rounded-[2px] text-[8px] font-bold uppercase"
                          >
                            {fid.replace("_detect", "").toUpperCase()}
                          </span>
                        ))
                      ) : (
                        <span className="text-sm font-medium text-foreground">
                          Cơ bản
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="w-px h-6 bg-border" />
                  <div className="flex flex-col">
                    <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
                      Thương hiệu
                    </span>
                    <span className="text-sm font-medium text-foreground">
                      {mainCamera.brand || "N/A"}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {/* PTZ Button */}
                  <button
                    onClick={onPtzClick}
                    className={`flex items-center gap-2 px-4 py-2 font-semibold rounded-md transition-colors ${
                      isPtzActive 
                        ? "bg-blue-700 text-white ring-2 ring-blue-400" 
                        : "bg-blue-600 text-white hover:bg-blue-700"
                    }`}
                    title="Điều khiển PTZ"
                  >
                    <ControlCamera fontSize="small" />
                    PTZ
                  </button>

                  {/* Capture Button */}
                  <button
                    onClick={async () => {
                      const activeId = getActiveId(mainCamera);
                      if (!activeId) return;
                      try {
                        const res = await fetch(
                          `/api/cameras/${activeId}/capture`,
                          { method: "POST" }
                        );
                        if (res.ok) {
                          const data = await res.json();
                          if (data.success) {
                            toast.success(`Đã chụp ảnh: ${data.filename}`);
                            addLog(`📸 Chụp ảnh: ${data.filename}`, "success");
                          } else {
                            toast.error(`Lỗi: ${data.error}`);
                          }
                        }
                      } catch (e) {
                        toast.error("Lỗi khi chụp ảnh");
                      }
                    }}
                    className="flex items-center gap-2 px-4 py-2 bg-primary text-black font-semibold rounded-md hover:bg-primary/90 transition-colors"
                  >
                    <PhotoCamera fontSize="small" />
                    Chụp ảnh
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
