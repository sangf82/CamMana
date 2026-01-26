import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
from fpdf import FPDF

from backend.config import DATA_DIR, PROJECT_ROOT

logger = logging.getLogger(__name__)

def strip_accents(text):
    """Simple helper to remove Vietnamese accents for PDF compatibility with basic fonts"""
    if not isinstance(text, str): return str(text)
    accents = {
        'a': 'àáảãạăằắẳẵặâầấẩẫậ', 'A': 'ÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬ',
        'e': 'èéẻẽẹêềếểễệ', 'E': 'ÈÉẺẼẸÊỀẾỂỄỆ',
        'i': 'ìíỉĩị', 'I': 'ÌÍỈĨỊ',
        'o': 'òóỏõọôồốổỗộơờớởỡợ', 'O': 'ÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢ',
        'u': 'ùúủũụưừứửữự', 'U': 'ÙÚỦŨỤƯỪỨỬỮỰ',
        'y': 'ỳýỷỹỵ', 'Y': 'ỲÝỶỸỴ',
        'd': 'đ', 'D': 'Đ'
    }
    for char, accented in accents.items():
        for a in accented:
            text = text.replace(a, char)
    return text

class ReportLogic:
    REPORT_DIR = PROJECT_ROOT / "database" / "report"
    DATE_FORMAT = "%d-%m-%Y"

    def __init__(self):
        self.REPORT_DIR.mkdir(parents=True, exist_ok=True)

    def generate_report(self, date_str: str) -> Dict[str, Any]:
        """
        Generate daily report for a specific date.
        """
        history_file = DATA_DIR / f"history_{date_str}.csv"
        register_file = DATA_DIR / f"registered_cars_{date_str}.csv"

        if not history_file.exists():
            # If history file doesn't exist, we can't generate a meaningful report
            return self._empty_report(date_str)

        try:
            # Read history
            df_history = pd.read_csv(history_file)
            
            # Read registration (might be from previous day if they rotate daily)
            # In RegisteredCarLogic, it seems they copy today's from yesterday's if missing.
            if register_file.exists():
                df_reg = pd.read_csv(register_file)
            else:
                # Fallback to current registered cars file if specific date one is missing
                today_str = datetime.now().strftime(self.DATE_FORMAT)
                fallback_reg = DATA_DIR / f"registered_cars_{today_str}.csv"
                if fallback_reg.exists():
                    df_reg = pd.read_csv(fallback_reg)
                else:
                    df_reg = pd.DataFrame(columns=["car_plate", "car_wheel", "car_owner", "car_volume"])

            # 1. Total car registered
            total_registered = len(df_reg)

            # 2. Total car going in the place at that day
            # Assuming every row in history is an entry
            total_in = len(df_history)

            # 3. Total volume moved out
            # We need rows with time_out and vol_measured
            # Filter rows where time_out is not '---' or empty
            df_out = df_history[df_history['time_out'].notna() & (df_history['time_out'] != '---')].copy()
            
            # Convert vol_measured to numeric, handle errors
            df_out['vol_measured'] = pd.to_numeric(df_out['vol_measured'], errors='coerce').fillna(0)
            total_volume_out = float(df_out['vol_measured'].sum())

            # 4. Average volume each truck carry
            total_cars_out = len(df_out)
            avg_volume = total_volume_out / total_cars_out if total_cars_out > 0 else 0

            # 5. Distribution of car based on number of wheel
            # Group by car_wheel from registration
            wheel_dist = {}
            if 'car_wheel' in df_reg.columns:
                dist = df_reg['car_wheel'].value_counts().to_dict()
                wheel_dist = {str(k): int(v) for k, v in dist.items()}

            # 6. Distribution of volume taken out based on nha thau (car_owner)
            # Merge df_out with df_reg on plate
            contractor_dist = {}
            if not df_out.empty and not df_reg.empty:
                # Normalize plates for merging
                df_out['norm_plate'] = df_out['plate'].str.replace(r'[^a-zA-Z0-9]', '', regex=True).str.upper()
                df_reg['norm_plate'] = df_reg['car_plate'].str.replace(r'[^a-zA-Z0-9]', '', regex=True).str.upper()
                
                merged = pd.merge(df_out, df_reg, left_on='norm_plate', right_on='norm_plate', how='left')
                
                # Fill missing car_owner with 'Unknown'
                if 'car_owner' in merged.columns:
                    merged['car_owner'] = merged['car_owner'].fillna('Unknown')
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
                    "contractor_volume_distribution": contractor_dist
                },
                "generated_at": datetime.now().isoformat()
            }

            # Save to JSON
            report_file = self.REPORT_DIR / f"report_{date_str}.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)

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
                "contractor_volume_distribution": {}
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
        # Extract dates and sort descending
        dates = [f.name.replace("report_", "").replace(".json", "") for f in files]
        dates.sort(key=lambda x: datetime.strptime(x, self.DATE_FORMAT), reverse=True)
        return dates

    def export_pdf(self, date_str: str) -> Optional[bytes]:
        data = self.get_report(date_str)
        if not data:
            data = self.generate_report(date_str)
        
        try:
            pdf = FPDF()
            pdf.add_page()
            
            # Use a unicode-friendly font if available, or stick to standard
            pdf.set_font("helvetica", "B", 16)
            pdf.cell(0, 10, strip_accents(f"BAO CAO NGAY {date_str}"), ln=True, align="C")
            pdf.ln(10)
            
            # Summary Section
            pdf.set_font("helvetica", "B", 12)
            pdf.cell(0, 10, strip_accents("1. Thong ke tong hop"), ln=True)
            pdf.set_font("helvetica", "", 11)
            summary = data["summary"]
            pdf.cell(0, 8, strip_accents(f"- Tong so xe dang ky: {summary['total_registered']}"), ln=True)
            pdf.cell(0, 8, strip_accents(f"- Tong so luot xe vao: {summary['total_in']}"), ln=True)
            pdf.cell(0, 8, strip_accents(f"- Tong khoi luong ra: {summary['total_volume_out']} m3"), ln=True)
            pdf.cell(0, 8, strip_accents(f"- Khoi luong trung binh/xe: {summary['avg_volume']} m3"), ln=True)
            pdf.ln(5)
            
            # Wheel Distribution
            pdf.set_font("helvetica", "B", 12)
            pdf.cell(0, 10, strip_accents("2. Phan bo theo so banh xe"), ln=True)
            pdf.set_font("helvetica", "", 11)
            for wheel, count in data["charts"]["wheel_distribution"].items():
                pdf.cell(0, 8, strip_accents(f"- Loai {wheel} banh: {count} xe"), ln=True)
            pdf.ln(5)
            
            # Contractor Distribution
            pdf.set_font("helvetica", "B", 12)
            pdf.cell(0, 10, strip_accents("3. Khoi luong theo nha thau"), ln=True)
            pdf.set_font("helvetica", "", 11)
            for contractor, vol in data["charts"]["contractor_volume_distribution"].items():
                pdf.cell(0, 8, strip_accents(f"- {contractor}: {vol} m3"), ln=True)
                
            pdf.ln(20)
            pdf.set_font("helvetica", "I", 8)
            pdf.cell(0, 10, f"Generated at: {data['generated_at']}", align="R")
            
            return bytes(pdf.output())
        except Exception as e:
            logger.error(f"Error exporting PDF for {date_str}: {e}")
            return None

if __name__ == "__main__":
    # Test
    logic = ReportLogic()
    today = datetime.now().strftime("%d-%m-%Y")
    print(f"Generating report for {today}...")
    report = logic.generate_report(today)
    print(json.dumps(report, indent=2))
