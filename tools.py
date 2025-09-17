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
    Fetch account details from the database.
    
    Args:
        account_id: The account ID to search for
    
    Returns:
        JSON string containing structured account details or error message
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
            response = AccountResponse(
                success=True,
                message="Account details retrieved successfully",
                account_id=account.get('account_id'),
                account_name=account.get('account_name'),
                status=account.get('status'),
                created_at=str(account.get('created_at')) if account.get('created_at') else None,
                updated_at=str(account.get('updated_at')) if account.get('updated_at') else None
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
    Fetch facility details from the database.
    
    Args:
        facility_id: The facility ID to search for
        account_id: Filter facilities by account ID
    
    Returns:
        JSON string containing structured facility details or error message
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
                facility_id=facility.get('facility_id'),
                facility_name=facility.get('facility_name'),
                account_id=facility.get('account_id'),
                status=facility.get('status'),
                created_at=str(facility.get('created_at')) if facility.get('created_at') else None,
                updated_at=str(facility.get('updated_at')) if facility.get('updated_at') else None
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
            INSERT INTO notes (account_id, note_content, created_by)
            VALUES (%(account_id)s, %(note_content)s, %(created_by)s)
            RETURNING note_id, created_at
        """
        
        result = db.execute_query(
            insert_sql,
            {
                "account_id": account_id,
                "note_content": note_content.strip(),
                "created_by": "conversational_agent"
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
            SELECT note_id, note_content, created_at, created_by
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
                "created_by": note['created_by']
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
