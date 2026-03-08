"""SailPoint IdentityIQ/IdentityNow API Client"""

import requests
from typing import Dict, List, Optional, Any
from ..logger import get_logger
from ..config_manager import ConfigManager


class SailPointClient:
    """Client for SailPoint IdentityIQ/IdentityNow API operations"""
    
    def __init__(self, config: ConfigManager):
        """Initialize SailPoint client
        
        Args:
            config: Configuration manager instance
        """
        self.config = config.get_section('sailpoint')
        self.base_url = self.config['base_url']
        self.client_id = self.config['client_id']
        self.client_secret = self.config['client_secret']
        self.logger = get_logger(__name__)
        self.access_token = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with SailPoint API"""
        auth_url = f"{self.base_url}/oauth/token"
        
        try:
            response = requests.post(
                auth_url,
                json={
                    'grant_type': 'client_credentials',
                    'client_id': self.client_id,
                    'client_secret': self.client_secret
                },
                timeout=30
            )
            response.raise_for_status()
            self.access_token = response.json()['access_token']
            self.logger.info("SailPoint authentication successful")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"SailPoint authentication failed: {e}")
            raise
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
    
    def get_identities(self, limit: int = 250, offset: int = 0, 
                       filters: Optional[Dict] = None) -> List[Dict]:
        """Get identities from SailPoint
        
        Args:
            limit: Maximum number of results
            offset: Pagination offset
            filters: Optional filter parameters
        
        Returns:
            List of identity objects
        """
        url = f"{self.base_url}/v3/identities"
        params = {'limit': limit, 'offset': offset}
        
        if filters:
            params.update(filters)
        
        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=30
            )
            response.raise_for_status()
            identities = response.json()
            self.logger.info(f"Retrieved {len(identities)} identities from SailPoint")
            return identities
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to get identities: {e}")
            raise
    
    def create_access_request(self, identity_id: str, 
                             access_items: List[Dict]) -> Dict:
        """Create access request for an identity
        
        Args:
            identity_id: Target identity ID
            access_items: List of access items to request
        
        Returns:
            Access request response
        """
        url = f"{self.base_url}/v3/access-requests"
        payload = {
            'requestedFor': identity_id,
            'requestType': 'GRANT_ACCESS',
            'requestedItems': access_items
        }
        
        try:
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            self.logger.info(f"Access request created for identity: {identity_id}")
            return result
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to create access request: {e}")
            raise
    
    def get_access_profiles(self, limit: int = 250) -> List[Dict]:
        """Get access profiles from SailPoint
        
        Args:
            limit: Maximum number of results
        
        Returns:
            List of access profile objects
        """
        url = f"{self.base_url}/v3/access-profiles"
        params = {'limit': limit}
        
        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=30
            )
            response.raise_for_status()
            profiles = response.json()
            self.logger.info(f"Retrieved {len(profiles)} access profiles")
            return profiles
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to get access profiles: {e}")
            raise
    
    def start_certification_campaign(self, campaign_config: Dict) -> Dict:
        """Start an access certification campaign
        
        Args:
            campaign_config: Campaign configuration
        
        Returns:
            Campaign creation response
        """
        url = f"{self.base_url}/v3/certification-campaigns"
        
        try:
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=campaign_config,
                timeout=30
            )
            response.raise_for_status()
            campaign = response.json()
            self.logger.info(f"Certification campaign created: {campaign.get('id')}")
            return campaign
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to start certification campaign: {e}")
            raise
    
    def get_account(self, account_id: str) -> Dict:
        """Get account details
        
        Args:
            account_id: Account ID
        
        Returns:
            Account object
        """
        url = f"{self.base_url}/v3/accounts/{account_id}"
        
        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to get account {account_id}: {e}")
            raise
