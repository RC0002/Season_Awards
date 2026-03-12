# -*- coding: utf-8 -*-
"""
Firebase Data Uploader
======================
Uploads scraped award data to Firebase Realtime Database.
Uses Firebase Admin SDK with service account authentication.
"""

import json
import os
import sys
import glob

import firebase_admin
from firebase_admin import credentials, db

sys.stdout.reconfigure(encoding='utf-8')

# Firebase Realtime Database URL
FIREBASE_DB_URL = "https://seasonawards-8deae-default-rtdb.europe-west1.firebasedatabase.app"

# Locate service account key (supports running from project root or scraper/ dir)
_SA_CANDIDATES = [
    os.path.join(os.path.dirname(__file__), 'firebase-service-account.json'),
    os.path.join(os.path.dirname(__file__), '..', 'firebase-service-account.json'),
    'scraper/firebase-service-account.json',
    'firebase-service-account.json',
]

def _find_service_account():
    for path in _SA_CANDIDATES:
        if os.path.exists(path):
            return os.path.abspath(path)
    return None

def _init_firebase():
    """Initialize Firebase Admin SDK (only once)."""
    if not firebase_admin._apps:
        sa_path = _find_service_account()
        if not sa_path:
            print("  ❌ firebase-service-account.json not found!")
            print("     Download it from Firebase Console → Project Settings → Service accounts → Generate new private key")
            print(f"     Save it to: scraper/firebase-service-account.json")
            sys.exit(1)
        cred = credentials.Certificate(sa_path)
        firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_DB_URL})

# Initialize on import
_init_firebase()


def upload_year_data(year, data):
    """Upload data to Firebase for a specific year"""
    try:
        ref = db.reference(f'/awards/{year}')
        ref.set(data)
        print(f"  ✓ Uploaded {year}")
        return True
    except Exception as e:
        print(f"  ✗ Failed {year}: {e}")
        return False


def upload_analysis(analysis_data):
    """Upload analysis.json data to Firebase"""
    try:
        ref = db.reference('/analysis')
        ref.set(analysis_data)
        return True
    except Exception as e:
        print(f"  ✗ Analysis upload error: {e}")
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
