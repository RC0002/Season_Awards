# -*- coding: utf-8 -*-
"""
GG Awards Scraper
"""

from . import CEREMONY_MAP, URL_TEMPLATES, fetch_page, ordinal, init_results

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


