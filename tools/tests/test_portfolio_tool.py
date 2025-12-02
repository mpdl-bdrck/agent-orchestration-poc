#!/usr/bin/env python3
"""
Standalone test script for portfolio pacing tool.
Run this outside the app to verify the tool works correctly.

Requires:
- AWS SSO authentication (profile: bedrock)
- Database credentials in .env file (POSTGRES_HOST, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD)
"""
import sys
import os
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Check AWS SSO authentication first (like chat.sh does)
print("🔐 Checking AWS SSO authentication...")
try:
    result = subprocess.run(
        ['aws', 'sts', 'get-caller-identity', '--profile', 'bedrock'],
        capture_output=True,
        text=True,
        timeout=10
    )
    if result.returncode == 0:
        print("✅ AWS SSO authentication successful")
    else:
        print("⚠️  AWS SSO login required for portfolio analysis tools")
        print("🔑 Running: aws sso login --profile bedrock")
        subprocess.run(['aws', 'sso', 'login', '--profile', 'bedrock'], check=False)
        
        # Verify login was successful
        verify_result = subprocess.run(
            ['aws', 'sts', 'get-caller-identity', '--profile', 'bedrock'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if verify_result.returncode != 0:
            print("❌ AWS SSO authentication failed")
            print("ℹ️  Portfolio analysis tools require AWS SSO authentication")
            sys.exit(1)
        print("✅ AWS SSO authentication successful")
except FileNotFoundError:
    print("⚠️  AWS CLI not found. Please install AWS CLI and configure SSO.")
    sys.exit(1)
except subprocess.TimeoutExpired:
    print("⚠️  AWS SSO check timed out. Continuing anyway...")
except Exception as e:
    print(f"⚠️  Error checking AWS SSO: {e}. Continuing anyway...")

# Load environment variables from .env file if it exists
env_file = project_root / '.env'
if env_file.exists():
    print(f"📋 Loading environment variables from {env_file}")
    try:
        from dotenv import load_dotenv
        load_dotenv(env_file)
        print("✅ Environment variables loaded")
    except ImportError:
        print("⚠️  python-dotenv not installed. Install with: pip install python-dotenv")
        print("   Attempting to load .env manually...")
        # Manual .env loading as fallback
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        print("✅ Environment variables loaded (manual)")
else:
    print(f"⚠️  .env file not found at {env_file}")
    print("ℹ️  Create .env file with POSTGRES_HOST, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD")
    print("   See tools/env.txt for template")

# Validate required environment variables
required_vars = ['POSTGRES_HOST', 'POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD']
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
    print("ℹ️  Set these in .env file or environment")
    sys.exit(1)

print("✅ Environment configuration validated")
print("")

import logging
logging.basicConfig(level=logging.INFO)

def test_portfolio_tool():
    """Test the portfolio pacing tool directly."""
    print("=" * 80)
    print("Testing Portfolio Pacing Tool (Standalone)")
    print("=" * 80)
    
    try:
        from src.tools.portfolio_pacing_tool import analyze_portfolio_pacing
        
        print("\nTesting with account_id='17', advertiser_filter='Lilly'")
        print("Date range: Rolling 30-day window (last 30 days from today, PST)")
        print("Budget: $233,000")
        print("-" * 80)
        result = analyze_portfolio_pacing.invoke({
            "account_id": "17",
            "advertiser_filter": "Lilly"
            # campaign_start and campaign_end default to None = rolling 30-day window
        })
        print(f"\nResult:\n{result}")
        
        print("\n" + "=" * 80)
        print("✅ Test completed successfully!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error testing tool: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_portfolio_tool()

