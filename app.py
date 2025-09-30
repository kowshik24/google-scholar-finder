import streamlit as st
from scholarly import scholarly, ProxyGenerator
from tavily import TavilyClient

tavily_client = TavilyClient(api_key="tvly-YOUR_API_KEY")

# Set up a proxy to avoid getting blocked by Google Scholar
# This is a good practice when scraping web data.
try:
    pg = ProxyGenerator()
    # You can try to use a free proxy service like the one below
    success = pg.FreeProxies()
    if success:
        scholarly.use_proxy(pg)
        print("Proxy setup successful")
    else:
        print("Proxy setup failed, proceeding without proxy")
except Exception as e:
    print(f"Proxy setup failed: {e}. Proceeding without proxy.")
    # Continue without proxy - scholarly can work without it, just with higher risk of being blocked

def fetch_scholar_data(author_id, start_year, end_year):
    """
    Fetches paper titles and abstracts for a given Google Scholar author ID and time frame.
    """
    try:
        st.write(f"Fetching data for author ID: {author_id}...")
        # Retrieve the author's profile
        author = scholarly.search_author_id(author_id)
        
        st.write("Author found, fetching publications...")
        # Fill the author's publications
        author = scholarly.fill(author, sections=['publications'])
        
        papers = []
        for pub in author['publications']:
            # Check if the paper has a 'pub_year' and if it's within the specified range
            if 'pub_year' in pub['bib'] and start_year <= int(pub['bib']['pub_year']) <= end_year:
                # Fill the publication to get more details like the abstract
                filled_pub = scholarly.fill(pub)
                papers.append(filled_pub)
        
        # Sort papers by year in descending order (most recent first)
        papers.sort(key=lambda x: int(x['bib'].get('pub_year', 0)), reverse=True)
        
        st.write(f"Found {len(papers)} papers between {start_year} and {end_year}.")
        return papers
    except Exception as e:
        st.error(f"An error occurred: {e}")
        st.error("This could be due to network issues, an invalid author ID, or being temporarily blocked by Google Scholar. Please check the ID and try again later.")
        return None

# --- Streamlit App ---

st.title("Google Scholar Paper Fetcher")

st.write("Enter a Google Scholar author ID and a date range to fetch their paper titles and abstracts.")

# Input for Google Scholar Author ID
scholar_id = st.text_input("Google Scholar Author ID", "qc6CJjYAAAAJ")
st.markdown("You can find the author ID in the URL of their Google Scholar profile. For example, for Stephen Hawking, the URL is `https://scholar.google.com/citations?user=qc6CJjYAAAAJ`, so the ID is `qc6CJjYAAAAJ`.")

# Inputs for the time frame
start_year = st.number_input("Start Year", min_value=1900, max_value=2100, value=2023)
end_year = st.number_input("End Year", min_value=1900, max_value=2100, value=2025)

if st.button("Fetch Papers"):
    if scholar_id:
        if start_year > end_year:
            st.error("Error: Start year must be before or the same as the end year.")
        else:
            with st.spinner("Fetching data from Google Scholar..."):
                papers = fetch_scholar_data(scholar_id, start_year, end_year)
            
            if papers:
                st.success("Data fetched successfully!")
                
                # Create formatted text for copying (papers are already sorted by year descending)
                formatted_text = ""
                for i, paper in enumerate(papers, 1):
                    title = paper['bib']['title']
                    year = paper['bib'].get('pub_year', 'N/A')
                    abstract = paper.get('bib', {}).get('abstract', 'No abstract available.')
                    url = paper.get('pub_url', '')
                    
                    formatted_text += f"{i}. {title} ({year})\n"
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
                    with st.expander(f"**{paper['bib']['title']}** ({paper['bib'].get('pub_year', 'N/A')})"):
                        st.markdown("**Abstract:**")
                        st.write(paper.get('bib', {}).get('abstract', 'No abstract available.'))
                        if 'pub_url' in paper:
                            st.markdown(f"[Read Paper]({paper['pub_url']})")

    else:
        st.warning("Please enter a Google Scholar Author ID.")
