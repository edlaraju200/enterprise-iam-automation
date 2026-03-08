"""Okta API Client"""

import requests
from typing import Dict, List, Optional
from ..logger import get_logger
from ..config_manager import ConfigManager


class OktaClient:
    """Client for Okta Identity Cloud API operations"""
    
    def __init__(self, config: ConfigManager):
        """Initialize Okta client
        
        Args:
            config: Configuration manager instance
        """
        self.config = config.get_section('okta')
        self.domain = self.config['domain']
        self.api_token = self.config['api_token']
        self.base_url = f"https://{self.domain}/api/v1"
        self.logger = get_logger(__name__)
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        return {
            'Authorization': f'SSWS {self.api_token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    
    def get_users(self, limit: int = 200, search: Optional[str] = None,
                 filter_query: Optional[str] = None) -> List[Dict]:
        """Get users from Okta
        
        Args:
            limit: Maximum number of results
            search: Search query
            filter_query: Filter expression
        
        Returns:
            List of user objects
        """
        url = f"{self.base_url}/users"
        params = {'limit': limit}
        
        if search:
            params['q'] = search
        if filter_query:
            params['filter'] = filter_query
        
        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=30
            )
            response.raise_for_status()
            users = response.json()
            self.logger.info(f"Retrieved {len(users)} users from Okta")
            return users
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to get users: {e}")
            raise
    
    def create_user(self, user_profile: Dict, activate: bool = True) -> Dict:
        """Create a new user in Okta
        
        Args:
            user_profile: User profile data
            activate: Activate user immediately
        
        Returns:
            Created user object
        """
        url = f"{self.base_url}/users"
        params = {'activate': str(activate).lower()}
        payload = {
            'profile': user_profile
        }
        
        try:
            response = requests.post(
                url,
                headers=self._get_headers(),
                params=params,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            user = response.json()
            self.logger.info(f"User created in Okta: {user_profile.get('email')}")
            return user
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to create user: {e}")
            raise
    
    def update_user(self, user_id: str, user_profile: Dict) -> Dict:
        """Update user profile
        
        Args:
            user_id: User ID
            user_profile: Updated profile data
        
        Returns:
            Updated user object
        """
        url = f"{self.base_url}/users/{user_id}"
        payload = {
            'profile': user_profile
        }
        
        try:
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            user = response.json()
            self.logger.info(f"User updated in Okta: {user_id}")
            return user
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to update user: {e}")
            raise
    
    def deactivate_user(self, user_id: str) -> None:
        """Deactivate a user
        
        Args:
            user_id: User ID
        """
        url = f"{self.base_url}/users/{user_id}/lifecycle/deactivate"
        
        try:
            response = requests.post(
                url,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            self.logger.info(f"User deactivated in Okta: {user_id}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to deactivate user: {e}")
            raise
    
    def get_groups(self, query: Optional[str] = None) -> List[Dict]:
        """Get groups from Okta
        
        Args:
            query: Search query
        
        Returns:
            List of group objects
        """
        url = f"{self.base_url}/groups"
        params = {}
        
        if query:
            params['q'] = query
        
        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=30
            )
            response.raise_for_status()
            groups = response.json()
            self.logger.info(f"Retrieved {len(groups)} groups from Okta")
            return groups
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to get groups: {e}")
            raise
    
    def add_user_to_group(self, group_id: str, user_id: str) -> None:
        """Add user to a group
        
        Args:
            group_id: Group ID
            user_id: User ID
        """
        url = f"{self.base_url}/groups/{group_id}/users/{user_id}"
        
        try:
            response = requests.put(
                url,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            self.logger.info(f"User {user_id} added to group {group_id}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to add user to group: {e}")
            raise
    
    def remove_user_from_group(self, group_id: str, user_id: str) -> None:
        """Remove user from a group
        
        Args:
            group_id: Group ID
            user_id: User ID
        """
        url = f"{self.base_url}/groups/{group_id}/users/{user_id}"
        
        try:
            response = requests.delete(
                url,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            self.logger.info(f"User {user_id} removed from group {group_id}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to remove user from group: {e}")
            raise
    
    def get_user_applications(self, user_id: str) -> List[Dict]:
        """Get applications assigned to a user
        
        Args:
            user_id: User ID
        
        Returns:
            List of application objects
        """
        url = f"{self.base_url}/apps"
        params = {'filter': f'user.id eq \"{user_id}\"'}
        
        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=30
            )
            response.raise_for_status()
            apps = response.json()
            self.logger.info(f"Retrieved {len(apps)} applications for user {user_id}")
            return apps
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to get user applications: {e}")
            raise
    
    def assign_application_to_user(self, app_id: str, user_id: str, 
                                   credentials: Optional[Dict] = None) -> Dict:
        """Assign application to a user
        
        Args:
            app_id: Application ID
            user_id: User ID
            credentials: Optional app credentials
        
        Returns:
            Assignment object
        """
        url = f"{self.base_url}/apps/{app_id}/users"
        payload = {
            'id': user_id
        }
        
        if credentials:
            payload['credentials'] = credentials
        
        try:
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            assignment = response.json()
            self.logger.info(f"Application {app_id} assigned to user {user_id}")
            return assignment
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to assign application: {e}")
            raise
