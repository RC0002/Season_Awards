# -*- coding: utf-8 -*-
"""
NYFCC Awards Scraper
New York Film Critics Circle Awards
"""

from . import CEREMONY_MAP, URL_TEMPLATES, fetch_page, ordinal, init_results


def scrape_nyfcc(year):
    """
    Scrape NYFCC (New York Film Critics Circle) Awards for a specific year.
    
    Page structure (based on 2025):
    - Winners section with multiple UL elements
    - Each category has its own UL with format:
      <ul><li>Category Name:\n<ul><li>Winner - Film</li></ul></li></ul>
    - For actors, format is: "Name – Film Title" (with en-dash)
    
    Only one winner per category (no nominees), all marked as winners.
    """
    url = URL_TEMPLATES['nyfcc'].format(year=year)
    print(f"  NYFCC ({year}): {url}")
    
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
    
    # Find Winners section
    winners_h2 = None
    for h2 in soup.find_all('h2'):
        span = h2.find('span', id='Winners')
        if span:
            winners_h2 = h2
            break
        if 'winners' in h2.get_text().lower():
            winners_h2 = h2
            break
    
    if not winners_h2:
        print(f"    NYFCC {year}: Could not find Winners section")
        return {}
    
    # Categories to track - map category text to result key and whether it's a person
    category_config = {
        'best film': ('best-film', False),
        'best picture': ('best-film', False),
        'best director': ('best-director', True),
        'best actor': ('best-actor', True),
        'best actress': ('best-actress', True),
        'best supporting actor': ('best-actor', True),
        'best supporting actress': ('best-actress', True),
    }
    
    # Find all ULs after Winners heading until we hit another section
    for ul in winners_h2.find_all_next('ul'):
        # Stop if we hit another section (h2)
        prev_h2 = ul.find_previous('h2')
        if prev_h2 != winners_h2:
            break
        
        # Each UL contains category items
        for li in ul.find_all('li', recursive=False):
            li_text = li.get_text().strip()
            li_text_lower = li_text.lower()
            
            # Check if this is a category header
            current_category = None
            is_person = False
            role = None
            
            for key, (cat, person_flag) in category_config.items():
                if li_text_lower.startswith(key + ':') or li_text_lower.startswith(key + '\n'):
                    current_category = cat
                    is_person = person_flag
                    if 'supporting' in key:
                        role = 'Supporting'
                    elif cat in ['best-actor', 'best-actress']:
                        role = 'Leading'
                    break
            
            if not current_category:
                continue
            
            # Find winner in nested ul - only take FIRST item (winner), skip runner-ups
            sub_ul = li.find('ul')
            if sub_ul:
                # Only process the first li (winner), ignore runner-ups
                first_li = sub_ul.find('li', recursive=False)
                if first_li:
                    # Find the first link (name for persons, or film title for best-film)
                    link = first_li.find('a')
                    if not link:
                        continue
                    
                    name = link.get_text().strip()
                    if len(name) < 2:
                        continue
                    
                    # Get film from italic tag or second link (for persons)
                    film = None
                    if is_person:
                        # Look for italic link (film title)
                        i_tag = first_li.find('i')
                        if i_tag:
                            i_link = i_tag.find('a')
                            if i_link:
                                film = i_link.get_text().strip()
                            else:
                                film = i_tag.get_text().strip()
                        else:
                            # Fallback: second link
                            all_links = first_li.find_all('a')
                            if len(all_links) >= 2:
                                film = all_links[1].get_text().strip()
                    
                    # NYFCC only has winners, all are 'Y'
                    unique_key = (name, film or '')
                    
                    if unique_key not in seen[current_category]:
                        seen[current_category].add(unique_key)
                        
                        entry = {
                            'name': name,
                            'awards': {'nyfcc': 'Y'}
                        }
                        if film:
                            entry['film'] = film
                        if role:
                            entry['role'] = role
                        results[current_category].append(entry)
    
    total = sum(len(v) for v in results.values())
    print(f"    NYFCC {year}: Found {total} entries (Films: {len(results['best-film'])}, Dir: {len(results['best-director'])}, Actor: {len(results['best-actor'])}, Actress: {len(results['best-actress'])})")
    return results
