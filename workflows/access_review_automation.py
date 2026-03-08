"""Automated Access Review and Certification Workflow

Automates access certification campaigns and compliance reporting
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.config_manager import ConfigManager
from src.integrations import SailPointClient, AzureADClient, OktaClient
from src.logger import get_logger
from typing import Dict, List
from datetime import datetime, timedelta
import pandas as pd


class AccessReviewWorkflow:
    """Automate access review and certification processes"""
    
    def __init__(self):
        """Initialize workflow with IAM clients"""
        self.config = ConfigManager()
        self.logger = get_logger(__name__)
        
        try:
            self.sailpoint = SailPointClient(self.config)
            self.azure_ad = AzureADClient(self.config)
            self.okta = OktaClient(self.config)
            self.logger.info("Access review workflow initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize workflow: {e}")
            raise
    
    def create_quarterly_certification(self, campaign_name: str) -> Dict:
        """Create quarterly access certification campaign in SailPoint
        
        Args:
            campaign_name: Name for the certification campaign
        
        Returns:
            Campaign creation result
        """
        self.logger.info(f"Creating quarterly certification: {campaign_name}")
        
        # Calculate campaign dates
        start_date = datetime.now()
        end_date = start_date + timedelta(days=30)
        
        campaign_config = {
            'name': campaign_name,
            'description': f'Quarterly Access Certification - {start_date.strftime("%Y Q%q")}',
            'type': 'Manager',
            'identityIdList': [],  # Empty means all identities
            'accessConstraints': [
                {
                    'type': 'ENTITLEMENT',
                    'operator': 'ALL'
                }
            ],
            'campaignOwner': {
                'type': 'IDENTITY',
                'id': 'admin-identity-id'  # Replace with actual admin ID
            },
            'deadline': end_date.isoformat(),
            'emailNotificationEnabled': True,
            'autoRevokeAllowed': True
        }
        
        try:
            campaign = self.sailpoint.start_certification_campaign(campaign_config)
            self.logger.info(f"Campaign created successfully: {campaign['id']}")
            return campaign
        except Exception as e:
            self.logger.error(f"Failed to create certification campaign: {e}")
            raise
    
    def generate_access_report(self, output_file: str = "access_report.xlsx") -> str:
        """Generate comprehensive access report across all systems
        
        Args:
            output_file: Output Excel file path
        
        Returns:
            Path to generated report
        """
        self.logger.info("Generating comprehensive access report")
        
        report_data = {
            'azure_ad': [],
            'okta': [],
            'sailpoint': []
        }
        
        # Collect Azure AD data
        try:
            azure_users = self.azure_ad.get_users(
                select_fields=['id', 'displayName', 'userPrincipalName', 
                             'accountEnabled', 'createdDateTime']
            )
            
            for user in azure_users:
                report_data['azure_ad'].append({
                    'User ID': user['id'],
                    'Display Name': user.get('displayName'),
                    'Email': user.get('userPrincipalName'),
                    'Enabled': user.get('accountEnabled'),
                    'Created': user.get('createdDateTime')
                })
                
            self.logger.info(f"Collected {len(azure_users)} Azure AD users")
            
        except Exception as e:
            self.logger.error(f"Failed to collect Azure AD data: {e}")
        
        # Collect Okta data
        try:
            okta_users = self.okta.get_users(limit=200)
            
            for user in okta_users:
                profile = user.get('profile', {})
                report_data['okta'].append({
                    'User ID': user['id'],
                    'Display Name': f"{profile.get('firstName', '')} {profile.get('lastName', '')}",
                    'Email': profile.get('email'),
                    'Status': user.get('status'),
                    'Created': user.get('created')
                })
                
            self.logger.info(f"Collected {len(okta_users)} Okta users")
            
        except Exception as e:
            self.logger.error(f"Failed to collect Okta data: {e}")
        
        # Collect SailPoint data
        try:
            identities = self.sailpoint.get_identities(limit=250)
            
            for identity in identities:
                report_data['sailpoint'].append({
                    'Identity ID': identity['id'],
                    'Display Name': identity.get('name'),
                    'Email': identity.get('email'),
                    'Manager': identity.get('manager', {}).get('name', 'N/A'),
                    'Department': identity.get('attributes', {}).get('department')
                })
                
            self.logger.info(f"Collected {len(identities)} SailPoint identities")
            
        except Exception as e:
            self.logger.error(f"Failed to collect SailPoint data: {e}")
        
        # Generate Excel report
        try:
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                # Write each sheet
                if report_data['azure_ad']:
                    df_azure = pd.DataFrame(report_data['azure_ad'])
                    df_azure.to_excel(writer, sheet_name='Azure AD Users', index=False)
                
                if report_data['okta']:
                    df_okta = pd.DataFrame(report_data['okta'])
                    df_okta.to_excel(writer, sheet_name='Okta Users', index=False)
                
                if report_data['sailpoint']:
                    df_sp = pd.DataFrame(report_data['sailpoint'])
                    df_sp.to_excel(writer, sheet_name='SailPoint Identities', index=False)
                
                # Summary sheet
                summary_data = {
                    'System': ['Azure AD', 'Okta', 'SailPoint'],
                    'User Count': [
                        len(report_data['azure_ad']),
                        len(report_data['okta']),
                        len(report_data['sailpoint'])
                    ],
                    'Report Generated': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')] * 3
                }
                df_summary = pd.DataFrame(summary_data)
                df_summary.to_excel(writer, sheet_name='Summary', index=False)
            
            self.logger.info(f"Access report generated: {output_file}")
            return output_file
            
        except Exception as e:
            self.logger.error(f"Failed to generate Excel report: {e}")
            raise
    
    def identify_inactive_accounts(self, days_inactive: int = 90) -> List[Dict]:
        """Identify inactive user accounts across systems
        
        Args:
            days_inactive: Number of days to consider account inactive
        
        Returns:
            List of inactive accounts
        """
        self.logger.info(f"Identifying accounts inactive for {days_inactive} days")
        
        inactive_accounts = []
        cutoff_date = datetime.now() - timedelta(days=days_inactive)
        
        # Check Azure AD for inactive users
        try:
            azure_users = self.azure_ad.get_users()
            
            for user in azure_users:
                # In production, check lastSignInDateTime
                # This is a simplified example
                created_date = datetime.fromisoformat(
                    user.get('createdDateTime', '').replace('Z', '+00:00')
                )
                
                if created_date < cutoff_date:
                    inactive_accounts.append({
                        'system': 'Azure AD',
                        'user_id': user['id'],
                        'email': user.get('userPrincipalName'),
                        'last_activity': 'Unknown',
                        'recommendation': 'Review and consider deprovisioning'
                    })
                    
        except Exception as e:
            self.logger.error(f"Failed to check Azure AD inactive accounts: {e}")
        
        self.logger.info(f"Found {len(inactive_accounts)} potentially inactive accounts")
        return inactive_accounts


if __name__ == "__main__":
    # Example usage
    workflow = AccessReviewWorkflow()
    
    # Generate access report
    report_path = workflow.generate_access_report("reports/quarterly_access_review.xlsx")
    print(f"Access report generated: {report_path}")
    
    # Identify inactive accounts
    inactive = workflow.identify_inactive_accounts(days_inactive=90)
    print(f"Found {len(inactive)} inactive accounts")
