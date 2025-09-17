from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class SimpleResponse(BaseModel):
    account_id: Optional[str] = None
    facility_id: Optional[str] = None
    response: str
    conversation_history: List[dict]

# Tool Response Models
class AccountResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    account_id: Optional[str] = None
    account_name: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class FacilityResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    facility_id: Optional[str] = None
    facility_name: Optional[str] = None
    account_id: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class NoteResponse(BaseModel):
    success: bool
    message: str
    note_id: Optional[int] = None

class NotesListResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    notes: List[dict] = []
    total_count: int = 0
