# -*- coding: utf-8 -*-
"""
Master Awards Scraper
=====================
Scrapes all 5 major awards for a given season year.
Maps season years to correct ceremony numbers.
"""

import requests
from bs4 import BeautifulSoup
import json
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

TMDB_API_KEY = "4399b8147e098e80be332f172d1fe490"
TMDB_BASE_URL = "https://api.themoviedb.org/3"

# ============ YEAR TO CEREMONY MAPPING ============
# Season year is the SECOND year (e.g., 2024/25 season = year 2025)
# These ceremonies happen in early 2025 for films released in 2024

CEREMONY_MAP = {
    # Oscar started in 1929, 97th in 2025
    # Season 2024/25 (films from 2024) = 97th ceremony in Feb 2025
    'oscar': {
        2026: 98, 2025: 97, 2024: 96, 2023: 95, 2022: 94, 2021: 93,
        2020: 92, 2019: 91, 2018: 90, 2017: 89, 2016: 88,
        2015: 87, 2014: 86, 2013: 85
    },
    # Golden Globe: 82nd in Jan 2025
    'gg': {
        2026: 83, 2025: 82, 2024: 81, 2023: 80, 2022: 79, 2021: 78,
        2020: 77, 2019: 76, 2018: 75, 2017: 74, 2016: 73,
        2015: 72, 2014: 71, 2013: 70
    },
    # BAFTA: 78th in Feb 2025
    'bafta': {
        2026: 79, 2025: 78, 2024: 77, 2023: 76, 2022: 75, 2021: 74,
        2020: 73, 2019: 72, 2018: 71, 2017: 70, 2016: 69,
        2015: 68, 2014: 67, 2013: 66
    },
    # SAG: 31st in Feb 2025
    'sag': {
        2026: 32, 2025: 31, 2024: 30, 2023: 29, 2022: 28, 2021: 27,
        2020: 26, 2019: 25, 2018: 24, 2017: 23, 2016: 22,
        2015: 21, 2014: 20, 2013: 19
    },
    # Critics Choice: 30th in Jan 2025
    'critics': {
        2026: 31, 2025: 30, 2024: 29, 2023: 28, 2022: 27, 2021: 26,
        2020: 25, 2019: 24, 2018: 23, 2017: 22, 2016: 21,
        2015: 20, 2014: 19, 2013: 18
    },
    # AFI: year of films (2024 season = films from 2024 = AFI 2024)
    # Maps season second year to AFI year (which is first year)
    'afi': {
        2026: 2025, 2025: 2024, 2024: 2023, 2023: 2022, 2022: 2021, 2021: 2020,
        2020: 2019, 2019: 2018, 2018: 2017, 2017: 2016, 2016: 2015,
        2015: 2014, 2014: 2013, 2013: 2012
    },
    # NBR: same as AFI - year of films
    'nbr': {
        2026: 2025, 2025: 2024, 2024: 2023, 2023: 2022, 2022: 2021, 2021: 2020,
        2020: 2019, 2019: 2018, 2018: 2017, 2017: 2016, 2016: 2015,
        2015: 2014, 2014: 2013, 2013: 2012
    },
    # Venice: Mostra di Venezia - uses ordinal like 82ª for 82nd edition
    # 82nd in 2025 (Sept 2025 for 2024/2025 season films)
    'venice': {
        2026: 83, 2025: 82, 2024: 81, 2023: 80, 2022: 79, 2021: 78,
        2020: 77, 2019: 76, 2018: 75, 2017: 74, 2016: 73,
        2015: 72, 2014: 71, 2013: 70
    }
}

# Wikipedia URL templates - use {ord} placeholder for ordinal (like 82nd, 31st)
URL_TEMPLATES = {
    'oscar': 'https://en.wikipedia.org/wiki/{ord}_Academy_Awards',
    'gg': 'https://en.wikipedia.org/wiki/{ord}_Golden_Globe_Awards',  
    'bafta': 'https://en.wikipedia.org/wiki/{ord}_British_Academy_Film_Awards',
    'sag': 'https://en.wikipedia.org/wiki/{ord}_Screen_Actors_Guild_Awards',
    'critics': 'https://en.wikipedia.org/wiki/{ord}_Critics%27_Choice_Awards',
    'nbr': 'https://en.wikipedia.org/wiki/National_Board_of_Review_Awards_{year}',
    'venice': 'https://it.wikipedia.org/wiki/{ord}%C2%AA_Mostra_internazionale_d%27arte_cinematografica_di_Venezia'
}

# Ordinal number suffix
def ordinal(n):
    suffix = 'th' if 11 <= n % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"


def fetch_page(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"    Error: HTTP {response.status_code}")
        return None
    return BeautifulSoup(response.text, 'html.parser')


def parse_nominees_from_cell(cell, category_type, award_name):
    """Parse nominees from a cell."""
    nominees = []
    lis = cell.find_all('li', recursive=True)
    seen_names = set()
    
    for li in lis:
        first_link = li.find('a')
        if not first_link:
            continue
            
        link_title = first_link.get('title', '') or ''
        # Skip award links
        skip_words = ['Academy Award', 'Golden Globe', 'BAFTA', 'Screen Actors Guild', 
                      'Critics', 'Outstanding', 'Best ']
        if any(w in link_title for w in skip_words):
            continue
            
        name = first_link.get_text().strip()
        
        if len(name) < 2 or name in seen_names:
            continue
        
        seen_names.add(name)
        
        full_text = li.get_text()
        is_winner = li.find('b') is not None or '‡' in full_text
        
        # Get film name for person categories
        film = None
        if category_type in ['director', 'actor']:
            all_links = li.find_all('a')
            for link in all_links[1:]:
                link_text = link.get_text().strip()
                link_title = link.get('title', '') or ''
                if any(w in link_title for w in skip_words):
                    continue
                if len(link_text) > 1:
                    film = link_text
                    break
        
        entry = {'name': name, 'is_winner': is_winner}
        if film:
            entry['film'] = film
            
        nominees.append(entry)
    
    return nominees


def scrape_gg_old_format(tables_or_soup, award_key):
    """
    Parse Golden Globe pages with old format structure:
    - Main header (Best Motion Picture)
    - Subcategory row (Drama | Musical or Comedy) 
    - Nominees in <li> items with winners in bold
    - Director under 'Other' section
    """
    if hasattr(tables_or_soup, 'find_all'):
        tables = tables_or_soup.find_all('table', class_='wikitable')
    else:
        tables = tables_or_soup

    if not tables:
        return {}
    
    results = {
        'best-film': [],
        'best-director': [],
        'best-actor': [],
        'best-actress': []
    }
    
    seen_names = {'best-film': set(), 'best-director': set(), 
                  'best-actor': set(), 'best-actress': set()}
    
    for table in tables:
        rows = table.find_all('tr')
        
        current_main_cat = None  # 'film', 'actor-drama', 'actor-comedy', 'other'
        subcategories = []  # ['drama', 'musical or comedy'] or ['actor', 'actress']
        
        for row in rows:
            ths = row.find_all('th')
            tds = row.find_all('td')
            
            # Single TH = main category header
            if len(ths) == 1 and not tds:
                header = ths[0].get_text().strip().lower()
                
                # Explicitly skip Animated and Foreign categories to prevent bleeding
                if 'animated' in header or 'foreign' in header or 'non-english' in header:
                    current_main_cat = None
                    subcategories = []
                    continue

                if 'best motion picture' in header:
                    if 'animated' in header or 'foreign' in header or 'non-english' in header:
                        current_main_cat = None
                    else:
                        current_main_cat = 'film'
                elif 'performance' in header and 'drama' in header and 'television' not in header and 'miniseries' not in header:
                    current_main_cat = 'actor-drama'
                elif 'performance' in header and ('comedy' in header or 'musical' in header) and 'television' not in header and 'miniseries' not in header:
                    current_main_cat = 'actor-comedy'
                elif 'supporting' in header and 'motion picture' in header and 'television' not in header and 'series' not in header and 'miniseries' not in header:
                    if 'actor' in header:
                        current_main_cat = 'supporting-film-actor'
                    elif 'actress' in header:
                        current_main_cat = 'supporting-film-actress'
                    else:
                        current_main_cat = 'supporting-film'
                elif 'other' in header:
                    current_main_cat = 'other'
                else:
                    current_main_cat = None
                subcategories = []
                continue
            
            # Two THs = subcategory row (or combined category header like Animated|Foreign)
            if len(ths) >= 2 and not tds:
                subcategories = [th.get_text().strip().lower() for th in ths]
                # Check if ANY of the combined headers is Animated/Foreign - if so, skip
                combined_header = ' '.join(subcategories)
                if 'animated' in combined_header or 'foreign' in combined_header or 'non-english' in combined_header:
                    current_main_cat = None
                    subcategories = []
                # For acting categories, validate that subcategories are actually actor/actress
                elif current_main_cat in ['actor-drama', 'actor-comedy']:
                    has_actor_actress = any('actor' in s or 'actress' in s for s in subcategories)
                    if not has_actor_actress:
                        # Subcategories changed to Director/Screenplay/Score/Song - reset
                        current_main_cat = None
                        subcategories = []
                continue
            
            # TD row = nominees
            if tds and current_main_cat:
                for idx, td in enumerate(tds):
                    # Determine result key and genre/role
                    key = None
                    genre = None
                    role = None
                    entry_film_suffix = ''
                    
                    subcat = subcategories[idx].lower() if idx < len(subcategories) else ''
                    
                    if current_main_cat == 'film':
                        key = 'best-film'
                        genre = 'Drama' if 'drama' in subcat else 'Comedy'
                    elif current_main_cat == 'actor-drama':
                        role = 'Leading'
                        genre = 'Drama'
                        key = 'best-actress' if 'actress' in subcat else 'best-actor'
                    elif current_main_cat == 'actor-comedy':
                        role = 'Leading'
                        genre = 'Comedy'
                        key = 'best-actress' if 'actress' in subcat else 'best-actor'
                    elif current_main_cat == 'supporting-film-actor':
                        role = 'Supporting'
                        key = 'best-actor'
                        entry_film_suffix = ''
                    elif current_main_cat == 'supporting-film-actress':
                        role = 'Supporting'
                        key = 'best-actress'
                        entry_film_suffix = ''
                    elif current_main_cat == 'supporting-film':
                        role = 'Supporting'
                        entry_film_suffix = ''
                        if 'actor' in subcat:
                            key = 'best-actor'
                        elif 'actress' in subcat:
                            key = 'best-actress'
                    elif current_main_cat == 'other':
                        if 'director' in subcat:
                            key = 'best-director'
                    
                    if not key:
                        continue
                    
                    # Safety: If parsing for Actor/Actress/Director, ensure we don't pick up Animated films if header failed
                    if key in ['best-actor', 'best-actress', 'best-director']:
                         if 'animated' in td.get_text().lower():
                             continue

                    # Parse nominees from <li> items
                    lis = td.find_all('li')
                    for li in lis:
                        # Get first link = person/film name
                        first_link = li.find('a')
                        if not first_link:
                            continue
                        
                        name = first_link.get_text().strip()
                        if len(name) < 2:
                            continue
                        
                        # For actors/directors, get film name FIRST (before dedup check)
                        entry_film = ''
                        if key in ['best-actor', 'best-actress', 'best-director']:
                            all_links = li.find_all('a')
                            if len(all_links) >= 2:
                                entry_film = all_links[1].get_text().strip()
                        
                        # Skip if already seen (use name+film as unique key)
                        seen_key = f"{name}|{entry_film}"
                        if seen_key in seen_names[key]:
                            continue
                        seen_names[key].add(seen_key)
                        
                        # Check if winner (bold)
                        is_bold = li.find('b') is not None or first_link.find_parent('b') is not None
                        
                        entry = {
                            'name': name,
                            'awards': {award_key: 'Y' if is_bold else 'X'}
                        }
                        
                        # Add film name if found
                        if entry_film:
                            entry['film'] = entry_film + entry_film_suffix
                        
                        if genre and key == 'best-film':
                            entry['genre'] = genre
                        if role:
                            entry['role'] = role
                        
                        results[key].append(entry)
    
    return results


def scrape_sag_old_format(tables_or_soup, award_key):
    """
    Parse SAG pages with old format structure:
    - TH rows with "Outstanding Performance by Male/Female Actor in Leading/Supporting Role"
    - TD rows with nominees in <li> items
    - Cast in a Motion Picture for best-film equivalent
    """
    if hasattr(tables_or_soup, 'find_all'):
        tables = tables_or_soup.find_all('table', class_='wikitable')
    else:
        tables = tables_or_soup

    if not tables:
        return {}
    
    results = {
        'best-film': [],
        'best-director': [],
        'best-actor': [],
        'best-actress': []
    }
    
    seen_names = {'best-film': set(), 'best-actor': set(), 'best-actress': set()}
    
    for table in tables:
        rows = table.find_all('tr')
        
        current_keys = []  # e.g., ['best-actor', 'best-actress']
        current_roles = []  # e.g., ['Leading', 'Leading']
        
        for row in rows:
            ths = row.find_all('th')
            tds = row.find_all('td')
            
            # TH row = category headers
            if ths and not tds:
                current_keys = []
                current_roles = []
                for th in ths:
                    header = th.get_text().strip().lower()
                    
                    # Skip TV categories
                    if 'television' in header or 'series' in header or 'miniseries' in header:
                        current_keys.append(None)
                        current_roles.append(None)
                        continue
                    
                    key = None
                    role = None
                    
                    if 'cast in a motion picture' in header:
                        key = 'best-film'
                    elif 'female actor' in header:
                        key = 'best-actress'
                        role = 'Supporting' if 'supporting' in header else 'Leading'
                    elif 'male actor' in header:
                        key = 'best-actor'
                        role = 'Supporting' if 'supporting' in header else 'Leading'
                    
                    current_keys.append(key)
                    current_roles.append(role)
                continue
            
            # TD row = nominees
            if tds and current_keys:
                for idx, td in enumerate(tds):
                    if idx >= len(current_keys) or not current_keys[idx]:
                        continue
                    
                    key = current_keys[idx]
                    role = current_roles[idx] if idx < len(current_roles) else None
                    
                    # First, check for winner in <p><b> format (legacy SAG format)
                    # Winner is in <p><b><i>Film</i> - Actor, Actor</b></p> for Cast category
                    # Or <p><b><a>Actor</a> - Film</b></p> for actor categories
                    for p in td.find_all('p'):
                        b = p.find('b')
                        if b:
                            # For best-film (Cast category), get film from <i> tag
                            if key == 'best-film':
                                i_tag = b.find('i')
                                if i_tag:
                                    film_name = i_tag.get_text().strip()
                                    if len(film_name) >= 2 and film_name not in seen_names.get(key, set()):
                                        seen_names[key].add(film_name)
                                        entry = {
                                            'name': film_name,
                                            'awards': {award_key: 'Y'}
                                        }
                                        results[key].append(entry)
                            else:
                                # For actors, get name from first <a> tag
                                first_link = b.find('a')
                                if first_link:
                                    name = first_link.get_text().strip()
                                    if len(name) >= 2 and name not in seen_names.get(key, set()):
                                        if key in seen_names:
                                            seen_names[key].add(name)
                                        
                                        entry = {
                                            'name': name,
                                            'awards': {award_key: 'Y'}  # Winner
                                        }
                                        
                                        if key in ['best-actor', 'best-actress']:
                                            all_links = b.find_all('a')
                                            if len(all_links) >= 2:
                                                entry['film'] = all_links[1].get_text().strip()
                                            if role:
                                                entry['role'] = role
                                        
                                        results[key].append(entry)
                    
                    # Then parse nominees from <li> items
                    lis = td.find_all('li')
                    for li in lis:
                        # For best-film, get film name from <i> tag
                        if key == 'best-film':
                            i_tag = li.find('i')
                            if i_tag:
                                film_name = i_tag.get_text().strip()
                                if len(film_name) >= 2 and film_name not in seen_names.get(key, set()):
                                    seen_names[key].add(film_name)
                                    is_bold = li.find('b') is not None
                                    entry = {
                                        'name': film_name,
                                        'awards': {award_key: 'Y' if is_bold else 'X'}
                                    }
                                    results[key].append(entry)
                        else:
                            # For actors, get from first <a> tag
                            first_link = li.find('a')
                            if not first_link:
                                continue
                            
                            name = first_link.get_text().strip()
                            if len(name) < 2 or name in seen_names.get(key, set()):
                                continue
                            
                            if key in seen_names:
                                seen_names[key].add(name)
                            
                            # Check if winner (bold)
                            is_bold = li.find('b') is not None or first_link.find_parent('b') is not None
                            
                            entry = {
                                'name': name,
                                'awards': {award_key: 'Y' if is_bold else 'X'}
                            }
                            
                            # For actors, get film name (second link)
                            if key in ['best-actor', 'best-actress']:
                                all_links = li.find_all('a')
                                if len(all_links) >= 2:
                                    entry['film'] = all_links[1].get_text().strip()
                                if role:
                                    entry['role'] = role
                            
                            results[key].append(entry)
    
    return results


# Cache for AFI page (fetched once, used for all years)
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


def scrape_nbr(year):
    """
    Scrape NBR (National Board of Review) Awards for a specific year.
    NBR has individual pages per year with Top 10 Films and individual winner categories.
    """
    url = URL_TEMPLATES['nbr'].format(year=year)
    print(f"  NBR ({year}): {url}")
    
    soup = fetch_page(url)
    if not soup:
        return {}
    
    results = {
        'best-film': [],
        'best-director': [],
        'best-actor': [],
        'best-actress': []
    }
    
    seen_films = set()
    
    # Find Top 10 Films section (h2 with id="Top_10_Films")
    # Wikipedia wraps h2 in <div class="mw-heading mw-heading2">
    top10_h2 = soup.find('h2', id='Top_10_Films')
    if not top10_h2:
        # Fallback: search all h2 for text match
        for h2 in soup.find_all('h2'):
            if 'top' in h2.get_text().lower() and 'film' in h2.get_text().lower():
                top10_h2 = h2
                break
    
    if top10_h2:
        # Navigate from parent div (mw-heading wrapper)
        container = top10_h2.parent
        current = container.next_sibling if container else top10_h2.next_sibling
        
        while current:
            if not hasattr(current, 'name'):
                current = current.next_sibling
                continue
            
            # Stop at next section (div with mw-heading class or h2)
            if current.name == 'h2':
                break
            if current.name == 'div' and 'mw-heading' in current.get('class', []):
                break
            
            # Parse films from ul or p elements
            if current.name == 'ul':
                for li in current.find_all('li', recursive=False):
                    link = li.find('a')
                    if link:
                        film_name = link.get_text().strip()
                        if len(film_name) >= 2 and film_name not in seen_films:
                            seen_films.add(film_name)
                            entry = {
                                'name': film_name,
                                'awards': {'nbr': 'Y'}
                            }
                            results['best-film'].append(entry)
            elif current.name == 'p':
                # Best Film might be in a p tag with link
                link = current.find('a')
                if link:
                    film_name = link.get_text().strip()
                    if len(film_name) >= 2 and film_name not in seen_films:
                        seen_films.add(film_name)
                        entry = {
                            'name': film_name,
                            'awards': {'nbr': 'Y'}
                        }
                        results['best-film'].append(entry)
            
            current = current.next_sibling
    
    # Find Winners section (h2 with id="Winners")
    winners_h2 = soup.find('h2', id='Winners')
    if not winners_h2:
        for h2 in soup.find_all('h2'):
            if 'winner' in h2.get_text().lower():
                winners_h2 = h2
                break
    
    if winners_h2:
        container = winners_h2.parent
        current = container.next_sibling if container else winners_h2.next_sibling
        current_category = None
        
        while current:
            if not hasattr(current, 'name'):
                current = current.next_sibling
                continue
            
            # Stop at next section
            if current.name == 'h2':
                break
            if current.name == 'div' and 'mw-heading' in current.get('class', []):
                break
            
            # Check for category header (p > b with colon)
            if current.name == 'p':
                b = current.find('b')
                if b:
                    cat_text = b.get_text().lower()
                    if 'best director' in cat_text and 'debut' not in cat_text:
                        current_category = 'best-director'
                    elif 'best actor' in cat_text and 'supporting' not in cat_text:
                        current_category = 'best-actor'
                    elif 'best actress' in cat_text and 'supporting' not in cat_text:
                        current_category = 'best-actress'
                    else:
                        current_category = None
            
            # Parse winner from ul after category header
            if current.name == 'ul' and current_category:
                li = current.find('li')
                if li:
                    links = li.find_all('a')
                    if links:
                        name = links[0].get_text().strip()
                        film = links[1].get_text().strip() if len(links) > 1 else None
                        
                        if len(name) >= 2:
                            entry = {
                                'name': name,
                                'awards': {'nbr': 'Y'}
                            }
                            if film:
                                entry['film'] = film
                            results[current_category].append(entry)
                current_category = None  # Reset after processing
            
            current = current.next_sibling
    
    total = sum(len(v) for v in results.values())
    print(f"    NBR {year}: Found {total} entries (Films: {len(results['best-film'])}, Dir: {len(results['best-director'])}, Actor: {len(results['best-actor'])}, Actress: {len(results['best-actress'])})")
    return results


def scrape_venice(ceremony_num):
    """
    Scrape Venice Film Festival (Mostra di Venezia) from Italian Wikipedia.
    Extracts from 'Premi della selezione ufficiale' > 'Concorso' section:
    - Leone d'oro (best film)
    - Leone d'argento - regia (best director)
    - Coppa Volpi maschile (best actor)
    - Coppa Volpi femminile (best actress)
    """
    url = URL_TEMPLATES['venice'].format(ord=ceremony_num)
    print(f"  VENICE ({ceremony_num}th): {url}")
    
    soup = fetch_page(url)
    if not soup:
        return {}
    
    results = {
        'best-film': [],
        'best-director': [],
        'best-actor': [],
        'best-actress': []
    }
    
    # Find 'Premi della selezione ufficiale' section (h3 with id)
    premi_h3 = soup.find('h3', id='Premi_della_selezione_ufficiale')
    if not premi_h3:
        # Fallback: search by text
        for h3 in soup.find_all('h3'):
            if 'premi' in h3.get_text().lower() and 'selezione' in h3.get_text().lower():
                premi_h3 = h3
                break
    
    if not premi_h3:
        print(f"    Venice: 'Premi della selezione ufficiale' section not found")
        return results
    
    # Helper function to parse awards from li items
    def parse_venice_li(li, results):
        li_text = li.get_text().lower()
        
        # Leone d'oro (Best Film) - film title is in first <i> tag
        if "leone d'oro" in li_text and 'miglior film' in li_text:
            i_tag = li.find('i')
            if i_tag:
                film_name = i_tag.get_text().strip()
                if len(film_name) >= 2:
                    results['best-film'].append({
                        'name': film_name,
                        'awards': {'venice': 'Y'}
                    })
        
        # Leone d'argento - regia (Best Director) - exclude 'giuria' (Gran premio)
        elif "leone d'argento" in li_text and 'regia' in li_text and 'giuria' not in li_text:
            b_tag = li.find('b')
            i_tag = li.find('i')
            if b_tag:
                director_name = b_tag.get_text().strip()
                entry = {
                    'name': director_name,
                    'awards': {'venice': 'Y'}
                }
                if i_tag:
                    entry['film'] = i_tag.get_text().strip()
                results['best-director'].append(entry)
        
        # Coppa Volpi maschile (Best Actor)
        elif 'coppa volpi' in li_text and 'maschile' in li_text:
            b_tag = li.find('b')
            i_tag = li.find('i')
            if b_tag:
                actor_name = b_tag.get_text().strip()
                entry = {
                    'name': actor_name,
                    'awards': {'venice': 'Y'}
                }
                if i_tag:
                    entry['film'] = i_tag.get_text().strip()
                results['best-actor'].append(entry)
        
        # Coppa Volpi femminile (Best Actress)
        elif 'coppa volpi' in li_text and 'femminile' in li_text:
            b_tag = li.find('b')
            i_tag = li.find('i')
            if b_tag:
                actress_name = b_tag.get_text().strip()
                entry = {
                    'name': actress_name,
                    'awards': {'venice': 'Y'}
                }
                if i_tag:
                    entry['film'] = i_tag.get_text().strip()
                results['best-actress'].append(entry)
    
    # Navigate siblings - look for section elements OR direct UL (older format)
    container = premi_h3.parent
    current = container.next_sibling
    found_awards = False
    
    while current:
        if not hasattr(current, 'name'):
            current = current.next_sibling
            continue
        
        # Stop at next h2/h3 section
        if current.name == 'div' and 'mw-heading' in str(current.get('class', [])):
            break
        
        # NEW FORMAT: Look for section containing 'Concorso'
        if current.name == 'section':
            section_text = current.get_text().lower()
            if 'concorso' in section_text:
                for ul in current.find_all('ul'):
                    for li in ul.find_all('li', recursive=False):
                        parse_venice_li(li, results)
                found_awards = True
                break
        
        # OLD FORMAT: Direct UL after premi header (no section tags)
        elif current.name == 'ul' and not found_awards:
            for li in current.find_all('li', recursive=False):
                parse_venice_li(li, results)
            # Don't break - there might be multiple ULs
        
        current = current.next_sibling
    
    total = sum(len(v) for v in results.values())
    print(f"    Venice {ceremony_num}: Found {total} entries (Films: {len(results['best-film'])}, Dir: {len(results['best-director'])}, Actor: {len(results['best-actor'])}, Actress: {len(results['best-actress'])})")
    return results

def scrape_award(award_key, year):
    """Scrape a single award for a given year"""
    if year not in CEREMONY_MAP[award_key]:
        print(f"  No mapping for {award_key} {year}")
        return {}
    
    ceremony_num = CEREMONY_MAP[award_key][year]
    url = URL_TEMPLATES[award_key].format(ord=ordinal(ceremony_num))
    print(f"  {award_key.upper()} ({ordinal(ceremony_num)}): {url}")
    
    soup = fetch_page(url)
    if not soup:
        return {}
    
    tables = soup.find_all('table', class_='wikitable')
    if not tables:
        print(f"    No wikitable found!")
        return {}
    
    
    # Split tables based on format (Mixed pages support)
    div_tables = []
    legacy_tables = []
    
    for t in tables:
        # Check if table has a DIV header in TD (Modern format)
        # Verify it's actually a header (contains "best" or "award")
        has_header_div = False
        for td in t.find_all('td'):
            div = td.find('div')
            if div:
                text = div.get_text().lower()
                if 'best' in text or 'award' in text or 'outstanding' in text:
                    has_header_div = True
                    break
        
        if has_header_div:
            div_tables.append(t)
        else:
            legacy_tables.append(t)

    results = {
        'best-film': [],
        'best-director': [],
        'best-actor': [],
        'best-actress': []
    }

    # Process Legacy Tables (if any)
    if legacy_tables:
        legacy_results = {}
        if award_key == 'gg':
            legacy_results = scrape_gg_old_format(legacy_tables, award_key)
        elif award_key == 'sag':
            legacy_results = scrape_sag_old_format(legacy_tables, award_key)
            
        # Merge legacy results
        for k, v in legacy_results.items():
            if k in results:
                results[k].extend(v)

    # Process Modern/Div Tables (if any)
    # Iterate ONLY div_tables to catch TV categories or modern Film tables
    all_cells = [cell for t in div_tables for cell in t.find_all(['td', 'th'])]
    
    for cell in all_cells:
        header_div = cell.find('div')
        if not header_div:
            continue
            
        header_text = header_div.get_text().strip().lower()
        
        role = None
        key = None
        cat_type = None
        
        # Award-specific category detection
        if award_key == 'oscar':
            if 'best picture' in header_text:
                key = 'best-film'
                cat_type = 'film'
            elif 'directing' in header_text:
                key = 'best-director'
                cat_type = 'director'
            elif 'actor' in header_text and 'leading' in header_text:
                key = 'best-actor'
                cat_type = 'actor'
                role = 'Leading'
            elif 'actress' in header_text and 'leading' in header_text:
                key = 'best-actress'
                cat_type = 'actor'
                role = 'Leading'
            elif 'actor' in header_text and 'supporting' in header_text:
                key = 'best-actor'
                cat_type = 'actor'
                role = 'Supporting'
            elif 'actress' in header_text and 'supporting' in header_text:
                key = 'best-actress'
                cat_type = 'actor'
                role = 'Supporting'
                
        elif award_key == 'gg':
            if 'best motion picture' in header_text and ('drama' in header_text or 'musical' in header_text or 'comedy' in header_text):
                if 'animated' not in header_text and 'non-english' not in header_text:
                    key = 'best-film'
                    cat_type = 'film'
            elif 'director' in header_text:
                key = 'best-director'
                cat_type = 'director'
            elif 'actor' in header_text and 'motion picture' in header_text and 'television' not in header_text:
                key = 'best-actor'
                cat_type = 'actor'
                role = 'Supporting' if 'supporting' in header_text else 'Leading'
            elif 'actress' in header_text and 'motion picture' in header_text and 'television' not in header_text:
                key = 'best-actress'
                cat_type = 'actor'
                role = 'Supporting' if 'supporting' in header_text else 'Leading'
                
        elif award_key == 'bafta':
            if header_text == 'best film':
                key = 'best-film'
                cat_type = 'film'
            elif header_text == 'best director':
                key = 'best-director'
                cat_type = 'director'
            elif 'actor' in header_text and 'leading' in header_text:
                key = 'best-actor'
                cat_type = 'actor'
                role = 'Leading'
            elif 'actress' in header_text and 'leading' in header_text:
                key = 'best-actress'
                cat_type = 'actor'
                role = 'Leading'
            elif 'actor' in header_text and 'supporting' in header_text:
                key = 'best-actor'
                cat_type = 'actor'
                role = 'Supporting'
            elif 'actress' in header_text and 'supporting' in header_text:
                key = 'best-actress'
                cat_type = 'actor'
                role = 'Supporting'
                
        elif award_key == 'sag':
            if 'cast in a motion picture' in header_text:
                key = 'best-film'
                cat_type = 'film'
            elif 'female actor' in header_text and 'leading' in header_text:
                key = 'best-actress'
                cat_type = 'actor'
                role = 'Leading'
            elif 'female actor' in header_text and 'supporting' in header_text:
                key = 'best-actress'
                cat_type = 'actor'
                role = 'Supporting'
            elif 'male actor' in header_text and 'leading' in header_text:
                key = 'best-actor'
                cat_type = 'actor'
                role = 'Leading'
            elif 'male actor' in header_text and 'supporting' in header_text:
                key = 'best-actor'
                cat_type = 'actor'
                role = 'Supporting'
                
        elif award_key == 'critics':
            if header_text == 'best picture':
                key = 'best-film'
                cat_type = 'film'
            elif header_text == 'best director':
                key = 'best-director'
                cat_type = 'director'
            elif header_text == 'best actor':
                key = 'best-actor'
                cat_type = 'actor'
                role = 'Leading'
            elif header_text == 'best actress':
                key = 'best-actress'
                cat_type = 'actor'
                role = 'Leading'
            elif header_text == 'best supporting actor':
                key = 'best-actor'
                cat_type = 'actor'
                role = 'Supporting'
            elif header_text == 'best supporting actress':
                key = 'best-actress'
                cat_type = 'actor'
                role = 'Supporting'
        
        if not key:
            continue
        
        nominees = parse_nominees_from_cell(cell, cat_type, award_key)
        
        if role:
            for nom in nominees:
                nom['role'] = role
        
        # Mark with award key
        for nom in nominees:
            nom['awards'] = {award_key: 'Y' if nom['is_winner'] else 'X'}
            del nom['is_winner']
        
        if nominees:
            results[key].extend(nominees)
    
    return results


def get_tmdb_image(name, search_type='movie'):
    """Get TMDB image path"""
    url = f"{TMDB_BASE_URL}/search/{search_type}"
    params = {'api_key': TMDB_API_KEY, 'query': name}
    try:
        r = requests.get(url, params=params)
        d = r.json()
        if d.get('results'):
            first = d['results'][0]
            path_key = 'poster_path' if search_type == 'movie' else 'profile_path'
            return first.get(path_key), first.get('id')
    except:
        pass
    return None, None


def merge_results(all_results):
    """Merge results from multiple awards into unified data"""
    merged = {
        'best-film': [],
        'best-director': [],
        'best-actor': [],
        'best-actress': []
    }
    
    for award_key, results in all_results.items():
        for cat_id, entries in results.items():
            if cat_id not in merged:
                continue
                
            for entry in entries:
                # Find existing or create new (use name+film as unique key)
                entry_film = entry.get('film', '')
                existing = next((e for e in merged[cat_id] 
                                if e['name'] == entry['name'] and e.get('film', '') == entry_film), None)
                
                if existing:
                    # Merge awards (same person, same film)
                    if 'awards' not in existing:
                        existing['awards'] = {}
                    existing['awards'].update(entry.get('awards', {}))
                else:
                    merged[cat_id].append(entry.copy())
    
    # Sort each category by wins (Y) then nominations (X)
    def sort_key(entry):
        awards = entry.get('awards', {})
        wins = sum(1 for v in awards.values() if v == 'Y')
        nominations = sum(1 for v in awards.values() if v == 'X')
        # Negative for descending order (more wins/noms first)
        return (-wins, -nominations)
    
    for cat_id in merged:
        merged[cat_id].sort(key=sort_key)
    
    return merged


def enrich_with_tmdb(data):
    """Add TMDB images to all entries"""
    print("\nFetching TMDB images...")
    total = sum(len(entries) for entries in data.values())
    count = 0
    
    for cat_id, entries in data.items():
        is_person = cat_id != 'best-film'
        search_type = 'person' if is_person else 'movie'
        
        for entry in entries:
            count += 1
            if count % 10 == 0:
                print(f"  Progress: {count}/{total}")
            
            # Skip if already has image
            key = 'profilePath' if is_person else 'posterPath'
            if key in entry:
                continue
                
            img, tid = get_tmdb_image(entry['name'], search_type)
            if img:
                entry[key] = img
                entry['tmdbId'] = tid
            
            time.sleep(0.1)  # Rate limiting
    
    return data


def scrape_year(year, awards=None):
    """Scrape all awards for a given year"""
    if awards is None:
        awards = ['oscar', 'gg', 'bafta', 'sag', 'critics', 'afi', 'nbr', 'venice']
    
    print(f"\n{'='*60}")
    print(f"  SCRAPING SEASON {year-1}/{year}")
    print(f"{'='*60}")
    
    all_results = {}
    
    for award_key in awards:
        # AFI, NBR, and Venice use special scrapers
        if award_key == 'afi':
            afi_year = CEREMONY_MAP['afi'].get(year)
            if afi_year:
                result = scrape_afi(afi_year)
                if result:
                    all_results['afi'] = result
        elif award_key == 'nbr':
            nbr_year = CEREMONY_MAP['nbr'].get(year)
            if nbr_year:
                result = scrape_nbr(nbr_year)
                if result:
                    all_results['nbr'] = result
        elif award_key == 'venice':
            venice_num = CEREMONY_MAP['venice'].get(year)
            if venice_num:
                result = scrape_venice(venice_num)
                if result:
                    all_results['venice'] = result
        else:
            result = scrape_award(award_key, year)
            if result:
                all_results[award_key] = result
        time.sleep(0.5)  # Be nice to Wikipedia
    
    # Merge all results
    merged = merge_results(all_results)
    
    # Enrich with TMDB
    merged = enrich_with_tmdb(merged)
    
    # Print summary
    print(f"\n  Summary for {year-1}/{year}:")
    for cat_id, entries in merged.items():
        print(f"    {cat_id}: {len(entries)} entries")
    
    return merged


def save_year_data(year, data):
    """Save data to JSON file with both years in name (e.g., data_2024_2025.json)"""
    filename = f'data/data_{year-1}_{year}.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n  Saved to: {filename}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Scrape awards for a season year')
    parser.add_argument('year', type=int, nargs='?', default=2025,
                        help='Season year (e.g., 2025 for 2024/25 season)')
    parser.add_argument('--all', action='store_true',
                        help='Scrape all years from 2018 to 2025')
    args = parser.parse_args()
    
    if args.all:
        for year in range(2025, 2017, -1):  # 2025 down to 2018
            data = scrape_year(year)
            save_year_data(year, data)
    else:
        data = scrape_year(args.year)
        save_year_data(args.year, data)
    
    print("\n" + "="*60)
    print("  DONE!")
    print("="*60)
