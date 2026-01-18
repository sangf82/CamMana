'use client'

import React, { useState, useEffect } from 'react'
import { Add, ExpandLess } from '@mui/icons-material'
import { toast } from 'sonner'
import VehicleTable, { Vehicle } from '../../../components/features/vehicles/VehicleTable'
import VehicleFilterBar from '../../../components/features/vehicles/VehicleFilterBar'
import VehicleDetailDialog from '../../../components/features/vehicles/VehicleDetailDialog'

export default function VehiclesPage() {
  const [data, setData] = useState<Vehicle[]>([])
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [editingItem, setEditingItem] = useState<Vehicle | null>(null)
  
  // Filters
  const [searchTerm, setSearchTerm] = useState('')
  const [filterContractor, setFilterContractor] = useState('All')
  const [filterType, setFilterType] = useState('All')

  const [showScrollTop, setShowScrollTop] = useState(false)

  useEffect(() => {
    const handleScroll = () => {
      setShowScrollTop(window.scrollY > 300)
    }
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
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
                    boxDimensions: item.box_dimensions || '',
                    standardVolume: item.standard_volume || '',
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
          box_dimensions: item.boxDimensions,
          standard_volume: item.standardVolume,
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

  const contractors = ['All', ...Array.from(new Set(data.map(d => d.contractor?.trim() || 'None')))]
  const vehicleTypes = ['All', ...Array.from(new Set(data.map(d => d.truckModel?.trim() || 'None')))]

  const filteredData = data.filter(item => {
    const matchesSearch = item.plate.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesContractor = filterContractor === 'All' || (item.contractor?.trim() || 'None') === filterContractor
    const matchesType = filterType === 'All' || (item.truckModel?.trim() || 'None') === filterType
    return matchesSearch && matchesContractor && matchesType
  })

  const handleEdit = (item: Vehicle) => {
    setEditingItem(item)
    setIsDialogOpen(true)
  }

  const handleDelete = (id: number | string) => {
      // Direct delete without separate confirmation state in this refined version (or add it back if needed)
      // For similar UI, we can use a toast/browser confirm or assume simple delete for now to match component
      if (window.confirm('Bạn có chắc chắn muốn xóa phương tiện này?')) {
        const newData = data.filter(item => item.id !== id)
        saveToBackend(newData)
      }
  }

  const handleSave = (e: React.FormEvent, updatedItem: Vehicle) => {
    // Auto update modified date
    const now = new Date().toLocaleString('vi-VN')
    const newItem = { ...updatedItem, lastModified: now }
    
    let newData: Vehicle[] = []

    if (!editingItem?.id) {
        // Add new
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

  const handleExportExcel = () => {
    if (filteredData.length === 0) {
      toast.error('Không có dữ liệu để xuất')
      return
    }

    const headers = [
      'Biển số', 
      'Loại xe', 
      'Màu xe', 
      'Số trục/bánh', 
      'Kích thước thùng', 
      'Thể tích (m3)', 
      'Nhà thầu', 
      'Ngày ĐK'
    ]

    const rows = filteredData.map(item => [
      item.plate,
      item.truckModel,
      item.color,
      `"${(item.axles || '').replace(/"/g, '""')}"`,
      `"${(item.boxDimensions || '').replace(/"/g, '""')}"`,
      item.standardVolume,
      `"${(item.contractor || '').replace(/"/g, '""')}"`,
      item.registrationDate
    ])

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.join(','))
    ].join('\n')

    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    
    link.setAttribute('href', url)
    link.setAttribute('download', `Danh_sach_xe_dang_ky.csv`)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    toast.success('Đã tải xuống danh sách xe')
  }

  const handleImport = (importedData: any[]) => {
      // Map and Merge logic
        const mappedImport = importedData.map((item: any) => {
          const getVal = (keys: string[]) => {
            const foundKey = Object.keys(item).find(k => keys.includes(k.trim().toLowerCase()))
            return foundKey ? String(item[foundKey]) : ''
          }
          return {
            id: 0, 
            plate: getVal(['biển số', 'plate', 'bien so', 'plate_number']),
            truckModel: getVal(['loại xe', 'truckmodel', 'loại', 'model']),
            color: getVal(['màu xe', 'color', 'mau xe', 'mau']),
            axles: getVal(['số trục/bánh', 'axles', 'so truc', 'notes']),
            boxDimensions: getVal(['kích thước thùng', 'boxdimensions', 'kich thuoc', 'box_dimensions']),
            standardVolume: getVal(['thể tích tiêu chuẩn', 'standardvolume', 'the tich', 'standard_volume']),
            contractor: getVal(['nhà thầu', 'contractor', 'nha thau', 'owner']),
            registrationDate: getVal(['ngày đk', 'registrationdate', 'ngay dk', 'created_at']) || new Date().toISOString().split('T')[0],
            lastModified: new Date().toLocaleString('vi-VN')
          }
        }).filter(v => v.plate)

        if (mappedImport.length === 0) {
          toast.error('Không tìm thấy dữ liệu hợp lệ (Thiếu cột Biển số)')
          return
        }

        const updatedData = [...data]
        mappedImport.forEach(importedItem => {
          const existingIndex = updatedData.findIndex(d => d.plate === importedItem.plate)
          if (existingIndex > -1) {
            updatedData[existingIndex] = { ...updatedData[existingIndex], ...importedItem, id: updatedData[existingIndex].id }
          } else {
            updatedData.push({ ...importedItem, id: Date.now() + Math.random() })
          }
        })

        setData(updatedData)
        saveToBackend(updatedData)
        setIsDialogOpen(false)
        toast.success(`Đã nhập thành công ${mappedImport.length} phương tiện`)
  }

  const openAddDialog = () => {
    const today = new Date().toISOString().split('T')[0]
    setEditingItem({ 
        id: 0, 
        plate: '', 
        truckModel: '', 
        color: '',            
        axles: '',            
        boxDimensions: '',
        standardVolume: '',
        contractor: '', 
        registrationDate: today,
        lastModified: ''     
    })
    setIsDialogOpen(true)
  }

  return (
    <div className="h-full flex flex-col p-6 gap-2 overflow-hidden">
      <VehicleFilterBar 
        searchTerm={searchTerm}
        setSearchTerm={setSearchTerm}
        filterContractor={filterContractor}
        setFilterContractor={setFilterContractor}
        filterType={filterType}
        setFilterType={setFilterType}
        contractors={contractors}
        vehicleTypes={vehicleTypes}
        onAdd={openAddDialog}
        onExport={handleExportExcel}
      />

      <VehicleTable 
        data={filteredData}
        onEdit={handleEdit}
        onDelete={handleDelete}
      />

      {showScrollTop && (
        <button
          onClick={scrollToTop}
          className="fixed bottom-10 left-1/2 -translate-x-1/2 p-2 bg-primary text-primary-foreground rounded-full shadow-lg hover:bg-primary/90 transition-all animate-in fade-in zoom-in duration-300 z-50 flex items-center justify-center border border-primary/20"
          aria-label="Back to top"
        >
          <ExpandLess fontSize="medium" />
        </button>
      )}

      <VehicleDetailDialog 
        isOpen={isDialogOpen}
        onClose={() => setIsDialogOpen(false)}
        editingItem={editingItem}
        setEditingItem={setEditingItem}
        onSave={handleSave}
        onImport={handleImport}
      />
    </div>
  )
}
