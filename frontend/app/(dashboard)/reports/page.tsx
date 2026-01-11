'use client'

import React from 'react'

export default function ReportsPage() {
  return (
    <div className="p-6 flex flex-col items-center justify-center h-[70vh] text-center space-y-4">
      <div className="w-20 h-20 bg-muted rounded-full flex items-center justify-center text-4xl">
        📊
      </div>
      <h1 className="text-2xl font-bold">Báo cáo & Thống kê</h1>
      <p className="text-muted-foreground max-w-md">
        Tính năng này đang được phát triển. Bạn sẽ có thể xem biểu đồ lưu lượng xe, hiệu suất camera và xuất báo cáo chi tiết tại đây.
      </p>
    </div>
  )
}
