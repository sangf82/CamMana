import React from "react";
import { LayoutGrid, Scan, Camera, Move, Info } from "lucide-react";
import VideoPlayer from "../../../components/features/monitoring/VideoPlayer";
import { toast } from "sonner";
import { StreamingLoader } from "@/components/ui/loading-spinner";
import { Button } from "@/components/ui/button";

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


function CameraGrid({
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
          <span className="text-xs font-bold text-amber-500 px-1 uppercase tracking-wide">
            {currentGate ? `GIÁM SÁT: ${currentGate}` : "CHỌN CỔNG ĐỂ XEM"}
          </span>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Button
            onClick={() => setViewMode("focus")}
            variant="ghost"
            size="icon"
            className={`h-8 w-8 rounded transition-colors ${
              viewMode === "focus"
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:bg-muted"
            }`}
            title="Chế độ Tập trung"
          >
            <Scan className="w-5 h-5 text-amber-500" />
          </Button>
          <Button
            onClick={() => setViewMode("grid")}
            variant="ghost"
            size="icon"
            className={`h-8 w-8 rounded transition-colors ${
              viewMode === "grid"
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:bg-muted"
            }`}
            title="Chế độ Lưới"
          >
            <LayoutGrid className="w-5 h-5 text-amber-500" />
          </Button>
        </div>
      </div>

      {/* Videos */}
      <div
        className={`flex-1 min-h-0 bg-background rounded-lg overflow-hidden p-1 ${
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
                  className={`relative bg-muted rounded-xl border-2 transition-all duration-300 overflow-hidden shadow-inner ${
                    cam ? "border-border/40 hover:border-amber-500/50 hover:shadow-amber-500/5" : "border-dashed border-border/20"
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
                      <Camera className="mb-2 w-8 h-8 opacity-10" />
                      <span className="text-[10px] font-medium uppercase tracking-widest">Trống {idx + 1}</span>
                    </div>
                  )}
                </div>
              );
            })}
          </>
        ) : !currentGate ? (
          <div className="w-full h-full flex flex-col items-center justify-center bg-muted/50 border-2 border-dashed border-border/20 rounded-xl text-muted-foreground/50">
            <p className="text-sm font-medium">Vui lòng chọn Cổng để bắt đầu giám sát</p>
          </div>
        ) : filteredCameras.length === 0 ? (
          <div className="w-full h-full flex flex-col items-center justify-center bg-muted/50 border-2 border-dashed border-border/20 rounded-xl text-muted-foreground/50">
            <Camera className="w-12 h-12 mb-4 opacity-10" />
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
                    <span className="text-sm font-black text-amber-500 truncate" title={mainCamera.name}>
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
                            className="px-1.5 py-0.5 bg-amber-500/10 text-amber-500 border border-amber-500/20 rounded-md text-[9px] font-black uppercase tracking-tighter"
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
                  <Button
                    onClick={onPtzClick}
                    variant={isPtzActive ? "default" : "secondary"}
                    size="sm"
                    className={`gap-2 font-black uppercase tracking-wider ${
                      isPtzActive 
                        ? "bg-blue-600 hover:bg-blue-500 shadow-lg shadow-blue-900/40" 
                        : "bg-muted text-muted-foreground hover:bg-muted/80 hover:text-foreground"
                    }`}
                  >
                    <Move className="w-4 h-4" />
                    PTZ
                  </Button>

                  {/* Capture Button */}
                  <Button
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
                    className="gap-2 bg-amber-500 text-black font-black hover:bg-amber-500/90 shadow-lg shadow-amber-500/20 uppercase tracking-widest"
                    size="sm"
                  >
                    <Camera className="w-4.5 h-4.5" />
                    Chụp ảnh
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default React.memo(CameraGrid);
