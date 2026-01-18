import React from "react";
import {
  EventNote,
  ToggleOn,
  ToggleOff,
  PlayCircle,
} from "@mui/icons-material";

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
}

export default function EventLog({
  logs,
  isAutoDetect,
  setIsAutoDetect,
  handleManualDetection,
  isProcessing,
  currentGate,
}: EventLogProps) {
  return (
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
            <span className="text-[10px] opacity-60">{log.time}</span>{" "}
            {log.message}
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
  );
}
