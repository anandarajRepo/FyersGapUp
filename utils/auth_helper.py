import hashlib
import requests
import logging
import os
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class FyersAuthHelper:
    """Enhanced Fyers authentication helper for WebSocket strategy"""

    def __init__(self):
        self.client_id = os.environ.get('FYERS_CLIENT_ID')
        self.secret_key = os.environ.get('FYERS_SECRET_KEY')
        self.redirect_uri = os.environ.get('FYERS_REDIRECT_URI', 'https://trade.fyers.in/api-login/redirect-to-app')

    def generate_auth_url(self) -> str:
        """Generate authorization URL for Fyers login"""
        try:
            auth_url = "https://api-t1.fyers.in/api/v3/generate-authcode"

            params = {
                'client_id': self.client_id,
                'redirect_uri': self.redirect_uri,
                'response_type': 'code',
                'state': 'sample_state'
            }

            url_params = "&".join([f"{k}={v}" for k, v in params.items()])
            return f"{auth_url}?{url_params}"

        except Exception as e:
            logger.error(f"Error generating auth URL: {e}")
            return None

    def get_access_token(self, auth_code: str) -> Optional[str]:
        """Get access token from authorization code"""
        try:
            url = "https://api-t1.fyers.in/api/v3/validate-authcode"

            app_id_hash = hashlib.sha256(f"{self.client_id}:{self.secret_key}".encode()).hexdigest()

            data = {
                'grant_type': 'authorization_code',
                'appIdHash': app_id_hash,
                'code': auth_code
            }

            headers = {'Content-Type': 'application/json'}

            response = requests.post(url, json=data, headers=headers)

            if response.status_code == 200:
                result = response.json()
                if result.get('s') == 'ok':
                    access_token = result.get('access_token')
                    logger.info("Access token generated successfully")
                    return access_token
                else:
                    logger.error(f"Token generation failed: {result.get('message')}")
                    return None
            else:
                logger.error(f"HTTP Error: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error getting access token: {e}")
            return None

    def validate_token(self, access_token: str) -> bool:
        """Validate if access token is still valid"""
        try:
            url = "https://api-t1.fyers.in/api/v3/profile"
            headers = {'Authorization': f"{self.client_id}:{access_token}"}

            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                result = response.json()
                return result.get('s') == 'ok'

            return False

        except Exception as e:
            logger.error(f"Error validating token: {e}")
            return False

    def setup_interactive_auth(self) -> Optional[str]:
        """Interactive authentication setup"""
        try:
            print("\n" + "=" * 60)
            print("FYERS API AUTHENTICATION SETUP")
            print("=" * 60)

            if not self.client_id or not self.secret_key:
                print("Missing CLIENT_ID or SECRET_KEY in environment variables")
                return None

            # Generate and display auth URL
            auth_url = self.generate_auth_url()
            if not auth_url:
                print("Failed to generate authentication URL")
                return None

            print(f"\n Step 1: Open this URL in your browser:")
            print(f" {auth_url}")
            print(f"\n Step 2: Complete the login process")
            print(f" Step 3: Copy the authorization code from the redirect URL")

            # Get auth code from user
            auth_code = input("\n Enter authorization code: ").strip()

            if not auth_code:
                print("No authorization code provided")
                return None

            # Get access token
            access_token = self.get_access_token(auth_code)

            if access_token:
                print(f"\n Authentication successful!")
                print(f"Access Token: {access_token[:20]}...")

                # Update .env file
                self.update_env_file('FYERS_ACCESS_TOKEN', access_token)
                print(f"Access token saved to .env file")

                return access_token
            else:
                print("Authentication failed!")
                return None

        except Exception as e:
            logger.error