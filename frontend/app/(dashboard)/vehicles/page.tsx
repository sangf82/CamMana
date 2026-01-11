'use client'

import React, { useState, useEffect } from 'react'
import { Add, Edit, Delete, LocalShipping, Description, Warning } from '@mui/icons-material'
import DataTable from '../../../components/ui/data-table'
import Dialog from '../../../components/ui/dialog'
import { toast } from 'sonner'

// --- Types ---
interface Vehicle {
  id: number | string // Allow string IDs from backend
  plate: string
  truckModel: string          
  color: string               // New: Màu xe
  axles: string               // New: Số bánh
  contractor: string
  registrationDate: string
  lastModified: string
}

// Math Component for "Latex-like" display


export default function VehiclesPage() {
  const [data, setData] = useState<Vehicle[]>([])
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [editingItem, setEditingItem] = useState<Vehicle | null>(null)
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | string | null>(null)

  const handleDelete = (id: number | string) => {
    setDeleteConfirmId(id)
  }

  const executeDelete = () => {
    if (deleteConfirmId !== null) {
      const newData = data.filter(item => item.id !== deleteConfirmId)
      saveToBackend(newData)
      setDeleteConfirmId(null)
    }
  }

  // --- Persistence ---
  // --- 1. Load Data from API ---
  const fetchInitialData = async () => {
      try {
          const res = await fetch('/api/cameras/registered_cars')
          if (res.ok) {
              const rawData = await res.json()
              // Map Backend -> Frontend
              const mappedData = rawData.map((item: any) => ({
                  id: item.id || Math.random(), // Use backend ID or fallback
                  plate: item.plate_number || '',
                  truckModel: item.model || '',
                  color: item.color || '',
                  axles: item.notes || '', // Using notes for axles
                  contractor: item.owner || '',
                  registrationDate: item.created_at || '',
                  lastModified: ''
              }))
              setData(mappedData)
          }
      } catch (error) {
          console.error("Failed to load vehicles", error)
          toast.error("Không thể tải danh sách xe")
      }
  }

  useEffect(() => {
    fetchInitialData()
  }, [])

  // --- 2. Save Data to API ---
  const saveToBackend = async (newData: Vehicle[]) => {
      // Map Frontend -> Backend
      const payload = newData.map(item => ({
          id: typeof item.id === 'string' ? item.id : undefined, // Send ID if it's a string (backend ID), else undefined (new item, let backend gen)
          plate_number: item.plate,
          model: item.truckModel,
          color: item.color,
          notes: item.axles, // Storing axles in notes
          owner: item.contractor,
          created_at: item.registrationDate
      }))

      const promise = (async () => {
        const res = await fetch('/api/cameras/registered_cars', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        if (!res.ok) throw new Error('Failed to save data')
        return res
      })()

      toast.promise(promise, {
          loading: 'Đang lưu dữ liệu...',
          success: () => {
              fetchInitialData() // Reload from CSV source
              return 'Đã cập nhật danh sách xe'
          },
          error: (err) => {
              console.error(err)
              return 'Lỗi khi lưu dữ liệu'
          }
      })
  }

  // --- Columns ---
  const columns = [
    { header: 'Biển số', accessorKey: 'plate' as keyof Vehicle },
    { header: 'Loại xe', accessorKey: 'truckModel' as keyof Vehicle },
    { 
        header: 'Màu xe',
        accessorKey: 'color' as keyof Vehicle 
    },
    { 
        header: 'Số trục/bánh',
        accessorKey: 'axles' as keyof Vehicle 
    },
    { header: 'Nhà thầu', accessorKey: 'contractor' as keyof Vehicle },
    { 
        header: 'Ngày ĐK', 
        accessorKey: 'registrationDate' as keyof Vehicle,
        render: (row: Vehicle) => {
            if (!row.registrationDate) return <span>-</span>
            // Assuming format is YYYY-MM-DD from input type='date'
            const [y, m, d] = row.registrationDate.split('-')
            return <span>{`${d}/${m}/${y}`}</span>
        }
    }, 
    { 
      header: 'Thao tác', 
      width: '100px',
      render: (row: Vehicle) => (
        <div className="flex gap-2">
          <button 
            onClick={(e) => { e.stopPropagation(); handleEdit(row) }}
            className="p-1 text-blue-500 hover:bg-blue-500/10 rounded transition-colors"
          >
            <Edit fontSize="small" />
          </button>
          <button 
             onClick={(e) => { e.stopPropagation(); handleDelete(row.id) }}
             className="p-1 text-red-500 hover:bg-red-500/10 rounded transition-colors"
          >
            <Delete fontSize="small" />
          </button>
        </div>
      )
    }
  ]

  const handleEdit = (item: Vehicle) => {
    setEditingItem(item)
    setIsDialogOpen(true)
  }



  const handleSave = (e: React.FormEvent) => {
    e.preventDefault()
    
    // Auto update modified date
    const now = new Date().toLocaleString('vi-VN')
    
    if (!editingItem) return

    let newItem = { ...editingItem, lastModified: now }
    let newData: Vehicle[] = []

    if (!editingItem.id) {
        // Add new
        // We don't verify strict ID here, just add to list. Backend will assign ID.
        // But for local UI state, we need a temp ID.
        newItem.id = Date.now() 
        newData = [...data, newItem]
    } else {
        // Update
        newData = data.map(item => item.id === editingItem.id ? newItem : item)
    }
    
    saveToBackend(newData)
    setIsDialogOpen(false)
    setEditingItem(null)
  }

  const openAddDialog = () => {
    const today = new Date().toISOString().split('T')[0]
    setEditingItem({ 
        id: 0, 
        plate: '', 
        truckModel: '', 
        color: '',            
        axles: '',            
        contractor: '', 
        registrationDate: today,
        lastModified: ''     
    })
    setIsDialogOpen(true)
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
           <h1 className="text-2xl font-bold tracking-tight">Danh sách xe đăng ký</h1>
           <p className="text-sm text-muted-foreground mt-1">Quản lý cơ sở dữ liệu phương tiện và thông số kỹ thuật</p>
        </div>
        <button 
          onClick={openAddDialog}
          className="bg-primary hover:bg-primary/90 text-primary-foreground px-4 py-2 rounded-md font-medium flex items-center gap-2 transition-colors shadow-lg shadow-primary/20"
        >
          <Add /> Thêm xe mới
        </button>
      </div>

      <DataTable 
        columns={columns} 
        data={data} 
      />

      {/* CRUD Dialog */}
      <Dialog 
        isOpen={isDialogOpen} 
        onClose={() => setIsDialogOpen(false)} 
        title={editingItem?.id ? 'Sửa thông tin xe' : 'Đăng ký xe mới'}
        maxWidth="2xl" // Wider dialog
      >
        <form onSubmit={handleSave} className="space-y-6">
          
          {/* Section 1: Basic Info */}
          <div className="space-y-4">
             <div className="flex items-center gap-2 text-primary font-semibold border-b border-border pb-2">
                <LocalShipping fontSize="small" />
                <span>Thông tin Phương tiện</span>
             </div>
             
             <div className="grid grid-cols-2 gap-6">
                <div className="space-y-2">
                    <label className="text-sm font-medium text-muted-foreground">Biển số <span className="text-red-500">*</span></label>
                    <div className="relative">
                        <input 
                            className="w-full p-2.5 bg-background border border-border rounded focus:border-primary focus:ring-0 outline-none font-sans text-md"
                            value={editingItem?.plate || ''}
                            onChange={e => setEditingItem(prev => ({ ...prev!, plate: e.target.value.toUpperCase() }))}
                            required 
                            placeholder="Ví dụ: 51A-123.45"
                        />
                    </div>
                </div>
                
                <div className="space-y-2">
                    <label className="text-sm font-medium text-muted-foreground">Loại xe <span className="text-red-500">*</span></label>
                    <input 
                        className="w-full p-2.5 bg-background border border-border rounded focus:border-primary focus:ring-0 outline-none font-sans text-md"
                        value={editingItem?.truckModel || ''}
                        onChange={e => setEditingItem(prev => ({ ...prev!, truckModel: e.target.value }))}
                        required
                        placeholder="Ví dụ: Howo 3 chân, Hyundai HD270..."
                    />
                </div>
             </div>

             <div className="grid grid-cols-2 gap-6">
                <div className="space-y-2">
                    <label className="text-sm font-medium text-muted-foreground">Màu xe <span className="text-red-500">*</span></label>
                    <input 
                        className="w-full p-2.5 bg-background border border-border rounded focus:border-primary focus:ring-0 outline-none font-sans text-md"
                        value={editingItem?.color || ''}
                        onChange={e => setEditingItem(prev => ({ ...prev!, color: e.target.value }))}
                        required
                        placeholder="Ví dụ: Trắng, Xanh..."
                    />
                </div>
                <div className="space-y-2">
                    <label className="text-sm font-medium text-muted-foreground">Số trục / Số bánh <span className="text-red-500">*</span></label>
                    <input 
                        className="w-full p-2.5 bg-background border border-border rounded focus:border-primary focus:ring-0 outline-none font-sans text-md"
                        value={editingItem?.axles || ''}
                        onChange={e => setEditingItem(prev => ({ ...prev!, axles: e.target.value }))}
                        required
                        placeholder="Ví dụ: 3 trục / 10 bánh"
                    />
                </div>
             </div>
          </div>



          {/* Section 3: Administrative Info */}
          <div className="space-y-4">
             <div className="flex items-center gap-2 text-primary font-semibold border-b border-border pb-2">
                <Description fontSize="small" />
                <span>Thông tin Hành chính</span>
             </div>

             <div className="grid grid-cols-2 gap-6">
                <div className="space-y-2">
                    <label className="text-sm font-medium text-muted-foreground">Nhà thầu / Chủ xe</label>
                    <input 
                        className="w-full p-2.5 bg-background border border-border rounded focus:border-primary focus:ring-0 outline-none font-sans text-md"
                        value={editingItem?.contractor || ''}
                        onChange={e => setEditingItem(prev => ({ ...prev!, contractor: e.target.value }))}
                        placeholder="Ví dụ: Tên công ty hoặc cá nhân"
                    />
                </div>

                <div className="space-y-2">
                    <label className="text-sm font-medium text-muted-foreground">Ngày đăng ký</label>
                    <input 
                        type="date"
                        className="w-full p-2.5 bg-background border border-border rounded focus:border-primary focus:ring-0 outline-none font-sans text-md dark:[color-scheme:dark]"
                        value={editingItem?.registrationDate || ''}
                        onChange={e => setEditingItem(prev => ({ ...prev!, registrationDate: e.target.value }))}
                        required
                    />
                </div>
             </div>
          </div>

          <div className="flex justify-end gap-3 pt-6 border-t border-border mt-8">
             <button 
               type="button"
               onClick={() => setIsDialogOpen(false)}
               className="px-6 py-2.5 text-sm font-medium text-muted-foreground hover:bg-muted rounded transition-colors"
             >
               Hủy bỏ
             </button>
             <button 
               type="submit"
               className="px-6 py-2.5 text-sm font-bold bg-primary text-primary-foreground hover:bg-primary/90 rounded transition-transform active:scale-95 shadow-lg shadow-primary/20"
             >
               {editingItem?.id ? 'Lưu thay đổi' : 'Đăng lý lưu hành'}
             </button>
          </div>
        </form>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog 
        isOpen={deleteConfirmId !== null} 
        onClose={() => setDeleteConfirmId(null)} 
        title="Xác nhận xóa"
        maxWidth="sm"
      >
        <div className="space-y-4">
          <p className="text-muted-foreground">
            Bạn có chắc chắn muốn xóa phương tiện này khỏi danh sách?
          </p>
          
          <div className="bg-red-500/10 border border-red-500/20 rounded-md p-3 flex items-start gap-3">
             <Warning className="text-red-500 shrink-0 mt-0.5" fontSize="small" />
             <div className="text-xs text-red-500">
                <span className="font-bold block mb-0.5">Cảnh báo</span>
                Hành động này sẽ xóa vĩnh viễn dữ liệu và không thể hoàn tác.
             </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-border mt-2">
            <button 
              onClick={() => setDeleteConfirmId(null)}
              className="px-4 py-2 text-sm font-medium text-muted-foreground hover:bg-muted rounded transition-colors"
            >
              Hủy bỏ
            </button>
            <button 
              onClick={executeDelete}
              className="px-4 py-2 text-sm font-bold bg-red-500 text-white hover:bg-red-600 rounded shadow-lg shadow-red-500/20 transition-all"
            >
              Xóa dữ liệu
            </button>
          </div>
        </div>
      </Dialog>
    </div>
  )
}
