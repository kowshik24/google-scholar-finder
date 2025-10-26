import streamlit as st
from scholarly import scholarly, ProxyGenerator
from tavily import TavilyClient
import random

#tavily_client = TavilyClient(api_key="tvly-YOUR_API_KEY")

# Set up a proxy to avoid getting blocked by Google Scholar
# This is a good practice when scraping web data.
def setup_proxy():
    try:
        pg = ProxyGenerator()
        # Try multiple proxy methods
        success = False
        
        # Try free proxies first
        try:
            success = pg.FreeProxies()
            if success:
                scholarly.use_proxy(pg)
                print("Free proxy setup successful")
                return True
        except:
            pass
        
        # Try Luminati proxy if free proxies fail
        if not success:
            try:
                success = pg.Luminati(usr="", passwd="", port=22225)
                if success:
                    scholarly.use_proxy(pg)
                    print("Luminati proxy setup successful")
                    return True
            except:
                pass
        
        # Try ScraperAPI if other methods fail
        if not success:
            try:
                success = pg.ScraperAPI("")
                if success:
                    scholarly.use_proxy(pg)
                    print("ScraperAPI proxy setup successful")
                    return True
            except:
                pass
        
        print("All proxy methods failed, proceeding without proxy")
        return False
        
    except Exception as e:
        print(f"Proxy setup failed: {e}. Proceeding without proxy.")
        return False

# Initialize proxy
proxy_setup_success = setup_proxy()

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

def test_connection():
    """Test if we can connect to Google Scholar"""
    try:
        # Try to search for a known author to test connection
        test_author = scholarly.search_author("Einstein")
        return test_author is not None
    except Exception as e:
        print(f"Connection test failed: {e}")
        return False

def fetch_scholar_data_alternative(author_id, start_year, end_year):
    """
    Alternative method to fetch author data using direct web scraping approach
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        import time
        import random
        import re
        
        st.write("Trying alternative web scraping method...")
        
        # Construct the Google Scholar URL
        url = f"https://scholar.google.com/citations?user={author_id}&hl=en"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Add random delay to avoid being blocked
        time.sleep(random.uniform(2, 4))
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            st.error(f"Failed to fetch author page. Status code: {response.status_code}")
            return None
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Check if author exists
        if "not found" in response.text.lower() or "profile not found" in response.text.lower():
            st.error("Author profile not found. Please verify the author ID.")
            return None
        
        st.write("Author page found, extracting publications...")
        
        # Extract author name
        author_name = "Unknown Author"
        name_elem = soup.find('div', {'id': 'gsc_prf_in'})
        if name_elem:
            author_name = name_elem.get_text(strip=True)
        
        st.write(f"Author: {author_name}")
        
        # Find publications in the page
        publications = []
        
        # Look for publication entries
        pub_rows = soup.find_all('tr', class_='gsc_a_tr')
        
        if not pub_rows:
            # Try alternative selectors
            pub_rows = soup.find_all('div', class_='gsc_a_tr')
        
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
                
                # Skip if year is not in range
                if year and (year < start_year or year > end_year):
                    continue
                
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
                
                # Add progress indicator
                if (i + 1) % 10 == 0:
                    st.write(f"Processed {i + 1} publications...")
                    
            except Exception as pub_error:
                st.warning(f"Skipping publication {i + 1} due to error: {pub_error}")
                continue
        
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
        import traceback
        st.error(f"Technical details: {traceback.format_exc()}")
        return None

def fetch_scholar_data(author_id, start_year, end_year):
    """
    Fetches paper titles and abstracts for a given Google Scholar author ID and time frame.
    """
    try:
        st.write(f"Fetching data for author ID: {author_id}...")
        
        # First, try the scholarly library with enhanced error handling
        author = None
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                st.write(f"Attempt {attempt + 1} to fetch author profile...")
                
                # Clear cache and reset proxy to avoid conflicts
                clear_scholarly_cache()
                
                # Try to get author profile
                author = scholarly.search_author_id(author_id)
                
                if author is not None and isinstance(author, dict):
                    st.write("✅ Author profile retrieved successfully!")
                    break
                else:
                    st.warning(f"Attempt {attempt + 1} returned None or invalid data. Retrying...")
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(random.uniform(2, 5))  # Random delay between retries
                        
            except AttributeError as attr_error:
                st.warning(f"Attempt {attempt + 1} failed with AttributeError: {attr_error}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(random.uniform(2, 5))
            except Exception as retry_error:
                st.warning(f"Attempt {attempt + 1} failed: {retry_error}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(random.uniform(2, 5))
        
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
        
        papers = []
        st.write(f"Processing {len(author['publications'])} publications...")
        
        for i, pub in enumerate(author['publications']):
            try:
                # Check if the paper has a 'pub_year' and if it's within the specified range
                if ('bib' in pub and 'pub_year' in pub['bib'] and 
                    start_year <= int(pub['bib']['pub_year']) <= end_year):
                    
                    # Fill the publication to get more details like the abstract
                    filled_pub = scholarly.fill(pub)
                    if filled_pub and 'bib' in filled_pub:
                        papers.append(filled_pub)
                    
                # Add progress indicator for large numbers of publications
                if (i + 1) % 10 == 0:
                    st.write(f"Processed {i + 1} publications...")
                    
            except Exception as pub_error:
                st.warning(f"Skipping publication {i + 1} due to error: {pub_error}")
                continue
        
        # Sort papers by year in descending order (most recent first)
        papers.sort(key=lambda x: int(x['bib'].get('pub_year', 0)), reverse=True)
        
        st.write(f"Found {len(papers)} papers between {start_year} and {end_year}.")
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
        st.success("✅ Proxy configured - Better protection against blocking")
    else:
        st.warning("⚠️ No proxy configured - Higher risk of being blocked")

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
            st.success("✅ Cache cleared!")

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

if st.button("Fetch Papers"):
    if scholar_id:
        if start_year > end_year:
            st.error("Error: Start year must be before or the same as the end year.")
        else:
            with st.spinner("Fetching data from Google Scholar..."):
                if method == "Use Web Scraping Only":
                    st.info("Using web scraping method directly...")
                    papers = fetch_scholar_data_alternative(scholar_id, start_year, end_year)
                else:
                    papers = fetch_scholar_data(scholar_id, start_year, end_year)
            
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
