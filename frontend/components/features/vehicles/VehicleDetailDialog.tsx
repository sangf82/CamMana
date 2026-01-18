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
  // Sub-fields
  const [dimL, setDimL] = useState('')
  const [dimW, setDimW] = useState('')
  const [dimH, setDimH] = useState('')
  const [volMin, setVolMin] = useState('')
  const [volMax, setVolMax] = useState('')

  // Refs for navigation
  const dimLRef = useRef<HTMLInputElement>(null)
  const dimWRef = useRef<HTMLInputElement>(null)
  const dimHRef = useRef<HTMLInputElement>(null)
  const volMinRef = useRef<HTMLInputElement>(null)
  const volMaxRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (editingItem && isOpen) {
        // Parse dimensions: "6.5 x 4.7 x 5.6 m"
        const dimStr = editingItem.boxDimensions || ''
        const dimMatch = dimStr.match(/([\d.]+)\s*x\s*([\d.]+)\s*x\s*([\d.]+)/)
        if (dimMatch) {
            setDimL(dimMatch[1])
            setDimW(dimMatch[2])
            setDimH(dimMatch[3])
        } else {
            setDimL(''); setDimW(''); setDimH('')
        }

        // Parse volume: "15.6 - 20"
        const volStr = editingItem.standardVolume || ''
        const volMatch = volStr.match(/([\d.]+)\s*-\s*([\d.]+)/)
        if (volMatch) {
            setVolMin(volMatch[1])
            setVolMax(volMatch[2])
        } else {
            setVolMin(''); setVolMax('')
        }
    }
  }, [editingItem, isOpen])

  const handleArrowNav = (e: React.KeyboardEvent<HTMLInputElement>, prev?: React.RefObject<HTMLInputElement | null>, next?: React.RefObject<HTMLInputElement | null>) => {
    if (e.key === 'ArrowRight' && next?.current) {
        next.current.focus()
        e.preventDefault()
    } else if (e.key === 'ArrowLeft' && prev?.current) {
        prev.current.focus()
        e.preventDefault()
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
      e.preventDefault()
      
      // Validation: Min volume should not be greater than Max volume
      if (volMin && volMax && parseFloat(volMin) > parseFloat(volMax)) {
          toast.error("Thể tích Min không thể lớn hơn Thể tích Max")
          return
      }
      
      const boxDimensions = dimL && dimW && dimH ? `${dimL} x ${dimW} x ${dimH} m` : ''
      const standardVolume = volMin && volMax ? `${volMin} - ${volMax}` : ''
      
      if (editingItem) {
          onSave(e, { ...editingItem, boxDimensions, standardVolume })
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

             <div className="grid grid-cols-2 gap-6 pt-2">
                <div className="space-y-2">
                    <label className="text-sm font-medium text-muted-foreground">Kích thước thùng (DxRxC)</label>
                    <div className="flex items-center gap-0.5 bg-background border border-border rounded p-1 focus-within:border-primary transition-colors">
                        <input 
                            ref={dimLRef}
                            type="number" step="0.1"
                            className="w-14 p-1.5 bg-transparent outline-none text-center font-mono text-sm [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
                            value={dimL}
                            onChange={e => setDimL(e.target.value)}
                            onKeyDown={e => handleArrowNav(e, undefined, dimWRef)}
                            placeholder="D"
                        />
                        <span className="text-muted-foreground/50 font-bold text-[10px]">x</span>
                        <input 
                            ref={dimWRef}
                            type="number" step="0.1"
                            className="w-14 p-1.5 bg-transparent outline-none text-center font-mono text-sm [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
                            value={dimW}
                            onChange={e => setDimW(e.target.value)}
                            onKeyDown={e => handleArrowNav(e, dimLRef, dimHRef)}
                            placeholder="R"
                        />
                        <span className="text-muted-foreground/50 font-bold text-[10px]">x</span>
                        <input 
                            ref={dimHRef}
                            type="number" step="0.1"
                            className="w-14 p-1.5 bg-transparent outline-none text-center font-mono text-sm [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
                            value={dimH}
                            onChange={e => setDimH(e.target.value)}
                            onKeyDown={e => handleArrowNav(e, dimWRef, undefined)}
                            placeholder="C"
                        />
                        <span className="text-muted-foreground ml-auto pr-2 font-mono text-xs opacity-50 italic">m</span>
                    </div>
                </div>
                <div className="space-y-2">
                    <label className="text-sm font-medium text-muted-foreground">Thể tích tiêu chuẩn (m³)</label>
                    <div className="flex items-center gap-0.5 bg-background border border-border rounded p-1 focus-within:border-primary transition-colors overflow-hidden">
                        <input 
                            ref={volMinRef}
                            type="number" step="0.1"
                            className="w-20 p-1.5 bg-transparent outline-none text-center font-mono text-sm [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
                            value={volMin}
                            onChange={e => setVolMin(e.target.value)}
                            onKeyDown={e => handleArrowNav(e, undefined, volMaxRef)}
                            placeholder="Min"
                        />
                        <span className="text-muted-foreground/50 font-bold text-[10px]">&mdash;</span>
                        <input 
                            ref={volMaxRef}
                            type="number" step="0.1"
                            className="w-20 p-1.5 bg-transparent outline-none text-center font-mono text-sm [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
                            value={volMax}
                            onChange={e => setVolMax(e.target.value)}
                            onKeyDown={e => handleArrowNav(e, volMinRef, undefined)}
                            placeholder="Max"
                        />
                         <span className="text-muted-foreground ml-auto pr-2 font-mono text-xs opacity-50 italic">m³</span>
                    </div>
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
                        className="w-full p-2.5 bg-background border border-border rounded focus:border-primary focus:ring-0 outline-none font-sans text-md"
                        value={editingItem?.registrationDate || ''}
                        onChange={e => setEditingItem(prev => ({ ...prev!, registrationDate: e.target.value }))}
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
