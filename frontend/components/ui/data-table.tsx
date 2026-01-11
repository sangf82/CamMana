'use client'

import React from 'react'

interface Column<T> {
  header: string | (() => React.ReactNode)
  accessorKey?: keyof T
  render?: (row: T) => React.ReactNode
  width?: string
}

interface DataTableProps<T> {
  columns: Column<T>[]
  data: T[]
  onRowClick?: (row: T) => void
  emptyMessage?: string
}

export default function DataTable<T>({ 
  columns, 
  data, 
  onRowClick, 
  emptyMessage = 'Không có dữ liệu' 
}: DataTableProps<T>) {
  return (
    <div className="w-full overflow-hidden rounded-lg border border-border bg-card">
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="text-xs uppercase bg-muted text-muted-foreground font-mono">
            <tr>
              {columns.map((col, idx) => (
                <th key={idx} scope="col" className="px-4 py-3 font-medium whitespace-nowrap" style={{ width: col.width }}>
                  {typeof col.header === 'function' ? col.header() : col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {data.length > 0 ? (
              data.map((row, rowIdx) => (
                <tr 
                  key={rowIdx} 
                  className={`bg-card hover:bg-muted/50 transition-colors ${onRowClick ? 'cursor-pointer' : ''}`}
                  onClick={() => onRowClick?.(row)}
                >
                  {columns.map((col, colIdx) => (
                    <td key={colIdx} className="px-4 py-3 whitespace-nowrap text-foreground">
                      {col.render ? col.render(row) : (row[col.accessorKey!] as React.ReactNode)}
                    </td>
                  ))}
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={columns.length} className="px-4 py-8 text-center text-muted-foreground">
                  {emptyMessage}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
