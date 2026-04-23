import os
import random
import time
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

AUTHOR_ID = os.getenv("AUTHOR_ID", "Q5qzD7EAAAAJ")
START_YEAR = int(os.getenv("START_YEAR", "2024"))
END_YEAR = int(os.getenv("END_YEAR", "2026"))

DECODO_USERNAME = os.getenv("DECODO_USERNAME", "")
DECODO_PASSWORD = os.getenv("DECODO_PASSWORD", "")

OUTPUT_CSV = os.getenv("OUTPUT_CSV", "scholar_results.csv")

FETCH_ABSTRACTS = os.getenv("FETCH_ABSTRACTS", "true").lower() == "true"
SAVE_EVERY_N = int(os.getenv("SAVE_EVERY_N", "10"))
BASE_DELAY_MIN = float(os.getenv("BASE_DELAY_MIN", "1.8"))
BASE_DELAY_MAX = float(os.getenv("BASE_DELAY_MAX", "3.0"))
DETAIL_DELAY_MIN = float(os.getenv("DETAIL_DELAY_MIN", "2.2"))
DETAIL_DELAY_MAX = float(os.getenv("DETAIL_DELAY_MAX", "4.0"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

BASE_URL = "https://scholar.google.com"


def build_proxy_url(username, password):
    return f"http://{username}:{password}@gate.decodo.com:10001"


def make_session(username, password):
    session = requests.Session()
    if username and password:
        proxy_url = build_proxy_url(username, password)
        session.proxies = {
            "http": proxy_url,
            "https": proxy_url,
        }

    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    })
    return session


def ghum(min_s, max_s):
    time.sleep(random.uniform(min_s, max_s))


def normalize_title(txt):
    if not isinstance(txt, str):
        return ""
    return " ".join(txt.strip().lower().split())


def load_existing(csv_path):
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
            print(f"Loaded existing cache: {csv_path} ({len(df)} rows)")
            return df
        except Exception as err:
            print(f"Could not read cache: {err}")

    return pd.DataFrame(columns=[
        "Title", "Year", "Authors", "Venue", "Citation Count", "Scholar URL", "Abstract"
    ])


def save_rows(rows, csv_path):
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    print(f"Saved {len(rows)} rows to {csv_path}")


def get_with_retry(session, url, params=None, timeout=40, label="request"):
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            res = session.get(url, params=params, timeout=timeout)
            res.raise_for_status()
            return res
        except Exception as err:
            last_err = err
            wait_time = 2.5 + random.uniform(1, 2.5) + (attempt - 1) * 2
            print(f"{label} failed ({attempt}/{MAX_RETRIES}): {err}")
            print(f"waiting {wait_time:.1f}s")
            time.sleep(wait_time)

    raise RuntimeError(f"{label} failed after {MAX_RETRIES} retries. Last error: {last_err}")


def parse_author_page(html):
    soup = BeautifulSoup(html, "html.parser")

    author_name = soup.select_one("#gsc_prf_in")
    author_name = author_name.get_text(" ", strip=True) if author_name else "N/A"

    rows = []
    for tr in soup.select("tr.gsc_a_tr"):
        try:
            title_tag = tr.select_one("a.gsc_a_at")
            if not title_tag:
                continue

            title = title_tag.get_text(" ", strip=True)
            rel_link = title_tag.get("href", "")
            scholar_url = urljoin(BASE_URL, rel_link) if rel_link else "N/A"

            meta_tags = tr.select("div.gs_gray")
            authors = meta_tags[0].get_text(" ", strip=True) if len(meta_tags) > 0 else "N/A"
            venue = meta_tags[1].get_text(" ", strip=True) if len(meta_tags) > 1 else "N/A"

            cited_tag = tr.select_one("a.gsc_a_ac")
            citation_count = cited_tag.get_text(" ", strip=True) if cited_tag else "0"
            citation_count = int(citation_count) if citation_count.isdigit() else 0

            year_tag = tr.select_one(".gsc_a_y span")
            year_text = year_tag.get_text(" ", strip=True) if year_tag else ""
            year = int(year_text) if year_text.isdigit() else None

            rows.append({
                "Title": title,
                "Year": year,
                "Authors": authors,
                "Venue": venue,
                "Citation Count": citation_count,
                "Scholar URL": scholar_url,
                "Abstract": "",
            })
        except Exception:
            continue

    return author_name, rows


def fetch_all_publications(session, author_id):
    all_rows = []
    start = 0
    author_name_final = None

    while True:
        url = f"{BASE_URL}/citations"
        params = {
            "user": author_id,
            "hl": "en",
            "cstart": start,
            "pagesize": 100,
        }

        res = get_with_retry(session, url, params=params, label=f"author page start={start}")
        author_name, page_rows = parse_author_page(res.text)

        if author_name_final is None:
            author_name_final = author_name

        if not page_rows:
            break

        all_rows.extend(page_rows)
        print(f"Fetched page starting at {start}, got {len(page_rows)} papers")

        if len(page_rows) < 100:
            break

        start += 100
        ghum(BASE_DELAY_MIN, BASE_DELAY_MAX)

    return author_name_final, all_rows


def fetch_abstract_from_detail(session, scholar_url):
    if not scholar_url or scholar_url == "N/A":
        return "No abstract available."

    res = get_with_retry(session, scholar_url, label="detail page")
    soup = BeautifulSoup(res.text, "html.parser")

    abs_box = soup.select_one("#gsc_oci_descr")
    if abs_box:
        txt = abs_box.get_text(" ", strip=True)
        return txt if txt else "No abstract available."

    for row in soup.select(".gs_scl"):
        field = row.select_one(".gsc_oci_field")
        value = row.select_one(".gsc_oci_value")
        if field and value and "description" in field.get_text(" ", strip=True).lower():
            txt = value.get_text(" ", strip=True)
            return txt if txt else "No abstract available."

    return "No abstract available."


def scrape_author_cost_optimized(session, author_id, start_year, end_year, fetch_abstracts, output_csv, use_cache=True):
    if use_cache:
        cache_df = load_existing(output_csv)
        existing_titles = set(cache_df["Title"].dropna().map(normalize_title).tolist())
        final_res = cache_df.to_dict(orient="records")
    else:
        existing_titles = set()
        final_res = []
        print("Cache disabled for scraper run; fetching fresh Google Scholar data.")

    author_name, all_rows = fetch_all_publications(session, author_id)
    print(f"Author: {author_name}")
    print(f"Total publications found on profile: {len(all_rows)}")

    filtered = []
    for row in all_rows:
        year = row.get("Year")
        title = row.get("Title", "")

        if year is None:
            continue
        if not (start_year <= year <= end_year):
            continue
        if normalize_title(title) in existing_titles:
            continue

        filtered.append(row)

    print(f"Publications selected in {start_year}-{end_year}: {len(filtered)}")
    if not filtered:
        print("Nothing to scrape for the requested range.")
        return final_res

    unsaved = 0
    for pub in tqdm(filtered):
        try:
            if fetch_abstracts:
                ghum(DETAIL_DELAY_MIN, DETAIL_DELAY_MAX)
                pub["Abstract"] = fetch_abstract_from_detail(session, pub["Scholar URL"])
            else:
                pub["Abstract"] = "Skipped to save proxy usage."

            final_res.append(pub)
            existing_titles.add(normalize_title(pub["Title"]))
            unsaved += 1

            if output_csv and unsaved >= SAVE_EVERY_N:
                save_rows(final_res, output_csv)
                unsaved = 0

            ghum(BASE_DELAY_MIN, BASE_DELAY_MAX)
        except Exception as err:
            print(f"Skipping '{pub.get('Title', 'N/A')}' due to error: {err}")
            ghum(1.5, 2.5)

    if output_csv:
        save_rows(final_res, output_csv)
    return final_res


def main():
    session = make_session(DECODO_USERNAME, DECODO_PASSWORD)
    data = scrape_author_cost_optimized(
        session=session,
        author_id=AUTHOR_ID,
        start_year=START_YEAR,
        end_year=END_YEAR,
        fetch_abstracts=FETCH_ABSTRACTS,
        output_csv=OUTPUT_CSV,
        use_cache=False,
    )

    data_in_range = []
    for row in data:
        year = row.get("Year")
        if isinstance(year, (int, float)) and START_YEAR <= int(year) <= END_YEAR:
            data_in_range.append(row)

    data_in_range = sorted(
        data_in_range,
        key=lambda x: (int(x.get("Year", 0)), x.get("Title", "")),
        reverse=True,
    )

    print(f"\nDone! Total stored papers in range {START_YEAR}-{END_YEAR}: {len(data_in_range)}\n")
    for idx, paper in enumerate(data_in_range, start=1):
        print(f"{idx}. {paper['Title']} ({int(paper['Year'])})")
        print(f"Authors: {paper['Authors']}")
        print(f"Venue: {paper['Venue']}")
        print(f"Citations: {paper['Citation Count']}")
        print(f"Scholar URL: {paper['Scholar URL']}")
        print(f"Abstract: {paper['Abstract']}")
        print("=" * 100)


if __name__ == "__main__":
    main()
