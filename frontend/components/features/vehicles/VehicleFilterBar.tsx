import { useState, useEffect } from 'react'
import { Add, Search, Download, ChevronLeft, ExpandMore } from '@mui/icons-material'

interface VehicleFilterBarProps {
  searchTerm: string
  setSearchTerm: (val: string) => void
  filterContractor: string
  setFilterContractor: (val: string) => void
  filterType: string
  setFilterType: (val: string) => void
  contractors: string[]
  vehicleTypes: string[]
  onAdd: () => void
  onExport: () => void
}

export default function VehicleFilterBar({
  searchTerm,
  setSearchTerm,
  filterContractor,
  setFilterContractor,
  filterType,
  setFilterType,
  contractors,
  vehicleTypes,
  onAdd,
  onExport
}: VehicleFilterBarProps) {
  const [showFilters, setShowFilters] = useState(false)
  const [isContractorOpen, setIsContractorOpen] = useState(false)
  const [isTypeOpen, setIsTypeOpen] = useState(false)
  
  // Pending states
  const [pendingFilterContractor, setPendingFilterContractor] = useState(filterContractor)
  const [pendingFilterType, setPendingFilterType] = useState(filterType)

  const handleApply = () => {
    setFilterContractor(pendingFilterContractor)
    setFilterType(pendingFilterType)
  }

  const handleClear = () => {
    setFilterContractor('All')
    setPendingFilterContractor('All')
    setFilterType('All')
    setPendingFilterType('All')
    setSearchTerm('')
  }
  
  // Sync if externally changed (optional, but good practice if needed)
  useEffect(() => {
    if (showFilters) {
         setPendingFilterContractor(filterContractor)
         setPendingFilterType(filterType)
    }
  }, [showFilters, filterContractor, filterType])

  return (
    <>
    <div className="flex justify-between items-center shrink-0">
        <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight">Danh sách xe đăng ký</h1>
            <span className="text-[#f59e0b] font-mono bg-[#f59e0b]/10 px-2 py-0.5 rounded text-sm border border-[#f59e0b]/20">
              {new Date().toLocaleDateString("vi-VN", {
                day: "2-digit",
                month: "2-digit",
                year: "numeric",
              })}
            </span>
        </div>

        <div className="flex items-center gap-3">
            {/* Search Bar */}
            <div className="relative group min-w-[300px]">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-[#f59e0b] transition-colors" fontSize="small" />
                <input 
                    type="text"
                    placeholder="Tìm kiếm biển số, loại xe..."
                    className="w-full pl-10 pr-4 py-2 bg-card border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-[#f59e0b] focus:border-[#f59e0b] transition-all text-sm"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                />
            </div>

            <button 
                onClick={() => setShowFilters(!showFilters)}
                className={`pl-3 pr-1 py-1.5 border rounded-md text-sm font-bold flex items-center gap-1 transition-all shadow-sm
                    ${showFilters || filterContractor !== 'All' || filterType !== 'All'
                        ? 'bg-[#f59e0b] text-black border-[#f59e0b] shadow-[#f59e0b]/20' 
                        : 'bg-card border-border text-foreground hover:bg-muted'}`}
            >
              Lọc
              <div className={`transition-transform duration-200 ${showFilters ? '-rotate-90' : ''}`}>
                <ChevronLeft fontSize="small" />
              </div>
            </button>
            
            <button 
              onClick={onAdd}
              className="bg-[#f59e0b] hover:bg-[#f59e0b]/90 text-black px-4 py-1.5 rounded-md text-sm font-bold flex items-center gap-2 transition-all shadow-lg shadow-[#f59e0b]/20 active:scale-95"
            >
              <Add fontSize="small" /> Thêm xe mới
            </button>

            <button 
              onClick={onExport}
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
                      className="w-full flex items-center justify-between min-w-[200px] px-3 py-1.5 bg-background border border-border rounded-md text-sm font-semibold focus:border-[#f59e0b] transition-all"
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
                                  className={`w-full text-left px-3 py-2 rounded-lg text-xs font-medium transition-colors hover:bg-[#f59e0b]/10 ${pendingFilterContractor === c ? 'text-[#f59e0b] bg-[#f59e0b]/10' : 'text-muted-foreground'}`}
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
                      className="w-full flex items-center justify-between min-w-[200px] px-3 py-1.5 bg-background border border-border rounded-md text-sm font-semibold focus:border-[#f59e0b] transition-all"
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
                                  className={`w-full text-left px-3 py-2 rounded-lg text-xs font-medium transition-colors hover:bg-[#f59e0b]/10 ${pendingFilterType === v ? 'text-[#f59e0b] bg-[#f59e0b]/10' : 'text-muted-foreground'}`}
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
                      onClick={handleClear}
                      className="text-xs text-red-400 hover:text-red-300 font-bold px-2 py-1 transition-colors"
                  >
                      Xóa lọc
                  </button>
              )}
              <button 
                  onClick={handleApply}
                  className="px-6 py-1.5 bg-[#f59e0b] text-black text-sm font-bold rounded-md hover:bg-[#f59e0b]/90 transition-all shadow-lg shadow-[#f59e0b]/20 active:scale-95"
              >
                  Áp dụng
              </button>
          </div>
      </div>
    )}
    </>
  )
}
