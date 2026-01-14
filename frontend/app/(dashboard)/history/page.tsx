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
  ExpandLess,
} from "@mui/icons-material";
import { toast } from "sonner";

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  "đang vào": { label: "Đang vào", color: "bg-blue-500/20 text-blue-400" },
  "đã vào": { label: "Đã vào", color: "bg-indigo-500/20 text-indigo-400" },
  "đang cân": { label: "Đang cân", color: "bg-yellow-500/20 text-yellow-400" },
  "đang ra": { label: "Đang ra", color: "bg-orange-500/20 text-orange-400" },
  "đã ra": { label: "Đã ra", color: "bg-green-500/20 text-green-400" },
};

const VERIFY_MAP: Record<string, { label: string; color: string }> = {
  "đã xác nhận": {
    label: "Đã xác nhận",
    color: "bg-emerald-500/20 text-emerald-400",
  },
  "ngoài danh sách": {
    label: "Ngoài DS",
    color: "bg-rose-500/20 text-rose-400",
  },
};

export default function HistoryPage() {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterGate, setFilterGate] = useState("All");
  const [filterStatus, setFilterStatus] = useState("All");

  // Pending states for filters
  const [pendingFilterGate, setPendingFilterGate] = useState("All");
  const [pendingFilterStatus, setPendingFilterStatus] = useState("All");

  const [showFilters, setShowFilters] = useState(false);
  const [isGateOpen, setIsGateOpen] = useState(false);
  const [isStatusOpen, setIsStatusOpen] = useState(false);

  // Fetch history data from API
  useEffect(() => {
    const fetchHistory = async () => {
      try {
        setLoading(true);
        const response = await fetch("http://localhost:8000/api/history");
        const result = await response.json();

        if (result.success && result.data) {
          setData(result.data);
        } else {
          toast.error("Không thể tải dữ liệu lịch sử");
        }
      } catch (error) {
        console.error("Error fetching history:", error);
        toast.error("Lỗi kết nối đến server");
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, []);

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
  });

  // Extract unique gates and statuses from data
  const gates = [
    "All",
    ...Array.from(new Set(data.map((d) => d.location).filter(Boolean))),
  ];
  const statuses = ["All", ...Object.keys(STATUS_MAP)];

  const filteredData = data.filter((item) => {
    const matchesSearch = item.plate
      .toLowerCase()
      .includes(searchTerm.toLowerCase());
    const matchesGate = filterGate === "All" || item.location === filterGate;
    const matchesStatus =
      filterStatus === "All" || item.status === filterStatus;
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

  const handleExportExcel = () => {
    if (filteredData.length === 0) {
      toast.error("Không có dữ liệu để xuất");
      return;
    }

    // CSV headers
    const headers = [
      "Biển số",
      "Vị trí",
      "Thời gian Vào",
      "Thời gian Ra",
      "Thễ tích tiêu chuẩn (m3)",
      "Thể tích đo được (m3)",
      "Trạng thái",
      "Xác minh",
      "Ghi chú",
    ];

    // Map data to CSV rows
    const rows = filteredData.map((item) => [
      item.plate,
      item.location,
      item.time_in,
      item.time_out,
      item.vol_std,
      item.vol_measured,
      STATUS_MAP[item.status]?.label || item.status,
      VERIFY_MAP[item.verify]?.label || item.verify,
      `"${(item.note || "").replace(/"/g, '""')}"`,
    ]);

    const csvContent = [
      headers.join(","),
      ...rows.map((row) => row.join(",")),
    ].join("\n");

    const blob = new Blob(["\ufeff" + csvContent], {
      type: "text/csv;charset=utf-8;",
    });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);

    link.setAttribute("href", url);
    link.setAttribute(
      "download",
      `Lich_su_ra_vao_${today.replace(/\//g, "-")}.csv`
    );
    link.style.visibility = "hidden";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    toast.success("Đã tải xuống danh sách lịch sử");
  };

  return (
    <div className="h-full flex flex-col p-6 gap-2 overflow-hidden">
      {/* Header Section */}
      <div className="flex justify-between items-center shrink-0">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight">
              Lịch sử Ra Vào
            </h1>
            <span className="text-primary font-mono bg-primary/10 px-2 py-0.5 rounded text-sm border border-primary/20">
              {today}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Search Bar */}
          <div className="relative group min-w-[300px]">
            <Search
              className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-primary transition-colors"
              fontSize="small"
            />
            <input
              type="text"
              placeholder="Tìm kiếm biển số..."
              className="w-full pl-10 pr-4 py-2 bg-card border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-all text-sm"
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
                        ? "bg-primary text-primary-foreground border-primary shadow-primary/20"
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
              <select
                className="appearance-none bg-background border border-border rounded-md pl-3 pr-10 py-1.5 text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none min-w-[180px] cursor-pointer"
                value={pendingFilterGate}
                onChange={(e) => {
                  setPendingFilterGate(e.target.value);
                  setIsGateOpen(false);
                }}
                onFocus={() => setIsGateOpen(true)}
                onBlur={() => setIsGateOpen(false)}
              >
                {gates.map((g) => (
                  <option key={g} value={g}>
                    {g === "All" ? "Tất cả vị trí" : g}
                  </option>
                ))}
              </select>
              <div className="absolute inset-y-0 right-2 flex items-center pointer-events-none text-muted-foreground">
                <ChevronLeft
                  fontSize="small"
                  className={`opacity-70 transition-transform duration-200 ${
                    isGateOpen ? "-rotate-90" : ""
                  }`}
                />
              </div>
            </div>
          </div>

          {/* Status Selector */}
          <div className="flex items-center gap-3">
            <label className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest whitespace-nowrap">
              Trạng thái
            </label>
            <div className="relative">
              <select
                className="appearance-none bg-background border border-border rounded-md pl-3 pr-10 py-1.5 text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none min-w-[180px] cursor-pointer"
                value={pendingFilterStatus}
                onChange={(e) => {
                  setPendingFilterStatus(e.target.value);
                  setIsStatusOpen(false);
                }}
                onFocus={() => setIsStatusOpen(true)}
                onBlur={() => setIsStatusOpen(false)}
              >
                {statuses.map((s) => (
                  <option key={s} value={s}>
                    {s === "All" ? "Tất cả trạng thái" : STATUS_MAP[s]?.label}
                  </option>
                ))}
              </select>
              <div className="absolute inset-y-0 right-2 flex items-center pointer-events-none text-muted-foreground">
                <ChevronLeft
                  fontSize="small"
                  className={`opacity-70 transition-transform duration-200 ${
                    isStatusOpen ? "-rotate-90" : ""
                  }`}
                />
              </div>
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
              className="px-6 py-1.5 bg-primary text-primary-foreground text-sm font-bold rounded-md hover:bg-primary/90 transition-all shadow-lg shadow-primary/20 active:scale-95"
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
                  <td colSpan={columns.length} className="px-4 py-12 text-center text-muted-foreground font-medium">
                    <div className="flex flex-col items-center gap-2">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
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
          className="fixed bottom-10 left-1/2 -translate-x-1/2 p-2 bg-primary text-primary-foreground rounded-full shadow-lg hover:bg-primary/90 transition-all animate-in fade-in zoom-in duration-300 z-50 flex items-center justify-center border border-primary/20"
          aria-label="Back to top"
        >
          <ExpandLess fontSize="medium" />
        </button>
      )}
    </div>
  );
}
