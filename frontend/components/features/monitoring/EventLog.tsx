import React, { useEffect, useCallback, useState } from "react";
import {
  FileText,
  PlayCircle,
  Move,
  ArrowUp,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  X,
  Gauge,
  Loader2,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import LogList, { LogEntry } from "./LogList";



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
  const [ptzSpeed, setPtzSpeed] = useState(50); // Speed from 1-100, default 50%

  // Convert percentage to actual speed (0.1 - 1.0)
  const getActualSpeed = useCallback(() => ptzSpeed / 100, [ptzSpeed]);

  const sendPtzCommand = useCallback(async (action: string) => {
    if (!activeMainCameraId) {
      toast.error("Camera chưa kết nối");
      return;
    }
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`/api/cameras/${activeMainCameraId}/ptz/${action}`, {
        method: "POST",
        headers: { 
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ speed: getActualSpeed() }),
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
  }, [activeMainCameraId, getActualSpeed]);

  const stopPtz = useCallback(async () => {
    if (!activeMainCameraId) return;
    try {
      const token = localStorage.getItem('token');
      await fetch(`/api/cameras/${activeMainCameraId}/ptz/stop`, {
        method: "POST",
        headers: { 
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        },
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
            <Move className="w-4 h-4 text-blue-500" />
          ) : (
            <FileText className="w-4 h-4 text-amber-500" />
          )}
          {showPtzPanel ? "Điều khiển PTZ" : "Nhật ký Sự kiện"}
        </div>
        
        {/* Cancel button for PTZ panel */}
        {showPtzPanel && (
          <Button
            onClick={onClosePtz}
            variant="ghost"
            size="icon"
            className="h-6 w-6 text-red-400 hover:text-red-300 hover:bg-red-500/20"
            title="Đóng PTZ"
          >
            <X className="w-4 h-4" />
          </Button>
        )}
      </div>

      {/* Content Area */}
      {showPtzPanel ? (
        /* PTZ Control Panel */
        <div className="flex-1 p-4 flex flex-col justify-between">
          <div className="flex-1 flex items-center justify-center">
             {/* Direction Controls - Square Layout */}
             <div className="grid grid-cols-3 gap-2 w-full max-w-[200px] aspect-square">
                <div />
                <button
                  onMouseDown={() => sendPtzCommand("up")}
                  onMouseUp={stopPtz}
                  onMouseLeave={stopPtz}
                  className={`aspect-square rounded-lg transition-colors flex items-center justify-center shadow-sm border border-border/50 ${
                    activeKey === "ArrowUp" 
                      ? "bg-amber-500 text-black scale-95" 
                      : "bg-muted hover:bg-amber-500 hover:text-black active:scale-95"
                  }`}
                >
                  <ArrowUp className="w-6 h-6" />
                </button>
                <div />

                <button
                  onMouseDown={() => sendPtzCommand("left")}
                  onMouseUp={stopPtz}
                  onMouseLeave={stopPtz}
                  className={`aspect-square rounded-lg transition-colors flex items-center justify-center shadow-sm border border-border/50 ${
                    activeKey === "ArrowLeft" 
                      ? "bg-amber-500 text-black scale-95" 
                      : "bg-muted hover:bg-amber-500 hover:text-black active:scale-95"
                  }`}
                >
                  <ArrowLeft className="w-6 h-6" />
                </button>
                <div className="aspect-square bg-muted/20 rounded-lg flex items-center justify-center border border-border/30">
                  <Move className="w-6 h-6 text-muted-foreground/50" />
                </div>
                <button
                  onMouseDown={() => sendPtzCommand("right")}
                  onMouseUp={stopPtz}
                  onMouseLeave={stopPtz}
                  className={`aspect-square rounded-lg transition-colors flex items-center justify-center shadow-sm border border-border/50 ${
                    activeKey === "ArrowRight" 
                      ? "bg-amber-500 text-black scale-95" 
                      : "bg-muted hover:bg-amber-500 hover:text-black active:scale-95"
                  }`}
                >
                  <ArrowRight className="w-6 h-6" />
                </button>

                <div />
                <button
                  onMouseDown={() => sendPtzCommand("down")}
                  onMouseUp={stopPtz}
                  onMouseLeave={stopPtz}
                  className={`aspect-square rounded-lg transition-colors flex items-center justify-center shadow-sm border border-border/50 ${
                    activeKey === "ArrowDown" 
                      ? "bg-amber-500 text-black scale-95" 
                      : "bg-muted hover:bg-amber-500 hover:text-black active:scale-95"
                  }`}
                >
                  <ArrowDown className="w-6 h-6" />
                </button>
                <div />
             </div>
          </div>

          {/* Speed Control Slider */}
          <div className="bg-muted/30 rounded-lg p-3 mt-4">
            <div className="flex items-center gap-3">
              <Gauge className="text-amber-500 w-4 h-4 flex-shrink-0" />
              <div className="flex-1 relative h-6 flex items-center">
                {/* Track background */}
                <div className="absolute inset-x-0 h-1 bg-muted-foreground/30 rounded-full" />
                {/* Filled track */}
                <div 
                  className="absolute left-0 h-1 bg-amber-500 rounded-full transition-all"
                  style={{ width: `${((ptzSpeed - 10) / 90) * 100}%` }}
                />
                {/* Range input */}
                <input
                  type="range"
                  min="10"
                  max="100"
                  step="10"
                  value={ptzSpeed}
                  onChange={(e) => setPtzSpeed(Number(e.target.value))}
                  className="absolute inset-0 w-full opacity-0 cursor-pointer z-10"
                />
                {/* Custom thumb */}
                <div 
                  className="absolute w-4 h-4 bg-amber-500 rounded-full shadow-lg border-2 border-background cursor-pointer pointer-events-none transition-all hover:scale-110"
                  style={{ left: `calc(${((ptzSpeed - 10) / 90) * 100}% - 8px)` }}
                />
              </div>
              <div className="bg-amber-500 text-black text-xs font-bold px-2 py-1 rounded-md min-w-[42px] text-center flex-shrink-0">
                {ptzSpeed}%
              </div>
            </div>
          </div>

          {/* Keyboard hints */}
          <div className="bg-muted/30 rounded-lg p-2 text-center mt-2">
            <p className="text-[10px] text-muted-foreground">
              <span className="font-bold">Bàn phím:</span> Sử dụng phím mũi tên ← ↑ → ↓
            </p>
          </div>
        </div>
      ) : (
        /* Event Log */
        /* Event Log */
        <LogList logs={logs} />
      )}

      {/* CONTROL PANEL */}
      <div className="p-3 border-t border-border bg-muted/10 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-muted-foreground">
            Tự động phát hiện
          </span>
          <Switch
            checked={isAutoDetect}
            onCheckedChange={setIsAutoDetect}
            className="data-[state=checked]:bg-[#f59e0b]"
          />
        </div>

        <Button
          onClick={handleManualDetection}
          disabled={isProcessing || !currentGate}
          className="w-full"
          variant={isProcessing ? "secondary" : "default"}
        >
          {isProcessing ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin text-amber-500" />
              ĐANG XỬ LÝ...
            </>
          ) : (
            <>
              <PlayCircle className="w-4 h-4 mr-2" />
              KÍCH HOẠT THỦ CÔNG
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
