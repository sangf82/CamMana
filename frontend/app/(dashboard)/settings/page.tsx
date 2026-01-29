'use client'

import React from 'react'
import { useTheme } from 'next-themes'
import { Sun, Moon, Monitor, Settings as SettingsIcon, ShieldCheck, User as UserIcon, Trash2, Key, MapPin, Camera, CarFront, Edit2, X, Server, RefreshCw, CheckCircle2, AlertCircle, LogOut, Pencil, Trash } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { toast } from 'sonner'
import Dialog from '@/components/ui/dialog'

export default function SettingsPage() {
  const { theme, setTheme, resolvedTheme } = useTheme()
  const [mounted, setMounted] = React.useState(false)
  const [currentUser, setCurrentUser] = React.useState<any>(null)
  
  // State Types
  interface FirewallStatus {
    supported?: boolean;
    rule_exists?: boolean;
    tcp_rule?: boolean;
    icmp_rule?: boolean;
    network_category?: string;
    message?: string;
    error?: string;
  }

  // New User Form State
  const [newUser, setNewUser] = React.useState({
    username: '',
    password: '',
    full_name: '',
    role: 'operator',
    allowed_gates: '*',
    can_manage_cameras: false,
    can_add_vehicles: false,
    vehicle_add_code: ''
  })
  const [locations, setLocations] = React.useState<string[]>([])
  const [selectedGates, setSelectedGates] = React.useState<string[]>([])
  const [userList, setUserList] = React.useState<any[]>([])
  const [isLoadingUsers, setIsLoadingUsers] = React.useState(false)
  const [editingUsername, setEditingUsername] = React.useState<string | null>(null)
  const [isUserDialogOpen, setIsUserDialogOpen] = React.useState(false)
  const [pcInfo, setPcInfo] = React.useState<any>(null)
  const [syncConfig, setSyncConfig] = React.useState({
    is_destination: true,
    remote_url: '',
    item_cleanup_days: 30
  })
  const [firewallStatus, setFirewallStatus] = React.useState<FirewallStatus>({})
  const [isOpeningFirewall, setIsOpeningFirewall] = React.useState(false)
  const [isFirewallDialogOpen, setIsFirewallDialogOpen] = React.useState(false)

  const updateFirewallStatus = async () => {
    try {
        const token = localStorage.getItem('token');
        const res = await fetch('/api/system/firewall/status', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        setFirewallStatus(data);
    } catch (e) {}
  };

  const fetchUsers = async (token: string | null) => {
    setIsLoadingUsers(true);
    try {
        const res = await fetch('/api/user', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            const data = await res.json();
            setUserList(data);
        }
    } catch (e) {
        toast.error("Không thể tải danh sách người dùng");
    } finally {
        setIsLoadingUsers(false);
    }
  };

  // Avoid hydration mismatch
  React.useEffect(() => {
    setMounted(true)
    const userStr = localStorage.getItem('user')
    if (userStr) {
      setCurrentUser(JSON.parse(userStr))
    }

    const token = localStorage.getItem('token');
    
    // Load data
    fetch('/api/cameras/locations', { headers: { 'Authorization': `Bearer ${token}` }})
      .then(res => res.json()).then(data => { if (Array.isArray(data)) setLocations(data.map(l => l.name)) }).catch(() => {})

    const user = userStr ? JSON.parse(userStr) : null;
    if (user?.role === 'admin') fetchUsers(token);

    fetch('/api/system/info', { headers: { 'Authorization': `Bearer ${token}` }})
      .then(res => res.json()).then(data => setPcInfo(data)).catch(() => {})

    fetch('/api/sync/status', { headers: { 'Authorization': `Bearer ${token}` }})
      .then(res => res.json()).then(data => setSyncConfig(data)).catch(() => {})

    updateFirewallStatus();
  }, [])

  if (!mounted) {
    return (
      <div className="p-6 flex items-center justify-center h-[70vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  const handleCreateUser = async () => {
    if (!newUser.username || (!editingUsername && !newUser.password)) {
      toast.error("Vui lòng nhập tên đăng nhập và mật khẩu");
      return;
    }
    const payload = { ...newUser, allowed_gates: selectedGates.length === locations.length || selectedGates.length === 0 ? '*' : selectedGates.join(',') };
    try {
      const token = localStorage.getItem('token');
      const url = editingUsername ? `/api/user/${editingUsername}` : '/api/user/register';
      const res = await fetch(url, {
        method: editingUsername ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        toast.success(editingUsername ? `Đã cập nhật ${editingUsername}` : `Đã tạo ${newUser.username}`);
        setNewUser({ username: '', password: '', full_name: '', role: 'operator', allowed_gates: '*', can_manage_cameras: false, can_add_vehicles: false, vehicle_add_code: '' });
        setEditingUsername(null); setIsUserDialogOpen(false); setSelectedGates([]);
        fetchUsers(token);
      } else {
        const err = await res.json();
        toast.error(err.detail || "Lỗi thao tác");
      }
    } catch (e) { toast.error("Lỗi kết nối"); }
  };

  const handleDeleteUser = async (username: string) => {
    if (username === 'admin') return toast.error("Không thể xóa Admin");
    if (!window.confirm(`Xóa tài khoản ${username}?`)) return;
    try {
        const token = localStorage.getItem('token');
        const res = await fetch(`/api/user/${username}`, { method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` } });
        if (res.ok) { toast.success("Đã xóa"); fetchUsers(token); }
    } catch (e) { toast.error("Lỗi kết nối"); }
  };

  const handleOpenFirewall = async () => {
    setIsOpeningFirewall(true);
    try {
        const token = localStorage.getItem('token');
        const res = await fetch('/api/system/firewall/open', { method: 'POST', headers: { 'Authorization': `Bearer ${token}` } });
        const data = await res.json();
        if (data.success) { toast.success(data.message); updateFirewallStatus(); } else toast.error(data.message);
    } catch (e) { toast.error("Lỗi yêu cầu"); } finally { setIsOpeningFirewall(false); setIsFirewallDialogOpen(false); }
  };

  const startEdit = (user: any) => {
    setEditingUsername(user.username);
    setNewUser({ username: user.username, password: '', full_name: user.full_name || '', role: user.role || 'operator', allowed_gates: user.allowed_gates || '*', can_manage_cameras: user.can_manage_cameras === true, can_add_vehicles: user.can_add_vehicles === true, vehicle_add_code: user.vehicle_add_code || '' });
    setSelectedGates(user.allowed_gates === '*' ? [] : user.allowed_gates.split(',').map((g: string) => g.trim()));
  };

  const isDark = resolvedTheme === 'dark'
  const isAdmin = currentUser?.role === 'admin'

  return (
    <div className="w-full h-full overflow-y-auto bg-background">
      <div className="max-w-[1500px] mx-auto p-6 pb-40 space-y-4 min-h-screen">
      {/* Header */}
      <div className="flex justify-between items-center shrink-0">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Cài đặt hệ thống
          </h1>
        </div>
        <div className="flex items-center gap-3">
            <div className={`px-3 py-1.5 rounded-md border flex items-center gap-2 ${syncConfig.is_destination ? 'bg-green-500/10 text-green-500 border-green-500/20' : 'bg-amber-500/10 text-amber-500 border-amber-500/20'}`}>
                <div className={`w-1.5 h-1.5 rounded-full ${syncConfig.is_destination ? 'bg-green-500' : 'bg-amber-500'} animate-pulse`} />
                <span className="text-[10px] font-bold tracking-widest uppercase">{syncConfig.is_destination ? 'Master Node' : 'Client Node'}</span>
            </div>
        </div>
      </div>
      
      {/* 2x2 Grid Window Layout */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          
          {/* Panel 1: TÀI KHOẢN NGƯỜI DÙNG */}
          <Card className="border-border shadow-sm flex flex-col h-full bg-card">
            <div className="h-24 bg-muted/30 relative shrink-0 border-b border-border">
                <div className="absolute -bottom-8 left-8 transition-transform hover:scale-105 duration-300">
                    <div className="w-16 h-16 rounded-2xl bg-[#f59e0b] flex items-center justify-center text-zinc-950 text-xl font-bold shadow-lg border-4 border-background">
                        {currentUser?.username?.substring(0, 2).toUpperCase()}
                    </div>
                </div>
            </div>
            <CardContent className="pt-12 pb-6 flex-1 flex flex-col justify-between px-8">
                <div>
                    <h2 className="text-xl font-bold tracking-tight mb-1">{currentUser?.full_name || currentUser?.username}</h2>
                    <p className="text-[11px] text-muted-foreground font-semibold flex items-center gap-1.5 uppercase tracking-wider">
                        <ShieldCheck size={14} className="text-[#f59e0b]" />
                        Cấp độ truy cập: <span className="text-foreground font-bold">{currentUser?.role?.toUpperCase()}</span>
                    </p>
                </div>

                <div className="space-y-3 py-5 border-y border-border/60 mt-6">
                    <div className="flex items-center justify-between">
                        <span className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider">Username</span>
                        <span className="font-mono text-xs bg-muted px-2.5 py-1 rounded text-foreground font-medium">@{currentUser?.username}</span>
                    </div>
                    <div className="flex items-center justify-between">
                        <span className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider">Phạm vi kiểm soát</span>
                        <span className="text-[#f59e0b] font-bold text-[10px] uppercase tracking-wider bg-[#f59e0b]/10 px-2.5 py-1 rounded border border-[#f59e0b]/20">
                            {currentUser?.allowed_gates === '*' ? 'Toàn bộ hệ thống' : 'Bị giới hạn'}
                        </span>
                    </div>
                </div>

                <Button variant="outline" size="sm" className="w-full text-[11px] h-9 font-bold mt-4 hover:bg-destructive hover:text-white transition-all border-border rounded-lg gap-2" onClick={() => {
                    localStorage.clear();
                    window.location.href = '/login';
                }}>
                    <LogOut size={14} />
                    ĐĂNG XUẤT HỆ THỐNG
                </Button>
            </CardContent>
          </Card>

          {/* Panel 2: THÔNG SỐ THIẾT BỊ ĐẦU CUỐI */}
          <Card className="bg-card border-border shadow-sm flex flex-col h-full">
            <CardHeader className="py-4 px-6 border-b border-border bg-muted/20 shrink-0">
                <CardTitle className="text-[11px] font-bold flex items-center gap-2.5 uppercase tracking-wider text-foreground/80">
                    <Monitor className="h-4 w-4 text-[#f59e0b]" />
                    Thông tin phần cứng
                </CardTitle>
            </CardHeader>
            <CardContent className="p-6 flex-1 overflow-y-auto">
                <div className="grid grid-cols-2 gap-y-5 gap-x-8">
                    <div className="space-y-1">
                        <p className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Tên máy tính</p>
                        <p className="font-mono font-bold truncate text-sm text-foreground">{pcInfo?.pc_name || 'Đang quét...'}</p>
                    </div>
                    <div className="space-y-1">
                        <p className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Hệ điều hành</p>
                        <p className="font-mono font-bold text-sm text-foreground">{pcInfo?.os || '---'}</p>
                    </div>
                    <div className="space-y-1">
                        <p className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Bộ nhớ RAM</p>
                        <p className="font-mono font-bold text-sm text-foreground">{pcInfo?.ram || '---'}</p>
                    </div>
                    <div className="space-y-1">
                        <p className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Địa chỉ IP</p>
                        <p className="font-mono font-bold text-sm text-[#f59e0b]">{pcInfo?.ip_address || '---'}</p>
                    </div>
                    <div className="col-span-2 space-y-2 pt-4 border-t border-border/60">
                        <p className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Vi xử lý (CPU)</p>
                        <div className="font-mono text-[11px] bg-muted/50 text-foreground p-3 rounded-lg border border-border group flex items-center justify-between gap-4">
                            <div className="truncate flex-1">
                                {pcInfo?.processor?.split(' @ ')[0] || 'Đang lấy thông tin CPU...'}
                            </div>
                            <div className="shrink-0 flex items-center gap-1.5 font-sans text-[8px] font-bold uppercase text-muted-foreground">
                                <span>Hoạt động</span>
                                <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                            </div>
                        </div>
                    </div>
                </div>
            </CardContent>
          </Card>

          {/* Panel 3: TÙY CHỈNH GIAO DIỆN */}
          <Card className="shadow-sm border-border flex flex-col h-full bg-card">
            <CardHeader className="py-4 px-6 border-b border-border bg-muted/20 shrink-0">
              <CardTitle className="text-[11px] font-bold flex items-center gap-2.5 uppercase tracking-wider text-foreground/80">
                {isDark ? <Moon className="h-4 w-4 text-[#f59e0b]" /> : <Sun className="h-4 w-4 text-[#f59e0b]" />}
                Giao diện người dùng
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 flex-1 flex flex-col justify-center gap-6">
              <div className="flex items-center justify-between p-4 bg-muted/20 rounded-xl border border-border/60 group hover:border-[#f59e0b]/30 transition-all">
                <div className="space-y-0.5">
                    <Label className="text-sm font-bold">Chế độ tối (Dark Mode)</Label>
                    <p className="text-[11px] text-muted-foreground font-medium opacity-70">Sử dụng tông màu trầm bảo vệ mắt.</p>
                </div>
                <Switch checked={isDark} onCheckedChange={(c) => setTheme(c ? 'dark' : 'light')} className="data-[state=checked]:bg-[#f59e0b]" />
              </div>
              <div className="flex gap-2 p-1 bg-muted/30 rounded-lg border border-border/60">
                {['light', 'dark', 'system'].map((t) => (
                    <button
                        key={t}
                        onClick={() => setTheme(t)}
                        className={`flex-1 py-1.5 text-[10px] font-bold rounded-md transition-all uppercase tracking-wider ${
                            theme === t ? 'bg-background text-[#f59e0b] shadow-sm border border-border' : 'text-muted-foreground opacity-60 hover:opacity-100'
                        }`}
                    >
                        {t === 'light' ? 'Sáng' : t === 'dark' ? 'Tối' : 'Hệ thống'}
                    </button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Panel 4: ĐỒNG BỘ DỮ LIỆU */}
          <Card className="shadow-sm border-border flex flex-col h-full bg-card">
            <CardHeader className="py-4 px-6 border-b border-border bg-muted/20 shrink-0">
              <CardTitle className="text-[11px] font-bold flex items-center justify-between gap-2.5 uppercase tracking-wider text-foreground/80">
                <div className="flex items-center gap-2.5">
                    <Server className="h-4 w-4 text-[#f59e0b]" />
                    Đồng bộ & Mạng
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 flex-1 flex flex-col justify-between">
               {syncConfig.is_destination ? (
                 <div className="space-y-6">
                    <div className="grid grid-cols-3 gap-4">
                        {[
                          { label: 'Cổng 8000', status: firewallStatus.tcp_rule },
                          { label: 'Phản hồi Ping', status: firewallStatus.icmp_rule },
                          { label: 'Mạng Private', status: firewallStatus.network_category === 'Private', text: firewallStatus.network_category }
                        ].map((item, idx) => (
                            <div key={idx} className="flex flex-col items-center gap-2 group">
                                <div className={`w-10 h-10 rounded-xl flex items-center justify-center border transition-all ${item.status ? 'bg-green-500/5 border-green-500/20 text-green-500' : 'bg-red-500/5 border-red-500/20 text-red-500'}`}>
                                    {item.status ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
                                </div>
                                <span className={`text-[9px] font-bold uppercase tracking-tight text-center ${item.status ? 'text-foreground' : 'text-muted-foreground'}`}>
                                    {item.text || item.label}
                                </span>
                            </div>
                        ))}
                    </div>

                    <div className="flex gap-2">
                        <Button variant="outline" className="flex-1 h-9 text-[10px] font-bold border-border hover:bg-muted group" onClick={updateFirewallStatus}>
                            <RefreshCw size={12} className="mr-2 group-active:rotate-180 transition-transform duration-500" /> QUÉT LẠI
                        </Button>
                        <Button className="flex-[1.5] h-9 text-[10px] font-bold bg-[#f59e0b] text-black hover:bg-[#f59e0b]/90 transition-all shadow-md rounded-lg" onClick={() => setIsFirewallDialogOpen(true)}>
                            MỞ CỔNG TƯỜNG LỬA
                        </Button>
                    </div>
                 </div>
               ) : (
                 <div className="space-y-4">
                     <div className="p-4 rounded-xl bg-muted/30 border border-border/60 relative group">
                         <p className="text-[10px] uppercase text-muted-foreground font-bold tracking-wider mb-1.5 opacity-60">Địa chỉ máy chủ đích</p>
                         <p className="font-mono text-xs font-bold text-[#f59e0b] truncate">{syncConfig.remote_url || 'CHƯA CẤU HÌNH'}</p>
                     </div>
                     <Button variant="outline" className="w-full h-10 text-[10px] font-bold border-[#f59e0b]/30 text-[#f59e0b] hover:bg-[#f59e0b]/5 transition-all rounded-lg gap-2" onClick={async () => {
                          const token = localStorage.getItem('token');
                          toast.loading("Đang kiểm tra kết nối...", { id: 'ping' });
                          try {
                            const res = await fetch('/api/sync/test-push', { method: 'POST', headers: { 'Authorization': `Bearer ${token}` }});
                            const data = await res.json();
                            if (data.success) toast.success(data.message, { id: 'ping' }); else toast.error(data.message, { id: 'ping' });
                          } catch (e) { toast.error("Không thể kết nối tới máy chủ", { id: 'ping' }); }
                     }}>
                         <RefreshCw size={14} /> KIỂM TRA ĐƯỜNG TRUYỀN
                     </Button>
                 </div>
               )}
            </CardContent>
          </Card>
      </div>

      {/* Admin User Management Section */}
      {isAdmin ? (
        <>
            <Card className="border-border shadow-sm overflow-hidden bg-card mt-2 mb-8">
                <CardHeader className="bg-muted/20 pb-4 border-b border-border px-6">
                    <div className="flex items-center justify-between">
                        <CardTitle className="text-sm flex items-center gap-2.5 font-bold uppercase tracking-wider">
                            <UserIcon className="h-4 w-4 text-[#f59e0b]" />
                            Quản lý tài khoản
                        </CardTitle>
                        <Button 
                            size="sm" 
                            className="bg-[#f59e0b] hover:bg-[#f59e0b]/90 text-black font-bold text-[11px] gap-2 px-6 py-4 rounded-lg shadow-md shadow-[#f59e0b]/10"
                            onClick={() => {
                                setEditingUsername(null);
                                setNewUser({
                                    username: '', password: '', full_name: '', role: 'operator',
                                    allowed_gates: '*', can_manage_cameras: false, can_add_vehicles: false, vehicle_add_code: ''
                                });
                                setSelectedGates([]);
                                setIsUserDialogOpen(true);
                            }}
                        >
                            <UserIcon className="h-3.5 w-3.5" /> THÊM TÀI KHOẢN MỚI
                        </Button>
                    </div>
                </CardHeader>
                <CardContent className="p-0">
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm text-left">
                            <thead className="text-[10px] uppercase bg-muted/50 border-b border-border font-bold tracking-wider text-muted-foreground/80">
                                <tr>
                                    <th className="px-6 py-3">Họ và tên / Username</th>
                                    <th className="px-6 py-3">Quyền hạn</th>
                                    <th className="px-6 py-3">Cổng truy cập</th>
                                    <th className="px-6 py-3 text-right">Điều khiển</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border/60">
                                {userList.map((user) => (
                                    <tr key={user.id} className="hover:bg-muted/5 transition-colors group/row">
                                        <td className="px-6 py-3 flex items-center gap-3">
                                            <div className="w-8 h-8 rounded-lg bg-[#f59e0b]/10 flex items-center justify-center text-[#f59e0b] text-[10px] font-bold border border-[#f59e0b]/20 group-hover/row:bg-[#f59e0b] group-hover/row:text-black transition-all">
                                                {user.username.substring(0,2).toUpperCase()}
                                            </div>
                                            <div>
                                                <p className="font-bold text-xs">{user.full_name || 'Classified Name'}</p>
                                                <p className="text-[10px] text-muted-foreground font-mono opacity-60">@{user.username}</p>
                                            </div>
                                        </td>
                                        <td className="px-6 py-3">
                                            <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider border ${
                                                user.role === 'admin' ? 'bg-[#f59e0b]/10 text-[#f59e0b] border-[#f59e0b]/30' : 'bg-blue-500/10 text-blue-500 border-blue-500/30'
                                            }`}>
                                                {user.role}
                                            </span>
                                        </td>
                                        <td className="px-6 py-3">
                                            <div className="flex flex-col gap-1.5">
                                                <div className="flex items-center gap-1.5 text-[10px] font-bold text-muted-foreground">
                                                    <MapPin className="h-3 w-3 text-[#f59e0b]" />
                                                    <span className="truncate uppercase tracking-tighter font-semibold">
                                                        {user.allowed_gates === '*' ? 'Toàn quyền truy cập (*)' : user.allowed_gates}
                                                    </span>
                                                </div>
                                                <div className="flex items-center gap-3 text-[9px] font-bold opacity-50 group-hover/row:opacity-100 transition-opacity">
                                                    <span className={`flex items-center gap-1 ${user.can_manage_cameras ? 'text-green-500' : 'text-red-500'}`}>
                                                        <Camera size={11} /> {user.can_manage_cameras ? 'CAMERA: CÓ' : 'CAMERA: KHÔNG'}
                                                    </span>
                                                    <span className={`flex items-center gap-1 ${user.can_add_vehicles ? 'text-green-500' : 'text-red-500'}`}>
                                                        <CarFront size={11} /> {user.can_add_vehicles ? 'XÁC THỰC: CÓ' : 'XÁC THỰC: KHÔNG'}
                                                    </span>
                                                </div>
                                            </div>
                                        </td>
                                         <td className="px-6 py-3 text-right">
                                            <div className="flex items-center justify-end gap-2 opacity-40 group-hover/row:opacity-100 transition-opacity">
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    className="h-7 w-7 text-amber-500 hover:text-amber-600 hover:bg-amber-500/10"
                                                    onClick={(e) => { e.stopPropagation(); startEdit(user); setIsUserDialogOpen(true); }}
                                                >
                                                    <Pencil className="w-4 h-4" />
                                                </Button>
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    className="h-7 w-7 text-destructive hover:text-destructive hover:bg-destructive/10"
                                                    disabled={user.username === 'admin'}
                                                    onClick={(e) => { e.stopPropagation(); handleDeleteUser(user.username); }}
                                                >
                                                    <Trash className="w-4 h-4" />
                                                </Button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </CardContent>
            </Card>
        </>
      ) : null}

      {/* User Logic Dialog */}
      <Dialog isOpen={isUserDialogOpen} onClose={() => setIsUserDialogOpen(false)} title={editingUsername ? 'Cập nhật thông tin tài khoản' : 'Đăng ký tài khoản mới'} maxWidth="2xl">
        <div className="space-y-5 pt-2">
            <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                    <Label className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider pl-0.5">Tên đăng nhập</Label>
                    <Input value={newUser.username} onChange={e=>setNewUser({...newUser, username: e.target.value})} disabled={!!editingUsername} className="h-10 text-sm font-medium rounded-lg bg-muted/20 border-border focus-visible:ring-[#f59e0b]/30" placeholder="VD: nguyen.van.a"/>
                </div>
                <div className="space-y-1.5">
                    <Label className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider pl-0.5">Mật khẩu</Label>
                    <Input type="password" value={newUser.password} onChange={e=>setNewUser({...newUser, password: e.target.value})} className="h-10 text-sm font-medium rounded-lg bg-muted/20 border-border focus-visible:ring-[#f59e0b]/30" placeholder="••••••••"/>
                </div>
            </div>
            
            <div className="space-y-5 pt-4 border-t border-border">
                <div className="space-y-1.5">
                    <Label className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider pl-0.5">Họ và tên đầy đủ</Label>
                    <Input value={newUser.full_name} onChange={e=>setNewUser({...newUser, full_name: e.target.value})} className="h-10 text-sm font-medium rounded-lg bg-muted/20 border-border" placeholder="VD: Nguyễn Văn A"/>
                </div>
                
                <div className="space-y-2">
                    <Label className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider pl-0.5">Cổng được phép truy cập:</Label>
                    <div className="flex flex-wrap gap-2 pt-1">
                        {locations.map(loc => (
                            <Button key={loc} variant={selectedGates.includes(loc) ? 'default' : 'outline'} size="sm" className={`h-8 text-[10px] px-3 font-bold rounded-md transition-all ${selectedGates.includes(loc) ? 'bg-[#f59e0b] text-black border-[#f59e0b] shadow-sm' : 'border-border hover:border-[#f59e0b]/50'}`} onClick={() => setSelectedGates(prev => prev.includes(loc) ? prev.filter(g => g !== loc) : [...prev, loc])}>
                                {loc.toUpperCase()}
                            </Button>
                        ))}
                        <Button variant={selectedGates.length === 0 ? 'secondary' : 'outline'} size="sm" className="h-8 text-[10px] px-4 font-bold rounded-md bg-zinc-900 shadow-sm text-white hover:bg-zinc-800" onClick={() => setSelectedGates([])}>Tất cả (*)</Button>
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div className="flex items-center justify-between p-3 bg-muted/20 rounded-lg border border-border group hover:border-green-500/30 transition-all">
                        <div className="space-y-0.5">
                            <Label className="text-[11px] font-bold uppercase tracking-tight">Quản lý Camera</Label>
                            <p className="text-[9px] text-muted-foreground font-bold uppercase opacity-50">Truy cập cấu hình</p>
                        </div>
                        <Switch checked={newUser.can_manage_cameras} onCheckedChange={c=>setNewUser({...newUser, can_manage_cameras: c})} className="data-[state=checked]:bg-green-500" />
                    </div>
                    <div className="flex items-center justify-between p-3 bg-muted/20 rounded-lg border border-border group hover:border-green-500/30 transition-all">
                        <div className="space-y-0.5">
                            <Label className="text-[11px] font-bold uppercase tracking-tight">Xác thực xe</Label>
                            <p className="text-[9px] text-muted-foreground font-bold uppercase opacity-50">Đăng ký vào/ra</p>
                        </div>
                        <Switch checked={newUser.can_add_vehicles} onCheckedChange={c=>setNewUser({...newUser, can_add_vehicles: c})} className="data-[state=checked]:bg-green-500" />
                    </div>
                </div>
                
                {newUser.can_add_vehicles && (
                    <div className="space-y-2 animate-in slide-in-from-top-2 duration-300">
                        <Label className="text-[10px] uppercase font-bold text-[#f59e0b] tracking-wider pl-0.5">Mã xác nhận bảo vệ</Label>
                        <Input value={newUser.vehicle_add_code} onChange={e=>setNewUser({...newUser, vehicle_add_code: e.target.value})} placeholder="CODE" className="h-10 font-mono text-center text-lg font-bold tracking-[0.4em] border-[#f59e0b]/30 rounded-lg bg-[#f59e0b]/5 text-[#f59e0b]"/>
                    </div>
                )}
            </div>
            
            <div className="pt-6 flex justify-end gap-3 border-t border-border">
                <Button variant="ghost" size="sm" className="text-xs font-bold px-6 opacity-60" onClick={()=>setIsUserDialogOpen(false)}>HỦY</Button>
                <Button className="bg-foreground text-background hover:bg-[#f59e0b] hover:text-black font-bold px-8 h-10 rounded-lg shadow-md transition-all active:scale-95" onClick={handleCreateUser}>
                    LƯU THAY ĐỔI
                </Button>
            </div>
        </div>
      </Dialog>

      {/* Firewall Dialog */}
      <Dialog isOpen={isFirewallDialogOpen} onClose={() => !isOpeningFirewall && setIsFirewallDialogOpen(false)} title="QUY TRÌNH HẠ TẦNG HỆ THỐNG">
        <div className="space-y-6 pt-2 text-center pb-2">
            <div className="relative mx-auto w-20 h-20">
                <div className="absolute inset-0 bg-[#f59e0b]/10 rounded-full animate-ping opacity-30" />
                <div className="relative w-20 h-20 rounded-full bg-[#f59e0b]/5 flex items-center justify-center text-[#f59e0b] border-2 border-[#f59e0b]/20 shadow-[0_0_20px_rgba(245,158,11,0.1)]">
                    <ShieldCheck size={40} />
                </div>
            </div>
            <div className="space-y-2 px-6">
                <h3 className="text-lg font-bold uppercase tracking-tight italic">Cấu hình bảo vệ Windows</h3>
                <p className="text-[11px] text-muted-foreground leading-relaxed font-medium">
                   Hành động này sẽ thiết lập lại <span className="text-foreground font-bold underline decoration-[#f59e0b] decoration-2 underline-offset-4">Tường lửa (Windows Firewall)</span>. 
                   Các cổng dịch vụ sẽ được mở, phản hồi ICMP (Ping) được cấp phép và cấu hình mạng được chuyển sang chế độ Private.
                </p>
                <div className="mt-6 p-3 bg-red-500/5 rounded-2xl border border-red-500/10 inline-block">
                    <p className="text-[10px] font-bold uppercase text-red-500 flex items-center gap-2.5 tracking-wider">
                        <AlertCircle size={14} className="animate-pulse" /> YÊU CẦU QUYỀN QUẢN TRỊ (ADMIN)
                    </p>
                </div>
            </div>
            <div className="pt-6 flex flex-col gap-2 px-6">
                <Button className="w-full bg-[#f59e0b] hover:bg-[#f59e0b]/90 text-black font-bold h-12 rounded-xl shadow-lg transition-all active:scale-95 flex items-center justify-center gap-2 text-sm" onClick={handleOpenFirewall} disabled={isOpeningFirewall}>
                    {isOpeningFirewall ? (
                       <>
                          <RefreshCw size={18} className="animate-spin" /> ĐANG THỰC THI...
                       </>
                    ) : 'BẮT ĐẦU CẤU HÌNH'}
                </Button>
                <Button variant="ghost" className="text-[10px] font-bold opacity-40 tracking-widest hover:opacity-100" onClick={()=>setIsFirewallDialogOpen(false)} disabled={isOpeningFirewall}>HỦY THAO TÁC</Button>
            </div>
        </div>
      </Dialog>
      
      {/* Extra space at bottom for better scrolling */}
      <div className="h-32" />
      </div>
    </div>
  )
}
