# -*- coding: utf-8 -*-
"""
Scrape and Upload Script
========================
Combined script for scraping all awards and uploading to Firebase.
Features:
- Parallel scraping for improved performance
- Change detection to skip unchanged data
- Extended years from 2012/13 onwards
"""

import requests
import json
import os
import sys
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding='utf-8')

# Import functions from existing modules
from master_scraper import scrape_year, save_year_data, CEREMONY_MAP
from firebase_upload import upload_year_data, load_json_file, FIREBASE_DB_URL


def get_file_hash(filepath):
    """Get MD5 hash of a JSON file for change detection"""
    if not os.path.exists(filepath):
        return None
    with open(filepath, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def get_firebase_hash(year_key):
    """Get hash of data currently in Firebase for comparison"""
    url = f"{FIREBASE_DB_URL}/awards/{year_key}.json"
    try:
        response = requests.get(url)
        if response.status_code == 200 and response.text != 'null':
            return hashlib.md5(response.content).hexdigest()
    except:
        pass
    return None


def scrape_single_year(year):
    """Scrape a single year and save to file"""
    try:
        data = scrape_year(year)
        save_year_data(year, data)
        return year, True
    except Exception as e:
        print(f"  Error scraping {year}: {e}")
        return year, False


def scrape_all_parallel(years, max_workers=3):
    """Scrape multiple years in parallel"""
    print(f"\n{'='*60}")
    print(f"  PARALLEL SCRAPING ({len(years)} years, {max_workers} workers)")
    print(f"{'='*60}")
    
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(scrape_single_year, year): year for year in years}
        for future in as_completed(futures):
            year, success = future.result()
            results[year] = success
    
    return results


def upload_with_change_detection(years):
    """Upload only years that have changed"""
    print(f"\n{'='*60}")
    print(f"  UPLOADING WITH CHANGE DETECTION")
    print(f"{'='*60}")
    
    uploaded = 0
    skipped = 0
    
    for year in sorted(years):
        year_key = f"{year-1}_{year}"
        filepath = f'data/data_{year_key}.json'
        
        if not os.path.exists(filepath):
            print(f"  {year_key}: File not found, skipping")
            continue
        
        # Get hashes
        local_hash = get_file_hash(filepath)
        firebase_hash = get_firebase_hash(year_key)
        
        if local_hash == firebase_hash and firebase_hash is not None:
            print(f"  {year_key}: No changes, skipping")
            skipped += 1
        else:
            data = load_json_file(filepath)
            total = sum(len(entries) for entries in data.values())
            
            if upload_year_data(year_key, data):
                print(f"  {year_key}: Uploaded ({total} entries)")
                uploaded += 1
            else:
                print(f"  {year_key}: Upload failed")
    
    return uploaded, skipped


def run_full_pipeline(years=None, parallel=True, force_upload=False):
    """
    Run the full scrape and upload pipeline.
    
    Args:
        years: List of years to process (default: 2013-2025)
        parallel: Use parallel scraping
        force_upload: Skip change detection and upload all
    """
    if years is None:
        years = list(range(2025, 2012, -1))  # 2025 down to 2013
    
    print("\n" + "="*60)
    print("   SCRAPE AND UPLOAD PIPELINE")
    print("="*60)
    print(f"  Years: {min(years)}-{max(years)} ({len(years)} total)")
    print(f"  Parallel: {parallel}")
    print(f"  Force upload: {force_upload}")
    
    # Step 1: Scrape
    if parallel:
        results = scrape_all_parallel(years)
    else:
        results = {}
        for year in years:
            year, success = scrape_single_year(year)
            results[year] = success
    
    # Count successes
    success_count = sum(1 for s in results.values() if s)
    print(f"\n  Scraped: {success_count}/{len(years)} years")
    
    # Step 2: Upload
    if force_upload:
        # Upload all without checking
        from firebase_upload import upload_all_years
        upload_all_years()
    else:
        uploaded, skipped = upload_with_change_detection(years)
        print(f"\n  Uploaded: {uploaded}, Skipped (unchanged): {skipped}")
    
    print("\n" + "="*60)
    print("   PIPELINE COMPLETE")
    print("="*60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Scrape and upload awards data')
    parser.add_argument('--years', type=str, default='2013-2025',
                        help='Year range (e.g., 2013-2025 or 2020,2021,2022)')
    parser.add_argument('--no-parallel', action='store_true',
                        help='Disable parallel scraping')
    parser.add_argument('--force', action='store_true',
                        help='Force upload even if unchanged')
    parser.add_argument('--upload-only', action='store_true',
                        help='Skip scraping, only upload existing files')
    args = parser.parse_args()
    
    # Parse years
    if '-' in args.years:
        start, end = map(int, args.years.split('-'))
        years = list(range(end, start-1, -1))
    else:
        years = [int(y) for y in args.years.split(',')]
    
    if args.upload_only:
        upload_with_change_detection(years)
    else:
        run_full_pipeline(
            years=years,
            parallel=not args.no_parallel,
            force_upload=args.force
        )
