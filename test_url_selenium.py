from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def fetch_with_selenium(url):
    """
    Fetch URL content using Selenium to handle JavaScript requirements
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in background
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        driver.get(url)
        
        # Wait for page to load
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Get page content
        content = driver.page_source
        
        driver.quit()
        return content
        
    except Exception as e:
        print(f"Error fetching with Selenium: {e}")
        return None

if __name__ == "__main__":
    url = "https://dl.acm.org/doi/abs/10.1145/3734477.3736148"
    content = fetch_with_selenium(url)
    if content:
        print("Successfully fetched content with Selenium")
        print(content[:500] + "..." if len(content) > 500 else content)
    else:
        print("Failed to fetch content")