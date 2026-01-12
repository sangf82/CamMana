"use client";

import React, { useState, useEffect } from "react";
// Only using Next.js hooks for client-side search params requires Suspense wrapper or similar,
// but in 'use client' page basic usage is fine, or standard window.location if necessary.
// Let's stick to useSearchParams for standard Next.js, but watch out for Suspense boundaries.
import { useSearchParams } from "next/navigation";

import {
  GridView,
  CropFree,
  PhotoCamera,
  EventNote,
  CheckCircle,
  Cancel,
  Edit,
  Palette,
  TireRepair,
  PlayCircle,
  ToggleOn,
  ToggleOff,
} from "@mui/icons-material";
import VideoPlayer from "../../../components/features/monitoring/VideoPlayer";

// --- Types ---
interface Camera {
  id: string;
  name: string;
  ip: string;
  location: string;
  status: "Online" | "Offline" | "Connected" | "Local";
  type: string;
  username?: string;
  password?: string;
  port?: number;
  cam_id?: string;
  brand?: string;
}

const MOCK_LOGS: string[] = []; // Empty initially

export default function MonitorPage() {
  const searchParams = useSearchParams();
  const gateParam = searchParams.get("gate");

  const [viewMode, setViewMode] = useState<"focus" | "grid">("focus");
  const [currentGate, setCurrentGate] = useState<string>("");
  const [isAutoDetect, setIsAutoDetect] = useState(true);
  const [selectedCameraIndex, setSelectedCameraIndex] = useState(0);

  // Data State
  const [logs, setLogs] = useState(MOCK_LOGS);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [activeCameras, setActiveCameras] = useState<Record<string, string>>(
    {}
  ); // savedId -> activeId
  const [connectingCameras, setConnectingCameras] = useState<Set<string>>(
    new Set()
  );
  const [streamInfo, setStreamInfo] = useState<{
    resolution: string;
    fps: number;
  } | null>(null);

  // --- 1. Load Data & Sync Filter ---
  useEffect(() => {
    // 1a. Load Cameras from Backend API (syncs with cameras.csv)
    const loadCameras = async () => {
      try {
        const res = await fetch("/api/cameras/saved");
        if (res.ok) {
          const data = await res.json();
          setCameras(data);
        }
      } catch (e) {
        console.error("Failed to load cameras", e);
      }
    };
    loadCameras();

    // 1b. Determine Gate from URL
    if (gateParam) {
      setCurrentGate(gateParam);
    } else {
      setCurrentGate("");
    }
  }, [gateParam]);

  // --- 2. Auto-connect cameras when gate changes ---
  const filteredCameras = cameras.filter((c) => c.location === currentGate);

  useEffect(() => {
    if (filteredCameras.length === 0) return;

    const connectAndStream = async (cam: Camera) => {
      if (activeCameras[cam.id] || connectingCameras.has(cam.id)) return;

      setConnectingCameras((prev) => new Set(prev).add(cam.id));

      try {
        // Connect camera
        const connectRes = await fetch("/api/cameras/connect", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            ip: cam.ip,
            port: cam.port || 8899,
            user: cam.username || "admin",
            password: cam.password || "",
            name: cam.name,
          }),
        });

        if (connectRes.ok) {
          const data = await connectRes.json();
          if (data.success || data.id) {
            const activeId = data.id;
            setActiveCameras((prev) => ({ ...prev, [cam.id]: activeId }));

            // Start stream
            await fetch(`/api/cameras/${activeId}/stream/start`, {
              method: "POST",
            });
          }
        }
      } catch (e) {
        console.error(`Failed to connect camera ${cam.name}`, e);
      } finally {
        setConnectingCameras((prev) => {
          const next = new Set(prev);
          next.delete(cam.id);
          return next;
        });
      }
    };

    filteredCameras.forEach((cam) => connectAndStream(cam));
  }, [filteredCameras.map((c) => c.id).join(",")]); // Re-run when filtered cameras change

  // Helper to get stream URL
  const getStreamUrl = (cam: Camera) => {
    const activeId = activeCameras[cam.id];
    if (activeId) return `/api/cameras/${activeId}/stream`;
    return undefined;
  };

  const getActiveId = (cam: Camera) => activeCameras[cam.id];
  const isConnecting = (cam: Camera) => connectingCameras.has(cam.id);

  // In focus mode, use selected camera; in grid mode, show all
  const mainCamera = filteredCameras[selectedCameraIndex] || filteredCameras[0];
  const secondaryCamera =
    filteredCameras.find((c) => c.type !== "LPR") || filteredCameras[1];
  
  // Reset selection when gate changes
  useEffect(() => {
    setSelectedCameraIndex(0);
  }, [currentGate]);

  // Fetch stream info for main camera
  useEffect(() => {
    const activeId = mainCamera ? activeCameras[mainCamera.id] : null;
    if (!activeId) {
      setStreamInfo(null);
      return;
    }

    const fetchStreamInfo = async () => {
      try {
        const res = await fetch("/api/cameras");
        if (res.ok) {
          const cameras = await res.json();
          const cam = cameras.find((c: { id: string }) => c.id === activeId);
          if (cam?.stream_info) {
            setStreamInfo({
              resolution: cam.stream_info.resolution || "N/A",
              fps: cam.stream_info.fps || 0,
            });
          }
        }
      } catch (e) {
        // Ignore
      }
    };

    fetchStreamInfo();
    const interval = setInterval(fetchStreamInfo, 2000);
    return () => clearInterval(interval);
  }, [mainCamera?.id, activeCameras]);

  return (
    <div className="h-full flex flex-col p-1 gap-1 overflow-hidden">
      {/* --- TOP AREA (70% Height) --- */}
      <div className="flex-1 flex gap-1 min-h-0">
        {/* LEFT: Camera Selector (Mini List) */}
        <div className="w-10 flex flex-col gap-1 bg-card border border-border rounded-lg p-1 overflow-hidden shrink-0">
          {filteredCameras.length > 0 ? (
            filteredCameras.map((cam, idx) => (
              <button
                key={cam.id}
                onClick={() => {
                  setSelectedCameraIndex(idx);
                  setViewMode("focus");
                }}
                className={`w-8 h-8 rounded flex items-center justify-center text-[10px] font-bold transition-colors ${
                  selectedCameraIndex === idx && viewMode === "focus"
                    ? "bg-primary text-black"
                    : "bg-muted text-muted-foreground hover:bg-primary hover:text-black"
                }`}
                title={cam.name}
              >
                {idx + 1}
              </button>
            ))
          ) : (
            <div className="text-[8px] text-center text-muted-foreground pt-2">
              No Cam
            </div>
          )}
        </div>

        {/* CENTER: Video Display Area */}
        <div className="flex-1 flex flex-col gap-1">
          {/* Controls Bar */}
          <div className="flex items-center justify-between bg-card border border-border px-2 py-1 rounded-lg">
            <div className="flex items-center gap-2">
              {/* Dynamic Title based on selection */}
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
              // Grid Mode - Always show 4 boxes (2x2)
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
              // Focus Mode - Single Camera with Info Panel
              <div className="h-full w-full flex flex-col overflow-hidden">
                {/* Video Area - fills entire container */}
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
                    activeId={
                      mainCamera ? getActiveId(mainCamera) : undefined
                    }
                    src={mainCamera ? getStreamUrl(mainCamera) : undefined}
                  />
                </div>

                {/* Info Panel Below Video - full width */}
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
                          Loại Camera
                        </span>
                        <span className="text-sm font-medium text-foreground">
                          {mainCamera.type || "N/A"}
                        </span>
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
                              alert(`Đã chụp ảnh: ${data.filename}`);
                            } else {
                              alert(`Lỗi: ${data.error}`);
                            }
                          }
                        } catch (e) {
                          alert("Lỗi khi chụp ảnh");
                        }
                      }}
                      className="flex items-center gap-2 px-4 py-2 bg-primary text-black font-semibold rounded-md hover:bg-primary/90 transition-colors"
                    >
                      <PhotoCamera fontSize="small" />
                      Chụp ảnh
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* RIGHT: AI Logs */}
        <div className="w-72 bg-card border border-border rounded-lg flex flex-col shrink-0">
          <div className="p-3 border-b border-border bg-muted/20 font-semibold text-sm flex items-center gap-2">
            <EventNote fontSize="small" className="text-primary" />
            Nhật ký Sự kiện
          </div>
          <div className="flex-1 overflow-y-auto p-2 font-mono text-xs space-y-1">
            {/* Empty State for Logs */}
            {logs.length === 0 && (
              <div className="text-center text-muted-foreground italic text-[10px] py-4 opacity-50">
                Chưa có sự kiện nào
              </div>
            )}
            {logs.map((log, i) => (
              <div
                key={i}
                className="p-2 rounded bg-muted/30 border border-border/50 text-muted-foreground animate-in fade-in slide-in-from-right-2 duration-300"
              >
                {log}
              </div>
            ))}
            {logs.length > 0 && (
              <div className="animate-pulse text-primary text-xs mt-2">
                Running...
              </div>
            )}
          </div>

          {/* CONTROL PANEL */}
          <div className="p-3 border-t border-border bg-muted/10 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground">
                Tự động phát hiện
              </span>
              <button
                onClick={() => setIsAutoDetect(!isAutoDetect)}
                className={`flex items-center gap-1 transition-colors ${
                  isAutoDetect ? "text-primary" : "text-muted-foreground"
                }`}
              >
                <span className="text-[10px] font-bold">
                  {isAutoDetect ? "ON" : "OFF"}
                </span>
                {isAutoDetect ? (
                  <ToggleOn fontSize="large" />
                ) : (
                  <ToggleOff fontSize="large" />
                )}
              </button>
            </div>

            <button
              className="w-full bg-secondary hover:bg-secondary/80 text-secondary-foreground border border-border/50 py-2 rounded text-xs font-bold flex items-center justify-center gap-2 transition-all active:scale-95"
              title="Kích hoạt phát hiện thủ công"
            >
              <PlayCircle fontSize="small" />
              KÍCH HOẠT THỦ CÔNG
            </button>
          </div>
        </div>
      </div>

      {/* --- BOTTOM: VERIFICATION --- */}
      <div className="h-48 bg-card border border-border rounded-lg p-4 flex gap-6 shrink-0 shadow-lg">
        {/* 1. Evidence */}
        <div className="w-64 bg-black rounded border border-border/50 relative overflow-hidden group">
          <div className="absolute inset-0 flex items-center justify-center text-muted-foreground text-sm">
            <PhotoCamera className="mr-2" /> Bằng chứng
          </div>
          {filteredCameras.length > 0 && currentGate && (
            <div className="absolute bottom-2 left-2 bg-black/60 px-2 py-0.5 rounded text-[10px] text-white">
              Snapshot: 14:32:01
            </div>
          )}
        </div>

        {/* 2. Comparison */}
        <div className="flex-1 flex gap-8">
          <div className="flex-1 space-y-3">
            <h4 className="text-xs font-bold text-primary uppercase tracking-wider flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
              Kết quả AI
            </h4>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-muted/30 p-2 rounded border border-border/50">
                <span className="block text-xs text-muted-foreground mb-1">
                  Biển số
                </span>
                <span className="text-xl font-mono font-bold text-white tracking-widest">
                  ---
                </span>
              </div>
              <div className="bg-muted/30 p-2 rounded border border-border/50">
                <span className="block text-xs text-muted-foreground mb-1">
                  Thể tích
                </span>
                <span className="text-xl font-mono font-bold text-white tracking-widest">---</span>
              </div>
              <div className="flex items-center gap-2">
                <Palette fontSize="small" className="text-muted-foreground" />
                <div>
                  <span className="block text-[10px] text-muted-foreground">
                    Màu xe
                  </span>
                  <span className="text-sm font-medium">---</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <TireRepair
                  fontSize="small"
                  className="text-muted-foreground"
                />
                <div>
                  <span className="block text-[10px] text-muted-foreground">
                    Số trục/bánh
                  </span>
                  <span className="text-sm font-medium">---</span>
                </div>
              </div>
            </div>
          </div>
          <div className="w-px bg-border my-2" />
          <div className="flex-1 space-y-3 opacity-50">
            <h4 className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
              Dữ liệu đăng ký
            </h4>
            <div className="p-3 border border-dashed border-border rounded bg-muted/10 text-center text-sm text-muted-foreground">
              Chờ xe vào cổng...
            </div>
          </div>
        </div>

        {/* 3. Actions */}
        <div className="w-48 flex flex-col justify-center gap-3 border-l border-border pl-6">
          <button className="flex-1 bg-green-600 hover:bg-green-500 text-white font-bold rounded shadow-lg shadow-green-900/20 flex items-center justify-center gap-2 transition-transform active:scale-95">
            <CheckCircle />
            XÁC NHẬN
          </button>
          <button className="flex-1 bg-secondary hover:bg-muted border border-border text-foreground font-medium rounded flex items-center justify-center gap-2 transition-colors">
            <Edit fontSize="small" />
            Sửa thông tin
          </button>
          <button className="flex-1 bg-red-900/30 hover:bg-red-900/50 border border-red-900 text-red-400 font-medium rounded flex items-center justify-center gap-2 transition-colors">
            <Cancel fontSize="small" />
            Từ chối
          </button>
        </div>
      </div>
    </div>
  );
}
