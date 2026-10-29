from datetime import date, datetime
from decimal import Decimal
from typing import Any
from pydantic import BaseModel, Field, ConfigDict, field_validator
class FDRInput(BaseModel):
    institution_name: str = Field(min_length=2, max_length=240)
    institution_id: str = Field(min_length=1, max_length=100)
    bank_name: str = Field(min_length=2, max_length=200)
    fdr_number: str = Field(min_length=2, max_length=160)
    deposit_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    issue_date: date
    maturity_date: date
    extracted_data: dict[str, Any] = {}
    document_token: str | None = None
    @field_validator("maturity_date")
    @classmethod
    def date_order(cls, value, info):
        issue = info.data.get("issue_date")
        if issue and value <= issue: raise ValueError("Maturity date must be after issue date.")
        return value
class FDROut(BaseModel):
    id: int
    institution_name: str
    institution_id: str
    bank_name: str
    fdr_number: str
    deposit_amount: Decimal
    issue_date: date
    maturity_date: date
    document_original_name: str | None
    record_status: str
    review_status: str
    created_by_role: str
    created_at: datetime
    extracted_data: dict[str, Any] | None
    model_config = ConfigDict(from_attributes=True)
class ObservationInput(BaseModel):
    notes: str = Field(min_length=3, max_length=3000)
class LifecycleInput(BaseModel):
    event_type: str
    event_date: date
    reference: str | None = None
    notes: str = Field(min_length=3, max_length=3000)
class ReleaseInput(BaseModel):
    request_type: str
    amount: Decimal | None = Field(default=None, gt=0)
    reason: str = Field(min_length=3, max_length=3000)
class DecisionInput(BaseModel):
    status: str
    officer_note: str = Field(min_length=3, max_length=3000)
