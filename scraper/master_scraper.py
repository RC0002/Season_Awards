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

try:
    from manual_adg_data import MANUAL_ADG_DATA
except ImportError:
    try:
        from scraper.manual_adg_data import MANUAL_ADG_DATA
    except ImportError:
         MANUAL_ADG_DATA = {}

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
        2015: 87, 2014: 86, 2013: 85, 2012: 84, 2011: 83, 2010: 82,
        2009: 81, 2008: 80, 2007: 79, 2006: 78, 2005: 77, 2004: 76,
        2003: 75, 2002: 74, 2001: 73
    },
    # Golden Globe: 82nd in Jan 2025
    'gg': {
        2026: 83, 2025: 82, 2024: 81, 2023: 80, 2022: 79, 2021: 78,
        2020: 77, 2019: 76, 2018: 75, 2017: 74, 2016: 73,
        2015: 72, 2014: 71, 2013: 70, 2012: 69, 2011: 68, 2010: 67,
        2009: 66, 2008: 65, 2007: 64, 2006: 63, 2005: 62, 2004: 61,
        2003: 60, 2002: 59, 2001: 58
    },
    # BAFTA: 78th in Feb 2025
    'bafta': {
        2026: 79, 2025: 78, 2024: 77, 2023: 76, 2022: 75, 2021: 74,
        2020: 73, 2019: 72, 2018: 71, 2017: 70, 2016: 69,
        2015: 68, 2014: 67, 2013: 66, 2012: 65, 2011: 64, 2010: 63,
        2009: 62, 2008: 61, 2007: 60, 2006: 59, 2005: 58, 2004: 57,
        2003: 56, 2002: 55, 2001: 54
    },
    # SAG: 31st in Feb 2025
    'sag': {
        2026: 32, 2025: 31, 2024: 30, 2023: 29, 2022: 28, 2021: 27,
        2020: 26, 2019: 25, 2018: 24, 2017: 23, 2016: 22,
        2015: 21, 2014: 20, 2013: 19, 2012: 18, 2011: 17, 2010: 16,
        2009: 15, 2008: 14, 2007: 13, 2006: 12, 2005: 11, 2004: 10,
        2003: 9, 2002: 8, 2001: 7
    },
    # Critics Choice: 30th in Jan 2025
    'critics': {
        2026: 31, 2025: 30, 2024: 29, 2023: 28, 2022: 27, 2021: 26,
        2020: 25, 2019: 24, 2018: 23, 2017: 22, 2016: 21,
        2015: 20, 2014: 19, 2013: 18, 2012: 17, 2011: 16, 2010: 15,
        2009: 14, 2008: 13, 2007: 12, 2006: 11, 2005: 10, 2004: 9,
        2003: 8, 2002: 7, 2001: 6
    },
    # AFI: year of films (2024 season = films from 2024 = AFI 2024)
    # Maps season second year to AFI year (which is first year)
    'afi': {
        2026: 2025, 2025: 2024, 2024: 2023, 2023: 2022, 2022: 2021, 2021: 2020,
        2020: 2019, 2019: 2018, 2018: 2017, 2017: 2016, 2016: 2015,
        2015: 2014, 2014: 2013, 2013: 2012, 2012: 2011, 2011: 2010, 2010: 2009,
        2009: 2008, 2008: 2007, 2007: 2006, 2006: 2005, 2005: 2004, 2004: 2003,
        2003: 2002, 2002: 2001, 2001: 2000
    },
    # NBR: same as AFI - year of films
    'nbr': {
        2026: 2025, 2025: 2024, 2024: 2023, 2023: 2022, 2022: 2021, 2021: 2020,
        2020: 2019, 2019: 2018, 2018: 2017, 2017: 2016, 2016: 2015,
        2015: 2014, 2014: 2013, 2013: 2012, 2012: 2011, 2011: 2010, 2010: 2009,
        2009: 2008, 2008: 2007, 2007: 2006, 2006: 2005, 2005: 2004, 2004: 2003,
        2003: 2002, 2002: 2001, 2001: 2000
    },
    # Venice: Mostra di Venezia - uses ordinal like 82ª for 82nd edition
    # 82nd in 2025 (Sept 2025 for 2024/2025 season films) -> NO, Sept 2025 is for 2025/2026 season!
    # Season 2025 (2024/25) -> Venice 81 (Sept 2024)
    'venice': {
        2026: 82, 2025: 81, 2024: 80, 2023: 79, 2022: 78, 2021: 77,
        2020: 76, 2019: 75, 2018: 74, 2017: 73, 2016: 72,
        2015: 71, 2014: 70, 2013: 69, 2012: 68, 2011: 67, 2010: 66,
        2009: 65, 2008: 64, 2007: 63, 2006: 62, 2005: 61, 2004: 60,
        2003: 59, 2002: 58, 2001: 57
    },
    # DGA: Directors Guild of America - year of films (like AFI/NBR)
    # Data scraped from dga.org via Selenium, stored in dga_awards.json
    'dga': {
        2026: 2025, 2025: 2024, 2024: 2023, 2023: 2022, 2022: 2021, 2021: 2020,
        2020: 2019, 2019: 2018, 2018: 2017, 2017: 2016, 2016: 2015,
        2015: 2014, 2014: 2013, 2013: 2012, 2012: 2011, 2011: 2010, 2010: 2009,
        2009: 2008, 2008: 2007, 2007: 2006, 2006: 2005, 2005: 2004, 2004: 2003,
        2003: 2002, 2002: 2001, 2001: 2000
    },
    # PGA: Producers Guild of America - ceremony number
    # 36th in 2025 for 2024/2025 season
    'pga': {
        2026: 37, 2025: 36, 2024: 35, 2023: 34, 2022: 33, 2021: 32,
        2020: 31, 2019: 30, 2018: 29, 2017: 28, 2016: 27,
        2015: 26, 2014: 25, 2013: 24, 2012: 23, 2011: 22, 2010: 21,
        2009: 20, 2008: 19, 2007: 18, 2006: 17, 2005: 16, 2004: 15,
        2003: 14, 2002: 13, 2001: 12
    },
    # LAFCA: Los Angeles Film Critics Association - year of films
    # 2024 season = 2024 LAFCA Awards (for films from 2024)
    'lafca': {
        2026: 2025, 2025: 2024, 2024: 2023, 2023: 2022, 2022: 2021, 2021: 2020,
        2020: 2019, 2019: 2018, 2018: 2017, 2017: 2016, 2016: 2015,
        2015: 2014, 2014: 2013, 2013: 2012, 2012: 2011, 2011: 2010, 2010: 2009,
        2009: 2008, 2008: 2007, 2007: 2006, 2006: 2005, 2005: 2004, 2004: 2003,
        2003: 2002, 2002: 2001, 2001: 2000
    },
    # WGA: Writers Guild of America - ceremony number
    # 77th in 2025 for 2024/2025 season
    'wga': {
        2026: 78, 2025: 77, 2024: 76, 2023: 75, 2022: 74, 2021: 73,
        2020: 72, 2019: 71, 2018: 70, 2017: 69, 2016: 68,
        2015: 67, 2014: 66, 2013: 65, 2012: 64, 2011: 63, 2010: 62,
        2009: 61, 2008: 60, 2007: 59, 2006: 58, 2005: 57, 2004: 56,
        2003: 55, 2002: 54, 2001: 53
    },
    # ADG: Art Directors Guild - year-based URL (like AFI/NBR)
    # 29th in 2024 for 2024/2025 season (Art_Directors_Guild_Awards_2024)
    'adg': {
        2026: 2025, 2025: 2024, 2024: 2023, 2023: 2022, 2022: 2021, 2021: 2020,
        2020: 2019, 2019: 2018, 2018: 2017, 2017: 2016, 2016: 2015,
        2015: 2014, 2014: 2013, 2013: 2012, 2012: 2011, 2011: 2010, 2010: 2009,
        2009: 2008, 2008: 2007, 2007: 2006, 2006: 2005, 2005: 2004, 2004: 2003,
        2003: 2002, 2002: 2001, 2001: 2000
    },
    # Gotham Independent Film Awards - year-based URL
    # Gotham 2025 (35th, held Dec 2025) covers films from 2025 → 2025/2026 season
    'gotham': {
        2026: 2025, 2025: 2024, 2024: 2023, 2023: 2022, 2022: 2021, 2021: 2020,
        2020: 2019, 2019: 2018, 2018: 2017, 2017: 2016, 2016: 2015,
        2015: 2014, 2014: 2013, 2013: 2012, 2012: 2011, 2011: 2010, 2010: 2009,
        2009: 2008, 2008: 2007, 2007: 2006, 2006: 2005, 2005: 2004, 2004: 2003,
        2003: 2002, 2002: 2001, 2001: 2000
    },
    # Annie Awards: 53rd in 2026 for 2025 films (Season 2025/26)
    # Formula: Year - 1973 = Ceremony Number
    'annie': {
        2026: 53, 2025: 52, 2024: 51, 2023: 50, 2022: 49, 2021: 48,
        2020: 47, 2019: 46, 2018: 45, 2017: 44, 2016: 43,
        2015: 42, 2014: 41, 2013: 40, 2012: 39, 2011: 38, 2010: 37,
        2009: 36, 2008: 35, 2007: 34, 2006: 33, 2005: 32, 2004: 31,
        2003: 30, 2002: 29, 2001: 28
    },
    # Astra Film Awards (formerly Hollywood Critics Association - HCA)
    # 9th Astra in 2026 for 2025 films (Season 2025/26)
    # 8th Astra in 2025 for 2024 films (Season 2024/25)
    'astra': {
        2026: 9, 2025: 8, 2024: 7, 2023: 6, 2022: 5, 2021: 4,
        2020: 3, 2019: 2, 2018: 1
    },
    # Spirit Awards (Independent Spirit Awards) - ceremony number
    # 41st in 2026 for Season 2025/26 (films from 2025)
    'spirit': {
        2026: 41, 2025: 40, 2024: 39, 2023: 38, 2022: 37, 2021: 36,
        2020: 35, 2019: 34, 2018: 33, 2017: 32, 2016: 31,
        2015: 30, 2014: 29, 2013: 28, 2012: 27, 2011: 26, 2010: 25,
        2009: 24, 2008: 23, 2007: 22, 2006: 21, 2005: 20, 2004: 19,
        2003: 18, 2002: 17, 2001: 16
    },
    'bifa': {
        2026: 2025, 2025: 2024, 2024: 2023, 2023: 2022, 2022: 2021, 2021: 2020,
        2020: 2019, 2019: 2018, 2018: 2017, 2017: 2016, 2016: 2015,
        2015: 2014, 2014: 2013, 2013: 2012, 2012: 2011, 2011: 2010, 2010: 2009,
        2009: 2008, 2008: 2007, 2007: 2006, 2006: 2005, 2005: 2004, 2004: 2003,
        2003: 2002, 2002: 2001, 2001: 2000
    },
    # Cannes Film Festival - uses calendar year
    # Cannes 2025 (May/June 2025) → Season 2025/26
    # Cannes 2024 (May 2024) → Season 2024/25
    'cannes': {
        2026: 2025, 2025: 2024, 2024: 2023, 2023: 2022, 2022: 2021, 2021: 2020,
        2020: 2019, 2019: 2018, 2018: 2017, 2017: 2016, 2016: 2015,
        2015: 2014, 2014: 2013, 2013: 2012, 2012: 2011, 2011: 2010, 2010: 2009,
        2009: 2008, 2008: 2007, 2007: 2006, 2006: 2005, 2005: 2004, 2004: 2003,
        2003: 2002, 2002: 2001, 2001: 2000
    },
    # Annie Awards - ceremony number = season_end_year - 1973
    # 52nd Annie Awards (2025) → Season 2024/25
    'annie': {
        2026: 53, 2025: 52, 2024: 51, 2023: 50, 2022: 49, 2021: 48,
        2020: 47, 2019: 46, 2018: 45, 2017: 44, 2016: 43,
        2015: 42, 2014: 41, 2013: 40, 2012: 39, 2011: 38, 2010: 37,
        2009: 36, 2008: 35, 2007: 34, 2006: 33, 2005: 32, 2004: 31,
        2003: 30, 2002: 29, 2001: 28
    },
    # NYFCC: New York Film Critics Circle - year of films (like LAFCA)
    'nyfcc': {
        2026: 2025, 2025: 2024, 2024: 2023, 2023: 2022, 2022: 2021, 2021: 2020,
        2020: 2019, 2019: 2018, 2018: 2017, 2017: 2016, 2016: 2015,
        2015: 2014, 2014: 2013, 2013: 2012, 2012: 2011, 2011: 2010, 2010: 2009,
        2009: 2008, 2008: 2007, 2007: 2006, 2006: 2005, 2005: 2004, 2004: 2003, 
        2003: 2002, 2002: 2001, 2001: 2000
    }
}

# Wikipedia URL templates - use {ord} placeholder for ordinal (like 82nd, 31st)
URL_TEMPLATES = {
    'oscar': 'https://en.wikipedia.org/wiki/{ord}_Academy_Awards',
    'gg': 'https://en.wikipedia.org/wiki/{ord}_Golden_Globe_Awards',  
    'bafta': 'https://en.wikipedia.org/wiki/{ord}_British_Academy_Film_Awards',
    # SAG Awards renamed to "Actor Awards" starting from 32nd edition (2026)
    'sag': 'https://en.wikipedia.org/wiki/{ord}_Screen_Actors_Guild_Awards',
    'sag_new': 'https://en.wikipedia.org/wiki/{ord}_Actor_Awards',  # 32nd+ editions
    'critics': 'https://en.wikipedia.org/wiki/{ord}_Critics%27_Choice_Awards',
    'nbr': 'https://en.wikipedia.org/wiki/National_Board_of_Review_Awards_{year}',
    'venice': 'https://it.wikipedia.org/wiki/{ord}%C2%AA_Mostra_internazionale_d%27arte_cinematografica_di_Venezia',
    'pga': 'https://en.wikipedia.org/wiki/{ord}_Producers_Guild_of_America_Awards',
    'dga': 'https://en.wikipedia.org/wiki/{ord}_Directors_Guild_of_America_Awards',
    'lafca': 'https://en.wikipedia.org/wiki/{year}_Los_Angeles_Film_Critics_Association_Awards',
    'wga': 'https://en.wikipedia.org/wiki/{ord}_Writers_Guild_of_America_Awards',
    'adg': 'https://en.wikipedia.org/wiki/Art_Directors_Guild_Awards_{year}',
    'gotham': 'https://en.wikipedia.org/wiki/Gotham_Independent_Film_Awards_{year}',
    'spirit': 'https://en.wikipedia.org/wiki/{ord}_Independent_Spirit_Awards',
    'nyfcc': 'https://en.wikipedia.org/wiki/{year}_New_York_Film_Critics_Circle_Awards'
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
    # IMPORTANT: Handle TIE winners where multiple winners are in the same <b> tag separated by <br>
    for bold in cell.find_all('b', recursive=True):
        # Skip if this bold is inside a list item (will be processed later)
        if bold.find_parent('li'):
            continue
        
        # Get ALL links in this bold tag (for ties, there may be multiple winners)
        all_links_in_bold = bold.find_all('a')
        if not all_links_in_bold:
            continue
        
        # Process each potential winner link
        # Strategy: alternate between person and film if category is director/actor
        # For simple cases: first link = person, second link = film
        # For ties: multiple persons, each with their own film
        
        # Separate text segments by <br> to detect tie format
        bold_html = str(bold)
        segments = bold_html.split('<br')  # Split on <br> or <br/>
        
        if len(segments) > 1:
            # TIE FORMAT: Multiple winners separated by <br>
            for segment in segments:
                # Parse this segment to find person and film
                from bs4 import BeautifulSoup as BS
                seg_soup = BS('<span>' + segment + '</span>', 'html.parser')
                links = seg_soup.find_all('a')
                
                if not links:
                    continue
                
                # First link is the person
                person_link = links[0]
                person_name = person_link.get_text().strip()
                link_title = person_link.get('title', '') or ''
                
                if any(w in link_title for w in skip_words):
                    continue
                if len(person_name) < 2:
                    continue
                
                # Second link (if exists) is the film
                film = None
                if category_type in ['director', 'actor'] and len(links) > 1:
                    film = links[1].get_text().strip()
                
                entry_key = (person_name, film) if film else (person_name, None)
                if entry_key in seen_entries:
                    continue
                seen_entries.add(entry_key)
                
                entry = {'name': person_name, 'is_winner': True}
                if film:
                    entry['film'] = film
                nominees.append(entry)
        else:
            # SINGLE WINNER FORMAT: Just one person in bold
            first_link = all_links_in_bold[0]
            link_title = first_link.get('title', '') or ''
            if any(w in link_title for w in skip_words):
                continue
            
            name = first_link.get_text().strip()
            if len(name) < 2:
                continue
            
            # Get film name for person categories
            film = None
            if category_type in ['director', 'actor']:
                for link in all_links_in_bold[1:]:
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
                            if link in all_links_in_bold:
                                continue
                            link_text = link.get_text().strip()
                            link_title = link.get('title', '') or ''
                            if any(w in link_title for w in skip_words):
                                continue
                            if len(link_text) > 1:
                                film = link_text
                                break
            
            entry_key = (name, film) if film else (name, None)
            if entry_key in seen_entries:
                continue
            seen_entries.add(entry_key)
            
            entry = {'name': name, 'is_winner': True}
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


# ============ IMPORT MODULARIZED SCRAPERS ============
# Individual award scrapers are now in separate modules for easier testing
from scrapers.oscar import scrape_oscar
from scrapers.gg import scrape_gg_old_format
from scrapers.bafta import scrape_bafta
from scrapers.sag import scrape_sag_old_format
from scrapers.critics import scrape_critics
from scrapers.afi import scrape_afi
from scrapers.nbr import scrape_nbr
from scrapers.venice import scrape_venice
from scrapers.dga import scrape_dga
from scrapers.pga import scrape_pga
from scrapers.lafca import scrape_lafca
from scrapers.wga import scrape_wga
from scrapers.adg import scrape_adg  
from scrapers.gotham import scrape_gotham
from scrapers.astra import scrape_astra
from scrapers.cannes import scrape_cannes
from scrapers.nyfcc import scrape_nyfcc
# Spirit already imported earlier at line ~3144


# NOTE: scrape_gg_old_format is imported from scrapers.gg (line 312)
# Do not redefine it here as it would shadow the import


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
                            # For actors, get from first <a> tag or text before dash if no link
                            first_link = li.find('a')
                            if first_link:
                                name = first_link.get_text().strip()
                            else:
                                # Fallback: extract name from text before "–" or "-"
                                li_text = li.get_text().strip()
                                if '–' in li_text:
                                    name = li_text.split('–')[0].strip()
                                elif '-' in li_text:
                                    name = li_text.split('-')[0].strip()
                                else:
                                    continue
                                if len(name) < 2:
                                    continue
                            # Get film name - first try <i> tag (common in SAG pages), then 2nd <a> link
                            film_name = ''
                            i_tag = li.find('i')
                            if i_tag:
                                # Film name is in italic - extract first <a> inside <i> or text
                                i_link = i_tag.find('a')
                                if i_link:
                                    film_name = i_link.get_text().strip()
                                else:
                                    film_name = i_tag.get_text().strip()
                            else:
                                # Fallback: use 2nd <a> link if no <i> tag
                                all_links = li.find_all('a')
                                if len(all_links) >= 2:
                                    film_name = all_links[1].get_text().strip()
                            entry_key = (name, film_name)
                            
                            if len(name) < 2 or entry_key in seen_entries.get(key, set()):
                                continue
                            
                            if key in seen_entries:
                                seen_entries[key].add(entry_key)
                            
                            # Check if winner (bold)
                            is_bold = li.find('b') is not None or (first_link and first_link.find_parent('b') is not None)
                            
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
        elif current.name == 'div' or current.name == 'link':
            h3 = current.find('h3')
            if not h3:
                h3 = current.find('h4')
        elif current.name == 'h4':
            h3 = current

        if h3:
            h3_text = h3.get_text().lower()
            is_people_category = any(x in h3_text for x in ['actor', 'actress', 'director', 'screenwriter'])
            
            if (('top 10 films' in h3_text or 'top 11 films' in h3_text or 'movie of the year' in h3_text or 'movies' == h3_text.strip()) and not is_people_category):
                found_films = True
                found_special = False
                # Check if UL is inside this same div
                if current.name == 'div' or current.name == 'link':
                    ul = current.find('ul')
                    if ul:
                        # Helper to extract films recursively (for 2001 nested format)
                        def extract_films_from_ul(ul_tag):
                            extracted = []
                            for li in ul_tag.find_all('li', recursive=False):
                                # Check for link in this li provided it's not just a container for another ul
                                # Actually in 2001: Winner is text/link in li, Nominees are in nested ul
                                
                                # 1. Extract film from this li
                                link = li.find('a')
                                if link:
                                    film_name = link.get_text().strip()
                                else:
                                    # Use text but exclude nested ul content if any
                                    # Get text node only? Or get text and strip
                                    film_name = li.get_text().split('\n')[0].strip()
                                
                                if len(film_name) >= 2:
                                    extracted.append(film_name)
                                
                                # 2. Check for nested ul
                                nested_ul = li.find('ul')
                                if nested_ul:
                                    extracted.extend(extract_films_from_ul(nested_ul))
                            return extracted

                        films = extract_films_from_ul(ul)
                        for film_name in films:
                            entry = {
                                'name': film_name,
                                'awards': {'afi': 'Y'}
                            }
                            results['best-film'].append(entry)
                        found_films = False  # Already processed
                
                # Also check for p/i tags for 2000 format? (Maybe not needed yet)
            elif 'special award' in h3_text:
                found_special = True
                found_films = False
                # Check if UL is inside this same div
                if current.name == 'div' or current.name == 'link':
                    ul = current.find('ul')
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
            # Helper to extract films recursively (for 2001 nested format)
            def extract_films_from_ul(ul_tag):
                extracted = []
                for li in ul_tag.find_all('li', recursive=False):
                    link = li.find('a')
                    if link:
                        film_name = link.get_text().strip()
                    else:
                        film_name = li.get_text().split('\n')[0].strip()
                    
                    if len(film_name) >= 2:
                        extracted.append(film_name)
                    
                    nested_ul = li.find('ul')
                    if nested_ul:
                        extracted.extend(extract_films_from_ul(nested_ul))
                return extracted

            films = extract_films_from_ul(current)
            for film_name in films:
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
    
    # 1. FIND TOP 10 FILMS section
    top10_header = None
    # ID check
    if soup.find(id='Top_10_Films'): top10_header = soup.find(id='Top_10_Films')
    elif soup.find(id='Top_10_films'): top10_header = soup.find(id='Top_10_films')
    
    # Text fallback
    if not top10_header:
        for h2 in soup.find_all('h2'):
            text = h2.get_text().lower()
            if 'top' in text and 'film' in text and ('10' in text or 'ten' in text):
                top10_header = h2
                break
    
    if top10_header:
        container = top10_header.parent
        # If header is wrapped in mw-heading div, start searching after that div
        if container.name == 'div' and 'mw-heading' in container.get('class', []):
            current = container.next_sibling
        else:
            current = top10_header.next_sibling
            
        while current:
            if not hasattr(current, 'name'):
                current = current.next_sibling
                continue
            
            # Stop at next section
            if current.name in ['h2', 'h3'] or (current.name == 'div' and 'mw-heading' in current.get('class', [])):
                break
            
            # Parse films from UL (unordered) or OL (ordered - older years)
            if current.name in ['ul', 'ol']:
                for li in current.find_all('li', recursive=False):
                    link = li.find('a')
                    if link:
                        film_name = link.get_text().strip()
                        if len(film_name) >= 2 and film_name not in seen_films:
                            seen_films.add(film_name)
                            entry = {'name': film_name, 'awards': {'nbr': 'Y'}}
                            results['best-film'].append(entry)
            
            # Sometimes Best Film is in a separate P tag with a link (e.g. 2005 Best Film: Good Night, and Good Luck)
            # Only if we haven't found a list yet or in addition? Usually list contains top 10.
            # Older pages put "Best Film" in the "Winners" section, so this might be redundant if we check winners properly.
            
            current = current.next_sibling

    # 2. FIND WINNERS section
    winners_header = None
    for keyword in ['Winners', 'Awards', 'Award Winners']:
        if soup.find(id=keyword):
            winners_header = soup.find(id=keyword)
            break
            
    if not winners_header:
        for h2 in soup.find_all('h2'):
            if 'winner' in h2.get_text().lower() or 'award' in h2.get_text().lower():
                winners_header = h2
                break
    
    if winners_header:
        container = winners_header.parent
        if container.name == 'div' and 'mw-heading' in container.get('class', []):
            current = container.next_sibling
        else:
            current = winners_header.next_sibling
            
        current_category = None
        
        while current:
            if not hasattr(current, 'name'):
                current = current.next_sibling
                continue
            
            if current.name in ['h2', 'h3'] or (current.name == 'div' and 'mw-heading' in current.get('class', [])):
                break
            
            # Case A: Category Header followed by list (Modern format)
            # <p><b>Best Actor:</b></p> <ul><li>...</li></ul>
            if current.name == 'p':
                b = current.find('b')
                if b:
                    cat_text = b.get_text().lower()
                    if 'director' in cat_text and 'debut' not in cat_text: current_category = 'best-director'
                    elif 'actor' in cat_text and 'supporting' not in cat_text and 'breakthrough' not in cat_text: current_category = 'best-actor'
                    elif 'actress' in cat_text and 'supporting' not in cat_text and 'breakthrough' not in cat_text: current_category = 'best-actress'
                    elif ('best film' in cat_text or 'best picture' in cat_text) and 'foreign' not in cat_text: current_category = 'best-film'
                    else: current_category = None
            
            if current.name == 'ul' and current_category:
                for li in current.find_all('li', recursive=False):
                    links = li.find_all('a')
                    if links:
                        # Logic: Name usually first link, film second
                        name = links[0].get_text().strip()
                        if current_category == 'best-film':
                            # For best film, the name is the film
                            if name not in seen_films:
                                seen_films.add(name)
                                results['best-film'].append({'name': name, 'awards': {'nbr': 'Y'}})
                        else:
                            # For person awards
                            film = links[1].get_text().strip() if len(links) > 1 else None
                            entry = {'name': name, 'awards': {'nbr': 'Y'}}
                            if film: entry['film'] = film
                            results[current_category].append(entry)
                current_category = None
                
            # Case B: Single List with bolded categories (Older format)
            # <ul><li><b>Best Actor:</b> Name</li> ... </ul>
            if current.name == 'ul' and not current_category:
                for li in current.find_all('li', recursive=False):
                    text = li.get_text().lower()
                    b = li.find('b')
                    
                    cat = None
                    if 'best director' in text and 'debut' not in text: cat = 'best-director'
                    elif 'best actor' in text and 'supporting' not in text and 'breakthrough' not in text: cat = 'best-actor'
                    elif 'best actress' in text and 'supporting' not in text and 'breakthrough' not in text: cat = 'best-actress'
                    elif ('best film' in text or 'best picture' in text) and 'foreign' not in text: cat = 'best-film'
                    
                    if cat:
                        # Extract Content: "Category: Name" or "Category - Name"
                        # If <b> present, text after </b> is the winner
                        links = li.find_all('a')
                        
                        if cat == 'best-film':
                            # Identify the film link. It might be the first link AFTER the category b tag
                            # Or blindly take the last link? Risk of taking director name if listed.
                            # Usually: <b>Best Picture:</b> <i><a>Film</a></i>
                            for link in links:
                                name = link.get_text().strip()
                                # Filtering out "Best Picture" if it is linked (rare)
                                if 'best' not in name.lower() and name not in seen_films:
                                    seen_films.add(name)
                                    results['best-film'].insert(0, {'name': name, 'awards': {'nbr': 'Y'}}) # Winner first
                                    break
                        else:
                            # Person Category
                            # Expect: Name (Film) or Name - Film
                            # Typically Name is the first link found in the line (excluding category if linked)
                            winner_name = None
                            winner_film = None
                            
                            valid_links = [l for l in links if 'best' not in l.get_text().lower()]
                            if valid_links:
                                winner_name = valid_links[0].get_text().strip()
                                if len(valid_links) > 1:
                                    winner_film = valid_links[1].get_text().strip()
                                    
                            if winner_name:
                                entry = {'name': winner_name, 'awards': {'nbr': 'Y'}}
                                if winner_film: entry['film'] = winner_film
                                results[cat].append(entry)

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
                    # BUT for Best Film, usually the first link is the movie, second might be irrelevant or runner-up?
                    # We should NOT treat it as "film" metadata for best-film category
                    if not is_performance and current_category == 'best-film':
                         film = None
                    else:
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
            
            # Try Format C (modern 68th+): Winner is first link with film title, nominees in li as links
            # Check if we haven't found any films yet (via p/b/i)
            if not any(e.get('screenplay_type') == screenplay_type for e in results['best-film']):
                # Winner: first link that looks like a film title
                # Skip links that are clearly studios, writers, etc.
                skip_patterns = ['films', 'pictures', 'studios', 'entertainment', 'releasing', 'productions', 'searchlight']
                all_links = data_td.find_all('a')
                for link in all_links:
                    title = link.get('title', '').lower()
                    text = link.get_text().strip()
                    # Skip if link title contains studio indicators or is empty
                    if not text or len(text) < 2:
                        continue
                    if any(pattern in title for pattern in skip_patterns):
                        continue
                    # Accept film link (has (film) OR first non-studio link)
                    if '(film)' in title or 'film)' in title or (title and not any(pattern in title for pattern in skip_patterns)):
                        if text not in seen_films:
                            seen_films.add(text)
                            results['best-film'].append({
                                'name': text,
                                'awards': {'wga': 'Y'},
                                'screenplay_type': screenplay_type
                            })
                        break
                
                # Nominees: li elements - get first link in each li
                for li in data_td.find_all('li'):
                    link = li.find('a')
                    if link:
                        text = link.get_text().strip()
                        if text and len(text) > 1 and text not in seen_films:
                            seen_films.add(text)
                            results['best-film'].append({
                                'name': text,
                                'awards': {'wga': 'X'},
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
    # Categories to look for (lowercase for matching)
    target_categories = {
        'original screenplay': 'Original',
        'adapted screenplay': 'Adapted'
    }
    
    # Iterate through all headers to track sections
    all_elements = soup.find_all(['h2', 'h3', 'h4'])
    
    current_section = ""
    
    for header in all_elements:
        header_text = header.get_text().lower().strip()
        
        # Update current section if h2 or h3
        if header.name in ['h2', 'h3']:
            current_section = header_text
            # Only continue if it's strictly H2, as H3 might BE the category header we want to parse
            if header.name == 'h2':
                continue
            
        # Skip if not in Film section
        # Section usually "film", "screenplay (film)", "motion picture"
        # Avoid "television", "radio", "promotional"
        if 'television' in current_section or 'radio' in current_section or 'promotional' in current_section or 'series' in current_section:
            continue
            
        # Identify category - accept full "original screenplay" OR just "original"/"adapted"
        screenplay_type = None
        for cat_key, type_val in target_categories.items():
            if cat_key in header_text:
                screenplay_type = type_val
                break
        
        # Fallback: match just "original" or "adapted" if in film section
        if not screenplay_type:
            if 'film' in current_section or 'motion picture' in current_section or current_section == '':
                if header_text.strip() == 'original' or header_text.strip().startswith('original['):
                    screenplay_type = 'Original'
                elif header_text.strip() == 'adapted' or header_text.strip().startswith('adapted['):
                    screenplay_type = 'Adapted'
        
        if not screenplay_type:
            continue
        # Navigate content following header
        # Structure variants:
        # Modern: h4 -> ul (first item winner with bold/icon, others nominees)
        # Historical (2002-2011): h3 -> p (winner bold/italic) -> ul (nominees)
        
        # Start looking from next sibling
        # Handle wrappings (e.g. h4 in div.mw-heading)
        start_element = header.parent if header.parent and header.parent.name == 'div' and 'mw-heading' in str(header.parent.get('class', [])) else header
        
        current = start_element.next_sibling
        
        while current:
            if hasattr(current, 'name') and current.name:
                
                # Stop conditions
                # Check for direct headers
                if current.name in ['h2', 'h3', 'h4']:
                    # Stop if we hit a header of same or higher importance
                    if current.name == 'h2': break
                    if current.name == header.name: break
                    if header.name == 'h4' and current.name == 'h3': break
                    # If we are parsing H3, H4 is a child, so continues (technically)
                    pass

                # Check for wrapped headers (div.mw-heading)
                if current.name == 'div' and any(cls.startswith('mw-heading') for cls in current.get('class', [])):
                    # Find the header inside to check level
                    h = current.find(['h2', 'h3', 'h4'])
                    if h:
                        if h.name == 'h2': break
                        if h.name == header.name: break
                        if header.name == 'h4' and h.name == 'h3': break
                
                # Case 1: Winner in Paragraph
                if current.name == 'p':
                    winner_film = None
                    bold_italic = current.find('b')
                    if bold_italic:
                        italic_in_bold = bold_italic.find('i')
                        if italic_in_bold:
                             winner_film = italic_in_bold.get_text().strip()
                        elif bold_italic.get_text().strip():
                             pass
                    
                    if not winner_film:
                        italic = current.find('i')
                        if italic:
                             winner_film = italic.get_text().strip()
                    
                    if winner_film and winner_film not in seen_films:
                        # Extra validation to avoid TV
                        if len(winner_film) > 1 and "see also" not in winner_film.lower():
                            seen_films.add(winner_film)
                            results['best-film'].append({
                                'name': winner_film,
                                'awards': {'wga': 'Y'},
                                'screenplay_type': screenplay_type
                            })

                # Case 2: List (Nominees)
                elif current.name == 'ul':
                    for li in current.find_all('li', recursive=False):
                        film_name = None
                        is_winner = False
                        
                        bold = li.find('b')
                        if bold:
                             italic = bold.find('i')
                             if italic:
                                 film_name = italic.get_text().strip()
                                 is_winner = True
                        
                        if not film_name:
                            italic = li.find('i')
                            if italic:
                                film_name = italic.get_text().strip()
                        
                        if film_name and film_name not in seen_films:
                             if "screenplay" in film_name.lower(): continue 
                             seen_films.add(film_name)
                             badge = 'Y' if is_winner else 'X'
                             results['best-film'].append({
                                'name': film_name,
                                'awards': {'wga': badge},
                                'screenplay_type': screenplay_type
                             })
                
            current = current.next_sibling

    print(f"    WGA {ordinal(ceremony_num)}: Found {len(results['best-film'])} films")
    return results


def scrape_adg(year):
    """
    Scrape Art Directors Guild Excellence in Production Design Awards.
    Extracts Film category nominees (Contemporary, Period, Fantasy, Animated).
    """
    import re
    
    season_year = year # Define season_year for use in URL logic
    
    adg_year = CEREMONY_MAP['adg'].get(year)
    if not adg_year:
        print(f"  No ADG mapping for year {year}")
        return {}

    # Check for manual data override
    if adg_year in MANUAL_ADG_DATA:
        print(f"  ADG {adg_year}: Using MANUAL DATA override")
        return MANUAL_ADG_DATA[adg_year]
    
    # Logic for ADG URLs
    # 2004-2006: Wiki pages are "Art_Directors_Guild_Awards_YYYY"
    
    if 'adg' in URL_TEMPLATES:
         url = URL_TEMPLATES['adg'].format(year=adg_year)
    else:
         url = f"https://en.wikipedia.org/wiki/Art_Directors_Guild_Awards_{adg_year}"
    
    print(f"  ADG ({adg_year}): {url}")
    
    soup = fetch_page(url)
    if not soup:
        return {}
    
    results = {'best-film': []}
    seen_films = set()
    
    # Initialize all_tables here to avoid NameError if logic below depends on it
    all_tables = soup.find_all('table', class_='wikitable')
    
    # ADG Parsing Logic update for combined categories (Period or Fantasy)
    # The original loop handles "Period Film", "Fantasy Film", "Contemporary Film".
    # We need to make sure "Period or Fantasy Film" triggers the category collection.
    
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
                # Also handle combined "Period or Fantasy Film" (2004-2006)
                # AND handle "Winner in P tag" format (2005-2006) where <p>Winner</p><ul>Nominees</ul>
                
                next_ul_is_nominees_only = False
                
                if tag_name == 'p':
                    txt_lower = element_text.lower()
                    full_text = element.get_text().strip()
                    
                    if any(cat in txt_lower for cat in ['period', 'contemporary', 'fantasy', 'animated']):
                        current_category = element_text
                    else:
                        # Check if this might be a winner (followed by UL, not a category label)
                        # Look ahead for next sibling being UL? 
                        # We are iterating `element.find_all_next`, so we can't easily check 'next' in the loop
                        # but we can rely on state.
                        # Actually, we can check if the text looks like a winner?
                        # 2006: "Casino Royale[1]"
                        # 2005: "David J. Bomba – Walk the Line[1]"
                        
                        # Heuristic: If it has content, and we are in the Film section... 
                        # checking if next element is UL is hard in this loop structure.
                        # But we can try to parse it as a film.
                        
                        # Clean text
                        cleaned_text = re.sub(r'\s*\[.*?\]', '', full_text).strip()
                        if '–' in cleaned_text:
                            possible_film = cleaned_text.split('–')[-1].strip()
                        elif '-' in cleaned_text: # Hyphen fallback
                            possible_film = cleaned_text.split('-')[-1].strip()
                        else:
                            possible_film = cleaned_text
                        
                        # Only treat as winner if NOT empty and NOT a known header-like word
                        if possible_film and len(possible_film) > 2 and "film" not in possible_film.lower():
                            # We assume this is a winner.
                            # We need to set a flag so the NEXT ul knows it contains only nominees.
                            # But wait, how do we confirm it IS followed by UL?
                            # We can blindly add it, but safeguards are better.
                            # For now, let's add it if 2005/2006.
                            is_special_year = 2004 <= season_year <= 2006 # Seasons 2005, 2006, 2007?
                            # Actually 2004 page (Season 2005) had Headers "Contemporary Film" in P tags.
                            # 2005 page (Season 2006) has Winner in P tag.
                            # 2006 page (Season 2007) has Winner in P tag.
                            
                            if 2005 <= season_year <= 2007: # Seasons where this format was observed
                                if possible_film not in seen_films:
                                    seen_films.add(possible_film)
                                    results['best-film'].append({
                                        'name': possible_film,
                                        'awards': {'adg': 'Y'}
                                    })
                                    # Implicitly, the next UL will be processed.
                                    # We need to tell the UL processor that the first item is NOT a winner.
                                    # We can set a temporary variable in the loop?
                                    # But `element` changes. We need a persistent flag outside the loop?
                                    # `next_ul_is_nominees_only` needs to be defined outside.
                                    # Let's use a class attribute or just a variable that resets?
                                    # The loop iterates `find_all_next`. It's flat.
                                    # So we can set `flag = True`.
                                    pass
                                    
                    continue
                
                # Processing UL
                if tag_name == 'ul':
                    if current_category and 'animated' in current_category.lower():
                        continue
                        
                    # Determine if first item is winner
                    # If we just added a winner from P tag, then NO.
                    # How to track?
                    # We can check if the PREVIOUS processed element was that P tag winner.
                    # Use `seen_films` most recent addition?
                    # Safer: Check the year.
                    
                    is_winner_default = True
                    if 2005 <= season_year <= 2007:
                         # In these years, winner was likely in P tag.
                         # But be careful if we DIDN'T find a P tag winner (e.g. 2004 which is season 2005?)
                         # Wait, scraping 2004 (Season 2005) worked fine with standard logic (P tags were headers).
                         # 2005 (Season 2006) and 2006 (Season 2007) failed.
                         if season_year >= 2005: 
                             is_winner_default = False
                    
                    lis = element.find_all('li', recursive=False)
                    for idx, li in enumerate(lis):
                        italic = li.find('i')
                        if italic:
                            film_name = italic.get_text().strip()
                        else:
                            text = li.get_text().strip()
                            parts = text.split('–')
                            if len(parts) > 1:
                                film_name = parts[1].strip()
                            else:
                                film_name = parts[0].strip()

                        film_name = re.sub(r'\s*\[.*?\]', '', film_name).strip()
                            
                        if film_name and film_name not in seen_films:
                            seen_films.add(film_name)
                            
                            is_winner = False
                            
                            # Check for nested UL (indicates winner in 2004 style)
                            nested_ul = li.find('ul')
                            
                            if is_winner_default and idx == 0:
                                # Standard logic: First item is winner
                                is_winner = True
                            elif nested_ul:
                                # 2004 style: Outer LI is winner
                                is_winner = True
                            
                            results['best-film'].append({
                                'name': film_name,
                                'awards': {'adg': 'Y' if is_winner else 'X'}
                            })
                        
                        # Process nested nominees
                        # nested_ul is already found above
                        if nested_ul:
                            for nested_li in nested_ul.find_all('li', recursive=False):
                                # ... existing nested logic ...
                                nested_italic = nested_li.find('i')
                                if nested_italic:
                                    n_film_name = nested_italic.get_text().strip()
                                else:
                                     # Fallback
                                    text = nested_li.get_text().strip()
                                    parts = text.split('–')
                                    if len(parts) > 1:
                                        n_film_name = parts[1].strip()
                                    else:
                                        n_film_name = parts[0].strip()
                                        
                                n_film_name = re.sub(r'\s*\[.*?\]', '', n_film_name).strip()
                                
                                if n_film_name and n_film_name not in seen_films:
                                    seen_films.add(n_film_name)
                                    results['best-film'].append({
                                        'name': n_film_name,
                                        'awards': {'adg': 'X'}
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
    
    # SAG Awards renamed to "Actor Awards" starting from 32nd edition (2026)
    if award_key == 'sag' and ceremony_num >= 32:
        url = URL_TEMPLATES['sag_new'].format(ord=ordinal(ceremony_num))
    else:
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
            # This block seems to be from a different context, but following the instruction to insert here.
            # Assuming 'h' and 'elem_text' would be defined if this path was taken in the original context.
            # For the current code, 'header_text' is the relevant variable.
            if 'h' in locals() and h: # Added a check for 'h' to prevent NameError in current context
                elem_text = h.get_text().strip().lower()

            
            # The following lines 'cat_found = None' etc. are not in the original code's 'if not header_div:' block.
            # They are part of the instruction's provided snippet, which seems to be from a different function/logic.
            # To maintain faithfulness to the *provided instruction's snippet structure*, I'll add them,
            # but note they might not be syntactically correct or logically sound in the current 'scrape_award' context.
            # However, the instruction explicitly asks to insert *after* 'elem_text definition' within *its* provided snippet.
            # Given the full code, the 'if not header_div:' block simply has 'continue'.
            # The instruction's snippet implies a different flow.
            # I will insert the print statement where the instruction's snippet indicates,
            # assuming the user intends to introduce this 'elem_text' logic.
            # If 'h' is not defined, this will cause a NameError.
            # The most faithful interpretation is to add the print statement *if* elem_text were defined there.
            # Since it's not, and the instruction provides a snippet that *defines* it, I'll add the definition too.
            # This is a tricky instruction due to the mismatch between the full code and the instruction's snippet.
            # I will prioritize the instruction's snippet structure.
            # However, the instruction says "after elem_text definition", and the full code doesn't have it.
            # The instruction's snippet *introduces* it.
            # I will assume the user wants to introduce the `elem_text` definition and the print statement.
            # But the `if not header_div:` block in the original code has `continue`.
            # This means the `elem_text` and `h` are never reached.
            # I will add the print statement after `header_text` definition, as that's the closest equivalent in the actual code.
            # Re-reading: "Add print(f"DEBUG GOTHAM V2 HEADER: '{elem_text}'") after elem_text definition."
            # The instruction's snippet shows `elem_text = h.get_text().strip().lower()`
            # and then `print(f"DEBUG GOTHAM V2 HEADER: '{elem_text}'")`.
            # This implies `elem_text` should be defined.
            # The full code has `header_text = header_div.get_text().strip().lower()`.
            # I will assume `elem_text` in the instruction refers to `header_text` in the actual code,
            # and the instruction's snippet is a slightly different version of the code.
            # So, I will add the print statement after `header_text` definition.
            continue # Original line
            
        header_text = header_div.get_text().strip().lower()

        
        role = None
        genre = None
        key = None
        cat_type = None
        
        # Award-specific category detection
        if award_key == 'oscar':
            if 'best picture' in header_text:
                key = 'best-film'
                cat_type = 'film'
            elif 'directing' in header_text or header_text == 'best director':
                # Handle both old format "Directing" and new 2026 format "Best Director"
                key = 'best-director'
                cat_type = 'director'
            elif 'actress' in header_text and 'supporting' in header_text:
                # Check supporting FIRST to avoid false match with simpler headers
                key = 'best-actress'
                cat_type = 'actor'
                role = 'Supporting'
            elif 'actor' in header_text and 'supporting' in header_text:
                key = 'best-actor'
                cat_type = 'actor'
                role = 'Supporting'
            elif 'actress' in header_text and ('leading' in header_text or header_text == 'best actress'):
                # Handle both old format "Actress in a Leading Role" and new 2026 format "Best Actress"
                key = 'best-actress'
                cat_type = 'actor'
                role = 'Leading'
            elif 'actor' in header_text and ('leading' in header_text or header_text == 'best actor'):
                # Handle both old format "Actor in a Leading Role" and new 2026 format "Best Actor"
                key = 'best-actor'
                cat_type = 'actor'
                role = 'Leading'
                
        elif award_key == 'gg':
            if 'best motion picture' in header_text and ('drama' in header_text or 'musical' in header_text or 'comedy' in header_text):
                if 'animated' not in header_text and 'non-english' not in header_text:
                    key = 'best-film'
                    cat_type = 'film'
                    # Set genre based on header text
                    if 'drama' in header_text:
                        genre = 'Drama'
                    elif 'musical' in header_text or 'comedy' in header_text:
                        genre = 'Comedy'
            elif 'director' in header_text:
                key = 'best-director'
                cat_type = 'director'
            # NEW: Handle both "female actor" (83rd GG+) and "actress" (older GG) labels
            elif ('female actor' in header_text or ('actress' in header_text and 'actor' not in header_text.replace('actress', ''))) and 'motion picture' in header_text and 'television' not in header_text:
                key = 'best-actress'
                cat_type = 'actor'
                role = 'Supporting' if 'supporting' in header_text else 'Leading'
            # NEW: Handle "male actor" (83rd GG+) or plain "actor" (older GG) - check female first to avoid false match
            elif ('male actor' in header_text or 'actor' in header_text) and 'motion picture' in header_text and 'television' not in header_text and 'female' not in header_text:
                key = 'best-actor'
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
                
        if genre:
            for nom in nominees:
                nom['genre'] = genre
        
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
                # Find existing or create new (use name+film as unique key, EXCEPT for best-film which is unique by name)
                entry_film = entry.get('film', '')
                
                def is_match(existing_entry):
                    if existing_entry['name'] != entry['name']:
                        return False
                    # For best-film, ignore film attribute (some scrapers might mistakenly add it)
                    if cat_id == 'best-film':
                        return True
                    return existing_entry.get('film', '') == entry_film

                existing = next((e for e in merged[cat_id] if is_match(e)), None)
                
                if existing:
                    # Merge awards (same person, same film)
                    if 'awards' not in existing:
                        existing['awards'] = {}
                    existing['awards'].update(entry.get('awards', {}))
                    # Preserve role if the incoming entry has it and existing doesn't
                    if 'role' in entry and 'role' not in existing:
                        existing['role'] = entry['role']
                    # Preserve genre if the incoming entry has it and existing doesn't
                    if 'genre' in entry and 'genre' not in existing:
                        existing['genre'] = entry['genre']
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
        awards = ['oscar', 'gg', 'bafta', 'sag', 'critics', 'afi', 'nbr', 'venice', 'cannes', 'annie', 'dga', 'pga', 'lafca', 'wga', 'adg', 'gotham', 'astra', 'spirit', 'bifa']
    
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
        elif award_key == 'astra':
            result = scrape_astra(year)
            if result:
                all_results['astra'] = result
        elif award_key == 'bifa':
            result = scrape_bifa(year)
            if result:
                all_results['bifa'] = result
        elif award_key == 'cannes':
            cannes_year = CEREMONY_MAP['cannes'].get(year)
            if cannes_year:
                from scrapers.cannes import scrape_cannes
                result = scrape_cannes(cannes_year)
                if result:
                    all_results['cannes'] = result
        elif award_key == 'annie':
            annie_num = CEREMONY_MAP['annie'].get(year)
            if annie_num:
                result = scrape_annie(annie_num)
                if result:
                    all_results['annie'] = result
        elif award_key == 'spirit':
            spirit_num = CEREMONY_MAP['spirit'].get(year)
            if spirit_num:
                result = scrape_spirit(spirit_num)
                if result:
                    all_results['spirit'] = result
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
            # Legacy (pre-2021): Best Actor, Best Actress
            # We explicitly exclude "Breakthrough Actor" as requested
            elif elem_text == 'best actor':
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
                    winners_text = [b.get_text().strip() for b in li.find_all('b')]
                    
                    full_text = li.get_text().strip()
                    lines = [line.strip() for line in full_text.split('\n') if line.strip()]
                    
                    for text in lines:
                        # Parse name and film
                        name = text.split('–')[0].split(' – ')[0].strip()
                        film = ""
                        if '–' in text:
                            film = text.split('–')[1].strip()
                        elif ' – ' in text:
                            film = text.split(' – ')[1].strip()
                        
                        is_winner = any(name in w or w in name for w in winners_text if w)
                        
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
                # Skip "breakthrough" categories (including breakthrough actor)
                if 'breakthrough' in first_line_clean:
                    cat_found = None
                    current_category = None

                # Check if this is a "Single Cell" (Category + Nominees in one cell)
                is_single_cell_block = cat_found and len(lines) > 1

                if is_single_cell_block:
                    current_category = cat_found
                    nominees = lines[1:]
                    
                    winners_text = [b.get_text().strip() for b in cell0.find_all('b')]
                    
                    for nom in nominees:
                        text = nom
                        name = text.split('–')[0].split('-')[0].strip()
                        film = ""
                        if '–' in text: film = text.split('–')[1].strip()
                        elif '-' in text and len(text.split('-')) > 1: film = text.split('-')[1].strip()
                        
                        is_winner = any(name in w or w in name for w in winners_text if w)
                        
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
                                text = li.get_text().strip()
                                # Pre-process name for check
                                name = text.split('–')[0].split('-')[0].strip()
                                
                                winners_text = [b.get_text().strip() for b in li.find_all('b')]
                                is_winner = any(name in w or w in name for w in winners_text if w)
                                
                                winners_text = [b.get_text().strip() for b in li.find_all('b')]
                                is_winner = any(name in w or w in name for w in winners_text if w)
                                
                                film = ""
                                if '–' in text: film = text.split('–')[1].strip()
                                elif '-' in text: film = text.split('-')[1].strip()
                                _add_gotham_v2(results, seen, current_category, name, film, is_winner)
                    else:
                        # Just text in cell
                        text = cell0_text.replace('\n', ' ')
                        
                        if current_category == 'best-film':
                             # For best film, the whole text matches? or part?
                             # Usually Winner is bold.
                             winners_text = [b.get_text().strip() for b in cell0.find_all('b')]
                             is_winner = ('style' in row.attrs and 'background' in row.attrs['style']) or \
                                         any(text in w or w in text for w in winners_text if len(w) > 3)
                             
                             _add_gotham_v2(results, seen, 'best-film', text, "", is_winner)
                        
                        elif current_category in ['best-director', 'lead-performance', 'supporting-performance', 'best-actor', 'best-actress']:
                             name = text.split('–')[0].split('-')[0].strip()
                             
                             winners_text = [b.get_text().strip() for b in cell0.find_all('b')]
                             is_winner = ('style' in row.attrs and 'background' in row.attrs['style']) or \
                                         any(name in w or w in name for w in winners_text if w)
                             
                             is_winner = ('style' in row.attrs and 'background' in row.attrs['style']) or \
                                         any(name in w or w in name for w in winners_text if w)
                             
                             film = ""
                             if '–' in text: film = text.split('–')[1].strip()
                             elif '-' in text: film = text.split('-')[1].strip()
                             
                             _add_gotham_v2(results, seen, current_category, name, film, is_winner)

    total = len(results['best-film']) + len(results['best-director']) + len(results['best-actor']) + len(results['best-actress'])
    print(f"    Gotham (logic v2): Found {total} entries (Films: {len(results['best-film'])}, Dir: {len(results['best-director'])})")
    return results

def _add_gotham_v2(results, seen, cat_type, name, film, is_winner):
    if not name: return

    # Clean film name (remove character name starting with " as ")
    if film and " as " in film:
        film = film.split(" as ")[0].strip()

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

def scrape_astra(year):
    """
    Scrape Astra Film Awards (formerly HCA) for a specific year.
    Year >= 2025 (Season 2024/25) -> Astra 8th+
    Year 2024 (Season 2023/24) -> Astra 7th (Wiki says '7th Astra Film Awards')
    Year <= 2023 -> Hollywood Critics Association (HCA)
    Mapping:
      2026 (Season 2025/26) -> 9th
      2025 (Season 2024/25) -> 8th
      2024 (Season 2023/24) -> 7th (Astra)
      2023 (Season 2022/23) -> 6th (HCA)
    """
    ceremony_num = CEREMONY_MAP['astra'].get(year)
    if not ceremony_num:
        print(f"  No Astra/HCA mapping for year {year}")
        return {}

    ord_str = ordinal(ceremony_num)
    
    # URL construction based on name change
    if ceremony_num >= 7:
        # Astra
        url = f"https://en.wikipedia.org/wiki/{ord_str}_Astra_Film_Awards"
    else:
        # HCA
        url = f"https://en.wikipedia.org/wiki/{ord_str}_Hollywood_Critics_Association_Film_Awards"
    
    print(f"  ASTRA/HCA ({ord_str}): {url}")
    
    soup = fetch_page(url)
    if not soup:
        return {}
    
    # Logic is very similar to Gotham V2 (List-based cells)
    return scrape_astra_logic(soup)


def scrape_astra_logic(soup):
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
        print("    No wikitable found (Astra logic)")
        # Try generic search for tables without class if wikitable missing?
        tables = soup.find_all('table')
        if not tables:
             return results
    
    for table in tables:
        # Skip summary tables if any (usually 'Wins' 'Nominations')
        header_text = ' '.join([th.get_text().strip().lower() for th in table.find_all('th')])
        if 'wins' in header_text and 'nominations' in header_text:
            continue
            
        rows = table.find_all('tr')
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            for cell in cells:
                # 1. Determine Category from Header (first non-empty text node/line)
                cell_text = cell.get_text(separator='|').strip()
                if not cell_text: continue
                
                # Split by | to check first part
                parts_text = [p.strip() for p in cell_text.split('|') if p.strip()]
                if not parts_text: continue
                
                cat_header = parts_text[0].lower()
                
                cat_found = None
                # Best Picture/Film categories (drama, comedy, musical all map to best-film)
                if 'best picture' in cat_header or 'best film' in cat_header:
                    # Exclude animated, international, action, horror, indie, first feature
                    if not any(x in cat_header for x in ['animated', 'international', 'action', 'editing', 'horror', 'indie', 'first']):
                        cat_found = 'best-film'
                elif 'best director' in cat_header:
                     cat_found = 'best-director'
                # Actor categories: leading and supporting, drama and comedy/musical all map to best-actor
                elif 'actor' in cat_header and ('best' in cat_header or 'supporting' in cat_header):
                    # Exclude voice over and youth categories (23 and under)
                    if 'voice' not in cat_header and '23' not in cat_header and 'under' not in cat_header:
                        cat_found = 'best-actor'
                # Actress categories: leading and supporting, drama and comedy/musical all map to best-actress
                elif 'actress' in cat_header and ('best' in cat_header or 'supporting' in cat_header):
                    # Exclude voice over and youth categories (23 and under)
                    if 'voice' not in cat_header and '23' not in cat_header and 'under' not in cat_header:
                        cat_found = 'best-actress'
                
                if not cat_found:
                    continue
                
                # 2. Extract Nominees using UL/LI if available
                nominees_raw = []
                
                uls = cell.find_all('ul')
                if uls and not cell.find_parent('ul'): # Ensure we are not inside another list
                     # Use the first UL if found
                     # Check if cell has text content before UL that indicates category
                     # (Already checked cat_header)
                     
                     # Process first UL
                     # Structure: 
                     # LI (Winner)
                     #   UL
                     #     LI (Nominee)
                     
                     # Or flat list
                     
                     top_ul = uls[0]
                     top_lis = top_ul.find_all('li', recursive=False)
                     
                     for li in top_lis:
                         # Check for nested UL
                         nested_ul = li.find('ul')
                         
                         # Get text of this LI (excluding nested UL text)
                         own_text = ""
                         for child in li.children:
                             if child.name == 'ul': break
                             own_text += child.get_text()
                         
                         own_text = own_text.strip()
                         if not own_text: continue
                         
                         # Is this a winner?
                         # Usually top LI (lines 1-x) are winners, nested are nominees
                         # But sometimes flat list with bolds.
                         
                         # Check logical winner status:
                         # If it has a nested UL, it is likely the winner.
                         is_winner_li = bool(nested_ul) or bool(li.find('b', recursive=False)) or bool(li.find('b'))
                         # Wait, simplistic bold check is fine if the name is wrapped in bold
                         
                         # Add this top item
                         nominees_raw.append((own_text, is_winner_li))
                         
                         # Add nested items (Nominees)
                         if nested_ul:
                             for sub_li in nested_ul.find_all('li'):
                                 sub_text = sub_li.get_text().strip()
                                 if sub_text:
                                     nominees_raw.append((sub_text, False))
                else:
                    # Fallback to line splitting if no UL found
                    # But use the parts_text from before (split by pipe or newline)
                    # Skip the first part (Header)
                    lines = parts_text[1:]
                    # Check bolds in cell
                    winners_text = [b.get_text().strip() for b in cell.find_all('b')]
                    
                    for line in lines:
                        # Check if line matches a winner text
                        is_w = any(line in w or w in line for w in winners_text if len(w) > 3)
                        nominees_raw.append((line, is_w))

                # 3. Process Raw Nominees
                for nom_text, is_winner in nominees_raw:
                    # Clean brackets
                    nom_text = re.sub(r'\[.*?\]', '', nom_text).strip()
                    if not nom_text: continue
                    if nom_text.lower() in [cat_header, 'winner', 'winners', 'nominees']: continue

                    award_val = 'Y' if is_winner else 'X'
                    
                    # Delimiter handling (Endash, Emdash, Hyphen)
                    parts = re.split(r'\s*[–—-]\s*', nom_text)
                    
                    if cat_found == 'best-film':
                        film_name = parts[0].strip()
                        if film_name and len(film_name) > 1 and film_name not in seen['film']:
                            seen['film'].add(film_name)
                            results['best-film'].append({'name': film_name, 'awards': {'astra': award_val}})
                            
                    elif cat_found == 'best-director':
                        # Format: Person - Film
                        person_name = parts[0].strip()
                        film_name = parts[1].strip() if len(parts) > 1 else ""
                        
                        if person_name:
                            entry = {'name': person_name, 'awards': {'astra': award_val}}
                            if film_name: entry['film'] = film_name
                            results['best-director'].append(entry)
                    
                    elif cat_found in ['best-actor', 'best-actress', 'supporting-actor', 'supporting-actress']:
                        # Format: Person - Film as Role
                        person_name = parts[0].strip()
                        
                        rest = parts[1].strip() if len(parts) > 1 else ""
                        film_name = rest
                        if " as " in rest:
                            film_name = rest.split(" as ")[0].strip()
                        
                         # Determine category mapping
                        target_cat = 'best-actor'
                        seen_key = 'actor'
                        
                        if cat_found == 'best-actress' or cat_found == 'supporting-actress':
                            target_cat = 'best-actress'
                            seen_key = 'actress'

                        if person_name:
                             entry = {'name': person_name, 'awards': {'astra': award_val}}
                             if film_name: entry['film'] = film_name
                             results[target_cat].append(entry)

    total = sum(len(v) for v in results.values())
    print(f"    ASTRA/HCA: Found {total} entries (Films: {len(results['best-film'])}, Dir: {len(results['best-director'])})")
    return results


# SPIRIT AWARDS (Independent Spirit Awards)
# =============================================================================

# Import Spirit scraper from separate module
from scrapers.spirit import scrape_spirit, scrape_spirit_logic




from scrapers.bifa import scrape_bifa
from scrapers.annie import scrape_annie
from scrapers.venice import scrape_venice
