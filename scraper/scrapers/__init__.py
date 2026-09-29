# -*- coding: utf-8 -*-
"""
Shared utilities and configuration for award scrapers.

This package is the single source of truth for CEREMONY_MAP and URL_TEMPLATES.
"""

import os
import re
import time
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup

# TMDB v3 key (read-only, also used client-side). Override with the TMDB_API_KEY env var.
TMDB_API_KEY = os.environ.get('TMDB_API_KEY', "4399b8147e098e80be332f172d1fe490")
TMDB_BASE_URL = "https://api.themoviedb.org/3"

# ============ YEAR TO CEREMONY MAPPING ============
# Season year is the SECOND year (e.g., 2024/25 season = year 2025).
# Every award follows a fixed offset from the season year, so the map is
# generated instead of hand-maintained: a new season only needs LAST_SEASON bumped
# (or nothing at all, since it follows the calendar).

FIRST_SEASON = 2001


SEASON_START_MONTH = 9  # September (Venice). Keep in sync with SEASON_START_MONTH in app.js


def current_season_year():
    """Season end year: Sep-Dec belongs to the next ceremony year (e.g. Sep 2025 -> 2026)."""
    from datetime import date
    today = date.today()
    return today.year + 1 if today.month >= SEASON_START_MONTH else today.year


# Map through the season after the current one, so upcoming ceremonies are always covered.
LAST_SEASON = current_season_year() + 1

# award -> (offset, first season year available). Value = season_year - offset.
_CEREMONY_OFFSETS = {
    'oscar': (1928, FIRST_SEASON),     # 97th Academy Awards = 2025
    'gg': (1943, FIRST_SEASON),        # 82nd Golden Globes = 2025
    'bafta': (1947, FIRST_SEASON),     # 78th BAFTA = 2025
    'sag': (1994, FIRST_SEASON),       # 31st SAG = 2025 (renamed "Actor Awards" from 32nd)
    'critics': (1995, FIRST_SEASON),   # 30th Critics' Choice = 2025
    'afi': (1, FIRST_SEASON),          # AFI Awards <film year>
    'nbr': (1, FIRST_SEASON),          # NBR Awards <film year>
    'venice': (1944, FIRST_SEASON),    # 81st Venice (Sept 2024) = season 2024/25
    'pga': (1989, FIRST_SEASON),       # 36th PGA = 2025
    'lafca': (1, FIRST_SEASON),        # <film year> LAFCA
    'wga': (1948, FIRST_SEASON),       # 77th WGA = 2025
    'adg': (1, FIRST_SEASON),          # ADG Awards <film year>
    'gotham': (1, FIRST_SEASON),       # Gotham <film year>
    'annie': (1973, FIRST_SEASON),     # 52nd Annie = 2025
    'astra': (2017, 2018),             # 8th Astra = 2025 (formerly HCA, started 2018)
    'spirit': (1985, FIRST_SEASON),    # 40th Spirit = 2025
    'bifa': (1, FIRST_SEASON),         # BIFA <film year>
    'cannes': (1, FIRST_SEASON),       # Cannes 2025 (May) = season 2025/26
    'nyfcc': (1, FIRST_SEASON),        # <film year> NYFCC
}

# DGA: 2026+ uses ordinal edition numbers (Wikipedia scraping, 78th = 2026).
# Historical years (pre-2026) use the film year (dga_awards.json fallback).
DGA_WIKIPEDIA_FROM = 2026


def _build_ceremony_map():
    ceremony_map = {}
    for award, (offset, first) in _CEREMONY_OFFSETS.items():
        ceremony_map[award] = {y: y - offset for y in range(first, LAST_SEASON + 1)}
    ceremony_map['dga'] = {
        y: (y - 1948 if y >= DGA_WIKIPEDIA_FROM else y - 1)
        for y in range(FIRST_SEASON, LAST_SEASON + 1)
    }
    return ceremony_map


CEREMONY_MAP = _build_ceremony_map()

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
    'astra': 'https://en.wikipedia.org/wiki/{ord}_Astra_Film_Awards',
    'spirit': 'https://en.wikipedia.org/wiki/{ord}_Independent_Spirit_Awards',
    'bifa': 'https://en.wikipedia.org/wiki/British_Independent_Film_Awards_{year}',
    'nyfcc': 'https://en.wikipedia.org/wiki/{year}_New_York_Film_Critics_Circle_Awards'
}


def ordinal(n):
    """Convert number to ordinal (1st, 2nd, 3rd, etc.)"""
    suffix = 'th' if 11 <= n % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"


HTTP_HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}


def fetch_page(url, retries=2, timeout=30):
    """Fetch and parse a webpage (retries on network errors, returns None on failure)"""
    for attempt in range(retries + 1):
        try:
            response = requests.get(url, headers=HTTP_HEADERS, timeout=timeout)
        except requests.RequestException as e:
            print(f"    Error: {e}")
            if attempt < retries:
                time.sleep(2 * (attempt + 1))
                continue
            return None
        if response.status_code != 200:
            print(f"    Error: HTTP {response.status_code}")
            return None
        soup = BeautifulSoup(response.text, 'html.parser')
        target = edition_redirect_target(url, soup)
        if target:
            print(f"    Page not published yet: redirects to '{target}'")
            return None
        return soup
    return None


# Edition markers in a Wikipedia title: ordinals ("54th") and years ("2026")
_EDITION_TOKEN = re.compile(r'\b(\d+(?:st|nd|rd|th)|(?:19|20)\d{2})\b')


def edition_redirect_target(url, soup):
    """
    Wikipedia serves redirects with HTTP 200, so a ceremony page that doesn't exist yet
    (e.g. "54th_Annie_Awards" -> "Annie_Award") would be parsed as the generic award page.
    Returns the redirect target title if it lost the requested edition, else None.
    Renames that keep the edition (e.g. "31st Screen Actors Guild Awards" -> "31st Actor Awards") pass.
    """
    if not soup.find(class_='mw-redirectedfrom'):
        return None
    canonical = soup.find('link', rel='canonical')
    if not canonical or not canonical.get('href'):
        return None
    requested = unquote(url.rsplit('/wiki/', 1)[-1]).replace('_', ' ')
    target = unquote(canonical['href'].rsplit('/wiki/', 1)[-1]).replace('_', ' ')
    tokens = _EDITION_TOKEN.findall(requested)
    if tokens and not all(t in _EDITION_TOKEN.findall(target) for t in tokens):
        return target
    return None


def own_text(li):
    """
    Text of a list item without its nested lists. On Wikipedia the winner's <li> often
    contains the other nominees as a nested <ul>, whose text must not leak into the winner.
    """
    parts = []
    for node in li.children:
        if getattr(node, 'name', None) in ('ul', 'ol'):
            continue
        parts.append(node.get_text(separator=' ') if hasattr(node, 'get_text') else str(node))
    return ' '.join(' '.join(parts).split())


def init_results():
    """Initialize empty results dictionary"""
    return {
        'best-film': [],
        'best-director': [],
        'best-actor': [],
        'best-actress': []
    }


# Hardcoded gender for performers where TMDB is unreliable (1=Female, 2=Male)
KNOWN_GENDER = {
    # 2025 Gotham
    'Sopé Dìrísù': 2, 'Jessie Buckley': 1, 'Rose Byrne': 1,
    'Lee Byung-hun': 2, 'Ethan Hawke': 2, 'Jennifer Lawrence': 1,
    'Wagner Moura': 2, "Josh O'Connor": 2, 'Amanda Seyfried': 1,
    'Tessa Thompson': 1, 'Wunmi Mosaku': 1, 'Benicio del Toro': 2,
    'Jacob Elordi': 2, 'Inga Ibsdotter Lilleaas': 1, 'Indya Moore': 1,
    'Adam Sandler': 2, 'Andrew Scott': 2, 'Alexander Skarsgård': 2,
    'Stellan Skarsgård': 2, 'Teyana Taylor': 1,
    # 2025 Spirit — Lead Performance
    'Naomi Ackie': 1, 'Everett Blunck': 2, 'Chang Chen': 2,
    'Joel Edgerton': 2, 'Dylan O\'Brien': 2, 'Théodore Pellerin': 2,
    'Ben Whishaw': 2,
    # 2025 Spirit — Supporting Performance
    'Zoey Deutch': 1, 'Kirsten Dunst': 1, 'Rebecca Hall': 1,
    'Nina Hoss': 1, 'Archie Madekwe': 2, 'Kali Reis': 1,
    'Jacob Tremblay': 2, 'Haipeng Xu': 2,
    # 2025 Spirit — Best Lead (gendered fallback)
    'Kathleen Chalfant': 1, 'Keke Palmer': 1, 'Jane Levy': 1,
}

def get_person_gender(name):
    """Get gender of a person. Checks hardcoded map first, then TMDB API.
    Returns: 1 = Female, 2 = Male, 0 = Unknown"""
    # Check hardcoded map first
    for known_name, gender in KNOWN_GENDER.items():
        if known_name.lower() == name.lower() or known_name.lower() in name.lower() or name.lower() in known_name.lower():
            return gender

    # Fallback to TMDB with retry
    import time
    for attempt in range(2):
        try:
            url = f"{TMDB_BASE_URL}/search/person"
            params = {'api_key': TMDB_API_KEY, 'query': name}
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                results = response.json().get('results', [])
                if results:
                    gender = results[0].get('gender', 0)
                    if gender in (1, 2):
                        return gender
        except Exception as e:
            print(f"    TMDB lookup failed for '{name}' (attempt {attempt+1}): {e}")
            time.sleep(1)

    print(f"    ⚠ Unknown gender for '{name}' — defaulting to actor")
    return 0

