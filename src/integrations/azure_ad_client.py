"""Azure AD (Entra ID) API Client using Microsoft Graph"""

import requests
from typing import Dict, List, Optional
from azure.identity import ClientSecretCredential
from ..logger import get_logger
from ..config_manager import ConfigManager


class AzureADClient:
    """Client for Azure AD (Entra ID) operations via Microsoft Graph API"""
    
    def __init__(self, config: ConfigManager):
        """Initialize Azure AD client
        
        Args:
            config: Configuration manager instance
        """
        self.config = config.get_section('azure_ad')
        self.tenant_id = self.config['tenant_id']
        self.client_id = self.config['client_id']
        self.client_secret = self.config['client_secret']
        self.logger = get_logger(__name__)
        self.graph_url = "https://graph.microsoft.com/v1.0"
        self.access_token = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Azure AD and get access token"""
        try:
            credential = ClientSecretCredential(
                tenant_id=self.tenant_id,
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            
            token = credential.get_token("https://graph.microsoft.com/.default")
            self.access_token = token.token
            self.logger.info("Azure AD authentication successful")
        except Exception as e:
            self.logger.error(f"Azure AD authentication failed: {e}")
            raise
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
    
    def get_users(self, filter_query: Optional[str] = None, 
                  select_fields: Optional[List[str]] = None) -> List[Dict]:
        """Get users from Azure AD
        
        Args:
            filter_query: OData filter query
            select_fields: Fields to include in response
        
        Returns:
            List of user objects
        """
        url = f"{self.graph_url}/users"
        params = {}
        
        if filter_query:
            params['$filter'] = filter_query
        if select_fields:
            params['$select'] = ','.join(select_fields)
        
        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=30
            )
            response.raise_for_status()
            users = response.json().get('value', [])
            self.logger.info(f"Retrieved {len(users)} users from Azure AD")
            return users
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to get users: {e}")
            raise
    
    def create_user(self, user_data: Dict) -> Dict:
        """Create a new user in Azure AD
        
        Args:
            user_data: User properties
        
        Returns:
            Created user object
        """
        url = f"{self.graph_url}/users"
        
        try:
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=user_data,
                timeout=30
            )
            response.raise_for_status()
            user = response.json()
            self.logger.info(f"User created in Azure AD: {user.get('userPrincipalName')}")
            return user
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to create user: {e}")
            raise
    
    def update_user(self, user_id: str, user_data: Dict) -> None:
        """Update user properties
        
        Args:
            user_id: User ID or userPrincipalName
            user_data: Properties to update
        """
        url = f"{self.graph_url}/users/{user_id}"
        
        try:
            response = requests.patch(
                url,
                headers=self._get_headers(),
                json=user_data,
                timeout=30
            )
            response.raise_for_status()
            self.logger.info(f"User updated in Azure AD: {user_id}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to update user: {e}")
            raise
    
    def delete_user(self, user_id: str) -> None:
        """Delete user from Azure AD
        
        Args:
            user_id: User ID or userPrincipalName
        """
        url = f"{self.graph_url}/users/{user_id}"
        
        try:
            response = requests.delete(
                url,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            self.logger.info(f"User deleted from Azure AD: {user_id}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to delete user: {e}")
            raise
    
    def get_groups(self, filter_query: Optional[str] = None) -> List[Dict]:
        """Get groups from Azure AD
        
        Args:
            filter_query: OData filter query
        
        Returns:
            List of group objects
        """
        url = f"{self.graph_url}/groups"
        params = {}
        
        if filter_query:
            params['$filter'] = filter_query
        
        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=30
            )
            response.raise_for_status()
            groups = response.json().get('value', [])
            self.logger.info(f"Retrieved {len(groups)} groups from Azure AD")
            return groups
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to get groups: {e}")
            raise
    
    def add_group_member(self, group_id: str, user_id: str) -> None:
        """Add user to a group
        
        Args:
            group_id: Group ID
            user_id: User ID
        """
        url = f"{self.graph_url}/groups/{group_id}/members/$ref"
        payload = {
            "@odata.id": f"https://graph.microsoft.com/v1.0/users/{user_id}"
        }
        
        try:
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            self.logger.info(f"User {user_id} added to group {group_id}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to add group member: {e}")
            raise
    
    def remove_group_member(self, group_id: str, user_id: str) -> None:
        """Remove user from a group
        
        Args:
            group_id: Group ID
            user_id: User ID
        """
        url = f"{self.graph_url}/groups/{group_id}/members/{user_id}/$ref"
        
        try:
            response = requests.delete(
                url,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            self.logger.info(f"User {user_id} removed from group {group_id}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to remove group member: {e}")
            raise
    
    def get_user_licenses(self, user_id: str) -> List[Dict]:
        """Get assigned licenses for a user
        
        Args:
            user_id: User ID or userPrincipalName
        
        Returns:
            List of assigned licenses
        """
        url = f"{self.graph_url}/users/{user_id}/licenseDetails"
        
        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            licenses = response.json().get('value', [])
            self.logger.info(f"Retrieved {len(licenses)} licenses for user {user_id}")
            return licenses
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to get user licenses: {e}")
            raise
    
    def assign_license(self, user_id: str, sku_id: str) -> None:
        """Assign license to a user
        
        Args:
            user_id: User ID or userPrincipalName
            sku_id: License SKU ID
        """
        url = f"{self.graph_url}/users/{user_id}/assignLicense"
        payload = {
            "addLicenses": [
                {
                    "skuId": sku_id
                }
            ],
            "removeLicenses": []
        }
        
        try:
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            self.logger.info(f"License {sku_id} assigned to user {user_id}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to assign license: {e}")
            raise
