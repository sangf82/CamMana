import React from "react";
import { GridView, CropFree, PhotoCamera, ControlCamera } from "@mui/icons-material";
import VideoPlayer from "../../../components/features/monitoring/VideoPlayer";
import { toast } from "sonner";
import { StreamingLoader } from "@/components/ui/loading-spinner";

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
          <span className="text-xs font-bold text-[#f59e0b] px-1 uppercase tracking-wide">
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
            <CropFree className="text-[#f59e0b]" />
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
            <GridView className="text-[#f59e0b]" />
          </button>
        </div>
      </div>

      {/* Videos */}
      <div
        className={`flex-1 min-h-0 bg-zinc-950 rounded-lg overflow-hidden p-1 ${
          viewMode === "grid"
            ? "grid grid-cols-2 grid-rows-2 gap-2"
            : "flex gap-2"
        }`}
      >
        {viewMode === "grid" ? (
          <>
            {Array.from({ length: 4 }).map((_, idx) => {
              const cam = filteredCameras[idx];
              return (
                <div
                  key={cam?.id || `empty-${idx}`}
                  className={`relative bg-zinc-900 rounded-xl border-2 transition-all duration-300 overflow-hidden shadow-inner ${
                    cam ? "border-border/40 hover:border-[#f59e0b]/50 hover:shadow-[#f59e0b]/5" : "border-dashed border-border/20"
                  }`}
                >
                  {cam ? (
                    <>
                      {isConnecting(cam) && (
                        <StreamingLoader message="Đang kết nối..." />
                      )}
                      <VideoPlayer
                        label={cam.name}
                        camCode={cam.cam_id}
                        activeId={getActiveId(cam)}
                        className="w-full h-full"
                        src={getStreamUrl(cam)}
                      />
                    </>
                  ) : (
                    <div className="w-full h-full flex flex-col items-center justify-center text-muted-foreground/30">
                      <PhotoCamera className="mb-2 opacity-10" fontSize="large" />
                      <span className="text-[10px] font-medium uppercase tracking-widest">Trống {idx + 1}</span>
                    </div>
                  )}
                </div>
              );
            })}
          </>
        ) : !currentGate ? (
          <div className="w-full h-full flex flex-col items-center justify-center bg-zinc-900/50 border-2 border-dashed border-border/20 rounded-xl text-muted-foreground/50">
            <p className="text-sm font-medium">Vui lòng chọn Cổng để bắt đầu giám sát</p>
          </div>
        ) : filteredCameras.length === 0 ? (
          <div className="w-full h-full flex flex-col items-center justify-center bg-zinc-900/50 border-2 border-dashed border-border/20 rounded-xl text-muted-foreground/50">
            <PhotoCamera className="text-5xl mb-4 opacity-10" />
            <p className="text-sm font-medium uppercase tracking-wider">Chưa có camera tại {currentGate}</p>
          </div>
        ) : (
          <div className="h-full w-full flex flex-col overflow-hidden gap-2">
            <div className="w-full flex-1 min-h-0 relative bg-black rounded-xl overflow-hidden border-2 border-border/40 shadow-2xl">
              {mainCamera && isConnecting(mainCamera) && (
                <StreamingLoader message={`Đang kết nối ${mainCamera.name}...`} />
              )}
              <VideoPlayer
                label={mainCamera?.name || "Camera Chính"}
                camCode={mainCamera?.cam_id}
                activeId={mainCamera ? getActiveId(mainCamera) : undefined}
                src={mainCamera ? getStreamUrl(mainCamera) : undefined}
                className="w-full h-full"
              />
            </div>

            {mainCamera && (
              <div className="shrink-0 bg-card/80 backdrop-blur-md border border-border/50 rounded-xl px-4 py-3 flex items-center justify-between w-full shadow-lg">
                <div className="flex items-center gap-6 overflow-x-auto no-scrollbar">
                  <div className="flex flex-col min-w-[120px]">
                    <span className="text-[9px] text-muted-foreground uppercase font-bold tracking-[0.15em] mb-1">
                      Camera
                    </span>
                    <span className="text-sm font-black text-[#f59e0b] truncate" title={mainCamera.name}>
                      {mainCamera.name || "N/A"}
                    </span>
                  </div>
                  <div className="w-px h-8 bg-border/50" />
                  <div className="flex flex-col">
                    <span className="text-[9px] text-muted-foreground uppercase font-bold tracking-[0.15em] mb-1">
                      Resolution
                    </span>
                    <span className="text-sm font-bold text-foreground font-mono">
                      {streamInfo?.resolution || "---"}
                    </span>
                  </div>
                  <div className="w-px h-8 bg-border/50" />
                  <div className="flex flex-col">
                    <span className="text-[9px] text-muted-foreground uppercase font-bold tracking-[0.15em] mb-1">
                      FPS
                    </span>
                    <span className="text-sm font-bold text-foreground font-mono">
                      {streamInfo?.fps || 0}
                    </span>
                  </div>
                  <div className="w-px h-8 bg-border/50" />
                  <div className="flex flex-col">
                    <span className="text-[9px] text-muted-foreground uppercase font-bold tracking-[0.15em] mb-1">
                      Tính năng
                    </span>
                    <div className="flex gap-1.5 mt-0.5">
                      {mainCamera.type ? (
                        mainCamera.type.split(",").map((fid) => (
                          <span
                            key={fid}
                            className="px-1.5 py-0.5 bg-[#f59e0b]/10 text-[#f59e0b] border border-[#f59e0b]/20 rounded-md text-[9px] font-black uppercase tracking-tighter"
                          >
                            {fid.replace("_detect", "").toUpperCase()}
                          </span>
                        ))
                      ) : (
                        <span className="text-sm font-bold text-foreground">
                          Cơ bản
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3 ml-4 shrink-0">
                  {/* PTZ Button */}
                  <button
                    onClick={onPtzClick}
                    className={`flex items-center gap-2 px-4 py-2 text-xs font-black rounded-lg transition-all duration-200 uppercase tracking-wider ${
                      isPtzActive 
                        ? "bg-blue-600 text-white shadow-lg shadow-blue-900/40 translate-y-[-1px]" 
                        : "bg-zinc-800 text-zinc-300 hover:bg-zinc-700 hover:text-white"
                    }`}
                  >
                    <ControlCamera sx={{ fontSize: 16 }} />
                    PTZ
                  </button>

                  {/* Capture Button */}
                  <button
                    onClick={async () => {
                      const activeId = getActiveId(mainCamera);
                      if (!activeId) return;
                      try {
                        const token = localStorage.getItem('token');
                        const res = await fetch(
                          `/api/cameras/${activeId}/capture`,
                          { 
                            method: "POST",
                            headers: { 'Authorization': `Bearer ${token}` }
                          }
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
                    className="flex items-center gap-2 px-5 py-2.5 bg-[#f59e0b] text-black font-black text-xs rounded-lg hover:bg-[#f59e0b]/90 transition-all duration-200 shadow-lg shadow-[#f59e0b]/20 hover:shadow-[#f59e0b]/30 uppercase tracking-widest active:scale-95"
                  >
                    <PhotoCamera sx={{ fontSize: 18 }} />
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
