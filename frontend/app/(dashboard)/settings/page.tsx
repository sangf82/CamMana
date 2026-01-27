'use client'

import React from 'react'
import { useTheme } from 'next-themes'
import { Sun, Moon, Monitor, Settings as SettingsIcon, ShieldCheck, User as UserIcon, Trash2, Key, MapPin, Camera, CarFront, Edit2, X } from 'lucide-react'
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
    status: 'standalone'
  })

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
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
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
      
      {/* 2x2 Window Layout */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* 1. User Info Panel */}
          <Card className="border-border shadow-md overflow-hidden flex flex-col h-[300px]">
            <div className="h-20 bg-gradient-to-r from-amber-500/20 to-amber-500/5 relative shrink-0">
                <div className="absolute -bottom-8 left-6">
                    <div className="w-16 h-16 rounded-xl bg-amber-500 flex items-center justify-center text-zinc-950 text-xl font-black shadow-lg border-2 border-background">
                        {currentUser?.username?.substring(0, 2).toUpperCase()}
                    </div>
                </div>
            </div>
            <CardContent className="pt-10 pb-4 flex-1 flex flex-col justify-between">
                <div>
                    <h2 className="text-lg font-bold leading-tight">{currentUser?.full_name || currentUser?.username}</h2>
                    <p className="text-[10px] text-muted-foreground font-mono flex items-center gap-1.5 uppercase tracking-tighter">
                        <ShieldCheck size={10} className="text-amber-500" />
                        Trạng thái: <span className="text-foreground">{currentUser?.role || 'Guest'}</span>
                    </p>
                </div>

                <div className="space-y-2 text-xs">
                    <div className="flex items-center justify-between">
                        <span className="text-muted-foreground">ID định danh:</span>
                        <span className="font-mono text-[10px] bg-muted px-1.5 py-0.5 rounded">{String(currentUser?.id || '').split('-')[0]}...</span>
                    </div>
                    <div className="flex items-center justify-between">
                        <span className="text-muted-foreground">Quyền Gate:</span>
                        <span className="bg-amber-500/10 text-amber-500 px-2 py-0.5 rounded-full font-bold text-[10px]">{currentUser?.allowed_gates === '*' ? 'Tất cả' : 'Hạn chế'}</span>
                    </div>
                </div>

                <Button variant="outline" size="sm" className="w-full text-[10px] h-7 font-bold mt-2" onClick={() => {
                    localStorage.clear();
                    window.location.href = '/login';
                }}>
                    ĐĂNG XUẤT TÀI KHOẢN
                </Button>
            </CardContent>
          </Card>

          {/* 2. PC Info Panel */}
          <Card className="bg-card border-border shadow-md h-[300px] flex flex-col">
            <CardHeader className="pb-2 border-b border-border/50 bg-muted/20 shrink-0">
                <CardTitle className="text-xs font-bold flex items-center gap-2 uppercase tracking-widest text-blue-500">
                    <Monitor className="h-4 w-4" />
                    Thiết bị đầu cuối
                </CardTitle>
            </CardHeader>
            <CardContent className="pt-4 flex-1 overflow-y-auto">
                <div className="grid grid-cols-2 gap-y-4 gap-x-4 text-[11px]">
                    <div className="space-y-0.5">
                        <p className="text-[10px] text-muted-foreground uppercase font-bold">Host Name</p>
                        <p className="font-semibold truncate text-[12px]">{pcInfo?.pc_name || 'Đang tải...'}</p>
                    </div>
                    <div className="space-y-0.5">
                        <p className="text-[10px] text-muted-foreground uppercase font-bold">OS Version</p>
                        <p className="font-semibold text-[12px]">{pcInfo?.os || '---'}</p>
                    </div>
                    <div className="space-y-0.5">
                        <p className="text-[10px] text-muted-foreground uppercase font-bold">Physical RAM</p>
                        <p className="font-semibold text-[12px]">{pcInfo?.ram || '---'}</p>
                    </div>
                    <div className="space-y-0.5">
                        <p className="text-[10px] text-muted-foreground uppercase font-bold">Network IP</p>
                        <p className="font-semibold font-mono text-[12px]">{pcInfo?.ip_address || '---'}</p>
                    </div>
                    <div className="col-span-2 space-y-0.5 pt-1">
                        <p className="text-[10px] text-muted-foreground uppercase font-bold">Processor Unit</p>
                        <p className="font-semibold truncate text-[11px] bg-muted/50 p-1 rounded italic">{pcInfo?.processor || '---'}</p>
                    </div>
                </div>
            </CardContent>
          </Card>

          {/* 3. Theme Panel */}
          <Card className="shadow-md border-border h-[200px] flex flex-col">
            <CardHeader className="pb-3 border-b border-border/50 bg-muted/20 shrink-0">
              <CardTitle className="text-xs font-bold flex items-center gap-2 uppercase tracking-widest text-amber-500">
                {isDark ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
                Tùy chỉnh thị giác
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6 flex-1 flex flex-col justify-center gap-6">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                    <Label className="text-xs font-bold">Chế độ tối (Dark mode)</Label>
                    <p className="text-[9px] text-muted-foreground italic">Phù hợp làm việc ban đêm.</p>
                </div>
                <Switch checked={isDark} onCheckedChange={(c) => setTheme(c ? 'dark' : 'light')} />
              </div>
              <div className="flex gap-1 p-1 bg-muted rounded-lg border border-border">
                {['light', 'dark', 'system'].map((t) => (
                    <button
                        key={t}
                        onClick={() => setTheme(t)}
                        className={`flex-1 py-2 text-[10px] font-black rounded transition-all uppercase tracking-tighter ${
                            theme === t ? 'bg-background text-foreground shadow-md ring-1 ring-border' : 'text-muted-foreground hover:bg-background/40'
                        }`}
                    >
                        {t === 'light' ? 'Sáng' : t === 'dark' ? 'Tối' : 'Hệ thống'}
                    </button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* 4. Sync Panel */}
          <Card className="shadow-md border-border h-[280px] flex flex-col">
            <CardHeader className="pb-3 border-b border-border/50 bg-muted/20 shrink-0">
              <CardTitle className="text-xs font-bold flex items-center justify-between gap-2 uppercase tracking-widest text-blue-500">
                <div className="flex items-center gap-2">
                    <Monitor className="h-4 w-4" />
                    Đồng bộ hạ tầng
                </div>
                <span className={`text-[10px] px-2 py-0.5 rounded-full ${syncConfig.is_destination ? 'bg-green-500/20 text-green-500' : 'bg-blue-500/20 text-blue-500'}`}>
                    {syncConfig.is_destination ? 'MASTER' : 'CLIENT'}
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4 flex-1 flex flex-col space-y-4">
              {/* CLIENT MODE - View Only */}
              {!syncConfig.is_destination ? (
                <div className="flex-1 flex flex-col space-y-4">
                  <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/30">
                    <p className="text-[10px] uppercase text-blue-400 font-black tracking-widest mb-1">Đang kết nối đến Master</p>
                    <p className="font-mono text-sm text-blue-500 truncate">{syncConfig.remote_url || 'Chưa cấu hình'}</p>
                  </div>
                  
                  <div className="flex-1 flex flex-col justify-center text-center opacity-60">
                    <p className="text-[10px] text-muted-foreground italic">
                      Dữ liệu đang được đồng bộ từ máy chủ Master.<br/>
                      Để thay đổi chế độ, vui lòng quay lại trang Đăng nhập.
                    </p>
                  </div>

                  <Button 
                    variant="outline"
                    className="h-8 text-[10px] font-black border-blue-600 text-blue-600" 
                    onClick={async () => {
                      const token = localStorage.getItem('token');
                      toast.loading("Đang kiểm tra kết nối...", { id: 'sync-test' });
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
                        toast.error("Lỗi kết nối đến máy chủ nội bộ", { id: 'sync-test' });
                      }
                    }}
                  >
                    KIỂM TRA KẾT NỐI ĐẾN MASTER
                  </Button>
                </div>
              ) : (
                /* MASTER MODE - Token Setup */
                <div className="flex-1 flex flex-col space-y-4">
                  <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/30">
                    <p className="text-[10px] uppercase text-green-400 font-black tracking-widest mb-1">Trạng thái</p>
                    <p className="text-sm text-green-500">✓ PC này đang hoạt động ở chế độ Master</p>
                  </div>
                  
                  <div className="space-y-2">
                    <Label className="text-[10px] uppercase text-muted-foreground font-black tracking-widest">
                      Địa chỉ để Client kết nối
                    </Label>
                    <div className="flex gap-2">
                      <Input 
                        readOnly
                        value={pcInfo ? `http://${pcInfo.ip_address}:8000` : 'Đang tải...'}
                        className="h-8 text-xs font-mono bg-muted flex-1"
                      />
                      <Button 
                        variant="outline" 
                        size="sm" 
                        className="h-8 text-[10px]"
                        onClick={() => {
                          if (pcInfo?.ip_address) {
                            navigator.clipboard.writeText(`http://${pcInfo.ip_address}:8000`);
                            toast.success("Đã sao chép địa chỉ!");
                          }
                        }}
                      >
                        COPY
                      </Button>
                    </div>
                  </div>

                  <div className="flex-1 flex flex-col justify-center text-center opacity-60">
                    <p className="text-[10px] text-muted-foreground italic">
                      Các PC Client sẽ kết nối đến địa chỉ này để đồng bộ dữ liệu.<br/>
                      Đảm bảo tường lửa cho phép cổng 8000.
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
      ) : (
        <Card className="lg:col-span-12 bg-muted/20 border-dashed">
            <CardContent className="py-12 flex flex-col items-center justify-center text-center opacity-50">
                <ShieldCheck size={48} className="text-muted-foreground mb-4" />
                <p className="text-sm">Bạn không có quyền xem danh sách người dùng.</p>
            </CardContent>
        </Card>
      )}

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
    </div>
  )
}
