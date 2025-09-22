from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime

class SimpleResponse(BaseModel):
    account_id: Optional[str] = None
    facility_id: Optional[str] = None
    response: str
    conversation_id: Optional[str] = None

# Tool Response Models
class AccountResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    # Basic account info
    account_id: Optional[str] = None
    name: Optional[str] = None
    status: Optional[str] = None
    is_tna: Optional[bool] = None
    created_at: Optional[str] = None
    pricing_model: Optional[str] = None
    
    # Address fields
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    address_city: Optional[str] = None
    address_state: Optional[str] = None
    address_postal_code: Optional[str] = None
    address_country: Optional[str] = None
    
    # Facilities list
    facilities: Optional[List[dict]] = None
    
    # Financial fields
    total_amount_due: Optional[float] = None
    total_amount_due_this_week: Optional[float] = None
    invoice_id: Optional[str] = None
    invoice_amount: Optional[float] = None
    invoice_due_date: Optional[str] = None
    current_balance: Optional[float] = None
    pending_balance: Optional[float] = None
    
    # Rewards/Loyalty fields
    points_earned_this_quarter: Optional[int] = None
    current_tier: Optional[str] = None
    next_tier: Optional[str] = None
    points_to_next_tier: Optional[int] = None
    quarter_end_date: Optional[str] = None
    free_vials_available: Optional[int] = None
    rewards_required_for_next_free_vial: Optional[int] = None
    rewards_redeemed_towards_next_free_vial: Optional[int] = None
    rewards_status: Optional[str] = None
    rewards_updated_at: Optional[str] = None
    evolux_level: Optional[str] = None

class FacilityResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    id: Optional[str] = None
    name: Optional[str] = None
    status: Optional[str] = None
    
    # Medical license fields
    has_signed_medical_liability_agreement: Optional[bool] = None
    medical_license_id: Optional[str] = None
    medical_license_state: Optional[str] = None
    medical_license_number: Optional[str] = None
    medical_license_involvement: Optional[str] = None
    medical_license_expiration_date: Optional[str] = None
    medical_license_is_expired: Optional[bool] = None
    medical_license_status: Optional[str] = None
    medical_license_owner_first_name: Optional[str] = None
    medical_license_owner_last_name: Optional[str] = None
    
    # Account information
    account_id: Optional[str] = None
    account_name: Optional[str] = None
    account_status: Optional[str] = None
    account_has_signed_financial_agreement: Optional[bool] = None
    account_has_accepted_jet_terms: Optional[bool] = None
    
    # Agreement fields
    agreement_status: Optional[str] = None
    agreement_signed_at: Optional[str] = None
    agreement_type: Optional[str] = None
    
    # Address fields
    shipping_address_line1: Optional[str] = None
    shipping_address_line2: Optional[str] = None
    shipping_address_city: Optional[str] = None
    shipping_address_state: Optional[str] = None
    shipping_address_zip: Optional[str] = None
    shipping_address_commercial: Optional[bool] = None
    sponsored: Optional[bool] = None

class NoteResponse(BaseModel):
    success: bool
    message: str
    note_id: Optional[int] = None

class NotesListResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    notes: List[dict] = []
    total_count: int = 0

# Chat Request Model
class ChatRequest(BaseModel):
    message: str
    account_id: Optional[str] = None
    facility_id: Optional[str] = None
    conversation_id: Optional[str] = None
    
    @validator('facility_id', always=True)
    def validate_context(cls, v, values):
        account_id = values.get('account_id')
        facility_id = v
        
        if not account_id and not facility_id:
            raise ValueError('Either account_id or facility_id is required')
        return v