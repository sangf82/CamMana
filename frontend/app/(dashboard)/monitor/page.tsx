"use client";

import React, { useState, useEffect, Suspense, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import {
  Camera as CameraIcon,
  CheckCircle,
  XCircle,
  Pencil,
  Palette,
  CircleDashed,
  Car,
  AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";
import CameraGrid from "../../../components/features/monitoring/CameraGrid";
import EventLog from "../../../components/features/monitoring/EventLog";
import EvidenceModal from "../../../components/features/monitoring/EvidenceModal";
import EditModal from "../../../components/features/monitoring/EditModal";
import { Button } from "@/components/ui/button";

// --- Types ---
interface Camera {
  id: string;
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
  functions?: string[];
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
  volume?: number | null;
  history_volume?: number | null;
  top_image_url?: string;
  is_checkout?: boolean;
}

interface EventLogEntry {
  time: string;
  message: string;
  type: "info" | "success" | "warning" | "error";
}

interface Location {
  id: string;
  name: string;
  tag: string;
}

function MonitorPageContent() {
  const searchParams = useSearchParams();
  const gateParam = searchParams.get("gate");

  // UI State
  const [viewMode, setViewMode] = useState<"focus" | "grid">("grid");
  const [currentGate, setCurrentGate] = useState<string>("");
  const [isAutoDetect, setIsAutoDetect] = useState(false);
  
  // Track previous gate for disconnect logic
  const previousGateRef = React.useRef<string>("");
  const [selectedCameraIndex, setSelectedCameraIndex] = useState(0);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showPtzPanel, setShowPtzPanel] = useState(false);

  // Data State
  const [logs, setLogs] = useState<EventLogEntry[]>([]);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [camTypes, setCamTypes] = useState<any[]>([]);
  const [activeCameras, setActiveCameras] = useState<Record<string, string>>(
    {},
  );
  const activeCamerasRef = React.useRef<Record<string, string>>({});
  
  // Keep ref in sync with state
  React.useEffect(() => {
    activeCamerasRef.current = activeCameras;
  }, [activeCameras]);
  
  const [connectingCameras, setConnectingCameras] = useState<Set<string>>(
    new Set(),
  );
  const [streamInfo, setStreamInfo] = useState<{
    resolution: string;
    fps: number;
  } | null>(null);

  // Detection State
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentDetection, setCurrentDetection] =
    useState<DetectionResult | null>(null);
  const [snapshotUrl, setSnapshotUrl] = useState<string | null>(null);
  // Dynamic camera images map: { [cameraId]: imageUrl }
  const [capturedImages, setCapturedImages] = useState<Record<string, string | null>>({});
  const [showEvidenceModal, setShowEvidenceModal] = useState(false);
  const [currentTimeIn, setCurrentTimeIn] = useState<string | null>(null);

  // Edit Modal State
  const [editPlate, setEditPlate] = useState("");
  const [editStatus, setEditStatus] = useState("vào cổng");
  const [editVerify, setEditVerify] = useState("chưa xác minh");
  const [editNote, setEditNote] = useState("");
  const [editVolume, setEditVolume] = useState("");

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
      const data = {
        currentDetection,
        snapshotUrl,
        capturedImages,
        currentTimeIn,
      };
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

  const addLog = useCallback(
    (message: string, type: EventLogEntry["type"] = "info") => {
      const time = new Date().toLocaleTimeString("vi-VN");
      setLogs((prev) => {
        // Skip duplicate messages within 2s
        if (
          prev.length > 0 &&
          prev[0].message === message &&
          prev[0].time === time
        ) {
          return prev;
        }
        return [{ time, message, type }, ...prev.slice(0, 49)];
      });
    },
    [],
  );

  // Disconnect all cameras for a specific gate
  const disconnectCamerasForGate = useCallback(async (gateName: string) => {
    if (!gateName) return;
    
    const camerasToDisconnect = cameras.filter((c) => c.location === gateName);
    const token = localStorage.getItem('token');
    
    // Get current active cameras from ref to avoid stale closure
    const currentActive = activeCamerasRef.current;
    
    for (const cam of camerasToDisconnect) {
      if (currentActive[cam.id]) {
        try {
          await fetch(`/api/cameras/${cam.id}/disconnect`, {
            method: "POST",
            headers: { 'Authorization': `Bearer ${token}` }
          });
        } catch (e) {
          console.error(`Failed to disconnect ${cam.name}`, e);
        }
      }
    }
    
    // Clear active cameras state for disconnected cameras
    setActiveCameras((prev) => {
      const next = { ...prev };
      for (const cam of camerasToDisconnect) {
        delete next[cam.id];
      }
      return next;
    });
  }, [cameras]); // Only depends on cameras list

  // Handle gate change - disconnect old cameras before connecting new ones
  // Use ref to prevent re-running on every activeCameras change
  const isGateChangeInProgress = React.useRef(false);
  
  useEffect(() => {
    const handleGateChange = async () => {
      const previousGate = previousGateRef.current;
      
      // Skip if same gate or already processing a gate change
      if (previousGate === currentGate || isGateChangeInProgress.current) {
        previousGateRef.current = currentGate;
        return;
      }
      
      // If gate changed and there was a previous gate, disconnect its cameras
      if (previousGate) {
        isGateChangeInProgress.current = true;
        addLog(`Ngắt kết nối cameras từ ${previousGate}...`, "info");
        await disconnectCamerasForGate(previousGate);
        addLog(`✓ Đã ngắt kết nối cameras từ ${previousGate}`, "success");
        isGateChangeInProgress.current = false;
      }
      
      // Update the previous gate ref
      previousGateRef.current = currentGate;
    };
    
    handleGateChange();
  }, [currentGate]); // Only depend on currentGate, not the functions

  // 1. Load Data & Sync Filter
  useEffect(() => {
    const loadCameras = async () => {
      try {
        const token = localStorage.getItem('token');
        if (!token) return;
        
        const headers = { 'Authorization': `Bearer ${token}` };
        
        const [resCam, resLoc, resTypes] = await Promise.all([
          fetch("/api/cameras", { headers }),
          fetch("/api/locations", { headers }),
          fetch("/api/camera_types", { headers })
        ]);
        
        if (resCam.ok) {
          const data = await resCam.json();
          setCameras(data);
        }
        if (resLoc.ok) {
           const data = await resLoc.json();
           setLocations(data);
        }
        if (resTypes.ok) {
            const data = await resTypes.json();
            setCamTypes(data);
        }
      } catch (e) {
        console.error("Failed to load data", e);
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
    [cameras, currentGate],
  );

  // Helper to check functions
  const hasFunction = useCallback((cam: Camera, func: string) => {
    const typeObj = camTypes.find(t => t.name === cam.type || t.id === cam.type);
    if (!typeObj) return false;
    const functions = typeObj.functions || [];
    if (typeof functions === 'string') return functions.split(';').filter(Boolean).includes(func);
    return Array.isArray(functions) && functions.includes(func);
  }, [camTypes]);

  // Camera role assignment - based ONLY on functions
  const frontCamera = React.useMemo(() => {
    return filteredCameras.find((c) => hasFunction(c, "plate_detect"));
  }, [filteredCameras, hasFunction]);

  // TopCamera selected before sideCamera to prioritize volume_top_down
  const topCamera = React.useMemo(() => {
    return filteredCameras.find(
      (c) =>
        c.id !== frontCamera?.id &&
        hasFunction(c, "volume_top_down")
    );
  }, [filteredCameras, hasFunction, frontCamera]);

  const sideCamera = React.useMemo(() => {
    return filteredCameras.find(
      (c) =>
        c.id !== frontCamera?.id &&
        c.id !== topCamera?.id &&
        (hasFunction(c, "color_detect") ||
         hasFunction(c, "wheel_detect") ||
         hasFunction(c, "volume_left_right"))
    );
  }, [filteredCameras, hasFunction, frontCamera, topCamera]);


  // Track if initial connection for this gate has been done
  const connectedGatesRef = React.useRef<Set<string>>(new Set());

  useEffect(() => {
    if (!currentGate || filteredCameras.length === 0) return;
    
    // Skip if already connected cameras for this gate
    if (connectedGatesRef.current.has(currentGate)) return;

    // Add a small delay to ensure disconnect completes first
    const timeoutId = setTimeout(() => {
      // Mark this gate as connected
      connectedGatesRef.current.add(currentGate);
      
      const connectAndStream = async (cam: Camera) => {
        // Check if already active using current state
        setActiveCameras((prevActive) => {
          if (prevActive[cam.id]) return prevActive; // Already connected, skip
          
          // Start connection process
          setConnectingCameras((prev) => {
            if (prev.has(cam.id)) return prev;
            const next = new Set(prev);
            next.add(cam.id);
            return next;
          });

          (async () => {
            try {
              addLog(`Đang kết nối ${cam.name}...`, "info");
              const token = localStorage.getItem('token');
              const connectRes = await fetch(`/api/cameras/${cam.id}/connect`, {
                method: "POST",
                headers: { 'Authorization': `Bearer ${token}` }
              });

              if (connectRes.ok) {
                const data = await connectRes.json();
                if (data.success) {
                  setActiveCameras((prev) => ({ ...prev, [cam.id]: cam.id }));
                  addLog(`✓ Đã kết nối ${cam.name}`, "success");
                } else {
                  addLog(`✗ Lỗi kết nối ${cam.name}: ${data.details?.error || 'Unknown'}`, "error");
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
          })();
          
          return prevActive; // Return unchanged, actual update happens in async
        });
      };

      filteredCameras.forEach((cam, index) => {
        setTimeout(() => connectAndStream(cam), index * 500);
      });
    }, 300); // Wait 300ms for disconnect to complete

    return () => clearTimeout(timeoutId);
  }, [currentGate, filteredCameras, addLog]);
  
  // Clear connected gate tracking when gate changes
  useEffect(() => {
    // Remove the old gate from tracked set when switching
    const previousGate = previousGateRef.current;
    if (previousGate && previousGate !== currentGate) {
      connectedGatesRef.current.delete(previousGate);
    }
  }, [currentGate]);

  const getStreamUrl = useCallback((cam: Camera) => {
    const activeId = activeCameras[cam.id];
    if (activeId) return `/api/cameras/${activeId}/stream`;
    return undefined;
  }, [activeCameras]);

  const getActiveId = useCallback((cam: Camera) => activeCameras[cam.id], [activeCameras]);
  const isConnecting = useCallback((cam: Camera) => connectingCameras.has(cam.id), [connectingCameras]);

  const mainCamera = filteredCameras[selectedCameraIndex] || filteredCameras[0];

  // Reset camera index when gate changes
  useEffect(() => {
    setSelectedCameraIndex(0);
  }, [currentGate]);

  // Auto-close PTZ panel when switching cameras to avoid conflicts
  useEffect(() => {
    setShowPtzPanel(false);
  }, [mainCamera?.id]);

  useEffect(() => {
    const activeId = mainCamera ? activeCameras[mainCamera.id] : null;
    if (!activeId) {
      setStreamInfo(null);
      return;
    }

    const fetchStreamInfo = async () => {
      try {
        const token = localStorage.getItem('token');
        const res = await fetch(`/api/cameras/${activeId}/stream-info`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setStreamInfo({
            resolution: data.resolution || "N/A",
            fps: data.fps || 0,
          });
        }
      } catch (e) {
        // Ignore - camera may not be connected yet
      }
    };

    fetchStreamInfo();
    const interval = setInterval(fetchStreamInfo, 5000); // Reduce frequency to 5s
    return () => clearInterval(interval);
  }, [mainCamera?.id, activeCameras]);

    // Detection Request
    // Detection Request
    const handleManualDetection = async () => {
      // Collect all cameras at current gate that have capabilities
      // We send ALL of them, backend will capture and use functions assigned in CSV
      const targetCameras = filteredCameras.filter(c => c.functions && c.functions.length > 0);

      if (targetCameras.length === 0) {
        toast.error("Không tìm thấy camera khả dụng (kiểm tra cấu hình chức năng)");
        return;
      }

      // Check for volume capability for feedback
      const hasTop = targetCameras.some(c => c.functions!.includes('volume_top_down'));
      const hasSide = targetCameras.some(c => c.functions!.some(f => ['volume_left_right','wheel_detect'].includes(f)));
      
      if (hasTop && hasSide) {
          addLog("Đủ điều kiện đo thể tích (Trên + Hông)", "info");
      }

      setIsProcessing(true);
      addLog("Đang chụp và phân tích...", "info");

      try {
        const token = localStorage.getItem('token');
        const currentLocation = locations.find(l => l.name === currentGate);

        const bodyObj = {
          cameras: targetCameras.map(c => getActiveId(c)),
          location_id: currentLocation?.id || "",
          location_name: currentGate
        };

        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || ''}/api/checkin/capture-and-process`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify(bodyObj),
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
            volume: data.volume,
            registered_info: data.registered_info,
            snapshot_url: data.snapshot_url,
            folder_path: data.folder_path,
            uuid: data.uuid,
            top_image_url: data.top_image_url,
            is_checkout: data.is_checkout,
            history_volume: data.history_volume,
          };

          setCurrentDetection(result);
          setSnapshotUrl(data.snapshot_url || null);
          
          // Build camera images map using camera IDs
          const newCameraImages: Record<string, string | null> = {};
          if (frontCamera && data.front_image_url) {
            newCameraImages[frontCamera.id] = data.front_image_url;
          }
          if (sideCamera && data.side_image_url) {
            newCameraImages[sideCamera.id] = data.side_image_url;
          }
          if (topCamera && data.top_image_url) {
            newCameraImages[topCamera.id] = data.top_image_url;
          }
          setCapturedImages(newCameraImages);


          if (result.plate_number)
            addLog(`✓ Biển số: ${result.plate_number}`, "success");
          else addLog("⚠ Không nhận diện được biển số", "warning");

          if (result.color) addLog(`✓ Màu xe: ${result.color}`, "success");
          if (result.wheel_count > 0)
            addLog(`✓ Số bánh: ${result.wheel_count}`, "success");
          if (result.volume !== undefined && result.volume !== null)
            addLog(`✓ Thể tích: ${result.volume} m³`, "success");

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
              setCurrentDetection((prev) =>
                prev ? { ...prev, plate_number: historyPlate } : result,
              );
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
      const bodyObj: any = {
        plate: currentDetection?.plate_number || "Không nhận diện",
        time_in: currentTimeIn,
        verify: "Đã xác minh",
        note: "Bình thường",
      };

      if (currentDetection?.is_checkout) {
        bodyObj.status = "Đã ra";
        bodyObj.verify = "Đã xác minh";
        bodyObj.time_out = new Date().toLocaleTimeString("en-GB");
        bodyObj.vol_measured = currentDetection.volume || "";
      } else {
        bodyObj.status = "Đã vào";
        bodyObj.verify = "Đã xác minh";
      }

      let res;
      const token = localStorage.getItem('token');
      const headers = { 
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      };

      if (currentDetection?.is_checkout) {
        // Use manual-confirm for checkout
        res = await fetch(`/api/checkout/manual-confirm`, {
          method: "POST",
          headers,
          body: JSON.stringify({
            uuid: currentDetection?.uuid,
            plate: currentDetection?.plate_number || "Không nhận diện",
            status: bodyObj.status,
            verify: bodyObj.verify,
            note: bodyObj.note,
            time_out: bodyObj.time_out,
          }),
        });
      } else {
        // Standard Update
        res = await fetch(`/api/history/${currentDetection?.uuid}`, {
          method: "PUT",
          headers,
          body: JSON.stringify(bodyObj),
        });
      }
      
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        if (data.merged) {
             addLog(`✓ Đã gộp và xác nhận xe ra: ${data.plate}`, "success");
        } else {
             addLog(`✓ Đã xác nhận xe: ${currentDetection?.plate_number || ""}`, "success");
        }
        const msg = currentDetection?.is_checkout
          ? "Đã xác nhận xe ra cổng!"
          : "Đã xác nhận xe vào cổng!";
        toast.success(msg);
        clearDetectionData();
      }
    } catch (e) {
      toast.error("Lỗi khi lưu dữ liệu");
    }
  };

  const handleReject = async () => {
    if (!currentDetection || !currentTimeIn) return;
    try {
      const bodyObj: any = {
        plate: currentDetection?.plate_number || "Không nhận diện",
        time_in: currentTimeIn,
        note: "Xe không được xác thực",
      };

      if (currentDetection?.is_checkout) {
        // Rejecting checkout: no change status (still moved in)
        bodyObj.status = "Đã vào";
        bodyObj.verify = "Từ chối";
        bodyObj.note = "Về lại mỏ - Khối lượng không khớp hoặc lỗi khác";
      } else {
        // Rejecting checkin: move in and move out time are the same
        bodyObj.status = "Đã ra";
        bodyObj.time_out = currentTimeIn;
        bodyObj.verify = "Từ chối";
        bodyObj.note = "Từ chối vào cổng";
      }
      
      const token = localStorage.getItem('token');
      const res = await fetch(`/api/history/${currentDetection?.uuid}`, {
        method: "PUT",
        headers: { 
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify(bodyObj),
      });

      if (res.ok) {
        addLog(
          `✗ Đã từ chối xe ${currentDetection?.plate_number || ""}`,
          "error",
        );
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
    setEditStatus(currentDetection?.is_checkout ? "Đã ra" : "Đã vào");
    setEditVerify(currentDetection?.matched ? "Đã xác minh" : "Xe lạ");
    setEditNote(currentDetection?.matched ? "Thông tin khớp" : "Xe lạ cần xác minh");
    setEditVolume(currentDetection?.volume?.toString() || "");
    setShowEditModal(true);
  };

  const handleSaveEdit = async () => {
    if (!currentTimeIn) {
      toast.error("Không có dữ liệu để cập nhật");
      return;
    }
    try {
      // Need uuid for editing. currentDetection needs to be valid.
      const uuid = currentDetection?.uuid;
      if (!uuid) {
          toast.error("Không tìm thấy ID bản ghi");
          return;
      }
      const bodyObj: any = {
        plate: editPlate || "Không nhận diện",
        time_in: currentTimeIn,
        status: editStatus,
        verify: editVerify,
        note: editNote || "Đã xác minh thủ công",
        vol_measured: editVolume,
      };

      // If status implies exit, or if we are at check-out gate and just saving, ensure time_out
      if (editStatus === "Đã ra" || editStatus === "Ra cổng") {
          // If rejecting from checkin: time_in and time_out are same
          if (!currentDetection?.is_checkout && editVerify === "Từ chối") {
              bodyObj.time_out = currentTimeIn;
          } else {
              bodyObj.time_out = new Date().toLocaleTimeString("en-GB");
          }
      }
      
      let res;
      const token = localStorage.getItem('token');
      const headers = { 
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      };

      if (currentDetection?.is_checkout) {
          // Use manual-confirm for checkout to handle merging
          res = await fetch(`/api/checkout/manual-confirm`, {
            method: "POST",
            headers,
            body: JSON.stringify({
                uuid: uuid,
                plate: editPlate || "Không nhận diện",
                status: editStatus,
                verify: editVerify,
                note: editNote || "Đã xác minh thủ công",
                vol_measured: editVolume,
                time_out: bodyObj.time_out // from logic above
            }),
          });
      } else {
          // Standard Update
          res = await fetch(`/api/history/${uuid}`, {
            method: "PUT",
            headers,
            body: JSON.stringify(bodyObj),
          });
      }

      const data = await res.json();
      if (res.ok) {
        if (data.merged) {
             addLog(`✓ Đã gộp dữ liệu ra với bản ghi vào cũ: ${data.plate}`, "success");
        } else {
             addLog(`✓ Đã cập nhật thông tin: ${editPlate}`, "success");
        }
        
        toast.success("Đã cập nhật thông tin!");
        setShowEditModal(false);
        clearDetectionData();
      } else {
        toast.error("Lỗi khi lưu dữ liệu");
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
              <Button
                key={cam.id}
                onClick={() => {
                  setSelectedCameraIndex(idx);
                  setViewMode("focus");
                }}
                variant={selectedCameraIndex === idx && viewMode === "focus" ? "default" : "secondary"}
                size="sm"
                className={`w-8 h-8 p-0 text-[10px] font-bold ${
                  selectedCameraIndex === idx && viewMode === "focus"
                    ? "bg-amber-500 text-black hover:bg-amber-600"
                    : "text-muted-foreground"
                }`}
                title={cam.name}
              >
                {idx + 1}
              </Button>
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
          onPtzClick={() => setShowPtzPanel(!showPtzPanel)}
          isPtzActive={showPtzPanel}
        />

        {/* RIGHT: AI Logs / PTZ Control */}
        <EventLog
          logs={logs}
          isAutoDetect={isAutoDetect}
          setIsAutoDetect={setIsAutoDetect}
          handleManualDetection={handleManualDetection}
          isProcessing={isProcessing}
          currentGate={currentGate}
          activeMainCameraId={mainCamera ? getActiveId(mainCamera) : undefined}
          showPtzPanel={showPtzPanel}
          onClosePtz={() => setShowPtzPanel(false)}
        />
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
          {(() => {
            const frontImg = frontCamera ? capturedImages[frontCamera.id] : null;
            const displayUrl = snapshotUrl || frontImg;
            
            return displayUrl ? (
              <>
                <img
                  src={displayUrl}
                  alt="Snapshot"
                  className="w-full h-full object-cover"
                />
                {/* Hover overlay */}
                {currentDetection && (
                   <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                     <span className="text-white text-xs font-medium">
                       Nhấn để xem ảnh
                     </span>
                   </div>
                )}
              </>
            ) : (
                <div className="absolute inset-0 flex items-center justify-center text-muted-foreground text-sm">
                  <CameraIcon className="mr-2" /> Bằng chứng
                </div>
            );
          })()}
        </div>


        {/* 2. Comparison */}
        <div className="flex-1 flex gap-4 lg:gap-8">
          <div className="flex-1 space-y-3 min-w-0">
            <h4 className="text-xs font-bold text-amber-500 uppercase tracking-wider flex items-center gap-2">
              <div
                className={`w-2 h-2 rounded-full ${currentDetection ? "bg-amber-500 animate-pulse" : "bg-muted"}`}
              />
              Kết quả AI
            </h4>
            <div className="grid grid-cols-2 gap-2 lg:gap-4">
              <div className="bg-muted/30 p-2 rounded border border-border/50 min-w-0">
                <span className="block text-xs text-muted-foreground mb-1">
                  Biển số
                </span>
                <span
                  className={`block text-sm sm:text-base lg:text-xl font-mono font-bold tracking-wide lg:tracking-widest truncate ${currentDetection?.plate_number ? "text-foreground" : "text-muted-foreground"}`}
                  title={currentDetection?.plate_number || "---"}
                >
                  {currentDetection?.plate_number || "---"}
                </span>
              </div>
              <div className="bg-muted/30 p-2 rounded border border-border/50 min-w-0">
                <span className="block text-xs text-muted-foreground mb-1">
                  Thể tích
                </span>
                {(() => {
                   const vol = currentDetection?.volume;
                   if (!vol) return <span className="text-sm sm:text-base lg:text-xl font-mono font-bold tracking-wide lg:tracking-widest text-muted-foreground">---</span>;
                   
                   const stdVol = parseFloat(currentDetection.registered_info?.standard_volume || "");
                   const histVol = currentDetection.history_volume;
                   const baseline = !isNaN(stdVol) ? stdVol : (histVol || null);
                   
                   let colorClass = "text-foreground";
                   if (baseline) {
                       const diff = Math.abs(vol - baseline);
                       const tolerance = baseline * 0.05;
                       colorClass = diff <= tolerance ? "text-green-400" : "text-amber-500";
                   }
                   
                   return (
                     <span className={`block text-sm sm:text-base lg:text-xl font-mono font-bold tracking-wide lg:tracking-widest truncate ${colorClass}`}>
                       {vol} m³
                     </span>
                   );
                })()}
              </div>
              <div className="flex items-center gap-2 min-w-0">
                <Palette className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                <div className="min-w-0">
                  <span className="block text-[10px] text-muted-foreground">
                    Màu xe
                  </span>
                  <span
                    className={`block text-xs sm:text-sm font-medium truncate ${currentDetection?.color ? "text-foreground" : "text-muted-foreground"}`}
                  >
                    {currentDetection?.color || "---"}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2 min-w-0">
                <CircleDashed
                  className="w-4 h-4 text-muted-foreground flex-shrink-0"
                />
                <div className="min-w-0">
                  <span className="block text-[10px] text-muted-foreground">
                    Số bánh
                  </span>
                  <span
                    className={`block text-xs sm:text-sm font-medium truncate ${currentDetection?.wheel_count ? "text-foreground" : "text-muted-foreground"}`}
                  >
                    {currentDetection?.wheel_count || "---"}
                  </span>
                </div>
              </div>
            </div>
          </div>
          <div className="w-px bg-border my-2 flex-shrink-0" />
          <div
            className={`flex-1 space-y-3 min-w-0 ${!currentDetection?.matched ? "opacity-50" : ""}`}
          >
            <h4 className="text-xs font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              {currentDetection?.matched ? (
                <Car className="w-4 h-4 text-green-400" />
              ) : (
                <AlertTriangle className="w-4 h-4 text-amber-400" />
              )}
              Dữ liệu đăng ký
            </h4>
            {currentDetection?.matched && currentDetection.registered_info ? (
              <div className="space-y-2">
                <div className="p-2 bg-green-500/10 border border-green-500/30 rounded">
                  <span className="text-[10px] text-muted-foreground">
                    Chủ xe
                  </span>
                  <p className="text-sm font-medium text-green-400">
                    {currentDetection.registered_info.owner}
                  </p>
                </div>
                <div className="p-2 bg-muted/20 rounded border border-border/50">
                  <span className="text-[10px] text-muted-foreground">
                    Model
                  </span>
                  <p className="text-sm">
                    {currentDetection.registered_info.model}
                  </p>
                </div>
                <div className="p-2 bg-muted/20 rounded border border-border/50">
                  <span className="text-[10px] text-muted-foreground">
                    Khoảng bình thường (±5%)
                  </span>
                  {(() => {
                    const stdVol = parseFloat(currentDetection.registered_info?.standard_volume || "");
                    const histVol = currentDetection.history_volume;
                    const baseline = !isNaN(stdVol) ? stdVol : (histVol || null);
                    
                    if (baseline) {
                      const min = (baseline * 0.95).toFixed(2);
                      const max = (baseline * 1.05).toFixed(2);
                      return (
                        <p className="text-sm font-mono text-amber-500">
                          {min} - {max} m³
                        </p>
                      );
                    }
                    return <p className="text-sm font-mono text-muted-foreground">---</p>;
                  })()}
                </div>
              </div>
            ) : (
              <div className="space-y-2">
                <div className="p-3 border border-dashed border-border rounded bg-muted/10 text-center text-sm text-muted-foreground">
                  {currentDetection
                    ? "Xe không có trong danh sách"
                    : "Chờ kết quả AI..."}
                </div>
                {currentDetection?.history_volume && (
                    <div className="p-2 bg-muted/20 rounded border border-border/50">
                    <span className="text-[10px] text-muted-foreground">
                        Khoảng bình thường (Entry ±5%)
                    </span>
                    {(() => {
                        const baseline = currentDetection.history_volume as number;
                        const min = (baseline * 0.95).toFixed(2);
                        const max = (baseline * 1.05).toFixed(2);
                        return (
                        <p className="text-sm font-mono text-amber-500">
                            {min} - {max} m³
                        </p>
                        );
                    })()}
                    </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* 3. Actions */}
        <div className="w-48 flex flex-col justify-center gap-3 border-l border-border pl-6">
          <Button
            onClick={handleConfirm}
            disabled={!currentDetection}
            variant="success"
            className="flex-1 py-2.5 font-medium rounded-lg flex items-center justify-center gap-2 transition-all active:scale-95 text-white shadow-lg"
          >
            <CheckCircle className="w-4 h-4" />
            Xác nhận
          </Button>
          <Button
            onClick={openEditModal}
            disabled={!currentDetection}
            variant="warning"
            className="flex-1 py-2.5 font-medium rounded-lg flex items-center justify-center gap-2 transition-all active:scale-95 text-white shadow-lg"
          >
            <Pencil className="w-4 h-4" />
            Sửa thông tin
          </Button>
          <Button
            onClick={handleReject}
            disabled={!currentDetection}
            variant="destructive"
            className="flex-1 py-2.5 font-medium rounded-lg flex items-center justify-center gap-2 transition-all active:scale-95 text-white shadow-lg"
          >
            <XCircle className="w-4 h-4" />
            Từ chối
          </Button>
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
        editVolume={editVolume}
        setEditVolume={setEditVolume}
        isVolumeEnabled={
          currentDetection?.is_checkout || 
          (() => {
            const loc = locations.find(l => l.name === currentGate);
            return loc?.tag !== "Cổng vào" && loc?.tag !== "Cơ bản";
          })()
        }
      />

      <EvidenceModal
        isOpen={showEvidenceModal}
        onClose={() => setShowEvidenceModal(false)}
        currentDetection={currentDetection}
        cameras={filteredCameras}
        cameraImages={capturedImages}
        snapshotUrl={snapshotUrl}
      />

    </div>
  );
}

export default function MonitorPage() {
  return (
    <Suspense
      fallback={
        <div className="h-full flex items-center justify-center">
          Loading...
        </div>
      }
    >
      <MonitorPageContent />
    </Suspense>
  );
}
