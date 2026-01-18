"use client";

import React, { useState, useEffect, Suspense, useCallback } from "react";
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
  Close,
  DriveEta,
  Warning,
} from "@mui/icons-material";
import VideoPlayer from "../../../components/features/monitoring/VideoPlayer";
import { toast } from "sonner";

// --- Types ---
interface Camera {
  id: string;
  name: string;
  ip: string;
  location: string;
  location_id?: string;
  status: "Online" | "Offline" | "Connected" | "Local";
  type: string;
  tag?: string;
  username?: string;
  password?: string;
  port?: number;
  cam_id?: string;
  brand?: string;
}

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

interface EventLog {
  time: string;
  message: string;
  type: "info" | "success" | "warning" | "error";
}

function MonitorPageContent() {
  const searchParams = useSearchParams();
  const gateParam = searchParams.get("gate");

  // UI State - Default to grid view
  const [viewMode, setViewMode] = useState<"focus" | "grid">("grid");
  const [currentGate, setCurrentGate] = useState<string>("");
  const [isAutoDetect, setIsAutoDetect] = useState(false); // Default to manual mode
  const [selectedCameraIndex, setSelectedCameraIndex] = useState(0);
  const [showEditModal, setShowEditModal] = useState(false);

  // Data State
  const [logs, setLogs] = useState<EventLog[]>([]);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [activeCameras, setActiveCameras] = useState<Record<string, string>>({});
  const [connectingCameras, setConnectingCameras] = useState<Set<string>>(new Set());
  const [streamInfo, setStreamInfo] = useState<{ resolution: string; fps: number } | null>(null);

  // Detection State
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentDetection, setCurrentDetection] = useState<DetectionResult | null>(null);
  const [snapshotUrl, setSnapshotUrl] = useState<string | null>(null);
  const [capturedImages, setCapturedImages] = useState<{ front?: string; side?: string }>({});
  const [showEvidenceModal, setShowEvidenceModal] = useState(false);
  const [evidenceActiveTab, setEvidenceActiveTab] = useState<"front" | "side">("front");
  const [currentTimeIn, setCurrentTimeIn] = useState<string | null>(null); // For updates

  // Edit Modal State
  const [editPlate, setEditPlate] = useState("");
  const [editStatus, setEditStatus] = useState("vào cổng");
  const [editVerify, setEditVerify] = useState("chưa xác minh");
  const [editNote, setEditNote] = useState("");

  // --- Persist detection data to sessionStorage ---
  const STORAGE_KEY = "monitor_pending_detection";
  
  // Load from sessionStorage on mount
  useEffect(() => {
    try {
      const saved = sessionStorage.getItem(STORAGE_KEY);
      if (saved) {
        const data = JSON.parse(saved);
        if (data.currentDetection) setCurrentDetection(data.currentDetection);
        if (data.snapshotUrl) setSnapshotUrl(data.snapshotUrl);
        if (data.capturedImages) setCapturedImages(data.capturedImages);
        if (data.currentTimeIn) setCurrentTimeIn(data.currentTimeIn);
      }
    } catch (e) {
      console.error("Failed to load detection from storage", e);
    }
  }, []);

  // Save to sessionStorage when detection data changes
  useEffect(() => {
    if (currentDetection || snapshotUrl || currentTimeIn) {
      const data = { currentDetection, snapshotUrl, capturedImages, currentTimeIn };
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    }
  }, [currentDetection, snapshotUrl, capturedImages, currentTimeIn]);

  // Clear storage helper (called after confirm/reject/edit)
  const clearDetectionData = useCallback(() => {
    setCurrentDetection(null);
    setSnapshotUrl(null);
    setCapturedImages({});
    setCurrentTimeIn(null);
    sessionStorage.removeItem(STORAGE_KEY);
  }, []);

  // Helper: Add log entry (prevents duplicates)
  const addLog = useCallback((message: string, type: EventLog["type"] = "info") => {
    const time = new Date().toLocaleTimeString("vi-VN");
    setLogs((prev) => {
      // Skip if the same message was logged in the last 2 seconds
      if (prev.length > 0 && prev[0].message === message && prev[0].time === time) {
        return prev;
      }
      return [{ time, message, type }, ...prev.slice(0, 49)];
    });
  }, []);

  // --- 1. Load Data & Sync Filter ---
  useEffect(() => {
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

    if (gateParam) {
      setCurrentGate(gateParam);
    } else {
      setCurrentGate("");
    }
  }, [gateParam]);

  // --- 2. Auto-connect cameras when gate changes ---
  const filteredCameras = React.useMemo(
    () => cameras.filter((c) => c.location === currentGate),
    [cameras, currentGate]
  );

  // Get front and side cameras based on tag, name, or type
  // Supports both English keywords (plate, color, wheel) and Vietnamese (biển số, màu, bánh)
  const frontCamera = React.useMemo(() => {
    const typeLower = (c: Camera) => (c.type || "").toLowerCase();
    const nameLower = (c: Camera) => (c.name || "").toLowerCase();
    
    return filteredCameras.find((c) => 
      c.tag === "front_cam" || 
      typeLower(c).includes("plate") || 
      typeLower(c).includes("biển số") ||
      typeLower(c).includes("bien so") ||
      nameLower(c).includes("trước") ||
      nameLower(c).includes("truoc") ||
      nameLower(c).includes("front")
    );
  }, [filteredCameras]);

  const sideCamera = React.useMemo(() => {
    const typeLower = (c: Camera) => (c.type || "").toLowerCase();
    const nameLower = (c: Camera) => (c.name || "").toLowerCase();
    
    return filteredCameras.find((c) => 
      c.tag === "side_cam" || 
      typeLower(c).includes("color") || 
      typeLower(c).includes("wheel") ||
      typeLower(c).includes("màu") ||
      typeLower(c).includes("bánh") ||
      nameLower(c).includes("hông") ||
      nameLower(c).includes("hong") ||
      nameLower(c).includes("side")
    );
  }, [filteredCameras]);

  useEffect(() => {
    if (!currentGate || filteredCameras.length === 0) return;

    const connectAndStream = async (cam: Camera) => {
      if (activeCameras[cam.id]) return;

      setConnectingCameras((prev) => {
        if (prev.has(cam.id)) return prev;
        const next = new Set(prev);
        next.add(cam.id);
        return next;
      });

      try {
        addLog(`Đang kết nối ${cam.name}...`, "info");
        const connectRes = await fetch("/api/cameras/connect", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            ip: cam.ip,
            port: cam.port || 8899,
            user: cam.username || "admin",
            password: cam.password || "",
            name: cam.name,
            location: cam.location,
          }),
        });

        if (connectRes.ok) {
          const data = await connectRes.json();
          if (data.success || data.id) {
            const activeId = data.id;
            setActiveCameras((prev) => ({ ...prev, [cam.id]: activeId }));
            addLog(`✓ Đã kết nối ${cam.name}`, "success");

            // Start stream
            await fetch(`/api/cameras/${activeId}/stream/start`, { method: "POST" });
          } else {
            addLog(`✗ Lỗi kết nối ${cam.name}: ${data.error}`, "error");
          }
        }
      } catch (e) {
        addLog(`✗ Lỗi kết nối ${cam.name}`, "error");
      } finally {
        setConnectingCameras((prev) => {
          const next = new Set(prev);
          next.delete(cam.id);
          return next;
        });
      }
    };

    filteredCameras.forEach((cam, index) => {
      setTimeout(() => connectAndStream(cam), index * 100);
    });
  }, [currentGate, filteredCameras, activeCameras, addLog]);

  // Helper functions
  const getStreamUrl = (cam: Camera) => {
    const activeId = activeCameras[cam.id];
    if (activeId) return `/api/cameras/${activeId}/stream`;
    return undefined;
  };

  const getActiveId = (cam: Camera) => activeCameras[cam.id];
  const isConnecting = (cam: Camera) => connectingCameras.has(cam.id);

  const mainCamera = filteredCameras[selectedCameraIndex] || filteredCameras[0];

  useEffect(() => {
    setSelectedCameraIndex(0);
  }, [currentGate]);

  // Fetch stream info
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

  // --- Manual Detection ---
  const handleManualDetection = async () => {
    if (!frontCamera) {
      toast.error("Không tìm thấy camera trước (biển số)");
      return;
    }

    const frontActiveId = getActiveId(frontCamera);
    if (!frontActiveId) {
      toast.error("Camera trước chưa được kết nối");
      return;
    }

    // Get side camera ID (optional)
    const sideActiveId = sideCamera ? getActiveId(sideCamera) : undefined;

    setIsProcessing(true);
    addLog("Đang chụp và phân tích...", "info");

    try {
      // Call check-in capture-and-process API
      const res = await fetch("/api/checkin/capture-and-process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          front_camera_id: frontActiveId,
          side_camera_id: sideActiveId || null,
          location_id: frontCamera.location_id || currentGate,
          location_name: currentGate,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        
        if (data.success) {
          const result: DetectionResult = {
            plate_number: data.plate || null,
            color: data.color || null,
            wheel_count: data.wheel_count || 0,
            confidence: data.confidence || 0,
            matched: !!data.matched,
            registered_info: data.registered_info,
            snapshot_url: data.snapshot_url,
            folder_path: data.folder_path,
            uuid: data.uuid,
          };

          setCurrentDetection(result);
          setSnapshotUrl(data.snapshot_url || null);
          
          // Store captured images for evidence panel
          setCapturedImages({
            front: data.front_image_url || null,
            side: data.side_image_url || null,
          });

          if (result.plate_number) {
            addLog(`✓ Biển số: ${result.plate_number}`, "success");
          } else {
            addLog("⚠ Không nhận diện được biển số", "warning");
          }

          if (result.color) {
            addLog(`✓ Màu xe: ${result.color}`, "success");
          }

          if (result.wheel_count > 0) {
            addLog(`✓ Số bánh: ${result.wheel_count}`, "success");
          }

          if (result.matched) {
            addLog("✓ Xe có trong danh sách đăng ký", "success");
            toast.success("Xe khớp với đăng ký!");
          } else if (result.plate_number) {
            addLog("⚠ Xe không có trong danh sách đăng ký", "warning");
            toast.warning("Xe lạ - cần xác minh thủ công");
          }

          // Use history data from backend response
          const historyTimeIn = data.time_in;
          const historyPlate = data.history_plate;
          
          if (historyTimeIn) {
            setCurrentTimeIn(historyTimeIn);
            
            // If backend saved with a different plate (e.g. PENDING or partial), 
            // update our current detection to match so future updates work
            if (historyPlate && historyPlate !== result.plate_number) {
               // We only update the plate used for API calls, not necessarily the UI display if we want to keep showing what was detected
               // But for consistency, let's trust the backend's saved record key
               result.plate_number = historyPlate;
               setCurrentDetection(prev => prev ? {...prev, plate_number: historyPlate} : result);
            }
          } else {
             // Fallback if backend didn't return time_in (old backend version?)
             const timeIn = new Date().toLocaleTimeString("vi-VN");
             setCurrentTimeIn(timeIn);
          }

          addLog("💾 Đã lưu vào lịch sử", "info");
          addLog("💾 Đã lưu vào lịch sử", "info");
        } else {
          addLog(`✗ ${data.error || data.reason}`, "error");
          toast.error(data.error || data.reason || "Không phát hiện được xe");
        }
      } else {
        const errorData = await res.json().catch(() => null);
        addLog(`✗ Lỗi server: ${errorData?.detail || res.statusText}`, "error");
        toast.error("Lỗi kết nối server");
      }
    } catch (e) {
      addLog("✗ Lỗi xử lý", "error");
      toast.error("Có lỗi xảy ra khi xử lý");
      console.error("Detection error:", e);
    } finally {
      setIsProcessing(false);
    }
  };

  // --- Confirm Check-in ---
  const handleConfirm = async () => {
    if (!currentDetection || !currentTimeIn) return;

    try {
      // Update existing history record
      const res = await fetch("/api/history", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          plate: currentDetection.plate_number || "Không nhận diện",
          time_in: currentTimeIn,
          status: "đã vào",
          verify: "đã xác minh",
          note: "Bình thường",
        }),
      });

      if (res.ok) {
        addLog(`✓ Đã xác nhận xe ${currentDetection.plate_number || ""}`, "success");
        toast.success("Đã xác nhận xe vào cổng!");
        clearDetectionData();
      }
    } catch (e) {
      toast.error("Lỗi khi lưu dữ liệu");
    }
  };

  // --- Reject ---
  const handleReject = async () => {
    if (!currentDetection || !currentTimeIn) return;
    
    try {
      // Update existing history record with rejection
      const res = await fetch("/api/history", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          plate: currentDetection.plate_number || "Không nhận diện",
          time_in: currentTimeIn,
          status: "vào cổng",
          verify: "xe chưa đk",
          note: "Xe không được xác thực",
        }),
      });

      if (res.ok) {
        addLog(`✗ Đã từ chối xe ${currentDetection.plate_number || ""}`, "error");
        toast.info("Đã cập nhật trạng thái từ chối");
      } else {
        toast.error("Lỗi khi lưu dữ liệu");
      }
    } catch (e) {
      toast.error("Lỗi khi lưu dữ liệu");
    }
    
    clearDetectionData();
  };

  // --- Edit Modal ---
  const openEditModal = () => {
    setEditPlate(currentDetection?.plate_number || "");
    setEditStatus("vào cổng");
    setEditVerify(currentDetection?.matched ? "chưa xác minh" : "xe lạ");
    setEditNote("");
    setShowEditModal(true);
  };

  const handleSaveEdit = async () => {
    // Update existing history record with edited info
    if (!currentTimeIn) {
      toast.error("Không có dữ liệu để cập nhật");
      return;
    }
    
    try {
      const res = await fetch("/api/history", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          plate: currentDetection?.plate_number || "Không nhận diện",
          time_in: currentTimeIn,
          status: editStatus,
          verify: editVerify,
          note: editNote || "Đã xác minh thủ công",
        }),
      });

      if (res.ok) {
        addLog(`✓ Đã cập nhật thông tin: ${editPlate}`, "success");
        toast.success("Đã cập nhật thông tin!");
        setShowEditModal(false);
        clearDetectionData();
      }
    } catch (e) {
      toast.error("Lỗi khi lưu dữ liệu");
    }
  };

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
            {logs.length === 0 && (
              <div className="text-center text-muted-foreground italic text-[10px] py-4 opacity-50">
                Chưa có sự kiện nào
              </div>
            )}
            {logs.map((log, i) => (
              <div
                key={i}
                className={`p-2 rounded border border-border/50 animate-in fade-in slide-in-from-right-2 duration-300 ${
                  log.type === "success"
                    ? "bg-green-500/10 text-green-400"
                    : log.type === "warning"
                    ? "bg-amber-500/10 text-amber-400"
                    : log.type === "error"
                    ? "bg-red-500/10 text-red-400"
                    : "bg-muted/30 text-muted-foreground"
                }`}
              >
                <span className="text-[10px] opacity-60">{log.time}</span> {log.message}
              </div>
            ))}
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
              onClick={handleManualDetection}
              disabled={isProcessing || !currentGate}
              className={`w-full py-2 rounded text-xs font-bold flex items-center justify-center gap-2 transition-all active:scale-95 ${
                isProcessing
                  ? "bg-muted text-muted-foreground cursor-not-allowed"
                  : "bg-secondary hover:bg-secondary/80 text-secondary-foreground border border-border/50"
              }`}
              title="Kích hoạt phát hiện thủ công"
            >
              {isProcessing ? (
                <>
                  <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                  ĐANG XỬ LÝ...
                </>
              ) : (
                <>
                  <PlayCircle fontSize="small" />
                  KÍCH HOẠT THỦ CÔNG
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* --- BOTTOM: VERIFICATION --- */}
      <div className="h-48 bg-card border border-border rounded-lg p-4 flex gap-6 shrink-0 shadow-lg">
        {/* 1. Evidence - Clickable to open modal */}
        <div 
          className={`w-64 bg-black rounded border border-border/50 relative overflow-hidden group ${currentDetection ? "cursor-pointer hover:border-primary/50" : ""}`}
          onClick={() => {
            if (currentDetection) {
              setShowEvidenceModal(true);
            }
          }}
        >
          {snapshotUrl || capturedImages.front ? (
            <>
              <img
                src={snapshotUrl || capturedImages.front}
                alt="Snapshot"
                className="w-full h-full object-cover"
              />
              {/* Hover overlay */}
              {currentDetection && (
                <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                  <span className="text-white text-xs font-medium">Nhấn để xem ảnh</span>
                </div>
              )}
            </>
          ) : (
            <div className="absolute inset-0 flex items-center justify-center text-muted-foreground text-sm">
              <PhotoCamera className="mr-2" /> Bằng chứng
            </div>
          )}

        </div>

        {/* 2. Comparison */}
        <div className="flex-1 flex gap-8">
          <div className="flex-1 space-y-3">
            <h4 className="text-xs font-bold text-primary uppercase tracking-wider flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${currentDetection ? "bg-primary animate-pulse" : "bg-muted"}`} />
              Kết quả AI
            </h4>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-muted/30 p-2 rounded border border-border/50">
                <span className="block text-xs text-muted-foreground mb-1">
                  Biển số
                </span>
                <span className={`text-xl font-mono font-bold tracking-widest ${currentDetection?.plate_number ? "text-white" : "text-muted-foreground"}`}>
                  {currentDetection?.plate_number || "---"}
                </span>
              </div>
              <div className="bg-muted/30 p-2 rounded border border-border/50">
                <span className="block text-xs text-muted-foreground mb-1">
                  Thể tích
                </span>
                <span className="text-xl font-mono font-bold text-muted-foreground tracking-widest">
                  ---
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Palette fontSize="small" className="text-muted-foreground" />
                <div>
                  <span className="block text-[10px] text-muted-foreground">
                    Màu xe
                  </span>
                  <span className={`text-sm font-medium ${currentDetection?.color ? "text-foreground" : "text-muted-foreground"}`}>
                    {currentDetection?.color || "---"}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <TireRepair fontSize="small" className="text-muted-foreground" />
                <div>
                  <span className="block text-[10px] text-muted-foreground">
                    Số bánh
                  </span>
                  <span className={`text-sm font-medium ${currentDetection?.wheel_count ? "text-foreground" : "text-muted-foreground"}`}>
                    {currentDetection?.wheel_count || "---"}
                  </span>
                </div>
              </div>
            </div>
          </div>
          <div className="w-px bg-border my-2" />
          <div className={`flex-1 space-y-3 ${!currentDetection?.matched ? "opacity-50" : ""}`}>
            <h4 className="text-xs font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              {currentDetection?.matched ? (
                <DriveEta className="text-green-400" fontSize="small" />
              ) : (
                <Warning className="text-amber-400" fontSize="small" />
              )}
              Dữ liệu đăng ký
            </h4>
            {currentDetection?.matched && currentDetection.registered_info ? (
              <div className="space-y-2">
                <div className="p-2 bg-green-500/10 border border-green-500/30 rounded">
                  <span className="text-[10px] text-muted-foreground">Chủ xe</span>
                  <p className="text-sm font-medium text-green-400">
                    {currentDetection.registered_info.owner}
                  </p>
                </div>
                <div className="p-2 bg-muted/20 rounded border border-border/50">
                  <span className="text-[10px] text-muted-foreground">Model</span>
                  <p className="text-sm">{currentDetection.registered_info.model}</p>
                </div>
              </div>
            ) : (
              <div className="p-3 border border-dashed border-border rounded bg-muted/10 text-center text-sm text-muted-foreground">
                {currentDetection ? "Xe không có trong danh sách" : "Chờ xe vào cổng..."}
              </div>
            )}
          </div>
        </div>

        {/* 3. Actions */}
        <div className="w-48 flex flex-col justify-center gap-3 border-l border-border pl-6">
          <button
            onClick={handleConfirm}
            disabled={!currentDetection}
            className={`flex-1 font-medium rounded shadow-lg flex items-center justify-center gap-2 transition-transform active:scale-95 ${
              currentDetection
                ? "bg-green-600 hover:bg-green-500 text-white shadow-green-900/20"
                : "bg-muted text-muted-foreground cursor-not-allowed"
            }`}
          >
            <CheckCircle />
            Xác nhận
          </button>
          <button
            onClick={openEditModal}
            disabled={!currentDetection}
            className={`flex-1 font-medium rounded flex items-center justify-center gap-2 transition-colors ${
              currentDetection
                ? "bg-secondary hover:bg-muted border border-border text-foreground"
                : "bg-muted text-muted-foreground cursor-not-allowed"
            }`}
          >
            <Edit fontSize="small" />
            Sửa thông tin
          </button>
          <button
            onClick={handleReject}
            disabled={!currentDetection}
            className={`flex-1 font-medium rounded flex items-center justify-center gap-2 transition-colors ${
              currentDetection
                ? "bg-red-900/30 hover:bg-red-900/50 border border-red-900 text-red-400"
                : "bg-muted text-muted-foreground cursor-not-allowed"
            }`}
          >
            <Cancel fontSize="small" />
            Từ chối
          </button>
        </div>
      </div>

      {/* Edit Modal */}
      {showEditModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[9999] pointer-events-auto">
          <div className="bg-card border border-border rounded-lg p-6 w-96 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-lg">Sửa thông tin xe</h3>
              <button
                onClick={() => setShowEditModal(false)}
                className="text-muted-foreground hover:text-foreground"
              >
                <Close />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-xs text-muted-foreground uppercase tracking-wider">
                  Biển số
                </label>
                <input
                  type="text"
                  value={editPlate}
                  onChange={(e) => setEditPlate(e.target.value.toUpperCase())}
                  className="w-full mt-1 px-3 py-2 bg-background border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-primary"
                  placeholder="Nhập biển số..."
                />
              </div>

              <div>
                <label className="text-xs text-muted-foreground uppercase tracking-wider">
                  Trạng thái
                </label>
                <select
                  value={editStatus}
                  onChange={(e) => setEditStatus(e.target.value)}
                  className="w-full mt-1 px-3 py-2 bg-background border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="vào cổng">Vào cổng</option>
                  <option value="đã vào">Đã vào</option>
                  <option value="đang cân">Đang cân</option>
                  <option value="ra cổng">Ra cổng</option>
                  <option value="đã ra">Đã ra</option>
                </select>
              </div>

              <div>
                <label className="text-xs text-muted-foreground uppercase tracking-wider">
                  Xác minh
                </label>
                <select
                  value={editVerify}
                  onChange={(e) => setEditVerify(e.target.value)}
                  className="w-full mt-1 px-3 py-2 bg-background border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="đã xác minh">Đã xác minh</option>
                  <option value="chưa xác minh">Chưa xác minh</option>
                  <option value="cần kt">Cần KT</option>
                  <option value="xe lạ">Xe lạ</option>
                  <option value="xe chưa đk">Xe chưa ĐK</option>
                </select>
              </div>

              <div>
                <label className="text-xs text-muted-foreground uppercase tracking-wider">
                  Ghi chú
                </label>
                <input
                  type="text"
                  value={editNote}
                  onChange={(e) => setEditNote(e.target.value)}
                  className="w-full mt-1 px-3 py-2 bg-background border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-primary"
                  placeholder="Nhập ghi chú..."
                />
              </div>
            </div>

            <div className="flex gap-3 pt-4">
              <button
                onClick={() => setShowEditModal(false)}
                className="flex-1 py-2 bg-muted text-muted-foreground rounded-md font-medium"
              >
                Hủy
              </button>
              <button
                onClick={handleSaveEdit}
                className="flex-1 py-2 bg-primary text-primary-foreground rounded-md font-bold"
              >
                Lưu
              </button>
            </div>
          </div>
        </div>
      )}

      {/* --- Evidence Modal --- */}
      {showEvidenceModal && (
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
                onClick={() => setShowEvidenceModal(false)}
                className="p-1 hover:bg-muted rounded-full transition-colors"
              >
                <Close />
              </button>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-border">
              <button
                onClick={() => setEvidenceActiveTab("front")}
                className={`flex-1 py-3 px-4 text-sm font-medium transition-colors ${
                  evidenceActiveTab === "front"
                    ? "text-primary border-b-2 border-primary bg-primary/10"
                    : "text-muted-foreground hover:bg-muted/50"
                }`}
              >
                📷 Camera Trước (Biển số)
              </button>
              <button
                onClick={() => setEvidenceActiveTab("side")}
                className={`flex-1 py-3 px-4 text-sm font-medium transition-colors ${
                  evidenceActiveTab === "side"
                    ? "text-primary border-b-2 border-primary bg-primary/10"
                    : "text-muted-foreground hover:bg-muted/50"
                }`}
              >
                📷 Camera Hông (Màu/Bánh)
              </button>
            </div>

            {/* Image Content */}
            <div className="p-4 bg-black min-h-[400px] flex items-center justify-center">
              {evidenceActiveTab === "front" ? (
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
              ) : (
                capturedImages.side ? (
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
                )
              )}
            </div>

            {/* Detection Info Footer */}
            {currentDetection && (
              <div className="p-4 border-t border-border bg-muted/30">
                <div className="grid grid-cols-4 gap-4 text-center">
                  <div>
                    <span className="block text-xs text-muted-foreground">Biển số</span>
                    <span className="font-mono font-bold">{currentDetection.plate_number || "---"}</span>
                  </div>
                  <div>
                    <span className="block text-xs text-muted-foreground">Màu xe</span>
                    <span className="font-medium">{currentDetection.color || "---"}</span>
                  </div>
                  <div>
                    <span className="block text-xs text-muted-foreground">Số bánh</span>
                    <span className="font-medium">{currentDetection.wheel_count || "---"}</span>
                  </div>
                  <div>
                    <span className="block text-xs text-muted-foreground">Trạng thái</span>
                    <span className={`font-medium ${currentDetection.matched ? "text-green-400" : "text-amber-400"}`}>
                      {currentDetection.matched ? "Khớp ĐK" : "Xe lạ"}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function MonitorPage() {
  return (
    <Suspense fallback={<div className="h-full flex items-center justify-center">Loading...</div>}>
      <MonitorPageContent />
    </Suspense>
  );
}
