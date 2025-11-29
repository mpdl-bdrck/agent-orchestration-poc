#!/usr/bin/env python3
"""
Cleanup script to remove legacy tables from bedrock_kb database.

Keeps only:
- knowledge_chunks
- conversations

Removes all other tables (legacy from StoryForge/Eternal Ink Suite).
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text, inspect
from src.core.database.session import get_db_session

# Tables to keep
KEEP_TABLES = {'knowledge_chunks', 'conversations'}

def get_all_tables(context_id: str = None):
    """Get all table names from the database."""
    db_session_context = get_db_session(context_id) if context_id else get_db_session()
    with db_session_context as session:
        inspector = inspect(session.bind)
        tables = inspector.get_table_names()
        return tables

def drop_table(session, table_name: str):
    """Drop a table."""
    try:
        session.execute(text(f'DROP TABLE IF EXISTS "{table_name}" CASCADE'))
        session.commit()
        print(f"✅ Dropped table: {table_name}")
        return True
    except Exception as e:
        print(f"❌ Failed to drop table {table_name}: {e}")
        session.rollback()
        return False

def cleanup_database(context_id: str = 'bedrock_kb'):
    """Remove all tables except knowledge_chunks and conversations."""
    print(f"🔍 Scanning database for context: {context_id}")
    
    db_session_context = get_db_session(context_id)
    with db_session_context as session:
        # Get all tables
        all_tables = get_all_tables(context_id)
        
        print(f"\n📊 Found {len(all_tables)} tables:")
        for table in sorted(all_tables):
            if table in KEEP_TABLES:
                print(f"  ✅ {table} (keeping)")
            else:
                print(f"  ❌ {table} (will drop)")
        
        # Confirm
        tables_to_drop = [t for t in all_tables if t not in KEEP_TABLES]
        
        if not tables_to_drop:
            print("\n✨ No tables to drop - database is already clean!")
            return
        
        print(f"\n⚠️  About to drop {len(tables_to_drop)} tables:")
        for table in sorted(tables_to_drop):
            print(f"   - {table}")
        
        response = input("\n❓ Proceed with cleanup? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Cleanup cancelled")
            return
        
        # Drop tables
        print("\n🗑️  Dropping tables...")
        dropped_count = 0
        failed_count = 0
        
        for table_name in sorted(tables_to_drop):
            if drop_table(session, table_name):
                dropped_count += 1
            else:
                failed_count += 1
        
        print(f"\n✅ Cleanup complete!")
        print(f"   Dropped: {dropped_count} tables")
        if failed_count > 0:
            print(f"   Failed: {failed_count} tables")
        
        # Verify final state
        remaining_tables = get_all_tables(context_id)
        print(f"\n📊 Remaining tables ({len(remaining_tables)}):")
        for table in sorted(remaining_tables):
            print(f"   ✅ {table}")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Cleanup legacy tables from bedrock_kb database')
    parser.add_argument(
        '--context-id',
        type=str,
        default='bedrock_kb',
        help='Database context ID (default: bedrock_kb)'
    )
    parser.add_argument(
        '--yes',
        action='store_true',
        help='Skip confirmation prompt'
    )
    
    args = parser.parse_args()
    
    if args.yes:
        # Override input for non-interactive mode
        import builtins
        original_input = builtins.input
        builtins.input = lambda _: 'yes'
    
    try:
        cleanup_database(args.context_id)
    except KeyboardInterrupt:
        print("\n❌ Cleanup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during cleanup: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

