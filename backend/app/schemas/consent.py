from pydantic import BaseModel, Field
from typing import Optional

class ConsentCreate(BaseModel):
    accept: bool = Field(..., description="Must be true to accept DPDP Act 2023 consent")
    policy_version: Optional[str] = Field(None, description="Version of consent notice accepted")

class ConsentResponse(BaseModel):
    status: str
    policy_version: str
    accepted_at: str
    retention_period_minutes: int = 30
    user_id: str

class ConsentStatusResponse(BaseModel):
    has_consented: bool
    policy_version: Optional[str] = None
    accepted_at: Optional[str] = None
    retention_period_minutes: int = 30
