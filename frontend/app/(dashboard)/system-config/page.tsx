'use client'

import React, { useState, useEffect } from 'react'
import { 
  Image as ImageIcon, 
  RefreshCw, 
  Calendar, 
  Trash2, 
  Settings2, 
  Camera,
  AlertCircle,
  CheckCircle2,
  Loader2
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { toast } from 'sonner'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

interface BackgroundInfo {
  camera_id: string
  camera_name: string
  filename: string
  path: string
  timestamp: string | null
  size_kb: number | null
}

interface BackgroundSettings {
  update_interval_hours: number
  scheduler_enabled: boolean
  last_update: string | null
}

interface DataExpirySettings {
  registered_cars_days: number
  history_days: number
  reports_days: number
  car_history_days: number
  auto_cleanup_enabled: boolean
}

interface VolumeTopDownCamera {
  id: string
  name: string
  location: string | null
  has_background: boolean
}

export default function SystemConfigPage() {
  const [backgrounds, setBackgrounds] = useState<BackgroundInfo[]>([])
  const [topdownCameras, setTopdownCameras] = useState<VolumeTopDownCamera[]>([])
  const [bgSettings, setBgSettings] = useState<BackgroundSettings>({
    update_interval_hours: 1,
    scheduler_enabled: true,
    last_update: null
  })
  const [expirySettings, setExpirySettings] = useState<DataExpirySettings>({
    registered_cars_days: 2,
    history_days: 2,
    reports_days: 2,
    car_history_days: 2,
    auto_cleanup_enabled: true
  })
  const [isCapturing, setIsCapturing] = useState(false)
  const [isCleaning, setIsCleaning] = useState(false)
  const [isSavingBg, setIsSavingBg] = useState(false)
  const [isSavingExpiry, setIsSavingExpiry] = useState(false)
  const [selectedImage, setSelectedImage] = useState<string | null>(null)

  useEffect(() => {
    loadBackgrounds()
    loadTopdownCameras()
    loadBgSettings()
    loadExpirySettings()
  }, [])

  const getToken = () => localStorage.getItem('token')

  const loadBackgrounds = async () => {
    try {
      const res = await fetch('/api/system-config/backgrounds', {
        headers: { 'Authorization': `Bearer ${getToken()}` }
      })
      if (res.ok) {
        const data = await res.json()
        setBackgrounds(data)
      }
    } catch (e) {
      console.error('Failed to load backgrounds:', e)
    }
  }

  const loadTopdownCameras = async () => {
    try {
      const res = await fetch('/api/system-config/backgrounds/cameras', {
        headers: { 'Authorization': `Bearer ${getToken()}` }
      })
      if (res.ok) {
        const data = await res.json()
        setTopdownCameras(data)
      }
    } catch (e) {
      console.error('Failed to load topdown cameras:', e)
    }
  }

  const loadBgSettings = async () => {
    try {
      const res = await fetch('/api/system-config/backgrounds/settings', {
        headers: { 'Authorization': `Bearer ${getToken()}` }
      })
      if (res.ok) {
        const data = await res.json()
        setBgSettings(data)
      }
    } catch (e) {
      console.error('Failed to load bg settings:', e)
    }
  }

  const loadExpirySettings = async () => {
    try {
      const res = await fetch('/api/system-config/data-expiry', {
        headers: { 'Authorization': `Bearer ${getToken()}` }
      })
      if (res.ok) {
        const data = await res.json()
        setExpirySettings(data)
      }
    } catch (e) {
      console.error('Failed to load expiry settings:', e)
    }
  }

  const handleManualCapture = async () => {
    setIsCapturing(true)
    try {
      const res = await fetch('/api/system-config/backgrounds/capture', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${getToken()}` }
      })
      const data = await res.json()
      if (res.ok) {
        toast.success(`Đã cập nhật ${data.updated} ảnh nền (kiểm tra: ${data.checked}, bỏ qua: ${data.skipped})`)
        loadBackgrounds()
        loadTopdownCameras()
        loadBgSettings()
      } else {
        toast.error(data.detail || 'Không thể cập nhật ảnh nền')
      }
    } catch (e) {
      toast.error('Lỗi kết nối server')
    } finally {
      setIsCapturing(false)
    }
  }

  const handleSaveBgSettings = async () => {
    setIsSavingBg(true)
    try {
      const params = new URLSearchParams({
        update_interval_hours: String(bgSettings.update_interval_hours),
        scheduler_enabled: String(bgSettings.scheduler_enabled)
      })
      const res = await fetch(`/api/system-config/backgrounds/settings?${params}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${getToken()}` }
      })
      if (res.ok) {
        toast.success('Đã lưu cài đặt ảnh nền')
      } else {
        toast.error('Không thể lưu cài đặt')
      }
    } catch (e) {
      toast.error('Lỗi kết nối server')
    } finally {
      setIsSavingBg(false)
    }
  }

  const handleSaveExpirySettings = async () => {
    setIsSavingExpiry(true)
    try {
      const params = new URLSearchParams({
        registered_cars_days: String(expirySettings.registered_cars_days),
        history_days: String(expirySettings.history_days),
        reports_days: String(expirySettings.reports_days),
        car_history_days: String(expirySettings.car_history_days),
        auto_cleanup_enabled: String(expirySettings.auto_cleanup_enabled)
      })
      const res = await fetch(`/api/system-config/data-expiry?${params}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${getToken()}` }
      })
      if (res.ok) {
        toast.success('Đã lưu cài đặt thời hạn dữ liệu')
      } else {
        toast.error('Không thể lưu cài đặt')
      }
    } catch (e) {
      toast.error('Lỗi kết nối server')
    } finally {
      setIsSavingExpiry(false)
    }
  }

  const handleManualCleanup = async () => {
    setIsCleaning(true)
    try {
      const res = await fetch('/api/system-config/data-expiry/cleanup', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${getToken()}` }
      })
      const data = await res.json()
      if (res.ok) {
        const total = data.registered_cars_deleted + data.history_deleted + data.reports_deleted + data.car_history_folders_deleted
        if (total > 0) {
          toast.success(`Đã xóa ${total} tệp/thư mục hết hạn`)
        } else {
          toast.info('Không có dữ liệu hết hạn cần xóa')
        }
      } else {
        toast.error(data.detail || 'Không thể dọn dẹp dữ liệu')
      }
    } catch (e) {
      toast.error('Lỗi kết nối server')
    } finally {
      setIsCleaning(false)
    }
  }

  const formatTimestamp = (ts: string | null) => {
    if (!ts) return 'Không xác định'
    // Parse format: dd-mm-yyyy_hh-mm-ss
    try {
      const parts = ts.split('_')
      if (parts.length === 2) {
        // Convert dd-mm-yyyy to display format
        const dateParts = parts[0].split('-')
        if (dateParts.length === 3) {
          const displayDate = `${dateParts[0]}/${dateParts[1]}/${dateParts[2]}`
          const displayTime = parts[1].replace(/-/g, ':')
          return `${displayDate} ${displayTime}`
        }
        return `${parts[0]} ${parts[1].replace(/-/g, ':')}`
      }
    } catch (e) {}
    return ts
  }

  const intervalOptions = [
    { value: 1, label: '1 giờ' },
    { value: 2, label: '2 giờ' },
    { value: 4, label: '4 giờ' },
    { value: 24, label: '1 ngày' }
  ]

  const dayOptions = [
    { value: 1, label: '1 ngày' },
    { value: 2, label: '2 ngày' },
    { value: 3, label: '3 ngày' },
    { value: 7, label: '7 ngày' },
    { value: 14, label: '14 ngày' },
    { value: 30, label: '30 ngày' }
  ]

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto pb-12">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Settings2 className="h-6 w-6 text-[#f59e0b]" />
        <h1 className="text-2xl font-bold tracking-tight">Thiết lập hệ thống</h1>
      </div>

      {/* Background Config Panel */}
      <Card className="border-border shadow-md">
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-500/10 rounded-lg">
                <ImageIcon className="h-5 w-5 text-amber-500" />
              </div>
              <CardTitle className="text-lg">Ảnh nền Volume Top-Down</CardTitle>
            </div>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleManualCapture}
              disabled={isCapturing}
              className="gap-2"
            >
              {isCapturing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
              Cập nhật ngay
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Background Images Grid */}
          {backgrounds.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {backgrounds.map((bg) => (
                <div 
                  key={bg.camera_id} 
                  className="relative group rounded-lg overflow-hidden border border-border bg-muted/30 cursor-pointer hover:border-amber-500/50 transition-colors"
                  onClick={() => setSelectedImage(bg.path)}
                >
                  <div className="aspect-video relative">
                    <img 
                      src={bg.path} 
                      alt={bg.camera_name}
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
                  </div>
                  <div className="absolute bottom-0 left-0 right-0 p-3">
                    <div className="flex items-center gap-2">
                      <Camera className="h-4 w-4 text-amber-500" />
                      <span className="text-sm font-medium text-white truncate">{bg.camera_name}</span>
                    </div>
                    <p className="text-xs text-white/70 mt-1">
                      {formatTimestamp(bg.timestamp)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
              <AlertCircle className="h-10 w-10 mb-3" />
              <p className="text-sm">Chưa có ảnh nền nào</p>
              <p className="text-xs mt-1">Nhấn "Cập nhật ngay" để chụp ảnh nền từ camera</p>
            </div>
          )}

          {/* Camera List */}
          {topdownCameras.length > 0 && (
            <div className="border-t border-border pt-4">
              <h4 className="text-sm font-semibold flex items-center gap-2 mb-3">
                <Camera className="h-4 w-4 text-muted-foreground" />
                Camera Volume Top-Down ({topdownCameras.length})
              </h4>
              <div className="flex flex-wrap gap-2">
                {topdownCameras.map((cam) => (
                  <div 
                    key={cam.id}
                    className={`px-3 py-1.5 rounded-full text-xs flex items-center gap-1.5 ${
                      cam.has_background 
                        ? 'bg-green-500/10 text-green-600 border border-green-500/20' 
                        : 'bg-muted text-muted-foreground border border-border'
                    }`}
                  >
                    {cam.has_background ? (
                      <CheckCircle2 className="h-3 w-3" />
                    ) : (
                      <AlertCircle className="h-3 w-3" />
                    )}
                    <span>{cam.name}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Settings - inline like data expiry panel */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="bg-interval" className="text-xs text-muted-foreground">
                Tần suất cập nhật
              </Label>
              <Select 
                value={String(bgSettings.update_interval_hours)}
                onValueChange={(v) => setBgSettings({...bgSettings, update_interval_hours: Number(v)})}
              >
                <SelectTrigger id="bg-interval" className="h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {intervalOptions.map(opt => (
                    <SelectItem key={opt.value} value={String(opt.value)}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-border">
            <div className="flex items-center gap-3">
              <Switch 
                id="bg-auto"
                checked={bgSettings.scheduler_enabled}
                onCheckedChange={(v) => setBgSettings({...bgSettings, scheduler_enabled: v})}
                className="data-[state=checked]:bg-amber-500"
              />
              <Label htmlFor="bg-auto" className="text-sm">
                Tự động cập nhật ảnh nền
              </Label>
            </div>
            <Button 
              onClick={handleSaveBgSettings} 
              disabled={isSavingBg}
              size="sm"
              className="gap-2 bg-amber-500 hover:bg-amber-600 text-white"
            >
              {isSavingBg ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <CheckCircle2 className="h-4 w-4" />
              )}
              Lưu cài đặt
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Data Expiry Config Panel */}
      <Card className="border-border shadow-md">
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-500/10 rounded-lg">
                <Calendar className="h-5 w-5 text-amber-500" />
              </div>
              <CardTitle className="text-lg">Thời hạn lưu trữ dữ liệu</CardTitle>
            </div>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleManualCleanup}
              disabled={isCleaning}
              className="gap-2 text-amber-600 hover:text-amber-700 hover:bg-amber-50"
            >
              {isCleaning ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="h-4 w-4" />
              )}
              Dọn dẹp ngay
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="space-y-2">
              <Label htmlFor="reg-days" className="text-xs text-muted-foreground">
                Xe đăng ký
              </Label>
              <Select 
                value={String(expirySettings.registered_cars_days)}
                onValueChange={(v) => setExpirySettings({...expirySettings, registered_cars_days: Number(v)})}
              >
                <SelectTrigger id="reg-days" className="h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {dayOptions.map(opt => (
                    <SelectItem key={opt.value} value={String(opt.value)}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="history-days" className="text-xs text-muted-foreground">
                Lịch sử ra vào
              </Label>
              <Select 
                value={String(expirySettings.history_days)}
                onValueChange={(v) => setExpirySettings({...expirySettings, history_days: Number(v)})}
              >
                <SelectTrigger id="history-days" className="h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {dayOptions.map(opt => (
                    <SelectItem key={opt.value} value={String(opt.value)}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="report-days" className="text-xs text-muted-foreground">
                Báo cáo
              </Label>
              <Select 
                value={String(expirySettings.reports_days)}
                onValueChange={(v) => setExpirySettings({...expirySettings, reports_days: Number(v)})}
              >
                <SelectTrigger id="report-days" className="h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {dayOptions.map(opt => (
                    <SelectItem key={opt.value} value={String(opt.value)}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="car-history-days" className="text-xs text-muted-foreground">
                Ảnh lịch sử
              </Label>
              <Select 
                value={String(expirySettings.car_history_days)}
                onValueChange={(v) => setExpirySettings({...expirySettings, car_history_days: Number(v)})}
              >
                <SelectTrigger id="car-history-days" className="h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {dayOptions.map(opt => (
                    <SelectItem key={opt.value} value={String(opt.value)}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-border">
            <div className="flex items-center gap-3">
              <Switch 
                id="auto-cleanup"
                checked={expirySettings.auto_cleanup_enabled}
                onCheckedChange={(v) => setExpirySettings({...expirySettings, auto_cleanup_enabled: v})}
                className="data-[state=checked]:bg-amber-500"
              />
              <Label htmlFor="auto-cleanup" className="text-sm">
                Tự động dọn dẹp dữ liệu hết hạn
              </Label>
            </div>
            <Button 
              onClick={handleSaveExpirySettings} 
              disabled={isSavingExpiry}
              size="sm"
              className="gap-2 bg-amber-500 hover:bg-amber-600 text-white"
            >
              {isSavingExpiry ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <CheckCircle2 className="h-4 w-4" />
              )}
              Lưu cài đặt
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Image Preview Modal */}
      {selectedImage && (
        <div 
          className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4"
          onClick={() => setSelectedImage(null)}
        >
          <div className="max-w-4xl max-h-[90vh] relative">
            <img 
              src={selectedImage} 
              alt="Background preview"
              className="max-w-full max-h-[90vh] object-contain rounded-lg"
            />
            <Button 
              variant="secondary" 
              size="sm"
              className="absolute top-2 right-2"
              onClick={() => setSelectedImage(null)}
            >
              Đóng
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
