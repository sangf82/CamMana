'use client'

import React, { useState, useEffect } from 'react'
import { Add, Edit, Delete, Settings, ExpandMore, Check, Close, Warning, Visibility, VisibilityOff, Search, Download, ExpandLess } from '@mui/icons-material'
import Dialog from '../../../components/ui/dialog'
import { toast } from 'sonner'

// --- Types ---
interface LocationItem {
    id: string | number
    name: string
    tag?: string  // Cơ bản | Cổng vào | Cổng ra | Đo thể tích
}

interface TypeItem {
    id: string | number
    name: string
    functions: string // comma separated IDs
}

interface Camera {
  id: number
  name: string
  ip: string
  location: string
  status: 'Online' | 'Offline' | 'Connected' | 'Local'
  type: string // Stores the TypeItem.name
  username?: string
  password?: string
  brand?: string
  cam_id?: string
}

const SMART_FUNCTIONS = [
    { id: 'car_detect', name: 'Nhận diện xe (Real-time)', desc: 'Phát hiện phương tiện từ luồng video trực tiếp' },
    { id: 'plate_detect', name: 'Nhận diện biển số', desc: 'Tự động trích xuất biển số xe từ hình ảnh' },
    { id: 'color_detect', name: 'Nhận diện màu xe', desc: 'Phân tích màu sắc chủ đạo của phương tiện' },
    { id: 'wheel_detect', name: 'Nhận diện số bánh', desc: 'Đếm số bánh và nhận diện loại trục xe' },
    { id: 'box_detect', name: 'Kích thước thùng xe', desc: 'Tính toán dài x rộng x cao của thùng xe' },
    { id: 'volume_detect', name: 'Tính thể tích vật liệu', desc: 'Ước tính thể tích hàng hóa trong thùng xe' },
]

export default function CamerasPage() {
  const [data, setData] = useState<Camera[]>([])
  const [locations, setLocations] = useState<LocationItem[]>([])
  const [camTypes, setCamTypes] = useState<TypeItem[]>([])
  const [searchTerm, setSearchTerm] = useState('')
  const [showScrollTop, setShowScrollTop] = useState(false)
  
  // Dialog States
  const [isCamDialogOpen, setIsCamDialogOpen] = useState(false)
  const [isConfigDialogOpen, setIsConfigDialogOpen] = useState(false)
  const [editingItem, setEditingItem] = useState<Camera | null>(null)
  
  // Delete confirm states
  const [deleteCamId, setDeleteCamId] = useState<number | null>(null)
  const [deleteLocId, setDeleteLocId] = useState<string | number | null>(null)
  const [deleteLocName, setDeleteLocName] = useState<string>('')

  // New Location Inputs
  const [newLocation, setNewLocation] = useState('')
  const [newLocationTag, setNewLocationTag] = useState('Cơ bản')
  const [editLocIndex, setEditLocIndex] = useState<number | null>(null)
  const [tempLocName, setTempLocName] = useState('')
  const [tempLocTag, setTempLocTag] = useState('')

  // New Type Inputs
  const [newTypeName, setNewTypeName] = useState('')
  const [newTypeFunctions, setNewTypeFunctions] = useState<string[]>([])
  const [editTypeIndex, setEditTypeIndex] = useState<number | null>(null)
  const [tempTypeName, setTempTypeName] = useState('')
  const [tempTypeFunctions, setTempTypeFunctions] = useState<string[]>([])

  const [showPassword, setShowPassword] = useState(false)
  const [isNewTypeDropdownOpen, setIsNewTypeDropdownOpen] = useState(false)
  const [editTypeDropdownIndex, setEditTypeDropdownIndex] = useState<number | null>(null)
  const [isNewLocDropdownOpen, setIsNewLocDropdownOpen] = useState(false)
  const [editLocDropdownIndex, setEditLocDropdownIndex] = useState<number | null>(null)
  const [isCamLocOpen, setIsCamLocOpen] = useState(false)
  const [isCamTypeOpen, setIsCamTypeOpen] = useState(false)

  // --- 1. Load Data from API ---
  const fetchInitialData = async () => {
    try {
        const [locRes, typeRes, camRes] = await Promise.all([
            fetch('/api/cameras/locations'),
            fetch('/api/cameras/types'),
            fetch('/api/cameras/saved')
        ])

        if (locRes.ok) setLocations(await locRes.json())
        if (typeRes.ok) {
            const types = await typeRes.json()
            setCamTypes(types.map((t: any) => ({ ...t, functions: t.functions || '' })))
        }
        if (camRes.ok) setData(await camRes.json())
    } catch (error) {
        console.error("Failed to load initial data", error)
    }
  }

  useEffect(() => {
    fetchInitialData()
  }, [])

  // --- 2. API Update Wrappers ---
  const updateLocations = async (updatedLocs: LocationItem[]) => {
      setLocations(updatedLocs)
      const promise = fetch('/api/cameras/locations', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(updatedLocs)
      })
      toast.promise(promise, {
        loading: 'Đang cập nhật vị trí...',
        success: 'Đã cập nhật danh sách vị trí',
        error: 'Lỗi khi cập nhật vị trí'
      })
      await promise
      window.dispatchEvent(new CustomEvent('cammana_locations_updated'))
  }

  const updateTypes = async (updatedTypes: TypeItem[]) => {
      setCamTypes(updatedTypes)
      const promise = fetch('/api/cameras/types', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(updatedTypes)
      })
      toast.promise(promise, {
        loading: 'Đang cập nhật loại camera...',
        success: 'Đã cập nhật danh sách loại camera',
        error: 'Lỗi khi cập nhật loại camera'
      })
      await promise
  }

  // --- 3. Camera CRUD ---
  const handleEdit = async (item: Camera) => {
    // Refresh dependencies
    const res = await fetch('/api/cameras/locations')
    if(res.ok) setLocations(await res.json())
    
    setEditingItem(item)
    setIsCamDialogOpen(true)
  }

  const openAddDialog = async () => {
    const res = await fetch('/api/cameras/locations')
    if(res.ok) setLocations(await res.json())

    setEditingItem({ 
        id: 0, 
        name: '', 
        ip: '', 
        location: locations[0]?.name || '', 
        status: 'Offline', 
        type: camTypes[0]?.name || '', 
        username: '', 
        password: '', 
        brand: '', 
        cam_id: '' 
    })
    setIsCamDialogOpen(true)
  }

  const executeDeleteCamera = () => {
    if (deleteCamId !== null) {
        const id = deleteCamId
        setData(prev => prev.filter(item => item.id !== id))
        const promise = fetch(`/api/cameras/${id}`, { method: 'DELETE' })
        toast.promise(promise, {
            loading: 'Đang xóa camera...',
            success: 'Đã xóa camera thành công',
            error: 'Lỗi khi xóa camera'
        })
        setDeleteCamId(null)
    }
  }

  const handleSaveCamera = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editingItem) return

    const isNew = !editingItem.id
    const camToSave = { ...editingItem, id: isNew ? Date.now() : editingItem.id }

    if (isNew) setData(prev => [camToSave, ...prev])
    else setData(prev => prev.map(item => item.id === camToSave.id ? camToSave : item))
    
    setIsCamDialogOpen(false)
    setEditingItem(null)

    const promise = fetch('/api/cameras', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(camToSave)
    })

    toast.promise(promise, {
        loading: isNew ? 'Đang thêm camera...' : 'Đang lưu camera...',
        success: isNew ? 'Đã thêm camera mới' : 'Đã cập nhật camera',
        error: 'Lỗi khi lưu camera'
    })
    await promise
    fetchInitialData()
  }

  // --- 4. Location Handlers ---
  const handleAddLocation = () => {
    if (newLocation && !locations.some(l => l.name === newLocation)) {
        updateLocations([...locations, { 
          id: Date.now().toString(), 
          name: newLocation,
          tag: newLocationTag
        }])
        setNewLocation('')
        setNewLocationTag('Cơ bản')
    }
  }

  const handleSaveEditLocation = (index: number) => {
    if (tempLocName && !locations.some((l, i) => i !== index && l.name === tempLocName)) {
        const updated = [...locations]
        updated[index] = { ...updated[index], name: tempLocName, tag: tempLocTag }
        updateLocations(updated)
        setEditLocIndex(null)
    }
  }

  const executeDeleteLocation = () => {
    if (deleteLocId !== null) {
        updateLocations(locations.filter(l => l.id !== deleteLocId))
        setDeleteLocId(null)
    }
  }

  // --- 5. Type Handlers ---
  const handleAddType = () => {
    if (newTypeName && !camTypes.some(t => t.name === newTypeName)) {
        updateTypes([...camTypes, {
            id: Date.now().toString(),
            name: newTypeName,
            functions: newTypeFunctions.join(';')
        }])
        setNewTypeName('')
        setNewTypeFunctions([])
    }
  }

  const handleToggleTypeFunction = (funcId: string, isNew: boolean = true) => {
    const current = isNew ? newTypeFunctions : tempTypeFunctions;
    const setter = isNew ? setNewTypeFunctions : setTempTypeFunctions;
    if (current.includes(funcId)) setter(current.filter(id => id !== funcId));
    else if (current.length < 2) setter([...current, funcId]);
    else toast.error('Tối đa 2 chức năng cho mỗi loại camera');
  }

  const handleSaveEditType = (index: number) => {
    if (tempTypeName && !camTypes.some((t, i) => i !== index && t.name === tempTypeName)) {
        const updated = [...camTypes];
        updated[index] = { ...updated[index], name: tempTypeName, functions: tempTypeFunctions.join(';') };
        updateTypes(updated);
        setEditTypeIndex(null);
    }
  }

  const handleDeleteType = (id: string | number) => {
    updateTypes(camTypes.filter(t => t.id !== id))
  }

  // --- 6. Scroll & Search ---
  useEffect(() => {
    const handleScroll = () => setShowScrollTop(window.scrollY > 300)
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const filteredData = data.filter(item => {
    const s = searchTerm.toLowerCase()
    return item.name.toLowerCase().includes(s) || item.ip.toLowerCase().includes(s) || item.location.toLowerCase().includes(s)
  })

  // --- 7. Table Columns ---
  const columns = [
    { 
      header: 'Trạng thái', 
      width: '100px',
      render: (row: Camera) => {
        const statusConfig = {
          Online: { color: 'bg-green-500/10 text-green-500', dot: 'bg-green-500 animate-pulse' },
          Connected: { color: 'bg-blue-500/10 text-blue-500', dot: 'bg-blue-500' },
          Local: { color: 'bg-yellow-500/10 text-yellow-500', dot: 'bg-yellow-500' },
          Offline: { color: 'bg-red-500/10 text-red-500', dot: 'bg-red-500' }
        }
        const cfg = statusConfig[row.status] || statusConfig.Offline
        return (
          <span className={`inline-flex items-center px-2 py-1 rounded text-[10px] font-bold uppercase ${cfg.color}`}>
            <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${cfg.dot}`} />
            {row.status}
          </span>
        )
      }
    },
    { header: 'Mã Camera', accessorKey: 'cam_id' },
    { header: 'Thương hiệu', accessorKey: 'brand' },
    { header: 'Tên Camera', accessorKey: 'name' },
    { header: 'IP Address', accessorKey: 'ip' },
    { header: 'Vị trí', accessorKey: 'location' },
    { 
      header: 'Loại Camera', 
      render: (row: Camera) => {
        const typeMatch = camTypes.find(t => t.name === row.type);
        return (
          <span className="text-xs font-semibold text-foreground">
            {typeMatch ? typeMatch.name : (row.type?.includes(';') ? 'Nhiều chức năng' : (row.type || 'Mặc định'))}
          </span>
        )
      }
    },
    { 
      header: 'Thao tác', 
      width: '100px',
      render: (row: Camera) => (
        <div className="flex gap-2">
          <button onClick={() => handleEdit(row)} className="p-1 text-blue-500 hover:bg-blue-500/10 rounded"><Edit fontSize="small"/></button>
          <button onClick={() => setDeleteCamId(row.id)} className="p-1 text-red-500 hover:bg-red-500/10 rounded"><Delete fontSize="small"/></button>
        </div>
      )
    }
  ]

  return (
    <div className="h-full flex flex-col p-6 gap-4 overflow-hidden bg-background">
      {/* Header */}
      <div className="flex justify-between items-center shrink-0">
          <h1 className="text-2xl font-bold tracking-tight text-primary">Danh sách Camera</h1>
          <div className="flex items-center gap-3">
              <div className="relative min-w-[300px]">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" fontSize="small" />
                  <input 
                      className="w-full pl-10 pr-4 py-2 bg-card border border-border rounded-md text-sm outline-none focus:border-primary"
                      placeholder="Tìm kiếm camera..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                  />
              </div>
              <button onClick={() => setIsConfigDialogOpen(true)} className="px-4 py-2 bg-card border border-border rounded-md text-sm font-bold flex items-center gap-2 hover:bg-muted transition-all"><Settings fontSize="small" /> Cấu hình</button>
              <button onClick={openAddDialog} className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-bold flex items-center gap-2 hover:bg-primary/90 transition-all shadow-lg shadow-primary/20"><Add fontSize="small" /> Thêm camera</button>
          </div>
      </div>

      {/* Table */}
      <div className="border border-border rounded-lg bg-card overflow-hidden flex-1 flex flex-col min-h-0">
        <div className="flex-1 overflow-auto scrollbar-show-always">
          <table className="text-sm text-left border-collapse w-full min-w-max">
            <thead className="text-[10px] uppercase text-muted-foreground font-bold sticky top-0 bg-muted/95 backdrop-blur-sm z-20 border-b border-border">
              <tr>{columns.map((c, i) => <th key={i} className="px-4 py-3" style={{ width: (c as any).width }}>{c.header}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filteredData.map((row, i) => (
                <tr key={i} className="hover:bg-muted/5 transition-colors">
                  {columns.map((c, j) => <td key={j} className="px-4 py-2.5 text-xs text-foreground font-medium">{(c as any).render ? (c as any).render(row) : (row as any)[(c as any).accessorKey]}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
          {filteredData.length === 0 && <div className="p-12 text-center text-muted-foreground italic">Không tìm thấy camera nào</div>}
        </div>
      </div>

      {/* Camera Dialog */}
      <Dialog isOpen={isCamDialogOpen} onClose={() => setIsCamDialogOpen(false)} title={editingItem?.id ? 'Cấu hình Camera' : 'Thêm Camera mới'} maxWidth="sm">
        <form onSubmit={handleSaveCamera} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-bold text-muted-foreground uppercase">Tên Camera</label>
              <input className="w-full p-2 bg-background border border-border rounded text-sm outline-none focus:border-primary" value={editingItem?.name || ''} onChange={e => setEditingItem(p => ({ ...p!, name: e.target.value }))} required />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-bold text-muted-foreground uppercase">Thương hiệu</label>
              <input className="w-full p-2 bg-background border border-border rounded text-sm outline-none focus:border-primary" value={editingItem?.brand || ''} onChange={e => setEditingItem(p => ({ ...p!, brand: e.target.value }))} required />
            </div>
          </div>
          <div className="space-y-1">
            <label className="text-xs font-bold text-muted-foreground uppercase">Địa chỉ IP</label>
            <input className="w-full p-2 bg-background border border-border rounded text-sm outline-none focus:border-primary" value={editingItem?.ip || ''} onChange={e => setEditingItem(p => ({ ...p!, ip: e.target.value }))} required />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-bold text-muted-foreground uppercase">Tài khoản</label>
              <input className="w-full p-2 bg-background border border-border rounded text-sm outline-none focus:border-primary" value={editingItem?.username || ''} onChange={e => setEditingItem(p => ({ ...p!, username: e.target.value }))} />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-bold text-muted-foreground uppercase">Mật khẩu</label>
              <div className="relative">
                <input type={showPassword ? "text" : "password"} className="w-full p-2 pr-10 bg-background border border-border rounded text-sm outline-none focus:border-primary" value={editingItem?.password || ''} onChange={e => setEditingItem(p => ({ ...p!, password: e.target.value }))} />
                <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute inset-y-0 right-0 px-3 text-muted-foreground hover:text-foreground">{showPassword ? <VisibilityOff fontSize="small"/> : <Visibility fontSize="small"/>}</button>
              </div>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-bold text-muted-foreground uppercase">Vị trí</label>
              <div className="relative">
                <button 
                  type="button" 
                  onClick={() => { setIsCamLocOpen(!isCamLocOpen); setIsCamTypeOpen(false); }}
                  className="w-full flex items-center justify-between p-2 bg-background border border-border rounded text-xs font-semibold focus:border-primary transition-all"
                >
                  <span className="truncate">{editingItem?.location || 'Chọn vị trí...'}</span>
                  <ExpandMore className={`transition-transform duration-200 ${isCamLocOpen ? 'rotate-180' : ''}`} fontSize="small" />
                </button>
                {isCamLocOpen && (
                  <div className="absolute top-full left-0 w-full z-[110] mt-1 bg-[#121212] border border-border rounded-lg shadow-2xl p-1 max-h-48 overflow-y-auto animate-in fade-in slide-in-from-top-1 duration-200">
                    {locations.map(l => (
                      <button 
                        key={l.id}
                        type="button"
                        onClick={() => { setEditingItem(p => ({ ...p!, location: l.name })); setIsCamLocOpen(false); }}
                        className={`w-full text-left px-3 py-1.5 rounded text-xs transition-colors hover:bg-primary/10 ${editingItem?.location === l.name ? 'text-primary bg-primary/5' : 'text-muted-foreground'}`}
                      >
                        {l.name}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
            <div className="space-y-1">
              <label className="text-xs font-bold text-muted-foreground uppercase">Loại Camera</label>
              <div className="relative">
                <button 
                  type="button" 
                  onClick={() => { setIsCamTypeOpen(!isCamTypeOpen); setIsCamLocOpen(false); }}
                  className="w-full flex items-center justify-between p-2 bg-background border border-border rounded text-xs font-semibold focus:border-primary transition-all"
                >
                  <span className="truncate">{editingItem?.type || 'Chọn loại...'}</span>
                  <ExpandMore className={`transition-transform duration-200 ${isCamTypeOpen ? 'rotate-180' : ''}`} fontSize="small" />
                </button>
                {isCamTypeOpen && (
                  <div className="absolute top-full left-0 w-full z-[110] mt-1 bg-[#121212] border border-border rounded-lg shadow-2xl p-1 max-h-48 overflow-y-auto animate-in fade-in slide-in-from-top-1 duration-200">
                    <button 
                      type="button"
                      onClick={() => { setEditingItem(p => ({ ...p!, type: '' })); setIsCamTypeOpen(false); }}
                      className="w-full text-left px-3 py-1.5 rounded text-xs text-muted-foreground hover:bg-primary/10"
                    >
                      Chọn loại...
                    </button>
                    {camTypes.map(t => (
                      <button 
                        key={t.id}
                        type="button"
                        onClick={() => { setEditingItem(p => ({ ...p!, type: t.name })); setIsCamTypeOpen(false); }}
                        className={`w-full text-left px-3 py-1.5 rounded text-xs transition-colors hover:bg-primary/10 ${editingItem?.type === t.name ? 'text-primary bg-primary/5' : 'text-muted-foreground'}`}
                      >
                        {t.name}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
          {editingItem?.type && camTypes.find(t => t.name === editingItem.type) && (
            <div className="flex flex-wrap gap-2 p-2 bg-muted/30 rounded border border-border/50">
              <span className="text-[10px] font-bold text-muted-foreground uppercase w-full">Chức năng tích hợp:</span>
              {(camTypes.find(t => t.name === editingItem.type)?.functions || '').split(';').filter(Boolean).map(fid => (
                <span key={fid} className="px-2 py-0.5 bg-primary/10 text-primary border border-primary/20 rounded text-[10px] font-bold">
                  {SMART_FUNCTIONS.find(sf => sf.id === fid)?.name || fid}
                </span>
              ))}
            </div>
          )}
          <div className="flex justify-end gap-3 pt-4 border-t border-border">
            <button type="button" onClick={() => setIsCamDialogOpen(false)} className="px-4 py-2 text-sm font-medium text-muted-foreground hover:bg-muted rounded">Hủy</button>
            <button type="submit" className="px-6 py-2 bg-primary text-primary-foreground rounded text-sm font-bold shadow-lg shadow-primary/20 hover:bg-primary/90">Lưu cấu hình</button>
          </div>
        </form>
      </Dialog>

      {/* Config Dialog */}
      <Dialog isOpen={isConfigDialogOpen} onClose={() => { 
        setIsConfigDialogOpen(false); 
        setIsNewTypeDropdownOpen(false); 
        setEditTypeDropdownIndex(null); 
        setIsNewLocDropdownOpen(false);
        setEditLocDropdownIndex(null);
      }} title="Cấu hình Hệ thống" maxWidth="3xl">
        <div className="grid grid-cols-2 gap-10 p-2">
          {/* Locations */}
          <div className="space-y-3">
            <h3 className="font-bold text-xl text-primary tracking-wider">Vị trí (Locations)</h3>
            <div className="space-y-2 bg-muted/20 p-4 rounded-xl border border-border/50 shadow-inner">
              <input 
                className="w-full h-10 px-3 bg-background/50 border border-border rounded-lg text-xs outline-none focus:border-primary transition-all placeholder:italic" 
                placeholder="Tên vị trí (vd: Cổng Chính)..." 
                value={newLocation} 
                onChange={e => setNewLocation(e.target.value)} 
              />
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <button 
                    type="button" 
                    onClick={() => setIsNewLocDropdownOpen(!isNewLocDropdownOpen)}
                    className="w-full h-10 px-3 bg-background/50 border border-border rounded-lg text-xs font-semibold text-foreground text-left flex justify-between items-center focus:border-primary transition-all"
                  >
                    <span>{newLocationTag}</span>
                    <ExpandMore className={`transition-transform duration-300 ${isNewLocDropdownOpen ? 'rotate-180' : ''}`} fontSize="small" />
                  </button>
                  {isNewLocDropdownOpen && (
                    <div className="absolute top-full left-0 w-full z-[60] mt-2 bg-[#121212] border border-border rounded-xl shadow-2xl p-1 animate-in fade-in slide-in-from-top-2 duration-200">
                      {['Cơ bản', 'Cổng vào', 'Cổng ra', 'Đo thể tích'].map(v => (
                        <button 
                          key={v}
                          onClick={() => { setNewLocationTag(v); setIsNewLocDropdownOpen(false); }}
                          className={`w-full text-left px-3 py-2 rounded-lg text-xs font-medium transition-colors hover:bg-primary/10 ${newLocationTag === v ? 'text-primary bg-primary/5' : 'text-muted-foreground'}`}
                        >
                          {v}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                <button onClick={handleAddLocation} className="w-[42px] h-[42px] shrink-0 bg-primary text-primary-foreground rounded-lg flex items-center justify-center shadow-lg shadow-primary/20 hover:scale-105 active:scale-95 transition-all"><Add fontSize="small"/></button>
              </div>
            </div>
            <div className="max-h-[450px] overflow-y-auto space-y-3 pr-2 scrollbar-thin">
              {locations.map((loc, idx) => (
                <div key={loc.id} className="p-3 bg-muted/10 border-l-4 border-l-primary rounded-r-xl flex items-center justify-between group hover:bg-muted/20 transition-all shadow-sm">
                  {editLocIndex === idx ? (
                    <div className="flex-1 flex flex-col gap-2">
                      <input className="w-full h-8 px-2 bg-background border border-primary rounded text-xs outline-none" value={tempLocName} onChange={e => setTempLocName(e.target.value)} autoFocus />
                      <div className="flex gap-2 items-center">
                        <div className="relative flex-1">
                          <button 
                            type="button" 
                            onClick={() => setEditLocDropdownIndex(editLocDropdownIndex === idx ? null : idx)}
                            className="w-full h-8 px-2 bg-background border border-border rounded text-[10px] font-semibold text-left flex justify-between items-center focus:border-primary transition-colors"
                          >
                            <span>{tempLocTag}</span>
                            <ExpandMore className={`transition-transform duration-300 ${editLocDropdownIndex === idx ? 'rotate-180' : ''}`} fontSize="small" />
                          </button>
                          {editLocDropdownIndex === idx && (
                            <div className="absolute top-full left-0 w-full z-[60] mt-1 bg-[#121212] border border-border rounded-lg shadow-2xl p-1 animate-in fade-in slide-in-from-top-2 duration-200">
                              {['Cơ bản', 'Cổng vào', 'Cổng ra', 'Đo thể tích'].map(v => (
                                <button 
                                  key={v}
                                  onClick={() => { setTempLocTag(v); setEditLocDropdownIndex(null); }}
                                  className={`w-full text-left px-2 py-1.5 rounded text-[10px] font-medium transition-colors hover:bg-primary/10 ${tempLocTag === v ? 'text-primary bg-primary/5' : 'text-muted-foreground'}`}
                                >
                                  {v}
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                        <div className="flex gap-1">
                          <button onClick={() => { handleSaveEditLocation(idx); setEditLocDropdownIndex(null); }} className="w-8 h-8 flex items-center justify-center bg-green-500/10 text-green-500 rounded-md hover:bg-green-500/20 transition-all"><Check sx={{ fontSize: 16 }}/></button>
                          <button onClick={() => { setEditLocIndex(null); setEditLocDropdownIndex(null); }} className="w-8 h-8 flex items-center justify-center bg-red-500/10 text-red-500 rounded-md hover:bg-red-500/20 transition-all"><Close sx={{ fontSize: 16 }}/></button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <>
                      <div className="flex-1">
                        <div className="font-semibold text-sm text-foreground">{loc.name}</div>
                        <div className="text-[10px] text-primary/80 font-medium mt-0.5">{loc.tag}</div>
                      </div>
                      <div className="flex gap-1 ml-4 opacity-0 group-hover:opacity-100 transition-all shrink-0">
                        <button onClick={() => {setEditLocIndex(idx); setTempLocName(loc.name); setTempLocTag(loc.tag||'Cơ bản')}} className="w-8 h-8 flex items-center justify-center bg-background border border-border rounded-md hover:text-blue-500 transition-colors"><Edit sx={{ fontSize: 16 }}/></button>
                        <button onClick={() => setDeleteLocId(loc.id)} className="w-8 h-8 flex items-center justify-center bg-background border border-border rounded-md hover:text-red-500 transition-colors"><Delete sx={{ fontSize: 16 }}/></button>
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Types */}
          <div className="space-y-3">
            <h3 className="font-bold text-xl text-primary tracking-wider">Loại Camera (Types)</h3>
            <div className="space-y-2 bg-muted/20 p-4 rounded-xl border border-border/50 shadow-inner">
              <input 
                className="w-full h-10 px-3 bg-background/50 border border-border rounded-lg text-xs outline-none focus:border-primary transition-all placeholder:italic" 
                placeholder="Tên loại (vd: Phân tích xe)..." 
                value={newTypeName} 
                onChange={e => setNewTypeName(e.target.value)} 
              />
              <div className="flex gap-2">
                {/* Custom Tickbox Dropdown */}
                <div className="relative flex-1">
                  <button 
                    type="button" 
                    onClick={() => setIsNewTypeDropdownOpen(!isNewTypeDropdownOpen)}
                    className="w-full h-10 px-3 bg-background/50 border border-border rounded-lg text-xs font-semibold text-foreground text-left flex justify-between items-center focus:border-primary transition-all"
                  >
                    <span className="truncate">
                      {newTypeFunctions.length === 0 ? 'Chọn chức năng' : `${newTypeFunctions.length} chức năng đã chọn`}
                    </span>
                    <ExpandMore className={`transition-transform duration-300 ${isNewTypeDropdownOpen ? 'rotate-180' : ''}`} fontSize="small" />
                  </button>
                  {isNewTypeDropdownOpen && (
                    <div className="absolute top-full left-0 w-full z-[60] mt-2 bg-[#121212] border border-border rounded-xl shadow-2xl p-1 max-h-56 overflow-y-auto animate-in fade-in slide-in-from-top-2 duration-200">
                      {SMART_FUNCTIONS.map(f => (
                        <label key={f.id} className="flex items-center gap-3 p-2.5 hover:bg-primary/10 rounded-lg cursor-pointer transition-colors group">
                          <input 
                            type="checkbox" 
                            checked={newTypeFunctions.includes(f.id)}
                            onChange={() => handleToggleTypeFunction(f.id, true)}
                            className="w-4 h-4 rounded border-border text-primary focus:ring-primary focus:ring-offset-0 bg-background"
                          />
                          <span className={`text-xs font-semibold transition-colors ${newTypeFunctions.includes(f.id) ? 'text-primary' : 'text-muted-foreground group-hover:text-foreground'}`}>
                            {f.name}
                          </span>
                        </label>
                      ))}
                    </div>
                  )}
                </div>
                <button onClick={handleAddType} className="w-[42px] h-[42px] shrink-0 bg-primary text-primary-foreground rounded-lg flex items-center justify-center shadow-lg shadow-primary/20 hover:scale-105 active:scale-95 transition-all"><Add fontSize="small"/></button>
              </div>
            </div>
            <div className="max-h-[450px] overflow-y-auto space-y-3 pr-2 scrollbar-thin">
              {camTypes.map((type, idx) => (
                <div key={type.id} id={`type-item-${idx}`} className="p-3 bg-muted/10 border-l-4 border-l-primary rounded-r-xl flex items-center justify-between group hover:bg-muted/20 transition-all shadow-sm">
                  {editTypeIndex === idx ? (
                    <div className="flex-1 space-y-2">
                       <input className="w-full h-8 px-2 bg-background border border-primary rounded text-xs" value={tempTypeName} onChange={e => setTempTypeName(e.target.value)} />
                       <div className="flex gap-2">
                        <div className="relative flex-1">
                          <button 
                            type="button" 
                            onClick={(e) => {
                                const isOpen = editTypeDropdownIndex === idx;
                                setEditTypeDropdownIndex(isOpen ? null : idx);
                                if (!isOpen) {
                                    setTimeout(() => {
                                        document.getElementById(`type-item-${idx}`)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                                    }, 100);
                                }
                            }}
                            className="w-full h-8 px-2 bg-background border border-border rounded text-[10px] font-semibold text-left flex justify-between items-center"
                          >
                            <span className="truncate">{tempTypeFunctions.length === 0 ? 'Chọn' : `${tempTypeFunctions.length} chức năng`}</span>
                            <ExpandMore fontSize="small" />
                          </button>
                          {editTypeDropdownIndex === idx && (
                            <div className="absolute top-full left-0 w-full z-[60] mt-1 bg-[#121212] border border-border rounded-lg shadow-2xl p-1 max-h-40 overflow-y-auto animate-in fade-in slide-in-from-top-2 duration-200">
                              {SMART_FUNCTIONS.map(f => (
                                <label key={f.id} className="flex items-center gap-2 p-1.5 hover:bg-muted rounded cursor-pointer transition-colors">
                                  <input type="checkbox" checked={tempTypeFunctions.includes(f.id)} onChange={() => handleToggleTypeFunction(f.id, false)} className="w-3 h-3 rounded text-primary" />
                                  <span className={`text-[10px] font-semibold ${tempTypeFunctions.includes(f.id) ? 'text-primary' : 'text-muted-foreground'}`}>{f.name}</span>
                                </label>
                              ))}
                            </div>
                          )}
                        </div>
                        <div className="flex gap-1">
                          <button onClick={() => { handleSaveEditType(idx); setEditTypeDropdownIndex(null); }} className="w-8 h-8 flex items-center justify-center bg-green-500/10 text-green-500 rounded-md hover:bg-green-500/20 transition-all"><Check sx={{ fontSize: 16 }}/></button>
                          <button onClick={() => { setEditTypeIndex(null); setEditTypeDropdownIndex(null); }} className="w-8 h-8 flex items-center justify-center bg-red-500/10 text-red-500 rounded-md hover:bg-red-500/20 transition-all"><Close sx={{ fontSize: 16 }}/></button>
                        </div>
                       </div>
                    </div>
                  ) : (
                    <div className="flex justify-between items-center w-full">
                      <div className="flex-1 min-w-0">
                        <div className="font-semibold text-sm text-foreground">{type.name}</div>
                        <div className="text-[10px] text-primary/80 font-medium mt-0.5 truncate">
                          {(type.functions || '').split(';').filter(Boolean).map(fid => SMART_FUNCTIONS.find(sf => sf.id === fid)?.name.split(' (')[0]).join(', ') || 'Mặc định'}
                        </div>
                      </div>
                      <div className="flex gap-1 ml-4 opacity-0 group-hover:opacity-100 transition-all shrink-0">
                        <button onClick={() => {setEditTypeIndex(idx); setTempTypeName(type.name); setTempTypeFunctions((type.functions || '').split(';').filter(Boolean))}} className="w-8 h-8 flex items-center justify-center bg-background border border-border rounded-md hover:text-blue-500 transition-colors"><Edit sx={{ fontSize: 16 }}/></button>
                        <button onClick={() => handleDeleteType(type.id)} className="w-8 h-8 flex items-center justify-center bg-background border border-border rounded-md hover:text-red-500 transition-colors"><Delete sx={{ fontSize: 16 }}/></button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </Dialog>

      {/* Delete Confirmation */}
      <Dialog isOpen={deleteCamId !== null} onClose={() => setDeleteCamId(null)} title="Xác nhận xóa Camera" maxWidth="sm">
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">Bạn có chắc muốn xóa camera này?</p>
          <div className="flex justify-end gap-3"><button onClick={() => setDeleteCamId(null)} className="px-4 py-2 text-sm text-muted-foreground">Hủy</button><button onClick={executeDeleteCamera} className="px-4 py-2 bg-red-500 text-white rounded text-sm font-bold">Xóa vĩnh viễn</button></div>
        </div>
      </Dialog>

      <Dialog isOpen={deleteLocId !== null} onClose={() => setDeleteLocId(null)} title="Xác nhận xóa Vị trí" maxWidth="sm">
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">Xóa vị trí này có thể ảnh hưởng đến các camera đang lắp đặt tại đây.</p>
          <div className="flex justify-end gap-3"><button onClick={() => setDeleteLocId(null)} className="px-4 py-2 text-sm text-muted-foreground">Hủy</button><button onClick={executeDeleteLocation} className="px-4 py-2 bg-red-500 text-white rounded text-sm font-bold">Xóa vị trí</button></div>
        </div>
      </Dialog>
    </div>
  )
}
