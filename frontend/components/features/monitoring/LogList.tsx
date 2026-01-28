import React from "react";

export interface LogEntry {
  time: string;
  message: string;
  type: "info" | "success" | "warning" | "error";
}

interface LogListProps {
  logs: LogEntry[];
}

const LogList = React.memo(({ logs }: LogListProps) => {
  return (
    <div className="flex-1 overflow-y-auto p-2 font-mono text-xs space-y-1 scrollbar-hide">
      {logs.length === 0 && (
        <div className="text-center text-muted-foreground italic text-[10px] py-4 opacity-50">
          Chưa có sự kiện nào
        </div>
      )}
      {logs.map((log, i) => (
        <div
          key={i} // Using index as key because logs are prepended and we don't have IDs
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
  );
});

LogList.displayName = "LogList";

export default LogList;
