# -*- coding: utf-8 -*-
"""
ADG Awards Scraper
"""

from . import CEREMONY_MAP, URL_TEMPLATES, fetch_page, ordinal, init_results

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


