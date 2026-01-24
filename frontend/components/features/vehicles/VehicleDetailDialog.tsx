import { useState, useEffect, useRef } from 'react'
import { LocalShipping, Description, UploadFile } from '@mui/icons-material'
import { toast } from 'sonner'
import Dialog from '../../../components/ui/dialog'
import { Vehicle } from './VehicleTable'
import * as Papa from 'papaparse'
import * as XLSX from 'xlsx'

interface VehicleDetailDialogProps {
  isOpen: boolean
  onClose: () => void
  editingItem: Vehicle | null
  setEditingItem: React.Dispatch<React.SetStateAction<Vehicle | null>>
  onSave: (e: React.FormEvent, updatedItem: Vehicle) => void
  onImport: (data: any[]) => void
}

export default function VehicleDetailDialog({
  isOpen,
  onClose,
  editingItem,
  setEditingItem,
  onSave,
  onImport
}: VehicleDetailDialogProps) {
  const minVolRef = useRef<HTMLInputElement>(null)
  const maxVolRef = useRef<HTMLInputElement>(null)

  // Use local state for immediate feedback, synced with editingItem
  const [vMin, vMax] = (editingItem?.standardVolume || '').split(' - ').concat(['', ''])

  const updateVolume = (minVal: string, maxVal: string) => {
    const combined = minVal && maxVal ? `${minVal} - ${maxVal}` : (minVal || maxVal || '')
    setEditingItem(prev => ({ ...prev!, standardVolume: combined.trim() }))
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>, side: 'min' | 'max') => {
    const input = e.currentTarget
    if (e.key === 'ArrowRight' && side === 'min' && input.selectionStart === input.value.length) {
      maxVolRef.current?.focus()
    } else if (e.key === 'ArrowLeft' && side === 'max' && input.selectionStart === 0) {
      minVolRef.current?.focus()
    }
  }

  const formatDateForInput = (dateStr: string) => {
    if (!dateStr) return ''
    const parts = dateStr.split('-')
    if (parts.length === 3) {
      if (parts[0].length === 4) return dateStr // YYYY-MM-DD
      return `${parts[2]}-${parts[1]}-${parts[0]}` // DD-MM-YYYY -> YYYY-MM-DD
    }
    return ''
  }

  const formatDateForBackend = (dateStr: string) => {
    if (!dateStr) return ''
    const parts = dateStr.split('-')
    if (parts.length === 3) {
      if (parts[2].length === 4) return dateStr // DD-MM-YYYY
      return `${parts[2]}-${parts[1]}-${parts[0]}` // YYYY-MM-DD -> DD-MM-YYYY
    }
    return dateStr
  }

  const handleSubmit = (e: React.FormEvent) => {
      e.preventDefault()
      
      if (editingItem) {
          onSave(e, editingItem)
      }
  }

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    const extension = file.name.split('.').pop()?.toLowerCase()

    reader.onload = (event) => {
      const bstr = event.target?.result
      let rawData: any[] = []

      try {
        if (extension === 'csv') {
          const result = Papa.parse(bstr as string, { header: true, skipEmptyLines: true })
          rawData = result.data
        } else if (extension === 'xlsx') {
          const workbook = XLSX.read(bstr, { type: 'binary' })
          const firstSheetName = workbook.SheetNames[0]
          const worksheet = workbook.Sheets[firstSheetName]
          rawData = XLSX.utils.sheet_to_json(worksheet)
        }
        
        if (rawData.length > 0) {
            onImport(rawData)
        } else {
            toast.error('Tệp không có dữ liệu')
        }

      } catch (err) {
        toast.error('Lỗi khi đọc file')
        console.error(err)
      }
    }

    if (extension === 'xlsx') {
      reader.readAsBinaryString(file)
    } else {
      reader.readAsText(file)
    }
    e.target.value = ''
  }

  if (!isOpen) return null

  return (
    <Dialog 
        isOpen={isOpen} 
        onClose={onClose} 
        title={editingItem?.id ? 'Sửa thông tin xe' : 'Đăng ký xe mới'}
        maxWidth="2xl" 
      >
        <div className="space-y-6">
          {/* Bulk Import UI - Only shown when adding new (id is 0 or undefined) */}
          {(editingItem?.id === 0 || !editingItem?.id) && (
            <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-4 mb-2">
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-amber-500/20 flex items-center justify-center text-amber-500">
                    <UploadFile fontSize="medium" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-foreground">Bạn có danh sách lớn?</h3>
                    <p className="text-xs text-muted-foreground">Tải lên tệp .csv hoặc .xlsx để cập nhật hàng loạt</p>
                  </div>
                </div>
                <label className="cursor-pointer bg-amber-500 hover:bg-amber-600 text-black px-4 py-2 rounded-md text-xs font-bold transition-all shadow-md active:scale-95 flex items-center gap-2">
                  <UploadFile fontSize="small" /> Chọn tệp
                  <input 
                    type="file" 
                    className="hidden" 
                    accept=".csv,.xlsx" 
                    onChange={handleFileUpload}
                  />
                </label>
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
          
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

                 <div className="space-y-2">
                     <label className="text-sm font-medium text-muted-foreground">Thể tích tiêu chuẩn (m³)</label>
                     <div className="flex items-center gap-3">
                         <div className="relative flex-1">
                             <input 
                                 ref={minVolRef}
                                 type="text" 
                                 className="w-full p-2.5 bg-background border border-border rounded focus:border-primary focus:ring-0 outline-none font-mono text-md text-center"
                                 value={vMin}
                                 onChange={e => updateVolume(e.target.value, vMax)}
                                 onKeyDown={e => handleKeyDown(e, 'min')}
                                 placeholder="Min"
                             />
                         </div>
                         <span className="text-muted-foreground font-bold">-</span>
                         <div className="relative flex-1">
                             <input 
                                 ref={maxVolRef}
                                 type="text" 
                                 className="w-full p-2.5 bg-background border border-border rounded focus:border-primary focus:ring-0 outline-none font-mono text-md text-center"
                                 value={vMax}
                                 onChange={e => updateVolume(vMin, e.target.value)}
                                 onKeyDown={e => handleKeyDown(e, 'max')}
                                 placeholder="Max"
                             />
                         </div>
                         <span className="text-sm font-bold text-primary bg-primary/10 px-2 py-1 rounded border border-primary/20">m³</span>
                     </div>
                     <p className="text-[10px] text-muted-foreground italic mt-1">Sử dụng phím mũi tên để di chuyển giữa 2 ô</p>
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
                        className="w-full p-2.5 bg-background border border-border rounded focus:border-primary focus:ring-1 focus:ring-primary outline-none font-sans text-md appearance-none [color-scheme:dark]"
                        value={formatDateForInput(editingItem?.registrationDate || '')}
                        onChange={e => setEditingItem(prev => ({ ...prev!, registrationDate: formatDateForBackend(e.target.value) }))}
                        required
                    />
                </div>
             </div>
          </div>

          <div className="pt-4 flex items-center justify-end gap-3 border-t border-border mt-6">
            <button 
                type="button" 
                onClick={onClose}
                className="px-4 py-2 rounded text-sm font-medium text-muted-foreground hover:bg-muted transition-colors"
            >
                Hủy bỏ
            </button>
            <button 
                type="submit" 
                className="px-6 py-2 rounded bg-primary text-primary-foreground text-sm font-bold hover:bg-primary/90 transition-all shadow-md active:scale-95"
            >
                {editingItem?.id ? 'Cập nhật' : 'Đăng ký'}
            </button>
          </div>
          </form>
        </div>
    </Dialog>
  )
}
