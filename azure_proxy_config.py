"""
Azure-optimized proxy configuration for Google Scholar scraping
Supports multiple proxy providers that work well with Azure hosting
"""

import os
from scholarly import ProxyGenerator
import requests
from typing import Optional, Dict, List
import random
import time

class AzureProxyManager:
    """
    Manages proxy configuration for Azure-hosted applications
    Supports multiple proxy strategies with fallback options
    """
    
    def __init__(self):
        self.proxy_generator = ProxyGenerator()
        self.current_proxy = None
        self.proxy_type = None
        
    def setup_scraperapi_proxy(self, api_key: str) -> bool:
        """
        Setup ScraperAPI proxy (Recommended for Azure)
        ScraperAPI handles rotating proxies, CAPTCHAs, and retries automatically
        Get API key from: https://www.scraperapi.com/
        """
        try:
            if not api_key or api_key == "":
                print("ScraperAPI key not provided")
                return False
            
            # Use ScraperAPI directly with requests instead of scholarly's proxy
            # ScraperAPI URL format: http://api.scraperapi.com?api_key=KEY&url=TARGET_URL
            proxy_url = f"http://scraperapi:{api_key}@proxy-server.scraperapi.com:8001"
            
            from scholarly import scholarly
            
            # Configure proxies for requests
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            
            # Test the proxy first
            test_response = requests.get(
                'http://httpbin.org/ip',
                proxies=proxies,
                timeout=10,
                verify=False  # Disable SSL verification for proxy
            )
            
            if test_response.status_code == 200:
                self.current_proxy = proxies
                self.proxy_type = "ScraperAPI"
                print(f"✅ ScraperAPI proxy configured successfully")
                print(f"   IP: {test_response.json()['origin']}")
                
                # Set up scholarly to use the proxy
                scholarly._SCHOLARLY_SESSION = None  # Reset session
                import requests as req
                session = req.Session()
                session.proxies = proxies
                session.verify = False  # Disable SSL verification
                scholarly._SCHOLARLY_SESSION = session
                
                return True
            return False
        except Exception as e:
            print(f"❌ ScraperAPI setup failed: {e}")
            return False
    
    def setup_smartproxy_proxy(self, username: str, password: str) -> bool:
        """
        Setup SmartProxy (Good for Azure with residential IPs)
        Get credentials from: https://smartproxy.com/
        """
        try:
            if not username or not password:
                print("SmartProxy credentials not provided")
                return False
                
            proxy_url = f"http://{username}:{password}@gate.smartproxy.com:7000"
            
            from scholarly import scholarly
            # Configure proxy manually
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            
            # Test the proxy
            test_response = requests.get(
                'http://httpbin.org/ip',
                proxies=proxies,
                timeout=10
            )
            
            if test_response.status_code == 200:
                self.current_proxy = proxies
                self.proxy_type = "SmartProxy"
                print(f"✅ SmartProxy configured successfully. IP: {test_response.json()['origin']}")
                return True
            return False
        except Exception as e:
            print(f"❌ SmartProxy setup failed: {e}")
            return False
    
    def setup_brightdata_proxy(self, username: str, password: str, zone: str = "residential") -> bool:
        """
        Setup BrightData/Luminati proxy (Enterprise-grade, works great with Azure)
        Get credentials from: https://brightdata.com/
        """
        try:
            if not username or not password:
                print("BrightData credentials not provided")
                return False
            
            # BrightData uses port 22225 for residential proxies
            port = 22225 if zone == "residential" else 22225
            success = self.proxy_generator.Luminati(
                usr=username,
                passwd=password,
                port=port
            )
            
            if success:
                from scholarly import scholarly
                scholarly.use_proxy(self.proxy_generator)
                self.proxy_type = "BrightData"
                print("✅ BrightData proxy configured successfully")
                return True
            return False
        except Exception as e:
            print(f"❌ BrightData setup failed: {e}")
            return False
    
    def setup_tor_proxy(self) -> bool:
        """
        Setup Tor proxy (Free option, but slower)
        Requires Tor to be installed and running on Azure VM
        """
        try:
            success = self.proxy_generator.Tor_External(tor_sock_port=9050, tor_control_port=9051)
            if success:
                from scholarly import scholarly
                scholarly.use_proxy(self.proxy_generator)
                self.proxy_type = "Tor"
                print("✅ Tor proxy configured successfully")
                return True
            return False
        except Exception as e:
            print(f"❌ Tor setup failed: {e}")
            return False
    
    def setup_custom_proxy_list(self, proxy_list: List[str]) -> bool:
        """
        Setup custom proxy list (for your own proxy servers)
        proxy_list format: ['http://proxy1:port', 'http://proxy2:port', ...]
        """
        try:
            if not proxy_list:
                print("No proxy list provided")
                return False
            
            # Pick a random proxy from the list
            proxy = random.choice(proxy_list)
            proxies = {
                'http': proxy,
                'https': proxy
            }
            
            # Test the proxy
            test_response = requests.get(
                'http://httpbin.org/ip',
                proxies=proxies,
                timeout=10
            )
            
            if test_response.status_code == 200:
                self.current_proxy = proxies
                self.proxy_type = "Custom"
                print(f"✅ Custom proxy configured. IP: {test_response.json()['origin']}")
                return True
            return False
        except Exception as e:
            print(f"❌ Custom proxy setup failed: {e}")
            return False
    
    def setup_azure_managed_proxy(self) -> bool:
        """
        Setup Azure-specific proxy if running on Azure VM with NAT Gateway
        This uses Azure's native networking features
        """
        try:
            # Check if running on Azure
            metadata_url = "http://169.254.169.254/metadata/instance?api-version=2021-02-01"
            headers = {"Metadata": "true"}
            
            response = requests.get(metadata_url, headers=headers, timeout=2)
            if response.status_code == 200:
                print("✅ Running on Azure VM - using Azure networking")
                # Azure VMs can use NAT Gateway for outbound connections
                # No additional proxy needed in this case
                self.proxy_type = "Azure Native"
                return True
            return False
        except Exception as e:
            print("Not running on Azure or Azure metadata service unavailable")
            return False
    
    def setup_with_fallback(self, config: Dict[str, any]) -> bool:
        """
        Try multiple proxy methods with fallback
        
        config example:
        {
            'scraperapi_key': 'your_key',
            'smartproxy_user': 'user',
            'smartproxy_pass': 'pass',
            'brightdata_user': 'user',
            'brightdata_pass': 'pass',
            'custom_proxies': ['http://proxy:port'],
            'enable_tor': True
        }
        """
        
        # Try Azure native first
        if self.setup_azure_managed_proxy():
            return True
        
        # Try ScraperAPI (recommended for production)
        if 'scraperapi_key' in config:
            if self.setup_scraperapi_proxy(config['scraperapi_key']):
                return True
        
        # Try SmartProxy
        if 'smartproxy_user' in config and 'smartproxy_pass' in config:
            if self.setup_smartproxy_proxy(config['smartproxy_user'], config['smartproxy_pass']):
                return True
        
        # Try BrightData
        if 'brightdata_user' in config and 'brightdata_pass' in config:
            if self.setup_brightdata_proxy(config['brightdata_user'], config['brightdata_pass']):
                return True
        
        # Try custom proxy list
        if 'custom_proxies' in config:
            if self.setup_custom_proxy_list(config['custom_proxies']):
                return True
        
        # Try Tor as last resort
        if config.get('enable_tor', False):
            if self.setup_tor_proxy():
                return True
        
        print("⚠️ All proxy methods failed - proceeding without proxy")
        return False
    
    def rotate_proxy(self, proxy_list: List[str]) -> bool:
        """Rotate to a new proxy from the list"""
        return self.setup_custom_proxy_list(proxy_list)
    
    def get_current_ip(self) -> str:
        """Get current public IP address"""
        try:
            if self.current_proxy:
                response = requests.get('http://httpbin.org/ip', proxies=self.current_proxy, timeout=10)
            else:
                response = requests.get('http://httpbin.org/ip', timeout=10)
            return response.json()['origin']
        except Exception as e:
            return f"Unable to determine IP: {e}"


# Environment-based configuration for Azure
def get_proxy_config_from_env() -> Dict[str, any]:
    """
    Load proxy configuration from environment variables
    Set these in Azure App Service Configuration or Azure Key Vault
    """
    return {
        'scraperapi_key': os.getenv('SCRAPERAPI_KEY', ''),
        'smartproxy_user': os.getenv('SMARTPROXY_USER', ''),
        'smartproxy_pass': os.getenv('SMARTPROXY_PASS', ''),
        'brightdata_user': os.getenv('BRIGHTDATA_USER', ''),
        'brightdata_pass': os.getenv('BRIGHTDATA_PASS', ''),
        'custom_proxies': os.getenv('CUSTOM_PROXIES', '').split(',') if os.getenv('CUSTOM_PROXIES') else [],
        'enable_tor': os.getenv('ENABLE_TOR', 'false').lower() == 'true'
    }


# Singleton instance
_proxy_manager = None

def get_proxy_manager() -> AzureProxyManager:
    """Get or create singleton proxy manager instance"""
    global _proxy_manager
    if _proxy_manager is None:
        _proxy_manager = AzureProxyManager()
    return _proxy_manager
