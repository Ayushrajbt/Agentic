#!/usr/bin/env python3
"""
Local Run Script for Evolyn Conversational Agent
Simple script to run the conversational agent in terminal mode.
"""

import sys
import os
from app import main

if __name__ == "__main__":
    print("🚀 Starting Evolyn Conversational Agent in Terminal Mode...")
    print("=" * 60)
    
    try:
        # Run the main function from app.py
        main()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error starting agent: {e}")
        print("Please check your .env file and database connection.")
        sys.exit(1)
