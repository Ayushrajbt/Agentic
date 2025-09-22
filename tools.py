from typing import Optional, Dict, Any, List
from langchain_core.tools import tool
from database import db
import logging
import json
from models import AccountResponse, FacilityResponse, NoteResponse, NotesListResponse

logger = logging.getLogger(__name__)

@tool
def fetch_account_details(account_id: str) -> str:
    """
    Fetch comprehensive account details from the database including financial, rewards, and quarter information.
    
    Use this tool when users ask about:
    - Account information (status, balance, rewards, quarter dates, tiers, etc.)
    - Quarter end dates (account-specific quarters, NOT calendar quarters)
    - Rewards and loyalty information (tiers, points, free vials, etc.)
    - Financial information (balances, amounts due, invoices, etc.)
    - Account overview or summary
    - Any account-specific data or metrics
    
    Args:
        account_id: The account ID to search for
    
    Returns:
        JSON string containing structured account details with facilities list, financial data, rewards info, and quarter end date
    """
    try:
        if not account_id or not account_id.strip():
            response = AccountResponse(
                success=False,
                message="Please provide account_id to search for account details."
            )
            return response.model_dump_json()
        
        # Build query based on provided parameters
        query = """
            SELECT * FROM accounts 
            WHERE account_id = %(account_id)s
        """
        params = {"account_id": account_id}
        
        results = db.execute_query(query, params)
        
        if not results:
            response = AccountResponse(
                success=False,
                message=f"No account found with account_id '{account_id}'."
            )
            return response.model_dump_json()
        
        if len(results) == 1:
            account = results[0]
            
            # Get facilities for this account
            facilities_query = """
                SELECT facility_id as id, facility_name as name, status, 
                       has_signed_medical_liability_agreement,
                       shipping_address_line1, shipping_address_line2,
                       shipping_address_city, shipping_address_state,
                       shipping_address_zip, shipping_address_commercial
                FROM facilities 
                WHERE account_id = %(account_id)s
            """
            facilities = db.execute_query(facilities_query, {"account_id": account.get('account_id')})
            
            response = AccountResponse(
                success=True,
                message="Account details retrieved successfully",
                # Basic account info
                account_id=account.get('account_id'),
                name=account.get('name') or account.get('account_name'),  # Use name field, fallback to account_name
                status=account.get('status'),
                is_tna=account.get('is_tna'),
                created_at=str(account.get('created_at')) if account.get('created_at') else None,
                pricing_model=account.get('pricing_model'),
                
                # Address fields
                address_line1=account.get('address_line1'),
                address_line2=account.get('address_line2'),
                address_city=account.get('address_city'),
                address_state=account.get('address_state'),
                address_postal_code=account.get('address_postal_code'),
                address_country=account.get('address_country'),
                
                # Facilities list
                facilities=facilities,
                
                # Financial fields
                total_amount_due=float(account.get('total_amount_due')) if account.get('total_amount_due') is not None else None,
                total_amount_due_this_week=float(account.get('total_amount_due_this_week')) if account.get('total_amount_due_this_week') is not None else None,
                invoice_id=account.get('invoice_id'),
                invoice_amount=float(account.get('invoice_amount')) if account.get('invoice_amount') is not None else None,
                invoice_due_date=account.get('invoice_due_date'),
                current_balance=float(account.get('current_balance')) if account.get('current_balance') is not None else None,
                pending_balance=float(account.get('pending_balance')) if account.get('pending_balance') is not None else None,
                
                # Rewards/Loyalty fields
                points_earned_this_quarter=account.get('points_earned_this_quarter'),
                current_tier=account.get('current_tier'),
                next_tier=account.get('next_tier'),
                points_to_next_tier=account.get('points_to_next_tier'),
                quarter_end_date=str(account.get('quarter_end_date')) if account.get('quarter_end_date') else None,
                free_vials_available=account.get('free_vials_available'),
                rewards_required_for_next_free_vial=account.get('rewards_required_for_next_free_vial'),
                rewards_redeemed_towards_next_free_vial=account.get('rewards_redeemed_towards_next_free_vial'),
                rewards_status=account.get('rewards_status'),
                rewards_updated_at=str(account.get('rewards_updated_at')) if account.get('rewards_updated_at') else None,
                evolux_level=account.get('evolux_level')
            )
            return response.model_dump_json()
        else:
            # Multiple accounts found
            account_list = []
            for account in results:
                account_list.append(f"- {account.get('account_name', 'N/A')} (ID: {account.get('account_id', 'N/A')})")
            
            response = AccountResponse(
                success=True,
                message=f"Found {len(results)} accounts matching your criteria:\n" + "\n".join(account_list)
            )
            return response.model_dump_json()
            
    except Exception as e:
        logger.error(f"Error fetching account details: {e}")
        response = AccountResponse(
            success=False,
            message=f"Error fetching account details: {str(e)}"
        )
        return response.model_dump_json()

@tool
def fetch_facility_details(facility_id: Optional[str] = None, account_id: Optional[str] = None) -> str:
    """
    Fetch comprehensive facility details from the database including medical license, agreements, and account information.
    
    Use this tool when users ask about:
    - Facility information (status, name, address, etc.)
    - Medical license details (provider, expiration, status, etc.)
    - License expiration dates and calculations
    - Medical agreements and signing status
    - Facility-specific data or metrics
    - License provider information
    - Agreement status and signing dates
    
    Args:
        facility_id: The facility ID to search for
        account_id: Filter facilities by account ID
    
    Returns:
        JSON string containing structured facility details with medical license info, agreement status, and account details
    """
    try:
        if not facility_id and not account_id:
            response = FacilityResponse(
                success=False,
                message="Please provide facility_id or account_id to search for facility details."
            )
            return response.model_dump_json()
        
        # Build query based on provided parameters
        conditions = []
        params = {}
        
        if facility_id:
            conditions.append("facility_id = %(facility_id)s")
            params["facility_id"] = facility_id
        
        if account_id:
            conditions.append("f.account_id = %(account_id)s")
            params["account_id"] = account_id
        
        where_clause = " AND ".join(conditions)
        query = f"""
            SELECT f.*, a.account_name 
            FROM facilities f
            LEFT JOIN accounts a ON f.account_id = a.account_id
            WHERE {where_clause}
        """
        
        results = db.execute_query(query, params)
        
        if not results:
            response = FacilityResponse(
                success=False,
                message="No facilities found with the provided criteria."
            )
            return response.model_dump_json()
        
        if len(results) == 1:
            facility = results[0]
            response = FacilityResponse(
                success=True,
                message="Facility details retrieved successfully",
                id=facility.get('facility_id'),
                name=facility.get('facility_name'),
                status=facility.get('status'),
                
                # Medical license fields
                has_signed_medical_liability_agreement=facility.get('has_signed_medical_liability_agreement'),
                medical_license_id=facility.get('medical_license_id'),
                medical_license_state=facility.get('medical_license_state'),
                medical_license_number=facility.get('medical_license_number'),
                medical_license_involvement=facility.get('medical_license_involvement'),
                medical_license_expiration_date=str(facility.get('medical_license_expiration_date')) if facility.get('medical_license_expiration_date') else None,
                medical_license_is_expired=facility.get('medical_license_is_expired'),
                medical_license_status=facility.get('medical_license_status'),
                medical_license_owner_first_name=facility.get('medical_license_owner_first_name'),
                medical_license_owner_last_name=facility.get('medical_license_owner_last_name'),
                
                # Account information
                account_id=facility.get('account_id'),
                account_name=facility.get('account_name'),
                account_status=facility.get('account_status'),
                account_has_signed_financial_agreement=facility.get('account_has_signed_financial_agreement'),
                account_has_accepted_jet_terms=facility.get('account_has_accepted_jet_terms'),
                
                # Agreement fields
                agreement_status=facility.get('agreement_status'),
                agreement_signed_at=str(facility.get('agreement_signed_at')) if facility.get('agreement_signed_at') else None,
                agreement_type=facility.get('agreement_type'),
                
                # Address fields
                shipping_address_line1=facility.get('shipping_address_line1'),
                shipping_address_line2=facility.get('shipping_address_line2'),
                shipping_address_city=facility.get('shipping_address_city'),
                shipping_address_state=facility.get('shipping_address_state'),
                shipping_address_zip=facility.get('shipping_address_zip'),
                shipping_address_commercial=facility.get('shipping_address_commercial'),
                sponsored=facility.get('sponsored')
            )
            return response.model_dump_json()
        else:
            # Multiple facilities found
            facility_list = []
            for facility in results:
                facility_list.append(f"- {facility.get('facility_name', 'N/A')} (ID: {facility.get('facility_id', 'N/A')}) - Account: {facility.get('account_name', 'N/A')}")
            
            response = FacilityResponse(
                success=True,
                message=f"Found {len(results)} facilities matching your criteria:\n" + "\n".join(facility_list)
            )
            return response.model_dump_json()
            
    except Exception as e:
        logger.error(f"Error fetching facility details: {e}")
        response = FacilityResponse(
            success=False,
            message=f"Error fetching facility details: {str(e)}"
        )
        return response.model_dump_json()


@tool
def save_note(note_content: str, account_id: str) -> str:
    """
    Save a note for a specific account.
    
    Args:
        note_content: The content of the note to save
        account_id: The account ID to associate the note with
    
    Returns:
        JSON string confirming the note was saved or error message
    """
    try:
        if not note_content.strip():
            response = NoteResponse(
                success=False,
                message="Note content cannot be empty."
            )
            return response.model_dump_json()
        
        if not account_id.strip():
            response = NoteResponse(
                success=False,
                message="Account ID is required to save a note."
            )
            return response.model_dump_json()
        
        # Check if account exists
        account_exists = db.execute_scalar(
            "SELECT COUNT(*) FROM accounts WHERE account_id = %(account_id)s",
            {"account_id": account_id}
        )
        
        if account_exists == 0:
            response = NoteResponse(
                success=False,
                message=f"Account with ID '{account_id}' not found. Cannot save note."
            )
            return response.model_dump_json()
        
        # Insert the note
        insert_sql = """
            INSERT INTO notes (account_id, note_content)
            VALUES (%(account_id)s, %(note_content)s)
            RETURNING note_id, created_at
        """
        
        result = db.execute_query(
            insert_sql,
            {
                "account_id": account_id,
                "note_content": note_content.strip(),
            }
        )
        
        if result:
            note_id = result[0]['note_id']
            created_at = result[0]['created_at']
            
            response = NoteResponse(
                success=True,
                message=f"Note saved successfully! Note ID: {note_id}, Created: {created_at}",
                note_id=note_id
            )
            return response.model_dump_json()
        else:
            response = NoteResponse(
                success=False,
                message="Failed to save note. Please try again."
            )
            return response.model_dump_json()
            
    except Exception as e:
        logger.error(f"Error saving note: {e}")
        response = NoteResponse(
            success=False,
            message=f"Error saving note: {str(e)}"
        )
        return response.model_dump_json()

@tool
def get_notes(account_id: str, limit: int = 10) -> str:
    """
    Get notes for a specific account. 
    
    CRITICAL: If user asks for "summary" or "summarize", do NOT list individual notes. Instead, synthesize the information into a brief overview highlighting main themes and key points.
    
    Args:
        account_id: The account ID to get notes for
        limit: Maximum number of notes to return (default: 10)
    
    Returns:
        JSON string containing the notes or error message
    """
    try:
        if not account_id.strip():
            response = NotesListResponse(
                success=False,
                message="Account ID is required to retrieve notes."
            )
            return response.model_dump_json()
        
        # Check if account exists
        account_exists = db.execute_scalar(
            "SELECT COUNT(*) FROM accounts WHERE account_id = %(account_id)s",
            {"account_id": account_id}
        )
        
        if account_exists == 0:
            response = NotesListResponse(
                success=False,
                message=f"Account with ID '{account_id}' not found."
            )
            return response.model_dump_json()
        
        # Get notes for the account
        notes_query = """
            SELECT note_id, note_content, created_at
            FROM notes 
            WHERE account_id = %(account_id)s
            ORDER BY created_at DESC
            LIMIT %(limit)s
        """
        
        notes = db.execute_query(notes_query, {"account_id": account_id, "limit": limit})
        
        if not notes:
            response = NotesListResponse(
                success=True,
                message=f"No notes found for account '{account_id}'.",
                notes=[],
                total_count=0
            )
            return response.model_dump_json()
        
        # Format the notes
        notes_list = []
        for note in notes:
            notes_list.append({
                "note_id": note['note_id'],
                "note_content": note['note_content'],
                "created_at": str(note['created_at']),
            })
        
        response = NotesListResponse(
            success=True,
            message=f"Retrieved {len(notes)} notes for account {account_id}",
            notes=notes_list,
            total_count=len(notes)
        )
        return response.model_dump_json()
        
    except Exception as e:
        logger.error(f"Error getting notes: {e}")
        response = NotesListResponse(
            success=False,
            message=f"Error retrieving notes: {str(e)}"
        )
        return response.model_dump_json()
