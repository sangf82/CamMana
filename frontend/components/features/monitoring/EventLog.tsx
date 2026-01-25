import React, { useEffect, useCallback } from "react";
import {
  EventNote,
  ToggleOn,
  ToggleOff,
  PlayCircle,
  ControlCamera,
  ArrowUpward,
  ArrowDownward,
  ArrowBack,
  ArrowForward,
  ZoomIn,
  ZoomOut,
  Close,
} from "@mui/icons-material";
import { toast } from "sonner";

interface LogEntry {
  time: string;
  message: string;
  type: "info" | "success" | "warning" | "error";
}

interface EventLogProps {
  logs: LogEntry[];
  isAutoDetect: boolean;
  setIsAutoDetect: (value: boolean) => void;
  handleManualDetection: () => void;
  isProcessing: boolean;
  currentGate: string;
  activeMainCameraId?: string;
  showPtzPanel: boolean;
  onClosePtz: () => void;
}

export default function EventLog({
  logs,
  isAutoDetect,
  setIsAutoDetect,
  handleManualDetection,
  isProcessing,
  currentGate,
  activeMainCameraId,
  showPtzPanel,
  onClosePtz,
}: EventLogProps) {
  const [activeKey, setActiveKey] = React.useState<string | null>(null);

  const sendPtzCommand = useCallback(async (action: string) => {
    if (!activeMainCameraId) {
      toast.error("Camera chưa kết nối");
      return;
    }
    try {
      const res = await fetch(`/api/cameras/${activeMainCameraId}/ptz/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ speed: 0.5 }),
      });
      if (res.ok) {
        const data = await res.json();
        if (!data.success && data.error) {
          toast.error(`PTZ: ${data.error}`);
        }
      } else {
        const errData = await res.json().catch(() => ({}));
        toast.error(errData?.detail || "Lỗi điều khiển PTZ");
      }
    } catch (e) {
      toast.error("Lỗi kết nối PTZ");
    }
  }, [activeMainCameraId]);

  const stopPtz = useCallback(async () => {
    if (!activeMainCameraId) return;
    try {
      await fetch(`/api/cameras/${activeMainCameraId}/ptz/stop`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ speed: 0 }),
      });
    } catch (e) {
      // Ignore stop errors
    }
  }, [activeMainCameraId]);

  // Keyboard support for PTZ
  useEffect(() => {
    if (!showPtzPanel) return;

    const keyActionMap: Record<string, string> = {
      ArrowUp: "up",
      ArrowDown: "down",
      ArrowLeft: "left",
      ArrowRight: "right",
      "+": "zoom_in",
      "=": "zoom_in",
      "-": "zoom_out",
      "_": "zoom_out",
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      const action = keyActionMap[e.key];
      if (action && !activeKey) {
        e.preventDefault();
        setActiveKey(e.key);
        sendPtzCommand(action);
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      const action = keyActionMap[e.key];
      if (action) {
        e.preventDefault();
        setActiveKey(null);
        stopPtz();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
    };
  }, [showPtzPanel, activeKey, sendPtzCommand, stopPtz]);

  return (
    <div className="w-72 bg-card border border-border rounded-lg flex flex-col shrink-0">
      {/* Header */}
      <div className="p-3 border-b border-border bg-muted/20 font-semibold text-sm flex items-center justify-between">
        <div className="flex items-center gap-2">
          {showPtzPanel ? (
            <ControlCamera fontSize="small" className="text-blue-500" />
          ) : (
            <EventNote fontSize="small" className="text-primary" />
          )}
          {showPtzPanel ? "Điều khiển PTZ" : "Nhật ký Sự kiện"}
        </div>
        
        {/* Cancel button for PTZ panel */}
        {showPtzPanel && (
          <button
            onClick={onClosePtz}
            className="p-1 hover:bg-red-500/20 text-red-400 hover:text-red-300 rounded-full transition-colors"
            title="Đóng PTZ"
          >
            <Close fontSize="small" />
          </button>
        )}
      </div>

      {/* Content Area */}
      {showPtzPanel ? (
        /* PTZ Control Panel */
        <div className="flex-1 p-4 flex flex-col justify-center">
          {/* Direction Controls */}
          <div className="grid grid-cols-3 gap-2 mb-4">
            <div />
            <button
              onMouseDown={() => sendPtzCommand("up")}
              onMouseUp={stopPtz}
              onMouseLeave={stopPtz}
              className={`p-3 rounded-lg transition-colors flex items-center justify-center ${
                activeKey === "ArrowUp" 
                  ? "bg-primary text-black" 
                  : "bg-muted hover:bg-primary hover:text-black"
              }`}
            >
              <ArrowUpward />
            </button>
            <div />

            <button
              onMouseDown={() => sendPtzCommand("left")}
              onMouseUp={stopPtz}
              onMouseLeave={stopPtz}
              className={`p-3 rounded-lg transition-colors flex items-center justify-center ${
                activeKey === "ArrowLeft" 
                  ? "bg-primary text-black" 
                  : "bg-muted hover:bg-primary hover:text-black"
              }`}
            >
              <ArrowBack />
            </button>
            <div className="p-3 bg-muted/50 rounded-lg flex items-center justify-center">
              <ControlCamera className="text-muted-foreground" />
            </div>
            <button
              onMouseDown={() => sendPtzCommand("right")}
              onMouseUp={stopPtz}
              onMouseLeave={stopPtz}
              className={`p-3 rounded-lg transition-colors flex items-center justify-center ${
                activeKey === "ArrowRight" 
                  ? "bg-primary text-black" 
                  : "bg-muted hover:bg-primary hover:text-black"
              }`}
            >
              <ArrowForward />
            </button>

            <div />
            <button
              onMouseDown={() => sendPtzCommand("down")}
              onMouseUp={stopPtz}
              onMouseLeave={stopPtz}
              className={`p-3 rounded-lg transition-colors flex items-center justify-center ${
                activeKey === "ArrowDown" 
                  ? "bg-primary text-black" 
                  : "bg-muted hover:bg-primary hover:text-black"
              }`}
            >
              <ArrowDownward />
            </button>
            <div />
          </div>

          {/* Zoom Controls */}
          <div className="flex gap-2 mb-4">
            <button
              onMouseDown={() => sendPtzCommand("zoom_out")}
              onMouseUp={stopPtz}
              onMouseLeave={stopPtz}
              className={`flex-1 p-3 rounded-lg transition-colors flex items-center justify-center gap-2 ${
                activeKey === "-" || activeKey === "_"
                  ? "bg-primary text-black" 
                  : "bg-muted hover:bg-primary hover:text-black"
              }`}
            >
              <ZoomOut fontSize="small" /> Thu nhỏ
            </button>
            <button
              onMouseDown={() => sendPtzCommand("zoom_in")}
              onMouseUp={stopPtz}
              onMouseLeave={stopPtz}
              className={`flex-1 p-3 rounded-lg transition-colors flex items-center justify-center gap-2 ${
                activeKey === "+" || activeKey === "="
                  ? "bg-primary text-black" 
                  : "bg-muted hover:bg-primary hover:text-black"
              }`}
            >
              <ZoomIn fontSize="small" /> Phóng to
            </button>
          </div>

          {/* Keyboard hints */}
          <div className="bg-muted/30 rounded-lg p-3 text-center">
            <p className="text-[10px] text-muted-foreground mb-1">
              <span className="font-bold">Bàn phím:</span> Mũi tên ← ↑ → ↓
            </p>
            <p className="text-[10px] text-muted-foreground">
              <span className="font-bold">Zoom:</span> + / - 
            </p>
          </div>
        </div>
      ) : (
        /* Event Log */
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
              <span className="text-[10px] opacity-60">{log.time}</span>{" "}
              {log.message}
            </div>
          ))}
        </div>
      )}

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
  );
}
