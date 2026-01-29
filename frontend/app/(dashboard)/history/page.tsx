"use client";

import React, { useState, useEffect } from "react";
import DataTable from "../../../components/ui/data-table";
import {
  FilterList,
  Download,
  Search,
  Close,
  ExpandMore,
  ChevronRight,
  ChevronLeft,
  CalendarMonth,
  CheckCircle,
} from "@mui/icons-material";
import { toast } from "sonner";
import { LoadingPanel } from "@/components/ui/loading-spinner";

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  // Primary flow statuses (Trạng thái)
  "vào cổng": { label: "Vào cổng", color: "bg-blue-500/20 text-blue-400" },
  "đã vào": { label: "Đã vào", color: "bg-indigo-500/20 text-indigo-400" },
  "đang cân": { label: "Đang cân", color: "bg-yellow-500/20 text-yellow-400" },
  "ra cổng": { label: "Ra cổng", color: "bg-orange-500/20 text-orange-400" },
  "đã ra": { label: "Đã ra", color: "bg-green-500/20 text-green-400" },
  "xe ra lạ": { label: "Xe ra lạ", color: "bg-rose-500/20 text-rose-400" },
  "check-in pending": { label: "Check-In Pending", color: "bg-slate-500/20 text-slate-400" },
  
  // Mixed case fallback
  "Vào cổng": { label: "Vào cổng", color: "bg-blue-500/20 text-blue-400" },
  "Đã vào": { label: "Đã vào", color: "bg-indigo-500/20 text-indigo-400" },
  "Đang cân": { label: "Đang cân", color: "bg-yellow-500/20 text-yellow-400" },
  "Ra cổng": { label: "Ra cổng", color: "bg-orange-500/20 text-orange-400" },
  "Đã ra": { label: "Đã ra", color: "bg-green-500/20 text-green-400" },
  "Xe ra lạ": { label: "Xe ra lạ", color: "bg-rose-500/20 text-rose-400" },
  "Check-In Pending": { label: "Check-In Pending", color: "bg-slate-500/20 text-slate-400" },
};

const VERIFY_MAP: Record<string, { label: string; color: string }> = {
  // Primary verify statuses (Xác minh)
  "đã xác minh": { label: "Đã XM", color: "bg-emerald-500/20 text-emerald-400" },
  "chưa xác minh": { label: "Chưa XM", color: "bg-amber-500/20 text-amber-400" },
  "cần kt": { label: "Cần KT", color: "bg-orange-500/20 text-orange-400" },
  "xe lạ": { label: "Xe lạ", color: "bg-rose-500/20 text-rose-400" },
  "xe chưa đk": { label: "Xe chưa ĐK", color: "bg-red-500/20 text-red-400" },
  "từ chối": { label: "Từ chối", color: "bg-red-500/20 text-red-500" },

  // Mixed case fallback
  "Đã xác minh": { label: "Đã XM", color: "bg-emerald-500/20 text-emerald-400" },
  "Chưa xác minh": { label: "Chưa XM", color: "bg-amber-500/20 text-amber-400" },
  "Cần KT": { label: "Cần KT", color: "bg-orange-500/20 text-orange-400" },
  "Xe lạ": { label: "Xe lạ", color: "bg-rose-500/20 text-rose-400" },
  "Xe chưa ĐK": { label: "Xe chưa ĐK", color: "bg-red-500/20 text-red-400" },
  "Từ chối": { label: "Từ chối", color: "bg-red-500/20 text-red-500" },
};

export default function HistoryPage() {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterGate, setFilterGate] = useState("All");
  const [filterStatus, setFilterStatus] = useState("All");
  
  // Date selection
  const [availableDates, setAvailableDates] = useState<string[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>("");
  const [isDateDropdownOpen, setIsDateDropdownOpen] = useState(false);

  // Pending states for filters
  const [pendingFilterGate, setPendingFilterGate] = useState("All");
  const [pendingFilterStatus, setPendingFilterStatus] = useState("All");

  const [showFilters, setShowFilters] = useState(false);
  const [isGateOpen, setIsGateOpen] = useState(false);
  const [isStatusOpen, setIsStatusOpen] = useState(false);

  // Fetch history data & dates
  useEffect(() => {
    fetchDates();
    fetchHistory();
  }, []);

  const fetchDates = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch("/api/history/dates", {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const dates = await response.json();
        setAvailableDates(dates);
      }
    } catch (e) { console.error(e); }
  };

  const fetchHistory = async (date?: string) => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const url = date ? `/api/history?date=${date}` : "/api/history";
      const response = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (!response.ok) {
          const err = await response.json().catch(() => ({ detail: "Unknown error" }));
          toast.error(err.detail || "Không thể tải lịch sử");
          setData([]);
          return;
      }

      const result = await response.json();
      if (Array.isArray(result)) {
        setData(result);
      } else if (result.success && result.data) {
        setData(result.data);
      } else {
        setData([]);
      }
    } catch (error) {
      console.error("Error fetching history:", error);
      toast.error("Lỗi kết nối");
    } finally {
      setLoading(false);
    }
  };

  const handleDateChange = (date: string) => {
    setSelectedDate(date);
    fetchHistory(date);
    setIsDateDropdownOpen(false);
  };

  // Sync pending filters when opening
  useEffect(() => {
    if (showFilters) {
      setPendingFilterGate(filterGate);
      setPendingFilterStatus(filterStatus);
    }
  }, [showFilters]);

  const handleApplyFilters = () => {
    setFilterGate(pendingFilterGate);
    setFilterStatus(pendingFilterStatus);
    // Optional: setShowFilters(false) if you want it to close on apply
  };

  const [showScrollTop, setShowScrollTop] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setShowScrollTop(window.scrollY > 300);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const today = new Date().toLocaleDateString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).replace(/\//g, '-');

  const gates = [
    "All",
    ...Array.from(new Set(data.map((d) => d.location?.trim() || "None"))),
  ];
  const statuses = [
    "All",
    ...Array.from(new Set(data.map((d) => d.status?.trim() || "None"))),
  ];

  const filteredData = data.filter((item) => {
    const matchesSearch = (item.plate ?? "")
      .toLowerCase()
      .includes(searchTerm.toLowerCase());
    const matchesGate =
      filterGate === "All" || (item.location?.trim() || "None") === filterGate;
    const matchesStatus =
      filterStatus === "All" ||
      (item.status?.trim() || "None") === filterStatus;
    return matchesSearch && matchesGate && matchesStatus;
  });

  const columns = [
    { header: "Biển số", accessorKey: "plate", width: "120px" },
    { header: "Vị trí", accessorKey: "location", width: "180px" },
    { header: "Thời gian Vào", accessorKey: "time_in", width: "120px" },
    { header: "Thời gian Ra", accessorKey: "time_out", width: "120px" },
    {
      header: "Thể tích tiêu chuẩn (m³)",
      accessorKey: "vol_std",
      width: "150px",
    },
    {
      header: "Thể tích đo được (m³)",
      accessorKey: "vol_measured",
      width: "150px",
    },
    {
      header: "Trạng thái",
      width: "120px",
      render: (row: any) => {
        const config = STATUS_MAP[row.status] || {
          label: row.status,
          color: "bg-muted text-muted-foreground",
        };
        return (
          <span
            className={`inline-block px-2 py-1 rounded text-[10px] font-bold ${config.color}`}
          >
            {config.label}
          </span>
        );
      },
    },
    {
      header: "Xác minh",
      width: "120px",
      render: (row: any) => {
        const config = VERIFY_MAP[row.verify] || {
          label: row.verify,
          color: "bg-muted text-muted-foreground",
        };
        return (
          <span
            className={`inline-block px-2 py-1 rounded text-[10px] font-bold ${config.color} whitespace-nowrap`}
          >
            {config.label}
          </span>
        );
      },
    },
    { header: "Ghi chú", accessorKey: "note", width: "300px" },
  ];

  const handleExportExcel = async () => {
    if (filteredData.length === 0) {
      toast.error("Không có dữ liệu để xuất");
      return;
    }

    try {
      const token = localStorage.getItem('token');
      const dateParam = (selectedDate || today).replace(/\//g, '-');
      
      // Try to save directly to Downloads folder (desktop app mode)
      const saveResponse = await fetch(`/api/history/export/excel/save?date=${dateParam}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (saveResponse.ok) {
        const result = await saveResponse.json();
        toast.success(`Đã lưu vào: ${result.file_path}`);
        return;
      }
      
      // Check if no data on backend
      if (saveResponse.status === 404) {
        toast.error("Không có dữ liệu để xuất");
        return;
      }
      
      // Fallback to browser download if save fails
      const response = await fetch(`/api/history/export/excel?date=${dateParam}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.status === 404) {
        toast.error("Không có dữ liệu để xuất");
        return;
      }
      
      if (!response.ok) throw new Error('Export failed');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Lich_su_ra_vao_${dateParam}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success("Đã tải xuống danh sách lịch sử");
    } catch (e) {
      console.error('Export Error:', e);
      toast.error('Lỗi khi xuất file');
    }
  };

  return (
    <div className="h-full flex flex-col overflow-hidden bg-background">
      <div className="max-w-[1500px] w-full mx-auto flex-1 flex flex-col p-6 gap-4 min-h-0">
      {/* Header Section */}
      <div className="flex justify-between items-center shrink-0">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight">
              Lịch sử Ra Vào
            </h1>
            <div className="relative">
              <button 
                onClick={() => setIsDateDropdownOpen(!isDateDropdownOpen)}
                className="flex items-center gap-2 bg-card border border-border px-3 py-1 rounded text-sm font-bold text-[#f59e0b] shadow-sm hover:border-[#f59e0b] transition-all min-w-[140px] justify-between"
              >
                <div className="flex items-center gap-2">
                  <CalendarMonth fontSize="small" />
                  <span>{selectedDate || today}</span>
                </div>
                <ExpandMore className={` transition-transform duration-200 ${isDateDropdownOpen ? 'rotate-180' : ''}`} fontSize="small" />
              </button>
              
              {isDateDropdownOpen && (
                <div className="absolute top-full left-0 mt-1 w-full z-[100] bg-popover text-popover-foreground border border-border rounded-xl shadow-2xl p-1 max-h-56 overflow-y-auto animate-in fade-in slide-in-from-top-1 duration-200">
                  {availableDates.map(date => (
                    <button 
                      key={date} 
                      onClick={() => handleDateChange(date)}
                      className={`w-full text-left px-3 py-2 rounded-lg text-xs font-medium transition-colors hover:bg-[#f59e0b]/10 flex items-center justify-between ${selectedDate === date || (selectedDate === "" && date === today) ? "text-[#f59e0b] bg-[#f59e0b]/5" : "text-muted-foreground"}`}
                    >
                      <span>{date}{date === today ? " (Hôm nay)" : ""}</span>
                      {(selectedDate === date || (selectedDate === "" && date === today)) && <CheckCircle sx={{ fontSize: 14 }} />}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Search Bar */}
          <div className="relative group min-w-[300px]">
            <Search
              className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-[#f59e0b] transition-colors"
              fontSize="small"
            />
            <input
              type="text"
              placeholder="Tìm kiếm biển số..."
              className="w-full pl-10 pr-4 py-2 bg-card border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-[#f59e0b] focus:border-[#f59e0b] transition-all text-sm"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`pl-3 pr-1 py-2 border rounded-md text-sm font-bold flex items-center gap-1 transition-all shadow-sm
                    ${
                      showFilters ||
                      filterGate !== "All" ||
                      filterStatus !== "All"
                        ? "bg-[#f59e0b] text-black border-[#f59e0b] shadow-[#f59e0b]/20"
                        : "bg-card border-border text-foreground hover:bg-muted"
                    }`}
          >
            Lọc
            <div
              className={`transition-transform duration-200 ${
                showFilters ? "-rotate-90" : ""
              }`}
            >
              <ChevronLeft fontSize="small" />
            </div>
          </button>

          <button
            onClick={handleExportExcel}
            className="px-4 py-2 bg-card border border-border text-foreground hover:bg-muted rounded-md text-sm font-bold flex items-center gap-2 transition-all shadow-sm"
          >
            <Download fontSize="small" /> Xuất Excel
          </button>
        </div>
      </div>

      {/* Compact Filter Bar */}
      {showFilters && (
        <div className="flex flex-wrap items-center gap-6 py-2 px-4 bg-muted/20 border border-border rounded-lg animate-in fade-in slide-in-from-top-2 duration-200">
          {/* Location Selector */}
          <div className="flex items-center gap-3">
            <label className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest whitespace-nowrap">
              Vị trí (Gate)
            </label>
            <div className="relative">
              <button
                onClick={() => {
                  setIsGateOpen(!isGateOpen);
                  setIsStatusOpen(false);
                }}
                className="w-full flex items-center justify-between min-w-[180px] px-3 py-1.5 bg-background border border-border rounded-md text-sm font-semibold focus:border-[#f59e0b] transition-all"
              >
                <span>
                  {pendingFilterGate === "All"
                    ? "Tất cả vị trí"
                    : pendingFilterGate}
                </span>
                <ExpandMore
                  className={`transition-transform duration-200 ${isGateOpen ? "rotate-180" : ""}`}
                  fontSize="small"
                />
              </button>
              {isGateOpen && (
                <div className="absolute top-full left-0 w-full z-[100] mt-1 bg-popover text-popover-foreground border border-border rounded-xl shadow-2xl p-1 max-h-56 overflow-y-auto animate-in fade-in slide-in-from-top-1 duration-200">
                  {gates.map((g) => (
                    <button
                      key={g}
                      onClick={() => {
                        setPendingFilterGate(g);
                        setIsGateOpen(false);
                      }}
                      className={`w-full text-left px-3 py-2 rounded-lg text-xs font-medium transition-colors hover:bg-[#f59e0b]/10 ${pendingFilterGate === g ? "text-[#f59e0b] bg-[#f59e0b]/5" : "text-muted-foreground"}`}
                    >
                      {g === "All" ? "Tất cả vị trí" : g}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Status Selector */}
          <div className="flex items-center gap-3">
            <label className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest whitespace-nowrap">
              Trạng thái
            </label>
            <div className="relative">
              <button
                onClick={() => {
                  setIsStatusOpen(!isStatusOpen);
                  setIsGateOpen(false);
                }}
                className="w-full flex items-center justify-between min-w-[180px] px-3 py-1.5 bg-background border border-border rounded-md text-sm font-semibold focus:border-[#f59e0b] transition-all"
              >
                <span>
                  {pendingFilterStatus === "All"
                    ? "Tất cả trạng thái"
                    : STATUS_MAP[pendingFilterStatus]?.label ||
                      pendingFilterStatus}
                </span>
                <ExpandMore
                  className={`transition-transform duration-200 ${isStatusOpen ? "rotate-180" : ""}`}
                  fontSize="small"
                />
              </button>
              {isStatusOpen && (
                <div className="absolute top-full left-0 w-full z-[100] mt-1 bg-popover text-popover-foreground border border-border rounded-xl shadow-2xl p-1 max-h-56 overflow-y-auto animate-in fade-in slide-in-from-top-1 duration-200">
                  {statuses.map((s) => (
                    <button
                      key={s}
                      onClick={() => {
                        setPendingFilterStatus(s);
                        setIsStatusOpen(false);
                      }}
                      className={`w-full text-left px-3 py-2 rounded-lg text-xs font-medium transition-colors hover:bg-[#f59e0b]/10 ${pendingFilterStatus === s ? "text-[#f59e0b] bg-[#f59e0b]/5" : "text-muted-foreground"}`}
                    >
                      {s === "All"
                        ? "Tất cả trạng thái"
                        : STATUS_MAP[s]?.label || s}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-3 ml-auto">
            {(filterGate !== "All" ||
              filterStatus !== "All" ||
              searchTerm !== "") && (
              <button
                onClick={() => {
                  setFilterGate("All");
                  setFilterStatus("All");
                  setPendingFilterGate("All");
                  setPendingFilterStatus("All");
                  setSearchTerm("");
                }}
                className="text-xs text-red-400 hover:text-red-300 font-bold px-2 py-1 transition-colors"
              >
                Xóa lọc
              </button>
            )}
            <button
              onClick={handleApplyFilters}
              className="px-6 py-1.5 bg-[#f59e0b] text-black text-sm font-bold rounded-md hover:bg-[#f59e0b]/90 transition-all shadow-lg shadow-[#f59e0b]/20 active:scale-95"
            >
              Áp dụng
            </button>
          </div>
        </div>
      )}

      {/* Table Section */}
      <div className="border border-border rounded-lg bg-card overflow-hidden flex-1 flex flex-col min-h-0">
        {/* Unified Scroll Container */}
        <div className="flex-1 overflow-y-scroll overflow-x-auto scrollbar-show-always min-h-0">
          <table className="text-sm text-left border-collapse table-fixed w-fit min-w-full">
            {/* Sticky Header */}
            <thead className="text-[10px] uppercase text-muted-foreground font-bold sticky top-0 bg-muted/90 backdrop-blur-md z-20 border-b border-border">
              <tr>
                {columns.map((col, idx) => (
                  <th
                    key={idx}
                    className="px-4 py-3 whitespace-nowrap"
                    style={{ width: col.width || "auto" }}
                  >
                    {typeof (col.header as any) === "function"
                      ? (col.header as any)()
                      : col.header}
                  </th>
                ))}
              </tr>
            </thead>

            {/* Data Body */}
            <tbody className="divide-y divide-border">
              {loading ? (
                <tr>
                  <td
                    colSpan={columns.length}
                    className="px-4 py-12 text-center text-muted-foreground font-medium"
                  >
                    <div className="flex flex-col items-center gap-2">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#f59e0b]"></div>
                      <span>Đang tải dữ liệu...</span>
                    </div>
                  </td>
                </tr>
              ) : filteredData.length > 0 ? (
                filteredData.map((row, rowIdx) => (
                  <tr
                    key={rowIdx}
                    className="bg-card hover:bg-muted/5 transition-colors"
                  >
                    {columns.map((col, colIdx) => (
                      <td
                        key={colIdx}
                        className="px-4 py-2.5 whitespace-nowrap text-foreground font-medium text-xs truncate"
                        style={{ width: col.width || "auto" }}
                      >
                        {col.render
                          ? col.render(row)
                          : (row as any)[col.accessorKey!]}
                      </td>
                    ))}
                  </tr>
                ))
              ) : (
                <tr>
                  <td
                    colSpan={columns.length}
                    className="px-4 py-12 text-center text-muted-foreground font-medium"
                  >
                    Không có dữ liệu
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Floating Scroll to Top Button */}
      {showScrollTop && (
        <button
          onClick={scrollToTop}
          className="fixed bottom-10 left-1/2 -translate-x-1/2 p-2 bg-[#f59e0b] text-black rounded-full shadow-lg hover:bg-[#f59e0b]/90 transition-all animate-in fade-in zoom-in duration-300 z-50 flex items-center justify-center border border-[#f59e0b]/20"
          aria-label="Back to top"
        >
          <ChevronRight className="-rotate-90" fontSize="medium" />
        </button>
      )}
      </div>
    </div>
  )
}
