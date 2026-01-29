"use client";

import React, { useState, useEffect } from "react";
import { Search, Refresh, EventNote } from "@mui/icons-material";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

interface LogEntry {
  timestamp: string;
  camera_name: string;
  camera_id?: string;
  event_type: string;
  details: string;
}

export default function LogsPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [loading, setLoading] = useState(false);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch("/api/cameras/logs", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setLogs(await res.json());
      } else {
        toast.error("Không thể tải nhật ký");
      }
    } catch (error) {
      console.error("Failed to fetch logs", error);
      toast.error("Lỗi kết nối máy chủ");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  const filteredLogs = logs.filter((log) => {
    const s = searchTerm.toLowerCase();
    return (
      log.camera_id.toLowerCase().includes(s) ||
      log.event_type.toLowerCase().includes(s) ||
      log.details.toLowerCase().includes(s)
    );
  }).reverse(); // Latest logs first

  return (
    <div className="h-full flex flex-col overflow-hidden bg-background">
      <div className="max-w-[1500px] w-full mx-auto flex-1 flex flex-col p-6 gap-4 min-h-0">
        <div className="flex justify-between items-center shrink-0">
          <h1 className="text-2xl font-bold tracking-tight">
            Nhật ký hệ thống
          </h1>
          <div className="flex items-center gap-3">
            <div className="relative group min-w-[300px]">
              <Search
                className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-[#f59e0b] transition-colors"
                fontSize="small"
              />
              <input
                className="w-full pl-10 pr-4 py-2 bg-card border border-border rounded-md text-sm outline-none focus:outline-none focus:ring-1 focus:ring-[#f59e0b] focus:border-[#f59e0b] transition-all"
                placeholder="Tìm kiếm nhật ký..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <button
              onClick={fetchLogs}
              disabled={loading}
              className="px-4 py-2 bg-card border border-border rounded-md text-sm font-bold flex items-center gap-2 hover:bg-muted transition-all hover:text-[#f59e0b]"
            >
              <Refresh fontSize="small" className={`${loading ? 'animate-spin' : ''} text-[#f59e0b]`} />
              Làm mới
            </button>
          </div>
        </div>

        <div className="border border-border rounded-lg bg-card overflow-hidden flex-1 flex flex-col min-h-0">
          <div className="flex-1 overflow-auto scrollbar-show-always">
            <table className="text-sm text-left border-collapse w-full min-w-max">
              <thead className="text-[10px] uppercase text-muted-foreground font-bold sticky top-0 bg-muted/95 backdrop-blur-sm z-20 border-b border-border">
                <tr>
                  <th className="px-4 py-3 w-[200px]">Thời gian</th>
                  <th className="px-4 py-3 w-[350px]">Tên Camera</th>
                  <th className="px-4 py-3 w-[250px]">Sự kiện</th>
                  <th className="px-4 py-3">Chi tiết</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredLogs.map((log, i) => (
                  <tr key={i} className="hover:bg-muted/5 transition-colors">
                    <td className="px-4 py-2.5 text-xs text-foreground font-medium">
                      {log.timestamp}
                    </td>
                    <td className="px-4 py-2.5 text-xs font-bold text-[#f59e0b]">
                      {log.camera_name || log.camera_id}
                    </td>
                    <td className="px-4 py-2.5 text-xs font-semibold">
                      <span className={`px-2 py-0.5 rounded ${
                        log.event_type.includes('Error') || log.event_type.includes('Failure') 
                        ? 'bg-red-500/10 text-red-500' 
                        : log.event_type.includes('Warning')
                        ? 'bg-amber-500/10 text-amber-500'
                        : log.event_type.includes('Success') || log.event_type.includes('Started')
                        ? 'bg-green-500/10 text-green-500'
                        : 'bg-blue-500/10 text-blue-500'
                      }`}>
                        {log.event_type}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-xs text-muted-foreground">
                      {log.details}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filteredLogs.length === 0 && (
              <div className="p-12 text-center text-muted-foreground italic">
                {loading ? "Đang tải..." : "Chưa có nhật ký nào"}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
