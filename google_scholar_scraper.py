import requests
from bs4 import BeautifulSoup
import time
import csv
from urllib.parse import urljoin

def get_paper_details(paper_url, session):
    """
    Fetch detailed information including abstract for a specific paper.
    """
    try:
        response = session.get(paper_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract abstract
        abstract = ""
        abstract_div = soup.find('div', {'class': 'gsh_small'})
        if abstract_div:
            abstract = abstract_div.get_text(strip=True)
        
        return abstract
    except Exception as e:
        print(f"Error fetching paper details: {e}")
        return ""

def scrape_google_scholar_profile(user_id, start_year=2023, end_year=2026):
    """
    Scrape papers and abstracts from a Google Scholar profile for specified years.
    
    Args:
        user_id: The Google Scholar user ID
        start_year: Starting year (inclusive)
        end_year: Ending year (inclusive)
    """
    base_url = f"https://scholar.google.ca/citations?hl=en&user={user_id}&view_op=list_works&sortby=pubdate"
    
    # Create a session to persist cookies
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    
    papers = []
    page_start = 0
    
    print(f"Scraping papers from {start_year} to {end_year}...")
    
    while True:
        # Add pagination parameter
        url = f"{base_url}&cstart={page_start}&pagesize=100"
        
        try:
            response = session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all paper entries
            paper_entries = soup.find_all('tr', {'class': 'gsc_a_tr'})
            
            if not paper_entries:
                break
            
            papers_on_page = 0
            
            for entry in paper_entries:
                try:
                    # Extract title and link
                    title_element = entry.find('a', {'class': 'gsc_a_at'})
                    if not title_element:
                        continue
                    
                    title = title_element.get_text(strip=True)
                    paper_link = urljoin('https://scholar.google.ca', title_element['href'])
                    
                    # Extract year
                    year_element = entry.find('span', {'class': 'gsc_a_h gsc_a_hc gs_ibl'})
                    if not year_element:
                        continue
                    
                    year_text = year_element.get_text(strip=True)
                    if not year_text.isdigit():
                        continue
                    
                    year = int(year_text)
                    
                    # Filter by year range
                    if year < start_year:
                        # Since papers are sorted by date (newest first), we can stop
                        print(f"Reached papers older than {start_year}, stopping...")
                        return papers
                    
                    if year > end_year:
                        continue
                    
                    # Extract authors and publication info
                    authors_element = entry.find('div', {'class': 'gs_gray'})
                    authors = authors_element.get_text(strip=True) if authors_element else ""
                    
                    publication_element = entry.find_all('div', {'class': 'gs_gray'})
                    publication = publication_element[1].get_text(strip=True) if len(publication_element) > 1 else ""
                    
                    # Extract citation count
                    citation_element = entry.find('a', {'class': 'gsc_a_ac gs_ibl'})
                    citations = citation_element.get_text(strip=True) if citation_element else "0"
                    
                    print(f"Processing: {title} ({year})")
                    
                    # Get abstract from paper detail page
                    time.sleep(1)  # Be polite to the server
                    abstract = get_paper_details(paper_link, session)
                    
                    paper_data = {
                        'title': title,
                        'authors': authors,
                        'publication': publication,
                        'year': year,
                        'citations': citations,
                        'abstract': abstract,
                        'url': paper_link
                    }
                    
                    papers.append(paper_data)
                    papers_on_page += 1
                    
                except Exception as e:
                    print(f"Error processing paper entry: {e}")
                    continue
            
            if papers_on_page == 0:
                break
            
            # Move to next page
            page_start += 100
            time.sleep(2)  # Be polite to the server
            
        except Exception as e:
            print(f"Error fetching page: {e}")
            break
    
    return papers

def save_to_csv(papers, filename='google_scholar_papers.csv'):
    """
    Save scraped papers to a CSV file.
    """
    if not papers:
        print("No papers to save.")
        return
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['title', 'authors', 'publication', 'year', 'citations', 'abstract', 'url']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for paper in papers:
            writer.writerow(paper)
    
    print(f"Saved {len(papers)} papers to {filename}")

def main():
    # The Google Scholar user ID from the URL
    user_id = "a6MYnuUAAAAJ"
    
    # Scrape papers
    papers = scrape_google_scholar_profile(user_id, start_year=2023, end_year=2026)
    
    # Display results
    print(f"\nFound {len(papers)} papers from 2023-2026:\n")
    for i, paper in enumerate(papers, 1):
        print(f"{i}. {paper['title']} ({paper['year']})")
        print(f"   Authors: {paper['authors']}")
        print(f"   Publication: {paper['publication']}")
        print(f"   Citations: {paper['citations']}")
        print(f"   Abstract: {paper['abstract'][:200]}..." if len(paper['abstract']) > 200 else f"   Abstract: {paper['abstract']}")
        print(f"   URL: {paper['url']}")
        print()
    
    # Save to CSV
    save_to_csv(papers)

if __name__ == "__main__":
    main()
