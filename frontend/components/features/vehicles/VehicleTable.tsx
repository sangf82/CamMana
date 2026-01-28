import { Pencil, Trash } from 'lucide-react'
import { Button } from "@/components/ui/button"

export interface Vehicle {
  id: number | string
  plate: string
  truckModel: string          
  color: string               
  axles: string               
  standardVolume: string      
  contractor: string
  registrationDate: string
  lastModified: string
}

interface VehicleTableProps {
  data: Vehicle[]
  loading?: boolean
  onEdit: (item: Vehicle) => void
  onDelete: (id: number | string) => void
}

export default function VehicleTable({ data, loading, onEdit, onDelete }: VehicleTableProps) {
  const columns = [
    { header: 'Biển số', accessorKey: 'plate', width: '120px' },
    { header: 'Loại xe', accessorKey: 'truckModel', width: '150px' },
    { header: 'Màu xe', accessorKey: 'color', width: '100px' },
    { header: 'Số bánh', accessorKey: 'axles', width: '130px' },
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
          <Button
            onClick={(e) => { e.stopPropagation(); onEdit(row) }}
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-amber-500 hover:text-amber-600 hover:bg-amber-500/10"
          >
            <Pencil className="w-4 h-4" />
          </Button>
          <Button
             onClick={(e) => { e.stopPropagation(); onDelete(row.id) }}
             variant="ghost"
             size="icon"
             className="h-7 w-7 text-destructive hover:text-destructive hover:bg-destructive/10"
          >
            <Trash className="w-4 h-4" />
          </Button>
        </div>
      )
    }
  ]

  return (
    <div className="border border-border rounded-lg bg-card overflow-hidden flex-1 flex flex-col min-h-0">
      <div className="flex-1 overflow-y-scroll overflow-x-auto scrollbar-show-always min-h-0">
        <table className="text-sm text-left border-collapse table-fixed w-fit min-w-full">
          <thead className="text-[10px] uppercase text-muted-foreground font-bold font-mono sticky top-0 bg-muted/90 backdrop-blur-md z-20 border-b border-border">
            <tr>
              {columns.map((col, idx) => (
                <th key={idx} className="px-4 py-3 whitespace-nowrap" style={{ width: col.width || 'auto' }}>
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {loading ? (
                <tr>
                  <td colSpan={columns.length} className="px-4 py-12 text-center text-muted-foreground font-medium">
                    Đang tải dữ liệu...
                  </td>
                </tr>
            ) : data.length > 0 ? (
              data.map((row, rowIdx) => (
                <tr 
                  key={rowIdx} 
                  className="bg-card hover:bg-muted/5 transition-colors group"
                >
                  {columns.map((col, colIdx) => (
                    <td key={colIdx} className="px-4 py-2.5 whitespace-nowrap text-foreground font-medium text-xs truncate" style={{ width: col.width || 'auto' }}>
                      {/* @ts-ignore */}
                      {col.render ? col.render(row) : row[col.accessorKey]}
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
  )
}
