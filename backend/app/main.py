import os, uuid, hashlib, mimetypes
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from fastapi import FastAPI, Depends, File, UploadFile, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from pydantic import ValidationError
from app.config import settings
from app.database import Base, engine, get_db
from app import models, schemas
from app.ocr import extract_text, parse_fields
app=FastAPI(title="NidhiRaksha API", version="1.0.0", description="FDR lifecycle management prototype")

# Create local SQLite tables automatically for the no-Docker demo setup.
Base.metadata.create_all(bind=engine)
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in settings.cors_origins.split(",")], allow_credentials=True, allow_methods=["*"], allow_headers=["*","X-User-Role"])
STORAGE=Path(settings.document_storage_path).resolve()
STORAGE.mkdir(parents=True,exist_ok=True)
ALLOWED={".pdf":"application/pdf",".jpg":"image/jpeg",".jpeg":"image/jpeg",".png":"image/png"}
def role(x_user_role: str = Header(default="institution")):
    if x_user_role not in ("institution","officer","admin"): raise HTTPException(403,"Unsupported demo role.")
    return x_user_role
def audit(db, actor, action, record_id=None, details=None):
    db.add(models.AuditLog(record_id=record_id, actor_role=actor, action=action, details=details or {}))
def status_for(r):
    today=date.today()
    if r.maturity_date < today: return "matured"
    if (r.maturity_date-today).days <= 30: return "maturing_soon"
    return "active"
def serialize(r):
    return { "id":r.id,"institution_name":r.institution_name,"institution_id":r.institution_id,"bank_name":r.bank_name,
      "fdr_number":r.fdr_number,"deposit_amount":str(r.deposit_amount),"issue_date":r.issue_date.isoformat(),
      "maturity_date":r.maturity_date.isoformat(),"document_original_name":r.document_original_name,
      "document_available":bool(r.document_path),"record_status":status_for(r),"review_status":r.review_status,
      "created_by_role":r.created_by_role,"created_at":r.created_at.isoformat() if r.created_at else None,
      "extracted_data":r.extracted_data or {} }
@app.get("/api/health")
def health(): return {"status":"ok","service":"NidhiRaksha API"}
@app.post("/api/extract")
async def extract(file: UploadFile=File(...), actor=Depends(role)):
    ext=Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED: raise HTTPException(415,"Only PDF, JPG and PNG files are accepted.")
    if file.content_type not in (ALLOWED[ext],"application/octet-stream"): raise HTTPException(415,"File extension and content type do not match.")
    data=await file.read(settings.max_upload_mb*1024*1024+1)
    if not data: raise HTTPException(400,"The uploaded file is empty.")
    if len(data)>settings.max_upload_mb*1024*1024: raise HTTPException(413,f"Maximum upload size is {settings.max_upload_mb} MB.")
    signature_ok=(ext==".pdf" and data.startswith(b"%PDF")) or (ext in (".jpg",".jpeg") and data.startswith(b"\xff\xd8\xff")) or (ext==".png" and data.startswith(b"\x89PNG\r\n\x1a\n"))
    if not signature_ok: raise HTTPException(415,"The file signature does not match a supported PDF/JPG/PNG.")
    text,method=extract_text(data,ALLOWED[ext])
    fields=parse_fields(text)
    token=uuid.uuid4().hex
    safe_name=token+ext
    target=STORAGE/"pending"
    target.mkdir(exist_ok=True)
    (target/safe_name).write_bytes(data)
    (target/(token+".json")).write_text(__import__("json").dumps({"original_name":Path(file.filename or "upload").name[:255],"mime":ALLOWED[ext],"sha256":hashlib.sha256(data).hexdigest()}), encoding="utf-8")
    return {"document_token":token,"original_name":Path(file.filename or "upload").name[:255],"mime":ALLOWED[ext],
      "extraction_method":method,"extracted_data":fields,"ocr_text":text[:30000],
      "field_flags":{k:("missing_or_unreadable" if not v else "machine_extracted_unverified") for k,v in fields.items()},
      "message":"OCR/text extraction is a draft only. Review every field; no bank verification was performed."}
@app.get("/api/records")
def list_records(q: str="", status: str="", review_status: str="", db:Session=Depends(get_db), actor=Depends(role)):
    query=db.query(models.FDRRecord)
    if q:
        like=f"%{q.strip()}%"
        query=query.filter(or_(models.FDRRecord.institution_name.ilike(like),models.FDRRecord.institution_id.ilike(like),models.FDRRecord.fdr_number.ilike(like),models.FDRRecord.bank_name.ilike(like)))
    records=query.order_by(desc(models.FDRRecord.created_at)).all()
    out=[serialize(r) for r in records]
    if status: out=[r for r in out if r["record_status"]==status]
    if review_status: out=[r for r in out if r["review_status"]==review_status]
    return out
@app.post("/api/records")
def create_record(payload: schemas.FDRInput, db:Session=Depends(get_db), actor=Depends(role)):
    if payload.maturity_date<=payload.issue_date: raise HTTPException(422,"Maturity date must be after issue date.")
    if db.query(models.FDRRecord).filter_by(institution_id=payload.institution_id.strip(),fdr_number=payload.fdr_number.strip()).first():
        raise HTTPException(409,"Duplicate FDR reference for this institution.")
    path=None; original=None; mime=None
    token=payload.document_token
    if token:
        pending=STORAGE/"pending"
        matches=list(pending.glob(token+".*"))
        if matches:
            src=matches[0]; destdir=STORAGE/"records"; destdir.mkdir(exist_ok=True)
            meta_path=pending/(token+".json")
            meta=__import__("json").loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
            dest=destdir/(uuid.uuid4().hex+src.suffix)
            src.replace(dest); path=str(dest); original=meta.get("original_name", dest.name); mime=meta.get("mime", ALLOWED.get(dest.suffix.lower()))
            if meta_path.exists(): meta_path.unlink()
    r=models.FDRRecord(institution_name=payload.institution_name.strip(),institution_id=payload.institution_id.strip(),
      bank_name=payload.bank_name.strip(),fdr_number=payload.fdr_number.strip(),deposit_amount=payload.deposit_amount,
      issue_date=payload.issue_date,maturity_date=payload.maturity_date,document_path=path,document_original_name=original,
      document_mime=mime,extracted_data=payload.extracted_data,created_by_role=actor,review_status="pending_review")
    db.add(r); db.flush()
    audit(db,actor,"record_created",r.id,{"source":"user_reviewed_submission","extracted_data_kept_separate":True})
    db.commit(); db.refresh(r)
    return serialize(r)
@app.get("/api/records/{record_id}")
def get_record(record_id:int,db:Session=Depends(get_db),actor=Depends(role)):
    r=db.get(models.FDRRecord,record_id)
    if not r: raise HTTPException(404,"FDR record not found.")
    events=db.query(models.LifecycleEvent).filter_by(record_id=record_id).order_by(desc(models.LifecycleEvent.event_date)).all()
    logs=db.query(models.AuditLog).filter_by(record_id=record_id).order_by(desc(models.AuditLog.created_at)).all()
    requests=db.query(models.ReleaseRequest).filter_by(record_id=record_id).order_by(desc(models.ReleaseRequest.created_at)).all()
    return {**serialize(r),"ocr_text":r.ocr_text,"events":[{"id":e.id,"event_type":e.event_type,"event_date":e.event_date.isoformat(),"reference":e.reference,"notes":e.notes,"created_by_role":e.created_by_role} for e in events],
      "audit_logs":[{"id":a.id,"action":a.action,"actor_role":a.actor_role,"details":a.details,"created_at":a.created_at.isoformat()} for a in logs],
      "release_requests":[{"id":x.id,"request_type":x.request_type,"amount":str(x.amount) if x.amount is not None else None,"reason":x.reason,"status":x.status,"officer_note":x.officer_note,"created_at":x.created_at.isoformat()} for x in requests]}
@app.get("/api/records/{record_id}/document")
def get_document(record_id:int,db:Session=Depends(get_db),actor=Depends(role)):
    r=db.get(models.FDRRecord,record_id)
    if not r: raise HTTPException(404,"FDR record not found.")
    if not r.document_path or not Path(r.document_path).exists(): raise HTTPException(404,"No uploaded document is attached.")
    return FileResponse(r.document_path,media_type=r.document_mime or "application/octet-stream",filename="fdr-document"+Path(r.document_path).suffix)
@app.post("/api/records/{record_id}/observations")
def observation(record_id:int,payload:schemas.ObservationInput,db:Session=Depends(get_db),actor=Depends(role)):
    r=db.get(models.FDRRecord,record_id)
    if not r: raise HTTPException(404,"FDR record not found.")
    if actor not in ("officer","admin"): raise HTTPException(403,"Only an authorized officer can record review observations.")
    r.review_status="needs_attention"; audit(db,actor,"review_observation_added",r.id,{"observation":payload.notes})
    db.commit(); return {"ok":True,"message":"Review observation recorded in the audit log."}
@app.post("/api/records/{record_id}/lifecycle")
def lifecycle(record_id:int,payload:schemas.LifecycleInput,db:Session=Depends(get_db),actor=Depends(role)):
    r=db.get(models.FDRRecord,record_id)
    if not r: raise HTTPException(404,"FDR record not found.")
    if actor not in ("officer","admin"): raise HTTPException(403,"Only an authorized officer can record lifecycle events.")
    if payload.event_type not in ("renewal","replacement","review"): raise HTTPException(422,"Unsupported lifecycle event type.")
    e=models.LifecycleEvent(record_id=record_id,event_type=payload.event_type,event_date=payload.event_date,reference=payload.reference,notes=payload.notes,created_by_role=actor)
    db.add(e); audit(db,actor,"lifecycle_event_added",r.id,{"event_type":payload.event_type,"reference":payload.reference})
    db.commit(); return {"ok":True}
@app.get("/api/alerts")
def alerts(db:Session=Depends(get_db),actor=Depends(role)):
    records=db.query(models.FDRRecord).all(); out=[]
    for r in records:
        days=(r.maturity_date-date.today()).days
        if days<0: out.append({"id":r.id,"type":"matured","severity":"critical","title":"FDR matured","description":f"{r.fdr_number} matured {abs(days)} day(s) ago.","record_id":r.id})
        elif days<=30: out.append({"id":r.id,"type":"maturity","severity":"warning","title":"Upcoming maturity","description":f"{r.fdr_number} matures in {days} day(s).","record_id":r.id})
        if r.review_status!="reviewed": out.append({"id":r.id*100000+1,"type":"review","severity":"info","title":"Review required","description":f"{r.fdr_number} has status {r.review_status.replace('_',' ')}.","record_id":r.id})
        if not r.document_path or not Path(r.document_path).exists(): out.append({"id":r.id*100000+2,"type":"document","severity":"warning","title":"Missing document","description":f"{r.fdr_number} has no attached document.","record_id":r.id})
    return out
@app.post("/api/records/{record_id}/release-requests")
def create_release(record_id:int,payload:schemas.ReleaseInput,db:Session=Depends(get_db),actor=Depends(role)):
    r=db.get(models.FDRRecord,record_id)
    if not r: raise HTTPException(404,"FDR record not found.")
    if payload.request_type not in ("release","refund"): raise HTTPException(422,"Request type must be release or refund.")
    if payload.amount is not None and payload.amount>r.deposit_amount: raise HTTPException(422,"Requested amount cannot exceed the deposit amount.")
    req=models.ReleaseRequest(record_id=record_id,request_type=payload.request_type,amount=payload.amount,reason=payload.reason,requested_by_role=actor,status="pending")
    db.add(req); db.flush(); audit(db,actor,"release_request_created",r.id,{"request_id":req.id,"request_type":payload.request_type})
    db.commit(); return {"id":req.id,"status":"pending","message":"Request submitted for officer review; no financial release was approved."}
@app.get("/api/release-requests")
def release_requests(db:Session=Depends(get_db),actor=Depends(role)):
    rows=db.query(models.ReleaseRequest).order_by(desc(models.ReleaseRequest.created_at)).all()
    return [{"id":x.id,"record_id":x.record_id,"fdr_number":db.get(models.FDRRecord,x.record_id).fdr_number,"request_type":x.request_type,"amount":str(x.amount) if x.amount is not None else None,"reason":x.reason,"status":x.status,"officer_note":x.officer_note,"created_at":x.created_at.isoformat()} for x in rows]
@app.patch("/api/release-requests/{request_id}")
def decide_release(request_id:int,payload:schemas.DecisionInput,db:Session=Depends(get_db),actor=Depends(role)):
    if actor not in ("officer","admin"): raise HTTPException(403,"Only an authorized officer can update request status.")
    if payload.status not in ("under_review","approved","rejected","returned_for_information"): raise HTTPException(422,"Unsupported decision status.")
    req=db.get(models.ReleaseRequest,request_id)
    if not req: raise HTTPException(404,"Request not found.")
    req.status=payload.status; req.officer_note=payload.officer_note
    audit(db,actor,"release_request_decision_recorded",req.record_id,{"request_id":req.id,"status":payload.status,"note":payload.officer_note})
    db.commit()
    return {"ok":True,"message":"Decision recorded for audit. This prototype does not initiate a bank transaction."}
@app.get("/api/audit")
def audit_feed(db:Session=Depends(get_db),actor=Depends(role)):
    rows=db.query(models.AuditLog).order_by(desc(models.AuditLog.created_at)).limit(100).all()
    return [{"id":a.id,"record_id":a.record_id,"actor_role":a.actor_role,"action":a.action,"details":a.details,"created_at":a.created_at.isoformat()} for a in rows]
