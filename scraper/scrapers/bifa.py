import sys
import re
from . import CEREMONY_MAP, URL_TEMPLATES, fetch_page, get_person_gender

def scrape_bifa(year):
    """Scrape British Independent Film Awards (BIFA) from Wikipedia."""
    bifa_year = CEREMONY_MAP['bifa'].get(year)
    if not bifa_year:
        print(f"  BIFA: No year mapped for {year}")
        return {}
    
    url = URL_TEMPLATES['bifa'].format(year=bifa_year)
    print(f"  BIFA ({bifa_year}): {url}")
    
    return scrape_bifa_logic(url)


def scrape_bifa_logic(url):
    """
    Scrape BIFA categories:
    - Best British Independent Film
    - Best Director
    - Best Lead Performance
    - Best Supporting Performance
    """
    results = {
        'best-film': [],
        'best-director': [],
        'best-actor': [],
        'best-actress': []
    }
    
    try:
        soup = fetch_page(url)
        if not soup:
            return results
    except Exception as e:
        print(f"    Error: {e}")
        return results
    
    tables = soup.find_all('table', class_='wikitable')
    
    # Fallback: If no wikitables, try h3-based section parsing (older format)
    if not tables:
        results = scrape_bifa_section_format(soup)
        return results
    
    
    for table in tables:
        rows = table.find_all('tr')
        
        for row_idx in range(len(rows) - 1):
            row = rows[row_idx]
            next_row = rows[row_idx + 1]
            
            headers = row.find_all('th')
            data_cells = next_row.find_all('td')
            
            if not headers or not data_cells:
                continue
            
            for i, header in enumerate(headers):
                header_text = header.get_text(separator=' ').strip().lower()
                # print(f"DEBUG: Header '{header_text}'")
                print(f"DEBUG: Header '{header_text}'")
                
                cat_found = None
                
                if 'best british independent film' in header_text:
                    cat_found = 'best-film'
                elif 'best director' in header_text:
                    cat_found = 'best-director'
                # Exclude Joint Lead and Ensemble
                elif 'joint' in header_text or 'ensemble' in header_text:
                    continue
                # Gender-neutral categories (2022+)
                elif 'best lead performance' in header_text:
                    cat_found = 'best-actor'  # Will be split by gender detection
                elif 'best supporting performance' in header_text:
                    cat_found = 'best-actor'  # Will be split by gender detection
                # Gendered categories (pre-2022)
                elif 'best actor' in header_text and 'supporting' not in header_text:
                    cat_found = 'best-actor-direct'  # Direct assignment, no gender detection
                elif 'best actress' in header_text and 'supporting' not in header_text:
                    cat_found = 'best-actress-direct'
                elif 'best supporting actor' in header_text:
                    cat_found = 'best-actor-direct'
                elif 'best supporting actress' in header_text:
                    cat_found = 'best-actress-direct'
                
                if not cat_found or i >= len(data_cells):
                    continue
                
                cell = data_cells[i]
                
                lis = cell.find_all('li')
                for li in lis:
                    text = li.get_text(separator=' ').strip()
                    if not text:
                        continue
                    
                    is_winner = bool(li.find(['b', 'strong']))
                    
                    # Split by hyphen or en-dash
                    parts = re.split(r'\s*[–-]\s*', text)
                    if not parts:
                        continue
                        
                    name_part = parts[0].strip()
                    
                    if cat_found == 'best-film':
                        film_name = name_part
                        if len(film_name) > 1 and film_name.lower() not in ['winner', 'nominees']:
                            results['best-film'].append({
                                'name': film_name,
                                'awards': {'bifa': 'Y' if is_winner else 'X'}
                            })
                                
                    elif cat_found == 'best-director':
                        if len(parts) >= 2:
                            director_name = name_part
                            film_name = parts[1].strip()
                            results['best-director'].append({
                                'name': director_name,
                                'film': film_name,
                                'awards': {'bifa': 'Y' if is_winner else 'X'}
                            })
                            
                    elif cat_found == 'best-actor':
                        # Gender-neutral: use TMDB to determine gender
                        if len(parts) >= 2:
                            actor_name = name_part
                            rest = parts[1].strip()
                            film_name = rest
                            if ' as ' in rest:
                                film_name = rest.split(' as ')[0].strip()
                            
                            target_cat = 'best-actor'
                            gender = get_person_gender(actor_name)
                            if gender == 1: # Female
                                target_cat = 'best-actress'
                            
                            entry = {
                                'name': actor_name,
                                'film': film_name,
                                'awards': {'bifa': 'Y' if is_winner else 'X'}
                            }
                            results[target_cat].append(entry)
                    
                    elif cat_found == 'best-actor-direct':
                        # Pre-2022: Direct assignment to actor category
                        if len(parts) >= 2:
                            actor_name = name_part
                            rest = parts[1].strip()
                            film_name = rest
                            if ' as ' in rest:
                                film_name = rest.split(' as ')[0].strip()
                            
                            entry = {
                                'name': actor_name,
                                'film': film_name,
                                'awards': {'bifa': 'Y' if is_winner else 'X'}
                            }
                            results['best-actor'].append(entry)
                    
                    elif cat_found == 'best-actress-direct':
                        # Pre-2022: Direct assignment to actress category
                        if len(parts) >= 2:
                            actress_name = name_part
                            rest = parts[1].strip()
                            film_name = rest
                            if ' as ' in rest:
                                film_name = rest.split(' as ')[0].strip()
                            
                            entry = {
                                'name': actress_name,
                                'film': film_name,
                                'awards': {'bifa': 'Y' if is_winner else 'X'}
                            }
                            results['best-actress'].append(entry)

    total = sum(len(v) for v in results.values())
    print(f"    BIFA: Found {total} entries (F:{len(results['best-film'])}, D:{len(results['best-director'])}, A:{len(results['best-actor'])}, As:{len(results['best-actress'])})")
    return results


def scrape_bifa_section_format(soup):
    """
    Fallback parser for older BIFA pages using H3/H2 sections followed by UL lists.
    Used for 2012-2017 pages.
    """
    results = {
        'best-film': [],
        'best-director': [],
        'best-actor': [],
        'best-actress': []
    }
    
    # Try find headings first
    headings = soup.find_all(['h2', 'h3', 'h4'])
    
    # Map text to category keys
    cat_map = {
        'best british independent film': 'best-film',
        'best director': 'best-director',
        'best actor': 'best-actor',
        'best actress': 'best-actress',
        'best supporting actor': 'best-actor',
        'best supporting actress': 'best-actress',
        'best lead performance': 'best-actor', # Will check gender
        'best supporting performance': 'best-actor' # Will check gender
    }
    
    for h in headings:
        text = h.get_text(separator=' ').strip().lower()
        if 'most promising' in text or 'debut' in text or 'screenplay' in text or 'documentary' in text or 'international' in text or 'short' in text or 'joint' in text or 'ensemble' in text or 'music' in text or 'cinematography' in text or 'costume' in text or 'editing' in text or 'makeup' in text or 'sound' in text or 'effects' in text or 'casting' in text or 'production' in text:
            # Skip irrelevant categories early to avoid false positives
            continue
            
        target_cat = None
        
        # Identify category
        for key, val in cat_map.items():
            if key in text and 'debut' not in text: # Extra check to avoid Debut Director matching Best Director
                 # Check exact match for simpler categories to avoid "Best Actor" matching "Best Supporting Actor"
                 if key == 'best actor' and 'supporting' in text:
                     continue
                 if key == 'best actress' and 'supporting' in text:
                     continue
                 
                 target_cat = val
                 break
        
        if not target_cat:
            continue
            
        # Find the next UL list
        ul = None
        
        # Check parent wrapper first (common in Wikipedia)
        container = h
        if h.parent and h.parent.name == 'div' and ('mw-heading' in h.parent.get('class', []) or 'mw-heading3' in h.parent.get('class', [])):
             container = h.parent
        
        sibling = container.find_next_sibling()
        count = 0
        while sibling and count < 5:
            if sibling.name == 'ul':
                ul = sibling
                break
            if sibling.name in ['h2', 'h3', 'h4', 'table']:
                # Stop if we hit another section
                break
            sibling = sibling.find_next_sibling()
            count += 1
            
        if not ul:
             # Try looking inside next div (sometimes lists are wrapped)
             sibling = container.find_next_sibling()
             if sibling and sibling.name == 'div':
                 ul = sibling.find('ul')
        
        if not ul:
            continue
            
        # Parse list items
        for li in ul.find_all('li'):
            li_text = li.get_text(separator=' ').strip()
            if not li_text:
                continue
                
            is_winner = bool(li.find(['b', 'strong']))
            
            # Parsing logic: "Name - Film" or "Name for Film"
            # Remove " (winner)" text if present
            clean_text = re.sub(r'\s*\(\s*winner\s*\)\s*', '', li_text, flags=re.IGNORECASE)
            
            # Common separators: " – ", " - ", " for ", " in "
            parts = re.split(r'\s*[–-]\s*|\s+for\s+|\s+in\s+', clean_text)
            
            name = clean_text
            film = None
            
            if len(parts) >= 2:
                name = parts[0].strip()
                film = parts[1].strip()
                # Clean up film name (sometimes has role info like "as Role")
                if ' as ' in film:
                    film = film.split(' as ')[0].strip()
            
            # Assign to correct bucket
            final_cat = target_cat
            
            # Handle supporting / gender assignment
            if 'supporting' in text:
                if 'performance' in text or 'actor/actress' in text:
                     # Neutral logic
                     gender = get_person_gender(name)
                     if gender == 1: final_cat = 'best-actress'
                     else: final_cat = 'best-actor'
                elif 'actress' in text:
                     final_cat = 'best-actress'
                else: 
                     final_cat = 'best-actor'
            elif 'lead performance' in text:
                 # Neutral logic
                 gender = get_person_gender(name)
                 if gender == 1: final_cat = 'best-actress'
                 else: final_cat = 'best-actor'
            elif 'best actress' in text:
                final_cat = 'best-actress'
            elif 'best actor' in text:
                final_cat = 'best-actor'
                
            # Filter bad names
            name = name.strip()
            if not name or len(name) < 2: continue
            
            # Film special handling
            if target_cat == 'best-film':
                film = name # For film category, the first part is often the film name
                name = None # No "person" name
                
                results[final_cat].append({
                    'name': film,
                    'awards': {'bifa': 'Y' if is_winner else 'X'}
                })
            else:
                 results[final_cat].append({
                    'name': name,
                    'film': film,
                    'awards': {'bifa': 'Y' if is_winner else 'X'}
                })

    total = sum(len(v) for v in results.values())
    print(f"    BIFA (Section): Found {total} entries (F:{len(results['best-film'])}, D:{len(results['best-director'])}, A:{len(results['best-actor'])}, As:{len(results['best-actress'])})")
    return results
