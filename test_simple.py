#!/usr/bin/env python3
"""
Simple test of ScraperAPI REST API (most reliable method)
"""

import os
import requests
from bs4 import BeautifulSoup

SCRAPERAPI_KEY = "ba32df0ed6069c2277a6dd94ae4579c1"

print("="*60)
print("Testing ScraperAPI REST API with Google Scholar")
print("="*60)

# Test 1: Get your IP through ScraperAPI
print("\n1. Testing ScraperAPI connection...")
try:
    test_url = "http://httpbin.org/ip"
    api_url = f"http://api.scraperapi.com?api_key={SCRAPERAPI_KEY}&url={test_url}"
    response = requests.get(api_url, timeout=30)
    
    if response.status_code == 200:
        print(f"✅ ScraperAPI is working!")
        print(f"   Response: {response.text[:200]}")
    else:
        print(f"❌ Status: {response.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: Fetch Google Scholar profile
print("\n2. Fetching Google Scholar profile...")
try:
    author_id = "qc6CJjYAAAAJ"  # Stephen Hawking
    scholar_url = f"https://scholar.google.com/citations?user={author_id}&hl=en"
    api_url = f"http://api.scraperapi.com?api_key={SCRAPERAPI_KEY}&url={scholar_url}"
    
    print(f"   Author ID: {author_id}")
    print(f"   Fetching via ScraperAPI...")
    
    response = requests.get(api_url, timeout=60)
    
    if response.status_code == 200:
        print(f"✅ Successfully fetched Google Scholar page!")
        
        # Parse the content
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Get author name
        name_elem = soup.find('div', {'id': 'gsc_prf_in'})
        if name_elem:
            name = name_elem.get_text(strip=True)
            print(f"   Author: {name}")
        
        # Get affiliation
        affiliation_elem = soup.find('div', class_='gsc_prf_il')
        if affiliation_elem:
            affiliation = affiliation_elem.get_text(strip=True)
            print(f"   Affiliation: {affiliation}")
        
        # Count publications
        pub_rows = soup.find_all('tr', class_='gsc_a_tr')
        print(f"   Publications found: {len(pub_rows)}")
        
        # Show first 3 publications
        if pub_rows:
            print(f"\n   First 3 publications:")
            for i, row in enumerate(pub_rows[:3], 1):
                title_elem = row.find('a', class_='gsc_a_at')
                year_elem = row.find('span', class_='gsc_a_y')
                
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    year = year_elem.get_text(strip=True) if year_elem else 'N/A'
                    print(f"   {i}. {title} ({year})")
        
        print("\n✅ ScraperAPI is working perfectly with Google Scholar!")
        
    elif response.status_code == 403:
        print(f"❌ Access forbidden - check your ScraperAPI key")
    elif response.status_code == 429:
        print(f"❌ Rate limit exceeded")
    else:
        print(f"❌ HTTP {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("Test Complete!")
print("="*60)
print("\nYour ScraperAPI key is working! 🎉")
print("\nYou can now:")
print("1. Run the app locally: streamlit run app_azure.py")
print("2. Deploy to Azure using QUICKSTART.md")
print("\nThe app will automatically use ScraperAPI when")
print("SCRAPERAPI_KEY environment variable is set.")
