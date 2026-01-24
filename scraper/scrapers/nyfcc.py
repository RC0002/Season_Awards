# -*- coding: utf-8 -*-
"""
NYFCC Awards Scraper
New York Film Critics Circle Awards
"""

from . import CEREMONY_MAP, URL_TEMPLATES, fetch_page, ordinal, init_results


def scrape_nyfcc(year):
    """
    Scrape NYFCC (New York Film Critics Circle) Awards for a specific year.
    2025: Standard structure (H2 Winners -> UL -> LI)
    2008/2009: Legacy structure (H3 Header -> OL -> LI)
    """
    # Use CEREMONY_MAP to get the correct year for URL (e.g. System 2009 -> NYFCC 2008)
    if 'nyfcc' in CEREMONY_MAP and year in CEREMONY_MAP['nyfcc']:
        nyfcc_year = CEREMONY_MAP['nyfcc'][year]
    else:
        print(f"    Warning: No mapping for year {year}, using raw year.")
        nyfcc_year = year
        
    url = URL_TEMPLATES['nyfcc'].format(year=nyfcc_year)
    print(f"  NYFCC ({nyfcc_year}): {url}")
    
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
    
    # Categories to track
    category_config = {
        'best film': ('best-film', False),
        'best picture': ('best-film', False),
        'best director': ('best-director', True),
        'best actor': ('best-actor', True),
        'best actress': ('best-actress', True),
        'best supporting actor': ('best-actor', True),
        'best supporting actress': ('best-actress', True),
    }

    # Strategy 1: Find "Winners" H2 and look for UL lists (Modern format)
    winners_h2 = None
    for h2 in soup.find_all('h2'):
        span = h2.find('span', id='Winners')
        if span:
            winners_h2 = h2
            break
        if 'winners' in h2.get_text().lower():
            winners_h2 = h2
            break
            
    if winners_h2:
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

    # Strategy 2: H3 Parsing (Legacy format like 2008/2009)
    total_found = sum(len(v) for v in results.values())
    
    if total_found == 0:
        print(f"    NYFCC {year}: Standard parsing found 0. Trying legacy H3+OL format...")

        # Structure: <h3>Best Film</h3> <ol><li>Winner</li></ol>
        # Iterate all H3 in content
        all_h3 = soup.find_all('h3')
        print(f"    Debug: Found {len(all_h3)} H3 headers")
        
        for h3 in all_h3:
            header_text = h3.get_text().strip().lower()
            # print(f"    Debug: H3 text = '{header_text}'")
            
            # Identify category
            current_category = None
            is_person = False
            role = None
            
            for key, (cat, person_flag) in category_config.items():
                if key == header_text or header_text.startswith(key):
                    current_category = cat
                    is_person = person_flag
                    if 'supporting' in key:
                        role = 'Supporting'
                    elif cat in ['best-actor', 'best-actress']:
                        role = 'Leading'
                    break
            
            if not current_category:
                continue
                
            # Robust strategy to find associated list or paragraph:
            # Find the very next OL/UL/P in document order.
            # Verify it belongs to this header by checking if its previous header is this one.
            next_list = h3.find_next(['ol', 'ul', 'p'])
            
            if not next_list:
                print(f"    Debug: No list (ol/ul/p) found anywhere after H3 '{header_text}'")
                continue
                
            # Verify ownership
            prev_h3_of_list = next_list.find_previous('h3')
            
            if prev_h3_of_list != h3:
                print(f"    Debug: List/P belongs to different header '{prev_h3_of_list.get_text().strip()}'")
                continue
            
            # Extract content
            first_li = None
            if next_list.name in ['ol', 'ul']:
                first_li = next_list.find('li')
            elif next_list.name == 'p':
                # Treat 'p' as the 'li' content carrier
                first_li = next_list
            
            if not first_li:
                continue
                
            # Parse LI or P content
            winner_name = ""
            film_name = None
            
            # Text cleaning: Get first line only, remove header lines
            extracted_text = first_li.get_text().strip()
            if '\n' in extracted_text:
                extracted_text = extracted_text.split('\n')[0].strip()
            
            # Remove leading numbering "1. "
            import re
            extracted_text = re.sub(r'^\d+\.\s*', '', extracted_text)
            
            # Logic for Person vs Film
            if is_person:
                # Try to split by dash
                parts = extracted_text.split('–') # En dash
                if len(parts) < 2:
                    parts = extracted_text.split('-') # Hyphen
                
                if len(parts) >= 2:
                    winner_name = parts[0].strip()
                    film_name = parts[1].strip()
                else:
                    winner_name = extracted_text
                    # Try to find film in italics if inside valid tag (not P text)
                    if hasattr(first_li, 'find') and first_li.find('i'):
                        i_tag = first_li.find('i')
                        film_text = i_tag.get_text().strip()
                        if film_text and film_text in winner_name:
                             winner_name = winner_name.replace(film_text, '').strip(' -–,')
                        if not film_name:
                            film_name = film_text
            else:
                # Film
                winner_name = extracted_text
            
            # Verify we didn't get a header
            if winner_name.lower().startswith('winner'):
                 continue
                
            # Constraints
            if '<' in winner_name: # Simple HTML strip fallback
                 from bs4 import BeautifulSoup as BS
                 winner_name = BS(winner_name, "html.parser").get_text()

            # Cleanup film name in winner name (common issue)
            if film_name and film_name in winner_name:
                 winner_name = winner_name.replace(film_name, '').strip(' -–,')
            
            if winner_name:
                unique_key = (winner_name, film_name or '')
                if unique_key not in seen[current_category]:
                    seen[current_category].add(unique_key)
                    entry = {
                        'name': winner_name,
                        'awards': {'nyfcc': 'Y'}
                    }
                    if film_name:
                        entry['film'] = film_name
                    if role:
                        entry['role'] = role
                    results[current_category].append(entry)
    
    total = sum(len(v) for v in results.values())
    print(f"    NYFCC {year}: Found {total} entries (Films: {len(results['best-film'])}, Dir: {len(results['best-director'])}, Actor: {len(results['best-actor'])}, Actress: {len(results['best-actress'])})")
    return results
