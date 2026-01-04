# -*- coding: utf-8 -*-
"""
AFI Awards Scraper
"""

from . import CEREMONY_MAP, URL_TEMPLATES, fetch_page, ordinal, init_results

_afi_soup_cache = None

def scrape_afi(year):
    """
    Scrape AFI Awards for a specific year from the single Wikipedia page.
    AFI year = calendar year of films (e.g., 2024 for films released in 2024)
    """
    global _afi_soup_cache
    
    AFI_URL = "https://en.wikipedia.org/wiki/American_Film_Institute_Awards"
    
    # Fetch page only once
    if _afi_soup_cache is None:
        print(f"  AFI: Fetching {AFI_URL}")
        _afi_soup_cache = fetch_page(AFI_URL)
        if not _afi_soup_cache:
            return {}
    
    soup = _afi_soup_cache
    
    results = {
        'best-film': [],
        'best-director': [],
        'best-actor': [],
        'best-actress': []
    }
    
    # Find the year section by looking for h2 with id="YEAR" or span with id="YEAR"
    year_header = soup.find(id=str(year))
    if not year_header:
        print(f"    AFI: Year {year} section not found")
        return results
    
    # Navigate from the header to find "Top 10 Films" section
    # The h2 is wrapped in a div, so get the parent and iterate siblings
    current = year_header.parent
    
    found_films = False
    found_special = False
    
    while current:
        current = current.next_sibling
        if not current:
            break
            
        # Skip text nodes
        if not hasattr(current, 'name'):
            continue
            
        # Stop at next year section (another h2, or div containing h2)
        if current.name == 'h2':
            break
        if current.name == 'div' and current.find('h2'):
            break
        
        # Check for section headers (h3 or div containing h3)
        h3 = None
        containing_div = None
        if current.name == 'h3':
            h3 = current
        elif current.name == 'div':
            h3 = current.find('h3')
            if h3:
                containing_div = current
        
        if h3:
            h3_text = h3.get_text().lower()
            if 'top 10 films' in h3_text or 'top 11 films' in h3_text:
                found_films = True
                found_special = False
                # Check if UL is inside this same div
                if containing_div:
                    ul = containing_div.find('ul')
                    if ul:
                        for li in ul.find_all('li', recursive=False):
                            link = li.find('a')
                            if link:
                                film_name = link.get_text().strip()
                                if len(film_name) >= 2:
                                    entry = {
                                        'name': film_name,
                                        'awards': {'afi': 'Y'}
                                    }
                                    results['best-film'].append(entry)
                        found_films = False  # Already processed
            elif 'special award' in h3_text:
                found_special = True
                found_films = False
                # Check if UL is inside this same div
                if containing_div:
                    ul = containing_div.find('ul')
                    if ul:
                        for li in ul.find_all('li', recursive=False):
                            link = li.find('a')
                            if link:
                                film_name = link.get_text().strip()
                                if len(film_name) >= 2:
                                    entry = {
                                        'name': film_name,
                                        'awards': {'afi': 'Y'},
                                        'note': 'AFI Special Award'
                                    }
                                    results['best-film'].append(entry)
                        found_special = False  # Already processed
            else:
                found_films = False
                found_special = False
            continue
        
        # Also parse ul elements that come as siblings (for older format pages)
        if (found_films or found_special) and current.name == 'ul':
            for li in current.find_all('li', recursive=False):
                link = li.find('a')
                if link:
                    film_name = link.get_text().strip()
                    if len(film_name) >= 2:
                        entry = {
                            'name': film_name,
                            'awards': {'afi': 'Y'}
                        }
                        if found_special:
                            entry['note'] = 'AFI Special Award'
                        results['best-film'].append(entry)
            
            # Reset after processing
            if found_films:
                found_films = False
            if found_special:
                found_special = False
    
    print(f"    AFI {year}: Found {len(results['best-film'])} films")
    return results


