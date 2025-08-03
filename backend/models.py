from pydantic import BaseModel
from typing import Optional

class PatientCreate(BaseModel):
    name: str
    diagnosis: Optional[str] = None
    summary: Optional[str] = None
    medication_schedule: Optional[str] = None
    call_schedule: Optional[str] = None
    automated_call_category: Optional[str] = None
