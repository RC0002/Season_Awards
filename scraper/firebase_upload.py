# -*- coding: utf-8 -*-
"""
Firebase Data Uploader
======================
Uploads scraped award data to Firebase Realtime Database.
No server needed - data loads directly from Firebase.
"""

import requests
import json
import os
import sys
import glob

sys.stdout.reconfigure(encoding='utf-8')

# Firebase Realtime Database URL (from app.js)
FIREBASE_DB_URL = "https://seasonawards-8deae-default-rtdb.europe-west1.firebasedatabase.app"


def upload_year_data(year, data):
    """Upload data to Firebase for a specific year"""
    url = f"{FIREBASE_DB_URL}/awards/{year}.json"
    
    try:
        response = requests.put(url, json=data)
        if response.status_code == 200:
            print(f"  ✓ Uploaded {year}")
            return True
        else:
            print(f"  ✗ Failed {year}: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"  ✗ Error {year}: {e}")
        return False


def load_json_file(filepath):
    """Load JSON file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def upload_all_years():
    """Upload all year data files to Firebase"""
    print("="*60)
    print("   FIREBASE DATA UPLOADER")
    print("="*60)
    print(f"\n  Database: {FIREBASE_DB_URL}")
    
    # Find all data files with pattern data_YYYY_YYYY.json
    data_files = glob.glob('data/data_*_*.json')
    
    if not data_files:
        print("\n  No data files found!")
        return
    
    print(f"\n  Found {len(data_files)} data files\n")
    
    success = 0
    for filepath in sorted(data_files):
        # Extract years from filename (e.g., data_2024_2025.json -> "2024_2025")
        filename = os.path.basename(filepath)
        parts = filename.replace('.json', '').replace('data_', '')
        year_key = parts  # Use full format like "2024_2025"
        
        data = load_json_file(filepath)
        
        # Count entries
        total = sum(len(entries) for entries in data.values())
        print(f"  {filename} ({total} entries) -> /awards/{year_key}")
        
        if upload_year_data(year_key, data):
            success += 1
    
    print(f"\n{'='*60}")
    print(f"  Uploaded {success}/{len(data_files)} years successfully")
    print("="*60)


def upload_single_year(year):
    """Upload a single year's data using YYYY_YYYY format"""
    year_key = f"{year-1}_{year}"
    filepath = f'data/data_{year_key}.json'
    
    if not os.path.exists(filepath):
        print(f"  File not found: {filepath}")
        return False
    
    print(f"\n  Uploading {filepath} to Firebase /awards/{year_key}...")
    data = load_json_file(filepath)
    
    if upload_year_data(year_key, data):
        print("  Done!")
        return True
    return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Upload scraped data to Firebase')
    parser.add_argument('year', type=int, nargs='?', 
                        help='Specific year to upload (e.g., 2025 for 2024/25)')
    parser.add_argument('--all', action='store_true',
                        help='Upload all available years')
    args = parser.parse_args()
    
    if args.all or args.year is None:
        upload_all_years()
    else:
        upload_single_year(args.year)
