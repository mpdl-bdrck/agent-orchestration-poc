#!/usr/bin/env python3
"""
BidSwitch Client - API Connection Handler
==========================================

Handles BidSwitch API authentication and data retrieval.
Extracted from bidswitch_deal_verifier.py for modularity.
"""

import os
import requests
from typing import Dict, List, Any, Optional


class BidSwitchClient:
    """Handles BidSwitch API authentication and requests"""
    
    def __init__(self):
        self.bidswitch_token = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate to BidSwitch API using OAuth2 flow from data-sources.md"""
        try:
            # Get credentials from environment
            bidswitch_username = os.getenv('BIDSWITCH_USERNAME')
            bidswitch_password = os.getenv('BIDSWITCH_PASSWORD')
            
            if not bidswitch_username or not bidswitch_password:
                print("❌ BidSwitch credentials not found in environment")
                print("ℹ️  Set BIDSWITCH_USERNAME and BIDSWITCH_PASSWORD environment variables")
                raise ValueError("BidSwitch credentials required but not found")

            # Real BidSwitch OAuth2 endpoint from data-sources.md
            auth_url = "https://iam.bidswitch.com/auth/realms/bidswitch/protocol/openid-connect/token"
            print("🔐 Authenticating to BidSwitch using OAuth2...")
            
            # OAuth2 password grant as specified in data-sources.md
            auth_data = {
                'client_id': 'public-client',
                'grant_type': 'password',
                'username': bidswitch_username,
                'password': bidswitch_password,
                'scope': 'openid email profile'
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            response = requests.post(auth_url, data=auth_data, headers=headers, timeout=10)
            
            if response.status_code == 200:
                token_data = response.json()
                self.bidswitch_token = token_data.get('access_token')
                
                if self.bidswitch_token:
                    print("✅ BidSwitch OAuth2 authentication successful")
                else:
                    print("❌ No access token in OAuth2 response")
                    raise ValueError("BidSwitch OAuth2 response missing access_token")
            else:
                print(f"❌ BidSwitch OAuth2 authentication failed: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                raise ValueError(f"BidSwitch OAuth2 authentication failed with status {response.status_code}")

        except requests.exceptions.RequestException as e:
            print(f"❌ BidSwitch API connection error: {e}")
            raise ValueError(f"BidSwitch API connection failed: {e}")
        except ValueError:
            # Re-raise ValueError (credentials missing or auth failed)
            raise
        except Exception as e:
            print(f"❌ BidSwitch authentication error: {e}")
            raise ValueError(f"BidSwitch authentication failed: {e}")
    
    def get_deal_performance(self, deal_id: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Get deal performance data from BidSwitch API using real endpoint from data-sources.md
        
        Args:
            deal_id: SSP deal identifier (e.g., "939094715008")
            start_date: Analysis start date (YYYY-MM-DD)
            end_date: Analysis end date (YYYY-MM-DD)
            
        Returns:
            Dict containing deal performance data with structure:
            {
                "deals": [{"name_external": "Equativ", "dsp_bid_requests": 5803200, ...}],
                "total": {"dsp_bid_requests": 5803200, "imps": 2812, ...}
            }
        """
        try:
            # Get DSP ID from environment
            dsp_seat_id = os.getenv('DSP_SEAT_ID')
            if not dsp_seat_id:
                raise ValueError("DSP_SEAT_ID must be configured in environment variables")
            
            # Real BidSwitch API endpoint from data-sources.md
            api_url = f"https://my.bidswitch.com/api/reporting/deals/dsp/{dsp_seat_id}"
            
            # Parameters as specified in data-sources.md
            params = {
                'deal_id': deal_id,
                'start_date': start_date,
                'end_date': end_date,
                'utc_offset': '0'
            }
            
            headers = {
                "Authorization": f"Bearer {self.bidswitch_token}",
                "Content-Type": "application/json"
            }
            
            print(f"   📡 Calling BidSwitch API for deal {deal_id} ({start_date} to {end_date})...")
            
            response = requests.get(api_url, params=params, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ BidSwitch API error for deal {deal_id}: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                raise ValueError(f"BidSwitch API returned status {response.status_code} for deal {deal_id}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ BidSwitch API request error for deal {deal_id}: {e}")
            raise ValueError(f"BidSwitch API request failed for deal {deal_id}: {e}")
        except Exception as e:
            print(f"❌ BidSwitch API error for deal {deal_id}: {e}")
            raise
    
    def is_authenticated(self) -> bool:
        """Check if client is authenticated"""
        return self.bidswitch_token is not None
