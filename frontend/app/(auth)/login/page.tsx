"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import { Lock, User, ShieldCheck, Eye, EyeOff, Monitor, Wifi, Globe, Server, CheckCircle2, AlertCircle, RefreshCw } from "lucide-react";
import Dialog from "@/components/ui/dialog";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isSyncDialogOpen, setIsSyncDialogOpen] = useState(false);
  const [discoveryList, setDiscoveryList] = useState<any[]>([]);
  const [isScanning, setIsScanning] = useState(false);
  const [syncStatus, setSyncStatus] = useState<any>(null);
  const router = useRouter();

  const fetchSyncStatus = async () => {
    try {
        const res = await fetch("http://127.0.0.1:8000/api/sync/status");
        if (res.ok) setSyncStatus(await res.json());
    } catch (e) {}
  };

  const startDiscovery = async () => {
    setIsScanning(true);
    try {
        const res = await fetch("http://127.0.0.1:8000/api/sync/discover");
        if (res.ok) {
            const rawList = await res.json();
            // Parse cleaner names from Zeroconf format
            // e.g., "DESKTOP-4C6855B._cammana-sync._tcp.local." -> "DESKTOP-4C6855B"
            const cleanedList = rawList.map((pc: any) => {
                let cleanName = pc.name;
                // Remove the Zeroconf service suffix
                const suffixIndex = cleanName.indexOf('._cammana-sync');
                if (suffixIndex > 0) {
                    cleanName = cleanName.substring(0, suffixIndex);
                }
                // Also remove trailing dots
                cleanName = cleanName.replace(/\.$/, '');
                
                return {
                    ...pc,
                    displayName: cleanName,
                    originalName: pc.name
                };
            });
            setDiscoveryList(cleanedList);
        }
    } catch (e) {
        toast.error("Không thể quét mạng nội bộ");
    } finally {
        setIsScanning(false);
    }
  };

  const [isConnecting, setIsConnecting] = useState<string | null>(null);

  const connectToMaster = async (url: string, displayName?: string) => {
    setIsConnecting(url);
    
    try {
        // Step 1: Check if the Master is reachable
        toast.info(`Đang kiểm tra kết nối đến ${displayName || url}...`);
        
        const checkRes = await fetch(`${url}/api/sync/status`, {
            signal: AbortSignal.timeout(5000) // 5 second timeout
        });
        
        if (!checkRes.ok) {
            toast.error(`Không thể kết nối: Master trả về lỗi ${checkRes.status}`);
            setIsConnecting(null);
            return;
        }
        
        const masterStatus = await checkRes.json();
        
        // Verify it's actually a Master (is_destination = true)
        if (!masterStatus.is_destination) {
            toast.error("Thiết bị này không phải là Master (PC Chủ)");
            setIsConnecting(null);
            return;
        }
        
        // Step 2: Configure local backend to use this Master
        const params = new URLSearchParams();
        params.append('remote_url', url);
        params.append('is_destination', 'false');
        
        const res = await fetch(`http://127.0.0.1:8000/api/sync/configure?${params.toString()}`, {
            method: 'POST'
        });
        
        if (res.ok) {
            toast.success(`Đã kết nối với ${displayName || 'Master PC'}!`);
            setIsSyncDialogOpen(false);
            fetchSyncStatus();
        } else {
            toast.error("Không thể lưu cấu hình kết nối");
        }
    } catch (e: any) {
        if (e.name === 'TimeoutError' || e.name === 'AbortError') {
            toast.error(`Không thể kết nối: Hết thời gian chờ (${displayName || url})`);
        } else {
            toast.error(`Lỗi kết nối: ${e.message || 'Không xác định'}`);
        }
    } finally {
        setIsConnecting(null);
    }
  };

  const useAsMaster = async () => {
    try {
        const res = await fetch(`http://127.0.0.1:8000/api/sync/configure?is_destination=true`, {
            method: 'POST'
        });
        if (res.ok) {
            toast.success("Đang chạy ở chế độ Master (Lưu trữ dữ liệu)");
            setIsSyncDialogOpen(false);
            fetchSyncStatus();
        }
    } catch (e) {}
  };

  useEffect(() => {
    fetchSyncStatus();
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const formData = new FormData();
      formData.append("username", username);
      formData.append("password", password);

      const response = await fetch("http://127.0.0.1:8000/api/user/login", {
        method: "POST",
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();
        localStorage.setItem("token", data.access_token);
        localStorage.setItem("user", JSON.stringify(data.user));
        toast.success("Đăng nhập thành công!");
        router.push("/monitor");
      } else {
        const error = await response.json();
        toast.error(error.detail || "Đăng nhập thất bại");
      }
    } catch (error) {
      toast.error("Không thể kết nối đến máy chủ");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-background relative overflow-hidden font-sans">
      {/* Yellow/Orange gradient highlight in top left */}
      <div className="absolute top-0 left-0 w-[60%] h-[60%] bg-gradient-to-br from-amber-500/30 via-orange-500/20 to-transparent blur-[60px] rounded-full" />
      <div className="absolute top-[-20%] left-[-20%] w-[50%] h-[50%] bg-amber-400/25 blur-[80px] rounded-full" />
      
      {/* Subtle secondary glow */}
      <div className="absolute bottom-[-10%] right-[-10%] w-[30%] h-[30%] bg-muted-foreground/5 blur-[100px] rounded-full" />
      
      {/* Grid Pattern Background - Clear and visible */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,var(--border)_1px,transparent_1px),linear-gradient(to_bottom,var(--border)_1px,transparent_1px)] bg-[size:48px_48px] opacity-10" />
      
      {/* Radial fade overlay for grid - softer fade */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,transparent_30%,var(--background)_80%)]" />

      <Card className="w-full max-w-md border-border/50 bg-card/50 backdrop-blur-xl shadow-2xl relative z-10 transition-all duration-300 hover:border-amber-500/20">
        <CardHeader className="space-y-1 pb-6 text-center">
            <div className="flex justify-center mb-4">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-amber-400 to-amber-600 flex items-center justify-center shadow-lg shadow-amber-500/20">
                    <ShieldCheck className="w-10 h-10 text-black" />
                </div>
            </div>
          <CardTitle className="text-3xl font-bold tracking-tight text-foreground font-sans">CamMana</CardTitle>
          <CardDescription className="text-muted-foreground">
            Hệ thống giám sát & Quản lý Gate
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleLogin}>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username" className="text-foreground">Tài khoản</Label>
              <div className="relative group">
                <Input
                  id="username"
                  placeholder="Nhập tên đăng nhập"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="pl-10 h-11 bg-background/50 border-input text-foreground placeholder:text-muted-foreground focus:border-amber-500/50 transition-all duration-300"
                  required
                />
                <div className="absolute left-3 top-1/2 -translate-y-1/2 text-amber-500/70 group-focus-within:text-amber-500 transition-colors">
                    <User className="h-4.5 w-4.5" />
                </div>
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="password" className="text-foreground">Mật khẩu</Label>
              </div>
              <div className="relative group">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-10 h-11 bg-background/50 border-input text-foreground placeholder:text-muted-foreground focus:border-amber-500/50 transition-all duration-300"
                  required
                />
                <div className="absolute left-3 top-1/2 -translate-y-1/2 text-amber-500/70 group-focus-within:text-amber-500 transition-colors">
                    <Lock className="h-4.5 w-4.5" />
                </div>
              </div>
            </div>
          </CardContent>
          <CardFooter className="flex flex-col space-y-4 pt-2 pb-8">
            <Button 
                type="submit" 
                className="w-full bg-amber-500 hover:bg-amber-400 text-black font-bold h-11 shadow-lg shadow-amber-500/20 transition-all active:scale-[0.98]"
                disabled={isLoading}
            >
              {isLoading ? "Đang đăng nhập..." : "Đăng nhập"}
            </Button>

            <div className="w-full flex items-center justify-between text-[10px] text-muted-foreground border-t border-border/50 pt-4">
                <div className="flex items-center gap-1.5">
                    <div className={`w-1.5 h-1.5 rounded-full ${syncStatus?.is_destination ? 'bg-success' : 'bg-info'} animate-pulse`} />
                    <span className="uppercase tracking-widest font-bold">
                        {syncStatus?.mode || 'ĐANG TẢI...'}
                    </span>
                </div>
                <button 
                    type="button" 
                    onClick={() => {
                        setIsSyncDialogOpen(true);
                        startDiscovery();
                    }}
                    className="hover:text-amber-500 transition-colors uppercase font-black"
                >
                    ĐỔI CHẾ ĐỘ KẾT NỐI
                </button>
            </div>
          </CardFooter>
        </form>
      </Card>

      {/* Sync Discovery Dialog */}
      <Dialog 
        isOpen={isSyncDialogOpen} 
        onClose={() => setIsSyncDialogOpen(false)}
        title="Thiết lập Hạ tầng Kết nối"
        maxWidth="md"
      >
        <div className="space-y-6 pt-2">
            <div className="grid grid-cols-2 gap-4">
                <button 
                    onClick={useAsMaster}
                    className={`p-4 rounded-xl border flex flex-col items-center gap-3 transition-all ${
                        syncStatus?.is_destination 
                        ? 'bg-amber-500/10 border-amber-500 text-amber-500' 
                        : 'bg-zinc-900 border-zinc-800 text-zinc-400 hover:border-zinc-700'
                    }`}
                >
                    <Server size={32} />
                    <div className="text-center">
                        <p className="font-bold text-sm">PC Chủ (Master)</p>
                        <p className="text-[10px] opacity-60">Lưu trữ dữ liệu tại máy này</p>
                    </div>
                </button>
                <button 
                    onClick={() => {}} // Already in client view or stays here to pick
                    className={`p-4 rounded-xl border flex flex-col items-center gap-3 transition-all ${
                        !syncStatus?.is_destination 
                        ? 'bg-blue-500/10 border-blue-500 text-blue-500' 
                        : 'bg-zinc-900 border-zinc-800 text-zinc-400 hover:border-zinc-700'
                    }`}
                >
                    <Monitor size={32} />
                    <div className="text-center">
                        <p className="font-bold text-sm">PC Trạm (Client)</p>
                        <p className="text-[10px] opacity-60">Kết nối dữ liệu từ Master</p>
                    </div>
                </button>
            </div>

            <div className="space-y-3">
                <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold uppercase tracking-widest text-zinc-500">Thiết bị tìm thấy trong mạng:</h3>
                    <Button variant="ghost" size="sm" className="h-6 text-[10px] gap-1" onClick={startDiscovery} disabled={isScanning}>
                        <RefreshCw size={10} className={isScanning ? 'animate-spin' : ''} />
                        QUÉT LẠI
                    </Button>
                </div>

                <div className="space-y-2 max-h-[200px] overflow-y-auto pr-1">
                    {discoveryList.length > 0 ? discoveryList.map((pc) => (
                        <div key={pc.name || pc.url} className={`p-3 rounded-lg bg-zinc-900 border flex items-center justify-between group transition-all ${
                            isConnecting === pc.url ? 'border-blue-500 bg-blue-500/5' : 'border-zinc-800 hover:border-blue-500/50'
                        }`}>
                            <div className="flex items-center gap-3">
                                <div className="w-8 h-8 rounded-full bg-blue-500/10 flex items-center justify-center text-blue-500 font-bold text-xs uppercase">
                                    {(pc.displayName || pc.name || 'PC').substring(0,2)}
                                </div>
                                <div>
                                    <p className="text-xs font-bold text-zinc-200">{pc.displayName || pc.name}</p>
                                    <p className="text-[10px] font-mono text-zinc-500">{pc.url}</p>
                                </div>
                            </div>
                            <Button 
                                size="sm" 
                                className="h-7 text-[10px] font-black bg-blue-600 hover:bg-blue-500 min-w-[70px]"
                                onClick={() => connectToMaster(pc.url, pc.displayName || pc.name)}
                                disabled={isConnecting !== null}
                            >
                                {isConnecting === pc.url ? (
                                    <RefreshCw size={12} className="animate-spin" />
                                ) : (
                                    'KẾT NỐI'
                                )}
                            </Button>
                        </div>
                    )) : (
                        <div className="py-8 flex flex-col items-center justify-center text-center bg-zinc-900/50 rounded-lg border border-dashed border-zinc-800">
                            {isScanning ? (
                                <RefreshCw className="h-8 w-8 text-zinc-700 animate-spin mb-2" />
                            ) : (
                                <Wifi className="h-8 w-8 text-zinc-700 mb-2" />
                            )}
                            <p className="text-[10px] text-zinc-500 uppercase font-black">
                                {isScanning ? "Đang tìm kiếm..." : "Không tìm thấy thiết bị nào"}
                            </p>
                        </div>
                    )}
                </div>
            </div>

            <div className="pt-4 border-t border-zinc-800 flex justify-end">
                <Button variant="ghost" size="sm" className="text-zinc-500 text-xs" onClick={() => setIsSyncDialogOpen(false)}>Đóng</Button>
            </div>
        </div>
      </Dialog>
    </div>
  );
}
