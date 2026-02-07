# -*- coding: utf-8 -*-
"""
DGA Awards Scraper
"""

import json
from . import CEREMONY_MAP, URL_TEMPLATES, fetch_page, ordinal, init_results

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


