#!/usr/bin/env python3
"""
Database Connection Layer
========================

Centralized database connection management for PostgreSQL and Redshift.
Handles connections, query execution, and cleanup.
"""

import os
import sys
import time
import psycopg2
import boto3
from typing import List, Any, Optional

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    # Try loading from project root and tools directory
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    load_dotenv(os.path.join(project_root, '.env'))
    load_dotenv(os.path.join(project_root, 'tools', '.env'))
except ImportError:
    pass  # dotenv not available, use system environment variables


class DatabaseConnector:
    """Manages PostgreSQL and Redshift database connections"""
    
    def __init__(self):
        self.postgres_conn = None
        self.redshift_client = None
        self._connect_databases()
    
    def _connect_databases(self):
        """Initialize PostgreSQL and Redshift connections"""
        try:
            # PostgreSQL connection - prioritize POSTGRES_* vars (for exchange DB) over DATABASE_URL (knowledge_base)
            # This matches the original tool's behavior
            postgres_url = os.getenv('POSTGRES_URL')
            postgres_host = os.getenv('POSTGRES_HOST')
            
            if postgres_url:
                # Use POSTGRES_URL if explicitly set (for exchange database)
                self.postgres_conn = psycopg2.connect(postgres_url)
            elif postgres_host:
                # Use individual POSTGRES_* vars if POSTGRES_HOST is set (for exchange database)
                self.postgres_conn = psycopg2.connect(
                    host=postgres_host,
                    port=int(os.getenv('POSTGRES_PORT', 5432)),
                    database=os.getenv('POSTGRES_DB'),
                    user=os.getenv('POSTGRES_USER'),
                    password=os.getenv('POSTGRES_PASSWORD')
                )
            else:
                # Fall back to DATABASE_URL (for knowledge_base - vector DB)
                database_url = os.getenv('DATABASE_URL')
                if database_url:
                    self.postgres_conn = psycopg2.connect(database_url)
                else:
                    raise ValueError("No PostgreSQL connection configured. Set POSTGRES_URL, POSTGRES_HOST, or DATABASE_URL")
            print("✅ PostgreSQL connected")
            
            # Redshift connection (use AWS profile like MCP)
            session = boto3.Session(profile_name='bedrock')  # Use same profile as MCP
            self.redshift_client = session.client(
                'redshift-data',
                region_name=os.getenv('AWS_REGION', 'eu-west-1')
            )
            print("✅ Redshift connected")
            
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            print("⚠️  Continuing without database connections - some features may not work")
            # Don't exit - allow tools to work with available connections
    
    def execute_postgres_query(self, query: str, params: tuple = ()) -> List[tuple]:
        """Execute PostgreSQL query and return results"""
        try:
            cursor = self.postgres_conn.cursor()
            cursor.execute(query, params)
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            print(f"❌ PostgreSQL query failed: {e}")
            raise
    
    def execute_redshift_query(self, query: str, params: List[Any], timeout_seconds: int = 180) -> List[tuple]:
        """
        Execute Redshift query and return results with timeout

        IMPORTANT LIMITATION:
        - AWS bedrock profile only has access to EU Redshift cluster (bedrock-eu-west-1)
        - No access to US Redshift clusters (us-east-1, us-west-2, etc.)
        - US campaign spend data is not accessible via direct Redshift queries
        - For US campaign data, consider MCP API integration
        """
        try:
            # Replace %s with actual values for Redshift
            formatted_query = query
            for param in params:
                formatted_query = formatted_query.replace('%s', f"'{param}'", 1)
            
            print(f"   Executing query: {formatted_query[:100]}...")
            
            response = self.redshift_client.execute_statement(
                ClusterIdentifier='bedrock-eu-west-1',  # Hardcoded correct cluster name
                Database=os.getenv('REDSHIFT_DATABASE', 'bedrock'),
                Sql=formatted_query
            )
            
            query_id = response['Id']
            print(f"   Query ID: {query_id}")
            
            # Wait for completion
            start_time = time.time()
            while True:
                elapsed = time.time() - start_time
                
                if elapsed > timeout_seconds:
                    print(f"   ⚠️  Query timeout after {timeout_seconds}s, attempting to abort...")
                    try:
                        self.redshift_client.cancel_statement(Id=query_id)
                    except:
                        pass
                    raise Exception(f"Redshift query timed out after {timeout_seconds} seconds")
                
                status_response = self.redshift_client.describe_statement(Id=query_id)
                status = status_response['Status']
                
                if elapsed > 30:
                    print(f"   Query status: {status} (elapsed: {elapsed:.1f}s) - Large table, please wait...")
                else:
                    print(f"   Query status: {status} (elapsed: {elapsed:.1f}s)")
                
                if status == 'FINISHED':
                    break
                elif status == 'FAILED':
                    error = status_response.get('Error', 'Unknown error')
                    raise Exception(f"Redshift query failed: {error}")
                elif status == 'ABORTED':
                    raise Exception("Redshift query was aborted")
                
                time.sleep(2)  # Check every 2 seconds instead of 1
            
            # Get results
            result_response = self.redshift_client.get_statement_result(Id=query_id)
            records = result_response.get('Records', [])
            
            # Convert to tuples
            results = []
            for record in records:
                row = []
                for field in record:
                    if 'stringValue' in field:
                        row.append(field['stringValue'])
                    elif 'longValue' in field:
                        row.append(field['longValue'])
                    elif 'doubleValue' in field:
                        row.append(field['doubleValue'])
                    elif 'isNull' in field and field['isNull']:
                        row.append(None)
                    else:
                        row.append(str(field))
                results.append(tuple(row))
            
            return results
            
        except Exception as e:
            print(f"❌ Redshift query execution failed: {e}")
            raise
    
    def close_connections(self):
        """Close all database connections"""
        if self.postgres_conn:
            self.postgres_conn.close()
        # Redshift client doesn't need explicit closing
