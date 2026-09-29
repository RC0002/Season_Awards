# -*- coding: utf-8 -*-
"""
ADG (Art Directors Guild) Scraper
"""

from . import CEREMONY_MAP, URL_TEMPLATES, fetch_page

try:
    from manual_adg_data import MANUAL_ADG_DATA
except ImportError:
    try:
        from scraper.manual_adg_data import MANUAL_ADG_DATA
    except ImportError:
        MANUAL_ADG_DATA = {}


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
                        elif ' - ' in cleaned_text:  # Spaced hyphen fallback (keeps "Spider-Man")
                            possible_film = cleaned_text.split(' - ')[-1].strip()
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
