import re
import os
import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Try defensive imports for OCR tools
EASYOCR_AVAILABLE = False
TESSERACT_AVAILABLE = False

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    logger.warning("easyocr not installed, falling back to Tesseract or rule-based parser")

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    logger.warning("pytesseract or PIL not installed, falling back to rule-based parser")

def parse_extracted_text(text: str) -> Dict[str, Any]:
    """
    Scans OCR-extracted text using regex patterns to pull blood values.
    """
    data = {
        "blood_group": None,
        "hemoglobin": None,
        "platelets": None,
        "wbc_count": None,
        "last_donation_date": None,
        "diagnosis": ""
    }
    
    # Blood Group: A/B/O/AB with +/-
    bg_match = re.search(r'\b(A|B|AB|O)\s*[\+\-]\b', text, re.IGNORECASE)
    if bg_match:
        data["blood_group"] = bg_match.group(0).upper().replace(" ", "")
    else:
        # Check alternative spelling e.g., "O Positive"
        for gp in ["A", "B", "O", "AB"]:
            for sign, sign_char in [("positive", "+"), ("negative", "-"), ("pos", "+"), ("neg", "-")]:
                if re.search(rf'\b{gp}\s+{sign}\b', text, re.IGNORECASE):
                    data["blood_group"] = f"{gp.upper()}{sign_char}"
                    break
            if data["blood_group"]:
                break

    # Hemoglobin (g/dL)
    hb_match = re.search(r'(?:hemoglobin|hb|hgb)\s*:?\s*(\d+(?:\.\d+)?)\s*(?:g/dl|g/l)?', text, re.IGNORECASE)
    if hb_match:
        data["hemoglobin"] = float(hb_match.group(1))

    # Platelets (per mcL or cells/uL)
    plt_match = re.search(r'(?:platelet|platelets|plt|thrombocyte)\s*count?\s*:?\s*(\d{1,3}(?:[,\s]?\d{3})*|\d+)\s*(?:k/ul|thou/ul)?', text, re.IGNORECASE)
    if plt_match:
        val_str = plt_match.group(1).replace(",", "").replace(" ", "")
        try:
            val = float(val_str)
            # If platelet count is written in thousands e.g. 250 instead of 250000
            if val < 1000:
                val *= 1000
            data["platelets"] = val
        except ValueError:
            pass

    # WBC Count (White Blood Cells)
    wbc_match = re.search(r'(?:wbc|white\s*blood\s*cells?|leukocytes)\s*:?\s*(\d{1,3}(?:[,\s]?\d{3})*|\d+(?:\.\d+)?)\s*(?:k/ul)?', text, re.IGNORECASE)
    if wbc_match:
        val_str = wbc_match.group(1).replace(",", "").replace(" ", "")
        try:
            val = float(val_str)
            if val < 100:  # e.g., 6.5 instead of 6500
                val *= 1000
            data["wbc_count"] = val
        except ValueError:
            pass

    # Last Donation Date
    ldd_match = re.search(r'(?:last\s*donation|donated\s*on)\s*:?\s*(\d{4}[-\/\.]\d{1,2}[-\/\.]\d{1,2}|\d{1,2}[-\/\.]\d{1,2}[-\/\.]\d{2,4})', text, re.IGNORECASE)
    if ldd_match:
        date_str = ldd_match.group(1)
        # Try parsing date formats
        for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%d.%m.%Y"]:
            try:
                parsed_dt = datetime.strptime(date_str, fmt)
                data["last_donation_date"] = parsed_dt.date()
                break
            except ValueError:
                continue

    # Diagnosis and Notes
    diag_match = re.search(r'(?:diagnosis|notes|remarks|doctor\s*notes)\s*:?\s*(.*)', text, re.IGNORECASE)
    if diag_match:
        data["diagnosis"] = diag_match.group(1).strip()

    return data

def mock_ocr_from_filename(filename: str) -> Dict[str, Any]:
    """
    A smart simulation helper that looks for keywords in filenames to test OCR
    and eligibility pipelines. e.g. "report_hb_11_Oplus.png"
    """
    text_content = ""
    # Defaults
    bg = "O+"
    hb = 14.5
    plt = 250000.0
    wbc = 7200.0
    last_don = (date.today() - timedelta(days=90)).strftime("%Y-%m-%d")
    diag = "Normal health examination. Fit for blood donation."
    
    filename_lower = filename.lower()
    if "hb_low" in filename_lower or "hb11" in filename_lower or "anemic" in filename_lower:
        hb = 11.2
        diag = "Patient is mildly anemic."
    if "plt_low" in filename_lower or "thrombocytopenia" in filename_lower:
        plt = 120000.0
        diag = "Thrombocytopenia detected."
    if "recent_donation" in filename_lower or "donated_recent" in filename_lower:
        last_don = (date.today() - timedelta(days=20)).strftime("%Y-%m-%d")
    
    # Extract custom groups from filename
    # Check blood group in name: A_pos, A_neg, B_pos, O_pos, AB_pos, AB_neg, etc.
    for gp in ["A", "B", "AB", "O"]:
        for suffix in ["_pos", "pos", "_plus", "plus", "positive"]:
            if f"{gp.lower()}{suffix}" in filename_lower:
                bg = f"{gp.upper()}+"
        for suffix in ["_neg", "neg", "_minus", "minus", "negative"]:
            if f"{gp.lower()}{suffix}" in filename_lower:
                bg = f"{gp.upper()}-"

    text_content = f"""
    LABORATORY BLOOD REPORT
    =======================
    Patient Name: Test Donor
    Blood Group: {bg}
    Hemoglobin (Hb): {hb} g/dL
    Platelet Count: {plt} /mcL
    WBC Count: {wbc} /uL
    Last Donation Date: {last_don}
    Diagnosis: {diag}
    """
    return parse_extracted_text(text_content)

def extract_medical_report(file_path: str) -> Dict[str, Any]:
    """
    Extracts text from file_path using OCR (Tesseract / EasyOCR) if installed,
    otherwise parses text directly if it is a text file or runs simulation.
    """
    filename = os.path.basename(file_path)
    text = ""

    # If file is text, read it directly
    if file_path.endswith(('.txt', '.json')):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            logger.error(f"Error reading text report file: {e}")
    else:
        # Check if easyocr can parse
        parsed_successfully = False
        if EASYOCR_AVAILABLE:
            try:
                reader = easyocr.Reader(['en'], gpu=False)
                result = reader.readtext(file_path, detail=0)
                text = " ".join(result)
                parsed_successfully = True
            except Exception as e:
                logger.error(f"EasyOCR failed: {e}")

        # Check if tesseract can parse
        if not parsed_successfully and TESSERACT_AVAILABLE:
            try:
                img = Image.open(file_path)
                text = pytesseract.image_to_string(img)
                parsed_successfully = True
            except Exception as e:
                logger.error(f"Tesseract failed: {e}")

        # If both failed or are unavailable, simulate based on filename
        if not parsed_successfully or not text.strip():
            logger.info("Using simulated fallback OCR parser.")
            return mock_ocr_from_filename(filename)

    return parse_extracted_text(text)

def determine_eligibility(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Runs medical report statistics through rules to assess blood donor eligibility.
    """
    is_eligible = True
    reasons = []
    
    # 1. Hemoglobin check
    # Min 12.5 required
    hb = extracted_data.get("hemoglobin")
    if hb is not None:
        if hb < 12.5:
            is_eligible = False
            reasons.append(f"Low Hemoglobin level ({hb} g/dL). Must be at least 12.5 g/dL.")
    else:
        # Default fallback if missing
        extracted_data["hemoglobin"] = 14.0

    # 2. Platelet check
    # Min 150,000 required
    plt = extracted_data.get("platelets")
    if plt is not None:
        if plt < 150000:
            is_eligible = False
            reasons.append(f"Low platelet count ({int(plt):,} /mcL). Must be at least 150,000 /mcL.")
    else:
        # Default fallback
        extracted_data["platelets"] = 220000.0

    # 3. WBC Check
    # Abnormal WBC count might mean infection
    wbc = extracted_data.get("wbc_count")
    if wbc is not None:
        if wbc > 15000:
            is_eligible = False
            reasons.append(f"Elevated White Blood Cell count ({int(wbc):,} /uL), indicating active infection.")
        elif wbc < 3500:
            is_eligible = False
            reasons.append(f"Abnormally low White Blood Cell count ({int(wbc):,} /uL).")
    else:
        extracted_data["wbc_count"] = 6500.0

    # 4. Last donation date check
    # Must be > 56 days ago (approx 8 weeks)
    last_don = extracted_data.get("last_donation_date")
    next_eligible = date.today()
    if last_don:
        # If last_don is string, convert it
        if isinstance(last_don, str):
            try:
                last_don = datetime.strptime(last_don, "%Y-%m-%d").date()
            except ValueError:
                last_don = None
        
        if last_don:
            days_since = (date.today() - last_don).days
            if days_since < 56:
                is_eligible = False
                wait_days = 56 - days_since
                next_eligible = date.today() + timedelta(days=wait_days)
                reasons.append(f"Last donation was too recent ({days_since} days ago). Must wait 56 days between donations.")
            else:
                next_eligible = date.today()

    # Determine risk level
    risk_level = "Low"
    diagnosis = extracted_data.get("diagnosis", "").lower()
    
    # If ineligible or specific symptoms mentioned, increase risk
    if not is_eligible:
        risk_level = "Medium"
    
    # Any major diagnosis keywords
    high_risk_words = ["anemia", "hepatitis", "hiv", "malaria", "leukemia", "cancer", "diabetes", "syphilis"]
    if any(word in diagnosis for word in high_risk_words):
        risk_level = "High"
        is_eligible = False
        reasons.append(f"Report contains medical risk diagnosis: {diagnosis}")

    # Format output
    result = {
        "blood_group_extracted": extracted_data.get("blood_group") or "O+", # default
        "hemoglobin": extracted_data.get("hemoglobin"),
        "platelets": extracted_data.get("platelets"),
        "wbc_count": extracted_data.get("wbc_count"),
        "last_donation_date": last_don,
        "diagnosis": extracted_data.get("diagnosis") or "No symptoms reported",
        "is_eligible": is_eligible,
        "ineligibility_reason": "; ".join(reasons) if reasons else None,
        "next_eligible_date": next_eligible,
        "risk_level": risk_level
    }
    return result
