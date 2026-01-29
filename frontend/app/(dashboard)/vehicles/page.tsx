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
  
  // Date selection
  const [selectedDate, setSelectedDate] = useState('')
  const [availableDates, setAvailableDates] = useState<string[]>([])

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
  const fetchInitialData = async (date?: string) => {
      try {
          const token = localStorage.getItem('token');
          const url = date ? `/api/registered_cars?date=${date}` : '/api/registered_cars';
          const res = await fetch(url, {
            headers: { 'Authorization': `Bearer ${token}` }
          })
          if (res.ok) {
              const rawData = await res.json()
              // Map Backend -> Frontend
                const mappedData = rawData.map((item: any) => ({
                    id: item.car_id,
                    plate: item.car_plate || '',
                    truckModel: item.car_model || '',
                    color: item.car_color || '',
                    axles: item.car_wheel || '',
                    standardVolume: item.car_volume || '',
                    contractor: item.car_owner || '',
                    registrationDate: item.car_register_date || '',
                    lastModified: item.car_update_date || ''
                }))
              setData(mappedData)
          }
      } catch (error) {
          console.error("Failed to load vehicles", error)
          toast.error("Không thể tải danh sách xe")
      }
  }

  const fetchDates = async () => {
    try {
        const token = localStorage.getItem('token');
        const res = await fetch('/api/registered_cars/dates', {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        if (res.ok) {
            const dates = await res.json()
            setAvailableDates(dates)
        }
    } catch (error) {
        console.error("Failed to load dates", error)
    }
  }

  useEffect(() => {
    fetchDates()
    fetchInitialData()
  }, [])

  const handleDateChange = (date: string) => {
    setSelectedDate(date);
    fetchInitialData(date);
  };

  // --- 2. Save Data to API ---
  const saveToBackend = async (newData: Vehicle[]) => {
      // Map Frontend -> Backend
      const payload = newData.map(item => ({
          id: typeof item.id === 'string' ? item.id : undefined, // Send ID if it's a string (backend ID), else undefined (new item, let backend gen)
          plate_number: item.plate,
          model: item.truckModel,
          color: item.color,
          notes: item.axles,
          standard_volume: item.standardVolume,
          owner: item.contractor,
          created_at: item.registrationDate
      }))

      const promise = (async () => {
        const token = localStorage.getItem('token');
        const res = await fetch('/api/registered_cars', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
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

  const handleSave = async (e: React.FormEvent, updatedItem: Vehicle, adminCode?: string) => {
    e.preventDefault();
    
    const isNew = !editingItem?.id || editingItem.id === 0;
    const token = localStorage.getItem('token');
    
    // Map Frontend -> Backend
    const payload = {
      car_plate: updatedItem.plate,
      car_brand: '',
      car_model: updatedItem.truckModel,
      car_color: updatedItem.color,
      car_wheel: updatedItem.axles,
      car_volume: updatedItem.standardVolume,
      car_owner: updatedItem.contractor,
      car_note: updatedItem.axles,
      car_register_date: updatedItem.registrationDate,
      admin_code: adminCode || '',
    };

    const promise = isNew
      ? fetch('/api/registered_cars', {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify(payload),
        })
      : fetch(`/api/registered_cars/${updatedItem.id}`, {
          method: 'PUT',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify(payload),
        });

    toast.promise(promise, {
      loading: isNew ? 'Đang thêm xe...' : 'Đang cập nhật xe...',
      success: () => {
        fetchInitialData();
        setIsDialogOpen(false);
        setEditingItem(null);
        return isNew ? 'Đã thêm xe mới' : 'Đã cập nhật xe';
      },
      error: (err) => {
        console.error(err);
        return 'Lỗi khi lưu dữ liệu';
      },
    });
  };

  const handleExportExcel = async () => {
    if (filteredData.length === 0) {
      toast.error('Không có dữ liệu để xuất')
      return
    }

    try {
      const token = localStorage.getItem('token');
      
      const urlParams = selectedDate ? `?date=${selectedDate}` : '';
      // Try to save directly to Downloads folder (desktop app mode)
      const saveResponse = await fetch(`/api/registered_cars/export/excel/save${urlParams}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (saveResponse.ok) {
        const result = await saveResponse.json();
        toast.success(`Đã lưu vào: ${result.file_path}`);
        return;
      }
      
      // Check if no data on backend
      if (saveResponse.status === 404) {
        toast.error("Không có dữ liệu để xuất");
        return;
      }
      
      // Fallback to browser download if save fails
      const response = await fetch(`/api/registered_cars/export/excel${urlParams}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.status === 404) {
        toast.error("Không có dữ liệu để xuất");
        return;
      }
      
      if (!response.ok) throw new Error('Export failed');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'Danh_sach_xe_dang_ky.csv';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success('Đã tải xuống danh sách xe');
    } catch (e) {
      console.error('Export Error:', e);
      toast.error('Lỗi khi xuất file');
    }
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
        standardVolume: '',
        contractor: '', 
        registrationDate: today,
        lastModified: ''     
    })
    setIsDialogOpen(true)
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="max-w-[1500px] w-full mx-auto flex-1 flex flex-col p-6 gap-4 min-h-0">
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
        selectedDate={selectedDate}
        setSelectedDate={handleDateChange}
        availableDates={availableDates}
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
    </div>
  )
}
