import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
import matplotlib.pyplot as plt
import io
import os
from fpdf import FPDF

from backend.config import DATA_DIR, PROJECT_ROOT

logger = logging.getLogger(__name__)

class ReportLogic:
    REPORT_DIR = PROJECT_ROOT / "database" / "report"
    DATE_FORMAT = "%d-%m-%Y"
    
    # Path to a font that supports Vietnamese (standard on Windows)
    FONT_PATH = "C:\\Windows\\Fonts\\Arial.ttf"

    def __init__(self):
        self.REPORT_DIR.mkdir(parents=True, exist_ok=True)

    def generate_report(self, date_str: str, allowed_gates: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Generate daily report for a specific date.
        If allowed_gates is provided, filters data by gate.
        """
        history_file = DATA_DIR / f"history_{date_str}.csv"
        register_file = DATA_DIR / f"registered_cars_{date_str}.csv"

        if not history_file.exists():
            return self._empty_report(date_str)

        try:
            df_history = pd.read_csv(history_file)
            
            # Filter by gate if restricted
            if allowed_gates:
                df_history = df_history[df_history['location'].isin(allowed_gates)]
            
            if register_file.exists():
                df_reg = pd.read_csv(register_file)
            else:
                today_str = datetime.now().strftime(self.DATE_FORMAT)
                fallback_reg = DATA_DIR / f"registered_cars_{today_str}.csv"
                if fallback_reg.exists():
                    df_reg = pd.read_csv(fallback_reg)
                else:
                    df_reg = pd.DataFrame(columns=["car_plate", "car_wheel", "car_owner", "car_volume"])

            total_registered = len(df_reg)
            total_in = len(df_history)
            
            df_out = df_history[df_history['time_out'].notna() & (df_history['time_out'] != '---')].copy()
            df_out['vol_measured'] = pd.to_numeric(df_out['vol_measured'], errors='coerce').fillna(0)
            total_volume_out = float(df_out['vol_measured'].sum())

            total_cars_out = len(df_out)
            avg_volume = total_volume_out / total_cars_out if total_cars_out > 0 else 0

            # Hourly distribution
            hourly_dist = {}
            if not df_history.empty:
                # Convert time_in to datetime and extract hour
                df_history['hour'] = pd.to_datetime(df_history['time_in'], format='%H:%M:%S', errors='coerce').dt.hour
                h_dist = df_history['hour'].dropna().value_counts().sort_index().to_dict()
                # Ensure all 24 hours are represented
                hourly_dist = {str(int(h)): int(h_dist.get(h, 0)) for h in range(24)}

            wheel_dist = {}
            if 'car_wheel' in df_reg.columns:
                dist = df_reg['car_wheel'].value_counts().to_dict()
                wheel_dist = {str(k): int(v) for k, v in dist.items()}

            contractor_dist = {}
            if not df_out.empty and not df_reg.empty:
                df_out_copy = df_out.copy()
                df_out_copy['norm_plate'] = df_out_copy['plate'].astype(str).str.replace(r'[^a-zA-Z0-9]', '', regex=True).str.upper()
                
                df_reg_copy = df_reg.copy()
                df_reg_copy['norm_plate'] = df_reg_copy['car_plate'].astype(str).str.replace(r'[^a-zA-Z0-9]', '', regex=True).str.upper()
                
                df_reg_subset = df_reg_copy[['norm_plate', 'car_owner']].drop_duplicates(subset=['norm_plate'])
                merged = pd.merge(df_out_copy, df_reg_subset, on='norm_plate', how='left')
                merged['car_owner'] = merged['car_owner'].fillna('Khách vãng lai') 
                
                c_dist = merged.groupby('car_owner')['vol_measured'].sum().to_dict()
                contractor_dist = {str(k): float(v) for k, v in c_dist.items()}

            report_data = {
                "date": date_str,
                "summary": {
                    "total_registered": total_registered,
                    "total_in": total_in,
                    "total_volume_out": round(total_volume_out, 2),
                    "avg_volume": round(avg_volume, 2)
                },
                "charts": {
                    "wheel_distribution": wheel_dist,
                    "contractor_volume_distribution": contractor_dist,
                    "hourly_distribution": hourly_dist
                },
                "generated_at": datetime.now().isoformat()
            }

            # ONLY save to disk if it's a global report (not filtered)
            if not allowed_gates:
                report_file = self.REPORT_DIR / f"report_{date_str}.json"
                with open(report_file, 'w', encoding='utf-8') as f:
                    json.dump(report_data, f, ensure_ascii=False, indent=2)
            else:
                report_data["is_filtered"] = True
                report_data["allowed_gates"] = allowed_gates

            return report_data

        except Exception as e:
            logger.error(f"Error generating report for {date_str}: {e}")
            return self._empty_report(date_str, error=str(e))

    def _empty_report(self, date_str: str, error: str = None) -> Dict[str, Any]:
        return {
            "date": date_str,
            "summary": {
                "total_registered": 0,
                "total_in": 0,
                "total_volume_out": 0,
                "avg_volume": 0
            },
            "charts": {
                "wheel_distribution": {},
                "contractor_volume_distribution": {},
                "hourly_distribution": {}
            },
            "generated_at": datetime.now().isoformat(),
            "status": "empty",
            "error": error
        }

    def get_report(self, date_str: str) -> Optional[Dict[str, Any]]:
        report_file = self.REPORT_DIR / f"report_{date_str}.json"
        if report_file.exists():
            with open(report_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def list_reports(self) -> List[str]:
        files = list(self.REPORT_DIR.glob("report_*.json"))
        dates = [f.name.replace("report_", "").replace(".json", "") for f in files]
        dates.sort(key=lambda x: datetime.strptime(x, self.DATE_FORMAT), reverse=True)
        return dates

    def _create_chart_image(self, data: Dict[str, Any], title: str, ylabel: str, color: str) -> io.BytesIO:
        """Create a chart image and return as BytesIO"""
        plt.figure(figsize=(10, 6))
        
        # Vietnamese support for matplotlib requires font setting
        # Fallback to standard if Arial not found
        try:
            plt.rcParams['font.family'] = 'Arial'
        except:
            pass
            
        names = list(data.keys())
        values = list(data.values())
        
        plt.bar(names, values, color=color)
        plt.title(title, fontsize=16, fontweight='bold', pad=20)
        plt.ylabel(ylabel, fontsize=12)
        plt.xticks(rotation=45, ha='right')
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png', dpi=300)
        plt.close()
        img_buf.seek(0)
        return img_buf

    def export_pdf(self, date_str: str) -> Optional[bytes]:
        data = self.get_report(date_str)
        if not data:
            data = self.generate_report(date_str)
        
        try:
            pdf = FPDF()
            
            # Setup Fonts
            has_unicode = False
            # Common paths for Arial family on Windows
            reg_font = "C:\\Windows\\Fonts\\arial.ttf"
            bold_font = "C:\\Windows\\Fonts\\arialbd.ttf"
            italic_font = "C:\\Windows\\Fonts\\ariali.ttf"

            if os.path.exists(reg_font):
                try:
                    pdf.add_font("Arial", "", reg_font)
                    if os.path.exists(bold_font):
                        pdf.add_font("Arial", "B", bold_font)
                    if os.path.exists(italic_font):
                        pdf.add_font("Arial", "I", italic_font)
                    
                    pdf.set_font("Arial", size=12)
                    has_unicode = True
                except Exception as e:
                    logger.warning(f"Failed to load Arial font: {e}")
            
            if not has_unicode:
                pdf.set_font("helvetica", size=12)
                
            def txt(t):
                if not has_unicode:
                    # Fallback helper if no unicode font
                    from backend.data_process.report.logic import strip_accents
                    return strip_accents(t)
                return t

            pdf.add_page()
            
            # Header
            pdf.set_fill_color(245, 158, 11) # Orange theme
            pdf.rect(0, 0, 210, 40, 'F')
            
            pdf.set_text_color(255, 255, 255)
            pdf.set_font(pdf.font_family, "B", 24)
            pdf.cell(0, 20, txt(f"BÁO CÁO NGÀY {date_str}"), ln=True, align="C")
            pdf.ln(5)
            
            # Info box
            pdf.set_text_color(255, 255, 255)
            pdf.set_font(pdf.font_family, "", 10)
            pdf.cell(0, 5, txt(f"Hệ thống Quản lý Camera CamMana"), ln=True, align="C")
            pdf.ln(10)
            
            # Summary Section
            pdf.set_font(pdf.font_family, "B", 16)
            pdf.set_text_color(245, 158, 11)
            pdf.cell(0, 10, txt("1. Thống kê tổng hợp"), ln=True)
            pdf.set_draw_color(245, 158, 11)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)
            
            pdf.set_text_color(0, 0, 0)
            pdf.set_font(pdf.font_family, "", 12)
            summary = data["summary"]
            
            # Table-like summary
            col_width = 95
            pdf.cell(col_width, 10, txt(f"Tổng số xe đăng ký:"), border=0)
            pdf.cell(col_width, 10, txt(f"{summary['total_registered']} xe"), border=0, ln=True)
            
            pdf.cell(col_width, 10, txt(f"Tổng số lượt xe vào:"), border=0)
            pdf.cell(col_width, 10, txt(f"{summary['total_in']} lượt"), border=0, ln=True)
            
            pdf.cell(col_width, 10, txt(f"Tổng khối lượng ra:"), border=0)
            pdf.cell(col_width, 10, txt(f"{summary['total_volume_out']} m³"), border=0, ln=True)
            
            pdf.cell(col_width, 10, txt(f"Khối lượng trung bình/xe:"), border=0)
            pdf.cell(col_width, 10, txt(f"{summary['avg_volume']} m³"), border=0, ln=True)
            pdf.ln(10)
            
            # Charts
            if data["charts"]["wheel_distribution"]:
                pdf.set_font(pdf.font_family, "B", 16)
                pdf.set_text_color(245, 158, 11)
                pdf.cell(0, 10, txt("2. Phân bổ theo số bánh xe"), ln=True)
                pdf.ln(5)
                
                wheel_img = self._create_chart_image(
                    data["charts"]["wheel_distribution"], 
                    "Phân bổ theo số bánh xe", 
                    "Số lượng xe", 
                    "#3b82f6"
                )
                pdf.image(wheel_img, x=15, w=180)
                pdf.ln(10)

            if data["charts"]["contractor_volume_distribution"]:
                # New page for second chart if needed, or just check space
                if pdf.get_y() > 180:
                    pdf.add_page()
                    
                pdf.set_font(pdf.font_family, "B", 16)
                pdf.set_text_color(245, 158, 11)
                pdf.cell(0, 10, txt("3. Khối lượng theo nhà thầu"), ln=True)
                pdf.ln(5)
                
                contractor_img = self._create_chart_image(
                    data["charts"]["contractor_volume_distribution"], 
                    "Khối lượng theo nhà thầu (m³)", 
                    "Khối lượng (m³)", 
                    "#f59e0b"
                )
                pdf.image(contractor_img, x=15, w=180)
                pdf.ln(10)

            if data["charts"].get("hourly_distribution"):
                if pdf.get_y() > 180:
                    pdf.add_page()
                
                pdf.set_font(pdf.font_family, "B", 16)
                pdf.set_text_color(245, 158, 11)
                pdf.cell(0, 10, txt("4. Mật độ xe theo giờ trong ngày"), ln=True)
                pdf.ln(5)
                
                hourly_img = self._create_chart_image(
                    data["charts"]["hourly_distribution"], 
                    "Mật độ xe theo giờ trong ngày (số lượt)", 
                    "Số lượt xe", 
                    "#3b82f6"
                )
                pdf.image(hourly_img, x=15, w=180)
            
            # Footer
            pdf.set_y(-25)
            # Use Italic only if available
            footer_style = "I" if os.path.exists(italic_font) and has_unicode else ""
            pdf.set_font(pdf.font_family, footer_style, 8)
            pdf.set_text_color(128, 128, 128)
            pdf.cell(0, 10, txt(f"Báo cáo được tạo tự động bởi CamMana lúc {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}"), align="L")
            pdf.cell(0, 10, txt(f"Trang {pdf.page_no()}"), align="R")
            
            return bytes(pdf.output())
        except Exception as e:
            logger.error(f"Error exporting PDF for {date_str}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

if __name__ == "__main__":
    logic = ReportLogic()
    today = datetime.now().strftime("%d-%m-%Y")
    print(f"Generating report for {today}...")
    report = logic.generate_report(today)
    print(json.dumps(report, indent=2))
