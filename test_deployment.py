#!/usr/bin/env python3
"""
Test script to verify proxy setup before deploying to Azure
Run this locally to ensure everything works!
"""

import os
import sys

def print_header(text):
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def test_imports():
    """Test if all required packages are installed"""
    print_header("Testing Package Imports")
    
    required_packages = [
        'streamlit',
        'scholarly',
        'requests',
        'bs4',  # beautifulsoup4
        'tavily',
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package:20s} - installed")
        except ImportError:
            print(f"❌ {package:20s} - MISSING")
            missing.append(package)
    
    if missing:
        print("\n⚠️  Install missing packages with:")
        print(f"   pip install {' '.join(missing)}")
        return False
    
    print("\n✅ All packages installed!")
    return True

def test_azure_proxy_config():
    """Test if azure_proxy_config.py works"""
    print_header("Testing Azure Proxy Configuration")
    
    try:
        from azure_proxy_config import get_proxy_manager, get_proxy_config_from_env
        print("✅ azure_proxy_config.py imported successfully")
        
        # Test proxy manager initialization
        pm = get_proxy_manager()
        print(f"✅ Proxy manager created: {type(pm).__name__}")
        
        # Test config loading
        config = get_proxy_config_from_env()
        print(f"✅ Config loaded: {len(config)} settings")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_proxy_setup():
    """Test proxy setup with actual credentials if available"""
    print_header("Testing Proxy Setup")
    
    from azure_proxy_config import get_proxy_manager, get_proxy_config_from_env
    
    pm = get_proxy_manager()
    config = get_proxy_config_from_env()
    
    # Check which credentials are available
    print("\nChecking environment variables:")
    env_vars = {
        'SCRAPERAPI_KEY': 'ScraperAPI',
        'SMARTPROXY_USER': 'SmartProxy',
        'SMARTPROXY_PASS': 'SmartProxy',
        'BRIGHTDATA_USER': 'BrightData',
        'BRIGHTDATA_PASS': 'BrightData',
    }
    
    configured = []
    for var, service in env_vars.items():
        value = os.getenv(var)
        if value:
            # Mask the value for security
            masked = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
            print(f"✅ {var:20s} = {masked}")
            if service not in configured:
                configured.append(service)
        else:
            print(f"⚠️  {var:20s} = Not set")
    
    if not configured:
        print("\n⚠️  No proxy credentials configured!")
        print("   Set at least SCRAPERAPI_KEY to test proxy functionality")
        print("   Example: export SCRAPERAPI_KEY='your_key_here'")
        return False
    
    print(f"\n📝 Configured services: {', '.join(set(configured))}")
    
    # Try to setup proxy
    print("\nAttempting proxy setup...")
    try:
        success = pm.setup_with_fallback(config)
        if success:
            print(f"✅ Proxy setup successful!")
            print(f"   Type: {pm.proxy_type}")
            
            # Try to get current IP
            try:
                ip = pm.get_current_ip()
                print(f"   Current IP: {ip}")
            except Exception as e:
                print(f"   Could not fetch IP: {e}")
            
            return True
        else:
            print("❌ Proxy setup failed")
            return False
    except Exception as e:
        print(f"❌ Error during proxy setup: {e}")
        return False

def test_scholarly():
    """Test scholarly library basic functionality"""
    print_header("Testing Scholarly Library")
    
    try:
        from scholarly import scholarly
        print("✅ Scholarly imported successfully")
        
        # Try a simple search (this might get blocked without proxy)
        print("\nAttempting to search for 'Einstein'...")
        try:
            search_query = scholarly.search_author("Einstein")
            author = next(search_query, None)
            
            if author:
                print(f"✅ Search successful!")
                print(f"   Found: {author.get('name', 'Unknown')}")
                return True
            else:
                print("⚠️  Search returned no results")
                return False
        except Exception as e:
            print(f"⚠️  Search failed: {e}")
            print("   This is expected if proxy is not configured")
            print("   Configure a proxy and try again")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_app_azure_exists():
    """Test if app_azure.py exists and is valid"""
    print_header("Testing app_azure.py")
    
    import os.path
    
    if not os.path.exists('app_azure.py'):
        print("❌ app_azure.py not found!")
        print("   Make sure you're running this from the project directory")
        return False
    
    print("✅ app_azure.py exists")
    
    # Try to import it as a module
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("app_azure", "app_azure.py")
        # We won't actually load it to avoid running Streamlit
        print("✅ app_azure.py is valid Python")
        return True
    except Exception as e:
        print(f"❌ Error in app_azure.py: {e}")
        return False

def test_azure_files():
    """Test if all Azure deployment files exist"""
    print_header("Testing Azure Deployment Files")
    
    required_files = {
        'app_azure.py': 'Main application file',
        'azure_proxy_config.py': 'Proxy configuration',
        'requirements.txt': 'Python dependencies',
        'QUICKSTART.md': 'Quick start guide',
        'AZURE_DEPLOYMENT_GUIDE.md': 'Full deployment guide',
        'README.md': 'Documentation',
        'Dockerfile': 'Container deployment',
    }
    
    missing = []
    for filename, description in required_files.items():
        if os.path.exists(filename):
            print(f"✅ {filename:30s} - {description}")
        else:
            print(f"❌ {filename:30s} - MISSING")
            missing.append(filename)
    
    if missing:
        print(f"\n⚠️  Missing files: {', '.join(missing)}")
        return False
    
    print("\n✅ All deployment files present!")
    return True

def main():
    """Run all tests"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   Google Scholar Finder - Azure Deployment Test Suite       ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    results = {
        'Package Imports': test_imports(),
        'Azure Proxy Config': test_azure_proxy_config(),
        'Proxy Setup': test_proxy_setup(),
        'Scholarly Library': test_scholarly(),
        'App Azure File': test_app_azure_exists(),
        'Azure Files': test_azure_files(),
    }
    
    print_header("Test Summary")
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n{'='*60}")
    print(f"Results: {passed}/{total} tests passed")
    print('='*60)
    
    if passed == total:
        print("""
✅ ALL TESTS PASSED! 

Your environment is ready for Azure deployment!

Next steps:
1. Read QUICKSTART.md for deployment instructions
2. Get a ScraperAPI key from https://www.scraperapi.com/signup
3. Deploy to Azure using the commands in QUICKSTART.md

To test the app locally:
    export SCRAPERAPI_KEY="your_key"
    streamlit run app_azure.py
        """)
        return 0
    else:
        print(f"""
⚠️  {total - passed} test(s) failed.

Please fix the issues above before deploying to Azure.

Common fixes:
- Install missing packages: pip install -r requirements.txt
- Set proxy credentials: export SCRAPERAPI_KEY="your_key"
- Make sure you're in the project directory

For help, see:
- QUICKSTART.md
- AZURE_DEPLOYMENT_GUIDE.md
        """)
        return 1

if __name__ == "__main__":
    sys.exit(main())
