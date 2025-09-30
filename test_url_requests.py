import requests
from bs4 import BeautifulSoup
import time
import random

def fetch_with_requests(url):
    """
    Fetch URL content using requests with proper headers and session
    """
    session = requests.Session()
    
    # Set headers to mimic a real browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0',
    }
    
    session.headers.update(headers)
    
    try:
        # Add a small delay to avoid being detected as a bot
        time.sleep(random.uniform(1, 3))
        
        response = session.get(url, timeout=10)
        response.raise_for_status()
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract text content
        text = soup.get_text()
        
        return text
        
    except Exception as e:
        print(f"Error fetching with requests: {e}")
        return None

if __name__ == "__main__":
    url = "https://dl.acm.org/doi/abs/10.1145/3734477.3736148"
    content = fetch_with_requests(url)
    if content:
        print("Successfully fetched content with requests")
        print(content[:1000] + "..." if len(content) > 1000 else content)
    else:
        print("Failed to fetch content")