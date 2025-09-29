from typing import Optional, Dict, Any, List
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from database import db
import logging
import json
from models import AccountResponse, FacilityResponse, NoteResponse, NotesListResponse, FacilityInfo, NoteInfo

logger = logging.getLogger(__name__)

@tool
def fetch_account_details(config: RunnableConfig) -> str:
    """
    Fetch comprehensive account details from the database including financial, rewards, quarter information, and facility medical license details.
    
    CROSS-REFERENCE INTELLIGENCE:
    - If user asks for account information but only facility_id is provided, automatically get the account_id from the facility
    - If both account_id and facility_id are provided, prioritize account_id but verify they match
    - If neither is provided, return an error asking for account_id
    
    Use this tool when users ask about:
    - Account information (status, balance, rewards, quarter dates, tiers, etc.)
    - Quarter end dates (account-specific quarters, NOT calendar quarters)
    - Rewards and loyalty information (tiers, points, free vials, etc.)
    - Financial information (balances, amounts due, invoices, etc.)
    - Account overview or summary
    - Medical license status, expiration dates, or license provider information
    - Facility medical license details (status, owner, expiration, etc.)
    - Any account-specific data or metrics
        
    Args:
        config: A configuration object containing 'account_id', 'facility_id', and 'user_id'
    
    Returns:
        JSON string containing structured account details with facilities list (including medical license data), financial data, rewards info, and quarter end date
    """
    try:
        # Extract IDs from RunnableConfig
        account_id = config.get("configurable", {}).get("account_id")
        facility_id = config.get("configurable", {}).get("facility_id")
        user_id = config.get("configurable", {}).get("user_id")
        
        print(f"Fetching account details with account_id: {account_id}, facility_id: {facility_id}, user_id: {user_id}")
        
        # CROSS-REFERENCE INTELLIGENCE: Handle facility-to-account resolution
        if not account_id and facility_id:
            # User wants account info but only facility_id is provided - get account_id from facility
            print(f"Cross-reference: Getting account_id from facility {facility_id}")
            facility_query = """
                SELECT account_id FROM facilities WHERE facility_id = %(facility_id)s
            """
            facility_result = db.execute_query(facility_query, {"facility_id": facility_id})
            
            if facility_result:
                account_id = facility_result[0]['account_id']
                print(f"Cross-reference: Found account_id {account_id} for facility {facility_id}")
            else:
                response = AccountResponse(
                    success=False,
                    message=f"Facility '{facility_id}' not found. Cannot determine account information."
                )
                return response.model_dump_json()
        
        elif account_id and facility_id:
            # Both provided - verify they match
            facility_query = """
                SELECT account_id FROM facilities WHERE facility_id = %(facility_id)s
            """
            facility_result = db.execute_query(facility_query, {"facility_id": facility_id})
            
            if facility_result:
                facility_account_id = facility_result[0]['account_id']
                if facility_account_id != account_id:
                    response = AccountResponse(
                        success=False,
                        message=f"Account ID '{account_id}' does not match facility '{facility_id}' which belongs to account '{facility_account_id}'."
                    )
                    return response.model_dump_json()
                print(f"Verified: Account {account_id} matches facility {facility_id}")
            else:
                response = AccountResponse(
                    success=False,
                    message=f"Facility '{facility_id}' not found."
                )
                return response.model_dump_json()
        
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
            
            # Get facilities for this account with medical license details
            facilities_query = """
                SELECT facility_id as id, facility_name as name, status, 
                       has_signed_medical_liability_agreement,
                       medical_license_id, medical_license_state, medical_license_number,
                       medical_license_involvement, medical_license_expiration_date,
                       medical_license_is_expired, medical_license_status,
                       medical_license_owner_first_name, medical_license_owner_last_name,
                       agreement_status, agreement_signed_at, agreement_type,
                       shipping_address_line1, shipping_address_line2,
                       shipping_address_city, shipping_address_state,
                       shipping_address_zip, shipping_address_commercial,
                       sponsored, account_has_signed_financial_agreement,
                       account_has_accepted_jet_terms
                FROM facilities 
                WHERE account_id = %(account_id)s
            """
            facilities_data = db.execute_query(facilities_query, {"account_id": account.get('account_id')})
            
            # Convert facilities to structured format
            facilities = []
            if facilities_data:
                for facility in facilities_data:
                    facility_info = FacilityInfo(
                        id=facility.get('id'),
                        name=facility.get('name'),
                        status=facility.get('status')
                    )
                    facilities.append(facility_info)
            
            response = AccountResponse(
                success=True,
                message="Account details retrieved successfully",
                # Basic account info
                account_id=account.get('account_id'),
                name=account.get('account_name'),  # Use account_name field from database
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
def fetch_facility_details(config: RunnableConfig) -> str:
    """
    Fetch comprehensive facility details from the database including medical license, agreements, and account information.
    
    IMPORTANT: This tool should ONLY be used when:
    1. User asks for facility details/overview/summary
    2. User asks for information about a specific facility ID
    3. User asks for facility-specific information (medical license, agreements, etc.)
    
    CROSS-REFERENCE INTELLIGENCE:
    - If user asks for facility information but only account_id is provided, get all facilities for that account
    - If both account_id and facility_id are provided, prioritize facility_id but verify they match
    - If neither is provided, return an error asking for facility_id or account_id
    
    CRITICAL FALLBACK RULE:
    - If user asks for a specific facility ID (e.g., "Show me facility F-123456") but that facility doesn't exist or doesn't match the context facility_id, return an error message saying "Sorry, I don't have information for the Facility ID provided by user"
    - DO NOT return information for a different facility just because it exists in the context
    - Always prioritize the specific facility ID mentioned by the user over context facility_id
    
    Use this tool when users ask about:
    - Facility information (status, name, address, etc.)
    - Medical license details (provider, expiration, status, etc.)
    - License expiration dates and calculations
    - Medical agreements and signing status
    - Facility-specific data or metrics
    - License provider information
    - Agreement status and signing dates
    - Medical license owner details
    - License number and state information
    
    Args:
        config: A configuration object containing 'account_id', 'facility_id', and 'user_id'
    
    Returns:
        JSON string containing structured facility details with medical license info, agreement status, and account details
    """
    try:
        # Extract IDs from RunnableConfig
        account_id = config.get("configurable", {}).get("account_id")
        facility_id = config.get("configurable", {}).get("facility_id")
        user_id = config.get("configurable", {}).get("user_id")
        
        print(f"Fetching facility details with account_id: {account_id}, facility_id: {facility_id}, user_id: {user_id}")
        
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
            SELECT f.*, a.account_name, a.status as account_status
            FROM facilities f
            LEFT JOIN accounts a ON f.account_id = a.account_id
            WHERE {where_clause}
        """
        
        
        results = db.execute_query(query, params)
        logger.info(f"AAAAAAAAAAAAAAAAAAAAAAAAA: {results}")
        if not results:
            response = FacilityResponse(
                success=False,
                message="No facilities found with the provided criteria."
            )
            return response.model_dump_json()
        
        if len(results) == 1:
            logger.info("This belongs to single result", results)
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
            logger.info("This belongs to Multiple result", results)
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
def save_note(config: RunnableConfig) -> str:
    """
    Save a note for a specific account or facility and user.
    
    IMPORTANT: This tool expects the note content to be already extracted from the user message.
    The agent should extract the actual note content (e.g., "I am Ayush" from "Save this note: I am Ayush")
    and pass it as note_content in the RunnableConfig.
    
    Args:
        config: A configuration object containing 'user_id', 'account_id', 'facility_id', and 'note_content'
               where note_content should be the extracted content without any prefixes like "Save this note:"
    
    Returns:
        JSON string confirming the note was saved or error message
    """
    try:
        # Extract parameters from RunnableConfig
        note_content = config.get("configurable", {}).get("note_content")
        user_id = config.get("configurable", {}).get("user_id")
        account_id = config.get("configurable", {}).get("account_id")
        facility_id = config.get("configurable", {}).get("facility_id")
        
        print(f"Saving note with user_id: {user_id}, account_id: {account_id}, facility_id: {facility_id}")
        print(f"Note content: {note_content}")
        
        # Note content should be extracted by the agent from user message
        # The agent should pass the actual note content, not the full message
        
        if not note_content or not note_content.strip():
            response = NoteResponse(
                success=False,
                message="Note content cannot be empty. Please provide the note content to save."
            )
            return response.model_dump_json()
        
        if not user_id or not user_id.strip():
            response = NoteResponse(
                success=False,
                message="User ID is required to save a note."
            )
            return response.model_dump_json()
        
        # At least one of account_id or facility_id must be provided
        if not account_id and not facility_id:
            response = NoteResponse(
                success=False,
                message="Either account_id or facility_id is required to save a note."
            )
            return response.model_dump_json()
        
        # Check if account exists (if account_id provided)
        if account_id:
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
        
        # Check if facility exists (if facility_id provided)
        if facility_id:
            facility_exists = db.execute_scalar(
                "SELECT COUNT(*) FROM facilities WHERE facility_id = %(facility_id)s",
                {"facility_id": facility_id}
            )
            
            if facility_exists == 0:
                response = NoteResponse(
                    success=False,
                    message=f"Facility with ID '{facility_id}' not found. Cannot save note."
                )
                return response.model_dump_json()
        
        # Handle flexible account/facility relationships:
        # - If only account_id: save with account_id, facility_id = NULL
        # - If only facility_id: save with facility_id, account_id = NULL  
        # - If both: save with both account_id and facility_id
        
        # Convert empty strings to None for proper NULL handling
        account_id = account_id if account_id and account_id.strip() else None
        facility_id = facility_id if facility_id and facility_id.strip() else None
        
        # Insert the note
        insert_sql = """
            INSERT INTO notes (account_id, facility_id, user_id, note_content)
            VALUES (%(account_id)s, %(facility_id)s, %(user_id)s, %(note_content)s)
            RETURNING note_id, created_at
        """
        
        result = db.execute_query(
            insert_sql,
            {
                "account_id": account_id,
                "facility_id": facility_id,
                "user_id": user_id.strip(),
                "note_content": note_content.strip(),
            }
        )
        
        if result:
            note_id = result[0]['note_id']
            created_at = result[0]['created_at']
            
            # Create appropriate context message based on what was provided
            if account_id and facility_id:
                context = f"Account: {account_id} and Facility: {facility_id}"
            elif account_id:
                context = f"Account: {account_id}"
            else:
                context = f"Facility: {facility_id}"
                
            response = NoteResponse(
                success=True,
                message=f"Note saved successfully for {context}! Note ID: {note_id}, Created: {created_at}",
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
def get_notes(config: RunnableConfig) -> str:
    """
    Get notes for a specific account or facility and user. 
    
    CRITICAL: If user asks for "summary" or "summarize", do NOT list individual notes. Instead, synthesize the information into a brief overview highlighting main themes and key points.
    
    Args:
        config: A configuration object containing 'user_id', 'account_id', 'facility_id', and 'limit'
    
    Returns:
        JSON string containing the notes or error message
    """
    try:
        # Extract parameters from RunnableConfig
        user_id = config.get("configurable", {}).get("user_id")
        account_id = config.get("configurable", {}).get("account_id")
        facility_id = config.get("configurable", {}).get("facility_id")
        limit = config.get("configurable", {}).get("limit", 10)
        
        print(f"Getting notes with user_id: {user_id}, account_id: {account_id}, facility_id: {facility_id}, limit: {limit}")
        
        if not user_id or not user_id.strip():
            response = NotesListResponse(
                success=False,
                message="User ID is required to retrieve notes."
            )
            return response.model_dump_json()
        
        # At least one of account_id or facility_id must be provided
        if not account_id and not facility_id:
            response = NotesListResponse(
                success=False,
                message="Either account_id or facility_id is required to retrieve notes."
            )
            return response.model_dump_json()
        
        # Check if account exists (if account_id provided)
        if account_id:
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
        
        # Check if facility exists (if facility_id provided)
        if facility_id:
            facility_exists = db.execute_scalar(
                "SELECT COUNT(*) FROM facilities WHERE facility_id = %(facility_id)s",
                {"facility_id": facility_id}
            )
            
            if facility_exists == 0:
                response = NotesListResponse(
                    success=False,
                    message=f"Facility with ID '{facility_id}' not found."
                )
                return response.model_dump_json()
        
        # Convert empty strings to None for proper NULL handling
        account_id = account_id if account_id and account_id.strip() else None
        facility_id = facility_id if facility_id and facility_id.strip() else None
        
        # Build query based on what's provided
        if account_id and facility_id:
            # Both provided - get notes for both account and facility
            notes_query = """
                SELECT note_id, note_content, user_id, created_at, account_id, facility_id
                FROM notes 
                WHERE ((account_id = %(account_id)s AND facility_id IS NULL) OR 
                       (facility_id = %(facility_id)s AND account_id IS NULL) OR
                       (account_id = %(account_id)s AND facility_id = %(facility_id)s)) 
                AND user_id = %(user_id)s
                ORDER BY created_at DESC
                LIMIT %(limit)s
            """
            params = {"account_id": account_id, "facility_id": facility_id, "user_id": user_id.strip(), "limit": limit}
        elif account_id:
            # Only account_id provided - get account-level notes (facility_id IS NULL)
            notes_query = """
                SELECT note_id, note_content, user_id, created_at, account_id, facility_id
                FROM notes 
                WHERE account_id = %(account_id)s AND facility_id IS NULL AND user_id = %(user_id)s
                ORDER BY created_at DESC
                LIMIT %(limit)s
            """
            params = {"account_id": account_id, "user_id": user_id.strip(), "limit": limit}
        else:
            # Only facility_id provided - get facility-level notes (account_id IS NULL)
            notes_query = """
                SELECT note_id, note_content, user_id, created_at, account_id, facility_id
                FROM notes 
                WHERE facility_id = %(facility_id)s AND account_id IS NULL AND user_id = %(user_id)s
                ORDER BY created_at DESC
                LIMIT %(limit)s
            """
            params = {"facility_id": facility_id, "user_id": user_id.strip(), "limit": limit}
        
        notes = db.execute_query(notes_query, params)
        
        if not notes:
            # Create appropriate context message
            if account_id and facility_id:
                context = f"account '{account_id}' and facility '{facility_id}'"
            elif account_id:
                context = f"account '{account_id}'"
            else:
                context = f"facility '{facility_id}'"
                
            response = NotesListResponse(
                success=True,
                message=f"No notes found for {context}.",
                notes=[],
                total_count=0
            )
            return response.model_dump_json()
        
        # Format the notes
        notes_list = []
        for note in notes:
            note_info = NoteInfo(
                note_id=note['note_id'],
                note_content=note['note_content'],
                user_id=note['user_id'],
                created_at=str(note['created_at'])
            )
            notes_list.append(note_info)
        
        # Create appropriate context message
        if account_id and facility_id:
            context = f"account {account_id} and facility {facility_id}"
        elif account_id:
            context = f"account {account_id}"
        else:
            context = f"facility {facility_id}"
            
        response = NotesListResponse(
            success=True,
            message=f"Retrieved {len(notes)} notes for {context}",
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