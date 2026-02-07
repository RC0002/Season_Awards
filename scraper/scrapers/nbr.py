# -*- coding: utf-8 -*-
"""
NBR Awards Scraper
"""

from . import CEREMONY_MAP, URL_TEMPLATES, fetch_page, ordinal, init_results

def scrape_nbr(year):
    """
    Scrape NBR (National Board of Review) Awards for a specific year.
    NBR has individual pages per year with Top 10 Films and individual winner categories.
    """
    url = URL_TEMPLATES['nbr'].format(year=year)
    print(f"  NBR ({year}): {url}")
    
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
    
    # Find Top 10 Films section (h2 with id="Top_10_Films")
    # Wikipedia wraps h2 in <div class="mw-heading mw-heading2">
    top10_h2 = soup.find('h2', id='Top_10_Films')
    if not top10_h2:
        # Fallback: search all h2 for text match
        for h2 in soup.find_all('h2'):
            if 'top' in h2.get_text().lower() and 'film' in h2.get_text().lower():
                top10_h2 = h2
                break
    
    if top10_h2:
        # Navigate from parent div (mw-heading wrapper)
        container = top10_h2.parent
        current = container.next_sibling if container else top10_h2.next_sibling
        
        while current:
            if not hasattr(current, 'name'):
                current = current.next_sibling
                continue
            
            # Stop at next section (div with mw-heading class or h2)
            if current.name == 'h2':
                break
            if current.name == 'div' and 'mw-heading' in current.get('class', []):
                break
            
            # Parse films from ul or p elements
            if current.name == 'ul':
                for li in current.find_all('li', recursive=False):
                    link = li.find('a')
                    if link:
                        film_name = link.get_text().strip()
                        if len(film_name) >= 2 and film_name not in seen_films:
                            seen_films.add(film_name)
                            entry = {
                                'name': film_name,
                                'awards': {'nbr': 'Y'}
                            }
                            results['best-film'].append(entry)
            elif current.name == 'p':
                # Best Film might be in a p tag with link
                link = current.find('a')
                if link:
                    film_name = link.get_text().strip()
                    if len(film_name) >= 2 and film_name not in seen_films:
                        seen_films.add(film_name)
                        entry = {
                            'name': film_name,
                            'awards': {'nbr': 'Y'}
                        }
                        results['best-film'].append(entry)
            
            current = current.next_sibling
    
    # Find Winners section (h2 with id="Winners")
    winners_h2 = soup.find('h2', id='Winners')
    if not winners_h2:
        for h2 in soup.find_all('h2'):
            if 'winner' in h2.get_text().lower():
                winners_h2 = h2
                break
    
    if winners_h2:
        container = winners_h2.parent
        current = container.next_sibling if container else winners_h2.next_sibling
        current_category = None
        
        while current:
            if not hasattr(current, 'name'):
                current = current.next_sibling
                continue
            
            # Stop at next section
            if current.name == 'h2':
                break
            if current.name == 'div' and 'mw-heading' in current.get('class', []):
                break
            
            # Check for category header (p > b with colon)
            if current.name == 'p':
                b = current.find('b')
                if b:
                    cat_text = b.get_text().lower()
                    if 'best director' in cat_text and 'debut' not in cat_text:
                        current_category = 'best-director'
                    elif 'best actor' in cat_text and 'supporting' not in cat_text and 'breakthrough' not in cat_text:
                        current_category = 'best-actor'
                    elif 'best actress' in cat_text and 'supporting' not in cat_text and 'breakthrough' not in cat_text:
                        current_category = 'best-actress'
                    else:
                        current_category = None
            
            # Parse winner from ul after category header
            if current.name == 'ul' and current_category:
                li = current.find('li')
                if li:
                    links = li.find_all('a')
                    if links:
                        name = links[0].get_text().strip()
                        film = links[1].get_text().strip() if len(links) > 1 else None
                        
                        if len(name) >= 2:
                            entry = {
                                'name': name,
                                'awards': {'nbr': 'Y'}
                            }
                            if film:
                                entry['film'] = film
                            results[current_category].append(entry)
                current_category = None  # Reset after processing
            
            current = current.next_sibling
    
    total = sum(len(v) for v in results.values())
    print(f"    NBR {year}: Found {total} entries (Films: {len(results['best-film'])}, Dir: {len(results['best-director'])}, Actor: {len(results['best-actor'])}, Actress: {len(results['best-actress'])})")
    return results


