# -*- coding: utf-8 -*-
"""
Annie Awards Scraper
Scrapes Best Animated Feature category only
"""

from . import fetch_page, ordinal, init_results

def scrape_annie(ceremony_number):
    """
    Scrape Annie Awards from English Wikipedia.
    Extracts only Best Animated Feature category.
    
    Args:
        ceremony_number: Ceremony number (e.g., 52 for 52nd Annie Awards)
    
    Returns:
        dict: Results with best-film only (no director/actor/actress)
    """
    ordinal_str = ordinal(ceremony_number)
    url = f"https://en.wikipedia.org/wiki/{ordinal_str}_Annie_Awards"
    print(f"  ANNIE ({ordinal_str}): {url}")
    
    soup = fetch_page(url)
    if not soup:
        return {}
    
    results = {
        'best-film': [],
        'best-director': [],
        'best-actor': [],
        'best-actress': []
    }
    
    # Find the table containing "Best Animated Feature" or "Best Feature"
    # Some years use different header names
    best_feature_th = None
    for th in soup.find_all('th'):
        th_text = th.get_text()
        # Match both "Best Animated Feature" and "Best Feature"
        if 'Best Animated Feature' in th_text or th_text.strip() == 'Best Feature':
            best_feature_th = th
            break
    
    # FALLBACK: Check for h2/h3 headers by ID (used in older Annie Awards pages like 29th-39th)
    # Wikipedia uses IDs like "Best_Animated_Feature" or "Best_Feature" in section headers
    if not best_feature_th:
        # Try to find section by ID
        section_ids = ['Best_Animated_Feature', 'Best_Feature']
        section_header = None
        for sid in section_ids:
            elem = soup.find(id=sid)
            if elem:
                # The ID might be on a span inside h2, or on h2 itself
                section_header = elem.find_parent(['h2', 'h3']) or (elem if elem.name in ['h2', 'h3'] else None)
                if section_header:
                    break
        
        if section_header:
            # Found header-based structure
            # Use find_all_next to get p and ul elements (not siblings due to wiki structure)
            following_elements = section_header.find_all_next(['p', 'ul', 'h2', 'h3'])
            
            found_winner = None
            nominees = []
            winner_section = False
            
            for elem in following_elements:
                # Stop at next h2/h3 section
                if elem.name in ['h2', 'h3']:
                    break
                
                text = elem.get_text()
                
                # Check if this is a "Winner:" header
                if elem.name == 'p' and 'Winner' in text:
                    winner_section = True
                    continue
                
                # Check if this is a "Nominees:" header
                if elem.name == 'p' and 'Nominee' in text:
                    winner_section = False
                    continue
                
                # Process ul lists
                if elem.name == 'ul':
                    for li in elem.find_all('li', recursive=False):
                        # Check if this list item is bold (winner)
                        is_bold = li.find(['b', 'strong'])
                        
                        # Get film name - try italic first, then link, then text
                        film_i = li.find('i')
                        if film_i:
                            film_name = film_i.get_text().strip()
                        else:
                            first_link = li.find('a')
                            if first_link:
                                film_name = first_link.get_text().strip()
                            else:
                                film_name = li.get_text().strip()
                        
                        # Clean up film name
                        if ' - ' in film_name:
                            film_name = film_name.split(' - ')[0].strip()
                        if '-' in film_name and len(film_name.split('-')[0]) > 3:
                            film_name = film_name.split('-')[0].strip()
                        if '(' in film_name:
                            film_name = film_name.split('(')[0].strip()
                        
                        if film_name:
                            # If we are in a winner section OR the item is bold, it's a winner
                            if (winner_section or is_bold) and not found_winner:
                                found_winner = film_name
                            else:
                                if film_name != found_winner:
                                    nominees.append(film_name)
            
            # Add results
            if found_winner:
                results['best-film'].append({
                    'name': found_winner,
                    'awards': {'annie': 'Y'}
                })
            
            for nominee in nominees:
                results['best-film'].append({
                    'name': nominee,
                    'awards': {'annie': 'X'}
                })
            
            if results['best-film']:
                total = len(results['best-film'])
                winners = len([f for f in results['best-film'] if f['awards']['annie'] == 'Y'])
                print(f"    Annie {ordinal_str}: Found {total} entries (Winner: {winners}, Nominees: {total - winners}) [header structure]")
                return results
    
    # FALLBACK 2: Search for wikitable containing "Best Animated Feature" in cell text
    # Used in 35th Annie Awards where category is in td, not th
    if not best_feature_th:
        for table in soup.find_all('table', class_='wikitable'):
            table_text = table.get_text()
            if 'Best Animated Feature' in table_text:
                # Find the cell containing "Best Animated Feature"
                for td in table.find_all('td'):
                    td_text = td.get_text()
                    if 'Best Animated Feature' in td_text:
                        # Parse films from this cell - each line is a film
                        # Films with † are winners
                        lines = [line.strip() for line in td_text.split('\n') if line.strip()]
                        for line in lines:
                            if 'Best Animated Feature' in line or 'Best Home' in line:
                                continue
                            
                            # Check for winner marker (†)
                            is_winner = '†' in line
                            
                            # Extract film name (before – or - that separates studio)
                            film_name = line.replace('†', '').strip()
                            if '–' in film_name:
                                film_name = film_name.split('–')[0].strip()
                            elif ' - ' in film_name:
                                film_name = film_name.split(' - ')[0].strip()
                            
                            if film_name and len(film_name) > 2:
                                results['best-film'].append({
                                    'name': film_name,
                                    'awards': {'annie': 'Y' if is_winner else 'X'}
                                })
                        
                        if results['best-film']:
                            total = len(results['best-film'])
                            winners = len([f for f in results['best-film'] if f['awards']['annie'] == 'Y'])
                            print(f"    Annie {ordinal_str}: Found {total} entries (Winner: {winners}, Nominees: {total - winners}) [table text structure]")
                            return results
                        break
                break
    
    if not best_feature_th:
        print(f"    Annie: 'Best Animated Feature' / 'Best Feature' section not found")
        return results


    
    # Get the <td> cell that contains the films
    table = best_feature_th.find_parent('table')
    if not table:
        print(f"    Annie: Could not find table")
        return results
    
    # Find the row containing the th
    th_row = best_feature_th.find_parent('tr')
    if not th_row:
        print(f"    Annie: Could not find th row")
        return results
    
    # Get next row which should contain the td with films
    td_row = th_row.find_next_sibling('tr')
    if not td_row:
        print(f"    Annie: Could not find td row")
        return results
    
    # Find the td element
    td = td_row.find('td')
    if not td:
        print(f"    Annie: Could not find td element")
        return results
    
    # STRUCTURE 3: Winner in <p> tag, nominees in separate <ul>
    # Used in 41st-42nd Annie Awards (older format)
    # Check for <p> with bold/italic winner followed by <ul> with nominees
    p_tag = td.find('p')
    main_ul = td.find('ul')
    
    if p_tag and main_ul:
        # Check if p_tag contains a bold winner
        winner_b = p_tag.find('b')
        if winner_b:
            # STRUCTURE 3: Winner in <p>, nominees in <ul>
            winner_i = p_tag.find('i')
            if winner_i:
                film_name = winner_i.get_text().strip()
            elif winner_b:
                film_name = winner_b.get_text().strip()
            else:
                film_name = p_tag.get_text().strip()
            
            if '(' in film_name:
                film_name = film_name.split('(')[0].strip()
            
            if film_name:
                results['best-film'].append({
                    'name': film_name,
                    'awards': {'annie': 'Y'}
                })
            
            # Get nominees from <ul>
            for li in main_ul.find_all('li', recursive=False):
                film_i = li.find('i')
                if film_i:
                    film_name = film_i.get_text().strip()
                else:
                    film_name = li.get_text().strip()
                
                if '(' in film_name:
                    film_name = film_name.split('(')[0].strip()
                
                if film_name:
                    results['best-film'].append({
                        'name': film_name,
                        'awards': {'annie': 'X'}
                    })
            
            total = len(results['best-film'])
            winners = len([f for f in results['best-film'] if f['awards']['annie'] == 'Y'])
            print(f"    Annie {ordinal_str}: Found {total} entries (Winner: {winners}, Nominees: {total - winners})")
            return results
    
    # STRUCTURE 1 & 2: Check for ul-based structures
    if not main_ul:
        print(f"    Annie: Could not find ul element")
        return results
    
    # Get all <li> items from the main list
    all_lis = main_ul.find_all('li', recursive=False)
    if not all_lis:
        print(f"    Annie: Could not find any li elements")
        return results
    
    # Check structure: nested (52nd style) or flat (53rd style)
    first_li = all_lis[0]
    winner_b = first_li.find('b')
    nested_ul = first_li.find('ul')
    
    if winner_b and nested_ul:
        # STRUCTURE 1: NESTED (winner in bold li, nominees in nested ul)
        # Used in 52nd and similar years with results announced
        
        # Extract winner
        winner_i = winner_b.find('i')
        if winner_i:
            film_name = winner_i.get_text().strip()
        else:
            film_name = winner_b.get_text().strip()
        
        if '(' in film_name:
            film_name = film_name.split('(')[0].strip()
        
        if film_name:
            results['best-film'].append({
                'name': film_name,
                'awards': {'annie': 'Y'}
            })
        
        # Get nominees from nested <ul>
        for nominee_li in nested_ul.find_all('li', recursive=False):
            nominee_i = nominee_li.find('i')
            if nominee_i:
                film_name = nominee_i.get_text().strip()
            else:
                film_name = nominee_li.get_text().strip()
            
            if '(' in film_name:
                film_name = film_name.split('(')[0].strip()
            
            if film_name:
                results['best-film'].append({
                    'name': film_name,
                    'awards': {'annie': 'X'}
                })
    else:
        # STRUCTURE 2: FLAT (all nominees in same list, no winner yet or all equal)
        # Used in 53rd (future ceremony with nominations only)
        
        for li in all_lis:
            # Check if this item is a winner (bolded)
            is_winner = bool(li.find('b'))
            
            # Get film name from <i> tag
            film_i = li.find('i')
            if film_i:
                film_name = film_i.get_text().strip()
            else:
                film_name = li.get_text().strip()
            
            if '(' in film_name:
                film_name = film_name.split('(')[0].strip()
            
            if film_name:
                results['best-film'].append({
                    'name': film_name,
                    'awards': {'annie': 'Y' if is_winner else 'X'}
                })
    
    total = len(results['best-film'])
    winners = len([f for f in results['best-film'] if f['awards']['annie'] == 'Y'])
    print(f"    Annie {ordinal_str}: Found {total} entries (Winner: {winners}, Nominees: {total - winners})")
    
    return results
