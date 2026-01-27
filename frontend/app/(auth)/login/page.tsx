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
        if (res.ok) setDiscoveryList(await res.json());
    } catch (e) {
        toast.error("Không thể quét mạng nội bộ");
    } finally {
        setIsScanning(false);
    }
  };

  const connectToMaster = async (url: string) => {
    try {
        const params = new URLSearchParams();
        params.append('remote_url', url);
        params.append('is_destination', 'false');
        
        const res = await fetch(`http://127.0.0.1:8000/api/sync/configure?${params.toString()}`, {
            method: 'POST'
        });
        
        if (res.ok) {
            toast.success("Đã kết nối với Master PC!");
            setIsSyncDialogOpen(false);
            fetchSyncStatus();
        } else {
            toast.error("Không thể kết nối với thiết bị đã chọn");
        }
    } catch (e) {
        toast.error("Lỗi cấu hình");
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
    <div className="min-h-screen w-full flex items-center justify-center bg-[#09090b] relative overflow-hidden font-sans">
      {/* Background blobs for premium look - Amber tint matching dashboard */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-amber-500/10 blur-[120px] rounded-full" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-zinc-500/5 blur-[120px] rounded-full" />
      
      {/* Grid Pattern Background */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff05_1px,transparent_1px),linear-gradient(to_bottom,#ffffff05_1px,transparent_1px)] bg-[size:32px_32px] [mask-image:radial-gradient(ellipse_at_center,black_30%,transparent_100%)]" />

      <Card className="w-full max-w-md border-white/5 bg-zinc-900/50 backdrop-blur-xl shadow-2xl relative z-10 transition-all duration-300 hover:border-amber-500/20">
        <CardHeader className="space-y-1 pb-6 text-center">
            <div className="flex justify-center mb-4">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-amber-400 to-amber-600 flex items-center justify-center shadow-lg shadow-amber-500/20">
                    <ShieldCheck className="w-10 h-10 text-zinc-950" />
                </div>
            </div>
          <CardTitle className="text-3xl font-bold tracking-tight text-white font-sans">CamMana</CardTitle>
          <CardDescription className="text-zinc-400">
            Hệ thống giám sát & Quản lý Gate
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleLogin}>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username" className="text-zinc-200">Tài khoản</Label>
              <div className="relative group">
                <Input
                  id="username"
                  placeholder="Nhập tên đăng nhập"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="pl-10 h-11 bg-zinc-950/50 border-zinc-800 text-white placeholder:text-zinc-500 focus:border-amber-500/50 transition-all duration-300"
                  required
                />
                <div className="absolute left-3 top-1/2 -translate-y-1/2 text-amber-500/70 group-focus-within:text-amber-500 transition-colors">
                    <User className="h-4.5 w-4.5" />
                </div>
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="password" className="text-zinc-200">Mật khẩu</Label>
              </div>
              <div className="relative group">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-10 h-11 bg-zinc-950/50 border-zinc-800 text-white placeholder:text-zinc-500 focus:border-amber-500/50 transition-all duration-300"
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
                className="w-full bg-amber-500 hover:bg-amber-400 text-zinc-950 font-bold h-11 shadow-lg shadow-amber-500/20 transition-all active:scale-[0.98]"
                disabled={isLoading}
            >
              {isLoading ? "Đang đăng nhập..." : "Đăng nhập"}
            </Button>

            <div className="w-full pt-2 flex items-center justify-between text-[10px] text-zinc-500 border-t border-white/5 pt-4">
                <div className="flex items-center gap-1.5">
                    <div className={`w-1.5 h-1.5 rounded-full ${syncStatus?.is_destination ? 'bg-green-500' : 'bg-blue-500'} animate-pulse`} />
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
                        <div key={pc.name} className="p-3 rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-between group hover:border-blue-500/50 transition-all">
                            <div className="flex items-center gap-3">
                                <div className="w-8 h-8 rounded-full bg-blue-500/10 flex items-center justify-center text-blue-500 font-bold text-xs uppercase">
                                    {pc.name.substring(0,2)}
                                </div>
                                <div>
                                    <p className="text-xs font-bold text-zinc-200">{pc.name}</p>
                                    <p className="text-[10px] font-mono text-zinc-500">{pc.url}</p>
                                </div>
                            </div>
                            <Button 
                                size="sm" 
                                className="h-7 text-[10px] font-black bg-blue-600 hover:bg-blue-500"
                                onClick={() => connectToMaster(pc.url)}
                            >
                                KẾT NỐI
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
