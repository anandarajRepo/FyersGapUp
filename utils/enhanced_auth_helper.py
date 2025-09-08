# utils/enhanced_auth_helper.py

import hashlib
import requests
import logging
import os
import json
import getpass
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class FyersAuthManager:
    """Enhanced Fyers authentication manager with refresh token and PIN support"""

    def __init__(self):
        self.client_id = os.environ.get('FYERS_CLIENT_ID')
        self.secret_key = os.environ.get('FYERS_SECRET_KEY')
        self.redirect_uri = os.environ.get('FYERS_REDIRECT_URI', "https://trade.fyers.in/api-login/redirect-to-app")
        self.refresh_token = os.environ.get('FYERS_REFRESH_TOKEN')
        self.access_token = os.environ.get('FYERS_ACCESS_TOKEN')
        self.pin = os.environ.get('FYERS_PIN')

    def save_to_env(self, key: str, value: str) -> None:
        """Save or update environment variable in .env file"""
        env_file = '.env'

        # Read existing .env file
        env_vars = {}
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        k, v = line.strip().split('=', 1)
                        env_vars[k] = v

        # Update the specific key
        env_vars[key] = value

        # Write back to .env file
        with open(env_file, 'w') as f:
            for k, v in env_vars.items():
                f.write(f"{k}={v}\n")

        # Update current environment
        os.environ[key] = value

    def get_or_request_pin(self) -> str:
        """Get PIN from environment or request from user"""
        if self.pin:
            return self.pin

        print("\n=== PIN Required for Token Refresh ===")
        print("Your trading PIN is required for security authentication.")
        print("This PIN will be saved securely in your .env file for future use.")

        # Use getpass for secure PIN input (hides the input)
        pin = getpass.getpass("Enter your Fyers trading PIN: ").strip()

        if pin:
            # Save PIN to environment for future use
            self.save_to_env('FYERS_PIN', pin)
            self.pin = pin
            print("PIN saved successfully to .env file")
            return pin
        else:
            raise ValueError("PIN is required for authentication")

    def generate_access_token_with_refresh(self, refresh_token: str) -> Tuple[Optional[str], Optional[str]]:
        """Generate new access token using refresh token with PIN verification"""
        url = "https://api-t1.fyers.in/api/v3/validate-refresh-token"

        # Get PIN (from env or user input)
        try:
            pin = self.get_or_request_pin()
        except ValueError as e:
            logging.error(f"PIN error: {e}")
            return None, None

        headers = {
            "Content-Type": "application/json"
        }

        data = {
            "grant_type": "refresh_token",
            "appIdHash": self.get_app_id_hash(),
            "refresh_token": refresh_token,
            "pin": pin
        }

        try:
            response = requests.post(url, headers=headers, data=json.dumps(data))
            response_data = response.json()

            if response_data.get('s') == 'ok' and 'access_token' in response_data:
                logging.info("Successfully refreshed access token with PIN verification")
                return response_data['access_token'], response_data.get('refresh_token')
            else:
                error_msg = response_data.get('message', 'Unknown error')
                error_code = response_data.get('code', 'Unknown')

                # Handle specific PIN-related errors
                if 'pin' in error_msg.lower() or 'invalid pin' in error_msg.lower():
                    logging.error(f"PIN verification failed: {error_msg}")
                    print("\n⚠️ PIN verification failed. The PIN might be incorrect.")

                    # Clear the saved PIN and retry
                    self.pin = None
                    os.environ.pop('FYERS_PIN', None)

                    retry = input("Would you like to retry with a different PIN? (y/n): ").strip().lower()
                    if retry == 'y':
                        # Recursive call to retry with new PIN
                        return self.generate_access_token_with_refresh(refresh_token)
                else:
                    logging.error(f"Error refreshing token: {error_msg} (Code: {error_code})")

                return None, None

        except requests.exceptions.RequestException as e:
            logging.error(f"Network error while refreshing token: {e}")
            return None, None
        except Exception as e:
            logging.error(f"Unexpected error while refreshing token: {e}")
            return None, None

    def get_app_id_hash(self) -> str:
        """Generate app_id_hash for API calls"""
        app_id = f"{self.client_id}:{self.secret_key}"
        return hashlib.sha256(app_id.encode()).hexdigest()

    def get_tokens_from_auth_code(self, auth_code: str) -> Tuple[Optional[str], Optional[str]]:
        """Get both access and refresh tokens from auth code"""
        url = "https://api-t1.fyers.in/api/v3/validate-authcode"

        headers = {
            "Content-Type": "application/json"
        }

        data = {
            "grant_type": "authorization_code",
            "appIdHash": self.get_app_id_hash(),
            "code": auth_code
        }

        try:
            response = requests.post(url, headers=headers, data=json.dumps(data))
            response_data = response.json()

            if response_data.get('s') == 'ok':
                return (response_data.get('access_token'),
                        response_data.get('refresh_token'))
            else:
                logging.error(f"Error getting tokens: {response_data.get('message', 'Unknown error')}")
                return None, None

        except Exception as e:
            logging.error(f"Exception while getting tokens: {e}")
            return None, None

    def is_token_valid(self, access_token: str) -> bool:
        """Check if access token is still valid"""
        if not access_token:
            return False

        try:
            url = "https://api-t1.fyers.in/api/v3/profile"
            headers = {'Authorization': f"{self.client_id}:{access_token}"}

            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                result = response.json()
                return result.get('s') == 'ok'
            return False
        except:
            return False

    def get_valid_access_token(self) -> Optional[str]:
        """Get a valid access token, using refresh token if available"""

        # First, check if current access token is still valid
        if self.access_token and self.is_token_valid(self.access_token):
            logging.info("Current access token is still valid")
            return self.access_token

        # Try to use refresh token if available
        if self.refresh_token:
            logging.info("Access token expired, trying to refresh...")
            new_access_token, new_refresh_token = self.generate_access_token_with_refresh(self.refresh_token)

            if new_access_token:
                logging.info("Successfully refreshed access token")

                # Save new tokens
                self.save_to_env('FYERS_ACCESS_TOKEN', new_access_token)
                self.access_token = new_access_token

                if new_refresh_token:
                    self.save_to_env('FYERS_REFRESH_TOKEN', new_refresh_token)
                    self.refresh_token = new_refresh_token

                return new_access_token
            else:
                logging.warning("Failed to refresh access token, need to re-authenticate")

        # If refresh failed or no refresh token, do full authentication
        return self.setup_full_authentication()

    def setup_full_authentication(self) -> Optional[str]:
        """Complete authentication flow to get new tokens"""
        print("\n=== Fyers API Full Authentication Setup ===")

        if not all([self.client_id, self.secret_key]):
            print("Missing CLIENT_ID or SECRET_KEY in environment variables")
            return None

        # Ask for PIN during initial setup if not already saved
        if not self.pin:
            print("\n📌 Trading PIN Setup")
            print("Your trading PIN will be needed for future token refreshes.")
            pin = getpass.getpass("Enter your Fyers trading PIN (will be saved securely): ").strip()
            if pin:
                self.save_to_env('FYERS_PIN', pin)
                self.pin = pin
                print("PIN saved successfully")

        # Generate auth URL
        auth_url = self.generate_auth_url()

        print(f"\n1. Open this URL: {auth_url}")
        print("2. Complete authorization and get the code")

        auth_code = input("\nEnter authorization code: ").strip()

        # Get both access and refresh tokens
        access_token, refresh_token = self.get_tokens_from_auth_code(auth_code)

        if access_token:
            print(f"\n=== Saving tokens to .env file ===")

            # Save all tokens to .env
            self.save_to_env('FYERS_CLIENT_ID', self.client_id)
            self.save_to_env('FYERS_SECRET_KEY', self.secret_key)
            self.save_to_env('FYERS_REDIRECT_URI', self.redirect_uri)
            self.save_to_env('FYERS_ACCESS_TOKEN', access_token)

            if refresh_token:
                self.save_to_env('FYERS_REFRESH_TOKEN', refresh_token)
                print(f"FYERS_REFRESH_TOKEN saved")

            print(f"\nAuthentication successful!")
            print(f"Access Token: {access_token[:20]}...")
            if refresh_token:
                print(f"Refresh Token: {refresh_token[:20]}...")

            return access_token
        else:
            print("Authentication failed!")
            return None

    def generate_auth_url(self) -> str:
        """Generate authorization URL"""
        auth_url = "https://api-t1.fyers.in/api/v3/generate-authcode"
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'state': 'sample_state'
        }

        url = f"{auth_url}?" + "&".join([f"{k}={v}" for k, v in params.items()])
        return url

    def update_pin(self) -> bool:
        """Update or change the saved PIN"""
        print("\n=== Update Trading PIN ===")
        print("This will update your saved trading PIN.")

        new_pin = getpass.getpass("Enter new PIN: ").strip()
        confirm_pin = getpass.getpass("Confirm new PIN: ").strip()

        if new_pin != confirm_pin:
            print("❌ PINs do not match!")
            return False

        if new_pin:
            self.save_to_env('FYERS_PIN', new_pin)
            self.pin = new_pin
            print("✅ PIN updated successfully")
            return True
        else:
            print("❌ Invalid PIN")
            return False


def setup_auth_only():
    """Enhanced authentication setup with refresh token and PIN support"""
    print("=== Enhanced Fyers API Authentication Setup with PIN ===")

    # Check if we already have credentials in environment
    if os.environ.get('FYERS_CLIENT_ID') and os.environ.get('FYERS_SECRET_KEY'):
        print("Found existing credentials in environment")
        auth_manager = FyersAuthManager()
        access_token = auth_manager.get_valid_access_token()

        if access_token:
            print("Authentication successful using existing/refreshed tokens!")
            return

    # Manual setup if no credentials or auth failed
    print("\n=== Manual Authentication Setup ===")
    client_id = input("Enter your Fyers Client ID: ").strip()
    secret_key = input("Enter your Fyers Secret Key: ").strip()
    redirect_uri = input("Enter Redirect URI (or press Enter for default): ").strip()

    if not redirect_uri:
        redirect_uri = "https://trade.fyers.in/api-login/redirect-to-app"

    # Update environment temporarily for this session
    os.environ['FYERS_CLIENT_ID'] = client_id
    os.environ['FYERS_SECRET_KEY'] = secret_key
    os.environ['FYERS_REDIRECT_URI'] = redirect_uri

    # Use the auth manager for enhanced authentication
    auth_manager = FyersAuthManager()
    access_token = auth_manager.setup_full_authentication()

    if access_token:
        print("\nEnhanced authentication setup completed!")
        print("Refresh token and PIN have been saved for automatic token renewal.")
    else:
        print("Authentication setup failed!")


def authenticate_fyers(config_dict: dict) -> bool:
    """Handle Fyers authentication with refresh token and PIN support"""
    auth_manager = FyersAuthManager()

    # Get valid access token (will auto-refresh if needed)
    access_token = auth_manager.get_valid_access_token()

    if access_token:
        # Update config with the valid token
        config_dict['fyers_config'].access_token = access_token
        logging.info("Fyers authentication successful")
        return True
    else:
        logging.error("Fyers authentication failed")
        return False


def test_authentication():
    """Test authentication without running strategies"""
    from config.settings import FyersConfig

    config = {
        'fyers_config': FyersConfig(
            client_id=os.environ.get('FYERS_CLIENT_ID'),
            secret_key=os.environ.get('FYERS_SECRET_KEY'),
            access_token=os.environ.get('FYERS_ACCESS_TOKEN')
        )
    }

    if authenticate_fyers(config):
        print("Authentication test successful!")

        # Test API call
        try:
            import requests
            headers = {
                'Authorization': f"{config['fyers_config'].client_id}:{config['fyers_config'].access_token}"
            }
            response = requests.get('https://api-t1.fyers.in/api/v3/profile', headers=headers)

            if response.status_code == 200:
                result = response.json()
                if result.get('s') == 'ok':
                    profile_data = result.get('data', {})
                    print(f"Profile: {profile_data.get('name', 'Unknown')}")
                    print(f"Email: {profile_data.get('email', 'Unknown')}")
                else:
                    print(f"API Error: {result.get('message')}")
            else:
                print(f"HTTP Error: {response.status_code}")

        except Exception as e:
            print(f"API test error: {e}")
    else:
        print("Authentication test failed!")


def update_pin_only():
    """Update trading PIN only"""
    auth_manager = FyersAuthManager()
    auth_manager.update_pin()