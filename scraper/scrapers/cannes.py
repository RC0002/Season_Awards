# -*- coding: utf-8 -*-
"""
CANNES Film Festival Awards Scraper
"""

from . import CEREMONY_MAP, URL_TEMPLATES, fetch_page, ordinal, init_results

def scrape_cannes(year):
    """
    Scrape Cannes Film Festival from English Wikipedia.
    Extracts from 'Official awards' > 'In Competition' section:
    - Palme d'Or (best film)
    - Best Director
    - Best Actor
    - Best Actress
    
    Args:
        year: Calendar year of Cannes (e.g., 2024 for Cannes 2024)
    
    Returns:
        dict: Results with best-film, best-director, best-actor, best-actress
    """
    url = f"https://en.wikipedia.org/wiki/{year}_Cannes_Film_Festival"
    print(f"  CANNES ({year}): {url}")
    
    soup = fetch_page(url)
    if not soup:
        return {}
    
    results = {
        'best-film': [],
        'best-director': [],
        'best-actor': [],
        'best-actress': []
    }
    
    # Find 'Official awards' section
    official_awards_h2 = None
    for h2 in soup.find_all('h2'):
        span = h2.find('span', id='Official_awards')
        if span:
            official_awards_h2 = h2
            break
        # Fallback: check text
        if 'official awards' in h2.get_text().lower():
            official_awards_h2 = h2
            break
    
    if not official_awards_h2:
        print(f"    Cannes: 'Official awards' section not found")
        return results
    
    # Find 'In Competition' subsection (h3)
    in_competition_h3 = None
    current = official_awards_h2.parent.next_sibling
    
    while current:
        if not hasattr(current, 'name'):
            current = current.next_sibling
            continue
        
        # Stop at next h2 section
        if current.name == 'h2':
            break
        
        # Look for h3 with 'In Competition'
        if current.name == 'h3':
            span = current.find('span', id='In_Competition')
            if span:
                in_competition_h3 = current
                break
            # Fallback: check text
            if 'in competition' in current.get_text().lower():
                in_competition_h3 = current
                break
        
        # For newer Wikipedia structure, h3 might be inside a div
        if current.name == 'div':
            h3 = current.find('h3')
            if h3:
                span = h3.find('span', id='In_Competition')
                if span or 'in competition' in h3.get_text().lower():
                    in_competition_h3 = h3
                    break
        
        current = current.next_sibling
    
    if not in_competition_h3:
        print(f"    Cannes: 'In Competition' section not found")
        return results
    
    # Parse list items after In Competition header
    container = in_competition_h3.parent
    current = container.next_sibling
    
    while current:
        if not hasattr(current, 'name'):
            current = current.next_sibling
            continue
        
        # Stop at next h2/h3 section
        if current.name in ['h2', 'h3']:
            break
        if current.name == 'div' and 'mw-heading' in str(current.get('class', [])):
            break
        
        # Process UL
        if current.name == 'ul':
            for li in current.find_all('li', recursive=False):
                li_text = li.get_text().lower()
                
                # Determine category
                category = None
                if "palme d'or" in li_text or "palme d'or" in li_text:
                    category = 'best-film'
                elif 'best director' in li_text:
                    category = 'best-director'
                elif 'best actor' in li_text and 'actress' not in li_text:
                    category = 'best-actor'
                elif 'best actress' in li_text:
                    category = 'best-actress'
                
                if not category:
                    continue
                
                # Extract information
                # Structure: "Award: Name(s) by Director for Film"
                # or "Award: Name(s) for Film"
                
                links = li.find_all('a')
                if not links:
                    continue
                
                # For film category
                if category == 'best-film':
                    # First link is usually the film
                    film_name = links[0].get_text().strip()
                    
                    # Sometimes it's "Palme d'Or: Film by Director"
                    # Try to get film from italic tag if present
                    i_tag = li.find('i')
                    if i_tag:
                        film_name = i_tag.get_text().strip()
                    
                    if film_name and len(film_name) >= 2:
                        entry = {
                            'name': film_name,
                            'awards': {'cannes': 'Y'}
                        }
                        
                        # Try to extract director as note
                        # Look for "by Name" pattern
                        if ' by ' in li.get_text():
                            by_idx = li.get_text().index(' by ')
                            remaining = li.get_text()[by_idx+4:]
                            # Find first link after "by"
                            for link in links[1:]:
                                link_text = link.get_text().strip()
                                if link_text in remaining:
                                    entry['note'] = f"Director: {link_text}"
                                    break
                        
                        results['best-film'].append(entry)
                
                # For person categories (director, actor, actress)
                else:
                    # Check for nested list structure (multiple winners)
                    nested_ul = li.find('ul')
                    
                    if nested_ul:
                        # Multiple winners - each in their own nested <li>
                        # Structure: Best Actor:
                        #   <ul>
                        #     <li>Person1 for <i>Film1</i></li>
                        #     <li>Person2 for <i>Film2</i></li>
                        #   </ul>
                        for nested_li in nested_ul.find_all('li', recursive=False):
                            # Extract person and film from each nested item
                            nested_links = nested_li.find_all('a')
                            if not nested_links:
                                continue
                            
                            # Film is always in <i> tag
                            film_name = None
                            i_tag = nested_li.find('i')
                            if i_tag:
                                film_link = i_tag.find('a')
                                if film_link:
                                    film_name = film_link.get_text().strip()
                            
                            # Person is the first link NOT in <i> tag
                            person_name = None
                            for link in nested_links:
                                # Skip if link is inside <i> tag (it's a film)
                                if link.find_parent('i'):
                                    continue
                                
                                link_text = link.get_text().strip()
                                link_title = link.get('title', '').lower()
                                
                                # Skip award names
                                if any(skip in link_text.lower() for skip in ['best director', 'best actor', 'best actress']):
                                    continue
                                
                                # Skip disambiguation pages
                                if 'disambiguation' in link_title or link_title.startswith('category:'):
                                    continue
                                
                                # This is the person
                                person_name = link_text
                                break
                            
                            if person_name:
                                entry = {
                                    'name': person_name,
                                    'awards': {'cannes': 'Y'}
                                }
                                if film_name:
                                    entry['film'] = film_name
                                results[category].append(entry)
                    
                    else:
                        # Single winner - direct in LI (not nested list)
                        # Structure: "Best Actor: Name for Film"
                        # OR multi-winner comma-separated: "Best Actress: Name1, Name2, Name3, and Name4 for Film"
                        film_name = None
                        i_tag = li.find('i')
                        if i_tag:
                            # Case 1: <i><a>Film</a></i> - link inside italic
                            film_link = i_tag.find('a')
                            if film_link:
                                film_name = film_link.get_text().strip()
                            else:
                                # Case 2: <a><i>Film</i></a> - italic inside link (Wikipedia uses this)
                                film_name = i_tag.get_text().strip()
                        
                        # Collect ALL valid person names (not just the first one)
                        # This handles comma-separated format like "Name1, Name2, Name3, and Name4 for Film"
                        skip_texts = ['best director', 'best actor', 'best actress']
                        persons_found = []
                        
                        for link in links:
                            # Skip if link is inside <i> tag (it's a film)
                            if link.find_parent('i'):
                                continue
                            
                            link_text = link.get_text().strip()
                            link_title = link.get('title', '').lower()
                            
                            if any(skip in link_text.lower() for skip in skip_texts):
                                continue
                            if 'disambiguation' in link_title or link_title.startswith('category:'):
                                continue
                            
                            # Valid person name
                            if len(link_text) >= 2:
                                persons_found.append(link_text)
                        
                        # Add all found persons as separate entries
                        for person_name in persons_found:
                            entry = {
                                'name': person_name,
                                'awards': {'cannes': 'Y'}
                            }
                            if film_name:
                                entry['film'] = film_name
                            results[category].append(entry)
        
        current = current.next_sibling
    
    total = sum(len(v) for v in results.values())
    print(f"    Cannes {year}: Found {total} entries (Films: {len(results['best-film'])}, Dir: {len(results['best-director'])}, Actor: {len(results['best-actor'])}, Actress: {len(results['best-actress'])})")
    return results
