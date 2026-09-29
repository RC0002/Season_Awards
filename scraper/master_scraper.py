# -*- coding: utf-8 -*-
"""
Master Awards Scraper
=====================
Orchestrates the per-award scrapers in scrapers/ for a given season year.
Ceremony mappings and URL templates live in scrapers/__init__.py.
"""

import json
import sys
import time

import requests

sys.stdout.reconfigure(encoding='utf-8')

from scrapers import (CEREMONY_MAP, URL_TEMPLATES, TMDB_API_KEY, TMDB_BASE_URL,
                      fetch_page, ordinal, current_season_year)
from scrapers.gg import scrape_gg_old_format
from scrapers.sag import scrape_sag_old_format
from scrapers.afi import scrape_afi
from scrapers.nbr import scrape_nbr
from scrapers.venice import scrape_venice
from scrapers.dga import scrape_dga, scrape_dga_wikipedia
from scrapers.pga import scrape_pga
from scrapers.lafca import scrape_lafca
from scrapers.wga import scrape_wga
from scrapers.adg import scrape_adg
from scrapers.gotham import scrape_gotham
from scrapers.astra import scrape_astra
from scrapers.cannes import scrape_cannes
from scrapers.nyfcc import scrape_nyfcc
from scrapers.spirit import scrape_spirit
from scrapers.bifa import scrape_bifa
from scrapers.annie import scrape_annie
from data_quality import consolidate


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
                # Fallback: film name in <i> tag without link
                if not film:
                    container = bold.parent or bold
                    i_tag = container.find('i')
                    if i_tag and not i_tag.find('a'):
                        film_text = i_tag.get_text().strip()
                        if len(film_text) > 1:
                            film = film_text
            
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
            # Fallback: film name in <i> tag without link (e.g. "Sean Penn – <i>Film</i>")
            if not film:
                i_tag = li.find('i')
                if i_tag and not i_tag.find('a'):
                    film_text = i_tag.get_text().strip()
                    if len(film_text) > 1:
                        film = film_text
        
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
            continue
            
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
                
        elif award_key == 'dga':
            if 'feature film' in header_text:
                key = 'best-director'
                cat_type = 'director'

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

    # Safety net: merge rows split by title variants / missing film (see data_quality.py)
    merged, notes = consolidate(merged)
    for note in notes:
        print(f"    🧹 {note}")

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


# Awards whose scraper takes the season year and resolves its own ceremony mapping
_SEASON_YEAR_SCRAPERS = {
    'adg': scrape_adg, 'gotham': scrape_gotham, 'astra': scrape_astra,
    'spirit': scrape_spirit, 'bifa': scrape_bifa, 'nyfcc': scrape_nyfcc,
}

# Awards whose scraper takes the mapped ceremony number / film year
_CEREMONY_SCRAPERS = {
    'afi': scrape_afi, 'nbr': scrape_nbr, 'venice': scrape_venice, 'pga': scrape_pga,
    'lafca': scrape_lafca, 'wga': scrape_wga,
    'cannes': scrape_cannes, 'annie': scrape_annie,
}

ALL_AWARDS = ['oscar', 'gg', 'bafta', 'sag', 'critics', 'afi', 'nbr', 'venice', 'cannes', 'annie',
              'dga', 'pga', 'lafca', 'nyfcc', 'wga', 'adg', 'gotham', 'astra', 'spirit', 'bifa']


def scrape_single_award(award_key, year):
    """Scrape one award for a season year using the right scraper. Returns {} if unavailable."""
    if award_key in _SEASON_YEAR_SCRAPERS:
        return _SEASON_YEAR_SCRAPERS[award_key](year) or {}

    ceremony = CEREMONY_MAP.get(award_key, {}).get(year)
    if not ceremony:
        print(f"  No mapping for {award_key} {year}")
        return {}

    if award_key == 'dga':
        # Ordinal edition (2026+) -> Wikipedia; film year (pre-2026) -> dga_awards.json fallback
        return (scrape_dga_wikipedia(ceremony) if ceremony < 100 else scrape_dga(ceremony)) or {}
    if award_key in _CEREMONY_SCRAPERS:
        return _CEREMONY_SCRAPERS[award_key](ceremony) or {}
    return scrape_award(award_key, year) or {}


def scrape_year(year, awards=None):
    """Scrape all awards for a given year"""
    if awards is None:
        awards = ALL_AWARDS
    
    print(f"\n{'='*60}")
    print(f"  SCRAPING SEASON {year-1}/{year}")
    print(f"{'='*60}")
    
    all_results = {}

    for award_key in awards:
        result = scrape_single_award(award_key, year)
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

    # Only the current season should be scraped: historical data in data/ is verified.
    # For the full pipeline (TMDB enrichment + Firebase upload) use scrape_and_upload.py.
    parser = argparse.ArgumentParser(description='Scrape awards for a season year')
    parser.add_argument('year', type=int, nargs='?', default=current_season_year(),
                        help='Season end year (e.g., 2027 for the 2026/27 season)')
    args = parser.parse_args()

    data = scrape_year(args.year)
    save_year_data(args.year, data)

    print("\n" + "="*60)
    print("  DONE!")
    print("="*60)
