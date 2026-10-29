# NidhiRaksha — no-Docker setup (SQLite)

Evidence-driven security deposit and FDR lifecycle management prototype for AICTE problem statement 26265. This version uses SQLite, so PostgreSQL and Docker are not required. The database is a local file (`backend/nidhiraksha.db`).

## Requirements
- Python 3.11+ (Python 3.12 is fine)
- Node.js 20+ (Node 22 is fine)
- Tesseract OCR is optional; PDF text extraction works without it for text-based PDFs.

## Windows setup (VS Code Terminal / PowerShell)
Unzip this project first. Open the extracted `NidhiRaksha` folder in VS Code.

### 1. Start backend
Open a terminal and run these commands one by one:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python seed_demo.py
uvicorn app.main:app --reload
```

If PowerShell blocks activation, run this in that terminal and then activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

Keep this terminal open. Backend API docs: http://127.0.0.1:8000/docs

### 2. Start frontend
Open a **second** VS Code terminal at the project root and run:

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite, normally http://localhost:5173. Keep both terminals open while using the app.

## Demo walkthrough
1. Open Upload & Extract and upload `sample-data/demo-fdr.pdf` or `sample-data/demo-fdr.png`.
2. Review extracted fields, edit if needed, and choose Validate & Save.
3. Open Repository, select a record, and inspect maturity status.
4. Add a review observation, record lifecycle history, or create a release/refund request.
5. Use the fictional seeded sample record as a demo.

## Important limitations
This is a local prototype. The demo role is selected through a request header, not real authentication. OCR output is only a draft and requires human review. No bank verification, AICTE production integration, e-signature, or real financial transfer is connected. Do not use real sensitive documents or treat this prototype as a production financial system.
