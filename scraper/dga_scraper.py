# -*- coding: utf-8 -*-
"""
DGA Awards Scraper
==================
Scrapes Directors Guild of America Feature Film awards.
Uses Selenium with JavaScript execution for all interactions.
"""

import json
import os
import time
import argparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

try:
    from webdriver_manager.chrome import ChromeDriverManager
    USE_WEBDRIVER_MANAGER = True
except ImportError:
    USE_WEBDRIVER_MANAGER = False
    print("Note: webdriver-manager not installed. Using system ChromeDriver.")

DGA_URL = "https://www.dga.org/awards/explore"

# Checkbox IDs
FEATURE_FILM_CHECKBOX_ID = "facet-awards_explore_category-facetid_eyJ0eXBlIjoiZXEiLCJuYW1lIjoiYXdhcmRzX2V4cGxvcmVfY2F0ZWdvcnkiLCJ2YWx1ZSI6IkZpbG06RmVhdHVyZSBGaWxtIn0="
WINNERS_ONLY_CHECKBOX_ID = "SingleCheckBoxWinnersOnly"


def create_driver():
    """Create a headless Chrome driver."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    if USE_WEBDRIVER_MANAGER:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    else:
        driver = webdriver.Chrome(options=options)
    
    return driver


def scrape_single_year(driver, year):
    """
    Scrape DGA Feature Film awards for a SINGLE year using JavaScript clicks.
    """
    print(f"\n  Scraping year {year}...")
    
    try:
        # Navigate to page fresh for each year
        driver.get(DGA_URL)
        time.sleep(4)  # Wait for JS to fully load
        
        # Use JavaScript to set up filters and extract data
        result = driver.execute_script(f"""
            return new Promise((resolve) => {{
                // Helper to wait
                const wait = (ms) => new Promise(r => setTimeout(r, ms));
                
                async function scrapeYear() {{
                    try {{
                        // Uncheck "Winners Only" if checked
                        const winnersOnly = document.getElementById('{WINNERS_ONLY_CHECKBOX_ID}');
                        if (winnersOnly && winnersOnly.checked) {{
                            winnersOnly.click();
                            await wait(500);
                        }}
                        
                        // Check Feature Film if not checked
                        const featureFilm = document.getElementById('{FEATURE_FILM_CHECKBOX_ID}');
                        if (featureFilm && !featureFilm.checked) {{
                            featureFilm.click();
                            await wait(500);
                        }}
                        
                        // Find and click start year dropdown
                        // Updated selector based on debug output (cursor-pointer might be missing)
                        const yearDropdowns = document.querySelectorAll('div.relative.border.border-gray-400');
                        if (yearDropdowns.length >= 2) {{
                            // Click start year dropdown
                            yearDropdowns[0].click();
                            await wait(500);
                            
                            // Find and click the year
                            const startItems = Array.from(document.querySelectorAll('li'));
                            const startItem = startItems.find(li => li.innerText.trim().startsWith('{year}'));
                            if (startItem) {{
                                startItem.click();
                                await wait(500);
                            }}
                            
                            // Click end year dropdown (set to same year)
                            yearDropdowns[1].click();
                            await wait(500);
                            
                            const endItems = Array.from(document.querySelectorAll('li'));
                            const endItem = endItems.find(li => li.innerText.trim().startsWith('{year}'));
                            if (endItem) {{
                                endItem.click();
                                await wait(500);
                            }}
                        }}
                        
                        // Click search button
                        const searchBtn = document.querySelector('button.bg-purple-darker');
                        if (searchBtn) {{
                            searchBtn.click();
                            await wait(3000);
                        }}
                        
                        // Extract results
                        const results = [];
                        const allDivs = document.querySelectorAll('div');
                        
                        allDivs.forEach(div => {{
                            const text = div.innerText;
                            if (text && (text.includes('WINNER') || text.includes('NOMINEE')) 
                                && /^[12][0-9]{{3}}/.test(text.trim().substring(0,4))) {{
                                
                                const lines = text.split('\\n').map(l => l.trim()).filter(l => l);
                                
                                // Only regular FEATURE FILM (exclude First Time)
                                if (lines.length >= 4 && lines[1].includes('FEATURE FILM') 
                                    && !lines[1].includes('FIRST TIME') && !lines[1].includes('FIRST-TIME')) {{
                                    results.push({{
                                        year: parseInt(lines[0]),
                                        status: lines[1],
                                        director: lines[2],
                                        film: lines[3]
                                    }});
                                }}
                            }}
                        }});
                        
                        // Remove duplicates
                        const uniqueResults = [];
                        const seen = new Set();
                        results.forEach(res => {{
                            const key = `${{res.year}}|${{res.director}}|${{res.film}}`;
                            if (!seen.has(key)) {{
                                uniqueResults.push(res);
                                seen.add(key);
                            }}
                        }});
                        
                        resolve(uniqueResults);
                        
                    }} catch (e) {{
                        resolve({{ error: e.toString() }});
                    }}
                }}
                
                scrapeYear();
            }});
        """)
        
        # Check for errors
        if isinstance(result, dict) and 'error' in result:
            print(f"    JS Error: {result['error']}")
            return []
        
        # Process results
        year_results = []
        for entry in result:
            if entry['year'] == year:
                is_winner = 'WINNER' in entry['status']
                year_results.append({
                    "name": entry['director'],
                    "film": entry['film'],
                    "isWinner": is_winner
                })
                status = "WINNER" if is_winner else "Nominee"
                print(f"    {entry['director']} - {entry['film']} [{status}]")
        
        print(f"  Found {len(year_results)} entries for {year}")
        return year_results
        
    except Exception as e:
        print(f"  ERROR scraping {year}: {e}")
        return []


def scrape_dga_all_years(start_year=2012, end_year=2024):
    """
    Scrape DGA for all years, one year at a time.
    """
    print(f"\n{'='*60}")
    print(f"  DGA Awards Scraper (Year by Year)")
    print(f"  Years: {start_year} - {end_year}")
    print(f"{'='*60}")
    
    all_results = {}
    driver = create_driver()
    
    try:
        for year in range(start_year, end_year + 1):
            year_data = scrape_single_year(driver, year)
            if year_data:
                all_results[year] = year_data
            
            # Delay between years
            time.sleep(2)
    
    finally:
        driver.quit()
    
    return all_results


def format_for_master_scraper(dga_data):
    """Convert DGA data to master_scraper format."""
    formatted = {}
    
    for year, entries in dga_data.items():
        formatted[year] = {
            "best-director": []
        }
        for entry in entries:
            formatted[year]["best-director"].append({
                "name": entry["name"],
                "film": entry["film"],
                "awards": {
                    "dga": "Y" if entry["isWinner"] else "X"
                }
            })
    
    return formatted


def save_dga_data(data, filename="scraper/dga_awards.json"):
    """Save scraped data to JSON file."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to: {filename}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Scrape DGA Feature Film Awards')
    parser.add_argument('--start', type=int, default=2012, help='Start year (default: 2012)')
    parser.add_argument('--end', type=int, default=2025, help='End year (default: 2025)')
    parser.add_argument('--output', type=str, default='scraper/dga_awards.json', help='Output file')
    
    args = parser.parse_args()
    
    # Scrape all years one by one
    raw_data = scrape_dga_all_years(args.start, args.end)
    
    # Format for integration
    formatted_data = format_for_master_scraper(raw_data)
    
    # Load existing data if exists
    existing_data = {}
    if os.path.exists(args.output):
        try:
            with open(args.output, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load existing data: {e}")
            
    # Merge existing with new (new overrides old)
    existing_data.update(formatted_data)
    
    # Save
    save_dga_data(existing_data, args.output)
    
    print("\n" + "="*60)
    print(f"  DONE! Updated {len(formatted_data)} years. Total years in file: {len(existing_data)}")
    print("="*60)
