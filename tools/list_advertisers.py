#!/usr/bin/env python3
"""
List Advertisers Script
======================

Simple script to list all advertisers/accounts in the Bedrock Platform.
"""

import os
import sys
from typing import List, Any

# Load environment variables from .env file (like campaign analysis script)
def load_env_file():
    """Load environment variables from .env file"""
    env_file = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key] = value

# Load environment first
load_env_file()

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "shared"))
from database_connector import DatabaseConnector


def list_advertisers():
    """List all advertisers/accounts"""
    db = DatabaseConnector()

    try:
        # Query for advertisers/accounts
        query = '''
            SELECT "accountId", "name", "statusId"
            FROM "accounts"
            ORDER BY "accountId"
        '''

        results = db.execute_postgres_query(query)

        print('📋 Advertisers/Accounts Found:')
        print('=' * 60)
        print(f"{'ID':<4} | {'Name':<35} | {'Status':<10}")
        print('-' * 60)

        for row in results:
            account_id = row[0]
            name = row[1] or 'Unknown'
            status_id = row[2]

            status = 'Active' if status_id == 1 else f'Status {status_id}'

            # Truncate long names for display
            name_display = name[:34] + '...' if len(name) > 34 else name

            print(f'{account_id:<4d} | {name_display:<35} | {status:<10}')

        print(f'\nTotal advertisers found: {len(results)}')

    except Exception as e:
        print(f'❌ Error retrieving advertisers: {e}')
        return False

    return True


if __name__ == "__main__":
    success = list_advertisers()
    sys.exit(0 if success else 1)
