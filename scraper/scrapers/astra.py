# -*- coding: utf-8 -*-
"""
ASTRA Awards Scraper
"""

from . import CEREMONY_MAP, URL_TEMPLATES, fetch_page, ordinal, init_results

def scrape_astra(year):
    """
    Scrape Astra Film Awards (formerly HCA) for a specific year.
    Year >= 2025 (Season 2024/25) -> Astra 8th+
    Year 2024 (Season 2023/24) -> Astra 7th (Wiki says '7th Astra Film Awards')
    Year <= 2023 -> Hollywood Critics Association (HCA)
    Mapping:
      2026 (Season 2025/26) -> 9th
      2025 (Season 2024/25) -> 8th
      2024 (Season 2023/24) -> 7th (Astra)
      2023 (Season 2022/23) -> 6th (HCA)
    """
    ceremony_num = CEREMONY_MAP['astra'].get(year)
    if not ceremony_num:
        print(f"  No Astra/HCA mapping for year {year}")
        return {}

    ord_str = ordinal(ceremony_num)
    
    # URL construction based on name change
    if ceremony_num >= 7:
        # Astra
        url = f"https://en.wikipedia.org/wiki/{ord_str}_Astra_Film_Awards"
    else:
        # HCA
        url = f"https://en.wikipedia.org/wiki/{ord_str}_Hollywood_Critics_Association_Film_Awards"
    
    print(f"  ASTRA/HCA ({ord_str}): {url}")
    
    soup = fetch_page(url)
    if not soup:
        return {}
    
    # Logic is very similar to Gotham V2 (List-based cells)
    return scrape_astra_logic(soup)


def scrape_astra_logic(soup):
    import re
    
    results = {
        'best-film': [],
        'best-director': [],
        'best-actor': [],
        'best-actress': []
    }
    
    seen = {'film': set(), 'director': set(), 'actor': set(), 'actress': set()}
    
    tables = soup.find_all('table', class_='wikitable')
    if not tables:
        print("    No wikitable found (Astra logic)")
        # Try generic search for tables without class if wikitable missing?
        tables = soup.find_all('table')
        if not tables:
             return results
    
    for table in tables:
        # Skip summary tables if any (usually 'Wins' 'Nominations')
        header_text = ' '.join([th.get_text().strip().lower() for th in table.find_all('th')])
        if 'wins' in header_text and 'nominations' in header_text:
            continue
            
        rows = table.find_all('tr')
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            for cell in cells:
                # 1. Determine Category from Header (first non-empty text node/line)
                cell_text = cell.get_text(separator='|').strip()
                if not cell_text: continue
                
                # Split by | to check first part
                parts_text = [p.strip() for p in cell_text.split('|') if p.strip()]
                if not parts_text: continue
                
                cat_header = parts_text[0].lower()
                
                cat_found = None
                # Best Picture/Film categories (drama, comedy, musical all map to best-film)
                if 'best picture' in cat_header or 'best film' in cat_header:
                    # Exclude animated, international, action, horror, indie, first feature
                    if not any(x in cat_header for x in ['animated', 'international', 'action', 'editing', 'horror', 'indie', 'first']):
                        cat_found = 'best-film'
                elif 'best director' in cat_header:
                     cat_found = 'best-director'
                # Actor categories: leading and supporting, drama and comedy/musical all map to best-actor
                elif 'actor' in cat_header and ('best' in cat_header or 'supporting' in cat_header):
                    # Exclude voice over and youth categories (23 and under)
                    if 'voice' not in cat_header and '23' not in cat_header and 'under' not in cat_header:
                        cat_found = 'best-actor'
                # Actress categories: leading and supporting, drama and comedy/musical all map to best-actress
                elif 'actress' in cat_header and ('best' in cat_header or 'supporting' in cat_header):
                    # Exclude voice over and youth categories (23 and under)
                    if 'voice' not in cat_header and '23' not in cat_header and 'under' not in cat_header:
                        cat_found = 'best-actress'
                
                if not cat_found:
                    continue
                
                # 2. Extract Nominees using UL/LI if available
                nominees_raw = []
                
                uls = cell.find_all('ul')
                if uls and not cell.find_parent('ul'): # Ensure we are not inside another list
                     # Use the first UL if found
                     # Check if cell has text content before UL that indicates category
                     # (Already checked cat_header)
                     
                     # Process first UL
                     # Structure: 
                     # LI (Winner)
                     #   UL
                     #     LI (Nominee)
                     
                     # Or flat list
                     
                     top_ul = uls[0]
                     top_lis = top_ul.find_all('li', recursive=False)
                     
                     for li in top_lis:
                         # Check for nested UL
                         nested_ul = li.find('ul')
                         
                         # Get text of this LI (excluding nested UL text)
                         own_text = ""
                         for child in li.children:
                             if child.name == 'ul': break
                             own_text += child.get_text()
                         
                         own_text = own_text.strip()
                         if not own_text: continue
                         
                         # Is this a winner?
                         # Usually top LI (lines 1-x) are winners, nested are nominees
                         # But sometimes flat list with bolds.
                         
                         # Check logical winner status:
                         # If it has a nested UL, it is likely the winner.
                         is_winner_li = bool(nested_ul) or bool(li.find('b', recursive=False)) or bool(li.find('b'))
                         # Wait, simplistic bold check is fine if the name is wrapped in bold
                         
                         # Add this top item
                         nominees_raw.append((own_text, is_winner_li))
                         
                         # Add nested items (Nominees)
                         if nested_ul:
                             for sub_li in nested_ul.find_all('li'):
                                 sub_text = sub_li.get_text().strip()
                                 if sub_text:
                                     nominees_raw.append((sub_text, False))
                else:
                    # Fallback to line splitting if no UL found
                    # But use the parts_text from before (split by pipe or newline)
                    # Skip the first part (Header)
                    lines = parts_text[1:]
                    # Check bolds in cell
                    winners_text = [b.get_text().strip() for b in cell.find_all('b')]
                    
                    for line in lines:
                        # Check if line matches a winner text
                        is_w = any(line in w or w in line for w in winners_text if len(w) > 3)
                        nominees_raw.append((line, is_w))

                # 3. Process Raw Nominees
                for nom_text, is_winner in nominees_raw:
                    # Clean brackets
                    nom_text = re.sub(r'\[.*?\]', '', nom_text).strip()
                    if not nom_text: continue
                    if nom_text.lower() in [cat_header, 'winner', 'winners', 'nominees']: continue

                    award_val = 'Y' if is_winner else 'X'
                    
                    # Delimiter handling (Endash, Emdash, Hyphen)
                    parts = re.split(r'\s*[–—-]\s*', nom_text)
                    
                    if cat_found == 'best-film':
                        film_name = parts[0].strip()
                        if film_name and len(film_name) > 1 and film_name not in seen['film']:
                            seen['film'].add(film_name)
                            results['best-film'].append({'name': film_name, 'awards': {'astra': award_val}})
                            
                    elif cat_found == 'best-director':
                        # Format: Person - Film
                        person_name = parts[0].strip()
                        film_name = parts[1].strip() if len(parts) > 1 else ""
                        
                        if person_name:
                            entry = {'name': person_name, 'awards': {'astra': award_val}}
                            if film_name: entry['film'] = film_name
                            results['best-director'].append(entry)
                    
                    elif cat_found in ['best-actor', 'best-actress', 'supporting-actor', 'supporting-actress']:
                        # Format: Person - Film as Role
                        person_name = parts[0].strip()
                        
                        rest = parts[1].strip() if len(parts) > 1 else ""
                        film_name = rest
                        if " as " in rest:
                            film_name = rest.split(" as ")[0].strip()
                        
                         # Determine category mapping
                        target_cat = 'best-actor'
                        seen_key = 'actor'
                        
                        if cat_found == 'best-actress' or cat_found == 'supporting-actress':
                            target_cat = 'best-actress'
                            seen_key = 'actress'

                        if person_name:
                             entry = {'name': person_name, 'awards': {'astra': award_val}}
                             if film_name: entry['film'] = film_name
                             results[target_cat].append(entry)

    total = sum(len(v) for v in results.values())
    print(f"    ASTRA/HCA: Found {total} entries (Films: {len(results['best-film'])}, Dir: {len(results['best-director'])})")
    return results

