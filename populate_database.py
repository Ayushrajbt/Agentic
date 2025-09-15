#!/usr/bin/env python3
"""
Database Population Script for Evolyn System
This script creates the necessary tables and populates them with mock data.
"""

import json
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from database import db
import logging

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_tables():
    """Create the accounts and facilities tables."""
    logger.info("Creating database tables...")
    
    # Create accounts table
    accounts_table_sql = """
    CREATE TABLE IF NOT EXISTS accounts (
        account_id VARCHAR(50) PRIMARY KEY,
        account_name VARCHAR(255) NOT NULL,
        status VARCHAR(20) NOT NULL,
        is_tna BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP WITH TIME ZONE,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        pricing_model VARCHAR(50),
        address_line1 VARCHAR(255),
        address_line2 VARCHAR(255),
        address_city VARCHAR(100),
        address_state VARCHAR(10),
        address_postal_code VARCHAR(20),
        address_country VARCHAR(100),
        total_amount_due DECIMAL(10,2) DEFAULT 0,
        total_amount_due_this_week DECIMAL(10,2) DEFAULT 0,
        invoice_id VARCHAR(100),
        invoice_amount DECIMAL(10,2) DEFAULT 0,
        invoice_due_date VARCHAR(50),
        current_balance DECIMAL(10,2) DEFAULT 0,
        points_earned_this_quarter INTEGER DEFAULT 0,
        pending_balance DECIMAL(10,2) DEFAULT 0,
        current_tier VARCHAR(50),
        next_tier VARCHAR(50),
        points_to_next_tier INTEGER DEFAULT 0,
        quarter_end_date TIMESTAMP WITH TIME ZONE,
        free_vials_available INTEGER DEFAULT 0,
        rewards_required_for_next_free_vial INTEGER DEFAULT 0,
        rewards_redeemed_towards_next_free_vial INTEGER DEFAULT 0,
        rewards_status VARCHAR(50),
        rewards_updated_at TIMESTAMP WITH TIME ZONE,
        evolux_level VARCHAR(50),
        description TEXT
    );
    """
    
    # Create facilities table
    facilities_table_sql = """
    CREATE TABLE IF NOT EXISTS facilities (
        facility_id VARCHAR(50) PRIMARY KEY,
        facility_name VARCHAR(255) NOT NULL,
        status VARCHAR(20) NOT NULL,
        account_id VARCHAR(50) NOT NULL,
        has_signed_medical_liability_agreement BOOLEAN DEFAULT FALSE,
        medical_license_id VARCHAR(100),
        medical_license_state VARCHAR(10),
        medical_license_number VARCHAR(50),
        medical_license_involvement VARCHAR(50),
        medical_license_expiration_date TIMESTAMP WITH TIME ZONE,
        medical_license_is_expired BOOLEAN DEFAULT FALSE,
        medical_license_status VARCHAR(100),
        medical_license_owner_first_name VARCHAR(100),
        medical_license_owner_last_name VARCHAR(100),
        account_has_signed_financial_agreement BOOLEAN DEFAULT FALSE,
        account_has_accepted_jet_terms BOOLEAN DEFAULT FALSE,
        shipping_address_line1 VARCHAR(255),
        shipping_address_line2 VARCHAR(255),
        shipping_address_city VARCHAR(100),
        shipping_address_state VARCHAR(10),
        shipping_address_zip VARCHAR(20),
        shipping_address_commercial BOOLEAN DEFAULT FALSE,
        sponsored BOOLEAN DEFAULT FALSE,
        agreement_status VARCHAR(50),
        agreement_signed_at TIMESTAMP WITH TIME ZONE,
        agreement_type VARCHAR(50),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        description TEXT,
        FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE CASCADE
    );
    """
    
    # Create notes table
    notes_table_sql = """
    CREATE TABLE IF NOT EXISTS notes (
        note_id SERIAL PRIMARY KEY,
        account_id VARCHAR(50) NOT NULL,
        note_content TEXT NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        created_by VARCHAR(100) DEFAULT 'system',
        FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE CASCADE
    );
    """
    

    
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                # Create accounts table
                cursor.execute(accounts_table_sql)
                logger.info("✅ Accounts table created successfully")
                
                # Create facilities table
                cursor.execute(facilities_table_sql)
                logger.info("✅ Facilities table created successfully")
                
                # Create notes table
                cursor.execute(notes_table_sql)
                logger.info("✅ Notes table created successfully")
                
                conn.commit()
                
    except Exception as e:
        logger.error(f"❌ Error creating tables: {e}")
        raise

def parse_datetime(date_str):
    """Parse datetime string to PostgreSQL format."""
    if not date_str:
        return None
    try:
        # Handle different datetime formats
        if 'T' in date_str:
            # ISO format with timezone
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        else:
            # Simple date format
            dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt
    except Exception as e:
        logger.warning(f"Could not parse datetime '{date_str}': {e}")
        return None

def populate_accounts(data):
    """Populate the accounts table with data."""
    logger.info("Populating accounts table...")
    
    accounts_data = data.get('account_overview', [])
    
    for account in accounts_data:
        try:
            insert_sql = """
            INSERT INTO accounts (
                account_id, account_name, status, is_tna, created_at, pricing_model,
                address_line1, address_line2, address_city, address_state, 
                address_postal_code, address_country, total_amount_due, 
                total_amount_due_this_week, invoice_id, invoice_amount, invoice_due_date,
                current_balance, points_earned_this_quarter, pending_balance,
                current_tier, next_tier, points_to_next_tier, quarter_end_date,
                free_vials_available, rewards_required_for_next_free_vial,
                rewards_redeemed_towards_next_free_vial, rewards_status,
                rewards_updated_at, evolux_level
            ) VALUES (
                %(account_id)s, %(account_name)s, %(status)s, %(is_tna)s, %(created_at)s,
                %(pricing_model)s, %(address_line1)s, %(address_line2)s, %(address_city)s,
                %(address_state)s, %(address_postal_code)s, %(address_country)s,
                %(total_amount_due)s, %(total_amount_due_this_week)s, %(invoice_id)s,
                %(invoice_amount)s, %(invoice_due_date)s, %(current_balance)s,
                %(points_earned_this_quarter)s, %(pending_balance)s, %(current_tier)s,
                %(next_tier)s, %(points_to_next_tier)s, %(quarter_end_date)s,
                %(free_vials_available)s, %(rewards_required_for_next_free_vial)s,
                %(rewards_redeemed_towards_next_free_vial)s, %(rewards_status)s,
                %(rewards_updated_at)s, %(evolux_level)s
            ) ON CONFLICT (account_id) DO UPDATE SET
                account_name = EXCLUDED.account_name,
                status = EXCLUDED.status,
                updated_at = CURRENT_TIMESTAMP
            """
            
            account_data = {
                'account_id': account.get('account_id'),
                'account_name': account.get('name'),
                'status': account.get('status'),
                'is_tna': account.get('is_tna', False),
                'created_at': parse_datetime(account.get('created_at')),
                'pricing_model': account.get('pricing_model'),
                'address_line1': account.get('address_line1'),
                'address_line2': account.get('address_line2'),
                'address_city': account.get('address_city'),
                'address_state': account.get('address_state'),
                'address_postal_code': account.get('address_postal_code'),
                'address_country': account.get('address_country'),
                'total_amount_due': account.get('total_amount_due', 0),
                'total_amount_due_this_week': account.get('total_amount_due_this_week', 0),
                'invoice_id': account.get('invoice_id'),
                'invoice_amount': account.get('invoice_amount', 0),
                'invoice_due_date': account.get('invoice_due_date'),
                'current_balance': account.get('current_balance', 0),
                'points_earned_this_quarter': account.get('points_earned_this_quarter', 0),
                'pending_balance': account.get('pending_balance', 0),
                'current_tier': account.get('current_tier'),
                'next_tier': account.get('next_tier'),
                'points_to_next_tier': account.get('points_to_next_tier', 0),
                'quarter_end_date': parse_datetime(account.get('quarter_end_date')),
                'free_vials_available': account.get('free_vials_available', 0),
                'rewards_required_for_next_free_vial': account.get('rewards_required_for_next_free_vial', 0),
                'rewards_redeemed_towards_next_free_vial': account.get('rewards_redeemed_towards_next_free_vial', 0),
                'rewards_status': account.get('rewards_status'),
                'rewards_updated_at': parse_datetime(account.get('rewards_updated_at')),
                'evolux_level': account.get('evolux_level')
            }
            
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(insert_sql, account_data)
                    conn.commit()
                    
            logger.info(f"✅ Inserted/Updated account: {account.get('name')} ({account.get('account_id')})")
            
        except Exception as e:
            logger.error(f"❌ Error inserting account {account.get('account_id')}: {e}")
            raise

def populate_facilities(data):
    """Populate the facilities table with data."""
    logger.info("Populating facilities table...")
    
    facilities_data = data.get('facility_overview', [])
    
    for facility in facilities_data:
        try:
            insert_sql = """
            INSERT INTO facilities (
                facility_id, facility_name, status, account_id, 
                has_signed_medical_liability_agreement, medical_license_id,
                medical_license_state, medical_license_number, medical_license_involvement,
                medical_license_expiration_date, medical_license_is_expired,
                medical_license_status, medical_license_owner_first_name,
                medical_license_owner_last_name, account_has_signed_financial_agreement,
                account_has_accepted_jet_terms, shipping_address_line1,
                shipping_address_line2, shipping_address_city, shipping_address_state,
                shipping_address_zip, shipping_address_commercial, sponsored,
                agreement_status, agreement_signed_at, agreement_type
            ) VALUES (
                %(facility_id)s, %(facility_name)s, %(status)s, %(account_id)s,
                %(has_signed_medical_liability_agreement)s, %(medical_license_id)s,
                %(medical_license_state)s, %(medical_license_number)s, %(medical_license_involvement)s,
                %(medical_license_expiration_date)s, %(medical_license_is_expired)s,
                %(medical_license_status)s, %(medical_license_owner_first_name)s,
                %(medical_license_owner_last_name)s, %(account_has_signed_financial_agreement)s,
                %(account_has_accepted_jet_terms)s, %(shipping_address_line1)s,
                %(shipping_address_line2)s, %(shipping_address_city)s, %(shipping_address_state)s,
                %(shipping_address_zip)s, %(shipping_address_commercial)s, %(sponsored)s,
                %(agreement_status)s, %(agreement_signed_at)s, %(agreement_type)s
            ) ON CONFLICT (facility_id) DO UPDATE SET
                facility_name = EXCLUDED.facility_name,
                status = EXCLUDED.status,
                updated_at = CURRENT_TIMESTAMP
            """
            
            facility_data = {
                'facility_id': facility.get('id'),
                'facility_name': facility.get('name'),
                'status': facility.get('status'),
                'account_id': facility.get('account_id'),
                'has_signed_medical_liability_agreement': facility.get('has_signed_medical_liability_agreement', False),
                'medical_license_id': facility.get('medical_license_id'),
                'medical_license_state': facility.get('medical_license_state'),
                'medical_license_number': facility.get('medical_license_number'),
                'medical_license_involvement': facility.get('medical_license_involvement'),
                'medical_license_expiration_date': parse_datetime(facility.get('medical_license_expiration_date')),
                'medical_license_is_expired': facility.get('medical_license_is_expired', False),
                'medical_license_status': facility.get('medical_license_status'),
                'medical_license_owner_first_name': facility.get('medical_license_owner_first_name'),
                'medical_license_owner_last_name': facility.get('medical_license_owner_last_name'),
                'account_has_signed_financial_agreement': facility.get('account_has_signed_financial_agreement', False),
                'account_has_accepted_jet_terms': facility.get('account_has_accepted_jet_terms', False),
                'shipping_address_line1': facility.get('shipping_address_line1'),
                'shipping_address_line2': facility.get('shipping_address_line2'),
                'shipping_address_city': facility.get('shipping_address_city'),
                'shipping_address_state': facility.get('shipping_address_state'),
                'shipping_address_zip': facility.get('shipping_address_zip'),
                'shipping_address_commercial': facility.get('shipping_address_commercial', False),
                'sponsored': facility.get('sponsored', False),
                'agreement_status': facility.get('agreement_status'),
                'agreement_signed_at': parse_datetime(facility.get('agreement_signed_at')),
                'agreement_type': facility.get('agreement_type')
            }
            
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(insert_sql, facility_data)
                    conn.commit()
                    
            logger.info(f"✅ Inserted/Updated facility: {facility.get('name')} ({facility.get('id')})")
            
        except Exception as e:
            logger.error(f"❌ Error inserting facility {facility.get('id')}: {e}")
            raise

def populate_note_saver(data):
    """Populate the note-saver table with data."""
    logger.info("Populating note-saver table...")
    
    # Get note data from the mock data, or create some sample notes
    notes_data = data.get('notes', [])
    
    # If no notes data exists, create some sample notes for existing accounts
    if not notes_data:
        logger.info("No notes data found in mock data, creating sample notes...")
        try:
            # Get some existing account IDs
            accounts = db.execute_query("SELECT account_id FROM accounts LIMIT 5")
            sample_notes = [
                "Initial consultation completed",
                "Follow-up appointment scheduled",
                "Payment processed successfully",
                "Account review pending",
                "Customer service inquiry resolved"
            ]
            
            for i, account in enumerate(accounts):
                note_text = sample_notes[i % len(sample_notes)]
                insert_sql = """
                INSERT INTO "note-saver" (account_id, note, created_at)
                VALUES (%(account_id)s, %(note)s, %(created_at)s)
                """
                
                note_data = {
                    'account_id': account['account_id'],
                    'note': note_text,
                    'created_at': datetime.now()
                }
                
                with db.get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(insert_sql, note_data)
                        conn.commit()
                        
                logger.info(f"✅ Inserted sample note for account: {account['account_id']}")
                
        except Exception as e:
            logger.error(f"❌ Error creating sample notes: {e}")
            raise
    else:
        # Process notes from mock data
        for note in notes_data:
            try:
                insert_sql = """
                INSERT INTO "note-saver" (account_id, note, created_at)
                VALUES (%(account_id)s, %(note)s, %(created_at)s)
                """
                
                note_data = {
                    'account_id': note.get('account_id'),
                    'note': note.get('note'),
                    'created_at': parse_datetime(note.get('created_at')) or datetime.now()
                }
                
                with db.get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(insert_sql, note_data)
                        conn.commit()
                        
                logger.info(f"✅ Inserted note for account: {note.get('account_id')}")
                
            except Exception as e:
                logger.error(f"❌ Error inserting note for account {note.get('account_id')}: {e}")
                raise

def verify_data():
    """Verify that data was inserted correctly."""
    logger.info("Verifying inserted data...")
    
    try:
        # Check accounts count
        account_count = db.execute_scalar("SELECT COUNT(*) FROM accounts")
        logger.info(f"📊 Total accounts: {account_count}")
        
        # Check facilities count
        facility_count = db.execute_scalar("SELECT COUNT(*) FROM facilities")
        logger.info(f"📊 Total facilities: {facility_count}")
        
        # Check note-saver count
        note_count = db.execute_scalar('SELECT COUNT(*) FROM "note-saver"')
        logger.info(f"📊 Total notes: {note_count}")
        
        # Show sample data
        accounts = db.execute_query("SELECT account_id, account_name, status FROM accounts LIMIT 3")
        logger.info("📋 Sample accounts:")
        for account in accounts:
            logger.info(f"  - {account['account_name']} ({account['account_id']}) - {account['status']}")
        
        facilities = db.execute_query("SELECT facility_id, facility_name, status, account_id FROM facilities LIMIT 3")
        logger.info("📋 Sample facilities:")
        for facility in facilities:
            logger.info(f"  - {facility['facility_name']} ({facility['facility_id']}) - {facility['status']}")
        
        notes = db.execute_query('SELECT id, account_id, note, created_at FROM "note-saver" LIMIT 3')
        logger.info("📋 Sample notes:")
        for note in notes:
            logger.info(f"  - Note {note['id']}: {note['note'][:50]}... (Account: {note['account_id']})")
            
    except Exception as e:
        logger.error(f"❌ Error verifying data: {e}")
        raise

def main():
    """Main function to populate the database."""
    logger.info("🚀 Starting database population...")
    
    try:
        # Test database connection
        if not db.test_connection():
            logger.error("❌ Database connection failed!")
            sys.exit(1)
        
        logger.info("✅ Database connection successful")
        
        # Load mock data
        logger.info("📂 Loading mock data...")
        with open('mock_data.json', 'r') as f:
            data = json.load(f)
        
        # Create tables
        create_tables()
        
        # Populate data
        populate_accounts(data)
        populate_facilities(data)
        populate_note_saver(data)
        
        # Verify data
        verify_data()
        
        logger.info("🎉 Database population completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Database population failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
