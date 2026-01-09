import { ArrowDownward, ArrowUpward, HourglassEmpty, Refresh, FileUpload } from '@mui/icons-material'
import { useRef } from 'react'

export default function ScheduleDashboard({ schedule, verificationResult, onReload, onImport }) {
  const fileInputRef = useRef(null)

  if (!schedule) return <div className="loading" style={{padding:'20px', color:'var(--text-secondary)'}}>Đang tải dữ liệu...</div>

  const handleFileChange = (e) => {
    const file = e.target.files[0]
    if (file && onImport) {
        onImport(file)
    }
    // reset
    e.target.value = null
  }

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <div style={{display:'flex', alignItems:'center', gap:'20px'}}>
            <h2>Bảng Lịch Trình Xe</h2>
            <div className="action-btns" style={{display:'flex', gap:'10px'}}>
                <button 
                    className="btn btn-secondary" 
                    onClick={onReload}
                    title="Tải lại dữ liệu"
                    style={{padding:'6px 12px'}}
                >
                    <Refresh fontSize="small" /> Tải lại
                </button>
                <button 
                    className="btn btn-primary"
                    onClick={() => fileInputRef.current?.click()}
                    title="Nhập file Excel mới"
                    style={{padding:'6px 12px'}}
                >
                    <FileUpload fontSize="small" /> Nhập Excel
                </button>
                <input 
                    type="file" 
                    accept=".xlsx, .xls"
                    ref={fileInputRef}
                    style={{display:'none'}}
                    onChange={handleFileChange}
                />
            </div>
        </div>
        <div className="stats-row">
            <div className="stat-card">
              <span className="stat-label">Tổng xe dự kiến</span>
              <span className="stat-value">{schedule.length}</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Đã vào bãi</span>
              <span className="stat-value">
                {schedule.filter(r => r.verified).length}
              </span>
            </div>
        </div>
      </div>

      <div className="table-container">
        <table className="schedule-table">
          <thead>
            <tr>
              <th>STT</th>
              <th>Giờ vào</th>
              <th>Biển số</th>
              <th>Loại xe</th>
              <th>Kích thước</th>
              <th>Thể tích</th>
              <th>Hợp lệ?</th>
              <th>Tình trạng</th>
              <th>Ghi chú</th>
            </tr>
          </thead>
          <tbody>
            {schedule.map((row, index) => {
              // Check if matching
              const isMatch = verificationResult?.matchedRow?.stt === row.stt;
              const rowClass = isMatch ? 'highlight-match' : (row.verified ? 'verified-row' : '');
              
              // Status Badge Logic
              const status = row.displayStatus || 'Chưa đến';
              let statusColor = 'var(--text-muted)';
              let statusText = status;
              let StatusIcon = HourglassEmpty;
              
              // Minimal status indicator color
              let dotColor = 'var(--text-muted)';

              if (status === 'Đã vào') {
                  statusColor = 'var(--success)';
                  dotColor = 'var(--success)';
                  StatusIcon = ArrowDownward;
              } else if (status === 'Đã ra') {
                  statusColor = 'var(--accent)';
                  dotColor = 'var(--accent)';
                  StatusIcon = ArrowUpward;
              }

              return (
                <tr key={index} className={rowClass}>
                  <td>{row.stt}</td>
                  <td>{row.time_in}</td>
                  <td>
                    <span className="plate-badge">{row.plate}</span>
                  </td>
                  <td>{row.vehicle_type}</td>
                  <td className="dim-cell">{row.dimensions}</td>
                  <td>{row.volume}</td>
                  
                  {/* Validity Status from Excel */}
                  <td>
                    <span className={`status-pill ${row.status_validity === 'Hợp lệ' ? 'valid' : 'warning'}`}>
                      {row.status_validity || 'N/A'}
                    </span>
                  </td>

                  {/* Vehicle Movement Status (Dynamic) */}
                   <td>
                    <span className="status-cell" style={{color: statusColor}}>
                      <StatusIcon fontSize="small" style={{ fontSize: '1rem' }} />
                      {statusText}
                    </span>
                  </td>

                  <td>{row.notes}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      
      <style jsx>{`
        .dashboard-container {
          padding: 24px;
          background: var(--bg-secondary);
          border-radius: 12px;
          height: 100%;
          overflow: hidden;
          display: flex;
          flex-direction: column;
          color: var(--text-primary);
        }

        .dashboard-header {
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        h2 {
            margin: 0;
            font-size: 1.5rem;
            color: var(--text-primary);
        }

        .stats-row {
            display: flex;
            gap: 20px;
        }

        .stat-card {
            background: var(--bg-primary);
            padding: 10px 20px;
            border-radius: 8px;
            border: 1px solid var(--border);
            text-align: center;
        }
        
        .stat-label {
            display: block;
            font-size: 0.8rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }
        
        .stat-value {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--accent);
        }

        .table-container {
          flex: 1;
          overflow-y: auto;
          background: var(--bg-primary);
          border-radius: 8px;
          border: 1px solid var(--border);
        }

        .schedule-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.9rem;
        }

        .schedule-table th {
          text-align: left;
          padding: 12px 16px;
          background: var(--bg-tertiary);
          color: var(--text-secondary);
          font-weight: 600;
          position: sticky;
          top: 0;
          z-index: 10;
          border-bottom: 1px solid var(--border);
        }

        .schedule-table td {
          padding: 12px 16px;
          border-bottom: 1px solid var(--border);
          color: var(--text-primary);
        }

        .schedule-table tr:hover {
          background: var(--bg-secondary);
        }

        .plate-badge {
          font-family: 'Consolas', monospace;
          background: var(--accent-dim);
          color: var(--accent);
          padding: 4px 8px;
          border-radius: 6px;
          font-weight: 700;
          border: 1px solid var(--accent);
          display: inline-block;
        }

        .status-pill {
          padding: 4px 10px;
          border-radius: 20px;
          font-size: 0.75rem;
          font-weight: 600;
        }
        
        .status-pill.valid {
          background: rgba(34, 197, 94, 0.1); /* Green-500 alpha */
          color: var(--success);
          border: 1px solid var(--success);
        }
        
        .status-pill.warning {
          background: var(--accent-dim);
          color: var(--accent);
          border: 1px solid var(--accent);
        }

        .status-cell {
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 600;
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            display: inline-block;
        }

        .dim-cell {
            font-family: monospace;
            opacity: 0.8;
            color: var(--text-secondary);
        }
        
        .highlight-match {
            background: rgba(34, 197, 94, 0.15) !important; /* Green tint */
        }
        
        /* Specific border/highlight for match */
        .highlight-match td:first-child {
            border-left: 4px solid var(--success);
        }

        .verified-row {
            background: var(--bg-tertiary);
        }
        
        .verified-row td:first-child {
             border-left: 4px solid var(--text-secondary);
        }
      `}</style>
    </div>
  )
}
