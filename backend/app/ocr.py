import io, re, shutil, subprocess
from datetime import datetime
from pypdf import PdfReader
from PIL import Image, ImageOps, ImageFilter
import pytesseract
def _image_ocr(image):
    image = ImageOps.grayscale(image)
    image = ImageOps.autocontrast(image)
    image = image.filter(ImageFilter.SHARPEN)
    return pytesseract.image_to_string(image, config="--psm 6")
def extract_text(data: bytes, mime: str) -> tuple[str, str]:
    if mime == "application/pdf":
        try:
            reader = PdfReader(io.BytesIO(data))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            text = ""
        if len(text.strip()) >= 20:
            return text, "pdf_text"
        if not shutil.which("tesseract"):
            return text, "ocr_unavailable"
        try:
            # Convert pages with pdftoppm when installed; otherwise report the limitation.
            if not shutil.which("pdftoppm"): return text, "ocr_unavailable"
            import tempfile, os
            with tempfile.TemporaryDirectory() as td:
                pdfpath=os.path.join(td,"upload.pdf")
                open(pdfpath,"wb").write(data)
                subprocess.run(["pdftoppm","-png","-r","200",pdfpath,os.path.join(td,"page")], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                pages=sorted(os.path.join(td,f) for f in os.listdir(td) if f.endswith(".png"))
                ocr="\n".join(_image_ocr(Image.open(p)) for p in pages)
                return ocr, "tesseract_ocr" if ocr.strip() else "unreadable"
        except Exception:
            return text, "ocr_failed"
    try:
        return _image_ocr(Image.open(io.BytesIO(data))), "tesseract_ocr"
    except Exception:
        return "", "unreadable"
def parse_fields(text: str) -> dict:
    # Label-based extraction for common FDR layouts. Values remain unverified drafts.
    lines = [re.sub(r"\s+", " ", line).strip(" \t:—-") for line in text.splitlines()]
    lines = [line for line in lines if line]

    def labeled(*labels):
        label_re = re.compile(r"^(?:" + "|".join(labels) + r")\s*[:：]?\s*(.*)$", re.I)
        for i, line in enumerate(lines):
            m = label_re.match(line)
            if m:
                value = m.group(1).strip()
                if value:
                    return value
                if i + 1 < len(lines):
                    return lines[i + 1].strip()
        return ""

    out = {
        "institution_name": labeled(r"institution(?:\s+name)?", r"college(?:\s+name)?", r"institute(?:\s+name)?", r"customer\s*/\s*depositor", r"depositor"),
        "institution_id": labeled(r"institution\s*(?:id|code)", r"aishe\s*code"),
        "bank_name": labeled(r"bank\s*name", r"bank"),
        "fdr_number": labeled(r"fdr\s*/\s*receipt\s*no\.?", r"fdr\s*(?:no|number|reference)", r"receipt\s*(?:no|number)", r"deposit\s*receipt\s*no"),
        "deposit_amount": labeled(r"deposit\s*amount", r"amount"),
        "issue_date": labeled(r"issue\s*date", r"date\s*of\s*issue", r"deposit\s*date"),
        "maturity_date": labeled(r"maturity\s*date", r"date\s*of\s*maturity"),
    }
    for key in ("institution_name", "bank_name", "fdr_number", "deposit_amount", "issue_date", "maturity_date"):
        out[key] = out[key].strip().strip(".,;")
    if out["deposit_amount"]:
        m = re.search(r"(?:INR|Rs\.?|₹|■)?\s*([\d,]+(?:\.\d{1,2})?)", out["deposit_amount"], re.I)
        out["deposit_amount"] = m.group(1).replace(",", "") if m else ""
    for key in ("issue_date", "maturity_date"):
        value = out[key]
        parsed = False
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y", "%d %B %Y", "%d %b %Y"):
            try:
                out[key] = datetime.strptime(value, fmt).date().isoformat()
                parsed = True
                break
            except ValueError:
                pass
        if value and not parsed:
            out[key] = ""
    return out
