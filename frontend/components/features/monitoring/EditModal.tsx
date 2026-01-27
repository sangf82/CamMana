import React from "react";
import { Close } from "@mui/icons-material";

interface EditModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: () => void;
  editPlate: string;
  setEditPlate: (value: string) => void;
  editStatus: string;
  setEditStatus: (value: string) => void;
  editVerify: string;
  setEditVerify: (value: string) => void;
  editNote: string;
  setEditNote: (value: string) => void;
  editVolume: string;
  setEditVolume: (value: string) => void;
  isVolumeEnabled?: boolean;
}

export default function EditModal({
  isOpen,
  onClose,
  onSave,
  editPlate,
  setEditPlate,
  editStatus,
  setEditStatus,
  editVerify,
  setEditVerify,
  editNote,
  setEditNote,
  editVolume,
  setEditVolume,
  isVolumeEnabled = true,
}: EditModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[9999] pointer-events-auto">
      <div className="bg-card border border-border rounded-lg p-6 w-96 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-lg">Sửa thông tin xe</h3>
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground"
          >
            <Close />
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-xs text-muted-foreground uppercase tracking-wider">
              Biển số
            </label>
            <input
              type="text"
              value={editPlate}
              onChange={(e) => setEditPlate(e.target.value.toUpperCase())}
              className="w-full mt-1 px-3 py-2 bg-background border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-[#f59e0b]"
              placeholder="Nhập biển số..."
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-muted-foreground uppercase tracking-wider">
                Trạng thái
              </label>
              <select
                value={editStatus}
                onChange={(e) => setEditStatus(e.target.value)}
                className="w-full mt-1 px-2 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-[#f59e0b]"
              >
                <option value="Vào cổng">Vào cổng</option>
                <option value="Đã vào">Đã vào</option>
                <option value="Đang cân">Đang cân</option>
                <option value="Ra cổng">Ra cổng</option>
                <option value="Đã ra">Đã ra</option>
              </select>
            </div>

            <div>
              <label className="text-xs text-muted-foreground uppercase tracking-wider">
                Thể tích (m³)
              </label>
              <input
                type="text"
                value={editVolume}
                onChange={(e) => setEditVolume(e.target.value)}
                disabled={!isVolumeEnabled}
                className={`w-full mt-1 px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-[#f59e0b] font-mono ${!isVolumeEnabled ? "opacity-50 blur-[0.5px] cursor-not-allowed select-none" : ""}`}
                placeholder="0.00"
              />
            </div>
          </div>

          <div>
            <label className="text-xs text-muted-foreground uppercase tracking-wider">
              Xác minh
            </label>
            <select
              value={editVerify}
              onChange={(e) => setEditVerify(e.target.value)}
              className="w-full mt-1 px-3 py-2 bg-background border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-[#f59e0b] text-sm"
            >
              <option value="Đã xác minh">Đã xác minh</option>
              <option value="Chưa xác minh">Chưa xác minh</option>
              <option value="Cần KT">Cần KT</option>
              <option value="Xe lạ">Xe lạ</option>
              <option value="Xe chưa ĐK">Xe chưa ĐK</option>
              <option value="Từ chối">Từ chối</option>
            </select>
          </div>

          <div>
            <label className="text-xs text-muted-foreground uppercase tracking-wider">
              Ghi chú
            </label>
            <input
              type="text"
              value={editNote}
              onChange={(e) => setEditNote(e.target.value)}
              className="w-full mt-1 px-3 py-2 bg-background border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-[#f59e0b]"
              placeholder="Nhập ghi chú..."
            />
          </div>
        </div>

        <div className="flex gap-3 pt-4">
          <button
            onClick={onClose}
            className="flex-1 py-2 bg-muted text-muted-foreground rounded-md font-medium"
          >
            Hủy
          </button>
          <button
            onClick={onSave}
            className="flex-1 py-2 bg-[#f59e0b] text-black rounded-md font-bold"
          >
            Lưu
          </button>
        </div>
      </div>
    </div>
  );
}
