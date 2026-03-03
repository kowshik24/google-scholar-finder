from scholarly import scholarly, ProxyGenerator
import csv
import time
import random
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def setup_proxy():
    """
    Set up a proxy to avoid Google Scholar blocking.
    
    Supported methods (set CONNECTION_METHOD in .env):
    - scraperapi: Requires SCRAPERAPI_KEY in .env (recommended)
    - http_proxy: Generic HTTP proxy (works with Oxylabs, Smartproxy, Webshare, etc.)
    - luminati: Direct connection to Bright Data super proxy
    - luminati_local: Connect via local Luminati Proxy Manager (docker-compose)
    - freeproxy: Uses free proxies (may be unreliable)
    - none: No proxy (default)
    """
    connection_method = os.getenv("CONNECTION_METHOD", "none").lower()
    pg = ProxyGenerator()
    
    try:
        if connection_method == "scraperapi":
            api_key = os.getenv("SCRAPERAPI_KEY")
            if not api_key:
                print("ScraperAPI key missing. Set SCRAPERAPI_KEY in .env")
                return False
            
            # Use ScraperAPI with render mode and US IP for better Google Scholar compatibility
            # Format: http://scraperapi.render=true.country_code=us:API_KEY@proxy-server.scraperapi.com:8001
            proxy_url = f"http://scraperapi.render=true.country_code=us:{api_key}@proxy-server.scraperapi.com:8001"
            success = pg.SingleProxy(http=proxy_url, https=proxy_url)
            if success:
                scholarly.use_proxy(pg)
                print("ScraperAPI proxy setup successful (render mode, US IP)")
                return True
        
        elif connection_method == "http_proxy":
            # Generic HTTP proxy - works with any proxy service
            # Format: http://username:password@host:port or http://host:port
            proxy_url = os.getenv("HTTP_PROXY_URL")
            if not proxy_url:
                # Build from individual components
                host = os.getenv("PROXY_HOST")
                port = os.getenv("PROXY_PORT", "8080")
                username = os.getenv("PROXY_USERNAME", "")
                password = os.getenv("PROXY_PASSWORD", "")
                
                if not host:
                    print("HTTP proxy config missing. Set HTTP_PROXY_URL or PROXY_HOST in .env")
                    return False
                
                if username and password:
                    proxy_url = f"http://{username}:{password}@{host}:{port}"
                else:
                    proxy_url = f"http://{host}:{port}"
            
            success = pg.SingleProxy(http=proxy_url, https=proxy_url)
            if success:
                scholarly.use_proxy(pg)
                print(f"HTTP proxy setup successful")
                return True
                
        elif connection_method == "luminati":
            # Direct connection to Bright Data super proxy
            username = os.getenv("BRIGHTDATA_USERNAME")
            password = os.getenv("BRIGHTDATA_PASSWORD")
            zone = os.getenv("BRIGHTDATA_ZONE", "residential")
            country = os.getenv("BRIGHTDATA_COUNTRY", "")
            host = os.getenv("BRIGHTDATA_HOST", "brd.superproxy.io")
            port = os.getenv("BRIGHTDATA_PORT", "22225")
            
            if not all([username, password]):
                print("Bright Data credentials missing. Set BRIGHTDATA_USERNAME, BRIGHTDATA_PASSWORD in .env")
                return False
            
            # Build the full username with zone and country
            full_username = f"brd-customer-{username}-zone-{zone}"
            if country:
                full_username += f"-country-{country}"
            
            success = pg.Luminati(usr=full_username, passwd=password, proxy_port=int(port))
            if success:
                scholarly.use_proxy(pg)
                print(f"Bright Data proxy setup successful (zone: {zone})")
                return True
                
        elif connection_method == "luminati_local":
            # Connect via local Luminati Proxy Manager
            proxy_host = os.getenv("LUMINATI_PROXY_HOST", "localhost")
            proxy_port = os.getenv("LUMINATI_PROXY_PORT", "24000")
            
            proxy_url = f"http://{proxy_host}:{proxy_port}"
            success = pg.SingleProxy(http=proxy_url, https=proxy_url)
            if success:
                scholarly.use_proxy(pg)
                print(f"Local Luminati Proxy Manager setup successful ({proxy_url})")
                return True
                
        elif connection_method == "freeproxy":
            success = pg.FreeProxies()
            if success:
                scholarly.use_proxy(pg)
                print("Free proxy setup successful")
                return True
        
        elif connection_method == "tor":
            # Use Tor network (must have tor running: apt install tor && systemctl start tor)
            try:
                success = pg.Tor_Internal(tor_cmd="tor")
                if success:
                    scholarly.use_proxy(pg)
                    print("Tor proxy setup successful")
                    return True
            except Exception as tor_err:
                print(f"Tor internal failed: {tor_err}, trying external...")
                # Try external Tor connection (if tor is already running)
                success = pg.Tor_External(tor_sock_port=9050, tor_control_port=9051, tor_pw="")
                if success:
                    scholarly.use_proxy(pg)
                    print("Tor external proxy setup successful")
                    return True
                
        elif connection_method == "none":
            print("No proxy configured. Set CONNECTION_METHOD in .env to use proxies.")
            return False
            
        else:
            print(f"Unknown CONNECTION_METHOD: {connection_method}")
            print("Valid options: scraperapi, http_proxy, tor, luminati, luminati_local, freeproxy, none")
            return False
            
    except Exception as e:
        print(f"Proxy setup failed: {e}")
    
    print("Continuing without proxy (may get blocked by Google Scholar)")
    return False

def scrape_with_scholarly(author_id, start_year=2023, end_year=2026, max_retries=3):
    """
    Use the scholarly library to scrape Google Scholar data.
    """
    papers = []
    
    for attempt in range(max_retries):
        try:
            # Search for the author
            author = scholarly.search_author_id(author_id)
            author = scholarly.fill(author, sections=['publications'])
            break
        except Exception as e:
            print(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5 + random.uniform(1, 3)
                print(f"Waiting {wait_time:.1f}s before retry...")
                time.sleep(wait_time)
            else:
                print("All retries failed. Google Scholar may be blocking requests.")
                print("Try using ScraperAPI or another proxy service.")
                return papers
    
    print(f"Author: {author['name']}")
    print(f"Total publications: {len(author['publications'])}\n")
    
    for pub in author['publications']:
        try:
            # Fill publication details including abstract
            pub_filled = scholarly.fill(pub)
            
            year = pub_filled['bib'].get('pub_year')
            if year and year.isdigit():
                year = int(year)
                
                if start_year <= year <= end_year:
                    paper_data = {
                        'title': pub_filled['bib'].get('title', ''),
                        'authors': ', '.join(pub_filled['bib'].get('author', [])),
                        'publication': pub_filled['bib'].get('venue', ''),
                        'year': year,
                        'citations': pub_filled.get('num_citations', 0),
                        'abstract': pub_filled['bib'].get('abstract', ''),
                        'url': pub_filled.get('pub_url', '')
                    }
                    
                    papers.append(paper_data)
                    print(f"Found: {paper_data['title']} ({year})")
        
        except Exception as e:
            print(f"Error processing publication: {e}")
            continue
    
    return papers

def main():
    # Set up proxy based on CONNECTION_METHOD in .env
    setup_proxy()
    
    user_id = "a6MYnuUAAAAJ"
    papers = scrape_with_scholarly(user_id, 2023, 2026)
    
    # Save to CSV
    if papers:
        with open('scholar_papers_scholarly.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['title', 'authors', 'publication', 'year', 'citations', 'abstract', 'url'])
            writer.writeheader()
            writer.writerows(papers)
        
        print(f"\nSaved {len(papers)} papers to scholar_papers_scholarly.csv")

if __name__ == "__main__":
    main()
