# -*- coding: utf-8 -*-
"""
SAG Awards Scraper
"""

from . import CEREMONY_MAP, URL_TEMPLATES, fetch_page, ordinal, init_results

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


