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
    # 82nd in 2025 (Sept 2025 for 2024/2025 season films) -> NO, Sept 2025 is for 2025/2026 season!
    # Season 2025 (2024/25) -> Venice 81 (Sept 2024)
    'venice': {
        2026: 82, 2025: 81, 2024: 80, 2023: 79, 2022: 78, 2021: 77,
        2020: 76, 2019: 75, 2018: 74, 2017: 73, 2016: 72,
        2015: 71, 2014: 70, 2013: 69
    },
    # DGA: Directors Guild of America - year of films (like AFI/NBR)
    # Data scraped from dga.org via Selenium, stored in dga_awards.json
    'dga': {
        2026: 2025, 2025: 2024, 2024: 2023, 2023: 2022, 2022: 2021, 2021: 2020,
        2020: 2019, 2019: 2018, 2018: 2017, 2017: 2016, 2016: 2015,
        2015: 2014, 2014: 2013, 2013: 2012
    },
    # PGA: Producers Guild of America - ceremony number
    # 36th in 2025 for 2024/2025 season
    'pga': {
        2026: 37, 2025: 36, 2024: 35, 2023: 34, 2022: 33, 2021: 32,
        2020: 31, 2019: 30, 2018: 29, 2017: 28, 2016: 27,
        2015: 26, 2014: 25, 2013: 24
    },
    # LAFCA: Los Angeles Film Critics Association - year of films
    # 2024 season = 2024 LAFCA Awards (for films from 2024)
    'lafca': {
        2026: 2025, 2025: 2024, 2024: 2023, 2023: 2022, 2022: 2021, 2021: 2020,
        2020: 2019, 2019: 2018, 2018: 2017, 2017: 2016, 2016: 2015,
        2015: 2014, 2014: 2013, 2013: 2012
    },
    # WGA: Writers Guild of America - ceremony number
    # 77th in 2025 for 2024/2025 season
    'wga': {
        2026: 78, 2025: 77, 2024: 76, 2023: 75, 2022: 74, 2021: 73,
        2020: 72, 2019: 71, 2018: 70, 2017: 69, 2016: 68,
        2015: 67, 2014: 66, 2013: 65
    },
    # ADG: Art Directors Guild - year-based URL (like AFI/NBR)
    # 29th in 2024 for 2024/2025 season (Art_Directors_Guild_Awards_2024)
    'adg': {
        2026: 2025, 2025: 2024, 2024: 2023, 2023: 2022, 2022: 2021, 2021: 2020,
        2020: 2019, 2019: 2018, 2018: 2017, 2017: 2016, 2016: 2015,
        2015: 2014, 2014: 2013, 2013: 2012
    },
    # Gotham Independent Film Awards - year-based URL
    # Gotham 2025 (35th, held Dec 2025) covers films from 2025 → 2025/2026 season
    'gotham': {
        2026: 2025, 2025: 2024, 2024: 2023, 2023: 2022, 2022: 2021, 2021: 2020,
        2020: 2019, 2019: 2018, 2018: 2017, 2017: 2016, 2016: 2015,
        2015: 2014, 2014: 2013, 2013: 2012
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
    'venice': 'https://it.wikipedia.org/wiki/{ord}%C2%AA_Mostra_internazionale_d%27arte_cinematografica_di_Venezia',
    'pga': 'https://en.wikipedia.org/wiki/{ord}_Producers_Guild_of_America_Awards',
    'lafca': 'https://en.wikipedia.org/wiki/{year}_Los_Angeles_Film_Critics_Association_Awards',
    'wga': 'https://en.wikipedia.org/wiki/{ord}_Writers_Guild_of_America_Awards',
    'adg': 'https://en.wikipedia.org/wiki/Art_Directors_Guild_Awards_{year}',
    'gotham': 'https://en.wikipedia.org/wiki/Gotham_Independent_Film_Awards_{year}'
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
    seen_entries = set()  # Use (name, film) tuple to allow same person with different films
    
    skip_words = ['Academy Award', 'Golden Globe', 'BAFTA', 'Screen Actors Guild', 
                  'Critics', 'Outstanding', 'Best ']
    
    # First, check for winners in bold text BEFORE the list (common in Critics Choice)
    # Look for <b> tags that contain <a> links and are NOT inside <li>
    for bold in cell.find_all('b', recursive=True):
        # Skip if this bold is inside a list item (will be processed later)
        if bold.find_parent('li'):
            continue
        
        first_link = bold.find('a')
        if not first_link:
            continue
        
        link_title = first_link.get('title', '') or ''
        if any(w in link_title for w in skip_words):
            continue
        
        name = first_link.get_text().strip()
        if len(name) < 2:
            continue
        
        # Get film name for person categories
        film = None
        if category_type in ['director', 'actor']:
            # Look for links after the name within the same bold or nearby
            all_links = bold.find_all('a')
            for link in all_links[1:]:
                link_text = link.get_text().strip()
                link_title = link.get('title', '') or ''
                if any(w in link_title for w in skip_words):
                    continue
                if len(link_text) > 1:
                    film = link_text
                    break
            # If no film found in bold, check the parent element
            if not film:
                parent = bold.parent
                if parent:
                    for link in parent.find_all('a'):
                        if link == first_link or link in bold.find_all('a'):
                            continue
                        link_text = link.get_text().strip()
                        link_title = link.get('title', '') or ''
                        if any(w in link_title for w in skip_words):
                            continue
                        if len(link_text) > 1:
                            film = link_text
                            break
        # Check for dedup AFTER we have the film (use tuple key)
        entry_key = (name, film) if film else (name, None)
        if entry_key in seen_entries:
            continue
        seen_entries.add(entry_key)
        
        entry = {'name': name, 'is_winner': True}  # Bold outside list = winner
        if film:
            entry['film'] = film
        nominees.append(entry)
    
    # Then process list items as before
    lis = cell.find_all('li', recursive=True)
    
    for li in lis:
        first_link = li.find('a')
        if not first_link:
            continue
            
        link_title = first_link.get('title', '') or ''
        if any(w in link_title for w in skip_words):
            continue
            
        name = first_link.get_text().strip()
        
        if len(name) < 2:
            continue
        
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
        
        # Check for dedup AFTER we have the film (use tuple key)
        entry_key = (name, film) if film else (name, None)
        if entry_key in seen_entries:
            continue
        seen_entries.add(entry_key)
        
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
            # Also handles direct "Best Director | Best Screenplay" header rows (70th GG format)
            if len(ths) >= 2 and not tds:
                subcategories = [th.get_text().strip().lower() for th in ths]
                # Check if ANY of the combined headers is Animated/Foreign - if so, skip
                combined_header = ' '.join(subcategories)
                if 'animated' in combined_header or 'foreign' in combined_header or 'non-english' in combined_header:
                    current_main_cat = None
                    subcategories = []
                # Check if this is a direct "Best Director | Best Screenplay" row (70th GG format)
                elif any('best director' in s for s in subcategories):
                    # Set special category for director-only row
                    current_main_cat = 'director-row'
                    # Keep subcategories as-is for idx matching
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
                    elif current_main_cat == 'director-row':
                        # Direct "Best Director | Best Screenplay" header row (70th GG format)
                        if 'best director' in subcat:
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
    
    seen_entries = {'best-film': set(), 'best-actor': set(), 'best-actress': set()}  # Track (name, film) tuples
    
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
                                    if len(film_name) >= 2 and film_name not in seen_entries.get(key, set()):
                                        seen_entries[key].add(film_name)
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
                                    # Get film name first for deduplication
                                    all_links = b.find_all('a')
                                    film_name = all_links[1].get_text().strip() if len(all_links) >= 2 else ''
                                    entry_key = (name, film_name)
                                    
                                    if len(name) >= 2 and entry_key not in seen_entries.get(key, set()):
                                        if key in seen_entries:
                                            seen_entries[key].add(entry_key)
                                        
                                        entry = {
                                            'name': name,
                                            'awards': {award_key: 'Y'}  # Winner
                                        }
                                        
                                        if key in ['best-actor', 'best-actress']:
                                            if film_name:
                                                entry['film'] = film_name
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
                                if len(film_name) >= 2 and film_name not in seen_entries.get(key, set()):
                                    seen_entries[key].add(film_name)
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
                            # Get film name first for deduplication
                            all_links = li.find_all('a')
                            film_name = all_links[1].get_text().strip() if len(all_links) >= 2 else ''
                            entry_key = (name, film_name)
                            
                            if len(name) < 2 or entry_key in seen_entries.get(key, set()):
                                continue
                            
                            if key in seen_entries:
                                seen_entries[key].add(entry_key)
                            
                            # Check if winner (bold)
                            is_bold = li.find('b') is not None or first_link.find_parent('b') is not None
                            
                            entry = {
                                'name': name,
                                'awards': {award_key: 'Y' if is_bold else 'X'}
                            }
                            
                            # For actors, add film name and role
                            if key in ['best-actor', 'best-actress']:
                                if film_name:
                                    entry['film'] = film_name
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


def get_person_gender(name, tmdb_api_key='4399b8147e098e80be332f172d1fe490'):
    """
    Get gender of a person using TMDB API.
    Returns: 1 = Female, 2 = Male, 0 = Unknown
    """
    import requests
    try:
        url = f"https://api.themoviedb.org/3/search/person?api_key={tmdb_api_key}&query={requests.utils.quote(name)}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('results') and len(data['results']) > 0:
                return data['results'][0].get('gender', 0)
    except Exception as e:
        print(f"    Warning: Could not get gender for {name}: {e}")
    return 0  # Unknown


def scrape_lafca(year):
    """
    Scrape LAFCA (Los Angeles Film Critics Association) Awards for a specific year.
    
    Page structure:
    - Winners section with nested lists
    - Category header (Best Film:, Best Director:, etc.)
      - Winners in bold sub-list
        - Runner-ups in third-level list (treated as nominations)
    
    Performance categories are gender-neutral, so we detect gender via TMDB.
    """
    url = URL_TEMPLATES['lafca'].format(year=year)
    print(f"  LAFCA ({year}): {url}")
    
    soup = fetch_page(url)
    if not soup:
        return {}
    
    results = {
        'best-film': [],
        'best-director': [],
        'best-actor': [],
        'best-actress': []
    }
    
    seen = {
        'best-film': set(),
        'best-director': set(),
        'best-actor': set(),
        'best-actress': set()
    }
    
    # Global seen set to prevent duplicates across categories (e.g. Actor vs Actress)
    global_seen = set()  # Stores (name, film) tuples
    
    # Find Winners section - structure is <div><h2 id="Winners">Winners</h2></div>
    # The winners UL is NOT a direct sibling - it's further down in the DOM
    winners_h2 = soup.find('h2', id='Winners')
    if not winners_h2:
        # Fallback: search for h2 with Winners text
        for h2 in soup.find_all('h2'):
            if 'winners' in h2.get_text().lower():
                winners_h2 = h2
                break
    
    if not winners_h2:
        print(f"    LAFCA {year}: Could not find Winners section")
        return {}
    
    # Find the UL that contains "Best Film" or "Best Picture" (older format) - use find_next from the h2
    main_ul = None
    for ul in winners_h2.find_all_next('ul'):
        ul_text = ul.get_text().lower()
        if 'best film' in ul_text or 'best picture' in ul_text:
            main_ul = ul
            break
    
    if not main_ul:
        print(f"    LAFCA {year}: Could not find winners list")
        return {}
    
    # Categories to track
    category_map = {
        'best film': 'best-film',
        'best director': 'best-director',
        # Modern gender-neutral categories (2017+)
        'best lead performance': 'lead-performance',
        'best supporting performance': 'supporting-performance',
        'best leading performance': 'lead-performance',
        # Older year formats (pre-2017):
        'best picture': 'best-film',  # Alternative name for Best Film
        'best actor': 'best-actor',   # Direct mapping for older years
        'best actress': 'best-actress',  # Direct mapping for older years
        'best supporting actor': 'best-supporting-actor',  # Need special handling
        'best supporting actress': 'best-supporting-actress',  # Need special handling
    }
    
    # Process each top-level list item (categories)
    for li in main_ul.find_all('li', recursive=False):
        li_text = li.get_text().lower()
        
        # Determine category
        current_category = None
        is_performance = False
        performance_type = None
        
        for key, cat in category_map.items():
            # Use startswith with colon to prevent partial matches 
            # (e.g., "best actor" matching in "best lead performance")
            if li_text.startswith(key + ':') or li_text.startswith(key + ' '):
                if cat in ['lead-performance', 'supporting-performance']:
                    is_performance = True
                    performance_type = cat
                elif cat in ['best-supporting-actor', 'best-supporting-actress']:
                    # Map supporting actor/actress to main actor/actress categories
                    current_category = 'best-actor' if cat == 'best-supporting-actor' else 'best-actress'
                else:
                    current_category = cat
                break
        
        if not current_category and not is_performance:
            continue
        
        # Find winners and runner-ups in sub-lists
        sub_lists = li.find_all('ul', recursive=False)
        
        # Track first item to handle pages where winners aren't bolded (2012/2013)
        first_item_in_category = True
        
        for sub_ul in sub_lists:
            # Use recursive=True to find nested runner-ups (e.g., UL > LI > UL > LI)
            for sub_li in sub_ul.find_all('li'):
                # Check for "runner-up" or "runner up" (with/without hyphen) at the start of the text
                li_text_lower = sub_li.get_text().lower().strip()
                is_runner_up = li_text_lower.startswith('runner-up') or li_text_lower.startswith('runner up')
                
                # Find the first link (name)
                link = sub_li.find('a')
                if not link:
                    continue
                
                name = link.get_text().strip()
                if len(name) < 2:
                    continue
                
                # Get film (second link or from text after dash)
                film = None
                all_links = sub_li.find_all('a')
                if len(all_links) >= 2:
                    # For directors and actors, second link is usually the film
                    film = all_links[1].get_text().strip()
                
                # Determine if winner: the link itself has a bold parent (not just any b in the li)
                # Structure: <i><b><a>...</a></b></i> for winners, plain <a> for runner-ups
                is_bold_link = (link.parent and link.parent.name in ['b', 'strong']) or \
                               (link.parent and link.parent.parent and link.parent.parent.name in ['b', 'strong'])
                
                # Winner logic: bold OR first item (if not runner-up) for pages without bold
                if is_bold_link and not is_runner_up:
                    is_winner = True
                elif first_item_in_category and not is_runner_up:
                    # Fallback: treat first non-runner-up item as winner (for 2012/2013 style pages)
                    is_winner = True
                else:
                    is_winner = False
                
                first_item_in_category = False  # No longer first item
                
                if is_performance:
                    # Detect gender via TMDB
                    gender = get_person_gender(name)
                    
                    if gender == 1:  # Female
                        target_cat = 'best-actress'
                    elif gender == 2:  # Male
                        target_cat = 'best-actor'
                    else:
                        # Unknown (0 or 3) - try to guess from first name
                        first_name = name.split()[0].lower() if name.split() else ''
                        # Common female first names
                        female_names = {'lily', 'emma', 'sandra', 'rachel', 'davine', "da'vine", 
                                       'amanda', 'viola', 'carey', 'youn', 'jennifer', 'jessica',
                                       'meryl', 'nicole', 'cate', 'margot', 'anne', 'julia',
                                       'natalie', 'penelope', 'penélope', 'michelle', 'kate', 'helen'}
                        if first_name in female_names:
                            target_cat = 'best-actress'
                        else:
                            # Default to actor for truly unknown
                            print(f"    Warning: Unknown gender for {name}, defaulting to actor")
                            target_cat = 'best-actor'
                    
                    # Add role info
                    role = 'Leading' if performance_type == 'lead-performance' else 'Supporting'
                    
                    unique_key = (name, film or '')
                    
                    # Check global seen to prevent duplicates (blocking by name to avoid film mismatch duplicates)
                    # We check if name is already processed for this award
                    if name in global_seen:
                        continue
                        
                    if unique_key not in seen[target_cat]:
                        seen[target_cat].add(unique_key)
                        global_seen.add(name)
                        
                        entry = {
                            'name': name,
                            'awards': {'lafca': 'Y' if is_winner else 'X'},
                            'role': role
                        }
                        if film:
                            entry['film'] = film
                        results[target_cat].append(entry)
                else:
                    # Film or Director category
                    unique_key = (name, film or '')
                    
                    if unique_key not in seen[current_category]:
                        seen[current_category].add(unique_key)
                        # No need to add to global_seen for film/director as they are distinct categories
                        
                        entry = {
                            'name': name, 
                            'awards': {'lafca': 'Y' if is_winner else 'X'}
                        }
                        if film:
                            entry['film'] = film
                        results[current_category].append(entry)
                        
    # Post-processing: Ensure no overlap between actor and actress (fix for gender detection edge cases)
    # If a person is in best-actress, remove them from best-actor (as actress detection is more specific via name fallback)
    actress_names = {entry['name'] for entry in results.get('best-actress', [])}
    if results.get('best-actor'):
        results['best-actor'] = [e for e in results['best-actor'] if e['name'] not in actress_names]
    
    total = sum(len(v) for v in results.values())
    print(f"    LAFCA {year}: Found {total} entries (Films: {len(results['best-film'])}, Dir: {len(results['best-director'])}, Actor: {len(results['best-actor'])}, Actress: {len(results['best-actress'])})")
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
    def parse_venice_li(li, results, forced_category=None):
        nested_ul = li.find('ul')
        li_text = li.get_text().lower()
        
        # If li has nested ul, process children
        if nested_ul:
            # Determine if parent defines a category
            parent_category = None
            
            # Check for ambiguity (both maschile and femminile)
            is_male_volpi = 'coppa volpi' in li_text and 'maschile' in li_text
            is_female_volpi = 'coppa volpi' in li_text and 'femminile' in li_text
            
            if is_male_volpi and not is_female_volpi:
                parent_category = 'best-actor'
            elif is_female_volpi and not is_male_volpi:
                parent_category = 'best-actress'
            elif "leone d'oro" in li_text:
                parent_category = 'best-film'
            elif "leone d'argento" in li_text and 'regia' in li_text:
                parent_category = 'best-director'
            
            # Recurse into children
            # If we found a category in parent, force it on children
            # Otherwise, children must self-identify
            nested_lis = nested_ul.find_all('li', recursive=False)
            
            for nested_li in nested_lis:
                parse_venice_li(nested_li, results, forced_category=parent_category)
            
            return
        
        # Determine category for this LI
        category = forced_category
        
        if not category:
            if "leone d'oro" in li_text and 'miglior film' in li_text:
                category = 'best-film'
            elif "leone d'argento" in li_text and 'regia' in li_text and 'giuria' not in li_text:
                category = 'best-director'
            elif 'coppa volpi' in li_text and 'maschile' in li_text:
                category = 'best-actor'
            elif 'coppa volpi' in li_text and 'femminile' in li_text:
                category = 'best-actress'
        
        if not category:
            return

        # Extract winners
        # Handle shared wins (multiple <b> tags)
        b_tags = li.find_all('b')
        i_tags = li.find_all('i')
        
        if not b_tags and category == 'best-film':
             # Sometimes film is just in <i> without bold in older years? 
             # Or sometimes <i> is the film.
             pass

        if category == 'best-film':
            # Usually only one film winner
            # Prefer <i> tag content
            film_name = None
            if i_tags:
                film_name = i_tags[0].get_text().strip()
            elif b_tags:
                film_name = b_tags[0].get_text().strip()
            
            if film_name and len(film_name) >= 2:
                results['best-film'].append({
                    'name': film_name,
                    'awards': {'venice': 'Y'}
                })
                
        elif category in ['best-director', 'best-actor', 'best-actress']:
            # Handle possible shared winners
            # Case 1: Multiple names, one film (e.g. "Name1 e Name2 per il film Film")
            # Case 2: Multiple names, multiple films (e.g. "Name1 (Film1) e Name2 (Film2)")
            
            if not b_tags:
                return

            if len(b_tags) == 1:
                # Simple case
                name = b_tags[0].get_text().strip()
                entry = {'name': name, 'awards': {'venice': 'Y'}}
                if i_tags:
                    entry['film'] = i_tags[0].get_text().strip()
                results[category].append(entry)
            else:
                # Multiple winners
                if len(i_tags) == 1:
                    # Shared film
                    shared_film = i_tags[0].get_text().strip()
                    for b in b_tags:
                        name = b.get_text().strip()
                        results[category].append({
                            'name': name,
                            'awards': {'venice': 'Y'},
                            'film': shared_film
                        })
                elif len(i_tags) == len(b_tags):
                     # One film per person
                     for b, i in zip(b_tags, i_tags):
                        results[category].append({
                            'name': b.get_text().strip(),
                            'awards': {'venice': 'Y'},
                            'film': i.get_text().strip()
                        })
                else:
                    # Mismatch or unknown structure - just add names
                    # Try to map if possible, or leave film empty
                    for idx, b in enumerate(b_tags):
                         entry = {'name': b.get_text().strip(), 'awards': {'venice': 'Y'}}
                         # Heuristic: if we have more names than films, maybe first film applies to all?
                         # Or just ignore film to avoid wrong attribution
                         if i_tags and idx < len(i_tags):
                             entry['film'] = i_tags[idx].get_text().strip()
                         elif i_tags:
                             entry['film'] = i_tags[0].get_text().strip() # Fallback
                         results[category].append(entry)
    
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
                # Only get direct ul children to avoid duplicates from nested ul
                for ul in current.find_all('ul', recursive=False):
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


def scrape_pga(ceremony_num):
    """
    Scrape PGA (Producers Guild of America) Awards.
    Only extracts 'Outstanding Producer of Theatrical Motion Pictures' category.
    Ignores Documentary and Animated categories.
    """
    url = URL_TEMPLATES['pga'].format(ord=ordinal(ceremony_num))
    print(f"  PGA ({ordinal(ceremony_num)}): {url}")
    
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
    
    # Find the "Darryl F. Zanuck Award" section
    # This is the main theatrical film producer award
    zanuck_link = soup.find('a', string=lambda t: t and 'Darryl F. Zanuck Award' in t)
    
    if not zanuck_link:
        # Fallback: search for text containing "Outstanding Producer of Theatrical"
        for th in soup.find_all(['th', 'td']):
            if 'Outstanding Producer of Theatrical Motion Pictures' in th.get_text():
                zanuck_link = th
                break
    
    if not zanuck_link:
        print(f"    PGA: Could not find Zanuck Award section")
        return results
    
    # Navigate to find the UL with nominees
    # Structure: The link is inside a header, the UL follows
    current = zanuck_link
    ul = None
    
    # Go up to find parent container, then find next UL
    for _ in range(10):
        if current is None:
            break
        
        # Check siblings for UL
        sibling = current.next_sibling
        while sibling:
            if hasattr(sibling, 'name') and sibling.name == 'ul':
                ul = sibling
                break
            sibling = sibling.next_sibling
        
        if ul:
            break
        
        # Check if current element contains UL
        if hasattr(current, 'find'):
            ul = current.find('ul')
            if ul:
                break
        
        current = current.parent
    
    if not ul:
        print(f"    PGA: Could not find nominee list")
        return results
    
    # Parse the list
    # Structure: Winner is in bold <b>, inside <li> with nested <ul> for nominees
    # First check top-level li items
    for li in ul.find_all('li', recursive=False):
        # Get film name from <i> tag
        italic = li.find('i')
        if not italic:
            continue
        
        film_name = italic.get_text().strip()
        
        # Check if this is a category we should skip (Documentary, Animated)
        li_text = li.get_text().lower()
        if 'documentary' in li_text or 'animated' in li_text:
            continue
        
        if film_name and film_name not in seen_films:
            # Check if winner (bold)
            is_winner = li.find('b') is not None
            
            seen_films.add(film_name)
            results['best-film'].append({
                'name': film_name,
                'awards': {'pga': 'Y' if is_winner else 'X'}
            })
        
        # Check for nested <ul> with more nominees
        nested_ul = li.find('ul')
        if nested_ul:
            for nested_li in nested_ul.find_all('li', recursive=False):
                nested_italic = nested_li.find('i')
                if nested_italic:
                    nested_film = nested_italic.get_text().strip()
                    if nested_film and nested_film not in seen_films:
                        seen_films.add(nested_film)
                        results['best-film'].append({
                            'name': nested_film,
                            'awards': {'pga': 'X'}  # Nested ones are nominees
                        })
    
    print(f"    PGA {ordinal(ceremony_num)}: Found {len(results['best-film'])} films")
    return results


def scrape_wga(ceremony_num):
    """
    Scrape WGA (Writers Guild of America) Awards.
    Extracts 'Best Original Screenplay' and 'Best Adapted Screenplay' categories.
    Only extracts film names (not writers). Adds 'screenplay_type' field for original/adapted distinction.
    
    Handles two page formats:
    1. Modern (75th+): Header in <td> with <div>, winner in bold <li>
    2. Legacy (older): Header in <th colspan="2">, winner in <p><b><i>, nominees in <ul><li><i>
    """
    url = URL_TEMPLATES['wga'].format(ord=ordinal(ceremony_num))
    print(f"  WGA ({ordinal(ceremony_num)}): {url}")
    
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
    
    for screenplay_type, header_text in [('original', 'Best Original Screenplay'), 
                                          ('adapted', 'Best Adapted Screenplay')]:
        # Find the anchor link with the award name
        header_link = None
        for a in soup.find_all('a'):
            if header_text in a.get_text():
                header_link = a
                break
        
        if not header_link:
            print(f"    WGA: Could not find {header_text} section")
            continue
        
        # Try MODERN format first: parent is TD
        td = header_link.find_parent('td')
        if td:
            # Modern format: process all li items in this TD
            found_in_td = False
            for li in td.find_all('li'):
                italic = li.find('i')
                if not italic:
                    continue
                
                film_name = italic.get_text().strip()
                
                if film_name and film_name not in seen_films:
                    parent_b = italic.find_parent('b')
                    is_winner = parent_b is not None
                    
                    seen_films.add(film_name)
                    results['best-film'].append({
                        'name': film_name,
                        'awards': {'wga': 'Y' if is_winner else 'X'},
                        'screenplay_type': screenplay_type
                    })
                    found_in_td = True
            if found_in_td:
                continue  # Only skip to next category if we actually found films
        
        # Try LEGACY format: parent is TH, data in next row's TD
        th = header_link.find_parent('th')
        if th:
            # Navigate to next row
            tr = th.find_parent('tr')
            if not tr:
                continue
            
            next_row = tr.find_next_sibling('tr')
            if not next_row:
                continue
            
            # Get the TD with nominees
            data_td = next_row.find('td')
            if not data_td:
                continue
            
            # Check for two formats:
            # Format A: Winner in <p><b><i>, nominees in sibling <ul>
            # Format B: Winner is top-level <li><b><i>, nominees in nested <ul> inside winner's <li>
            
            # Try Format A first: Winner in <p><b><i>
            p_winner = data_td.find('p')
            if p_winner:
                bold = p_winner.find('b')
                if bold:
                    italic = bold.find('i')
                    if italic:
                        film_name = italic.get_text().strip()
                        if film_name and film_name not in seen_films:
                            seen_films.add(film_name)
                            results['best-film'].append({
                                'name': film_name,
                                'awards': {'wga': 'Y'},
                                'screenplay_type': screenplay_type
                            })
            
            # Nominees in sibling <ul><li><i>
            ul = data_td.find('ul')
            if ul:
                # Check if this is Format B: first li is winner with nested ul
                first_li = ul.find('li', recursive=False)
                if first_li:
                    # Check for winner in first li (bold italic)
                    first_b = first_li.find('b', recursive=False)
                    if first_b:
                        first_i = first_b.find('i')
                        if first_i:
                            winner_name = first_i.get_text().strip()
                            if winner_name and winner_name not in seen_films:
                                seen_films.add(winner_name)
                                results['best-film'].append({
                                    'name': winner_name,
                                    'awards': {'wga': 'Y'},
                                    'screenplay_type': screenplay_type
                                })
                    
                    # Check for nested ul (nominees inside winner's li)
                    nested_ul = first_li.find('ul')
                    if nested_ul:
                        for nested_li in nested_ul.find_all('li', recursive=False):
                            italic = nested_li.find('i')
                            if not italic:
                                continue
                            
                            film_name = italic.get_text().strip()
                            
                            if film_name and film_name not in seen_films:
                                seen_films.add(film_name)
                                results['best-film'].append({
                                    'name': film_name,
                                    'awards': {'wga': 'X'},
                                    'screenplay_type': screenplay_type
                                })
                
                # Also check sibling li items (for Format A)
                for li in ul.find_all('li', recursive=False):
                    italic = li.find('i')
                    if not italic:
                        continue
                    
                    film_name = italic.get_text().strip()
                    
                    if film_name and film_name not in seen_films:
                        seen_films.add(film_name)
                        results['best-film'].append({
                            'name': film_name,
                            'awards': {'wga': 'X'},
                            'screenplay_type': screenplay_type
                        })
            continue
        
        # Try VERY OLD format (65th-66th): h4 with id="Original"/"Adapted"
        # Header is <h4 id="Original"> or <h4 id="Adapted">
        h4_id = 'Original' if screenplay_type == 'original' else 'Adapted'
        h4 = soup.find('h4', id=h4_id)
        if not h4:
            # Try finding by span inside h4
            span = soup.find('span', id=h4_id)
            if span:
                h4 = span.find_parent('h4')
        
        if h4:
            # Find content after h4: winner in <p>, nominees in <ul>
            # h4 is often wrapped in a <div class="mw-heading">, so navigate from parent
            start_element = h4.parent if h4.parent and h4.parent.name == 'div' else h4
            current = start_element.next_sibling
            while current:
                if hasattr(current, 'name'):
                    # Winner in <p> with <i> (may be <i><b> or <b><i> or just <i>)
                    if current.name == 'p':
                        # Try to find first <i> tag in paragraph
                        italic = current.find('i')
                        if italic:
                            film_name = italic.get_text().strip()
                            if film_name and film_name not in seen_films:
                                seen_films.add(film_name)
                                results['best-film'].append({
                                    'name': film_name,
                                    'awards': {'wga': 'Y'},
                                    'screenplay_type': screenplay_type
                                })
                    
                    # Nominees in <ul><li><i>
                    if current.name == 'ul':
                        for li in current.find_all('li', recursive=False):
                            italic = li.find('i')
                            if not italic:
                                continue
                            
                            film_name = italic.get_text().strip()
                            
                            if film_name and film_name not in seen_films:
                                seen_films.add(film_name)
                                results['best-film'].append({
                                    'name': film_name,
                                    'awards': {'wga': 'X'},
                                    'screenplay_type': screenplay_type
                                })
                        break  # Found the ul, stop
                    
                    # Stop if we hit next h3/h4 (new section)
                    if current.name in ['h3', 'h4']:
                        break
                
                current = current.next_sibling
    
    print(f"    WGA {ordinal(ceremony_num)}: Found {len(results['best-film'])} films")
    return results


def scrape_adg(year):
    """
    Scrape Art Directors Guild Excellence in Production Design Awards.
    Extracts Film category nominees (Contemporary, Period, Fantasy, Animated).
    """
    import re
    
    if year not in CEREMONY_MAP['adg']:
        print(f"  No mapping for ADG {year}")
        return {}
    
    adg_year = CEREMONY_MAP['adg'][year]
    url = URL_TEMPLATES['adg'].format(year=adg_year)
    print(f"  ADG ({adg_year}): {url}")
    
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
    
    # Find all wikitables
    all_tables = soup.find_all('table', class_='wikitable')
    
    # We need to find which tables are in the "Film" section (before "Television")
    # Strategy: Look at preceding h2/h3 headers to identify Film tables
    film_tables = []
    
    for table in all_tables:
        # Walk backwards from table to find the section header
        prev = table.find_previous(['h2', 'h3'])
        if prev:
            header_text = prev.get_text().lower()
            # Include if in Film section, exclude if in Television section
            if 'film' in header_text and 'television' not in header_text:
                film_tables.append(table)
            elif 'television' not in header_text and 'tv' not in header_text and 'series' not in header_text:
                # Check if we're still before Television section
                # by looking at all headers before this table
                in_film_section = False
                for h in table.find_all_previous(['h2', 'h3']):
                    h_text = h.get_text().lower()
                    if 'film' in h_text:
                        in_film_section = True
                        break
                    if 'television' in h_text or 'tv' in h_text:
                        break
                if in_film_section:
                    film_tables.append(table)
        
        # Stop if we've moved into Television section
        next_h = table.find_next(['h2', 'h3'])
        if next_h:
            next_text = next_h.get_text().lower()
            # If we're about to hit Television, stop collecting tables
            if 'television' in next_text or 'tv' in next_text or 'series' in next_text:
                if table not in film_tables:
                    break
    
    # Fallback: if no Film tables found, take first table only
    if not film_tables and all_tables:
        film_tables = all_tables[:1]
    
    if not film_tables:
        print(f"    ADG: No Film tables found, trying legacy list format...")
    
    # Parse Film tables
    for table in film_tables:
        rows = table.find_all('tr')
        
        # Track current category headers (updated when we hit a TH row)
        current_headers = []
        
        for row in rows:
            ths = row.find_all('th')
            tds = row.find_all('td')
            
            # If row has TH elements, update current headers
            if ths:
                current_headers = [th.get_text().lower() for th in ths]
                continue  # Don't process TH rows for films
            
            # Process TD cells using current headers
            for cell_idx, cell in enumerate(tds):
                # Skip Animated Film category (user requested only Contemporary, Period, Fantasy)
                if cell_idx < len(current_headers):
                    category = current_headers[cell_idx]
                    if 'animated' in category:
                        continue
                
                # ADG 2020+ format: Winner in <p> tag, nominees in <ul>
                # First check for winner in p tag (outside ul)
                for p_tag in cell.find_all('p', recursive=False):
                    italic = p_tag.find('i')
                    if italic:
                        film_name = italic.get_text().strip()
                        film_name = re.sub(r'\s*\[.*?\]', '', film_name).strip()
                        
                        if film_name and film_name not in seen_films:
                            seen_films.add(film_name)
                            results['best-film'].append({
                                'name': film_name,
                                'awards': {'adg': 'Y'}  # Winner (in p tag)
                            })
                
                # Then get nominees from ul
                top_ul = cell.find('ul', recursive=False)
                if top_ul:
                    # Get all li items as nominees (since winner is already in p)
                    for li in top_ul.find_all('li', recursive=False):
                        italic = li.find('i')
                        if italic:
                            film_name = italic.get_text().strip()
                            film_name = re.sub(r'\s*\[.*?\]', '', film_name).strip()
                            
                            if film_name and film_name not in seen_films:
                                seen_films.add(film_name)
                                # Check for bold indicating winner
                                is_bold = li.find('b') or li.find('strong') or italic.find_parent('b')
                                results['best-film'].append({
                                    'name': film_name,
                                    'awards': {'adg': 'Y' if is_bold else 'X'}
                                })
                        
                        # Check for nested ul (additional nominees)
                        nested_ul = li.find('ul')
                        if nested_ul:
                            for nested_li in nested_ul.find_all('li', recursive=False):
                                nested_italic = nested_li.find('i')
                                if nested_italic:
                                    film_name = nested_italic.get_text().strip()
                                    film_name = re.sub(r'\s*\[.*?\]', '', film_name).strip()
                                    
                                    if film_name and film_name not in seen_films:
                                        seen_films.add(film_name)
                                        results['best-film'].append({
                                            'name': film_name,
                                            'awards': {'adg': 'X'}
                                        })
    
    # ==== LEGACY LIST FORMAT (2013-2019) ====
    # If no tables found or tables yield no results, try parsing bulleted lists
    # These pages use p tags for category labels and ul tags for film lists
    if not film_tables or len(results['best-film']) == 0:
        # Find the Film section header (h2 or h3 with 'Film' in text)
        film_header = None
        for h in soup.find_all(['h2', 'h3']):
            h_text = h.get_text().lower()
            if 'film' in h_text and 'television' not in h_text and 'tv' not in h_text:
                film_header = h
                break
        
        if film_header:
            # Use find_all_next to traverse DOM across div boundaries
            # (h3 is inside div.mw-heading so siblings don't work)
            current_category = None
            
            for element in film_header.find_all_next(['h2', 'h3', 'p', 'ul']):
                tag_name = element.name
                element_text = element.get_text().lower()
                
                # Stop at next major section
                if tag_name == 'h2':
                    break
                if tag_name == 'h3':
                    if 'television' in element_text or 'tv' in element_text:
                        break
                    # Skip this header but continue
                    continue
                
                # Check for category labels in p tags (e.g., "Period Film:", "Fantasy Film:")
                if tag_name == 'p':
                    if any(cat in element_text for cat in ['period', 'contemporary', 'fantasy', 'animated']):
                        current_category = element_text
                    continue
                
                # Process bulleted lists (ul) - these contain the actual film nominees
                if tag_name == 'ul':
                    # Skip animated category (user requested)
                    # Keep current_category as animated so all ul in this section are skipped
                    if current_category and 'animated' in current_category:
                        continue
                    
                    lis = element.find_all('li', recursive=False)
                    for idx, li in enumerate(lis):
                        italic = li.find('i')
                        if italic:
                            film_name = italic.get_text().strip()
                            film_name = re.sub(r'\s*\[.*?\]', '', film_name).strip()
                            
                            if film_name and film_name not in seen_films:
                                seen_films.add(film_name)
                                # First item in each category list is typically the winner
                                is_winner = idx == 0
                                results['best-film'].append({
                                    'name': film_name,
                                    'awards': {'adg': 'Y' if is_winner else 'X'}
                                })
                        
                        # Also check nested ul for additional nominees
                        nested_ul = li.find('ul')
                        if nested_ul:
                            for nested_li in nested_ul.find_all('li', recursive=False):
                                nested_italic = nested_li.find('i')
                                if nested_italic:
                                    film_name = nested_italic.get_text().strip()
                                    film_name = re.sub(r'\s*\[.*?\]', '', film_name).strip()
                                    
                                    if film_name and film_name not in seen_films:
                                        seen_films.add(film_name)
                                        results['best-film'].append({
                                            'name': film_name,
                                            'awards': {'adg': 'X'}  # Nested = nominee
                                        })
    
    print(f"    ADG {adg_year}: Found {len(results['best-film'])} films")
    return results


def scrape_gotham(year):
    """
    Scrape Gotham Independent Film Awards for a specific year.
    
    Page structure: Wikitable with cells per category.
    Each cell has:
    - <div> with category header (e.g., "Best Feature")
    - <ul> with 1 li = winner info
    - Nested <ul> inside that li with other nominees
    
    Categories:
    - Best Feature (10 nominees)
    - Best Director (5 nominees)  
    - Outstanding Lead Performance (10 nominees, gender-neutral)
    - Outstanding Supporting Performance (10 nominees, gender-neutral)
    
    Performance categories are gender-neutral, so we detect gender via TMDB.
    """
    import re
    
    gotham_year = CEREMONY_MAP['gotham'][year]
    url = URL_TEMPLATES['gotham'].format(year=gotham_year)
    
    print(f"  GOTHAM ({gotham_year}): {url}")
    
    soup = fetch_page(url)
    if not soup:
        return {}
    
    return scrape_gotham_v2_logic(soup)
    
    results = {
        'best-film': [],
        'best-director': [],
        'best-actor': [],
        'best-actress': []
    }
    
    seen = {'film': set(), 'director': set(), 'actor': set(), 'actress': set()}
    
    # Find the main wikitable (first one with nominees)
    tables = soup.find_all('table', class_='wikitable')
    if not tables:
        print("    No wikitable found")
        return results
    
    main_table = tables[0]
    
    # Process each cell
    cells = main_table.find_all(['th', 'td'])
    
    for cell in cells:
        # Get category from div header or first text
        div = cell.find('div')
        if not div:
            continue
            
        category_text = div.get_text().strip().lower()
        
        # Determine which category this is
        category_type = None
        if 'best feature' in category_text:
            category_type = 'best-film'
        elif 'best director' in category_text:
            category_type = 'best-director'
        elif 'lead performance' in category_text or 'outstanding lead' in category_text:
            category_type = 'lead-performance'
        elif 'supporting performance' in category_text or 'outstanding supporting' in category_text:
            category_type = 'supporting-performance'
        else:
            continue  # Skip other categories
        
        # Find all ul lists in this cell
        all_uls = cell.find_all('ul')
        if not all_uls:
            continue
        
        # First ul contains winner (usually 1 item)
        # That li may have nested ul with nominees
        first_ul = all_uls[0]
        top_li = first_ul.find('li', recursive=False)
        
        if top_li:
            # Extract winner info
            winner_text = ""
            # Get text before any nested ul
            for item in top_li.children:
                if hasattr(item, 'name') and item.name == 'ul':
                    break
                if hasattr(item, 'get_text'):
                    winner_text += item.get_text()
                else:
                    winner_text += str(item)
            
            winner_text = winner_text.strip()
            
            # Parse winner_text (format: "Film Name – Person, Person, producers")
            # or for directors: "Person Name – Film Name"
            if winner_text:
                # Clean up
                winner_text = re.sub(r'\[.*?\]', '', winner_text).strip()
                
                # Split on separator
                parts = re.split(r'\s*[–—-]\s*', winner_text, 1)
                
                if category_type == 'best-film':
                    film_name = parts[0].strip()
                    if film_name and film_name not in seen['film']:
                        seen['film'].add(film_name)
                        results['best-film'].append({
                            'name': film_name,
                            'awards': {'gotham': 'Y'}
                        })
                        
                elif category_type == 'best-director':
                    person_name = parts[0].strip()
                    film_name = parts[1].strip() if len(parts) > 1 else None
                    if person_name and person_name not in seen['director']:
                        seen['director'].add(person_name)
                        entry = {
                            'name': person_name,
                            'awards': {'gotham': 'Y'}
                        }
                        if film_name:
                            entry['film'] = film_name
                        results['best-director'].append(entry)
                        
                elif category_type in ['lead-performance', 'supporting-performance']:
                    person_name = parts[0].strip()
                    film_name = parts[1].strip() if len(parts) > 1 else None
                    if person_name:
                        gender = get_person_gender(person_name)
                        cat = 'actress' if gender == 1 else 'actor'
                        if person_name not in seen[cat]:
                            seen[cat].add(person_name)
                            entry = {
                                'name': person_name,
                                'awards': {'gotham': 'Y'}
                            }
                            if film_name:
                                entry['film'] = film_name
                            results[f'best-{cat}'].append(entry)
            
            # Now get nominees from nested ul
            nested_ul = top_li.find('ul')
            if nested_ul:
                for li in nested_ul.find_all('li', recursive=False):
                    nominee_text = li.get_text().strip()
                    nominee_text = re.sub(r'\[.*?\]', '', nominee_text).strip()
                    
                    # Split on separator
                    parts = re.split(r'\s*[–—-]\s*', nominee_text, 1)
                    
                    if category_type == 'best-film':
                        film_name = parts[0].strip()
                        if film_name and film_name not in seen['film']:
                            seen['film'].add(film_name)
                            results['best-film'].append({
                                'name': film_name,
                                'awards': {'gotham': 'X'}
                            })
                            
                    elif category_type == 'best-director':
                        person_name = parts[0].strip()
                        film_name = parts[1].strip() if len(parts) > 1 else None
                        if person_name and person_name not in seen['director']:
                            seen['director'].add(person_name)
                            entry = {
                                'name': person_name,
                                'awards': {'gotham': 'X'}
                            }
                            if film_name:
                                entry['film'] = film_name
                            results['best-director'].append(entry)
                            
                    elif category_type in ['lead-performance', 'supporting-performance']:
                        person_name = parts[0].strip()
                        film_name = parts[1].strip() if len(parts) > 1 else None
                        if person_name:
                            gender = get_person_gender(person_name)
                            cat = 'actress' if gender == 1 else 'actor'
                            if person_name not in seen[cat]:
                                seen[cat].add(person_name)
                                entry = {
                                    'name': person_name,
                                    'awards': {'gotham': 'X'}
                                }
                                if film_name:
                                    entry['film'] = film_name
                                results[f'best-{cat}'].append(entry)
    
    total = len(results['best-film']) + len(results['best-director']) + len(results['best-actor']) + len(results['best-actress'])
    print(f"    Gotham {gotham_year}: Found {total} entries (Films: {len(results['best-film'])}, Dir: {len(results['best-director'])}, Actor: {len(results['best-actor'])}, Actress: {len(results['best-actress'])})")
    
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
            elif header_text == 'best director' or header_text == 'best direction':
                # Note: Old BAFTA pages (pre-2020) use "Best Direction" instead of "Best Director"
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
        awards = ['oscar', 'gg', 'bafta', 'sag', 'critics', 'afi', 'nbr', 'venice', 'dga', 'pga', 'wga']
    
    print(f"\n{'='*60}")
    print(f"  SCRAPING SEASON {year-1}/{year}")
    print(f"{'='*60}")
    
    all_results = {}
    
    for award_key in awards:
        # AFI, NBR, Venice, DGA, PGA use special scrapers
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
        elif award_key == 'dga':
            dga_year = CEREMONY_MAP['dga'].get(year)
            if dga_year:
                result = scrape_dga(dga_year)
                if result:
                    all_results['dga'] = result
        elif award_key == 'pga':
            pga_num = CEREMONY_MAP['pga'].get(year)
            if pga_num:
                result = scrape_pga(pga_num)
                if result:
                    all_results['pga'] = result
        elif award_key == 'lafca':
            lafca_year = CEREMONY_MAP['lafca'].get(year)
            if lafca_year:
                result = scrape_lafca(lafca_year)
                if result:
                    all_results['lafca'] = result
        elif award_key == 'wga':
            wga_num = CEREMONY_MAP['wga'].get(year)
            if wga_num:
                result = scrape_wga(wga_num)
                if result:
                    all_results['wga'] = result
        elif award_key == 'adg':
            adg_year = CEREMONY_MAP['adg'].get(year)
            if adg_year:
                result = scrape_adg(year)
                if result:
                    all_results['adg'] = result
        elif award_key == 'gotham':
            gotham_year = CEREMONY_MAP['gotham'].get(year)
            if gotham_year:
                result = scrape_gotham(year)
                if result:
                    all_results['gotham'] = result
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



def scrape_gotham_v2_logic(soup):
    import re
    
    results = {
        'best-film': [],
        'best-director': [],
        'best-actor': [],
        'best-actress': []
    }
    
    seen = {'film': set(), 'director': set(), 'actor': set(), 'actress': set()}
    
    tables = soup.find_all('table', class_='wikitable')
    if not tables:
        print("    No wikitable found (logic v2)")
        return results
    
    # ============ NEW: Try div-based format (2025+) ============
    # Look for bold tags or divs containing category titles, followed by ul lists
    # This handles the new two-column flex layout
    div_based_found = False
    
    for table in tables:
        # Skip summary tables
        header_text = ' '.join([th.get_text().strip().lower() for th in table.find_all('th')])
        if 'wins' in header_text and 'nominations' in header_text:
            continue
            
        # Find all bold or div elements that might be category headers
        category_elements = table.find_all(['b', 'div'])
        
        for elem in category_elements:
            elem_text = elem.get_text().strip().lower()
            
            # Skip excluded categories (but NOT breakthrough director/actor)
            excluded_keywords = ['international', 'documentary', 'series', 'screenplay', 'tribute', 'ensemble', 'icon', 'musical']
            if any(kw in elem_text for kw in excluded_keywords):
                continue
            
            # Skip "breakthrough" categories except "breakthrough actor" for legacy
            if 'breakthrough' in elem_text and 'actor' not in elem_text:
                continue
            
            # Identify category
            cat_found = None
            if elem_text == 'best feature' or elem_text == 'feature':
                cat_found = 'best-film'
            # Director: Only "Best Director" (exists from 2024+)
            elif 'best director' in elem_text:
                cat_found = 'best-director'
            # Performance (2021+): Outstanding Lead/Supporting Performance
            elif 'outstanding lead performance' in elem_text or 'lead performance' in elem_text:
                cat_found = 'lead-performance'
            elif 'outstanding supporting performance' in elem_text or 'supporting performance' in elem_text:
                cat_found = 'supporting-performance'
            # Legacy (pre-2021): Best Actor, Best Actress, Breakthrough Actor
            elif elem_text == 'best actor' or 'breakthrough actor' in elem_text:
                cat_found = 'best-actor'
            elif elem_text == 'best actress':
                cat_found = 'best-actress'
            
            if not cat_found:
                continue
            
            # Find the ul list following this element
            # It might be a sibling or inside the parent's next sibling
            ul = None
            if elem.find_next_sibling('ul'):
                ul = elem.find_next_sibling('ul')
            elif elem.parent and elem.parent.find_next_sibling():
                next_elem = elem.parent.find_next_sibling()
                if next_elem and next_elem.name == 'ul':
                    ul = next_elem
                elif next_elem:
                    ul = next_elem.find('ul')
            
            # Also check if ul is directly in the same cell (td)
            if not ul:
                parent_cell = elem.find_parent('td')
                if parent_cell:
                    ul = parent_cell.find('ul')
            
            if ul:
                div_based_found = True
                # Use recursive=True to get all li items including nested ones
                for li in ul.find_all('li'):
                    is_winner = bool(li.find('b'))
                    text = li.get_text().strip()
                    
                    # Parse name and film (first part before dash)
                    name = text.split('–')[0].split(' – ')[0].strip()
                    film = ""
                    if '–' in text:
                        film = text.split('–')[1].strip()
                    elif ' – ' in text:
                        film = text.split(' – ')[1].strip()
                    
                    _add_gotham_v2(results, seen, cat_found, name, film, is_winner)
    
    # If we found data using div-based approach, return early
    if div_based_found:
        total = len(results['best-film']) + len(results['best-director']) + len(results['best-actor']) + len(results['best-actress'])
        print(f"    Gotham (logic v2 - div format): Found {total} entries (Films: {len(results['best-film'])}, Dir: {len(results['best-director'])})")
        return results
    
    # ============ LEGACY: Skip summary tables ============
    valid_tables = []
    for t in tables:
        header_text = ' '.join([th.get_text().strip().lower() for th in t.find_all('th')])
        if 'wins' in header_text and 'nominations' in header_text and 'film' in header_text:
            continue  # Skip summary table
        valid_tables.append(t)
    tables = valid_tables

    for table in tables:
        # Check standard headers first (column-based)
        headers = [th.get_text().strip().lower() for th in table.find_all('th')]
        
        is_column_based = False
        col_map = {}
        for idx, h in enumerate(headers):
            if 'feature' in h and 'international' not in h: col_map[idx] = 'best-film'
            elif 'director' in h: col_map[idx] = 'best-director'
            elif 'lead performance' in h: col_map[idx] = 'lead-performance'
            elif 'supporting performance' in h: col_map[idx] = 'supporting-performance'
        
        if col_map: is_column_based = True

        rows = table.find_all('tr')
        current_category = None 

        for row in rows:
            cells = row.find_all(['td', 'th'])
            if not cells: continue

            # Iterate ALL cells in the row
            for cell_idx, cell0 in enumerate(cells):
                cell0_text = cell0.get_text(separator='\n').strip()
                cell0_lower = cell0_text.lower()
                
                if 'wins' in cell0_lower and 'nominations' in cell0_lower: continue
                
                # Analyze first line of cell to see if it's a category
                lines = [l.strip() for l in cell0_text.split('\n') if l.strip()]
                if not lines: continue
                
                first_line_clean = lines[0].lower().replace('best ', '').replace('outstanding ', '').strip()
                
                # Determine category from FIRST LINE
                cat_found = None
                if first_line_clean == 'feature': 
                    cat_found = 'best-film'
                elif 'director' in first_line_clean: 
                    cat_found = 'best-director' 
                elif 'lead performance' in first_line_clean: 
                    cat_found = 'lead-performance'
                elif 'supporting performance' in first_line_clean: 
                    cat_found = 'supporting-performance'
                elif first_line_clean == 'actor': 
                    cat_found = 'best-actor'
                elif first_line_clean == 'actress': 
                    cat_found = 'best-actress'
                
                # Exclude unwanted categories (but NOT breakthrough director/actor)
                excluded_keywords = ['international', 'documentary', 'series', 'screenplay', 'tribute', 'ensemble', 'icon', 'musical']
                if any(kw in first_line_clean for kw in excluded_keywords):
                    cat_found = None
                    current_category = None  # Also reset current category to avoid bleeding
                
                # Skip "breakthrough" categories except "breakthrough actor" for legacy
                if 'breakthrough' in first_line_clean:
                    if 'actor' in first_line_clean:
                        cat_found = 'best-actor'
                    else:
                        cat_found = None
                        current_category = None

                # Check if this is a "Single Cell" (Category + Nominees in one cell)
                is_single_cell_block = cat_found and len(lines) > 1

                if is_single_cell_block:
                    current_category = cat_found
                    nominees = lines[1:]
                    
                    winners_text = [b.get_text().strip() for b in cell0.find_all('b')]
                    
                    for nom in nominees:
                        is_winner = any(w in nom or nom in w for w in winners_text if w)
                        
                        text = nom
                        name = text.split('–')[0].split('-')[0].strip()
                        film = ""
                        if '–' in text: film = text.split('–')[1].strip()
                        elif '-' in text and len(text.split('-')) > 1: film = text.split('-')[1].strip()
                        
                        _add_gotham_v2(results, seen, current_category, name, film, is_winner)
                    
                    continue 

                # If pure header
                if cat_found:
                    current_category = cat_found
                    continue 

                # --- Nominee Parsing (Standard Rows / Multicell) ---
                if is_column_based:
                    continue 

                if current_category:
                     # LIST Format (ul) inside cell
                    uls = cell0.find_all('ul')
                    if uls:
                        for ul in uls:
                            for li in ul.find_all('li'):
                                is_winner = bool(li.find('b'))
                                text = li.get_text().strip()
                                name = text.split('–')[0].split('-')[0].strip()
                                film = ""
                                if '–' in text: film = text.split('–')[1].strip()
                                elif '-' in text: film = text.split('-')[1].strip()
                                _add_gotham_v2(results, seen, current_category, name, film, is_winner)
                    else:
                        # Just text in cell
                        is_winner = 'style' in row.attrs and 'background' in row.attrs['style']
                        if not is_winner: is_winner = bool(cell0.find('b'))
                        
                        text = cell0_text.replace('\n', ' ')
                        if current_category == 'best-film':
                             _add_gotham_v2(results, seen, 'best-film', text, "", is_winner)
                        elif current_category in ['best-director', 'lead-performance', 'supporting-performance', 'best-actor', 'best-actress']:
                             name = text.split('–')[0].split('-')[0].strip()
                             film = ""
                             if '–' in text: film = text.split('–')[1].strip()
                             elif '-' in text: film = text.split('-')[1].strip()
                             
                             _add_gotham_v2(results, seen, current_category, name, film, is_winner)

    total = len(results['best-film']) + len(results['best-director']) + len(results['best-actor']) + len(results['best-actress'])
    print(f"    Gotham (logic v2): Found {total} entries (Films: {len(results['best-film'])}, Dir: {len(results['best-director'])})")
    return results

def _add_gotham_v2(results, seen, cat_type, name, film, is_winner):
    if not name: return
    award_val = 'Y' if is_winner else 'X'
    
    if cat_type == 'best-film':
        if name not in seen['film']:
            seen['film'].add(name)
            results['best-film'].append({'name': name, 'awards': {'gotham': award_val}})
            
    elif cat_type == 'best-director':
        if name not in seen['director']:
            seen['director'].add(name)
            entry = {'name': name, 'awards': {'gotham': award_val}}
            if film: entry['film'] = film
            results['best-director'].append(entry)
            
    elif cat_type in ['lead-performance', 'supporting-performance', 'best-actor', 'best-actress']:
        if cat_type == 'best-actor':
            target_cat = 'best-actor'
            seen_key = 'actor'
        elif cat_type == 'best-actress':
            target_cat = 'best-actress'
            seen_key = 'actress'
        else:
            try:
                gender = get_person_gender(name)
            except:
                 gender = 0
            
            target_cat = 'best-actress' if gender == 1 else 'best-actor'
            seen_key = 'actress' if gender == 1 else 'actor'
        
        if name not in seen[seen_key]:
            seen[seen_key].add(name)
            entry = {'name': name, 'awards': {'gotham': award_val}}
            if film: entry['film'] = film
            results[target_cat].append(entry)



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
