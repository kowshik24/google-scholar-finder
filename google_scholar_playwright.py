"""
Google Scholar Scraper using Playwright
Uses browser automation for better success rate with rotating proxies
"""
import asyncio
from playwright.async_api import async_playwright
import json
import random
import re
import os
from dotenv import load_dotenv

load_dotenv()

class GoogleScholarScraper:
    def __init__(self, proxy_details=None, use_tor=False):
        self.results = []
        self.proxy_details = proxy_details
        self.use_tor = use_tor
   
    async def setup_browser(self):
        playwright = await async_playwright().start()
       
        # Browser launch arguments
        launch_args = [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-blink-features=AutomationControlled',
        ]
       
        # Proxy configuration for browser context
        proxy_config = None
        
        if self.use_tor:
            # Use Tor SOCKS5 proxy
            proxy_config = {
                'server': 'socks5://127.0.0.1:9050'
            }
            print("Using Tor proxy (socks5://127.0.0.1:9050)")
        elif self.proxy_details:
            try:
                # Parse proxy URL: http://user:pass@host:port
                if '@' in self.proxy_details:
                    # Authenticated proxy
                    parts = self.proxy_details.split('://')
                    scheme = parts[0]
                    rest = parts[1]
                    creds, server = rest.split('@')
                    username, password = creds.split(':')
                    proxy_config = {
                        'server': f'{scheme}://{server}',
                        'username': username,
                        'password': password
                    }
                else:
                    # Non-authenticated proxy
                    proxy_config = {'server': self.proxy_details}
                print(f"Using proxy: {self.proxy_details.split('@')[-1] if '@' in self.proxy_details else self.proxy_details}")
            except Exception as e:
                print(f"Failed to parse proxy: {e}")
       
        browser = await playwright.chromium.launch(
            headless=True,
            args=launch_args
        )
       
        # Create context with proxy
        context_args = {
            'viewport': {'width': 1920, 'height': 1080},
            'user_agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'ignore_https_errors': True,  # Required for proxy services that intercept HTTPS
        }
        
        if proxy_config:
            context_args['proxy'] = proxy_config
       
        context = await browser.new_context(**context_args)
       
        # Block images and fonts to speed up
        await context.route("**/*", lambda route: route.abort()
                          if route.request.resource_type in ["image", "font"]
                          else route.continue_())
       
        page = await context.new_page()
        return playwright, browser, context, page
   
    async def human_like_delay(self):
        """Add random delays to mimic human behavior"""
        await asyncio.sleep(random.uniform(2, 4))
   
    async def extract_citation_data(self, page, cite_button):
        """Extract citation formats by clicking the cite button"""
        citations = {
            'mla': '',
            'apa': '',
            'chicago': '',
            'harvard': '',
            'vancouver': ''
        }
       
        try:
            await cite_button.click()
            await asyncio.sleep(2)
           
            await page.wait_for_selector('#gs_cit', timeout=10000)
           
            citation_rows = await page.query_selector_all('#gs_citt tr')
           
            for row in citation_rows:
                type_element = await row.query_selector('.gs_cith')
                if type_element:
                    citation_type = (await type_element.text_content()).strip().lower()
                   
                    citation_element = await row.query_selector('.gs_citr')
                    if citation_element:
                        citation_text = await citation_element.text_content()
                        citation_text = citation_text.strip() if citation_text else ""
                       
                        if citation_type == 'mla':
                            citations['mla'] = citation_text
                        elif citation_type == 'apa':
                            citations['apa'] = citation_text
                        elif citation_type == 'chicago':
                            citations['chicago'] = citation_text
                        elif citation_type == 'harvard':
                            citations['harvard'] = citation_text
                        elif citation_type == 'vancouver':
                            citations['vancouver'] = citation_text
           
            close_btn = await page.query_selector('#gs_cit-x')
            if close_btn:
                await close_btn.click()
                await asyncio.sleep(1)
               
        except Exception as e:
            print(f"Error extracting citations: {e}")
           
        return citations
   
    def parse_authors_from_citation(self, citation_text):
        """Extract author names from citation text"""
        try:
            if citation_text:
                match = re.match(r'^([^\.]+?)(?:\s+et al\.|\.)', citation_text)
                if match:
                    authors_part = match.group(1).strip()
                    authors = [author.strip() for author in authors_part.split(',')]
                    if authors and ' and ' in authors[-1]:
                        last_authors = authors[-1].split(' and ')
                        authors = authors[:-1] + [author.strip() for author in last_authors]
                    return [author for author in authors if author]
        except Exception as e:
            print(f"Error parsing authors from citation: {e}")
       
        return []
   
    async def parse_scholar_result(self, page, result_element):
        """Parse individual Google Scholar result"""
        try:
            title_element = await result_element.query_selector('a[data-clk]')
            title = await title_element.text_content() if title_element else ""
            title = title.strip() if title else ""
           
            result_url = await title_element.get_attribute('href') if title_element else ""
           
            authors_element = await result_element.query_selector('.gs_a')
            authors_text = await authors_element.text_content() if authors_element else ""
            authors_text = authors_text.strip() if authors_text else ""
           
            authors = []
            publication_info = ""
           
            if authors_element:
                author_links = await authors_element.query_selector_all('a[href*="/citations?user="]')
                author_names = []
                for link in author_links:
                    author_name = await link.text_content()
                    if author_name and author_name.strip():
                        author_names.append(author_name.strip())
               
                full_text = authors_text
                for author in author_names:
                    full_text = full_text.replace(author, '', 1)
               
                publication_info = re.sub(r'\s+-\s+', ' - ', full_text).strip()
                publication_info = re.sub(r'\s+,', ',', publication_info)
                publication_info = re.sub(r'\s+', ' ', publication_info)
               
                authors = author_names
           
            if not authors and authors_text:
                parts = authors_text.split(' - ', 1)
                if len(parts) > 1:
                    author_part = parts[0]
                    publication_info = parts[1]
                    authors = [author.strip() for author in author_part.split(',')]
                else:
                    publication_info = authors_text
           
            snippet_element = await result_element.query_selector('.gs_rs')
            snippet = await snippet_element.text_content() if snippet_element else ""
            snippet = snippet.strip() if snippet else ""
           
            cited_by_element = await result_element.query_selector('a[href*="cites="]')
            cited_by_count = 0
            cited_by_url = ""
           
            if cited_by_element:
                cited_by_text = await cited_by_element.text_content()
                cited_by_text = cited_by_text.strip() if cited_by_text else ""
               
                if 'Cited by' in cited_by_text:
                    try:
                        count_text = cited_by_text.replace('Cited by', '').strip()
                        cited_by_count = int(count_text) if count_text.isdigit() else 0
                    except ValueError:
                        cited_by_count = 0
               
                cited_by_url = await cited_by_element.get_attribute('href')
                if cited_by_url and not cited_by_url.startswith('http'):
                    cited_by_url = 'https://scholar.google.com' + cited_by_url
           
            related_element = await result_element.query_selector('a:has-text("Related articles")')
            related_articles_url = await related_element.get_attribute('href') if related_element else ""
            if related_articles_url and not related_articles_url.startswith('http'):
                related_articles_url = 'https://scholar.google.com' + related_articles_url
           
            versions_element = await result_element.query_selector('a:has-text("All")')
            all_versions_url = await versions_element.get_attribute('href') if versions_element else ""
            if all_versions_url and not all_versions_url.startswith('http'):
                all_versions_url = 'https://scholar.google.com' + all_versions_url
           
            profile_elements = await result_element.query_selector_all('.gs_a a[href*="/citations?user="]')
            user_profile_urls = []
            for profile_element in profile_elements:
                profile_url = await profile_element.get_attribute('href')
                if profile_url and not profile_url.startswith('http'):
                    profile_url = 'https://scholar.google.com' + profile_url
                user_profile_urls.append(profile_url)
           
            cite_button = await result_element.query_selector('a.gs_or_cit')
            citations_data = await self.extract_citation_data(page, cite_button) if cite_button else {
                'mla': '', 'apa': '', 'chicago': '', 'harvard': '', 'vancouver': ''
            }
           
            if not authors and citations_data.get('mla'):
                authors_from_citation = self.parse_authors_from_citation(citations_data['mla'])
                if authors_from_citation:
                    authors = authors_from_citation
           
            return {
                'title': title,
                'authors': authors,
                'publication_info': publication_info,
                'snippet': snippet,
                'result_url': result_url,
                'cited_by': {
                    'count': cited_by_count,
                    'url': cited_by_url
                },
                'related_articles_url': related_articles_url,
                'all_versions_url': all_versions_url,
                'citations': citations_data,
                'user_profile_urls': user_profile_urls
            }
           
        except Exception as e:
            print(f"Error parsing result: {e}")
            return None
   
    async def scrape_scholar(self, query, since_year=None, sort_by="relevance", max_results=10):
        """Main function to scrape Google Scholar results"""
        playwright, browser, context, page = await self.setup_browser()
       
        try:
            search_url = "https://scholar.google.com/scholar"
            params = {
                'q': query,
                'hl': 'en',
                'as_sdt': '0,5'
            }
           
            if since_year:
                params['as_ylo'] = since_year
               
            if sort_by == "date":
                params['scisbd'] = '1'
           
            param_string = '&'.join([f'{k}={v}' for k, v in params.items()])
            full_url = f"{search_url}?{param_string}"
           
            print(f"Navigating to: {full_url}")
           
            await page.goto(full_url, wait_until='domcontentloaded', timeout=30000)
            await self.human_like_delay()
           
            if await page.query_selector('form#captcha-form'):
                print("CAPTCHA detected. Trying to continue...")
                await asyncio.sleep(5)
           
            try:
                await page.wait_for_selector('.gs_ri', timeout=15000)
            except:
                print("No results found or page structure different")
                content = await page.content()
                if "sorry" in content.lower():
                    print("Google is showing a blocking page")
                    return {
                        'search_parameters': {
                            'query': query,
                            'date_range': f"Since {since_year}" if since_year else "Any time",
                            'sort_by': sort_by
                        },
                        'organic_results': [],
                        'error': 'Google blocking detected'
                    }
           
            results = []
            result_elements = await page.query_selector_all('.gs_ri')
           
            print(f"Found {len(result_elements)} results")
           
            for i, result_element in enumerate(result_elements[:max_results]):
                print(f"Processing result {i+1}...")
               
                result_data = await self.parse_scholar_result(page, result_element)
                if result_data:
                    result_data['position'] = i + 1
                    results.append(result_data)
                    print(f"Extracted: {result_data['title'][:50]}...")
                    if result_data['citations']['mla']:
                        print(f"Got citation data")
                else:
                    print(f"Failed to extract result {i+1}")
               
                await self.human_like_delay()
           
            return {
                'search_parameters': {
                    'query': query,
                    'date_range': f"Since {since_year}" if since_year else "Any time",
                    'sort_by': sort_by
                },
                'organic_results': results
            }
           
        except Exception as e:
            print(f"Error during scraping: {e}")
            return {
                'search_parameters': {
                    'query': query,
                    'date_range': f"Since {since_year}" if since_year else "Any time",
                    'sort_by': sort_by
                },
                'organic_results': [],
                'error': str(e)
            }
        finally:
            await browser.close()
            await playwright.stop()


def get_proxy_from_env():
    """Build proxy URL from environment variables"""
    # Check for ScraperAPI first
    scraperapi_key = os.getenv("SCRAPERAPI_KEY", "")
    if scraperapi_key:
        return f"http://scraperapi.render=true.country_code=us:{scraperapi_key}@proxy-server.scraperapi.com:8001"
    
    proxy_url = os.getenv("WEBSHARE_PROXY_URL")
    if proxy_url:
        return proxy_url
    
    # Build from components
    host = os.getenv("WEBSHARE_HOST", "p.webshare.io")
    port = os.getenv("WEBSHARE_PORT", "80")
    username = os.getenv("WEBSHARE_USERNAME", "")
    password = os.getenv("WEBSHARE_PASSWORD", "")
    
    if username and password:
        return f"http://{username}:{password}@{host}:{port}"
    
    return None


async def main():
    # Get proxy from environment
    proxy_details = get_proxy_from_env()
    
    # Check if Tor should be used (only if no other proxy configured)
    use_tor = os.getenv("USE_TOR", "false").lower() == "true" and not proxy_details
    
    if use_tor:
        print("Using Tor proxy...")
    elif proxy_details:
        # Mask the API key in output
        display_proxy = proxy_details
        if 'scraperapi' in proxy_details.lower():
            display_proxy = "ScraperAPI proxy (render mode)"
        elif '@' in proxy_details:
            display_proxy = proxy_details.split('@')[1]
        print(f"Using proxy: {display_proxy}")
    else:
        print("No proxy configured. Running without proxy (may get blocked).")
   
    scraper = GoogleScholarScraper(proxy_details=proxy_details, use_tor=use_tor)
   
    # Search parameters - can be modified
    query = os.getenv("SCHOLAR_QUERY", "machine learning")
    since_year = os.getenv("SCHOLAR_SINCE_YEAR", "2024")
    max_results = int(os.getenv("SCHOLAR_MAX_RESULTS", "5"))
    
    results = await scraper.scrape_scholar(
        query=query,
        since_year=since_year,
        sort_by="relevance",
        max_results=max_results
    )
   
    # Save results to JSON file
    output_file = 'scholar_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
   
    print(f"\nScraping completed!")
    print(f"Found {len(results['organic_results'])} results")
    print(f"Results saved to {output_file}")
   
    # Print detailed results
    for result in results['organic_results']:
        print(f"\n--- Result {result['position']} ---")
        print(f"Title: {result['title']}")
        print(f"Authors: {', '.join(result['authors']) if result['authors'] else 'N/A'}")
        print(f"Publication: {result['publication_info']}")
        print(f"Cited by: {result['cited_by']['count']}")
        if result['citations']['mla']:
            print(f"MLA: {result['citations']['mla'][:100]}...")
        print(f"Author Profiles: {len(result['user_profile_urls'])}")


if __name__ == "__main__":
    asyncio.run(main())
