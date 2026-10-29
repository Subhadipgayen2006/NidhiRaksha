from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, Text, ForeignKey, UniqueConstraint, func, JSON
from sqlalchemy.orm import relationship
from app.database import Base
class FDRRecord(Base):
    __tablename__ = "fdr_records"
    __table_args__ = (UniqueConstraint("institution_id", "fdr_number", name="uq_institution_fdr"),)
    id = Column(Integer, primary_key=True)
    institution_name = Column(String(240), nullable=False)
    institution_id = Column(String(100), nullable=False)
    bank_name = Column(String(200), nullable=False)
    fdr_number = Column(String(160), nullable=False, index=True)
    deposit_amount = Column(Numeric(14,2), nullable=False)
    issue_date = Column(Date, nullable=False)
    maturity_date = Column(Date, nullable=False)
    document_path = Column(String(500))
    document_original_name = Column(String(255))
    document_mime = Column(String(100))
    ocr_text = Column(Text)
    extracted_data = Column(JSON)
    record_status = Column(String(40), nullable=False, default="active")
    review_status = Column(String(40), nullable=False, default="pending_review")
    created_by_role = Column(String(40), nullable=False, default="institution")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    events = relationship("LifecycleEvent", back_populates="record", cascade="all, delete-orphan")
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    record_id = Column(Integer, ForeignKey("fdr_records.id", ondelete="SET NULL"))
    actor_role = Column(String(40), nullable=False)
    action = Column(String(100), nullable=False)
    details = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
class LifecycleEvent(Base):
    __tablename__ = "lifecycle_events"
    id = Column(Integer, primary_key=True)
    record_id = Column(Integer, ForeignKey("fdr_records.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(40), nullable=False)
    event_date = Column(Date, nullable=False)
    reference = Column(String(200))
    notes = Column(Text, nullable=False)
    created_by_role = Column(String(40), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    record = relationship("FDRRecord", back_populates="events")
class ReleaseRequest(Base):
    __tablename__ = "release_requests"
    id = Column(Integer, primary_key=True)
    record_id = Column(Integer, ForeignKey("fdr_records.id", ondelete="CASCADE"), nullable=False)
    request_type = Column(String(40), nullable=False)
    amount = Column(Numeric(14,2))
    reason = Column(Text, nullable=False)
    status = Column(String(40), nullable=False, default="pending")
    requested_by_role = Column(String(40), nullable=False)
    officer_note = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
