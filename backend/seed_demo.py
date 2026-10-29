from datetime import date, timedelta
from decimal import Decimal
from app.database import SessionLocal, Base, engine
from app import models

# Register ORM models before creating tables so SQLite gets the schema.
Base.metadata.create_all(bind=engine)
db=SessionLocal()
try:
    existing=db.query(models.FDRRecord).filter_by(institution_id="AICTE-DEMO-001",fdr_number="FDR-DEMO-2026-001").first()
    if not existing:
        r=models.FDRRecord(institution_name="Eastern Institute of Technology (Fictional)",institution_id="AICTE-DEMO-001",
            bank_name="National Sample Bank",fdr_number="FDR-DEMO-2026-001",deposit_amount=Decimal("500000.00"),
            issue_date=date.today()-timedelta(days=335),maturity_date=date.today()+timedelta(days=30),
            document_original_name=None,document_path=None,document_mime=None,extracted_data={"source":"seed_demo","note":"Fictional sample; not bank verified."},
            record_status="active",review_status="pending_review",created_by_role="institution")
        db.add(r); db.flush()
        db.add(models.AuditLog(record_id=r.id,actor_role="admin",action="demo_record_seeded",details={"fictional":True}))
        db.commit()
        print("Created fictional demo FDR:",r.id)
    else: print("Demo record already exists.")
finally: db.close()
