"""CyberArk PAM API Client"""

import requests
from typing import Dict, List, Optional
from ..logger import get_logger
from ..config_manager import ConfigManager


class CyberArkClient:
    """Client for CyberArk Privileged Access Management API"""
    
    def __init__(self, config: ConfigManager):
        """Initialize CyberArk client
        
        Args:
            config: Configuration manager instance
        """
        self.config = config.get_section('cyberark')
        self.base_url = self.config['base_url']
        self.username = self.config['username']
        self.logger = get_logger(__name__)
        self.session_token = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with CyberArk PVWA"""
        auth_url = f"{self.base_url}/PasswordVault/API/Auth/CyberArk/Logon"
        
        # Note: In production, use secure credential retrieval
        payload = {
            'username': self.username,
            'password': 'PLACEHOLDER_USE_VAULT'  # Replace with secure method
        }
        
        try:
            response = requests.post(
                auth_url,
                json=payload,
                verify=True,
                timeout=30
            )
            response.raise_for_status()
            self.session_token = response.json()
            self.logger.info("CyberArk authentication successful")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"CyberArk authentication failed: {e}")
            raise
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        return {
            'Authorization': self.session_token,
            'Content-Type': 'application/json'
        }
    
    def get_accounts(self, safe_name: Optional[str] = None, 
                    search: Optional[str] = None) -> List[Dict]:
        """Get privileged accounts from CyberArk
        
        Args:
            safe_name: Filter by safe name
            search: Search keyword
        
        Returns:
            List of account objects
        """
        url = f"{self.base_url}/PasswordVault/API/Accounts"
        params = {}
        
        if safe_name:
            params['filter'] = f'safeName eq {safe_name}'
        if search:
            params['search'] = search
        
        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=30
            )
            response.raise_for_status()
            accounts = response.json().get('value', [])
            self.logger.info(f"Retrieved {len(accounts)} accounts from CyberArk")
            return accounts
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to get accounts: {e}")
            raise
    
    def add_account(self, account_data: Dict) -> Dict:
        """Add a new privileged account to CyberArk
        
        Args:
            account_data: Account configuration
        
        Returns:
            Created account object
        """
        url = f"{self.base_url}/PasswordVault/API/Accounts"
        
        try:
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=account_data,
                timeout=30
            )
            response.raise_for_status()
            account = response.json()
            self.logger.info(f"Account added to CyberArk: {account.get('id')}")
            return account
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to add account: {e}")
            raise
    
    def get_safe_members(self, safe_name: str) -> List[Dict]:
        """Get members of a safe
        
        Args:
            safe_name: Safe name
        
        Returns:
            List of safe members
        """
        url = f"{self.base_url}/PasswordVault/API/Safes/{safe_name}/Members"
        
        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            members = response.json().get('value', [])
            self.logger.info(f"Retrieved {len(members)} members from safe: {safe_name}")
            return members
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to get safe members: {e}")
            raise
    
    def add_safe_member(self, safe_name: str, member_data: Dict) -> Dict:
        """Add a member to a safe
        
        Args:
            safe_name: Safe name
            member_data: Member configuration
        
        Returns:
            Added member object
        """
        url = f"{self.base_url}/PasswordVault/API/Safes/{safe_name}/Members"
        
        try:
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=member_data,
                timeout=30
            )
            response.raise_for_status()
            member = response.json()
            self.logger.info(f"Member added to safe {safe_name}: {member_data.get('MemberName')}")
            return member
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to add safe member: {e}")
            raise
    
    def rotate_password(self, account_id: str) -> Dict:
        """Trigger immediate password rotation for an account
        
        Args:
            account_id: Account ID
        
        Returns:
            Rotation response
        """
        url = f"{self.base_url}/PasswordVault/API/Accounts/{account_id}/Change"
        
        try:
            response = requests.post(
                url,
                headers=self._get_headers(),
                json={'ChangeEntireGroup': False},
                timeout=30
            )
            response.raise_for_status()
            self.logger.info(f"Password rotation triggered for account: {account_id}")
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to rotate password: {e}")
            raise
    
    def logoff(self):
        """Logoff from CyberArk session"""
        url = f"{self.base_url}/PasswordVault/API/Auth/Logoff"
        
        try:
            response = requests.post(
                url,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            self.logger.info("CyberArk session logged off successfully")
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Logoff failed: {e}")
