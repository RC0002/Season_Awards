# -*- coding: utf-8 -*-
"""
Spirit Awards (Independent Spirit Awards) Scraper
"""

from . import CEREMONY_MAP, URL_TEMPLATES, fetch_page, ordinal, get_person_gender


def scrape_spirit(year):
    """Scrape Independent Spirit Awards from Wikipedia."""
    ceremony_num = CEREMONY_MAP['spirit'].get(year)
    if not ceremony_num:
        print(f"  SPIRIT: No ceremony number mapped for year {year}")
        return {}
    
    url = URL_TEMPLATES['spirit'].format(ord=ordinal(ceremony_num))
    print(f"  SPIRIT ({ordinal(ceremony_num)}): {url}")
    
    return scrape_spirit_logic(url)


def scrape_spirit_logic(url):
    """
    Scrape Spirit Awards categories:
    - Best Feature -> best-film
    - Best Director -> best-director
    - Pre-2022: Best Male/Female Lead, Best Supporting Male/Female
    - 2022+: Best Lead Performance, Best Supporting Performance (gender neutral)
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
    
    # Find wikitables
    tables = soup.find_all('table', class_='wikitable')
    
    for table in tables:
        rows = table.find_all('tr')
        
        # Process rows in pairs: th row followed by td row
        for row_idx in range(len(rows) - 1):
            row = rows[row_idx]
            next_row = rows[row_idx + 1]
            
            # Check if this row has th (headers) and next row has td (data)
            headers = row.find_all('th')
            data_cells = next_row.find_all('td')
            
            if not headers or not data_cells:
                continue
            
            # Match headers to data cells
            for i, header in enumerate(headers):
                header_text = header.get_text(separator=' ').strip().lower()
                
                # Determine category - only Film categories, not TV
                cat_found = None
                check_gender = False # Flag for gender neutral categories
                
                if 'best feature' in header_text:
                    cat_found = 'best-film'
                elif 'best director' in header_text and 'series' not in header_text:
                    cat_found = 'best-director'
                # Gender-neutral categories (2022+)
                elif 'best lead performance' in header_text and 'series' not in header_text:
                    cat_found = 'best-actor'
                    check_gender = True
                elif 'best supporting performance' in header_text and 'series' not in header_text:
                    cat_found = 'best-actor'  # Both map to best-actor initially
                    check_gender = True
                # Gendered categories (pre-2022)
                elif 'best male lead' in header_text:
                    cat_found = 'best-actor'
                elif 'best female lead' in header_text:
                    cat_found = 'best-actress'
                elif 'best supporting male' in header_text:
                    cat_found = 'best-actor'
                elif 'best supporting female' in header_text:
                    cat_found = 'best-actress'
                
                if not cat_found or i >= len(data_cells):
                    continue
                
                cell = data_cells[i]
                
                # Collect all nominees: winner (bold text before list) + nominees (li elements)
                nominees = []
                
                # 1. Check for winner as bold text BEFORE the ul (like "The Lost Daughter" in 37th)
                # The winner is often in <p><i><b>Name</b></i></p> structure before <ul>
                for child in cell.children:
                    if hasattr(child, 'name'):
                        if child.name == 'ul':
                            break  # Stop when we reach the list
                        # Check if this element contains a bold tag (winner)
                        if child.name in ['b', 'strong']:
                            winner_text = child.get_text(separator=' ').strip()
                            if winner_text:
                                nominees.append((winner_text, True))
                        elif child.name in ['p', 'div', 'span', 'i']:
                            # Look for bold inside these container elements
                            bold = child.find(['b', 'strong'])
                            if bold:
                                winner_text = child.get_text(separator=' ').strip()
                                if winner_text:
                                    nominees.append((winner_text, True))
                
                # 2. Get all LI elements (other nominees)
                lis = cell.find_all('li')
                for li in lis:
                    first_elem = li.find(['b', 'strong'])
                    is_winner = bool(first_elem)
                    text = li.get_text(separator=' ').strip()
                    if text:
                        nominees.append((text, is_winner))
                
                # Process all nominees
                for text, is_winner in nominees:
                    award_val = 'Y' if is_winner else 'X'
                    
                    # Parse based on category
                    if cat_found == 'best-film':
                        # Format: Film – Producers
                        parts = text.split('–')
                        if len(parts) >= 1:
                            film_name = parts[0].strip()
                            film_name = film_name.replace('|', '').strip()
                            if film_name:
                                results['best-film'].append({
                                    'name': film_name,
                                    'awards': {'spirit': award_val}
                                })
                    
                    elif cat_found == 'best-director':
                        # Format: Director – Film
                        parts = text.split('–')
                        person_name = parts[0].strip()
                        film_name = parts[1].strip() if len(parts) > 1 else ""
                        if person_name:
                            entry = {'name': person_name, 'awards': {'spirit': award_val}}
                            if film_name:
                                entry['film'] = film_name
                            results['best-director'].append(entry)
                    
                    elif cat_found == 'best-actor':
                        # Format: Actor – Film as Character
                        parts = text.split('–')
                        person_name = parts[0].strip()
                        rest = parts[1].strip() if len(parts) > 1 else ""
                        
                        # Extract film name (before " as ")
                        film_name = rest.split(' as ')[0].strip() if ' as ' in rest else rest
                        
                        if person_name:
                            entry = {'name': person_name, 'awards': {'spirit': award_val}}
                            if film_name:
                                entry['film'] = film_name
                                
                            # Handle gender neutral categories
                            target_cat = 'best-actor'
                            if check_gender:
                                gender = get_person_gender(person_name)
                                if gender == 1: # Female
                                    target_cat = 'best-actress'
                                    
                            results[target_cat].append(entry)
                    
                    elif cat_found == 'best-actress':
                        # Format: Actress – Film as Character
                        parts = text.split('–')
                        person_name = parts[0].strip()
                        rest = parts[1].strip() if len(parts) > 1 else ""
                        
                        # Extract film name (before " as ")
                        film_name = rest.split(' as ')[0].strip() if ' as ' in rest else rest
                        
                        if person_name:
                            entry = {'name': person_name, 'awards': {'spirit': award_val}}
                            if film_name:
                                entry['film'] = film_name
                            results['best-actress'].append(entry)
    
    total = sum(len(v) for v in results.values())
    print(f"    Spirit: Found {total} entries (Films: {len(results['best-film'])}, Dir: {len(results['best-director'])}, Actors: {len(results['best-actor'])}, Actresses: {len(results['best-actress'])})")
    return results
