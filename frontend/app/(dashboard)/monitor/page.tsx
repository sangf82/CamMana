"use client";

import React, { useState, useEffect, Suspense, useCallback } from "react";
import { useSearchParams } from "next/navigation";

import {
  PhotoCamera,
  CheckCircle,
  Cancel,
  Edit,
  Palette,
  TireRepair,
  DriveEta,
  Warning,
} from "@mui/icons-material";
import { toast } from "sonner";
import CameraGrid from "../../../components/features/monitoring/CameraGrid";
import EventLog from "../../../components/features/monitoring/EventLog";
import EvidenceModal from "../../../components/features/monitoring/EvidenceModal";
import EditModal from "../../../components/features/monitoring/EditModal";

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

interface EventLogEntry {
  time: string;
  message: string;
  type: "info" | "success" | "warning" | "error";
}

function MonitorPageContent() {
  const searchParams = useSearchParams();
  const gateParam = searchParams.get("gate");

  // UI State
  const [viewMode, setViewMode] = useState<"focus" | "grid">("grid");
  const [currentGate, setCurrentGate] = useState<string>("");
  const [isAutoDetect, setIsAutoDetect] = useState(false);
  const [selectedCameraIndex, setSelectedCameraIndex] = useState(0);
  const [showEditModal, setShowEditModal] = useState(false);

  // Data State
  const [logs, setLogs] = useState<EventLogEntry[]>([]);
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
  const [currentTimeIn, setCurrentTimeIn] = useState<string | null>(null);

  // Edit Modal State
  const [editPlate, setEditPlate] = useState("");
  const [editStatus, setEditStatus] = useState("vào cổng");
  const [editVerify, setEditVerify] = useState("chưa xác minh");
  const [editNote, setEditNote] = useState("");

  const STORAGE_KEY = "monitor_pending_detection";
  
  // Load from sessionStorage
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

  // Save to sessionStorage
  useEffect(() => {
    if (currentDetection || snapshotUrl || currentTimeIn) {
      const data = { currentDetection, snapshotUrl, capturedImages, currentTimeIn };
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    }
  }, [currentDetection, snapshotUrl, capturedImages, currentTimeIn]);

  const clearDetectionData = useCallback(() => {
    setCurrentDetection(null);
    setSnapshotUrl(null);
    setCapturedImages({});
    setCurrentTimeIn(null);
    sessionStorage.removeItem(STORAGE_KEY);
  }, []);

  const addLog = useCallback((message: string, type: EventLogEntry["type"] = "info") => {
    const time = new Date().toLocaleTimeString("vi-VN");
    setLogs((prev) => {
      // Skip duplicate messages within 2s
      if (prev.length > 0 && prev[0].message === message && prev[0].time === time) {
        return prev;
      }
      return [{ time, message, type }, ...prev.slice(0, 49)];
    });
  }, []);

  // 1. Load Data & Sync Filter
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

  // 2. Auto-connect cameras
  const filteredCameras = React.useMemo(
    () => cameras.filter((c) => c.location === currentGate),
    [cameras, currentGate]
  );

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

  // Detection Request
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

    const sideActiveId = sideCamera ? getActiveId(sideCamera) : undefined;

    setIsProcessing(true);
    addLog("Đang chụp và phân tích...", "info");

    try {
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
          setCapturedImages({
            front: data.front_image_url || null,
            side: data.side_image_url || null,
          });

          if (result.plate_number) addLog(`✓ Biển số: ${result.plate_number}`, "success");
          else addLog("⚠ Không nhận diện được biển số", "warning");

          if (result.color) addLog(`✓ Màu xe: ${result.color}`, "success");
          if (result.wheel_count > 0) addLog(`✓ Số bánh: ${result.wheel_count}`, "success");

          if (result.matched) {
            addLog("✓ Xe có trong danh sách đăng ký", "success");
            toast.success("Xe khớp với đăng ký!");
          } else if (result.plate_number) {
            addLog("⚠ Xe không có trong danh sách đăng ký", "warning");
            toast.warning("Xe lạ - cần xác minh thủ công");
          }

          const historyTimeIn = data.time_in;
          const historyPlate = data.history_plate;
          
          if (historyTimeIn) {
            setCurrentTimeIn(historyTimeIn);
            if (historyPlate && historyPlate !== result.plate_number) {
               result.plate_number = historyPlate;
               setCurrentDetection(prev => prev ? {...prev, plate_number: historyPlate} : result);
            }
          } else {
             const timeIn = new Date().toLocaleTimeString("vi-VN");
             setCurrentTimeIn(timeIn);
          }

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

  const handleConfirm = async () => {
    if (!currentDetection || !currentTimeIn) return;
    try {
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

  const handleReject = async () => {
    if (!currentDetection || !currentTimeIn) return;
    try {
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

  const openEditModal = () => {
    setEditPlate(currentDetection?.plate_number || "");
    setEditStatus("vào cổng");
    setEditVerify(currentDetection?.matched ? "chưa xác minh" : "xe lạ");
    setEditNote("");
    setShowEditModal(true);
  };

  const handleSaveEdit = async () => {
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
        <CameraGrid
          viewMode={viewMode}
          setViewMode={setViewMode}
          currentGate={currentGate}
          filteredCameras={filteredCameras}
          isConnecting={isConnecting}
          getActiveId={getActiveId}
          getStreamUrl={getStreamUrl}
          mainCamera={mainCamera}
          streamInfo={streamInfo}
          addLog={addLog}
        />

        {/* RIGHT: AI Logs */}
        <EventLog
          logs={logs}
          isAutoDetect={isAutoDetect}
          setIsAutoDetect={setIsAutoDetect}
          handleManualDetection={handleManualDetection}
          isProcessing={isProcessing}
          currentGate={currentGate}
        />
      </div>

      {/* --- BOTTOM: VERIFICATION --- */}
      <div className="h-48 bg-card border border-border rounded-lg p-4 flex gap-6 shrink-0 shadow-lg">
        {/* 1. Evidence - Clickable to open modal */}
        <div 
          className={`w-64 bg-black rounded border border-border/50 relative overflow-hidden group ${currentDetection ? "cursor-pointer hover:border-primary/50" : ""}`}
          onClick={() => {
            if (currentDetection) {
              setEvidenceActiveTab("front");
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

      <EditModal
        isOpen={showEditModal}
        onClose={() => setShowEditModal(false)}
        onSave={handleSaveEdit}
        editPlate={editPlate}
        setEditPlate={setEditPlate}
        editStatus={editStatus}
        setEditStatus={setEditStatus}
        editVerify={editVerify}
        setEditVerify={setEditVerify}
        editNote={editNote}
        setEditNote={setEditNote}
      />

      <EvidenceModal
        isOpen={showEvidenceModal}
        onClose={() => setShowEvidenceModal(false)}
        currentDetection={currentDetection}
        capturedImages={capturedImages}
        snapshotUrl={snapshotUrl}
        activeTab={evidenceActiveTab}
        setActiveTab={setEvidenceActiveTab}
      />
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
