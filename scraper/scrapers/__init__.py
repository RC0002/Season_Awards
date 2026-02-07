# -*- coding: utf-8 -*-
"""
Shared utilities for award scrapers
"""

import requests
from bs4 import BeautifulSoup

TMDB_API_KEY = "4399b8147e098e80be332f172d1fe490"
TMDB_BASE_URL = "https://api.themoviedb.org/3"

# ============ YEAR TO CEREMONY MAPPING ============
CEREMONY_MAP = {
    'oscar': {
        2026: 98, 2025: 97, 2024: 96, 2023: 95, 2022: 94, 2021: 93,
        2020: 92, 2019: 91, 2018: 90, 2017: 89, 2016: 88,
        2015: 87, 2014: 86, 2013: 85
    },
    'gg': {
        2026: 83, 2025: 82, 2024: 81, 2023: 80, 2022: 79, 2021: 78,
        2020: 77, 2019: 76, 2018: 75, 2017: 74, 2016: 73,
        2015: 72, 2014: 71, 2013: 70
    },
    'bafta': {
        2026: 79, 2025: 78, 2024: 77, 2023: 76, 2022: 75, 2021: 74,
        2020: 73, 2019: 72, 2018: 71, 2017: 70, 2016: 69,
        2015: 68, 2014: 67, 2013: 66
    },
    'sag': {
        2026: 32, 2025: 31, 2024: 30, 2023: 29, 2022: 28, 2021: 27,
        2020: 26, 2019: 25, 2018: 24, 2017: 23, 2016: 22,
        2015: 21, 2014: 20, 2013: 19
    },
    'critics': {
        2026: 31, 2025: 30, 2024: 29, 2023: 28, 2022: 27, 2021: 26,
        2020: 25, 2019: 24, 2018: 23, 2017: 22, 2016: 21,
        2015: 20, 2014: 19, 2013: 18, 2012: 17, 2011: 16, 2010: 15,
        2009: 14, 2008: 13, 2007: 12, 2006: 11, 2005: 10, 2004: 9,
        2003: 8, 2002: 7, 2001: 6
    },
    'afi': {
        2026: 2025, 2025: 2024, 2024: 2023, 2023: 2022, 2022: 2021, 2021: 2020,
        2020: 2019, 2019: 2018, 2018: 2017, 2017: 2016, 2016: 2015,
        2015: 2014, 2014: 2013, 2013: 2012
    },
    'nbr': {
        2026: 2025, 2025: 2024, 2024: 2023, 2023: 2022, 2022: 2021, 2021: 2020,
        2020: 2019, 2019: 2018, 2018: 2017, 2017: 2016, 2016: 2015,
        2015: 2014, 2014: 2013, 2013: 2012
    },
    'venice': {
        2026: 82, 2025: 81, 2024: 80, 2023: 79, 2022: 78, 2021: 77,
        2020: 76, 2019: 75, 2018: 74, 2017: 73, 2016: 72,
        2015: 71, 2014: 70, 2013: 69, 2012: 68, 2011: 67, 2010: 66,
        2009: 65, 2008: 64, 2007: 63, 2006: 62, 2005: 61, 2004: 60,
        2003: 59, 2002: 58, 2001: 57
    },
    'dga': {
        2026: 2025, 2025: 2024, 2024: 2023, 2023: 2022, 2022: 2021, 2021: 2020,
        2020: 2019, 2019: 2018, 2018: 2017, 2017: 2016, 2016: 2015,
        2015: 2014, 2014: 2013, 2013: 2012
    },
    'pga': {
        2026: 37, 2025: 36, 2024: 35, 2023: 34, 2022: 33, 2021: 32,
        2020: 31, 2019: 30, 2018: 29, 2017: 28, 2016: 27,
        2015: 26, 2014: 25, 2013: 24
    },
    'lafca': {
        2026: 2025, 2025: 2024, 2024: 2023, 2023: 2022, 2022: 2021, 2021: 2020,
        2020: 2019, 2019: 2018, 2018: 2017, 2017: 2016, 2016: 2015,
        2015: 2014, 2014: 2013, 2013: 2012
    },
    'wga': {
        2026: 77, 2025: 76, 2024: 75, 2023: 74, 2022: 73, 2021: 72,
        2020: 71, 2019: 70, 2018: 69, 2017: 68, 2016: 67,
        2015: 66, 2014: 65, 2013: 64
    },
    'adg': {
        2026: 2025, 2025: 2024, 2024: 2023, 2023: 2022, 2022: 2021, 2021: 2020,
        2020: 2019, 2019: 2018, 2018: 2017, 2017: 2016, 2016: 2015,
        2015: 2014, 2014: 2013, 2013: 2012
    },
    'gotham': {
        2026: 2025, 2025: 2024, 2024: 2023, 2023: 2022, 2022: 2021, 2021: 2020,
        2020: 2019, 2019: 2018, 2018: 2017, 2017: 2016, 2016: 2015,
        2015: 2014, 2014: 2013, 2013: 2012, 2012: 2011, 2011: 2010, 2010: 2009,
        2009: 2008, 2008: 2007, 2007: 2006, 2006: 2005, 2005: 2004, 2004: 2003,
        2003: 2002, 2002: 2001, 2001: 2000
    },
    'astra': {
        2026: 9, 2025: 8, 2024: 7, 2023: 6, 2022: 5, 2021: 4,
        2020: 3, 2019: 2, 2018: 1
    },
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
    'cannes': {
        2026: 2025, 2025: 2024, 2024: 2023, 2023: 2022, 2022: 2021, 2021: 2020,
        2020: 2019, 2019: 2018, 2018: 2017, 2017: 2016, 2016: 2015,
        2015: 2014, 2014: 2013, 2013: 2012, 2012: 2011, 2011: 2010, 2010: 2009,
        2009: 2008, 2008: 2007, 2007: 2006, 2006: 2005, 2005: 2004, 2004: 2003,
        2003: 2002, 2002: 2001, 2001: 2000
    },
    'annie': {
        2026: 53, 2025: 52, 2024: 51, 2023: 50, 2022: 49, 2021: 48,
        2020: 47, 2019: 46, 2018: 45, 2017: 44, 2016: 43,
        2015: 42, 2014: 41, 2013: 40
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
    'lafca': 'https://en.wikipedia.org/wiki/{year}_Los_Angeles_Film_Critics_Association_Awards',
    'wga': 'https://en.wikipedia.org/wiki/{ord}_Writers_Guild_of_America_Awards',
    'adg': 'https://en.wikipedia.org/wiki/Art_Directors_Guild_Awards_{year}',
    'gotham': 'https://en.wikipedia.org/wiki/Gotham_Independent_Film_Awards_{year}',
    'astra': 'https://en.wikipedia.org/wiki/{ord}_Astra_Film_Awards',
    'spirit': 'https://en.wikipedia.org/wiki/{ord}_Independent_Spirit_Awards',
    'bifa': 'https://en.wikipedia.org/wiki/British_Independent_Film_Awards_{year}',
    'nyfcc': 'https://en.wikipedia.org/wiki/{year}_New_York_Film_Critics_Circle_Awards'
}


def ordinal(n):
    """Convert number to ordinal (1st, 2nd, 3rd, etc.)"""
    suffix = 'th' if 11 <= n % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"


def fetch_page(url):
    """Fetch and parse a webpage"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"    Error: HTTP {response.status_code}")
        return None
    return BeautifulSoup(response.text, 'html.parser')


def parse_nominees_from_cell(cell, category_type, award_name):
    """Parse nominees from a wikitable cell - shared utility"""
    nominees = []
    seen_entries = set()
    
    skip_words = ['Academy Award', 'Golden Globe', 'BAFTA', 'Screen Actors Guild',
                  'Critics', 'Outstanding', 'Best ']
    
    # Check for winners in bold text before list
    for bold in cell.find_all('b', recursive=True):
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
        
        film = None
        if category_type in ['director', 'actor']:
            all_links = bold.find_all('a')
            for link in all_links[1:]:
                link_text = link.get_text().strip()
                link_title = link.get('title', '')
                if link_text and len(link_text) > 1 and not any(w in link_title for w in skip_words):
                    film = link_text
                    break
        
        entry_key = (name, film) if film else (name, None)
        if entry_key not in seen_entries:
            seen_entries.add(entry_key)
            if film:
                nominees.append({'name': name, 'film': film, 'winner': True})
            else:
                nominees.append({'name': name, 'winner': True})
    
    # Process LI elements
    for li in cell.find_all('li', recursive=False):
        first_link = li.find('a')
        if not first_link:
            continue
        
        link_title = first_link.get('title', '') or ''
        if any(w in link_title for w in skip_words):
            continue
        
        name = first_link.get_text().strip()
        if len(name) < 2:
            continue
        
        is_winner = bool(li.find('b') or li.find('strong'))
        
        film = None
        if category_type in ['director', 'actor']:
            all_links = li.find_all('a')
            for link in all_links[1:]:
                link_text = link.get_text().strip()
                link_title = link.get('title', '')
                if link_text and len(link_text) > 1 and not any(w in link_title for w in skip_words):
                    film = link_text
                    break
        
        entry_key = (name, film) if film else (name, None)
        if entry_key not in seen_entries:
            seen_entries.add(entry_key)
            if film:
                nominees.append({'name': name, 'film': film, 'winner': is_winner})
            else:
                nominees.append({'name': name, 'winner': is_winner})
    
    return nominees


def init_results():
    """Initialize empty results dictionary"""
    return {
        'best-film': [],
        'best-director': [],
        'best-actor': [],
        'best-actress': []
    }


def get_person_gender(name):
    """Get gender of a person using TMDB API. Returns: 1 = Female, 2 = Male, 0 = Unknown"""
    try:
        url = f"{TMDB_BASE_URL}/search/person"
        params = {'api_key': TMDB_API_KEY, 'query': name}
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            results = response.json().get('results', [])
            if results:
                return results[0].get('gender', 0)
    except:
        pass
    return 0

