# -*- coding: utf-8 -*-
"""
National Board of Review Scraper
"""

from . import URL_TEMPLATES, fetch_page


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
    
    # 1. FIND TOP 10 FILMS section
    top10_header = None
    # ID check
    if soup.find(id='Top_10_Films'): top10_header = soup.find(id='Top_10_Films')
    elif soup.find(id='Top_10_films'): top10_header = soup.find(id='Top_10_films')
    
    # Text fallback
    if not top10_header:
        for h2 in soup.find_all('h2'):
            text = h2.get_text().lower()
            if 'top' in text and 'film' in text and ('10' in text or 'ten' in text):
                top10_header = h2
                break
    
    if top10_header:
        container = top10_header.parent
        # If header is wrapped in mw-heading div, start searching after that div
        if container.name == 'div' and 'mw-heading' in container.get('class', []):
            current = container.next_sibling
        else:
            current = top10_header.next_sibling
            
        while current:
            if not hasattr(current, 'name'):
                current = current.next_sibling
                continue
            
            # Stop at next section
            if current.name in ['h2', 'h3'] or (current.name == 'div' and 'mw-heading' in current.get('class', [])):
                break
            
            # Parse films from UL (unordered) or OL (ordered - older years)
            if current.name in ['ul', 'ol']:
                for li in current.find_all('li', recursive=False):
                    link = li.find('a')
                    if link:
                        film_name = link.get_text().strip()
                        if len(film_name) >= 2 and film_name not in seen_films:
                            seen_films.add(film_name)
                            entry = {'name': film_name, 'awards': {'nbr': 'Y'}}
                            results['best-film'].append(entry)
            
            # Sometimes Best Film is in a separate P tag with a link (e.g. 2005 Best Film: Good Night, and Good Luck)
            # Only if we haven't found a list yet or in addition? Usually list contains top 10.
            # Older pages put "Best Film" in the "Winners" section, so this might be redundant if we check winners properly.
            
            current = current.next_sibling

    # 2. FIND WINNERS section
    winners_header = None
    for keyword in ['Winners', 'Awards', 'Award Winners']:
        if soup.find(id=keyword):
            winners_header = soup.find(id=keyword)
            break
            
    if not winners_header:
        for h2 in soup.find_all('h2'):
            if 'winner' in h2.get_text().lower() or 'award' in h2.get_text().lower():
                winners_header = h2
                break
    
    if winners_header:
        container = winners_header.parent
        if container.name == 'div' and 'mw-heading' in container.get('class', []):
            current = container.next_sibling
        else:
            current = winners_header.next_sibling
            
        current_category = None
        
        while current:
            if not hasattr(current, 'name'):
                current = current.next_sibling
                continue
            
            if current.name in ['h2', 'h3'] or (current.name == 'div' and 'mw-heading' in current.get('class', [])):
                break
            
            # Case A: Category Header followed by list (Modern format)
            # <p><b>Best Actor:</b></p> <ul><li>...</li></ul>
            if current.name == 'p':
                b = current.find('b')
                if b:
                    cat_text = b.get_text().lower()
                    if 'director' in cat_text and 'debut' not in cat_text: current_category = 'best-director'
                    elif 'actor' in cat_text and 'supporting' not in cat_text and 'breakthrough' not in cat_text: current_category = 'best-actor'
                    elif 'actress' in cat_text and 'supporting' not in cat_text and 'breakthrough' not in cat_text: current_category = 'best-actress'
                    elif ('best film' in cat_text or 'best picture' in cat_text) and 'foreign' not in cat_text: current_category = 'best-film'
                    else: current_category = None
            
            if current.name == 'ul' and current_category:
                for li in current.find_all('li', recursive=False):
                    links = li.find_all('a')
                    if links:
                        # Logic: Name usually first link, film second
                        name = links[0].get_text().strip()
                        if current_category == 'best-film':
                            # For best film, the name is the film
                            if name not in seen_films:
                                seen_films.add(name)
                                results['best-film'].append({'name': name, 'awards': {'nbr': 'Y'}})
                        else:
                            # For person awards
                            film = links[1].get_text().strip() if len(links) > 1 else None
                            entry = {'name': name, 'awards': {'nbr': 'Y'}}
                            if film: entry['film'] = film
                            results[current_category].append(entry)
                current_category = None
                
            # Case B: Single List with bolded categories (Older format)
            # <ul><li><b>Best Actor:</b> Name</li> ... </ul>
            if current.name == 'ul' and not current_category:
                for li in current.find_all('li', recursive=False):
                    text = li.get_text().lower()
                    b = li.find('b')
                    
                    cat = None
                    if 'best director' in text and 'debut' not in text: cat = 'best-director'
                    elif 'best actor' in text and 'supporting' not in text and 'breakthrough' not in text: cat = 'best-actor'
                    elif 'best actress' in text and 'supporting' not in text and 'breakthrough' not in text: cat = 'best-actress'
                    elif ('best film' in text or 'best picture' in text) and 'foreign' not in text: cat = 'best-film'
                    
                    if cat:
                        # Extract Content: "Category: Name" or "Category - Name"
                        # If <b> present, text after </b> is the winner
                        links = li.find_all('a')
                        
                        if cat == 'best-film':
                            # Identify the film link. It might be the first link AFTER the category b tag
                            # Or blindly take the last link? Risk of taking director name if listed.
                            # Usually: <b>Best Picture:</b> <i><a>Film</a></i>
                            for link in links:
                                name = link.get_text().strip()
                                # Filtering out "Best Picture" if it is linked (rare)
                                if 'best' not in name.lower() and name not in seen_films:
                                    seen_films.add(name)
                                    results['best-film'].insert(0, {'name': name, 'awards': {'nbr': 'Y'}}) # Winner first
                                    break
                        else:
                            # Person Category
                            # Expect: Name (Film) or Name - Film
                            # Typically Name is the first link found in the line (excluding category if linked)
                            winner_name = None
                            winner_film = None
                            
                            valid_links = [l for l in links if 'best' not in l.get_text().lower()]
                            if valid_links:
                                winner_name = valid_links[0].get_text().strip()
                                if len(valid_links) > 1:
                                    winner_film = valid_links[1].get_text().strip()
                                    
                            if winner_name:
                                entry = {'name': winner_name, 'awards': {'nbr': 'Y'}}
                                if winner_film: entry['film'] = winner_film
                                results[cat].append(entry)

            current = current.next_sibling
    
    total = sum(len(v) for v in results.values())
    print(f"    NBR {year}: Found {total} entries (Films: {len(results['best-film'])}, Dir: {len(results['best-director'])}, Actor: {len(results['best-actor'])}, Actress: {len(results['best-actress'])})")
    return results
