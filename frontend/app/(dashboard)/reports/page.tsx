'use client'

import React, { useState, useEffect } from 'react'
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend 
} from 'recharts'
import { 
  Download, RefreshCw, Calendar, TrendingUp, Truck, Package, UserCheck 
} from 'lucide-react'
import { toast } from 'sonner'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { LoadingPanel } from '@/components/ui/loading-spinner'
import { useTheme } from 'next-themes'
import { ExpandMore, CheckCircle } from '@mui/icons-material'

const COLORS = ['#f59e0b', '#3b82f6', '#10b981', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899'];

interface ReportData {
  date: string;
  summary: {
    total_registered: number;
    total_in: number;
    total_volume_out: number;
    avg_volume: number;
  };
  charts: {
    wheel_distribution: Record<string, number>;
    contractor_volume_distribution: Record<string, number>;
    hourly_distribution: Record<string, number>;
  };
  generated_at: string;
}

export default function ReportsPage() {
  const { theme, resolvedTheme } = useTheme();
  const [data, setData] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [availableDates, setAvailableDates] = useState<string[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [isDateDropdownOpen, setIsDateDropdownOpen] = useState(false);

  // Use CSS variable for axis text to ensure it updates with theme automatically
  const axisTextColor = "var(--foreground)";

  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      
      const historyRes = await fetch('/api/report/history', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (historyRes.ok) {
        const dates = await historyRes.json();
        setAvailableDates(dates);
      }

      const reportRes = await fetch('/api/report/today', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (reportRes.ok) {
        const report = await reportRes.json();
        setData(report);
        setSelectedDate(report.date);
      } else {
        const err = await reportRes.json();
        toast.error(err.detail || "Không thể tải báo cáo hôm nay");
      }
    } catch (error) {
      console.error('Error fetching reports:', error);
      toast.error('Lỗi kết nối máy chủ');
    } finally {
      setLoading(false);
    }
  };

  const handleDateChange = async (date: string) => {
    try {
      setLoading(true);
      setSelectedDate(date);
      const token = localStorage.getItem('token');
      const res = await fetch(`/api/report/detail?date=${date}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const report = await res.json();
        setData(report);
      } else {
        toast.error('Không tìm thấy dữ liệu cho ngày này');
      }
    } catch (error) {
      toast.error('Lỗi kết nối');
    } finally {
      setLoading(false);
    }
  };

  const handleManualGenerate = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const res = await fetch('/api/report/generate', { 
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
          const report = await res.json();
          setData(report);
          toast.success('Đã làm mới dữ liệu báo cáo');
      } else {
          toast.error("Lỗi khi tạo lại báo cáo");
      }
    } catch (error) {
      toast.error('Lỗi khi tạo báo cáo');
    } finally {
      setLoading(false);
    }
  };

  const handleExportPDF = async () => {
    if (!selectedDate) return;
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/report/export/pdf?date=${selectedDate}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (!response.ok) throw new Error('Export failed');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report_${selectedDate}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success('Đã tải xuống báo cáo PDF');
    } catch (e) {
      console.error('PDF Export Error:', e);
      toast.error('Lỗi khi tải xuống PDF');
    }
  };

  if (loading && !data) {
    return (
      <div className="p-6">
        <LoadingPanel message="Đang tải báo cáo..." size="lg" />
      </div>
    );
  }

  const wheelChartData = data?.charts?.wheel_distribution 
    ? Object.entries(data.charts.wheel_distribution).map(([name, value]) => ({
        name: `${name} bánh`,
        value
      })) 
    : [];

  const contractorChartData = data?.charts?.contractor_volume_distribution 
    ? Object.entries(data.charts.contractor_volume_distribution).map(([name, value]) => ({
        name,
        value
      })) 
    : [];

  const hourlyChartData = data?.charts?.hourly_distribution
    ? Object.entries(data.charts.hourly_distribution).map(([hour, count]) => ({
        name: `${hour}h`,
        value: count
      }))
    : [];

  return (
    <div className="p-6 space-y-6 overflow-y-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight">Báo cáo & Thống kê</h1>
          <p className="text-muted-foreground text-sm">
            Xem tổng hợp lưu lượng xe và sản lượng trong ngày.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative">
            <button 
              onClick={() => setIsDateDropdownOpen(!isDateDropdownOpen)}
              className="flex items-center gap-2 bg-card border border-border px-3 py-1.5 rounded-md shadow-sm hover:border-[#f59e0b] focus:border-[#f59e0b] focus:ring-1 focus:ring-[#f59e0b] transition-all min-w-[150px] justify-between"
            >
              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4 text-[#f59e0b]" />
                <span className="text-sm font-medium">{selectedDate || 'Chọn ngày...'}</span>
              </div>
              <ExpandMore className={`h-4 w-4 transition-transform duration-200 ${isDateDropdownOpen ? 'rotate-180' : ''}`} />
            </button>
            
            {isDateDropdownOpen && (
              <div className="absolute top-full right-0 mt-1 w-full z-[100] bg-popover text-popover-foreground border border-border rounded-xl shadow-2xl p-1 max-h-56 overflow-y-auto animate-in fade-in slide-in-from-top-1 duration-200">
                {availableDates.map(date => (
                  <button 
                    key={date} 
                    onClick={() => {
                      handleDateChange(date);
                      setIsDateDropdownOpen(false);
                    }}
                    className={`w-full text-left px-3 py-2 rounded-lg text-xs font-medium transition-colors hover:bg-[#f59e0b]/10 flex items-center justify-between ${selectedDate === date ? "text-[#f59e0b] bg-[#f59e0b]/5" : "text-muted-foreground"}`}
                  >
                    <span>{date}</span>
                    {selectedDate === date && <CheckCircle sx={{ fontSize: 14 }} />}
                  </button>
                ))}
              </div>
            )}
          </div>
          
          <button
            onClick={handleManualGenerate}
            disabled={loading}
            className="px-4 py-1.5 bg-card border border-border rounded-md text-sm font-bold flex items-center gap-2 hover:bg-muted transition-all hover:text-[#f59e0b] shadow-sm disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Làm mới
          </button>

          <button
            onClick={handleExportPDF}
            className="px-4 py-1.5 bg-[#f59e0b] text-black rounded-md text-sm font-bold flex items-center gap-2 hover:bg-[#f59e0b]/90 transition-all shadow-lg shadow-[#f59e0b]/20 active:scale-95"
          >
            <Download className="h-4 w-4" />
            Xuất PDF
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Tổng xe đăng ký</CardTitle>
            <UserCheck className="h-5 w-5 text-[#f59e0b]" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{data?.summary.total_registered || 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Lượt xe trong ngày</CardTitle>
            <Truck className="h-5 w-5 text-[#f59e0b]" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{data?.summary.total_in || 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Tổng khối lượng (m³)</CardTitle>
            <Package className="h-5 w-5 text-[#f59e0b]" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{data?.summary.total_volume_out || 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Khối lượng TB/Xe</CardTitle>
            <TrendingUp className="h-5 w-5 text-[#f59e0b]" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{data?.summary.avg_volume || 0}</div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Phân bố theo số bánh xe</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={wheelChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                  <XAxis dataKey="name" stroke="var(--border)" fontSize={12} tickLine={false} axisLine={false} tick={{ fill: 'var(--foreground)', fontSize: 11 }} dy={10} />
                  <YAxis stroke="var(--border)" fontSize={12} tickLine={false} axisLine={false} tick={{ fill: 'var(--foreground)', fontSize: 11 }} />
                  <Tooltip 
                    cursor={{ fill: 'rgba(245, 158, 11, 0.1)' }}
                    contentStyle={{ 
                        backgroundColor: '#18181b', 
                        border: '1px solid #f59e0b', 
                        borderRadius: '8px',
                        boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)'
                    }}
                    itemStyle={{ color: '#ffffff' }}
                    labelStyle={{ color: '#f59e0b', fontWeight: 'bold' }}
                    formatter={(value: number) => [`${value} xe`, 'Số lượng']}
                  />
                  <Bar dataKey="value" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Khối lượng theo nhà thầu (m³)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={contractorChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                  <XAxis dataKey="name" stroke="var(--border)" fontSize={12} tickLine={false} axisLine={false} tick={{ fill: 'var(--foreground)', fontSize: 11 }} dy={10} />
                  <YAxis stroke="var(--border)" fontSize={12} tickLine={false} axisLine={false} tick={{ fill: 'var(--foreground)', fontSize: 11 }} />
                  <Tooltip 
                    cursor={{ fill: 'rgba(245, 158, 11, 0.1)' }}
                    contentStyle={{ 
                        backgroundColor: '#18181b', 
                        border: '1px solid #f59e0b', 
                        borderRadius: '8px',
                        boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)'
                    }}
                    itemStyle={{ color: '#ffffff' }}
                    labelStyle={{ color: '#f59e0b', fontWeight: 'bold' }}
                    formatter={(value: number) => [`${value} m³`, 'Khối lượng']}
                  />
                  <Bar dataKey="value" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>
      
      <Card>
        <CardHeader>
          <CardTitle>Mật độ xe theo giờ trong ngày (số lượt)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[250px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={hourlyChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                <XAxis dataKey="name" stroke="var(--border)" fontSize={11} tickLine={false} axisLine={false} tick={{ fill: 'var(--foreground)', fontSize: 10 }} />
                <YAxis stroke="var(--border)" fontSize={11} tickLine={false} axisLine={false} tick={{ fill: 'var(--foreground)', fontSize: 10 }} />
                <Tooltip 
                  cursor={{ fill: 'rgba(245, 158, 11, 0.1)' }}
                  contentStyle={{ 
                      backgroundColor: '#18181b', 
                      border: '1px solid #f59e0b', 
                      borderRadius: '8px'
                  }}
                  itemStyle={{ color: '#ffffff' }}
                  labelStyle={{ color: '#f59e0b', fontWeight: 'bold' }}
                />
                <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Metadata */}
      <div className="text-right">
        <p className="text-[10px] text-muted-foreground uppercase font-bold tracking-widest">
          Cập nhật lần cuối: {data ? new Date(data.generated_at).toLocaleString('vi-VN') : '---'}
        </p>
      </div>
    </div>
  );
}
