'use client'

import React from 'react'
import { useTheme } from 'next-themes'
import { Sun, Moon, Monitor, Settings as SettingsIcon } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'

export default function SettingsPage() {
  const { theme, setTheme, resolvedTheme } = useTheme()
  const [mounted, setMounted] = React.useState(false)

  // Avoid hydration mismatch
  React.useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) {
    return (
      <div className="p-6 flex items-center justify-center h-[70vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  const isDark = resolvedTheme === 'dark'

  return (
    <div className="p-6 space-y-6 max-w-3xl">
      {/* Header */}
      <div className="space-y-1">
        <div className="flex items-center gap-3">
          <SettingsIcon className="h-6 w-6 text-[#f59e0b]" />
          <h1 className="text-2xl font-bold tracking-tight">Cài đặt</h1>
        </div>
        <p className="text-muted-foreground text-sm">
          Quản lý cấu hình và tùy chỉnh giao diện hệ thống.
        </p>
      </div>

      {/* Theme Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {isDark ? <Moon className="h-5 w-5 text-[#f59e0b]" /> : <Sun className="h-5 w-5 text-[#f59e0b]" />}
            Giao diện
          </CardTitle>
          <CardDescription>
            Chọn chế độ hiển thị phù hợp với môi trường làm việc của bạn.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Quick Toggle */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="dark-mode" className="text-base font-medium">Chế độ tối</Label>
              <p className="text-sm text-muted-foreground">
                {isDark ? 'Đang bật - Nền đen, chữ sáng' : 'Đang tắt - Nền trắng, chữ tối'}
              </p>
            </div>
            <Switch
              id="dark-mode"
              checked={isDark}
              onCheckedChange={(checked) => setTheme(checked ? 'dark' : 'light')}
            />
          </div>

          {/* Theme Buttons */}
          <div className="pt-4 border-t border-border">
            <p className="text-sm font-medium mb-3">Chọn chế độ</p>
            <div className="flex gap-3">
              <Button
                variant={theme === 'light' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setTheme('light')}
                className="flex items-center gap-2"
              >
                <Sun className="h-4 w-4" />
                Sáng
              </Button>
              <Button
                variant={theme === 'dark' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setTheme('dark')}
                className="flex items-center gap-2"
              >
                <Moon className="h-4 w-4" />
                Tối
              </Button>
              <Button
                variant={theme === 'system' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setTheme('system')}
                className="flex items-center gap-2"
              >
                <Monitor className="h-4 w-4" />
                Hệ thống
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Additional Settings Placeholder */}
      <Card>
        <CardHeader>
          <CardTitle>Cấu hình khác</CardTitle>
          <CardDescription>
            Các tùy chọn cấu hình bổ sung sẽ được thêm vào đây.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground italic">
            Tính năng đang được phát triển...
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
