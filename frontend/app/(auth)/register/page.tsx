"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import { Lock, User, UserPlus, ShieldCheck, Eye, EyeOff } from "lucide-react";

export default function RegisterPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [fullName, setFullName] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/api/user/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username,
          password,
          full_name: fullName,
          role: "operator"
        }),
      });

      if (response.ok) {
        toast.success("Đăng ký thành công! Vui lòng đăng nhập.");
        router.push("/login");
      } else {
        const error = await response.json();
        toast.error(error.detail || "Đăng ký thất bại");
      }
    } catch (error) {
      toast.error("Không thể kết nối đến máy chủ");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-[#09090b] relative overflow-hidden font-sans">
      <div className="absolute top-[-10%] right-[-10%] w-[40%] h-[40%] bg-amber-500/10 blur-[120px] rounded-full" />
      <div className="absolute bottom-[-10%] left-[-10%] w-[40%] h-[40%] bg-zinc-500/5 blur-[120px] rounded-full" />

      {/* Grid Pattern Background */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff05_1px,transparent_1px),linear-gradient(to_bottom,#ffffff05_1px,transparent_1px)] bg-[size:32px_32px] [mask-image:radial-gradient(ellipse_at_center,black_30%,transparent_100%)]" />

      <Card className="w-full max-w-md border-white/5 bg-zinc-900/50 backdrop-blur-xl shadow-2xl relative z-10 transition-all duration-300 hover:border-amber-500/20">
        <CardHeader className="space-y-1 pb-6 text-center">
            <div className="flex justify-center mb-4">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-amber-400 to-amber-600 flex items-center justify-center shadow-lg shadow-amber-500/20">
                    <UserPlus className="w-10 h-10 text-zinc-950" />
                </div>
            </div>
          <CardTitle className="text-3xl font-bold tracking-tight text-white font-sans">Đăng ký</CardTitle>
          <CardDescription className="text-zinc-400">
            Tạo tài khoản mới cho nhân viên Gate
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleRegister}>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="fullName" className="text-zinc-200">Họ và tên</Label>
              <div className="relative group">
                <Input
                  id="fullName"
                  placeholder="Nhập họ và tên"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="pl-10 h-11 bg-zinc-950/50 border-zinc-800 text-white placeholder:text-zinc-500 focus:border-amber-500/50 transition-all duration-300"
                />
                <div className="absolute left-3 top-1/2 -translate-y-1/2 text-amber-500/70 group-focus-within:text-amber-500 transition-colors">
                    <User className="h-4.5 w-4.5" />
                </div>
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="username" className="text-zinc-200">Tên đăng nhập</Label>
              <div className="relative group">
                <Input
                  id="username"
                  placeholder="Username"
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
              <Label htmlFor="password" className="text-zinc-200">Mật khẩu</Label>
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
                className="w-full bg-amber-500 hover:bg-amber-400 text-zinc-950 font-bold h-11"
                disabled={isLoading}
            >
              {isLoading ? "Đang xử lý..." : "Đăng ký tài khoản"}
            </Button>
            <Button 
                variant="ghost" 
                onClick={() => router.push("/login")}
                className="text-zinc-400 hover:text-white hover:bg-white/5"
            >
                Quay lại Đăng nhập
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
