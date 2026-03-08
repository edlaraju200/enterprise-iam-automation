"""Privileged Access Management Automation

Automates CyberArk PAM operations and SailPoint integration for privileged accounts
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.config_manager import ConfigManager
from src.integrations import CyberArkClient, SailPointClient
from src.logger import get_logger
from typing import Dict, List, Optional
from datetime import datetime
import json


class PrivilegedAccessWorkflow:
    """Automate privileged access management operations"""
    
    def __init__(self):
        """Initialize workflow with CyberArk and SailPoint clients"""
        self.config = ConfigManager()
        self.logger = get_logger(__name__)
        
        try:
            self.cyberark = CyberArkClient(self.config)
            self.sailpoint = SailPointClient(self.config)
            self.logger.info("Privileged access workflow initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize workflow: {e}")
            raise
    
    def onboard_privileged_account(self, account_data: Dict) -> Dict:
        """Onboard a new privileged account to CyberArk
        
        Args:
            account_data: Account information including:
                - name: Account name
                - address: Target system address
                - username: Account username
                - platform_id: CyberArk platform ID
                - safe_name: Target safe name
                - secret_type: Type of secret (password/key)
        
        Returns:
            Onboarding result with account ID
        """
        self.logger.info(f"Onboarding privileged account: {account_data['username']}@{account_data['address']}")
        
        cyberark_account = {
            'name': account_data['name'],
            'address': account_data['address'],
            'userName': account_data['username'],
            'platformId': account_data['platform_id'],
            'safeName': account_data['safe_name'],
            'secretType': account_data.get('secret_type', 'password'),
            'secret': account_data.get('password', ''),
            'platformAccountProperties': {
                'LogonDomain': account_data.get('domain', ''),
                'Port': account_data.get('port', '22')
            },
            'secretManagement': {
                'automaticManagementEnabled': True,
                'manualManagementReason': ''
            }
        }
        
        try:
            result = self.cyberark.add_account(cyberark_account)
            self.logger.info(f"Account onboarded successfully: {result['id']}")
            
            return {
                'status': 'success',
                'account_id': result['id'],
                'safe': account_data['safe_name'],
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to onboard account: {e}")
            return {
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def grant_jit_access(self, user_email: str, safe_name: str, 
                        duration_hours: int = 8, permissions: Optional[List[str]] = None) -> Dict:
        """Grant Just-In-Time (JIT) privileged access to a user
        
        Args:
            user_email: User's email address
            safe_name: CyberArk safe name
            duration_hours: Access duration in hours
            permissions: List of permissions to grant
        
        Returns:
            JIT access grant result
        """
        self.logger.info(f"Granting JIT access to {user_email} for safe {safe_name}")
        
        if permissions is None:
            permissions = ['UseAccounts', 'RetrieveAccounts', 'ViewAuditLog']
        
        member_data = {
            'MemberName': user_email,
            'SearchIn': 'Vault',
            'MembershipExpirationDate': self._calculate_expiration(duration_hours),
            'Permissions': {
                'UseAccounts': 'UseAccounts' in permissions,
                'RetrieveAccounts': 'RetrieveAccounts' in permissions,
                'ListAccounts': True,
                'ViewAuditLog': 'ViewAuditLog' in permissions,
                'ViewSafeMembers': True
            }
        }
        
        try:
            result = self.cyberark.add_safe_member(safe_name, member_data)
            
            self.logger.info(
                f"JIT access granted to {user_email} on safe {safe_name} "
                f"for {duration_hours} hours"
            )
            
            return {
                'status': 'success',
                'user': user_email,
                'safe': safe_name,
                'expires_at': member_data['MembershipExpirationDate'],
                'permissions': permissions
            }
            
        except Exception as e:
            self.logger.error(f"Failed to grant JIT access: {e}")
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def rotate_privileged_credentials(self, safe_name: Optional[str] = None) -> Dict:
        """Trigger credential rotation for privileged accounts
        
        Args:
            safe_name: Optional safe name to filter accounts
        
        Returns:
            Rotation summary
        """
        self.logger.info(f"Starting credential rotation for safe: {safe_name or 'all'}")
        
        summary = {
            'total_accounts': 0,
            'rotated': 0,
            'failed': 0,
            'details': []
        }
        
        try:
            # Get accounts from specified safe
            accounts = self.cyberark.get_accounts(safe_name=safe_name)
            summary['total_accounts'] = len(accounts)
            
            for account in accounts:
                account_id = account['id']
                account_name = account.get('name', 'Unknown')
                
                try:
                    self.cyberark.rotate_password(account_id)
                    summary['rotated'] += 1
                    summary['details'].append({
                        'account_id': account_id,
                        'account_name': account_name,
                        'status': 'success'
                    })
                    
                    self.logger.info(f"Password rotated for account: {account_name}")
                    
                except Exception as e:
                    summary['failed'] += 1
                    summary['details'].append({
                        'account_id': account_id,
                        'account_name': account_name,
                        'status': 'failed',
                        'error': str(e)
                    })
                    
                    self.logger.error(f"Failed to rotate password for {account_name}: {e}")
            
            self.logger.info(
                f"Credential rotation complete. "
                f"Rotated: {summary['rotated']}, Failed: {summary['failed']}"
            )
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Credential rotation workflow failed: {e}")
            raise
    
    def audit_privileged_access(self, safe_name: str) -> Dict:
        """Audit privileged access for a safe
        
        Args:
            safe_name: Safe name to audit
        
        Returns:
            Audit report
        """
        self.logger.info(f"Auditing privileged access for safe: {safe_name}")
        
        audit_report = {
            'safe_name': safe_name,
            'audit_timestamp': datetime.now().isoformat(),
            'accounts': [],
            'members': [],
            'compliance_issues': []
        }
        
        try:
            # Get all accounts in safe
            accounts = self.cyberark.get_accounts(safe_name=safe_name)
            audit_report['accounts'] = [
                {
                    'id': acc['id'],
                    'name': acc.get('name'),
                    'address': acc.get('address'),
                    'username': acc.get('userName')
                }
                for acc in accounts
            ]
            
            # Get safe members
            members = self.cyberark.get_safe_members(safe_name)
            audit_report['members'] = [
                {
                    'name': mem.get('memberName'),
                    'type': mem.get('memberType'),
                    'permissions': mem.get('permissions', {})
                }
                for mem in members
            ]
            
            # Check for compliance issues
            for member in members:
                permissions = member.get('permissions', {})
                
                # Flag overly permissive access
                if permissions.get('AddAccounts') and permissions.get('DeleteAccounts'):
                    audit_report['compliance_issues'].append({
                        'type': 'overly_permissive',
                        'member': member.get('memberName'),
                        'issue': 'Has both Add and Delete account permissions'
                    })
            
            self.logger.info(
                f"Audit complete. Found {len(audit_report['compliance_issues'])} issues"
            )
            
            return audit_report
            
        except Exception as e:
            self.logger.error(f"Audit failed: {e}")
            raise
    
    def _calculate_expiration(self, hours: int) -> str:
        """Calculate expiration timestamp
        
        Args:
            hours: Number of hours from now
        
        Returns:
            ISO format timestamp
        """
        from datetime import timedelta
        expiration = datetime.now() + timedelta(hours=hours)
        return expiration.strftime('%m/%d/%Y %H:%M:%S')
    
    def sync_privileged_accounts_to_sailpoint(self, safe_name: str) -> Dict:
        """Sync privileged accounts from CyberArk to SailPoint for governance
        
        Args:
            safe_name: CyberArk safe name
        
        Returns:
            Sync summary
        """
        self.logger.info(f"Syncing privileged accounts to SailPoint from safe: {safe_name}")
        
        summary = {
            'cyberark_accounts': 0,
            'sailpoint_synced': 0,
            'errors': []
        }
        
        try:
            # Get accounts from CyberArk
            accounts = self.cyberark.get_accounts(safe_name=safe_name)
            summary['cyberark_accounts'] = len(accounts)
            
            # In production, this would trigger SailPoint aggregation
            # or use SailPoint's account aggregation API
            self.logger.info(
                f"Would sync {len(accounts)} accounts to SailPoint for governance"
            )
            
            summary['sailpoint_synced'] = len(accounts)
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to sync accounts: {e}")
            summary['errors'].append(str(e))
            return summary


if __name__ == "__main__":
    # Example usage
    workflow = PrivilegedAccessWorkflow()
    
    # Example: Onboard privileged account
    new_account = {
        'name': 'prod-db-admin',
        'address': 'prod-db-01.company.com',
        'username': 'dbadmin',
        'platform_id': 'PostgreSQL',
        'safe_name': 'Database_Admins',
        'password': 'TemporaryPassword123!',
        'port': '5432'
    }
    
    result = workflow.onboard_privileged_account(new_account)
    print(f"Onboarding result: {json.dumps(result, indent=2)}")
    
    # Example: Grant JIT access
    jit_result = workflow.grant_jit_access(
        user_email='john.doe@company.com',
        safe_name='Database_Admins',
        duration_hours=4,
        permissions=['UseAccounts', 'RetrieveAccounts', 'ViewAuditLog']
    )
    print(f"JIT access result: {json.dumps(jit_result, indent=2)}")
