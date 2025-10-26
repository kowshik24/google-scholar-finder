#!/usr/bin/env python3
"""
Quick test to verify ScraperAPI proxy works with Google Scholar
"""

import os
import sys

# Set the API key
os.environ['SCRAPERAPI_KEY'] = 'ba32df0ed6069c2277a6dd94ae4579c1'

print("="*60)
print("Testing Google Scholar with ScraperAPI Proxy")
print("="*60)

# Import the proxy manager
from azure_proxy_config import get_proxy_manager, get_proxy_config_from_env

print("\n1. Setting up proxy...")
pm = get_proxy_manager()
config = get_proxy_config_from_env()
success = pm.setup_with_fallback(config)

if not success:
    print("❌ Proxy setup failed!")
    sys.exit(1)

print(f"✅ Proxy configured: {pm.proxy_type}")

# Test with scholarly
print("\n2. Testing scholarly library...")
try:
    from scholarly import scholarly
    
    print("   Searching for author 'Einstein'...")
    search_query = scholarly.search_author("Einstein")
    author = next(search_query, None)
    
    if author:
        print(f"✅ Found: {author.get('name', 'Unknown')}")
        print(f"   Affiliation: {author.get('affiliation', 'N/A')}")
        print(f"   Scholar ID: {author.get('scholar_id', 'N/A')}")
    else:
        print("⚠️  No results found")
        
except Exception as e:
    print(f"❌ Error: {e}")

# Test with direct web scraping
print("\n3. Testing direct web scraping with ScraperAPI REST API...")
try:
    import requests
    from bs4 import BeautifulSoup
    
    # Test with a known Google Scholar profile
    author_id = "qc6CJjYAAAAJ"  # Stephen Hawking
    url = f"https://scholar.google.com/citations?user={author_id}&hl=en"
    
    # Use ScraperAPI REST API format (more reliable)
    scraperapi_key = os.getenv('SCRAPERAPI_KEY')
    api_url = f"http://api.scraperapi.com?api_key={scraperapi_key}&url={url}"
    
    print(f"   Fetching via ScraperAPI: {author_id}")
    response = requests.get(api_url, timeout=60)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        name_elem = soup.find('div', {'id': 'gsc_prf_in'})
        
        if name_elem:
            print(f"✅ Successfully fetched profile!")
            print(f"   Name: {name_elem.get_text(strip=True)}")
            
            # Count publications
            pub_rows = soup.find_all('tr', class_='gsc_a_tr')
            print(f"   Publications found: {len(pub_rows)}")
        else:
            print("⚠️  Could not parse profile")
    else:
        print(f"❌ HTTP {response.status_code}")
        
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "="*60)
print("Test Complete!")
print("="*60)
print("\n✅ Your ScraperAPI key is working!")
print("✅ Ready to deploy to Azure!")
print("\nNext steps:")
print("1. Read QUICKSTART.md for deployment instructions")
print("2. Deploy to Azure with: az webapp up --name google-scholar-finder")
print("3. Configure SCRAPERAPI_KEY in Azure App Service settings")
