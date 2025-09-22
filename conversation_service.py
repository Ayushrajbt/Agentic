#!/usr/bin/env python3
"""
Conversation Service for managing conversation history in database
"""

import json
import uuid
from typing import Optional, List, Dict, Any
from database import db
import logging

logger = logging.getLogger(__name__)

class ConversationService:
    """Service for managing conversation history in the database."""
    
    def create_conversation(self, conversation_history: List[Dict], account_id: Optional[str] = None, facility_id: Optional[str] = None) -> str:
        """Create a new conversation and return the conversation_id."""
        try:
            conversation_id = str(uuid.uuid4())
            
            insert_sql = """
            INSERT INTO convos (conversation_id, conversation_history, account_id, facility_id)
            VALUES (%s, %s, %s, %s)
            """
            
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(insert_sql, (
                        conversation_id,
                        json.dumps(conversation_history),
                        account_id,
                        facility_id
                    ))
                    conn.commit()
            
            logger.info(f"Created new conversation with ID: {conversation_id}")
            return conversation_id
            
        except Exception as e:
            logger.error(f"Error creating conversation: {e}")
            raise
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation by ID."""
        try:
            select_sql = """
            SELECT conversation_id, conversation_history, account_id, facility_id, 
                   created_at, updated_at
            FROM convos 
            WHERE conversation_id = %s
            """
            
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(select_sql, (conversation_id,))
                    result = cursor.fetchone()
                    
                    if result:
                        # Handle both string and already parsed JSON
                        conversation_history = result[1]
                        if isinstance(conversation_history, str):
                            conversation_history = json.loads(conversation_history)
                        elif conversation_history is None:
                            conversation_history = []
                            
                        return {
                            'conversation_id': result[0],
                            'conversation_history': conversation_history,
                            'account_id': result[2],
                            'facility_id': result[3],
                            'created_at': result[4],
                            'updated_at': result[5]
                        }
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting conversation {conversation_id}: {e}")
            raise
    
    def update_conversation(self, conversation_id: str, conversation_history: List[Dict]) -> bool:
        """Update conversation history."""
        try:
            update_sql = """
            UPDATE convos 
            SET conversation_history = %s, updated_at = CURRENT_TIMESTAMP
            WHERE conversation_id = %s
            """
            
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(update_sql, (
                        json.dumps(conversation_history),
                        conversation_id
                    ))
                    conn.commit()
                    
                    # Check if any rows were affected
                    return cursor.rowcount > 0
                    
        except Exception as e:
            logger.error(f"Error updating conversation {conversation_id}: {e}")
            raise
    
    def conversation_exists(self, conversation_id: str) -> bool:
        """Check if conversation exists."""
        try:
            select_sql = "SELECT 1 FROM convos WHERE conversation_id = %s"
            
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(select_sql, (conversation_id,))
                    result = cursor.fetchone()
                    return result is not None
                    
        except Exception as e:
            logger.error(f"Error checking conversation existence {conversation_id}: {e}")
            raise

# Global conversation service instance
conversation_service = ConversationService()
