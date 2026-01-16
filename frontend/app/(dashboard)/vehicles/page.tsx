'use client'

import React, { useState, useEffect, useRef } from 'react'
import { Add, Edit, Delete, LocalShipping, Description, Warning, Search, Download, ChevronLeft, ExpandLess, FilterList, UploadFile, ExpandMore } from '@mui/icons-material'
import DataTable from '../../../components/ui/data-table'
import Dialog from '../../../components/ui/dialog'
import { toast } from 'sonner'
import * as Papa from 'papaparse'
import * as XLSX from 'xlsx'

// --- Types ---
interface Vehicle {
  id: number | string // Allow string IDs from backend
  plate: string
  truckModel: string          
  color: string               // New: Màu xe
  axles: string               // New: Số bánh
  boxDimensions: string       // New: Kích thước thùng
  standardVolume: string      // New: Thể tích tiêu chuẩn
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
  
  // Filters
  const [searchTerm, setSearchTerm] = useState('')
  const [filterContractor, setFilterContractor] = useState('All')
  const [pendingFilterContractor, setPendingFilterContractor] = useState('All')
  const [filterType, setFilterType] = useState('All')
  const [pendingFilterType, setPendingFilterType] = useState('All')
  const [showFilters, setShowFilters] = useState(false)
  const [isContractorOpen, setIsContractorOpen] = useState(false)
  const [isTypeOpen, setIsTypeOpen] = useState(false)

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

  // Sub-fields for improved entry
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

  const handleArrowNav = (e: React.KeyboardEvent<HTMLInputElement>, prev?: React.RefObject<HTMLInputElement | null>, next?: React.RefObject<HTMLInputElement | null>) => {
    // For number inputs, these keys move cursor or change focus
    if (e.key === 'ArrowRight' && next?.current) {
        // If at end of value or simple jump
        next.current.focus()
        e.preventDefault()
    } else if (e.key === 'ArrowLeft' && prev?.current) {
        prev.current.focus()
        e.preventDefault()
    }
  }

  // Sync sub-fields when editingItem starts
  useEffect(() => {
    if (editingItem) {
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
  }, [editingItem?.id, isDialogOpen])

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

  // --- Columns ---
  const columns = [
    { header: 'Biển số', accessorKey: 'plate', width: '120px' },
    { header: 'Loại xe', accessorKey: 'truckModel', width: '150px' },
    { header: 'Màu xe', accessorKey: 'color', width: '100px' },
    { header: 'Số trục/bánh', accessorKey: 'axles', width: '130px' },
    { header: 'Kích thước thùng', accessorKey: 'boxDimensions', width: '180px' },
    { header: 'Thể tích (m³)', accessorKey: 'standardVolume', width: '130px' },
    { header: 'Nhà thầu', accessorKey: 'contractor', width: '180px' },
    { 
        header: 'Ngày ĐK', 
        accessorKey: 'registrationDate',
        width: '120px',
        render: (row: Vehicle) => {
            if (!row.registrationDate) return <span>-</span>
            const parts = row.registrationDate.split('-')
            if (parts.length < 3) return <span>{row.registrationDate}</span>
            const [y, m, d] = parts
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

    // Validation: Min volume should not be greater than Max volume
    if (volMin && volMax && parseFloat(volMin) > parseFloat(volMax)) {
        toast.error("Thể tích Min không thể lớn hơn Thể tích Max")
        return
    }

    // Reconstruct strings from sub-fields
    const boxDimensions = dimL && dimW && dimH ? `${dimL} x ${dimW} x ${dimH} m` : ''
    const standardVolume = volMin && volMax ? `${volMin} - ${volMax}` : ''

    let newItem = { ...editingItem, boxDimensions, standardVolume, lastModified: now }
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

        if (rawData.length === 0) {
          toast.error('Tệp không có dữ liệu hoặc định dạng không đúng')
          return
        }

        // Map raw data to Vehicle interface
        // We try to match both Vietnamese headers and technical keys
        const mappedImport = rawData.map((item: any) => {
          const getVal = (keys: string[]) => {
            const foundKey = Object.keys(item).find(k => keys.includes(k.trim().toLowerCase()))
            return foundKey ? String(item[foundKey]) : ''
          }

          return {
            id: 0, // Mark as new for merging logic
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
        }).filter(v => v.plate) // Only keep rows with a plate number

        if (mappedImport.length === 0) {
          toast.error('Không tìm thấy dữ liệu hợp lệ (Thiếu cột Biển số)')
          return
        }

        // Merge with existing data (update if plate exists, else append)
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
      } catch (err) {
        console.error(err)
        toast.error('Lỗi khi xử lý tệp')
      }
    }

    if (extension === 'xlsx') {
      reader.readAsBinaryString(file)
    } else {
      reader.readAsText(file)
    }
    
    // Reset input
    e.target.value = ''
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
      {/* Header Section */}
      <div className="flex justify-between items-center shrink-0">
          <div className="space-y-1">
              <h1 className="text-2xl font-bold tracking-tight">Danh sách xe đăng ký</h1>
          </div>

          <div className="flex items-center gap-3">
              {/* Search Bar */}
              <div className="relative group min-w-[300px]">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-primary transition-colors" fontSize="small" />
                  <input 
                      type="text"
                      placeholder="Tìm kiếm biển số, loại xe..."
                      className="w-full pl-10 pr-4 py-2 bg-card border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-all text-sm"
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                  />
              </div>

              <button 
                  onClick={() => setShowFilters(!showFilters)}
                  className={`pl-3 pr-1 py-1.5 border rounded-md text-sm font-bold flex items-center gap-1 transition-all shadow-sm
                      ${showFilters || filterContractor !== 'All' || filterType !== 'All'
                          ? 'bg-primary text-primary-foreground border-primary shadow-primary/20' 
                          : 'bg-card border-border text-foreground hover:bg-muted'}`}
              >
                Lọc
                <div className={`transition-transform duration-200 ${showFilters ? '-rotate-90' : ''}`}>
                  <ChevronLeft fontSize="small" />
                </div>
              </button>
              
              <button 
                onClick={openAddDialog}
                className="bg-primary hover:bg-primary/90 text-primary-foreground px-4 py-1.5 rounded-md text-sm font-bold flex items-center gap-2 transition-all shadow-lg shadow-primary/20 active:scale-95"
              >
                <Add fontSize="small" /> Thêm xe mới
              </button>

              <button 
                onClick={handleExportExcel}
                className="px-4 py-1.5 bg-card border border-border text-foreground hover:bg-muted rounded-md text-sm font-bold flex items-center gap-2 transition-all shadow-sm"
              >
                <Download fontSize="small" /> Xuất Excel
              </button>
          </div>
      </div>

      {/* Filter Panel */}
      {showFilters && (
        <div className="flex flex-wrap items-center gap-6 py-2 px-4 bg-muted/20 border border-border rounded-lg animate-in fade-in slide-in-from-top-2 duration-200">
            <div className="flex items-center gap-3">
                <label className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest whitespace-nowrap">Nhà thầu</label>
                <div className="relative">
                    <button 
                        onClick={() => { setIsContractorOpen(!isContractorOpen); setIsTypeOpen(false); }}
                        className="w-full flex items-center justify-between min-w-[200px] px-3 py-1.5 bg-background border border-border rounded-md text-sm font-semibold focus:border-primary transition-all"
                    >
                        <span>{pendingFilterContractor === 'All' ? 'Tất cả nhà thầu' : pendingFilterContractor}</span>
                        <ExpandMore className={`transition-transform duration-200 ${isContractorOpen ? 'rotate-180' : ''}`} fontSize="small" />
                    </button>
                    {isContractorOpen && (
                        <div className="absolute top-full left-0 w-full z-[100] mt-1 bg-[#121212] border border-border rounded-xl shadow-2xl p-1 max-h-56 overflow-y-auto animate-in fade-in slide-in-from-top-1 duration-200">
                            {contractors.map(c => (
                                <button 
                                    key={c}
                                    onClick={() => { setPendingFilterContractor(c); setIsContractorOpen(false); }}
                                    className={`w-full text-left px-3 py-2 rounded-lg text-xs font-medium transition-colors hover:bg-primary/10 ${pendingFilterContractor === c ? 'text-primary bg-primary/5' : 'text-muted-foreground'}`}
                                >
                                    {c === 'All' ? 'Tất cả nhà thầu' : c}
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            <div className="flex items-center gap-3">
                <label className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest whitespace-nowrap">Loại xe</label>
                <div className="relative">
                    <button 
                        onClick={() => { setIsTypeOpen(!isTypeOpen); setIsContractorOpen(false); }}
                        className="w-full flex items-center justify-between min-w-[200px] px-3 py-1.5 bg-background border border-border rounded-md text-sm font-semibold focus:border-primary transition-all"
                    >
                        <span>{pendingFilterType === 'All' ? 'Tất cả loại xe' : pendingFilterType}</span>
                        <ExpandMore className={`transition-transform duration-200 ${isTypeOpen ? 'rotate-180' : ''}`} fontSize="small" />
                    </button>
                    {isTypeOpen && (
                        <div className="absolute top-full left-0 w-full z-[100] mt-1 bg-[#121212] border border-border rounded-xl shadow-2xl p-1 max-h-56 overflow-y-auto animate-in fade-in slide-in-from-top-1 duration-200">
                            {vehicleTypes.map(v => (
                                <button 
                                    key={v}
                                    onClick={() => { setPendingFilterType(v); setIsTypeOpen(false); }}
                                    className={`w-full text-left px-3 py-2 rounded-lg text-xs font-medium transition-colors hover:bg-primary/10 ${pendingFilterType === v ? 'text-primary bg-primary/5' : 'text-muted-foreground'}`}
                                >
                                    {v === 'All' ? 'Tất cả loại xe' : v}
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            <div className="flex items-center gap-3 ml-auto">
                {(filterContractor !== 'All' || filterType !== 'All' || searchTerm !== '') && (
                    <button 
                        onClick={() => { 
                            setFilterContractor('All'); setPendingFilterContractor('All'); 
                            setFilterType('All'); setPendingFilterType('All');
                            setSearchTerm(''); 
                        }}
                        className="text-xs text-red-400 hover:text-red-300 font-bold px-2 py-1 transition-colors"
                    >
                        Xóa lọc
                    </button>
                )}
                <button 
                    onClick={() => {
                        setFilterContractor(pendingFilterContractor);
                        setFilterType(pendingFilterType);
                    }}
                    className="px-6 py-1.5 bg-primary text-primary-foreground text-sm font-bold rounded-md hover:bg-primary/90 transition-all shadow-lg shadow-primary/20 active:scale-95"
                >
                    Áp dụng
                </button>
            </div>
        </div>
      )}

      {/* Table Section */}
      <div className="border border-border rounded-lg bg-card overflow-hidden flex-1 flex flex-col min-h-0">
        {/* Unified Scroll Container */}
        <div className="flex-1 overflow-y-scroll overflow-x-auto scrollbar-show-always min-h-0">
          <table className="text-sm text-left border-collapse table-fixed w-fit min-w-full">
            {/* Sticky Header */}
            <thead className="text-[10px] uppercase text-muted-foreground font-bold font-mono sticky top-0 bg-muted/90 backdrop-blur-md z-20 border-b border-border">
              <tr>
                {columns.map((col, idx) => (
                  <th key={idx} className="px-4 py-3 whitespace-nowrap" style={{ width: col.width || 'auto' }}>
                    {col.header}
                  </th>
                ))}
              </tr>
            </thead>

            {/* Data Body */}
            <tbody className="divide-y divide-border">
              {filteredData.length > 0 ? (
                filteredData.map((row, rowIdx) => (
                  <tr 
                    key={rowIdx} 
                    className="bg-card hover:bg-muted/5 transition-colors group"
                  >
                    {columns.map((col, colIdx) => (
                      <td key={colIdx} className="px-4 py-2.5 whitespace-nowrap text-foreground font-medium text-xs truncate" style={{ width: col.width || 'auto' }}>
                        {col.render ? col.render(row) : (row as any)[col.accessorKey!]}
                      </td>
                    ))}
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={columns.length} className="px-4 py-12 text-center text-muted-foreground font-medium">
                    Không có phương tiện nào được tìm thấy
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Floating Scroll to Top Button */}
      {showScrollTop && (
        <button
          onClick={scrollToTop}
          className="fixed bottom-10 left-1/2 -translate-x-1/2 p-2 bg-primary text-primary-foreground rounded-full shadow-lg hover:bg-primary/90 transition-all animate-in fade-in zoom-in duration-300 z-50 flex items-center justify-center border border-primary/20"
          aria-label="Back to top"
        >
          <ExpandLess fontSize="medium" />
        </button>
      )}

      {/* CRUD Dialog */}
      <Dialog 
        isOpen={isDialogOpen} 
        onClose={() => setIsDialogOpen(false)} 
        title={editingItem?.id ? 'Sửa thông tin xe' : 'Đăng ký xe mới'}
        maxWidth="2xl" 
      >
        <div className="space-y-6">
          {/* Bulk Import UI - Only shown when adding new */}
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
                        className="w-full p-2.5 bg-background border border-border rounded focus:border-primary focus:ring-0 outline-none font-sans text-md dark:[color-scheme:dark]"
                        value={editingItem?.registrationDate || ''}
                        onChange={e => setEditingItem(prev => ({ ...prev!, registrationDate: e.target.value }))}
                        required
                    />
                </div>
             </div>
          </div>

          <div className="flex justify-end gap-3 pt-2 mt-4">
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
        </div>
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
