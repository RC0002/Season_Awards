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
