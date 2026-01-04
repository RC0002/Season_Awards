# -*- coding: utf-8 -*-
"""
GOTHAM Awards Scraper
"""

from . import CEREMONY_MAP, URL_TEMPLATES, fetch_page, ordinal, init_results

import time
TMDB_API_KEY = "4399b8147e098e80be332f172d1fe490"
TMDB_BASE_URL = "https://api.themoviedb.org/3"

def get_person_gender(name, tmdb_api_key='4399b8147e098e80be332f172d1fe490'):
    """Get gender of a person using TMDB API. Returns: 1 = Female, 2 = Male, 0 = Unknown"""
    import requests
    try:
        url = f"{TMDB_BASE_URL}/search/person"
        params = {'api_key': tmdb_api_key, 'query': name}
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            results = response.json().get('results', [])
            if results:
                return results[0].get('gender', 0)
    except:
        pass
    return 0

def scrape_gotham(year):
    """
    Scrape Gotham Independent Film Awards for a specific year.
    
    Page structure: Wikitable with cells per category.
    Each cell has:
    - <div> with category header (e.g., "Best Feature")
    - <ul> with 1 li = winner info
    - Nested <ul> inside that li with other nominees
    
    Categories:
    - Best Feature (10 nominees)
    - Best Director (5 nominees)  
    - Outstanding Lead Performance (10 nominees, gender-neutral)
    - Outstanding Supporting Performance (10 nominees, gender-neutral)
    
    Performance categories are gender-neutral, so we detect gender via TMDB.
    """
    import re
    
    gotham_year = CEREMONY_MAP['gotham'][year]
    url = URL_TEMPLATES['gotham'].format(year=gotham_year)
    
    print(f"  GOTHAM ({gotham_year}): {url}")
    
    soup = fetch_page(url)
    if not soup:
        return {}
    
    return scrape_gotham_v2_logic(soup)
    
    results = {
        'best-film': [],
        'best-director': [],
        'best-actor': [],
        'best-actress': []
    }
    
    seen = {'film': set(), 'director': set(), 'actor': set(), 'actress': set()}
    
    # Find the main wikitable (first one with nominees)
    tables = soup.find_all('table', class_='wikitable')
    if not tables:
        print("    No wikitable found")
        return results
    
    main_table = tables[0]
    
    # Process each cell
    cells = main_table.find_all(['th', 'td'])
    
    for cell in cells:
        # Get category from div header or first text
        div = cell.find('div')
        if not div:
            continue
            
        category_text = div.get_text().strip().lower()
        
        # Determine which category this is
        category_type = None
        if 'best feature' in category_text:
            category_type = 'best-film'
        elif 'best director' in category_text:
            category_type = 'best-director'
        elif 'lead performance' in category_text or 'outstanding lead' in category_text:
            category_type = 'lead-performance'
        elif 'supporting performance' in category_text or 'outstanding supporting' in category_text:
            category_type = 'supporting-performance'
        else:
            continue  # Skip other categories
        
        # Find all ul lists in this cell
        all_uls = cell.find_all('ul')
        if not all_uls:
            continue
        
        # First ul contains winner (usually 1 item)
        # That li may have nested ul with nominees
        first_ul = all_uls[0]
        top_li = first_ul.find('li', recursive=False)
        
        if top_li:
            # Extract winner info
            winner_text = ""
            # Get text before any nested ul
            for item in top_li.children:
                if hasattr(item, 'name') and item.name == 'ul':
                    break
                if hasattr(item, 'get_text'):
                    winner_text += item.get_text()
                else:
                    winner_text += str(item)
            
            winner_text = winner_text.strip()
            
            # Parse winner_text (format: "Film Name – Person, Person, producers")
            # or for directors: "Person Name – Film Name"
            if winner_text:
                # Clean up
                winner_text = re.sub(r'\[.*?\]', '', winner_text).strip()
                
                # Split on separator
                parts = re.split(r'\s*[–—-]\s*', winner_text, 1)
                
                if category_type == 'best-film':
                    film_name = parts[0].strip()
                    if film_name and film_name not in seen['film']:
                        seen['film'].add(film_name)
                        results['best-film'].append({
                            'name': film_name,
                            'awards': {'gotham': 'Y'}
                        })
                        
                elif category_type == 'best-director':
                    person_name = parts[0].strip()
                    film_name = parts[1].strip() if len(parts) > 1 else None
                    if person_name and person_name not in seen['director']:
                        seen['director'].add(person_name)
                        entry = {
                            'name': person_name,
                            'awards': {'gotham': 'Y'}
                        }
                        if film_name:
                            entry['film'] = film_name
                        results['best-director'].append(entry)
                        
                elif category_type in ['lead-performance', 'supporting-performance']:
                    person_name = parts[0].strip()
                    film_name = parts[1].strip() if len(parts) > 1 else None
                    if person_name:
                        gender = get_person_gender(person_name)
                        cat = 'actress' if gender == 1 else 'actor'
                        if person_name not in seen[cat]:
                            seen[cat].add(person_name)
                            entry = {
                                'name': person_name,
                                'awards': {'gotham': 'Y'}
                            }
                            if film_name:
                                entry['film'] = film_name
                            results[f'best-{cat}'].append(entry)
            
            # Now get nominees from nested ul
            nested_ul = top_li.find('ul')
            if nested_ul:
                for li in nested_ul.find_all('li', recursive=False):
                    nominee_text = li.get_text().strip()
                    nominee_text = re.sub(r'\[.*?\]', '', nominee_text).strip()
                    
                    # Split on separator
                    parts = re.split(r'\s*[–—-]\s*', nominee_text, 1)
                    
                    if category_type == 'best-film':
                        film_name = parts[0].strip()
                        if film_name and film_name not in seen['film']:
                            seen['film'].add(film_name)
                            results['best-film'].append({
                                'name': film_name,
                                'awards': {'gotham': 'X'}
                            })
                            
                    elif category_type == 'best-director':
                        person_name = parts[0].strip()
                        film_name = parts[1].strip() if len(parts) > 1 else None
                        if person_name and person_name not in seen['director']:
                            seen['director'].add(person_name)
                            entry = {
                                'name': person_name,
                                'awards': {'gotham': 'X'}
                            }
                            if film_name:
                                entry['film'] = film_name
                            results['best-director'].append(entry)
                            
                    elif category_type in ['lead-performance', 'supporting-performance']:
                        person_name = parts[0].strip()
                        film_name = parts[1].strip() if len(parts) > 1 else None
                        if person_name:
                            gender = get_person_gender(person_name)
                            cat = 'actress' if gender == 1 else 'actor'
                            if person_name not in seen[cat]:
                                seen[cat].add(person_name)
                                entry = {
                                    'name': person_name,
                                    'awards': {'gotham': 'X'}
                                }
                                if film_name:
                                    entry['film'] = film_name
                                results[f'best-{cat}'].append(entry)
    
    total = len(results['best-film']) + len(results['best-director']) + len(results['best-actor']) + len(results['best-actress'])
    print(f"    Gotham {gotham_year}: Found {total} entries (Films: {len(results['best-film'])}, Dir: {len(results['best-director'])}, Actor: {len(results['best-actor'])}, Actress: {len(results['best-actress'])})")
    
    return results

