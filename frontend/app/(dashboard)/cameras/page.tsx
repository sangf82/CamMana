'use client'

import React, { useState, useEffect } from 'react'
import { Add, Edit, Delete, Settings, ExpandMore, Check, Close, Warning } from '@mui/icons-material'
import DataTable from '../../../components/ui/data-table'
import Dialog from '../../../components/ui/dialog'
import { toast } from 'sonner'

// --- Types ---
// --- Types ---
interface LocationItem {
    id: string | number
    name: string
}

interface TypeItem {
    id: string | number
    name: string
}

interface Camera {
  id: number
  name: string
  ip: string
  location: string
  status: 'Online' | 'Offline' | 'Connected' | 'Local'
  type: string
  username?: string
  password?: string
  brand?: string
  cam_id?: string
}

const DEFAULT_TYPES_NAMES = [
    'Nhận diện xe & biển số',
    'Nhận diện màu & số bánh',
    'Tính toán trọng lượng & khối lượng'
]

export default function CamerasPage() {
  const [data, setData] = useState<Camera[]>([])
  const [locations, setLocations] = useState<LocationItem[]>([])
  const [camTypes, setCamTypes] = useState<TypeItem[]>([])
  
  // Dialog States
  const [isCamDialogOpen, setIsCamDialogOpen] = useState(false)
  const [isConfigDialogOpen, setIsConfigDialogOpen] = useState(false)
  const [editingItem, setEditingItem] = useState<Camera | null>(null)
  
  // Delete confirm states
  const [deleteCamId, setDeleteCamId] = useState<number | null>(null)
  const [deleteLocId, setDeleteLocId] = useState<string | number | null>(null) // Use ID for location
  const [deleteLocName, setDeleteLocName] = useState<string>('') // For display only

  // New Input States
  const [newLocation, setNewLocation] = useState('')
  // For editing location
  const [editLocIndex, setEditLocIndex] = useState<number | null>(null)
  const [tempLocName, setTempLocName] = useState('')
  const [isLocInputFocused, setIsLocInputFocused] = useState(false)

  // --- 1. Load Data from API ---
  const fetchInitialData = async () => {
    try {
        const [locRes, typeRes, camRes] = await Promise.all([
            fetch('/api/cameras/locations'),
            fetch('/api/cameras/types'),
            fetch('/api/cameras/saved')
        ])

        if (locRes.ok) setLocations(await locRes.json())
        if (typeRes.ok) setCamTypes(await typeRes.json())
        if (camRes.ok) setData(await camRes.json())
    } catch (error) {
        console.error("Failed to load initial data", error)
    }
  }

  useEffect(() => {
    fetchInitialData()
  }, [])

  // --- 2. API Operations ---
  
  // --- 2. API Operations ---
  
  const updateLocations = async (updatedLocs: LocationItem[]) => {
      setLocations(updatedLocs) // Optimistic update
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
  }

  const updateTypes = async (updatedTypes: TypeItem[]) => {
      setCamTypes(updatedTypes) // Optimistic update
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

  // --- CRUD Handlers (Cameras) ---
  const handleEdit = async (item: Camera) => {
    // Ensure locations are up-to-date before opening
    const res = await fetch('/api/cameras/locations')
    if(res.ok) setLocations(await res.json())
    
    setEditingItem(item)
    setIsCamDialogOpen(true)
  }

  const handleDelete = (id: number) => {
    setDeleteCamId(id)
  }

  const executeDeleteCamera = () => {
    if (deleteCamId !== null) {
        const id = deleteCamId
        // Optimistic
        setData(prev => prev.filter(item => item.id !== id))
        
        const promise = fetch(`/api/cameras/${id}`, { method: 'DELETE' })
        
        toast.promise(promise, {
            loading: 'Đang xóa camera...',
            success: 'Đã xóa camera thành công',
            error: (err) => {
                fetchInitialData() // Revert
                return 'Lỗi khi xóa camera'
            }
        })
        setDeleteCamId(null)
    }
  }

  const handleSaveCamera = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editingItem) return

    const isNew = !editingItem.id
    const camToSave = { 
        ...editingItem, 
        id: isNew ? Date.now() : editingItem.id // Temp ID for new, backend uses UUID or keeps generic ID
    }

    // Optimistic Update
    if (isNew) {
        setData(prev => [camToSave, ...prev])
    } else {
        setData(prev => prev.map(item => item.id === camToSave.id ? camToSave : item))
    }
    
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
        error: (err) => {
             fetchInitialData()
            return 'Lỗi khi lưu camera'
        }
    })
    
    try {
        const res = await promise
        if (res.ok) {
             fetchInitialData()
        }
    } catch (e) {
        console.error("Save failed", e)
    }
  }

  const openAddDialog = async () => {
    // Ensure locations are up-to-date before opening
    const res = await fetch('/api/cameras/locations')
    if(res.ok) setLocations(await res.json())

    setEditingItem({ id: 0, name: '', ip: '', location: locations[0]?.name || '', status: 'Offline', type: camTypes[0]?.name || '', username: '', password: '', brand: '', cam_id: '' })
    setIsCamDialogOpen(true)
  }

  // --- CRUD Handlers (Locations & Types) ---
  // --- CRUD Handlers (Locations & Types) ---
  const handleAddLocation = () => {
      if (newLocation && !locations.some(l => l.name === newLocation)) {
          // Add new with temp ID (or no ID)
          updateLocations([...locations, { id: Date.now().toString(), name: newLocation }])
          setNewLocation('')
      }
  }

  const handleDeleteLocation = (id: string | number, name: string) => {
      setDeleteLocId(id)
      setDeleteLocName(name)
  }

  const executeDeleteLocation = () => {
      if (deleteLocId !== null) {
          updateLocations(locations.filter(l => l.id !== deleteLocId))
          setDeleteLocId(null)
          setDeleteLocName('')
      }
  }

  const handleStartEditLocation = (index: number, currentName: string) => {
    setEditLocIndex(index)
    setTempLocName(currentName)
  }

  const handleSaveEditLocation = (index: number) => {
    if (tempLocName && !locations.some((l, i) => i !== index && l.name === tempLocName)) {
        const updated = [...locations]
        updated[index] = { ...updated[index], name: tempLocName }
        updateLocations(updated)
        setEditLocIndex(null)
        setTempLocName('')
    } else if (tempLocName === locations[index].name) {
        setEditLocIndex(null) // No change
    } else {
        toast.error('Tên vị trí không hợp lệ hoặc đã tồn tại!')
    }
  }

  const handleToggleType = (name: string) => {
    const exists = camTypes.find(t => t.name === name)
    if (exists) {
        // Remove
        updateTypes(camTypes.filter(type => type.id !== exists.id))
    } else {
        // Add
        updateTypes([...camTypes, { id: Date.now().toString(), name: name }])
    }
  }


  // Columns Configuration
  const columns = [
    { 
      header: 'Trạng thái', 
      width: '100px',
      render: (row: Camera) => {
        let colorClass = 'bg-gray-500/10 text-gray-500'
        let dotClass = 'bg-gray-500'
        let text = row.status

        if (row.status === 'Online') {
            colorClass = 'bg-green-500/10 text-green-500'
            dotClass = 'bg-green-500 animate-pulse'
        } else if (row.status === 'Connected') {
            colorClass = 'bg-blue-500/10 text-blue-500'
            dotClass = 'bg-blue-500'
        } else if (row.status === 'Local') {
             colorClass = 'bg-yellow-500/10 text-yellow-500'
             dotClass = 'bg-yellow-500'
        } else {
             colorClass = 'bg-red-500/10 text-red-500'
             dotClass = 'bg-red-500'
        }

        return (
            <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${colorClass}`}>
               <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${dotClass}`} />
               {text}
            </span>
        )
      }
    },

    { header: 'Mã Camera', accessorKey: 'cam_id' as keyof Camera },
    { header: 'Thương hiệu', accessorKey: 'brand' as keyof Camera },
    { header: 'Tên Camera', accessorKey: 'name' as keyof Camera },
    { header: 'IP Address', accessorKey: 'ip' as keyof Camera },
    { header: 'Vị trí', accessorKey: 'location' as keyof Camera },
    { header: 'Loại', accessorKey: 'type' as keyof Camera },
    { 
      header: 'Thao tác', 
      width: '120px',
      render: (row: Camera) => (
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

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Danh sách Camera</h1>
        
        <div className="flex gap-3">
            {/* Configuration Button */}
            <button 
                onClick={() => setIsConfigDialogOpen(true)}
                className="bg-secondary hover:bg-muted text-secondary-foreground border border-border px-4 py-2 rounded-md font-medium flex items-center gap-2 transition-colors"
            >
                <Settings fontSize="small" /> Cấu hình
            </button>

            {/* Add Camera Button */}
            <button 
            onClick={openAddDialog}
            className="bg-primary hover:bg-primary/90 text-primary-foreground px-4 py-2 rounded-md font-medium flex items-center gap-2 transition-colors"
            >
            <Add /> Thêm Camera
            </button>
        </div>
      </div>

      {/* Main Table */}
      <DataTable 
        columns={columns} 
        data={data} 
      />

      {/* --- ADD/EDIT CAMERA DIALOG --- */}
      <Dialog 
        isOpen={isCamDialogOpen} 
        onClose={() => setIsCamDialogOpen(false)} 
        title={editingItem?.id ? 'Cấu hình Camera' : 'Thêm Camera mới'}
        maxWidth="sm"
      >
        <form onSubmit={handleSaveCamera} className="space-y-4" autoComplete="off">
           <input autoComplete="false" name="hidden" type="text" style={{display: 'none'}} />

           <div className="space-y-2">
             <label className="text-sm font-medium text-muted-foreground">Tên Camera <span className="text-red-500">*</span></label>
             <input 
               className="w-full p-2 bg-background border border-border rounded focus:border-primary focus:ring-0 outline-none"
               value={editingItem?.name || ''}
               onChange={e => setEditingItem(prev => ({ ...prev!, name: e.target.value }))}
               required
               autoComplete="off"
               placeholder="Camera Cổng Chính"
             />
           </div>

           <div className="space-y-2">
             <label className="text-sm font-medium text-muted-foreground">Thương hiệu <span className="text-red-500">*</span></label>
             <input 
               className="w-full p-2 bg-background border border-border rounded focus:border-primary focus:ring-0 outline-none"
               value={editingItem?.brand || ''}
               onChange={e => setEditingItem(prev => ({ ...prev!, brand: e.target.value }))}
               required
               placeholder="Hikvision/Dahua"
               autoComplete="off"
             />
           </div>
           
           <div className="space-y-2">
             <label className="text-sm font-medium text-muted-foreground">Địa chỉ IP <span className="text-red-500">*</span></label>
             <input 
               className="w-full p-2 bg-background border border-border rounded focus:border-primary focus:ring-0 outline-none"
               value={editingItem?.ip || ''}
               onChange={e => setEditingItem(prev => ({ ...prev!, ip: e.target.value }))}
               required
               autoComplete="off"
             />
           </div>

           <div className="space-y-2">
             <label className="text-sm font-medium text-muted-foreground">Tài khoản (Username)</label>
             <input 
                className="w-full p-2 bg-background border border-border rounded focus:border-primary focus:ring-0 outline-none"
                value={editingItem?.username || ''}
                onChange={e => setEditingItem(prev => ({ ...prev!, username: e.target.value }))}
                autoComplete="new-password" 
                name="camera_username"
             />
           </div>

           <div className="space-y-2">
             <label className="text-sm font-medium text-muted-foreground">Mật khẩu (Password)</label>
             <input 
                type="password"
                className="w-full p-2 bg-background border border-border rounded focus:border-primary focus:ring-0 outline-none"
                value={editingItem?.password || ''}
                onChange={e => setEditingItem(prev => ({ ...prev!, password: e.target.value }))}
                autoComplete="new-password"
                name="camera_password"
             />
           </div>

           <div className="space-y-2">
             <label className="text-sm font-medium text-muted-foreground">Vị trí lắp đặt <span className="text-red-500">*</span></label>
             <div className="relative">
                 <select 
                   className="w-full p-2 pr-10 bg-background border border-border rounded focus:border-primary focus:ring-0 outline-none appearance-none"
                   value={editingItem?.location || ''}
                   onChange={e => setEditingItem(prev => ({ ...prev!, location: e.target.value }))}
                   required
                 >
                    {locations.map(loc => (
                        <option key={loc.id} value={loc.name}>{loc.name}</option>
                    ))}
                 </select>
                 <div className="absolute inset-y-0 right-4 flex items-center pointer-events-none text-muted-foreground">
                    <ExpandMore fontSize="small" />
                 </div>
             </div>
           </div>

           <div className="space-y-2">
             <label className="text-sm font-medium text-muted-foreground">Loại Camera <span className="text-red-500">*</span></label>
              <div className="relative">
                  <select 
                      className="w-full p-2 pr-10 bg-background border border-border rounded focus:border-primary focus:ring-0 outline-none appearance-none"
                      value={editingItem?.type || ''}
                      onChange={e => setEditingItem(prev => ({ ...prev!, type: e.target.value }))}
                      required
                    >
                       {camTypes.map(t => (
                           <option key={t.id} value={t.name}>{t.name}</option>
                       ))}
                    </select>
                    <div className="absolute inset-y-0 right-4 flex items-center pointer-events-none text-muted-foreground">
                        <ExpandMore fontSize="small" />
                    </div>
              </div>
           </div>

           <div className="flex justify-end gap-3 pt-4 border-t border-border mt-4">
             <button 
               type="button"
               onClick={() => setIsCamDialogOpen(false)}
               className="px-4 py-2 text-sm font-medium text-muted-foreground hover:bg-muted rounded transition-colors"
             >
               Hủy bỏ
             </button>
             <button 
               type="submit"
               className="px-4 py-2 text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 rounded transition-colors"
             >
               Lưu cấu hình
             </button>
          </div>
        </form>
      </Dialog>

      {/* --- CONFIGURATION DIALOG --- */}
      <Dialog
         isOpen={isConfigDialogOpen}
         onClose={() => setIsConfigDialogOpen(false)}
         title="Cấu hình Hệ thống"
         maxWidth="3xl"
      >
          <div className="grid grid-cols-2 gap-8 p-1">
              {/* Left Column: Locations */}
              <div className="space-y-4">
                  <h3 className="font-semibold text-lg flex items-center gap-2 border-b border-border pb-2 text-primary">
                      Vị trí (Location)
                  </h3>
                  
                  {/* Add Input Group */}
                  {/* Add Input Group */}
                  <div className="flex items-center gap-2">
                      <input 
                         className="flex-1 px-3 py-2 bg-background border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary text-sm placeholder:text-muted-foreground h-10 w-full"
                         placeholder="Tên vị trí mới..."
                         value={newLocation}
                         onChange={(e) => setNewLocation(e.target.value)}
                      />
                      <button 
                        onClick={handleAddLocation}
                        className="h-8 w-8 flex items-center justify-center bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors shadow-sm shrink-0"
                        title="Thêm vị trí"
                      >
                          <Add fontSize="small" />
                      </button>
                  </div>

                  {/* List Container */}
                  <div className="bg-muted/30 rounded-lg p-2 max-h-[400px] overflow-y-auto space-y-2">
                      {locations.length === 0 && <div className="p-4 text-center text-muted-foreground text-sm italic">Chưa có vị trí nào</div>}
                      {locations.map((loc, idx) => (
                          <div key={loc.id || idx} className="flex items-center justify-between p-3 bg-card border border-border/50 rounded-md shadow-sm hover:shadow-md transition-all group min-h-[50px]">
                              {editLocIndex === idx ? (
                                  <div className="flex items-center gap-2 flex-1 animate-in fade-in zoom-in-95 duration-200">
                                      <input 
                                          className="flex-1 p-1 bg-background border border-primary rounded focus:outline-none text-sm"
                                          value={tempLocName}
                                          onChange={e => setTempLocName(e.target.value)}
                                          autoFocus
                                      />
                                      <button onClick={() => handleSaveEditLocation(idx)} className="text-green-500 hover:bg-green-500/10 p-1 rounded"><Check fontSize="small"/></button>
                                      <button onClick={() => setEditLocIndex(null)} className="text-red-500 hover:bg-red-500/10 p-1 rounded"><Close fontSize="small"/></button>
                                  </div>
                              ) : (
                                  <>
                                    <span className="font-medium">{loc.name}</span>
                                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <button 
                                            onClick={() => handleStartEditLocation(idx, loc.name)}
                                            className="text-muted-foreground hover:text-blue-500 p-1 rounded transition-colors"
                                            title="Sửa"
                                        >
                                            <Edit fontSize="small" />
                                        </button>
                                        <button 
                                            onClick={() => handleDeleteLocation(loc.id, loc.name)}
                                            className="text-muted-foreground hover:text-red-500 p-1 rounded transition-colors"
                                            title="Xóa"
                                        >
                                            <Delete fontSize="small" />
                                        </button>
                                    </div>
                                  </>
                              )}
                          </div>
                      ))}
                  </div>
              </div>

              {/* Right Column: Camera Types */}
              <div className="space-y-4">
                  <h3 className="font-semibold text-lg flex items-center gap-2 border-b border-border pb-2 text-primary">
                      Loại Camera (Types)
                  </h3>
                  
                   {/* List Container - Toggles */}
                  <div className="bg-muted/30 rounded-lg p-2 space-y-2">
                      {DEFAULT_TYPES_NAMES.map(t => {
                          const isActive = camTypes.some(type => type.name === t)
                          return (
                            <div key={t} className="flex items-center justify-between p-3 bg-card border border-border/50 rounded-md shadow-sm hover:shadow-md transition-all cursor-pointer" onClick={() => handleToggleType(t)}>
                                <span className={`font-medium ${isActive ? 'text-foreground' : 'text-muted-foreground'}`}>{t}</span>
                                
                                <div className={`w-11 h-6 flex items-center rounded-full p-1 transition-colors duration-300 ${isActive ? 'bg-primary' : 'bg-muted-foreground/30'}`}>
                                    <div className={`bg-white w-4 h-4 rounded-full shadow-md transform transition-transform duration-300 ${isActive ? 'translate-x-5' : 'translate-x-0'}`}></div>
                                </div>
                            </div>
                          )
                      })}
                  </div>
              </div>
          </div>
      </Dialog>
      
      {/* --- DELETE CAMERA CONFIRMATION --- */}
      <Dialog 
        isOpen={!!deleteCamId} 
        onClose={() => setDeleteCamId(null)} 
        title="Xác nhận xóa Camera"
        maxWidth="sm"
      >
        <div className="space-y-4">
          <p className="text-muted-foreground">
            Bạn có chắc chắn muốn xóa camera này khỏi danh sách?
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
              onClick={() => setDeleteCamId(null)}
              className="px-4 py-2 text-sm font-medium text-muted-foreground hover:bg-muted rounded transition-colors"
            >
              Hủy bỏ
            </button>
            <button 
              onClick={executeDeleteCamera}
              className="px-4 py-2 text-sm font-bold bg-red-500 text-white hover:bg-red-600 rounded shadow-lg shadow-red-500/20 transition-all"
            >
              Xóa Camera
            </button>
          </div>
        </div>
      </Dialog>

      {/* --- DELETE LOCATION CONFIRMATION --- */}
      <Dialog 
        isOpen={deleteLocId !== null} 
        onClose={() => { setDeleteLocId(null); setDeleteLocName(''); }} 
        title="Xác nhận xóa Vị trí"
        maxWidth="sm"
      >
        <div className="space-y-4">
          <p className="text-muted-foreground">
            Bạn có chắc chắn muốn xóa vị trí <strong>"{deleteLocName}"</strong> khỏi danh sách?
          </p>
          
          <div className="bg-red-500/10 border border-red-500/20 rounded-md p-3 flex items-start gap-3">
             <Warning className="text-red-500 shrink-0 mt-0.5" fontSize="small" />
             <div className="text-xs text-red-500">
                <span className="font-bold block mb-0.5">Cảnh báo</span>
                Hành động này sẽ xóa vĩnh viễn cấu hình này.
             </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-border mt-2">
            <button 
              onClick={() => { setDeleteLocId(null); setDeleteLocName(''); }}
              className="px-4 py-2 text-sm font-medium text-muted-foreground hover:bg-muted rounded transition-colors"
            >
              Hủy bỏ
            </button>
            <button 
              onClick={executeDeleteLocation}
              className="px-4 py-2 text-sm font-bold bg-red-500 text-white hover:bg-red-600 rounded shadow-lg shadow-red-500/20 transition-all"
            >
              Xóa Vị trí
            </button>
          </div>
        </div>
      </Dialog>
    </div>
  )
}
