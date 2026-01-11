'use client'

import React from 'react'
import DataTable from '../../../components/ui/data-table'
import { FilterList, Download } from '@mui/icons-material'

// Mock Data
const HISTORY_DATA = [
  { id: 1, plate: '51C-123.45', time_in: '14:32:01', time_out: '---', gate: 'Cổng A', status: 'In' },
  { id: 2, plate: '60A-111.22', time_in: '12:15:00', time_out: '13:00:20', gate: 'Cổng B', status: 'Completed' },
  { id: 3, plate: '59B-555.55', time_in: '11:20:15', time_out: '12:10:45', gate: 'Cổng A', status: 'Completed' },
  { id: 4, plate: '29C-999.99', time_in: '09:05:10', time_out: '---', gate: 'Cổng C', status: 'In' },
]

export default function HistoryPage() {
  const columns = [
    { header: 'Biển số', accessorKey: 'plate' },
    { header: 'Cổng', accessorKey: 'gate' },
    { header: 'Thời gian Vào', accessorKey: 'time_in' },
    { header: 'Thời gian Ra', accessorKey: 'time_out' },
    { 
      header: 'Trạng thái', 
      render: (row: any) => (
        <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold ${row.status === 'In' ? 'bg-blue-500/10 text-blue-400' : 'bg-green-500/10 text-green-500'}`}>
          {row.status === 'In' ? 'Đang trong bãi' : 'Đã hoàn thành'}
        </span>
      )
    },
  ]

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
         <div className="space-y-1">
            <h1 className="text-2xl font-bold tracking-tight">Lịch sử ra vào</h1>
            <p className="text-muted-foreground text-sm">Theo dõi toàn bộ hoạt động ra vào tại các cổng</p>
         </div>
         <div className="flex gap-2">
            <button className="px-3 py-2 bg-card border border-border text-foreground hover:bg-muted rounded text-sm font-medium flex items-center gap-2">
              <FilterList fontSize="small" /> Lọc
            </button>
            <button className="px-3 py-2 bg-card border border-border text-foreground hover:bg-muted rounded text-sm font-medium flex items-center gap-2">
              <Download fontSize="small" /> Xuất Excel
            </button>
         </div>
      </div>
      
      <DataTable columns={columns} data={HISTORY_DATA} />
    </div>
  )
}
