"""Automated User Provisioning Workflow

Orchestrates user lifecycle operations across SailPoint, Azure AD, Okta, and CyberArk
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.config_manager import ConfigManager
from src.integrations import SailPointClient, AzureADClient, OktaClient, CyberArkClient
from src.logger import get_logger
from typing import Dict, List
import time


class UserProvisioningWorkflow:
    """Automate user provisioning across IAM platforms"""
    
    def __init__(self):
        """Initialize workflow with all IAM clients"""
        self.config = ConfigManager()
        self.logger = get_logger(__name__)
        
        # Initialize all clients
        try:
            self.sailpoint = SailPointClient(self.config)
            self.azure_ad = AzureADClient(self.config)
            self.okta = OktaClient(self.config)
            self.cyberark = CyberArkClient(self.config)
            self.logger.info("All IAM clients initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize IAM clients: {e}")
            raise
    
    def provision_new_user(self, user_data: Dict) -> Dict:
        """Provision a new user across all IAM systems
        
        Args:
            user_data: User information including:
                - first_name
                - last_name
                - email
                - department
                - job_title
                - manager_email
        
        Returns:
            Dictionary with provisioning results from each system
        """
        results = {
            'azure_ad': None,
            'okta': None,
            'sailpoint': None,
            'cyberark': None,
            'status': 'success',
            'errors': []
        }
        
        self.logger.info(f"Starting user provisioning for: {user_data['email']}")
        
        # Step 1: Create user in Azure AD
        try:
            azure_user_data = {
                'accountEnabled': True,
                'displayName': f"{user_data['first_name']} {user_data['last_name']}",
                'mailNickname': user_data['email'].split('@')[0],
                'userPrincipalName': user_data['email'],
                'passwordProfile': {
                    'forceChangePasswordNextSignIn': True,
                    'password': 'TempPassword123!'  # Generate secure password
                },
                'jobTitle': user_data.get('job_title'),
                'department': user_data.get('department')
            }
            
            azure_user = self.azure_ad.create_user(azure_user_data)
            results['azure_ad'] = azure_user['id']
            self.logger.info(f"User created in Azure AD: {azure_user['id']}")
            
            # Wait for replication
            time.sleep(2)
            
        except Exception as e:
            error_msg = f"Azure AD provisioning failed: {str(e)}"
            self.logger.error(error_msg)
            results['errors'].append(error_msg)
            results['status'] = 'partial'
        
        # Step 2: Create user in Okta
        try:
            okta_profile = {
                'firstName': user_data['first_name'],
                'lastName': user_data['last_name'],
                'email': user_data['email'],
                'login': user_data['email'],
                'mobilePhone': user_data.get('phone'),
                'department': user_data.get('department'),
                'title': user_data.get('job_title')
            }
            
            okta_user = self.okta.create_user(okta_profile, activate=True)
            results['okta'] = okta_user['id']
            self.logger.info(f"User created in Okta: {okta_user['id']}")
            
        except Exception as e:
            error_msg = f"Okta provisioning failed: {str(e)}"
            self.logger.error(error_msg)
            results['errors'].append(error_msg)
            results['status'] = 'partial'
        
        # Step 3: Trigger SailPoint identity refresh
        try:
            # In production, this would trigger account aggregation
            # For now, we'll simulate checking for the identity
            identities = self.sailpoint.get_identities(
                limit=10,
                filters={'email': user_data['email']}
            )
            
            if identities:
                results['sailpoint'] = identities[0]['id']
                self.logger.info(f"Identity found in SailPoint: {identities[0]['id']}")
            else:
                self.logger.warning("Identity not yet synced to SailPoint - may need aggregation")
                
        except Exception as e:
            error_msg = f"SailPoint check failed: {str(e)}"
            self.logger.error(error_msg)
            results['errors'].append(error_msg)
        
        self.logger.info(f"User provisioning completed with status: {results['status']}")
        return results
    
    def deprovision_user(self, user_email: str) -> Dict:
        """Deprovision user from all IAM systems
        
        Args:
            user_email: User's email address
        
        Returns:
            Dictionary with deprovisioning results
        """
        results = {
            'azure_ad': False,
            'okta': False,
            'status': 'success',
            'errors': []
        }
        
        self.logger.info(f"Starting user deprovisioning for: {user_email}")
        
        # Deprovision from Azure AD
        try:
            users = self.azure_ad.get_users(
                filter_query=f"userPrincipalName eq '{user_email}'"
            )
            
            if users:
                self.azure_ad.delete_user(users[0]['id'])
                results['azure_ad'] = True
                self.logger.info(f"User deprovisioned from Azure AD")
                
        except Exception as e:
            error_msg = f"Azure AD deprovisioning failed: {str(e)}"
            self.logger.error(error_msg)
            results['errors'].append(error_msg)
            results['status'] = 'partial'
        
        # Deprovision from Okta
        try:
            users = self.okta.get_users(search=user_email)
            
            if users:
                self.okta.deactivate_user(users[0]['id'])
                results['okta'] = True
                self.logger.info(f"User deprovisioned from Okta")
                
        except Exception as e:
            error_msg = f"Okta deprovisioning failed: {str(e)}"
            self.logger.error(error_msg)
            results['errors'].append(error_msg)
            results['status'] = 'partial'
        
        self.logger.info(f"User deprovisioning completed with status: {results['status']}")
        return results
    
    def bulk_provision_users(self, users_list: List[Dict]) -> Dict:
        """Provision multiple users in batch
        
        Args:
            users_list: List of user data dictionaries
        
        Returns:
            Summary of provisioning results
        """
        summary = {
            'total': len(users_list),
            'successful': 0,
            'failed': 0,
            'partial': 0,
            'details': []
        }
        
        self.logger.info(f"Starting bulk user provisioning for {len(users_list)} users")
        
        for user_data in users_list:
            try:
                result = self.provision_new_user(user_data)
                summary['details'].append({
                    'email': user_data['email'],
                    'status': result['status'],
                    'errors': result['errors']
                })
                
                if result['status'] == 'success':
                    summary['successful'] += 1
                elif result['status'] == 'partial':
                    summary['partial'] += 1
                else:
                    summary['failed'] += 1
                    
                # Rate limiting
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Bulk provisioning failed for {user_data['email']}: {e}")
                summary['failed'] += 1
                summary['details'].append({
                    'email': user_data['email'],
                    'status': 'failed',
                    'errors': [str(e)]
                })
        
        self.logger.info(
            f"Bulk provisioning complete. "
            f"Success: {summary['successful']}, "
            f"Partial: {summary['partial']}, "
            f"Failed: {summary['failed']}"
        )
        
        return summary


if __name__ == "__main__":
    # Example usage
    workflow = UserProvisioningWorkflow()
    
    # Example: Provision a single user
    new_user = {
        'first_name': 'John',
        'last_name': 'Doe',
        'email': 'john.doe@example.com',
        'department': 'Engineering',
        'job_title': 'Software Engineer',
        'phone': '+1-555-0123'
    }
    
    result = workflow.provision_new_user(new_user)
    print(f"Provisioning result: {result}")
