# -*- coding: utf-8 -*-
"""
LAFCA Awards Scraper
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

def scrape_lafca(year):
    """
    Scrape LAFCA (Los Angeles Film Critics Association) Awards for a specific year.
    
    Page structure:
    - Winners section with nested lists
    - Category header (Best Film:, Best Director:, etc.)
      - Winners in bold sub-list
        - Runner-ups in third-level list (treated as nominations)
    
    Performance categories are gender-neutral, so we detect gender via TMDB.
    """
    url = URL_TEMPLATES['lafca'].format(year=year)
    print(f"  LAFCA ({year}): {url}")
    
    soup = fetch_page(url)
    if not soup:
        return {}
    
    results = {
        'best-film': [],
        'best-director': [],
        'best-actor': [],
        'best-actress': []
    }
    
    seen = {
        'best-film': set(),
        'best-director': set(),
        'best-actor': set(),
        'best-actress': set()
    }
    
    # Global seen set to prevent duplicates across categories (e.g. Actor vs Actress)
    global_seen = set()  # Stores (name, film) tuples
    
    # Find Winners section - structure is <div><h2 id="Winners">Winners</h2></div>
    # The winners UL is NOT a direct sibling - it's further down in the DOM
    winners_h2 = soup.find('h2', id='Winners')
    if not winners_h2:
        # Fallback: search for h2 with Winners text
        for h2 in soup.find_all('h2'):
            if 'winners' in h2.get_text().lower():
                winners_h2 = h2
                break
    
    if not winners_h2:
        print(f"    LAFCA {year}: Could not find Winners section")
        return {}
    
    # Find the UL that contains "Best Film" or "Best Picture" (older format) - use find_next from the h2
    main_ul = None
    for ul in winners_h2.find_all_next('ul'):
        ul_text = ul.get_text().lower()
        if 'best film' in ul_text or 'best picture' in ul_text:
            main_ul = ul
            break
    
    if not main_ul:
        print(f"    LAFCA {year}: Could not find winners list")
        return {}
    
    # Categories to track
    category_map = {
        'best film': 'best-film',
        'best director': 'best-director',
        # Modern gender-neutral categories (2017+)
        'best lead performance': 'lead-performance',
        'best supporting performance': 'supporting-performance',
        'best leading performance': 'lead-performance',
        # Older year formats (pre-2017):
        'best picture': 'best-film',  # Alternative name for Best Film
        'best actor': 'best-actor',   # Direct mapping for older years
        'best actress': 'best-actress',  # Direct mapping for older years
        'best supporting actor': 'best-supporting-actor',  # Need special handling
        'best supporting actress': 'best-supporting-actress',  # Need special handling
    }
    
    # Process each top-level list item (categories)
    for li in main_ul.find_all('li', recursive=False):
        li_text = li.get_text().lower()
        
        # Determine category
        current_category = None
        is_performance = False
        performance_type = None
        
        for key, cat in category_map.items():
            # Use startswith with colon to prevent partial matches 
            # (e.g., "best actor" matching in "best lead performance")
            if li_text.startswith(key + ':') or li_text.startswith(key + ' '):
                # Explicitly exclude "Best Film Not in the English Language"
                if key == 'best film' and 'not in' in li_text:
                    continue

                if cat in ['lead-performance', 'supporting-performance']:
                    is_performance = True
                    performance_type = cat
                elif cat in ['best-supporting-actor', 'best-supporting-actress']:
                    # Map supporting actor/actress to main actor/actress categories
                    current_category = 'best-actor' if cat == 'best-supporting-actor' else 'best-actress'
                else:
                    current_category = cat
                break
        
        if not current_category and not is_performance:
            continue
        
        # Find winners and runner-ups in sub-lists
        sub_lists = li.find_all('ul', recursive=False)
        
        # Track first item to handle pages where winners aren't bolded (2012/2013)
        first_item_in_category = True
        
        for sub_ul in sub_lists:
            # Use recursive=True to find nested runner-ups (e.g., UL > LI > UL > LI)
            for sub_li in sub_ul.find_all('li'):
                # Check for "runner-up" or "runner up" (with/without hyphen) at the start of the text
                li_text_lower = sub_li.get_text().lower().strip()
                is_runner_up = li_text_lower.startswith('runner-up') or li_text_lower.startswith('runner up')
                
                # Find the first link (name)
                link = sub_li.find('a')
                if not link:
                    continue
                
                name = link.get_text().strip()
                if len(name) < 2:
                    continue
                
                # Get film (second link or from text after dash)
                film = None
                all_links = sub_li.find_all('a')
                if len(all_links) >= 2:
                    # For directors and actors, second link is usually the film
                    # BUT for Best Film, usually the first link is the movie, second might be irrelevant or runner-up?
                    # We should NOT treat it as "film" metadata for best-film category
                    if not is_performance and current_category == 'best-film':
                         film = None
                    else:
                         film = all_links[1].get_text().strip()
                
                # Determine if winner: the link itself has a bold parent (not just any b in the li)
                # Structure: <i><b><a>...</a></b></i> for winners, plain <a> for runner-ups
                is_bold_link = (link.parent and link.parent.name in ['b', 'strong']) or \
                               (link.parent and link.parent.parent and link.parent.parent.name in ['b', 'strong'])
                
                # Winner logic: bold OR first item (if not runner-up) for pages without bold
                if is_bold_link and not is_runner_up:
                    is_winner = True
                elif first_item_in_category and not is_runner_up:
                    # Fallback: treat first non-runner-up item as winner (for 2012/2013 style pages)
                    is_winner = True
                else:
                    is_winner = False
                
                first_item_in_category = False  # No longer first item
                
                if is_performance:
                    # Detect gender via TMDB
                    gender = get_person_gender(name)
                    
                    if gender == 1:  # Female
                        target_cat = 'best-actress'
                    elif gender == 2:  # Male
                        target_cat = 'best-actor'
                    else:
                        # Unknown (0 or 3) - try to guess from first name
                        first_name = name.split()[0].lower() if name.split() else ''
                        # Common female first names
                        female_names = {'lily', 'emma', 'sandra', 'rachel', 'davine', "da'vine", 
                                       'amanda', 'viola', 'carey', 'youn', 'jennifer', 'jessica',
                                       'meryl', 'nicole', 'cate', 'margot', 'anne', 'julia',
                                       'natalie', 'penelope', 'penélope', 'michelle', 'kate', 'helen'}
                        if first_name in female_names:
                            target_cat = 'best-actress'
                        else:
                            # Default to actor for truly unknown
                            print(f"    Warning: Unknown gender for {name}, defaulting to actor")
                            target_cat = 'best-actor'
                    
                    # Add role info
                    role = 'Leading' if performance_type == 'lead-performance' else 'Supporting'
                    
                    unique_key = (name, film or '')
                    
                    # Check global seen to prevent duplicates (blocking by name to avoid film mismatch duplicates)
                    # We check if name is already processed for this award
                    if name in global_seen:
                        continue
                        
                    if unique_key not in seen[target_cat]:
                        seen[target_cat].add(unique_key)
                        global_seen.add(name)
                        
                        entry = {
                            'name': name,
                            'awards': {'lafca': 'Y' if is_winner else 'X'},
                            'role': role
                        }
                        if film:
                            entry['film'] = film
                        results[target_cat].append(entry)
                else:
                    # Film or Director category
                    unique_key = (name, film or '')
                    
                    if unique_key not in seen[current_category]:
                        seen[current_category].add(unique_key)
                        # No need to add to global_seen for film/director as they are distinct categories
                        
                        entry = {
                            'name': name, 
                            'awards': {'lafca': 'Y' if is_winner else 'X'}
                        }
                        if film:
                            entry['film'] = film
                        results[current_category].append(entry)
                        
    # Post-processing: Ensure no overlap between actor and actress (fix for gender detection edge cases)
    # If a person is in best-actress, remove them from best-actor (as actress detection is more specific via name fallback)
    actress_names = {entry['name'] for entry in results.get('best-actress', [])}
    if results.get('best-actor'):
        results['best-actor'] = [e for e in results['best-actor'] if e['name'] not in actress_names]
    
    total = sum(len(v) for v in results.values())
    print(f"    LAFCA {year}: Found {total} entries (Films: {len(results['best-film'])}, Dir: {len(results['best-director'])}, Actor: {len(results['best-actor'])}, Actress: {len(results['best-actress'])})")
    return results


