# -*- coding: utf-8 -*-
"""
DGA Awards Scraper
"""

import json
from . import CEREMONY_MAP, fetch_page, ordinal


def scrape_dga(year):
    """
    Get DGA (Directors Guild of America) data for a specific year.
    Reads from pre-scraped dga_awards.json file (scraped via Selenium from dga.org).
    """
    import os

    dga_file = 'scraper/dga_awards.json'

    results = {
        'best-film': [],
        'best-director': [],
        'best-actor': [],
        'best-actress': []
    }

    if not os.path.exists(dga_file):
        print(f"  DGA: File not found: {dga_file}")
        print(f"       Run 'python scraper/dga_scraper.py' first to scrape DGA data.")
        return results

    with open(dga_file, 'r', encoding='utf-8') as f:
        dga_data = json.load(f)

    year_str = str(year)
    if year_str not in dga_data:
        print(f"  DGA: No data for year {year}")
        return results

    year_data = dga_data[year_str]

    # Copy best-director entries
    if 'best-director' in year_data:
        results['best-director'] = year_data['best-director'].copy()

    print(f"  DGA ({year}): Found {len(results['best-director'])} directors")
    return results


def scrape_dga_wikipedia(ceremony_num):
    """
    Scrape DGA Feature Film nominees/winners from Wikipedia.
    Used for 2026+ editions. Page uses <th> headers (not <div>).
    """
    url = f'https://en.wikipedia.org/wiki/{ordinal(ceremony_num)}_Directors_Guild_of_America_Awards'
    print(f"  DGA ({ordinal(ceremony_num)}): {url}")

    soup = fetch_page(url)
    if not soup:
        return {}

    results = {
        'best-film': [],
        'best-director': [],
        'best-actor': [],
        'best-actress': []
    }

    # Find the table with "Feature Film" header in <th>
    for table in soup.find_all('table', class_='wikitable'):
        th = table.find('th')
        if not th:
            continue
        header_text = th.get_text().strip().lower()
        if 'feature film' not in header_text:
            continue

        # Found Feature Film table — parse the <td> cell with nominees
        td = table.find('td')
        if not td:
            continue

        seen = set()

        # Parse all <li> items: winner is in bold, others are nominees
        for li in td.find_all('li', recursive=True):
            first_link = li.find('a')
            if not first_link:
                continue

            name = first_link.get_text().strip()
            if len(name) < 2:
                continue

            # Get film name from second <a> link (format: Director – Film)
            all_links = li.find_all('a')
            film = all_links[1].get_text().strip() if len(all_links) >= 2 else ''

            entry_key = (name, film)
            if entry_key in seen:
                continue
            seen.add(entry_key)

            is_winner = li.find('b') is not None or first_link.find_parent('b') is not None

            entry = {
                'name': name,
                'awards': {'dga': 'Y' if is_winner else 'X'}
            }
            if film:
                entry['film'] = film

            results['best-director'].append(entry)

        # Also check for winner in bold <p> before the list (same pattern as other awards)
        for bold in td.find_all('b', recursive=True):
            if bold.find_parent('li'):
                continue
            first_link = bold.find('a')
            if not first_link:
                continue
            name = first_link.get_text().strip()
            if len(name) < 2:
                continue

            all_links = bold.find_all('a')
            film = all_links[1].get_text().strip() if len(all_links) >= 2 else ''

            entry_key = (name, film)
            if entry_key in seen:
                continue
            seen.add(entry_key)

            entry = {
                'name': name,
                'awards': {'dga': 'Y'},
                'film': film
            }
            results['best-director'].append(entry)

        break  # Only process Feature Film table

    print(f"  DGA: Found {len(results['best-director'])} directors")
    return results
