# -*- coding: utf-8 -*-
"""
PGA Awards Scraper
"""

from . import CEREMONY_MAP, URL_TEMPLATES, fetch_page, ordinal, init_results

def scrape_pga(ceremony_num):
    """
    Scrape PGA (Producers Guild of America) Awards.
    Only extracts 'Outstanding Producer of Theatrical Motion Pictures' category.
    Ignores Documentary and Animated categories.
    """
    url = URL_TEMPLATES['pga'].format(ord=ordinal(ceremony_num))
    print(f"  PGA ({ordinal(ceremony_num)}): {url}")
    
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
    
    # Find the "Darryl F. Zanuck Award" section
    # This is the main theatrical film producer award
    zanuck_link = soup.find('a', string=lambda t: t and 'Darryl F. Zanuck Award' in t)
    
    if not zanuck_link:
        # Fallback: search for text containing "Outstanding Producer of Theatrical"
        for th in soup.find_all(['th', 'td']):
            if 'Outstanding Producer of Theatrical Motion Pictures' in th.get_text():
                zanuck_link = th
                break
    
    if not zanuck_link:
        print(f"    PGA: Could not find Zanuck Award section")
        return results
    
    # Navigate to find the UL with nominees
    # Structure: The link is inside a header, the UL follows
    current = zanuck_link
    ul = None
    
    # Go up to find parent container, then find next UL
    for _ in range(10):
        if current is None:
            break
        
        # Check siblings for UL
        sibling = current.next_sibling
        while sibling:
            if hasattr(sibling, 'name') and sibling.name == 'ul':
                ul = sibling
                break
            sibling = sibling.next_sibling
        
        if ul:
            break
        
        # Check if current element contains UL
        if hasattr(current, 'find'):
            ul = current.find('ul')
            if ul:
                break
        
        current = current.parent
    
    if not ul:
        print(f"    PGA: Could not find nominee list")
        return results
    
    # Parse the list
    # Structure: Winner is in bold <b>, inside <li> with nested <ul> for nominees
    # First check top-level li items
    for li in ul.find_all('li', recursive=False):
        # Get film name from <i> tag
        italic = li.find('i')
        if not italic:
            continue
        
        film_name = italic.get_text().strip()
        
        # Check if this is a category we should skip (Documentary, Animated)
        li_text = li.get_text().lower()
        if 'documentary' in li_text or 'animated' in li_text:
            continue
        
        if film_name and film_name not in seen_films:
            # Check if winner (bold)
            is_winner = li.find('b') is not None
            
            seen_films.add(film_name)
            results['best-film'].append({
                'name': film_name,
                'awards': {'pga': 'Y' if is_winner else 'X'}
            })
        
        # Check for nested <ul> with more nominees
        nested_ul = li.find('ul')
        if nested_ul:
            for nested_li in nested_ul.find_all('li', recursive=False):
                nested_italic = nested_li.find('i')
                if nested_italic:
                    nested_film = nested_italic.get_text().strip()
                    if nested_film and nested_film not in seen_films:
                        seen_films.add(nested_film)
                        results['best-film'].append({
                            'name': nested_film,
                            'awards': {'pga': 'X'}  # Nested ones are nominees
                        })
    
    print(f"    PGA {ordinal(ceremony_num)}: Found {len(results['best-film'])} films")
    return results


