'use client'

import React from 'react'
import { useTheme } from 'next-themes'
import { Sun, Moon, Monitor, Settings as SettingsIcon, ShieldCheck, User as UserIcon, Trash2, Key, MapPin, Camera, CarFront, Edit2, X, Server } from 'lucide-react'
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
  const [firewallStatus, setFirewallStatus] = React.useState<{rule_exists?: boolean, supported?: boolean, message?: string}>({})
  const [isOpeningFirewall, setIsOpeningFirewall] = React.useState(false)
  const [isFirewallDialogOpen, setIsFirewallDialogOpen] = React.useState(false)

  // Avoid hydration mismatch
  React.useEffect(() => {
    setMounted(true)
    const userStr = localStorage.getItem('user')
    if (userStr) {
      setCurrentUser(JSON.parse(userStr))
    }

    // Load locations for gate selection
    const token = localStorage.getItem('token');
    fetch('/api/cameras/locations', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) {
          setLocations(data.map(l => l.name))
        }
      })
      .catch(() => {})

    // Load user list if admin
    const user = userStr ? JSON.parse(userStr) : null;
    if (user?.role === 'admin') {
        fetchUsers(token);
    }

    // Load PC Info
    fetch('/api/system/info', {
        headers: { 'Authorization': `Bearer ${token}` }
    })
    .then(res => res.json())
    .then(data => setPcInfo(data))
    .catch(() => {})

    // Load Sync Config
    fetch('/api/sync/status', {
        headers: { 'Authorization': `Bearer ${token}` }
    })
    .then(res => res.json())
    .then(data => setSyncConfig(data))
    .catch(() => {})

    // Check Firewall Status
    fetch('/api/system/firewall/status', {
        headers: { 'Authorization': `Bearer ${token}` }
    })
    .then(res => res.json())
    .then(data => setFirewallStatus(data))
    .catch(() => {})
  }, [])

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

  if (!mounted) {
    return (
      <div className="p-6 flex items-center justify-center h-[70vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  const handleCreateUser = async () => {
    if (!newUser.username || !newUser.password) {
      toast.error("Vui lòng nhập tên đăng nhập và mật khẩu");
      return;
    }

    const payload = {
      ...newUser,
      allowed_gates: selectedGates.length === locations.length || selectedGates.length === 0 ? '*' : selectedGates.join(',')
    };

    try {
      const token = localStorage.getItem('token');
      const url = editingUsername 
        ? `/api/user/${editingUsername}`
        : '/api/user/register';
      
      const res = await fetch(url, {
        method: editingUsername ? 'PUT' : 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        toast.success(editingUsername ? `Đã cập nhật ${editingUsername}` : `Đã tạo người dùng ${newUser.username} thành công`);
        setNewUser({
          username: '', password: '', full_name: '', role: 'operator',
          allowed_gates: '*', can_manage_cameras: false, can_add_vehicles: false, vehicle_add_code: ''
        });
        setSelectedGates([]);
        setEditingUsername(null);
        setIsUserDialogOpen(false);
        const token = localStorage.getItem('token');
        fetchUsers(token);
      } else {
        const err = await res.json();
        toast.error(err.detail || "Lỗi khi tạo người dùng");
      }
    } catch (e) {
      toast.error("Không thể kết nối đến máy chủ");
    }
  };

  const handleDeleteUser = async (username: string) => {
    if (username === 'admin') {
        toast.error("Không thể xóa tài khoản Admin hệ thống");
        return;
    }
    if (!window.confirm(`Bạn có chắc muốn xóa tài khoản ${username}?`)) return;

    try {
        const token = localStorage.getItem('token');
        const res = await fetch(`/api/user/${username}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            toast.success("Đã xóa người dùng");
            fetchUsers(token);
        } else {
            toast.error("Lỗi khi xóa người dùng");
        }
    } catch (e) {
        toast.error("Lỗi kết nối");
    }
  };

  const handleOpenFirewall = async () => {
    setIsOpeningFirewall(true);
    try {
        const token = localStorage.getItem('token');
        const res = await fetch('/api/system/firewall/open', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        const data = await res.json();
        if (data.success) {
            toast.success(data.message);
            setFirewallStatus({ rule_exists: true, supported: true, message: "Đã mở firewall" });
        } else {
            toast.error(data.message || "Không thể thực hiện");
        }
    } catch (e) {
        toast.error("Lỗi khi gửi yêu cầu");
    } finally {
        setIsOpeningFirewall(false);
        setIsFirewallDialogOpen(false);
    }
  };

  const handleUpdateSync = async () => {
    try {
        const token = localStorage.getItem('token');
        const params = new URLSearchParams();
        params.append('is_destination', String(syncConfig.is_destination));
        if (syncConfig.remote_url) {
            params.append('remote_url', syncConfig.remote_url);
        }

        const res = await fetch(`/api/sync/configure?${params.toString()}`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (res.ok) {
            toast.success("Đã cập nhật cấu hình đồng bộ");
            const data = await res.json();
            setSyncConfig(prev => ({ ...prev, ...data }));
        } else {
            toast.error("Lỗi khi cập nhật cấu hình");
        }
    } catch (e) {
        toast.error("Lỗi kết nối máy chủ");
    }
  };

  const startEdit = (user: any) => {
    setEditingUsername(user.username);
    setNewUser({
        username: user.username,
        password: '', // Don't show hashed password, leave empty to keep current
        full_name: user.full_name || '',
        role: user.role || 'operator',
        allowed_gates: user.allowed_gates || '*',
        can_manage_cameras: user.can_manage_cameras === true,
        can_add_vehicles: user.can_add_vehicles === true,
        vehicle_add_code: user.vehicle_add_code || ''
    });
    
    if (user.allowed_gates === '*') {
        setSelectedGates([]);
    } else {
        setSelectedGates(user.allowed_gates.split(',').map((g: string) => g.trim()));
    }
    
    // Scroll to form
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const isDark = resolvedTheme === 'dark'
  const isAdmin = currentUser?.role === 'admin'

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="space-y-1">
        <div className="flex items-center gap-3">
          <SettingsIcon className="h-6 w-6 text-[#f59e0b]" />
          <h1 className="text-2xl font-bold tracking-tight">Cài đặt hệ thống</h1>
        </div>
        <p className="text-muted-foreground text-sm">
          Quản lý cấu hình cá nhân, thiết bị và hạ tầng.
        </p>
      </div>
      
      {/* 2x2/4x1 Window Layout */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 auto-rows-fr">
          {/* 1. User Info Panel */}
          <Card className="border-border shadow-md overflow-hidden flex flex-col h-full min-h-[300px]">
            <div className="h-24 bg-gradient-to-r from-amber-500/20 to-amber-500/5 relative shrink-0">
                <div className="absolute -bottom-8 left-8">
                    <div className="w-16 h-16 rounded-2xl bg-amber-500 flex items-center justify-center text-zinc-950 text-xl font-black shadow-xl border-4 border-background">
                        {currentUser?.username?.substring(0, 2).toUpperCase()}
                    </div>
                </div>
                <div className="absolute top-4 right-6">
                    <span className="text-[10px] font-semibold bg-amber-500/10 text-amber-500 px-3 py-1 rounded-full uppercase tracking-widest border border-amber-500/20">
                        Tài khoản đang hoạt động
                    </span>
                </div>
            </div>
            <CardContent className="pt-10 pb-6 flex-1 flex flex-col justify-between px-8">
                <div>
                    <h2 className="text-xl font-semibold tracking-tight">{currentUser?.full_name || currentUser?.username}</h2>
                    <p className="text-[10px] text-muted-foreground font-mono flex items-center gap-1.5 uppercase tracking-widest mt-1">
                        <ShieldCheck size={12} className="text-amber-500" />
                        VAI TRÒ HỆ THỐNG: <span className="text-foreground font-medium">{currentUser?.role || 'Khách'}</span>
                    </p>
                </div>

                <div className="space-y-3 py-2 border-y border-border/50">
                    <div className="flex items-center justify-between">
                        <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Mã định danh duy nhất</span>
                        <span className="font-mono text-[10px] bg-muted px-2 py-0.5 rounded text-foreground/80">{String(currentUser?.id || '---').split('-')[0]}...</span>
                    </div>
                    <div className="flex items-center justify-between">
                        <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Phạm vi truy cập</span>
                        <span className="text-amber-500 font-semibold text-[10px] uppercase tracking-tighter">
                            {currentUser?.allowed_gates === '*' ? 'Toàn quyền (Tất cả Cổng)' : 'Truy cập hạn chế'}
                        </span>
                    </div>
                </div>

                <Button variant="outline" size="sm" className="w-full text-[10px] h-8 font-semibold mt-2 hover:bg-destructive hover:text-white transition-all duration-300" onClick={() => {
                    localStorage.clear();
                    window.location.href = '/login';
                }}>
                    ĐĂNG XUẤT AN TOÀN
                </Button>
            </CardContent>
          </Card>

          {/* 2. PC Info Panel */}
          <Card className="bg-card border-border shadow-md flex flex-col h-full min-h-[300px]">
            <CardHeader className="py-4 px-6 border-b border-border/50 bg-muted/20 shrink-0">
                <CardTitle className="text-[10px] font-semibold flex items-center gap-2 uppercase tracking-[0.2em] text-foreground">
                    <Monitor className="h-4 w-4 text-amber-500" />
                    Thông số thiết bị đầu cuối
                </CardTitle>
            </CardHeader>
            <CardContent className="p-6 flex-1 overflow-y-auto">
                <div className="grid grid-cols-2 gap-y-5 gap-x-6">
                    <div className="space-y-1">
                        <p className="text-[10px] text-muted-foreground uppercase font-semibold tracking-widest">Tên máy chủ</p>
                        <p className="font-mono font-medium truncate text-[12px]">{pcInfo?.pc_name || 'ĐANG TẢI...'}</p>
                    </div>
                    <div className="space-y-1">
                        <p className="text-[10px] text-muted-foreground uppercase font-semibold tracking-widest">Hệ điều hành</p>
                        <p className="font-mono font-medium text-[12px]">{pcInfo?.os || '---'}</p>
                    </div>
                    <div className="space-y-1">
                        <p className="text-[10px] text-muted-foreground uppercase font-semibold tracking-widest">Dung lượng Bộ nhớ</p>
                        <p className="font-mono font-medium text-[12px]">{pcInfo?.ram || '---'}</p>
                    </div>
                    <div className="space-y-1">
                        <p className="text-[10px] text-muted-foreground uppercase font-semibold tracking-widest">Địa chỉ IP</p>
                        <p className="font-mono font-semibold text-[12px] text-amber-500">{pcInfo?.ip_address || '---'}</p>
                    </div>
                    <div className="col-span-2 space-y-1 pt-2">
                        <p className="text-[10px] text-muted-foreground uppercase font-semibold tracking-widest">Vi xử lý (CPU)</p>
                        <p className="font-mono text-[11px] bg-muted/50 p-2 rounded-lg text-foreground/70 italic border border-border/50">
                            {pcInfo?.processor || 'ĐANG TRUY XUẤT THÔNG TIN...'}
                        </p>
                    </div>
                </div>
            </CardContent>
          </Card>

          {/* 3. Theme Panel */}
          <Card className="shadow-md border-border flex flex-col h-full min-h-[300px]">
            <CardHeader className="py-3 px-6 border-b border-border/50 bg-muted/20 shrink-0">
              <CardTitle className="text-[10px] font-semibold flex items-center gap-2 uppercase tracking-[0.2em] text-foreground">
                {isDark ? <Moon className="h-4 w-4 text-amber-500" /> : <Sun className="h-4 w-4 text-amber-500" />}
                Tùy chỉnh giao diện
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 flex-1 flex flex-col justify-center gap-5">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                    <Label className="text-xs font-semibold uppercase tracking-tight">Chế độ tối (Dark Mode)</Label>
                    <p className="text-[10px] text-muted-foreground italic font-medium opacity-70">Tối ưu cho môi trường ánh sáng yếu.</p>
                </div>
                <Switch checked={isDark} onCheckedChange={(c) => setTheme(c ? 'dark' : 'light')} />
              </div>
              <div className="flex gap-1.5 p-1 bg-muted/50 rounded-xl border border-border/50">
                {['light', 'dark', 'system'].map((t) => (
                    <button
                        key={t}
                        onClick={() => setTheme(t)}
                        className={`flex-1 py-1.5 text-[10px] font-semibold rounded-lg transition-all uppercase tracking-widest ${
                            theme === t ? 'bg-background text-amber-500 shadow-sm ring-1 ring-border' : 'text-muted-foreground hover:bg-background/40'
                        }`}
                    >
                        {t === 'light' ? 'Sáng' : t === 'dark' ? 'Tối' : 'Hệ thống'}
                    </button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* 4. Sync Panel */}
          <Card className="shadow-md border-border flex flex-col h-full min-h-[300px]">
            <CardHeader className="py-3 px-6 border-b border-border/50 bg-muted/20 shrink-0">
              <CardTitle className="text-[10px] font-semibold flex items-center justify-between gap-2 uppercase tracking-[0.2em] text-foreground">
                <div className="flex items-center gap-2">
                    <Server className="h-4 w-4 text-amber-500" />
                    Đồng bộ Dữ liệu
                </div>
                <span className={`text-[9px] font-bold px-3 py-1 rounded-full border flex items-center justify-center min-w-[70px] ${syncConfig.is_destination ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/30' : 'bg-amber-500/10 text-amber-500 border-amber-500/30'}`}>
                    {syncConfig.is_destination ? 'MÁY CHỦ' : 'TRẠM CUỐI'}
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 flex-1 flex flex-col space-y-2">
              {/* CLIENT MODE - View Only */}
              {!syncConfig.is_destination ? (
                <div className="flex-1 flex flex-col space-y-4">
                  <div className="p-3 rounded-xl bg-amber-500/5 border border-amber-500/20">
                    <p className="text-[10px] uppercase text-amber-500 font-semibold tracking-widest mb-1">MÁY CHỦ ĐANG KẾT NỐI</p>
                    <p className="font-mono text-sm text-amber-500 font-medium truncate">{syncConfig.remote_url || 'CHƯA XÁC ĐỊNH'}</p>
                  </div>
                  
                  <Button 
                    variant="outline"
                    className="h-9 text-[10px] font-semibold border-amber-500/50 text-amber-500 hover:bg-amber-500/10 transition-colors" 
                    onClick={async () => {
                      const token = localStorage.getItem('token');
                      toast.loading("Kiểm tra kết nối...", { id: 'sync-test' });
                      try {
                        const res = await fetch('/api/sync/test-push', { 
                          method: 'POST',
                          headers: { 'Authorization': `Bearer ${token}` }
                        });
                        const data = await res.json();
                        if (data.success) {
                          toast.success(data.message, { id: 'sync-test' });
                        } else {
                          toast.error(data.message, { id: 'sync-test' });
                        }
                      } catch (e) {
                        toast.error("Lỗi kết nối máy chủ", { id: 'sync-test' });
                      }
                    }}
                  >
                    CHẨN ĐOÁN KẾT NỐI
                  </Button>
                </div>
              ) : (
                /* MASTER MODE - Token Setup */
                <div className="flex-1 flex flex-col space-y-3">
                  <div className="flex flex-col gap-1.5">
                    <Label className="text-[10px] uppercase text-muted-foreground font-semibold tracking-widest px-1">
                      Địa chỉ nhận kết nối (Endpoint)
                    </Label>
                    <div className="flex gap-2">
                      <Input 
                        readOnly
                        value={pcInfo ? `http://${pcInfo.ip_address}:8000` : 'ĐANG DÒ TÌM...'}
                        className="h-8 text-[11px] font-mono font-medium bg-muted/30 flex-1 border-border/50 ring-0 focus-visible:ring-0"
                      />
                      <Button 
                        variant="secondary" 
                        size="sm" 
                        className="h-8 text-[10px] font-semibold px-4"
                        onClick={() => {
                          if (pcInfo?.ip_address) {
                            navigator.clipboard.writeText(`http://${pcInfo.ip_address}:8000`);
                            toast.success("Đã sao chép vào bộ nhớ tạm!");
                          }
                        }}
                      >
                        SAO CHÉP
                      </Button>
                    </div>
                  </div>

                  <div className="flex-1 flex flex-col justify-end text-center space-y-2">
                    <div className="flex items-center justify-center gap-3">
                      <span className={`text-[10px] uppercase font-semibold flex items-center gap-2 ${firewallStatus.rule_exists ? 'text-emerald-500' : 'text-amber-500'}`}>
                        <ShieldCheck size={12} />
                        {firewallStatus.message || 'SYS: ĐANG KIỂM TRA'}
                      </span>
                      {!firewallStatus.rule_exists && firewallStatus.supported && (
                        <Button 
                          size="sm" 
                          variant="outline" 
                          className="h-6 text-[9px] font-semibold bg-amber-500/5 hover:bg-amber-500/10 text-amber-500 border border-amber-500/30 rounded-full px-4"
                          onClick={() => setIsFirewallDialogOpen(true)}
                          disabled={isOpeningFirewall}
                        >
                          {isOpeningFirewall ? 'ĐANG TRIỂN KHAI...' : 'GỠ LỖI NHANH'}
                        </Button>
                      )}
                    </div>
                    <p className="text-[9px] text-muted-foreground font-mono opacity-60 uppercase leading-none tracking-tight py-1 border-t border-border/30">
                        Giao thức: TCP | Cổng Inbound: 8000 (Mở)
                    </p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
      </div>

      {/* Admin User List (Full Width) */}
      {isAdmin ? (
        <Card className="border-border shadow-lg overflow-hidden lg:col-span-12">
            <CardHeader className="bg-muted/30 pb-4 border-b border-border">
                <div className="flex items-center justify-between">
                    <div className="space-y-1">
                        <CardTitle className="text-lg flex items-center gap-2">
                            <UserIcon className="h-5 w-5 text-amber-500" />
                            Quản lý tài khoản
                        </CardTitle>
                        <CardDescription className="text-xs">Danh sách nhân sự và phân quyền truy cập hệ thống.</CardDescription>
                    </div>
                    <Button 
                        size="sm" 
                        className="bg-amber-500 hover:bg-amber-600 text-zinc-950 font-bold text-xs gap-2"
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
                        + Thêm nhân sự
                    </Button>
                </div>
            </CardHeader>
            <CardContent className="p-0">
                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                        <thead className="text-xs uppercase bg-muted/50 border-y border-border">
                            <tr>
                                <th className="px-6 py-3 font-semibold">Tên đăng nhập</th>
                                <th className="px-6 py-3 font-semibold">Họ và tên</th>
                                <th className="px-6 py-3 font-semibold">Vai trò</th>
                                <th className="px-6 py-3 font-semibold">Cổng/Cameras/Xe</th>
                                <th className="px-6 py-3 font-semibold text-right">Thao tác</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                            {userList.map((user) => (
                                <tr key={user.id} className="hover:bg-muted/20 transition-colors">
                                    <td className="px-6 py-4 font-medium flex items-center gap-2">
                                        <div className="w-8 h-8 rounded-full bg-amber-500/10 flex items-center justify-center text-amber-500 text-xs">
                                            {user.username.substring(0,2).toUpperCase()}
                                        </div>
                                        {user.username}
                                    </td>
                                    <td className="px-6 py-4 text-muted-foreground">{user.full_name || '---'}</td>
                                    <td className="px-6 py-4">
                                        <span className={`px-2 py-0.5 rounded-full text-[10px] uppercase font-bold ${
                                            user.role === 'admin' ? 'bg-amber-500/20 text-amber-500' : 'bg-blue-500/20 text-blue-500'
                                        }`}>
                                            {user.role}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex flex-col gap-1">
                                            <div className="flex items-center gap-1.5 text-[10px]">
                                                <MapPin className="h-2.5 w-2.5" />
                                                <span className="truncate max-w-[150px]">{user.allowed_gates === '*' ? 'Tất cả (*)' : user.allowed_gates}</span>
                                            </div>
                                            <div className="flex items-center gap-3 text-[10px]">
                                                <span className={`flex items-center gap-1 ${user.can_manage_cameras ? 'text-green-500' : 'text-red-500'}`}>
                                                    <Camera className="h-2.5 w-2.5" /> {user.can_manage_cameras ? 'Bật' : 'Tắt'}
                                                </span>
                                                <span className={`flex items-center gap-1 ${user.can_add_vehicles ? 'text-green-500' : 'text-red-500'}`}>
                                                    <CarFront className="h-2.5 w-2.5" /> {user.can_add_vehicles ? 'Bật' : 'Tắt'}
                                                </span>
                                                {user.can_add_vehicles && (
                                                    <span className="text-zinc-500 flex items-center gap-1">
                                                        <Key className="h-2.5 w-2.5" /> {user.vehicle_add_code}
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 text-right">
                                        <div className="flex items-center justify-end gap-1">
                                            <Button 
                                                variant="ghost" 
                                                size="sm" 
                                                className="text-muted-foreground hover:text-blue-500 h-8 w-8 p-0"
                                                onClick={() => {
                                                    startEdit(user);
                                                    setIsUserDialogOpen(true);
                                                }}
                                            >
                                                <Edit2 className="h-4 w-4" />
                                            </Button>
                                            <Button 
                                                variant="ghost" 
                                                size="sm" 
                                                className="text-muted-foreground hover:text-destructive h-8 w-8 p-0"
                                                disabled={user.username === 'admin'}
                                                onClick={() => handleDeleteUser(user.username)}
                                            >
                                                <Trash2 className="h-4 w-4" />
                                            </Button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                            {userList.length === 0 && (
                                <tr>
                                    <td colSpan={5} className="px-6 py-10 text-center text-muted-foreground">
                                        Đang tải danh sách...
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </CardContent>
        </Card>
      ) : null}

      {/* Add/Edit User Dialog */}
      <Dialog 
        isOpen={isUserDialogOpen} 
        onClose={() => setIsUserDialogOpen(false)}
        title={editingUsername ? `Sửa tài khoản: ${editingUsername}` : 'Thêm nhân sự mới'}
        maxWidth="xl"
      >
        <div className="space-y-6 pt-2">
            <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                <Label className="text-xs">Tên đăng nhập</Label>
                <Input 
                    value={newUser.username} 
                    onChange={e=>setNewUser({...newUser, username: e.target.value})} 
                    placeholder="username" 
                    className="h-9 font-sans" 
                    disabled={!!editingUsername}
                />
                </div>
                <div className="space-y-1">
                <Label className="text-xs">{editingUsername ? 'Mật khẩu mới (bỏ trống nếu giữ nguyên)' : 'Mật khẩu'}</Label>
                <Input type="password" value={newUser.password} onChange={e=>setNewUser({...newUser, password: e.target.value})} placeholder="••••••" className="h-9 font-sans" />
                </div>
            </div>

            <div className="space-y-1">
                <Label className="text-xs">Họ và tên</Label>
                <Input value={newUser.full_name} onChange={e=>setNewUser({...newUser, full_name: e.target.value})} placeholder="Nguyễn Văn A" className="h-9 font-sans" />
            </div>

            <div className="space-y-4 pt-4 border-t border-border">
                <div className="space-y-2">
                <Label className="text-[11px] uppercase tracking-wider text-muted-foreground font-bold italic">Quyền truy cập Cổng:</Label>
                <div className="flex flex-wrap gap-2">
                    {locations.map(loc => (
                        <Button 
                            key={loc} 
                            variant={selectedGates.includes(loc) ? 'default' : 'outline'} 
                            size="sm"
                            className="h-8 text-[11px] px-3 font-semibold"
                            onClick={() => {
                                setSelectedGates(prev => 
                                    prev.includes(loc) ? prev.filter(g => g !== loc) : [...prev, loc]
                                )
                            }}
                        >
                            {loc}
                        </Button>
                    ))}
                    <Button 
                        variant={selectedGates.length === 0 ? 'secondary' : 'outline'} 
                        size="sm" className="h-8 text-[11px] px-3 font-bold"
                        onClick={() => setSelectedGates([])}
                    >Tất cả (*)</Button>
                </div>
                </div>

                <div className="grid grid-cols-2 gap-6 pt-2">
                    <div className="flex items-center justify-between p-2 rounded-lg bg-muted/50 border border-border">
                        <div className="space-y-0.5">
                            <Label className="text-xs font-bold">Chỉnh sửa Camera</Label>
                            <p className="text-[9px] text-muted-foreground italic leading-tight">Quyền cấu hình/thêm cam.</p>
                        </div>
                        <Switch checked={newUser.can_manage_cameras} onCheckedChange={c=>setNewUser({...newUser, can_manage_cameras: c})} />
                    </div>

                    <div className="flex flex-col gap-2 p-2 rounded-lg bg-muted/50 border border-border">
                        <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                                <Label className="text-xs font-bold">Thêm xe mới</Label>
                                <p className="text-[9px] text-muted-foreground italic leading-tight">Yêu cầu mã Admin khi thêm.</p>
                            </div>
                            <Switch checked={newUser.can_add_vehicles} onCheckedChange={c=>setNewUser({...newUser, can_add_vehicles: c})} />
                        </div>
                        {newUser.can_add_vehicles && (
                            <div className="flex items-center gap-2 animate-in slide-in-from-top-1">
                                <span className="text-[9px] font-bold text-amber-500 uppercase">Code:</span>
                                <Input 
                                    value={newUser.vehicle_add_code} 
                                    onChange={e=>setNewUser({...newUser, vehicle_add_code: e.target.value})} 
                                    placeholder="ADMIN123" 
                                    className="h-7 text-xs font-mono bg-background"
                                />
                            </div>
                        )}
                    </div>
                </div>
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t border-border">
                <Button variant="ghost" size="sm" onClick={() => setIsUserDialogOpen(false)}>Hủy</Button>
                <Button className="bg-amber-500 hover:bg-amber-600 text-zinc-950 font-black px-8" onClick={handleCreateUser}>
                    {editingUsername ? 'CẬP NHẬT' : 'TẠO TÀI KHOẢN'}
                </Button>
            </div>
        </div>
      </Dialog>
      
      {/* Firewall Confirmation Dialog */}
      <Dialog
        isOpen={isFirewallDialogOpen}
        onClose={() => !isOpeningFirewall && setIsFirewallDialogOpen(false)}
        title="Yêu cầu cấu hình hệ thống"
        maxWidth="md"
      >
        <div className="space-y-6 pt-2">
            <div className="flex flex-col items-center text-center space-y-4">
                <div className="w-16 h-16 rounded-full bg-amber-500/10 flex items-center justify-center text-amber-500 animate-pulse">
                    <ShieldCheck size={32} />
                </div>
                <div className="space-y-2">
                    <h3 className="text-lg font-bold">Tự động cấu hình Windows Firewall</h3>
                    <p className="text-sm text-muted-foreground leading-relaxed">
                        Hệ thống sẽ thử tự động mở cổng <span className="font-bold text-foreground">8000</span> để cho phép các máy Client kết nối đến máy chủ này.
                    </p>
                </div>
            </div>

            <div className="bg-muted px-4 py-3 rounded-lg border border-border space-y-2">
                <p className="text-[11px] font-bold uppercase text-amber-500 flex items-center gap-2">
                    <Monitor size={12} /> HƯỚNG DẪN QUAN TRỌNG:
                </p>
                <ol className="text-[11px] text-muted-foreground list-decimal list-inside space-y-1">
                    <li>Sau khi nhấn <span className="text-foreground font-bold">XÁC NHẬN</span>, một cửa sổ Windows (UAC) sẽ hiện ra.</li>
                    <li>Bạn <span className="text-foreground font-bold underline">CẦN PHẢI CHỌN &quot;YES&quot;</span> để cấp quyền Administrator.</li>
                    <li>Nếu không thấy cửa sổ, hãy kiểm tra thanh Taskbar phía dưới.</li>
                </ol>
            </div>

            <div className="flex gap-3 pt-2">
                <Button 
                    variant="ghost" 
                    className="flex-1 h-10 font-bold" 
                    onClick={() => setIsFirewallDialogOpen(false)}
                    disabled={isOpeningFirewall}
                >
                    HỦY BỎ
                </Button>
                <Button 
                    className="flex-[2] bg-amber-500 hover:bg-amber-600 text-zinc-950 font-black h-10" 
                    onClick={handleOpenFirewall}
                    disabled={isOpeningFirewall}
                >
                    {isOpeningFirewall ? 'ĐANG XỬ LÝ...' : 'XÁC NHẬN VÀ TIẾP TỤC'}
                </Button>
            </div>
        </div>
      </Dialog>
    </div>
  )
}
