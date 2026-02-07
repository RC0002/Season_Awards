# -*- coding: utf-8 -*-
"""
Critics' Choice Awards Scraper
Handles both modern (table-based) and old (list-based) Wikipedia formats.
"""

from . import CEREMONY_MAP, URL_TEMPLATES, ordinal, fetch_page


def scrape_critics(year):
    """Scrape Critics' Choice Awards for a given year.
    
    For older editions (roughly pre-2013), Wikipedia uses list format instead of tables.
    This function detects the format and uses appropriate parsing.
    """
    ceremony_num = CEREMONY_MAP.get('critics', {}).get(year)
    if not ceremony_num:
        print(f"  CRITICS: No ceremony mapping for year {year}")
        return {}
    
    ord_str = ordinal(ceremony_num)
    url = URL_TEMPLATES['critics'].format(ord=ord_str)
    
    print(f"  CRITICS ({ord_str}): {url}")
    
    soup = fetch_page(url)
    if not soup:
        return {}
    
    # Check if page has wikitable (modern format) or just lists (old format)
    wikitables = soup.find_all('table', class_='wikitable')
    
    # For very old editions (6th-12th), there are no wikitables with nominees
    # They use a "Top X Films" list and "Winners" bullet list format
    if ceremony_num <= 12:
        print(f"    Using old list-based format for {ord_str} Critics' Choice")
        return scrape_critics_old_format(soup, ceremony_num)
    else:
        # Modern format - use generic scrape_award from master_scraper
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from master_scraper import scrape_award
        return scrape_award('critics', year)


def scrape_critics_old_format(soup, ceremony_num):
    """
    Parse old Critics' Choice Awards pages (6th-12th editions).
    
    Structure:
    - "Top X Films" section with list of films (all count as 'Y' since it's a top list)
    - "Winners" section with bullet points like "Best Actor: Name – Film"
    - No full nominee lists for individual categories, only winners
    
    Note: Wikipedia h2 headers are inside <div class="mw-heading"> wrappers,
    so we need to navigate from the parent div to get siblings.
    """
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
    
    # ========== 1. Find "Top X Films" section ==========
    for header in soup.find_all('h2'):
        header_text = header.get_text().strip().lower()
        
        if 'top' in header_text and 'film' in header_text:
            # Navigate from parent div (mw-heading wrapper)
            parent = header.parent
            start_elem = parent if parent and parent.name == 'div' else header
            
            next_elem = start_elem.find_next_sibling()
            while next_elem:
                if next_elem.name == 'ul':
                    # Extract films from list
                    for li in next_elem.find_all('li', recursive=False):
                        link = li.find('a')
                        if link:
                            film_name = link.get_text().strip()
                        else:
                            film_name = li.get_text().strip().split('–')[0].strip()
                        
                        if len(film_name) >= 2 and film_name not in seen['best-film']:
                            seen['best-film'].add(film_name)
                            results['best-film'].append({
                                'name': film_name,
                                'awards': {'critics': 'Y'}
                            })
                    break
                elif next_elem.name == 'div' and next_elem.find('h2'):
                    # Reached next section header
                    break
                next_elem = next_elem.find_next_sibling()
    
    # ========== 2. Find "Winners" section ==========
    for header in soup.find_all('h2'):
        header_text = header.get_text().strip().lower()
        
        if 'winner' in header_text:
            parent = header.parent
            start_elem = parent if parent and parent.name == 'div' else header
            
            next_elem = start_elem.find_next_sibling()
            while next_elem:
                if next_elem.name == 'ul':
                    # Process winner entries
                    for li in next_elem.find_all('li', recursive=False):
                        li_text = li.get_text().strip()
                        
                        # Parse "Category: Name – Film" format
                        if ':' in li_text:
                            category_part, rest = li_text.split(':', 1)
                            category_part = category_part.lower().strip()
                            
                            target_cat = None
                            is_supporting = 'supporting' in category_part
                            
                            if 'director' in category_part:
                                target_cat = 'best-director'
                            elif 'actress' in category_part:
                                target_cat = 'best-actress'
                            elif 'actor' in category_part:
                                target_cat = 'best-actor'
                            
                            if target_cat:
                                rest = rest.strip()
                                
                                # Get name from first <a> link after the category span
                                all_links = li.find_all('a')
                                name = None
                                film = None
                                
                                for link in all_links:
                                    link_text = link.get_text().strip()
                                    # Skip links that are part of category name
                                    if len(link_text) >= 2 and link_text.lower() not in category_part:
                                        if name is None:
                                            name = link_text
                                        elif film is None:
                                            film = link_text
                                            break
                                
                                # Fallback: parse from text
                                if not name:
                                    if '–' in rest:
                                        name = rest.split('–')[0].strip()
                                    elif '-' in rest:
                                        name = rest.split('-')[0].strip()
                                    else:
                                        name = rest.strip()
                                
                                if not film and '–' in rest:
                                    film = rest.split('–', 1)[1].strip()
                                
                                if name and len(name) >= 2:
                                    entry_key = (name, film) if film else (name, None)
                                    if entry_key not in seen[target_cat]:
                                        seen[target_cat].add(entry_key)
                                        entry = {
                                            'name': name,
                                            'awards': {'critics': 'Y'}
                                        }
                                        if film:
                                            entry['film'] = film
                                        entry['role'] = 'Supporting' if is_supporting else 'Leading'
                                        
                                        results[target_cat].append(entry)
                    break
                elif next_elem.name == 'div' and next_elem.find('h2'):
                    break
                next_elem = next_elem.find_next_sibling()
    
    # Log results
    for cat, entries in results.items():
        if entries:
            print(f"    {cat}: {len(entries)} entries")
    
    return results
