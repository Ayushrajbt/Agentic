from pydantic import BaseModel
from typing import Optional, List

class SimpleResponse(BaseModel):
    account_id: Optional[str] = None
    facility_id: Optional[str] = None
    response: str
    conversation_history: List[dict]
