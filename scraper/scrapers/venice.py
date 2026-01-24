# -*- coding: utf-8 -*-
"""
VENICE Awards Scraper
"""

from . import CEREMONY_MAP, URL_TEMPLATES, fetch_page, ordinal, init_results

def scrape_venice(ceremony_num):
    """
    Scrape Venice Film Festival (Mostra di Venezia) from Italian Wikipedia.
    Extracts from 'Premi della selezione ufficiale' > 'Concorso' section:
    - Leone d'oro (best film)
    - Leone d'argento - regia (best director)
    - Coppa Volpi maschile (best actor)
    - Coppa Volpi femminile (best actress)
    """
    url = URL_TEMPLATES['venice'].format(ord=ceremony_num)
    print(f"  VENICE ({ceremony_num}th): {url}")
    
    soup = fetch_page(url)
    if not soup:
        return {}
    
    results = {
        'best-film': [],
        'best-director': [],
        'best-actor': [],
        'best-actress': []
    }
    
    # Find Awards Section
    # Strategy:
    # 1. Look for specific H3 "Premi della selezione ufficiale" (standard modern)
    # 2. Look for H3 "Premi principali" (some years like 2011)
    # 3. Look for H2 "Premi" or "Giuria e Premi" and parse children (older years)
    
    premi_section = None
    
    # 1. Try specific H3 IDs/Text
    candidates_h3 = [
        'Premi_della_selezione_ufficiale',
        'Premi_ufficiali',
        'Premi_principali',
        'Concorso'
    ]
    
    for c_id in candidates_h3:
        premi_section = soup.find('h3', id=c_id)
        if premi_section: break
        
    if not premi_section:
        # Fallback: search by text
        for h3 in soup.find_all('h3'):
            text = h3.get_text().lower()
            if ('premi' in text and ('selezione' in text or 'ufficiali' in text or 'principali' in text)) or \
               ('leone' in text and "d'oro" in text):
                premi_section = h3
                break

    # 2. If not found, look for H2 "Premi" or "Giuria e premi"
    start_from_h2 = False
    if not premi_section:
        for h2 in soup.find_all('h2'):
            text = h2.get_text().lower()
            if text in ['premi', 'giuria e premi', 'premi ufficiali', 'i premi']:
                premi_section = h2
                start_from_h2 = True
                break
                
    if not premi_section:
        print(f"    Venice: Awards section header not found")
        return results

    import re

    # Helper function to parse awards from li items
    def parse_venice_li(li, results, forced_category=None):
        nested_ul = li.find('ul')
        text = li.get_text(" ", strip=True)
        # Remove nested UL text if present to process the main line
        if nested_ul:
            ul_text = nested_ul.get_text(" ", strip=True)
            if text.endswith(ul_text):
                text = text[:-len(ul_text)].strip()
        
        text_lower = text.lower()
        
        # --- PATTERN MATCHING ---
        
        # 1. Best Film (Leone d'oro)
        # User format: "Leone d'oro al miglior film: Faust di Aleksandr Sokurov"
        # Check explicit phrase OR if we are already in best-film context
        # EXCLUDE "alla carriera" (Lifetime Achievement) and "Leone d'oro speciale" (Special Golden Lion)
        if "carriera" in text_lower:
            return
        if "leone d'oro speciale" in text_lower or "leone speciale" in text_lower:
            return
        # EXCLUDE "Cinema del presente" section awards (non-main competition)
        if "cinema del presente" in text_lower or "presente" in text_lower:
            return

        is_best_film = ("leone d'oro" in text_lower and "miglior film" in text_lower)
        if not is_best_film and forced_category == 'best-film':
            is_best_film = "miglior film" in text_lower or (":" in text and "leone" not in text_lower) # Simple line in nested category
            
        if is_best_film:
            # Try regex: "Leone d'oro...: [Film] di [Director]"
            # Or just ": [Film] di [Director]" if context is known
            match = re.search(r":\s*(.+?)\s+di\s+", text, re.IGNORECASE)
            if match:
                film = match.group(1).strip()
                # Clean up ", regia" suffix if present (e.g. "The Room Next Door, regia")
                film = re.sub(r',?\s*regia$', '', film, flags=re.IGNORECASE).strip()
                
                # Remove italics or quotes if present (simple cleanup)
                results['best-film'].append({
                    'name': film,
                    'awards': {'venice': 'Y'}
                })
                # If we found it, return to avoid double adding
                return

        # 2. Coppa Volpi (Actor/Actress)
        # Formats: "Coppa Volpi per la miglior interpretazione maschile/femminile: [Name] per [Film]"
        #          "Coppa Volpi al miglior attore/attrice: [Name] per [Film]"
        key = None
        if "coppa volpi" in text_lower:
            if "maschile" in text_lower or "attore" in text_lower: key = 'best-actor'
            elif "femminile" in text_lower or "attrice" in text_lower: key = 'best-actress'
        elif forced_category in ['best-actor', 'best-actress']:
            key = forced_category
            
        if key:
            # Regex: "...: [Name] per [Film]"
            match = re.search(r":\s*(.+?)\s+per\s+(.+)", text, re.IGNORECASE)
            if match:
                person = match.group(1).strip()
                film = match.group(2).strip()
                # Clean up film (remove parentheses like "(Tao Jie)")
                film = re.sub(r'\s*\(.*?\)$', '', film)
                
                results[key].append({
                    'name': person,
                    'film': film,
                    'awards': {'venice': 'Y'}
                })
                return

        # 3. Best Director (Leone d'argento)
        # Formats: "Leone d'argento...regia...: [Film] di [Director]"
        #          "Premio speciale per la regia: [Film] di [Director]"
        #          "Premio per la migliore regia: [Film] di [Director]"
        is_director = False
        if ("leone d'argento" in text_lower and "regia" in text_lower): 
            # Exclude Grand Jury Prize (Leone d'argento - Gran premio della giuria)
            # which might contain "regia di" in the description but is NOT the Director award.
            if "gran premio" not in text_lower:
                is_director = True
        elif "premio speciale per la regia" in text_lower: is_director = True
        elif "premio per la migliore regia" in text_lower: is_director = True
        elif forced_category == 'best-director': is_director = True
        
        if is_director:
             # Pattern A: "...: [Director] per [Film]" (e.g. Leone d'Argento a X per Y)
            match = re.search(r":\s*(.+?)\s+per\s+(.+)", text, re.IGNORECASE)
            if match:
                person = match.group(1).strip()
                film = match.group(2).strip()
                results['best-director'].append({
                    'name': person,
                    'film': film,
                    'awards': {'venice': 'Y'}
                })
                return
            
            # Pattern B: "...: [Film] di [Director]" (e.g. Premio speciale: Film di Director)
            match_di = re.search(r":\s*(.+?)\s+di\s+(.+)", text, re.IGNORECASE)
            if match_di:
                film = match_di.group(1).strip()
                # Clean up ", regia" suffix if present
                film = re.sub(r',?\s*regia$', '', film, flags=re.IGNORECASE).strip()
                
                person = match_di.group(2).strip()
                results['best-director'].append({
                    'name': person,
                    'film': film,
                    'awards': {'venice': 'Y'}
                })
                return

        # --- FALLBACK / ORIGINAL LOGIC (for other years/formats) ---
        
        # Determine if parent defines a category
        category = forced_category
        
        if not category:
            if "leone d'oro" in text_lower: category = 'best-film'
            elif "leone d'argento" in text_lower and 'regia' in text_lower and "gran premio" not in text_lower: category = 'best-director'
            elif 'coppa volpi' in text_lower and 'maschile' in text_lower: category = 'best-actor'
            elif 'coppa volpi' in text_lower and 'femminile' in text_lower: category = 'best-actress'
            elif 'miglior attore' in text_lower: category = 'best-actor'
            elif 'miglior attrice' in text_lower: category = 'best-actress'
            elif 'miglior film' in text_lower: category = 'best-film'
            elif 'miglior regia' in text_lower: category = 'best-director'

        # If li has nested ul, process children with found category
        if nested_ul:
            nested_lis = nested_ul.find_all('li', recursive=False)
            for nested_li in nested_lis:
                parse_venice_li(nested_li, results, forced_category=category)
            return
        
        if not category:
            return

        # Extract winners
        # Cases:
        # A. <b>Winner Name</b> ... <i>Film</i>
        # B. <b>Winner Name</b> (Film)
        # C. <i>Film</i> di <b>Director</b> (Best Film case)
        # D. Leone d'oro al miglior film: <i>Film</i> di <b>Director</b> (Flat list)
        
        b_tags = li.find_all('b')
        i_tags = li.find_all('i')
        a_tags = li.find_all('a')
        
        if category == 'best-film':
            # Priority: <i> tag often holds film title
            film_name = None
            if i_tags:
                film_name = i_tags[0].get_text().strip()
            elif b_tags: 
                # Sometimes film is bold if no director mentioned or different style
                # But check if bold is "Leone d'oro" (the category)
                possible_film = b_tags[0].get_text().strip()
                if "leone" not in possible_film.lower() and "miglior" not in possible_film.lower():
                     film_name = possible_film
            elif a_tags:
                 # Check links, excluding category links
                 for a in a_tags:
                     txt = a.get_text().strip()
                     if "leone" not in txt.lower():
                         film_name = txt
                         break
            
            if film_name and len(film_name) >= 2:
                # Dedupe
                if not any(e['name'] == film_name for e in results['best-film']):
                    results['best-film'].append({
                        'name': film_name,
                        'awards': {'venice': 'Y'}
                    })
                
        elif category in ['best-director', 'best-actor', 'best-actress']:
            # Person Categories
            accepted_entries = []
            
            if b_tags:
                for b in b_tags:
                    name = b.get_text().strip()
                    # Filter out category names in bold (e.g. <b>Coppa Volpi:</b> Name)
                    if "coppa" in name.lower() or "miglior" in name.lower():
                        continue
                    accepted_entries.append({'name': name})
            elif a_tags:
                # If no bold, try links (common in old wikis)
                # But careful not to pick film link
                # Structure: Name (Film) or Name - Film
                # Heuristic: Person often first link, or link before italic film
                pass # Relying on bold for now is safer, most wikis use bold for winners.
                     # If needed, can expand.
            
            # Associate films
            if accepted_entries:
                film_title = None
                if i_tags:
                    film_title = i_tags[0].get_text().strip()
                
                for entry in accepted_entries:
                    entry['awards'] = {'venice': 'Y'}
                    if film_title:
                        entry['film'] = film_title
                    results[category].append(entry)

    # Navigation Logic
    container = premi_section.parent
    
    # If we started from a div wrapper (mw-heading)
    if container.name == 'div' and 'mw-heading' in container.get('class', []):
        current = container.next_sibling
    else:
        current = premi_section.next_sibling
        
    found_awards = False
    
    while current:
        if not current.name:
            current = current.next_sibling
            continue
        
        # Stop conditions
        if start_from_h2:
             # Stop at next H2
             if current.name == 'h2': break
             if current.name == 'div' and 'mw-heading' in str(current.get('class', [])):
                 h2_next = current.find('h2')
                 if h2_next: break
        else:
             # Started from H3
             if current.name in ['h2', 'h3']: break
             if current.name == 'div' and 'mw-heading' in str(current.get('class', [])):
                 break

        # Process Content
        if current.name == 'ul':
            print(f"    Found UL, parsing items...")
            for li in current.find_all('li', recursive=False):
                parse_venice_li(li, results)
            found_awards = True
            
        # NEW FORMAT: Look for section containing 'Concorso'
        if current.name == 'section':
            section_text = current.get_text().lower()
            if 'concorso' in section_text or 'ufficiali' in section_text:
                 # Parse ULs inside this section
                 for ul in current.find_all('ul'):
                     for li in ul.find_all('li', recursive=False):
                         parse_venice_li(li, results)
                 found_awards = True
            else:
                 pass # Not a relevant section, maybe collision or other awards
        # In some years (2011), H3 "Premi principali" is nested under H2 "Premi"
        # If we started from H2, we might encounter H3s.
        if start_from_h2 and current.name == 'h3':
             text = current.get_text().lower()
             if 'principali' in text or 'ufficiali' in text or 'concorso' in text:
                 # This is a good section, continue processing its siblings?
                 # Actually, usually the UL is immediately after this H3.
                 # Let the loop continue, next iteration will find UL.
                 pass
             else:
                 # Collateral awards or others -> maybe skip ULs?
                 # But sticking to "parse everything under H2" usually works because
                 # parse_venice_li filters by keyword (Leone d'oro etc).
                 pass

        current = current.next_sibling
    
    total = sum(len(v) for v in results.values())
    print(f"    Venice {ceremony_num}: Found {total} entries (Films: {len(results['best-film'])}, Dir: {len(results['best-director'])}, Actor: {len(results['best-actor'])}, Actress: {len(results['best-actress'])})")
    return results


