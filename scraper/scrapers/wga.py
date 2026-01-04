# -*- coding: utf-8 -*-
"""
WGA Awards Scraper
"""

from . import CEREMONY_MAP, URL_TEMPLATES, fetch_page, ordinal, init_results

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
            continue
        
        # Try VERY OLD format (65th-66th): h4 with id="Original"/"Adapted"
        # Header is <h4 id="Original"> or <h4 id="Adapted">
        h4_id = 'Original' if screenplay_type == 'original' else 'Adapted'
        h4 = soup.find('h4', id=h4_id)
        if not h4:
            # Try finding by span inside h4
            span = soup.find('span', id=h4_id)
            if span:
                h4 = span.find_parent('h4')
        
        if h4:
            # Find content after h4: winner in <p>, nominees in <ul>
            # h4 is often wrapped in a <div class="mw-heading">, so navigate from parent
            start_element = h4.parent if h4.parent and h4.parent.name == 'div' else h4
            current = start_element.next_sibling
            while current:
                if hasattr(current, 'name'):
                    # Winner in <p> with <i> (may be <i><b> or <b><i> or just <i>)
                    if current.name == 'p':
                        # Try to find first <i> tag in paragraph
                        italic = current.find('i')
                        if italic:
                            film_name = italic.get_text().strip()
                            if film_name and film_name not in seen_films:
                                seen_films.add(film_name)
                                results['best-film'].append({
                                    'name': film_name,
                                    'awards': {'wga': 'Y'},
                                    'screenplay_type': screenplay_type
                                })
                    
                    # Nominees in <ul><li><i>
                    if current.name == 'ul':
                        for li in current.find_all('li', recursive=False):
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
                        break  # Found the ul, stop
                    
                    # Stop if we hit next h3/h4 (new section)
                    if current.name in ['h3', 'h4']:
                        break
                
                current = current.next_sibling
    
    print(f"    WGA {ordinal(ceremony_num)}: Found {len(results['best-film'])} films")
    return results


