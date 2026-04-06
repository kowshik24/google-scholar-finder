import streamlit as st
from scholarly import scholarly, ProxyGenerator
import random
import os
import time
import requests
from bs4 import BeautifulSoup
import re
import traceback
from urllib.parse import quote_plus
from dotenv import load_dotenv
import google_scholar_scraper as env_scholar_scraper

# --- Load environment variables from .env file ---
load_dotenv()

# --- Configuration from Environment Variables ---
SCRAPERAPI_KEY = os.getenv('SCRAPERAPI_KEY', '')
LUMINATI_USER = os.getenv('LUMINATI_USER', '')
LUMINATI_PASS = os.getenv('LUMINATI_PASS', '')
USE_FREE_PROXY_ONLY = os.getenv('USE_FREE_PROXY_ONLY', 'true').lower() == 'true'
LOCAL_PROXY_URL = os.getenv('LOCAL_PROXY_URL', '').strip()
MAX_DIRECT_RETRIES = int(os.getenv('MAX_DIRECT_RETRIES', '3'))
MIN_REQUEST_DELAY = float(os.getenv('MIN_REQUEST_DELAY', '1.5'))
MAX_REQUEST_DELAY = float(os.getenv('MAX_REQUEST_DELAY', '3.5'))
DIRECT_TIMEOUT = int(os.getenv('DIRECT_TIMEOUT', '30'))
DECODO_USERNAME = os.getenv('DECODO_USERNAME', '').strip()
DECODO_PASSWORD = os.getenv('DECODO_PASSWORD', '').strip()
SCRAPER_OUTPUT_CSV = os.getenv('OUTPUT_CSV', 'scholar_results.csv').strip()
SCRAPER_FETCH_ABSTRACTS = os.getenv('FETCH_ABSTRACTS', 'true').lower() == 'true'

USER_AGENTS = [
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0',
]

# --- Circuit Breaker State ---
# Track proxy failures to skip consistently failing methods
if 'proxy_failures' not in st.session_state:
    st.session_state.proxy_failures = {
        'free_proxies': {'count': 0, 'cooldown_until': 0},
        'luminati': {'count': 0, 'cooldown_until': 0},
        'scraperapi_proxy': {'count': 0, 'cooldown_until': 0},
        'scraperapi_rest': {'count': 0, 'cooldown_until': 0},
    }

CIRCUIT_BREAKER_THRESHOLD = 3  # failures before cooldown
CIRCUIT_BREAKER_COOLDOWN = 300  # 5 minutes cooldown


def get_http_session() -> requests.Session:
    """Get or initialize a shared HTTP session for connection reuse."""
    if 'http_session' not in st.session_state:
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=0)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        st.session_state.http_session = session
    return st.session_state.http_session


def get_rotating_headers() -> dict:
    """Return a realistic browser header set with rotating UA."""
    ua = random.choice(USER_AGENTS)
    accept_lang = random.choice(['en-US,en;q=0.9', 'en-GB,en;q=0.9', 'en-US,en;q=0.8'])
    return {
        'User-Agent': ua,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': accept_lang,
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
    }


def maybe_refresh_free_proxy(reason: str = ''):
    """Refresh free proxy setup after block-like failures."""
    if not is_proxy_available('free_proxies'):
        return
    try:
        st.write(f"Refreshing free proxy pool ({reason})...")
        success, proxy_type = setup_proxy()
        if success and proxy_type == 'free_proxies':
            st.write("✅ Free proxy refreshed")
        else:
            st.write("⚠️ Free proxy refresh did not activate free proxy")
    except Exception as e:
        st.write(f"⚠️ Free proxy refresh failed: {e}")


def should_treat_as_block(response: requests.Response) -> bool:
    """Detect likely block/challenge responses from Scholar."""
    if response.status_code in (403, 429, 503):
        return True

    text = (response.text or '').lower()
    block_markers = [
        'sorry',
        'unusual traffic',
        'detected unusual traffic',
        'captcha',
        '/sorry/',
    ]
    return any(marker in text for marker in block_markers)

def is_proxy_available(proxy_type: str) -> bool:
    """Check if a proxy method is available (not in cooldown)"""
    state = st.session_state.proxy_failures.get(proxy_type, {})
    if state.get('count', 0) >= CIRCUIT_BREAKER_THRESHOLD:
        if time.time() < state.get('cooldown_until', 0):
            return False
        # Reset after cooldown
        st.session_state.proxy_failures[proxy_type] = {'count': 0, 'cooldown_until': 0}
    return True

def record_proxy_failure(proxy_type: str):
    """Record a proxy failure for circuit breaker"""
    state = st.session_state.proxy_failures.get(proxy_type, {'count': 0, 'cooldown_until': 0})
    state['count'] = state.get('count', 0) + 1
    if state['count'] >= CIRCUIT_BREAKER_THRESHOLD:
        state['cooldown_until'] = time.time() + CIRCUIT_BREAKER_COOLDOWN
        print(f"Circuit breaker tripped for {proxy_type}, cooldown until {state['cooldown_until']}")
    st.session_state.proxy_failures[proxy_type] = state

def record_proxy_success(proxy_type: str):
    """Reset failure count on success"""
    st.session_state.proxy_failures[proxy_type] = {'count': 0, 'cooldown_until': 0}


def render_proxy_health_panel():
    """Render current proxy/circuit-breaker health information."""
    st.markdown("### 🩺 Proxy Health")

    current_time = time.time()
    proxy_state = st.session_state.get('proxy_failures', {})

    rows = []
    for proxy_name, state in proxy_state.items():
        failures = state.get('count', 0)
        cooldown_until = state.get('cooldown_until', 0)
        in_cooldown = cooldown_until > current_time
        remaining = max(0, int(cooldown_until - current_time)) if in_cooldown else 0

        rows.append({
            'Proxy Method': proxy_name,
            'Failures': failures,
            'Status': 'cooldown' if in_cooldown else 'active',
            'Cooldown Left (s)': remaining,
        })

    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.caption(
        f"Retries={MAX_DIRECT_RETRIES} | Delay={MIN_REQUEST_DELAY:.1f}-{MAX_REQUEST_DELAY:.1f}s | "
        f"Timeout={DIRECT_TIMEOUT}s | FreeOnly={USE_FREE_PROXY_ONLY} | LocalProxy={'on' if LOCAL_PROXY_URL else 'off'}"
    )

# Set up a proxy to avoid getting blocked by Google Scholar
def setup_proxy():
    try:
        pg = ProxyGenerator()
        success = False
        proxy_type = None
        
        # If USE_FREE_PROXY_ONLY is set, skip paid proxies
        if not USE_FREE_PROXY_ONLY:
            # Try ScraperAPI first (most reliable for Google Scholar)
            if not success and SCRAPERAPI_KEY and is_proxy_available('scraperapi_proxy'):
                try:
                    success = pg.ScraperAPI(SCRAPERAPI_KEY)
                    if success:
                        scholarly.use_proxy(pg)
                        print("ScraperAPI proxy setup successful")
                        proxy_type = 'scraperapi_proxy'
                        record_proxy_success('scraperapi_proxy')
                        return True, 'scraperapi_proxy'
                except Exception as e:
                    print(f"ScraperAPI proxy failed: {e}")
                    record_proxy_failure('scraperapi_proxy')
            
            # Try Luminati proxy if ScraperAPI fails
            if not success and LUMINATI_USER and LUMINATI_PASS and is_proxy_available('luminati'):
                try:
                    success = pg.Luminati(usr=LUMINATI_USER, passwd=LUMINATI_PASS, port=22225)
                    if success:
                        scholarly.use_proxy(pg)
                        print("Luminati proxy setup successful")
                        proxy_type = 'luminati'
                        record_proxy_success('luminati')
                        return True, 'luminati'
                except Exception as e:
                    print(f"Luminati proxy failed: {e}")
                    record_proxy_failure('luminati')
        else:
            print("Using free proxy only mode (USE_FREE_PROXY_ONLY=true)")
        
        # Try free proxies
        if not success and is_proxy_available('free_proxies'):
            try:
                success = pg.FreeProxies()
                if success:
                    scholarly.use_proxy(pg)
                    print("Free proxy setup successful")
                    proxy_type = 'free_proxies'
                    record_proxy_success('free_proxies')
                    return True, 'free_proxies'
            except Exception as e:
                print(f"Free proxies failed: {e}")
                record_proxy_failure('free_proxies')
        
        print("All proxy methods failed, proceeding without proxy")
        return False, None
        
    except Exception as e:
        print(f"Proxy setup failed: {e}. Proceeding without proxy.")
        return False, None

# Initialize proxy
proxy_setup_success, active_proxy_type = setup_proxy()

def clear_scholarly_cache():
    """Clear any cached data that might be causing issues"""
    try:
        if hasattr(scholarly, '_cache'):
            scholarly._cache.clear()
        if hasattr(scholarly, '_proxy_generator'):
            scholarly._proxy_generator = None
        print("Scholarly cache cleared")
    except Exception as e:
        print(f"Failed to clear cache: {e}")

def clear_results_cache():
    """Clear the results cache to force fresh data"""
    if 'results_cache' in st.session_state:
        st.session_state.results_cache = {}
    print("Results cache cleared")

def test_connection():
    """Test if we can connect to Google Scholar"""
    try:
        # Try to search for a known author to test connection
        test_author = scholarly.search_author("Einstein")
        return test_author is not None
    except Exception as e:
        print(f"Connection test failed: {e}")
        return False

def get_with_scraperapi(url: str, timeout: int = 60) -> requests.Response:
    """
    Fetch a URL using ScraperAPI REST API (more reliable than proxy mode)
    """
    if not SCRAPERAPI_KEY:
        raise ValueError("SCRAPERAPI_KEY not configured")
    
    if not is_proxy_available('scraperapi_rest'):
        raise RuntimeError("ScraperAPI REST is in cooldown due to repeated failures")
    
    api_url = f"http://api.scraperapi.com?api_key={SCRAPERAPI_KEY}&url={quote_plus(url)}"
    
    try:
        session = get_http_session()
        response = session.get(api_url, timeout=timeout)
        if response.status_code == 200:
            record_proxy_success('scraperapi_rest')
        else:
            record_proxy_failure('scraperapi_rest')
        return response
    except Exception as e:
        record_proxy_failure('scraperapi_rest')
        raise

def exponential_backoff(attempt: int, base: float = 2.0, max_delay: float = 60.0) -> float:
    """Calculate exponential backoff delay with jitter"""
    delay = min(max_delay, (base ** attempt) + random.uniform(0, 1))
    return delay

def fetch_page_with_fallback(url: str, headers: dict = None) -> requests.Response:
    """
    Fetch a page with multiple fallback methods:
    1. ScraperAPI REST API (most reliable)
    2. Direct request with headers
    """
    session = get_http_session()
    headers = headers or get_rotating_headers()
    
    # Try ScraperAPI REST API first (most reliable)
    if SCRAPERAPI_KEY and is_proxy_available('scraperapi_rest'):
        try:
            st.write("Using ScraperAPI REST API...")
            response = get_with_scraperapi(url, timeout=60)
            if response.status_code == 200:
                return response
            else:
                st.warning(f"ScraperAPI returned status {response.status_code}, trying direct request...")
        except Exception as e:
            st.warning(f"ScraperAPI failed: {e}, trying direct request...")

    # Optional local proxy endpoint (free self-hosted)
    if LOCAL_PROXY_URL:
        try:
            st.write("Using local proxy endpoint...")
            proxy_url = f"{LOCAL_PROXY_URL.rstrip('/')}/proxy"
            response = session.get(proxy_url, params={'url': url}, headers=headers, timeout=max(45, DIRECT_TIMEOUT))
            if response.status_code == 200 and not should_treat_as_block(response):
                return response
            st.warning(f"Local proxy returned status {response.status_code}, trying direct request...")
        except Exception as e:
            st.warning(f"Local proxy failed: {e}, trying direct request...")
    
    # Fallback to direct request with retries, jitter, and block detection
    last_exception = None
    for attempt in range(MAX_DIRECT_RETRIES):
        try:
            if attempt > 0:
                delay = exponential_backoff(attempt, base=1.8, max_delay=12.0)
                st.write(f"Retrying direct request in {delay:.1f}s (attempt {attempt + 1}/{MAX_DIRECT_RETRIES})...")
                time.sleep(delay)
            else:
                time.sleep(random.uniform(MIN_REQUEST_DELAY, MAX_REQUEST_DELAY))

            rotated_headers = headers.copy()
            rotated_headers['User-Agent'] = random.choice(USER_AGENTS)
            response = session.get(url, headers=rotated_headers, timeout=DIRECT_TIMEOUT)

            if should_treat_as_block(response):
                record_proxy_failure('free_proxies')
                st.warning(f"Direct request appears blocked (status {response.status_code}).")
                maybe_refresh_free_proxy(reason=f"status {response.status_code}")
                continue

            return response
        except Exception as e:
            last_exception = e
            record_proxy_failure('free_proxies')
            st.warning(f"Direct request failed on attempt {attempt + 1}: {e}")
            maybe_refresh_free_proxy(reason="request exception")

    if last_exception:
        raise RuntimeError(f"Direct request failed after {MAX_DIRECT_RETRIES} attempts: {last_exception}")
    raise RuntimeError(f"Direct request failed after {MAX_DIRECT_RETRIES} attempts")

def fetch_scholar_data_alternative(author_id, start_year, end_year, max_pages=5):
    """
    Alternative method to fetch author data using direct web scraping approach.
    Supports pagination to fetch more than the first page of publications.
    Uses ScraperAPI REST API when available for better reliability.
    """
    try:
        st.write("Trying env-driven web scraping method...")

        session = env_scholar_scraper.make_session(DECODO_USERNAME, DECODO_PASSWORD)
        rows = env_scholar_scraper.scrape_author_cost_optimized(
            session=session,
            author_id=author_id,
            start_year=int(start_year),
            end_year=int(end_year),
            fetch_abstracts=SCRAPER_FETCH_ABSTRACTS,
            output_csv=SCRAPER_OUTPUT_CSV,
        )

        papers = []
        for row in rows:
            year_raw = row.get('Year')
            try:
                year_int = int(year_raw)
            except (TypeError, ValueError):
                continue

            if year_int < int(start_year) or year_int > int(end_year):
                continue

            citations_raw = row.get('Citation Count', 0)
            try:
                citations_int = int(citations_raw)
            except (TypeError, ValueError):
                citations_int = 0

            papers.append({
                'bib': {
                    'title': row.get('Title', ''),
                    'pub_year': str(year_int),
                    'author': row.get('Authors', 'Unknown authors'),
                    'abstract': row.get('Abstract', 'No abstract available.'),
                    'citation_count': citations_int,
                },
                'pub_url': row.get('Scholar URL', ''),
                'num_citations': citations_int,
            })

        papers.sort(
            key=lambda x: int(x['bib'].get('pub_year', 0)) if str(x['bib'].get('pub_year', '')).isdigit() else 0,
            reverse=True
        )

        if papers:
            st.success(f"Successfully extracted {len(papers)} publications using env-driven scraper!")
            return papers

        st.warning("Env-driven scraper returned no publications in the specified date range. Falling back...")
    except Exception as primary_error:
        st.warning(f"Env-driven scraper failed: {primary_error}. Falling back to legacy parser...")

    try:
        st.write("Trying alternative web scraping method...")
        
        publications = []
        page_start = 0
        page_size = 100  # Google Scholar default
        consecutive_empty_pages = 0
        found_older_than_range = False
        
        for page_num in range(max_pages):
            # Construct the Google Scholar URL with pagination
            url = f"https://scholar.google.com/citations?user={author_id}&hl=en&cstart={page_start}&pagesize={page_size}"
            
            if page_num > 0:
                st.write(f"Fetching page {page_num + 1}...")
            
            response = fetch_page_with_fallback(url)
            
            if response.status_code != 200:
                if page_num == 0:
                    st.error(f"Failed to fetch author page. Status code: {response.status_code}")
                    return None
                else:
                    # Stop pagination if we get an error on subsequent pages
                    break
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Check if author exists (only on first page)
            if page_num == 0:
                if "not found" in response.text.lower() or "profile not found" in response.text.lower():
                    st.error("Author profile not found. Please verify the author ID.")
                    return None
                
                # Extract author name
                author_name = "Unknown Author"
                name_elem = soup.find('div', {'id': 'gsc_prf_in'})
                if name_elem:
                    author_name = name_elem.get_text(strip=True)
                st.write(f"Author: {author_name}")
            
            # Find publications in the page
            pub_rows = soup.find_all('tr', class_='gsc_a_tr')
            
            if not pub_rows:
                pub_rows = soup.find_all('div', class_='gsc_a_tr')
            
            if not pub_rows:
                consecutive_empty_pages += 1
                if consecutive_empty_pages >= 2:
                    break  # Stop if we get 2 empty pages in a row
                continue
            
            consecutive_empty_pages = 0
            page_pubs_in_range = 0
            
            if page_num == 0:
                st.write(f"Found {len(pub_rows)} publication entries on the page")
            
            for i, row in enumerate(pub_rows):
                try:
                    # Extract title
                    title_elem = row.find('a', class_='gsc_a_at')
                    if not title_elem:
                        title_elem = row.find('a')
                    
                    if not title_elem:
                        continue
                        
                    title = title_elem.get_text(strip=True)
                    
                    # Extract year
                    year_elem = row.find('span', class_='gsc_a_y')
                    year = None
                    if year_elem:
                        year_text = year_elem.get_text(strip=True)
                        year_match = re.search(r'\d{4}', year_text)
                        if year_match:
                            year = int(year_match.group())
                    
                    # Track if we've gone past our date range (for early termination)
                    if year and year < start_year:
                        found_older_than_range = True
                    
                    # Skip if year is not in range
                    if year and (year < start_year or year > end_year):
                        continue
                    
                    page_pubs_in_range += 1
                    
                    # Extract authors (if available)
                    authors_elem = row.find('div', class_='gs_gray')
                    authors = authors_elem.get_text(strip=True) if authors_elem else "Unknown authors"
                    
                    # Extract citation count
                    citations_elem = row.find('a', class_='gsc_a_c')
                    citations = 0
                    if citations_elem:
                        cite_text = citations_elem.get_text(strip=True)
                        if cite_text and cite_text != '-':
                            citations = int(re.sub(r'[^\d]', '', cite_text)) if re.sub(r'[^\d]', '', cite_text) else 0
                    
                    # Create publication object similar to scholarly format
                    pub = {
                        'bib': {
                            'title': title,
                            'pub_year': str(year) if year else 'Unknown',
                            'author': authors,
                            'citation_count': citations
                        },
                        'pub_url': title_elem.get('href', '') if title_elem else '',
                        'num_citations': citations
                    }
                    
                    publications.append(pub)
                        
                except Exception as pub_error:
                    continue
            
            # Progress update
            total_pubs = len(publications)
            if total_pubs > 0 and page_num > 0:
                st.write(f"Found {total_pubs} publications in range so far...")
            
            # Early termination: if all publications on this page are older than start_year
            if found_older_than_range and page_pubs_in_range == 0:
                st.write("Reached publications older than the specified range, stopping pagination.")
                break
            
            # Move to next page
            page_start += page_size
            
            # Rate limiting between pages
            if page_num < max_pages - 1 and len(pub_rows) > 0:
                time.sleep(random.uniform(1, 2))
        
        # Sort papers by year in descending order (most recent first)
        publications.sort(key=lambda x: int(x['bib'].get('pub_year', 0)) if x['bib'].get('pub_year', '').isdigit() else 0, reverse=True)
        
        if publications:
            st.success(f"Successfully extracted {len(publications)} publications using web scraping!")
            return publications
        else:
            st.warning("No publications found in the specified date range using web scraping.")
            return None
        
    except Exception as e:
        st.error(f"Alternative method failed: {e}")
        st.error(f"Technical details: {traceback.format_exc()}")
        return None

def get_cache_key(author_id: str, start_year: int, end_year: int, method: str) -> str:
    """Generate a cache key for the results"""
    return f"{author_id}_{start_year}_{end_year}_{method}"

def get_cached_results(cache_key: str):
    """Get results from session state cache"""
    if 'results_cache' not in st.session_state:
        st.session_state.results_cache = {}
    
    cached = st.session_state.results_cache.get(cache_key)
    if cached:
        # Check if cache is still valid (1 hour TTL)
        if time.time() - cached.get('timestamp', 0) < 3600:
            return cached.get('data')
        else:
            # Cache expired, remove it
            del st.session_state.results_cache[cache_key]
    return None

def set_cached_results(cache_key: str, data):
    """Store results in session state cache"""
    if 'results_cache' not in st.session_state:
        st.session_state.results_cache = {}
    
    st.session_state.results_cache[cache_key] = {
        'data': data,
        'timestamp': time.time()
    }

def fetch_scholar_data(author_id, start_year, end_year, use_cache=True):
    """
    Fetches paper titles and abstracts for a given Google Scholar author ID and time frame.
    Uses caching and exponential backoff for better reliability.
    """
    # Check cache first
    cache_key = get_cache_key(author_id, start_year, end_year, 'scholarly')
    if use_cache:
        cached = get_cached_results(cache_key)
        if cached:
            st.success(f"✅ Loaded {len(cached)} papers from cache!")
            return cached
    
    try:
        st.write(f"Fetching data for author ID: {author_id}...")
        
        # First, try the scholarly library with enhanced error handling
        author = None
        max_retries = 5  # Increased from 3
        
        for attempt in range(max_retries):
            try:
                st.write(f"Attempt {attempt + 1} to fetch author profile...")
                
                # Clear cache and reset proxy to avoid conflicts
                clear_scholarly_cache()
                
                # Try to get author profile
                author = scholarly.search_author_id(author_id)
                
                if author is not None and isinstance(author, dict):
                    st.write("✅ Author profile retrieved successfully!")
                    record_proxy_success('free_proxies')
                    break
                else:
                    st.warning(f"Attempt {attempt + 1} returned None or invalid data. Retrying...")
                    record_proxy_failure('free_proxies')
                    maybe_refresh_free_proxy(reason='invalid author payload')
                    if attempt < max_retries - 1:
                        delay = exponential_backoff(attempt)
                        st.write(f"Waiting {delay:.1f}s before retry...")
                        time.sleep(delay)
                        
            except AttributeError as attr_error:
                st.warning(f"Attempt {attempt + 1} failed with AttributeError: {attr_error}")
                record_proxy_failure('free_proxies')
                maybe_refresh_free_proxy(reason='attribute error')
                if attempt < max_retries - 1:
                    delay = exponential_backoff(attempt)
                    st.write(f"Waiting {delay:.1f}s before retry...")
                    time.sleep(delay)
            except Exception as retry_error:
                st.warning(f"Attempt {attempt + 1} failed: {retry_error}")
                record_proxy_failure('free_proxies')
                maybe_refresh_free_proxy(reason='author fetch error')
                if attempt < max_retries - 1:
                    delay = exponential_backoff(attempt)
                    st.write(f"Waiting {delay:.1f}s before retry...")
                    time.sleep(delay)
        
        if author is None or not isinstance(author, dict):
            st.error("❌ Failed to retrieve author profile with scholarly library.")
            st.error("This is likely due to:")
            st.error("- Internal issues with the scholarly library")
            st.error("- Google Scholar blocking the requests")
            st.error("- Network connectivity issues")
            
            # Try alternative method
            return fetch_scholar_data_alternative(author_id, start_year, end_year)
        
        st.write("Author found, fetching publications...")
        
        # Fill the author's publications with better error handling
        try:
            author = scholarly.fill(author, sections=['publications'])
        except Exception as fill_error:
            st.error(f"Failed to fetch publications: {fill_error}")
            st.error("This might be due to the scholarly library version or Google Scholar blocking.")
            return fetch_scholar_data_alternative(author_id, start_year, end_year)
        
        if 'publications' not in author or not author['publications']:
            st.error("No publications found for this author.")
            return None
        
        # First pass: filter by year WITHOUT fetching full details
        matching_pubs = []
        st.write(f"Scanning {len(author['publications'])} publications for year range...")
        
        for pub in author['publications']:
            try:
                if 'bib' in pub and 'pub_year' in pub['bib']:
                    pub_year = int(pub['bib']['pub_year'])
                    if start_year <= pub_year <= end_year:
                        matching_pubs.append(pub)
            except (ValueError, TypeError):
                continue
        
        st.write(f"Found {len(matching_pubs)} publications in date range, fetching details...")
        
        # Second pass: fetch full details only for matching publications
        papers = []
        for i, pub in enumerate(matching_pubs):
            try:
                # Fill the publication to get more details like the abstract
                filled_pub = scholarly.fill(pub)
                if filled_pub and 'bib' in filled_pub:
                    papers.append(filled_pub)
                    
                # Add progress indicator
                if (i + 1) % 5 == 0:
                    st.write(f"Fetched details for {i + 1}/{len(matching_pubs)} publications...")
                
                # Rate limiting between fill() calls
                if i < len(matching_pubs) - 1:
                    time.sleep(random.uniform(0.5, 1.5))
                    
            except Exception as pub_error:
                st.warning(f"Skipping publication {i + 1} due to error: {pub_error}")
                continue
        
        # Sort papers by year in descending order (most recent first)
        papers.sort(key=lambda x: int(x['bib'].get('pub_year', 0)), reverse=True)
        
        st.write(f"Found {len(papers)} papers between {start_year} and {end_year}.")
        
        # Cache the results
        if papers:
            set_cached_results(cache_key, papers)
        
        return papers
        
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        st.error("This could be due to network issues, an invalid author ID, or being temporarily blocked by Google Scholar.")
        
        # Try alternative method as last resort
        st.write("Trying alternative approach...")
        return fetch_scholar_data_alternative(author_id, start_year, end_year)

# --- Streamlit App ---

st.title("Google Scholar Paper Fetcher")

st.write("Enter a Google Scholar author ID and a date range to fetch their paper titles and abstracts.")

# Connection status
col1, col2 = st.columns([3, 1])
with col1:
    if proxy_setup_success:
        proxy_info = f"✅ Proxy configured ({active_proxy_type}) - Better protection against blocking"
        if SCRAPERAPI_KEY:
            proxy_info += "\n🔑 ScraperAPI REST fallback available"
        st.success(proxy_info)
    elif SCRAPERAPI_KEY:
        st.info("🔑 ScraperAPI REST API available as fallback")
    else:
        st.warning("⚠️ No proxy configured - Higher risk of being blocked. Set SCRAPERAPI_KEY env var for better reliability.")

with col2:
    col2_1, col2_2 = st.columns(2)
    with col2_1:
        if st.button("Test Connection"):
            with st.spinner("Testing connection to Google Scholar..."):
                if test_connection():
                    st.success("✅ Connection successful!")
                else:
                    st.error("❌ Connection failed. Check your internet connection.")
    
    with col2_2:
        if st.button("Clear Cache"):
            clear_scholarly_cache()
            clear_results_cache()
            st.success("✅ All caches cleared!")

# Proxy health panel
with st.expander("📈 Proxy Health & Runtime Settings", expanded=False):
    render_proxy_health_panel()

# Input for Google Scholar Author ID
scholar_id = st.text_input("Google Scholar Author ID", "x12zA5gAAAAJ")
st.markdown("You can find the author ID in the URL of their Google Scholar profile. For example, for Stephen Hawking, the URL is `https://scholar.google.com/citations?user=qc6CJjYAAAAJ`, so the ID is `qc6CJjYAAAAJ`.")

# Troubleshooting tips
with st.expander("🔧 Troubleshooting Tips"):
    st.markdown("""
    **Common Issues and Solutions:**
    
    1. **"NoneType object has no attribute 'get'" Error:**
       - This is a known issue with the scholarly library
       - Try clicking "Clear Cache" and then "Fetch Papers" again
       - The app now has retry logic and alternative methods
       - Sometimes it's a temporary network issue - wait a few minutes and try again
    
    2. **Connection Timeouts:**
       - Use the "Test Connection" button above to verify connectivity
       - Try again after a few minutes
    
    3. **Rate Limiting:**
       - Google Scholar may temporarily block requests if too many are made
       - Wait 5-10 minutes before trying again
       - The app uses proxies to help avoid this
    
    4. **Invalid Author ID:**
       - Double-check the author ID in the Google Scholar URL
       - Make sure the profile is public and has publications
    
    5. **No Results:**
       - Check if the author has publications in your specified date range
       - Try expanding the date range
    """)

# Inputs for the time frame
start_year = st.number_input("Start Year", min_value=1900, max_value=2100, value=2023)
end_year = st.number_input("End Year", min_value=1900, max_value=2100, value=2025)

# Method selection
st.markdown("### 📊 Fetch Method")
method = st.radio(
    "Choose how to fetch the data:",
    ["Try Scholarly Library First (Recommended)", "Use Web Scraping Only"],
    help="Web scraping is more reliable when the scholarly library has issues"
)

# Cache control
use_cache = st.checkbox("Use cached results (if available)", value=True, 
                        help="Uncheck to force fresh data fetch. Cache expires after 1 hour.")

if st.button("Fetch Papers"):
    if scholar_id:
        if start_year > end_year:
            st.error("Error: Start year must be before or the same as the end year.")
        else:
            with st.spinner("Fetching data from Google Scholar..."):
                if method == "Use Web Scraping Only":
                    st.info("Using web scraping method directly...")
                    # Check cache for web scraping method too
                    cache_key = get_cache_key(scholar_id, start_year, end_year, 'webscraping')
                    papers = None
                    if use_cache:
                        papers = get_cached_results(cache_key)
                        if papers:
                            st.success(f"✅ Loaded {len(papers)} papers from cache!")
                    
                    if not papers:
                        papers = fetch_scholar_data_alternative(scholar_id, start_year, end_year)
                        if papers:
                            set_cached_results(cache_key, papers)
                else:
                    papers = fetch_scholar_data(scholar_id, start_year, end_year, use_cache=use_cache)
            
            if papers:
                st.success("Data fetched successfully!")
                
                # Create formatted text for copying (papers are already sorted by year descending)
                formatted_text = ""
                for i, paper in enumerate(papers, 1):
                    title = paper['bib']['title']
                    year = paper['bib'].get('pub_year', 'N/A')
                    authors = paper['bib'].get('author', 'Unknown authors')
                    citations = paper['bib'].get('citation_count', paper.get('num_citations', 0))
                    url = paper.get('pub_url', '')
                    abstract = paper.get('bib', {}).get('abstract', 'No abstract available.')
                    
                    formatted_text += f"{i}. {title} ({year})\n"
                    formatted_text += f"Authors: {authors}\n"
                    formatted_text += f"Citations: {citations}\n"
                    if abstract and abstract != 'No abstract available.':
                        formatted_text += f"Abstract: {abstract}\n"
                    if url:
                        formatted_text += f"URL: {url}\n"
                    formatted_text += "\n" + "="*80 + "\n\n"
                
                # Add copy functionality using text_area (no page reload)
                st.markdown("### 📋 Copy All Papers")
                st.markdown("*Click in the text area below and press Ctrl+A to select all, then Ctrl+C to copy:*")
                st.text_area(
                    "All Papers (sorted from most recent to oldest):",
                    value=formatted_text,
                    height=200,
                    help="Click in this box and press Ctrl+A to select all, then Ctrl+C to copy"
                )
                
                st.markdown("---")
                st.markdown("### 📄 Individual Papers")
                
                # Display papers in expandable format
                for i, paper in enumerate(papers):
                    title = paper['bib']['title']
                    year = paper['bib'].get('pub_year', 'N/A')
                    authors = paper['bib'].get('author', 'Unknown authors')
                    citations = paper['bib'].get('citation_count', paper.get('num_citations', 0))
                    
                    with st.expander(f"**{title}** ({year}) - {citations} citations"):
                        st.markdown(f"**Authors:** {authors}")
                        st.markdown(f"**Citations:** {citations}")
                        
                        abstract = paper.get('bib', {}).get('abstract', '')
                        if abstract and abstract != 'No abstract available.':
                            st.markdown("**Abstract:**")
                            st.write(abstract)
                        else:
                            st.info("Abstract not available (web scraping limitation)")
                            
                        if paper.get('pub_url'):
                            st.markdown(f"[Read Paper]({paper['pub_url']})")

    else:
        st.warning("Please enter a Google Scholar Author ID.")
