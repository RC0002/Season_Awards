# -*- coding: utf-8 -*-
"""
VENICE Awards Scraper
"""

from . import CEREMONY_MAP, URL_TEMPLATES, fetch_page, ordinal, init_results

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


