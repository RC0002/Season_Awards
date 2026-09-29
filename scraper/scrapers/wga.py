# -*- coding: utf-8 -*-
"""
WGA (Writers Guild of America) Scraper
"""

from . import URL_TEMPLATES, fetch_page, ordinal


def scrape_wga(ceremony_num):
    """
    Scrape WGA (Writers Guild of America) Awards.
    Extracts 'Best Original Screenplay' and 'Best Adapted Screenplay' categories.
    Only extracts film names (not writers). Adds 'screenplay_type' field for original/adapted distinction.
    
    Handles two page formats:
    1. Modern (75th+): Header in <td> with <div>, winner in bold <li>
    2. Legacy (older): Header in <th colspan="2">, winner in <p><b><i>, nominees in <ul><li><i>
    """
    url = URL_TEMPLATES['wga'].format(ord=ordinal(ceremony_num))
    print(f"  WGA ({ordinal(ceremony_num)}): {url}")
    
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
    
    for screenplay_type, header_text in [('original', 'Best Original Screenplay'), 
                                          ('adapted', 'Best Adapted Screenplay')]:
        # Find the anchor link with the award name
        header_link = None
        for a in soup.find_all('a'):
            if header_text in a.get_text():
                header_link = a
                break
        
        if not header_link:
            print(f"    WGA: Could not find {header_text} section")
            continue
        
        # Try MODERN format first: parent is TD
        td = header_link.find_parent('td')
        if td:
            # Modern format: process all li items in this TD
            found_in_td = False
            for li in td.find_all('li'):
                italic = li.find('i')
                if not italic:
                    continue
                
                film_name = italic.get_text().strip()
                
                if film_name and film_name not in seen_films:
                    parent_b = italic.find_parent('b')
                    is_winner = parent_b is not None
                    
                    seen_films.add(film_name)
                    results['best-film'].append({
                        'name': film_name,
                        'awards': {'wga': 'Y' if is_winner else 'X'},
                        'screenplay_type': screenplay_type
                    })
                    found_in_td = True
            if found_in_td:
                continue  # Only skip to next category if we actually found films
        
        # Try LEGACY format: parent is TH, data in next row's TD
        th = header_link.find_parent('th')
        if th:
            # Navigate to next row
            tr = th.find_parent('tr')
            if not tr:
                continue
            
            next_row = tr.find_next_sibling('tr')
            if not next_row:
                continue
            
            # Get the TD with nominees
            data_td = next_row.find('td')
            if not data_td:
                continue
            
            # Check for two formats:
            # Format A: Winner in <p><b><i>, nominees in sibling <ul>
            # Format B: Winner is top-level <li><b><i>, nominees in nested <ul> inside winner's <li>
            
            # Try Format A first: Winner in <p><b><i>
            p_winner = data_td.find('p')
            if p_winner:
                bold = p_winner.find('b')
                if bold:
                    italic = bold.find('i')
                    if italic:
                        film_name = italic.get_text().strip()
                        if film_name and film_name not in seen_films:
                            seen_films.add(film_name)
                            results['best-film'].append({
                                'name': film_name,
                                'awards': {'wga': 'Y'},
                                'screenplay_type': screenplay_type
                            })
            
            # Try Format C (modern 68th+): Winner is first link with film title, nominees in li as links
            # Check if we haven't found any films yet (via p/b/i)
            if not any(e.get('screenplay_type') == screenplay_type for e in results['best-film']):
                # Winner: first link that looks like a film title
                # Skip links that are clearly studios, writers, etc.
                skip_patterns = ['films', 'pictures', 'studios', 'entertainment', 'releasing', 'productions', 'searchlight']
                all_links = data_td.find_all('a')
                for link in all_links:
                    title = link.get('title', '').lower()
                    text = link.get_text().strip()
                    # Skip if link title contains studio indicators or is empty
                    if not text or len(text) < 2:
                        continue
                    if any(pattern in title for pattern in skip_patterns):
                        continue
                    # Accept film link (has (film) OR first non-studio link)
                    if '(film)' in title or 'film)' in title or (title and not any(pattern in title for pattern in skip_patterns)):
                        if text not in seen_films:
                            seen_films.add(text)
                            results['best-film'].append({
                                'name': text,
                                'awards': {'wga': 'Y'},
                                'screenplay_type': screenplay_type
                            })
                        break
                
                # Nominees: li elements - get first link in each li
                for li in data_td.find_all('li'):
                    link = li.find('a')
                    if link:
                        text = link.get_text().strip()
                        if text and len(text) > 1 and text not in seen_films:
                            seen_films.add(text)
                            results['best-film'].append({
                                'name': text,
                                'awards': {'wga': 'X'},
                                'screenplay_type': screenplay_type
                            })
            
            # Nominees in sibling <ul><li><i>
            ul = data_td.find('ul')
            if ul:
                # Check if this is Format B: first li is winner with nested ul
                first_li = ul.find('li', recursive=False)
                if first_li:
                    # Check for winner in first li (bold italic)
                    first_b = first_li.find('b', recursive=False)
                    if first_b:
                        first_i = first_b.find('i')
                        if first_i:
                            winner_name = first_i.get_text().strip()
                            if winner_name and winner_name not in seen_films:
                                seen_films.add(winner_name)
                                results['best-film'].append({
                                    'name': winner_name,
                                    'awards': {'wga': 'Y'},
                                    'screenplay_type': screenplay_type
                                })
                    
                    # Check for nested ul (nominees inside winner's li)
                    nested_ul = first_li.find('ul')
                    if nested_ul:
                        for nested_li in nested_ul.find_all('li', recursive=False):
                            italic = nested_li.find('i')
                            if not italic:
                                continue
                            
                            film_name = italic.get_text().strip()
                            
                            if film_name and film_name not in seen_films:
                                seen_films.add(film_name)
                                results['best-film'].append({
                                    'name': film_name,
                                    'awards': {'wga': 'X'},
                                    'screenplay_type': screenplay_type
                                })
                
                # Also check sibling li items (for Format A)
                for li in ul.find_all('li', recursive=False):
                    italic = li.find('i')
                    if not italic:
                        continue
                    
                    film_name = italic.get_text().strip()
                    
                    if film_name and film_name not in seen_films:
                        seen_films.add(film_name)
                        results['best-film'].append({
                            'name': film_name,
                            'awards': {'wga': 'X'},
                            'screenplay_type': screenplay_type
                        })
    # Categories to look for (lowercase for matching)
    target_categories = {
        'original screenplay': 'Original',
        'adapted screenplay': 'Adapted'
    }
    
    # Iterate through all headers to track sections
    all_elements = soup.find_all(['h2', 'h3', 'h4'])
    
    current_section = ""
    
    for header in all_elements:
        header_text = header.get_text().lower().strip()
        
        # Update current section if h2 or h3
        if header.name in ['h2', 'h3']:
            current_section = header_text
            # Only continue if it's strictly H2, as H3 might BE the category header we want to parse
            if header.name == 'h2':
                continue
            
        # Skip if not in Film section
        # Section usually "film", "screenplay (film)", "motion picture"
        # Avoid "television", "radio", "promotional"
        if 'television' in current_section or 'radio' in current_section or 'promotional' in current_section or 'series' in current_section:
            continue
            
        # Identify category - accept full "original screenplay" OR just "original"/"adapted"
        screenplay_type = None
        for cat_key, type_val in target_categories.items():
            if cat_key in header_text:
                screenplay_type = type_val
                break
        
        # Fallback: match just "original" or "adapted" if in film section
        if not screenplay_type:
            if 'film' in current_section or 'motion picture' in current_section or current_section == '':
                if header_text.strip() == 'original' or header_text.strip().startswith('original['):
                    screenplay_type = 'Original'
                elif header_text.strip() == 'adapted' or header_text.strip().startswith('adapted['):
                    screenplay_type = 'Adapted'
        
        if not screenplay_type:
            continue
        # Navigate content following header
        # Structure variants:
        # Modern: h4 -> ul (first item winner with bold/icon, others nominees)
        # Historical (2002-2011): h3 -> p (winner bold/italic) -> ul (nominees)
        
        # Start looking from next sibling
        # Handle wrappings (e.g. h4 in div.mw-heading)
        start_element = header.parent if header.parent and header.parent.name == 'div' and 'mw-heading' in str(header.parent.get('class', [])) else header
        
        current = start_element.next_sibling
        
        while current:
            if hasattr(current, 'name') and current.name:
                
                # Stop conditions
                # Check for direct headers
                if current.name in ['h2', 'h3', 'h4']:
                    # Stop if we hit a header of same or higher importance
                    if current.name == 'h2': break
                    if current.name == header.name: break
                    if header.name == 'h4' and current.name == 'h3': break
                    # If we are parsing H3, H4 is a child, so continues (technically)
                    pass

                # Check for wrapped headers (div.mw-heading)
                if current.name == 'div' and any(cls.startswith('mw-heading') for cls in current.get('class', [])):
                    # Find the header inside to check level
                    h = current.find(['h2', 'h3', 'h4'])
                    if h:
                        if h.name == 'h2': break
                        if h.name == header.name: break
                        if header.name == 'h4' and h.name == 'h3': break
                
                # Case 1: Winner in Paragraph
                if current.name == 'p':
                    winner_film = None
                    bold_italic = current.find('b')
                    if bold_italic:
                        italic_in_bold = bold_italic.find('i')
                        if italic_in_bold:
                             winner_film = italic_in_bold.get_text().strip()
                        elif bold_italic.get_text().strip():
                             pass
                    
                    if not winner_film:
                        italic = current.find('i')
                        if italic:
                             winner_film = italic.get_text().strip()
                    
                    if winner_film and winner_film not in seen_films:
                        # Extra validation to avoid TV
                        if len(winner_film) > 1 and "see also" not in winner_film.lower():
                            seen_films.add(winner_film)
                            results['best-film'].append({
                                'name': winner_film,
                                'awards': {'wga': 'Y'},
                                'screenplay_type': screenplay_type
                            })

                # Case 2: List (Nominees)
                elif current.name == 'ul':
                    for li in current.find_all('li', recursive=False):
                        film_name = None
                        is_winner = False
                        
                        bold = li.find('b')
                        if bold:
                             italic = bold.find('i')
                             if italic:
                                 film_name = italic.get_text().strip()
                                 is_winner = True
                        
                        if not film_name:
                            italic = li.find('i')
                            if italic:
                                film_name = italic.get_text().strip()
                        
                        if film_name and film_name not in seen_films:
                             if "screenplay" in film_name.lower(): continue 
                             seen_films.add(film_name)
                             badge = 'Y' if is_winner else 'X'
                             results['best-film'].append({
                                'name': film_name,
                                'awards': {'wga': badge},
                                'screenplay_type': screenplay_type
                             })
                
            current = current.next_sibling

    print(f"    WGA {ordinal(ceremony_num)}: Found {len(results['best-film'])} films")
    return results
