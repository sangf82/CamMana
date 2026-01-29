import React, { useState, useRef, useEffect } from "react";
import { X, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";

interface CustomSelectProps {
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  placeholder?: string;
}

function CustomSelect({ value, onChange, options, placeholder }: CustomSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const selectedLabel = options.find((o) => o.value === value)?.label || placeholder || "";

  return (
    <div ref={containerRef} className="relative mt-1">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-amber-500 transition-all text-foreground"
      >
        <span className={value ? "text-foreground" : "text-muted-foreground"}>{selectedLabel}</span>
        <ChevronDown className={`w-4 h-4 text-muted-foreground transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`} />
      </button>
      {isOpen && (
        <div className="absolute top-full left-0 w-full z-[100] mt-1 bg-popover text-popover-foreground border border-border rounded-xl shadow-2xl p-1 max-h-56 overflow-y-auto animate-in fade-in slide-in-from-top-1 duration-200">
          {options.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => {
                onChange(option.value);
                setIsOpen(false);
              }}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm font-medium transition-colors hover:bg-amber-500/10 ${
                value === option.value ? "text-amber-500 bg-amber-500/10" : "text-foreground"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

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

const STATUS_OPTIONS = [
  { value: "Vào cổng", label: "Vào cổng" },
  { value: "Đã vào", label: "Đã vào" },
  { value: "Đang cân", label: "Đang cân" },
  { value: "Ra cổng", label: "Ra cổng" },
  { value: "Đã ra", label: "Đã ra" },
];

const VERIFY_OPTIONS = [
  { value: "Đã xác minh", label: "Đã xác minh" },
  { value: "Chưa xác minh", label: "Chưa xác minh" },
  { value: "Cần KT", label: "Cần KT" },
  { value: "Xe lạ", label: "Xe lạ" },
  { value: "Xe chưa ĐK", label: "Xe chưa ĐK" },
  { value: "Từ chối", label: "Từ chối" },
];

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
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[9999] pointer-events-auto backdrop-blur-sm">
      <div className="bg-card border border-border rounded-lg p-6 w-96 space-y-4 shadow-xl animate-in zoom-in-95 duration-200">
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-lg">Sửa thông tin xe</h3>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="h-8 w-8 text-muted-foreground hover:text-foreground"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
              Biển số
            </label>
            <input
              type="text"
              value={editPlate}
              onChange={(e) => setEditPlate(e.target.value.toUpperCase())}
              className="w-full mt-1 px-3 py-2 bg-background border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-amber-500 transition-all font-mono font-bold tracking-wide text-foreground"
              placeholder="Nhập biển số..."
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
                Trạng thái
              </label>
              <CustomSelect
                value={editStatus}
                onChange={setEditStatus}
                options={STATUS_OPTIONS}
              />
            </div>

            <div>
              <label className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
                Thể tích (m³)
              </label>
              <input
                type="text"
                value={editVolume}
                onChange={(e) => setEditVolume(e.target.value)}
                disabled={!isVolumeEnabled}
                className={`w-full mt-1 px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-amber-500 font-mono transition-all text-foreground ${!isVolumeEnabled ? "opacity-50 blur-[0.5px] cursor-not-allowed select-none" : ""}`}
                placeholder="0.00"
              />
            </div>
          </div>

          <div>
            <label className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
              Xác minh
            </label>
            <CustomSelect
              value={editVerify}
              onChange={setEditVerify}
              options={VERIFY_OPTIONS}
            />
          </div>

          <div>
            <label className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
              Ghi chú
            </label>
            <input
              type="text"
              value={editNote}
              onChange={(e) => setEditNote(e.target.value)}
              className="w-full mt-1 px-3 py-2 bg-background border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-amber-500 transition-all text-foreground"
              placeholder="Nhập ghi chú..."
            />
          </div>
        </div>

        <div className="flex gap-3 pt-4">
          <Button
            onClick={onClose}
            variant="secondary"
            className="flex-1 font-medium"
          >
            Hủy
          </Button>
          <Button
            onClick={onSave}
            className="flex-1 font-bold bg-amber-500 hover:bg-amber-600 text-black"
          >
            Lưu
          </Button>
        </div>
      </div>
    </div>
  );
}
