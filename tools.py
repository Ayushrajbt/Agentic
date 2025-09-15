from typing import Optional, Dict, Any, List
from database import db
import logging

logger = logging.getLogger(__name__)

def fetch_account_details(account_id: Optional[str] = None, account_name: Optional[str] = None) -> str:
    """
    Fetch account details from the database.
    
    Args:
        account_id: The account ID to search for
    
    Returns:
        String containing account details or error message
    """
    try:
        if not account_id and not account_name:
            return "Please provide either account_id or account_name to search for account details."
        
        # Build query based on provided parameters
        if account_id:
            query = """
                SELECT * FROM accounts 
                WHERE account_id = %(account_id)s
            """
            params = {"account_id": account_id}
        else:
            query = """
                SELECT * FROM accounts 
                WHERE account_name ILIKE %(account_name)s
            """
            params = {"account_name": f"%{account_name}%"}
        
        results = db.execute_query(query, params)
        
        if not results:
            return f"No account found with the provided criteria."
        
        if len(results) == 1:
            account = results[0]
            return f"""Account Details:
- ID: {account.get('account_id', 'N/A')}
- Name: {account.get('account_name', 'N/A')}
- Status: {account.get('status', 'N/A')}
- Created: {account.get('created_at', 'N/A')}
- Updated: {account.get('updated_at', 'N/A')}
- Additional Info: {account.get('description', 'N/A')}"""
        else:
            # Multiple accounts found
            account_list = []
            for account in results:
                account_list.append(f"- {account.get('account_name', 'N/A')} (ID: {account.get('account_id', 'N/A')})")
            
            return f"Found {len(results)} accounts matching your criteria:\n" + "\n".join(account_list)
            
    except Exception as e:
        logger.error(f"Error fetching account details: {e}")
        return f"Error fetching account details: {str(e)}"

def fetch_facility_details(facility_id: Optional[str] = None, facility_name: Optional[str] = None, account_id: Optional[str] = None) -> str:
    """
    Fetch facility details from the database.
    
    Args:
        facility_id: The facility ID to search for
        account_id: Filter facilities by account ID
    
    Returns:
        String containing facility details or error message
    """
    try:
        if not facility_id and not facility_name and not account_id:
            return "Please provide facility_id, facility_name, or account_id to search for facility details."
        
        # Build query based on provided parameters
        conditions = []
        params = {}
        
        if facility_id:
            conditions.append("facility_id = %(facility_id)s")
            params["facility_id"] = facility_id
        
        if facility_name:
            conditions.append("facility_name ILIKE %(facility_name)s")
            params["facility_name"] = f"%{facility_name}%"
        
        if account_id:
            conditions.append("account_id = %(account_id)s")
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
            return f"No facilities found with the provided criteria."
        
        if len(results) == 1:
            facility = results[0]
            return f"""Facility Details:
- ID: {facility.get('facility_id', 'N/A')}
- Name: {facility.get('facility_name', 'N/A')}
- Account: {facility.get('account_name', 'N/A')} (ID: {facility.get('account_id', 'N/A')})
- Status: {facility.get('status', 'N/A')}
- Location: {facility.get('location', 'N/A')}
- Type: {facility.get('facility_type', 'N/A')}
- Created: {facility.get('created_at', 'N/A')}
- Updated: {facility.get('updated_at', 'N/A')}
- Additional Info: {facility.get('description', 'N/A')}"""
        else:
            # Multiple facilities found
            facility_list = []
            for facility in results:
                facility_list.append(f"- {facility.get('facility_name', 'N/A')} (ID: {facility.get('facility_id', 'N/A')}) - Account: {facility.get('account_name', 'N/A')}")
            
            return f"Found {len(results)} facilities matching your criteria:\n" + "\n".join(facility_list)
            
    except Exception as e:
        logger.error(f"Error fetching facility details: {e}")
        return f"Error fetching facility details: {str(e)}"


def save_note(note_content: str, account_id: str) -> str:
    """
    Save a note for a specific account.
    
    Args:
        note_content: The content of the note to save
        account_id: The account ID to associate the note with
    
    Returns:
        String confirming the note was saved or error message
    """
    try:
        if not note_content.strip():
            return "Note content cannot be empty."
        
        if not account_id.strip():
            return "Account ID is required to save a note."
        
        # Check if account exists
        account_exists = db.execute_scalar(
            "SELECT COUNT(*) FROM accounts WHERE account_id = %(account_id)s",
            {"account_id": account_id}
        )
        
        if account_exists == 0:
            return f"Account with ID '{account_id}' not found. Cannot save note."
        
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
            
            return f"""✅ Note saved successfully!
- Note ID: {note_id}
- Account ID: {account_id}
- Content: {note_content.strip()}
- Created: {created_at}
- Created by: Conversational Agent"""
        else:
            return "Failed to save note. Please try again."
            
    except Exception as e:
        logger.error(f"Error saving note: {e}")
        return f"Error saving note: {str(e)}"

def get_notes(account_id: str, limit: int = 10) -> str:
    """
    Get notes for a specific account.
    
    Args:
        account_id: The account ID to get notes for
        limit: Maximum number of notes to return (default: 10)
    
    Returns:
        String containing the notes or error message
    """
    try:
        if not account_id.strip():
            return "Account ID is required to retrieve notes."
        
        # Check if account exists
        account_exists = db.execute_scalar(
            "SELECT COUNT(*) FROM accounts WHERE account_id = %(account_id)s",
            {"account_id": account_id}
        )
        
        if account_exists == 0:
            return f"Account with ID '{account_id}' not found."
        
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
            return f"No notes found for account '{account_id}'."
        
        # Format the notes
        notes_list = []
        for note in notes:
            notes_list.append(f"""📝 Note #{note['note_id']}
   Content: {note['note_content']}
   Created: {note['created_at']}
   Created by: {note['created_by']}""")
        
        return f"""📋 Notes for Account {account_id}:
{chr(10).join(notes_list)}

Total notes: {len(notes)}"""
        
    except Exception as e:
        logger.error(f"Error getting notes: {e}")
        return f"Error retrieving notes: {str(e)}"
