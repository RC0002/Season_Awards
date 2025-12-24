# -*- coding: utf-8 -*-
"""
Scrape and Upload Script - Enhanced Version
============================================
Combined script for scraping all awards and uploading to Firebase.

Features:
- Detailed logging per award with clear separation
- Parallel scraping with buffered output (no mixed logs)
- Historical comparison to detect anomalies
- End-of-run recap showing issues and warnings
- Designed for monitoring new season (2025/26)

Usage:
  py scraper/scrape_and_upload.py --years 2026        # Scrape and upload 2025/26 season
  py scraper/scrape_and_upload.py --years 2026 --no-parallel  # Sequential for debugging
  py scraper/scrape_and_upload.py --upload-only --years 2026  # Just upload existing files
"""

import requests
import json
import os
import sys
import hashlib
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

sys.stdout.reconfigure(encoding='utf-8')

# Import functions from existing modules
from master_scraper import scrape_year, save_year_data, CEREMONY_MAP
from firebase_upload import upload_year_data, load_json_file, FIREBASE_DB_URL


# =============================================================================
# HISTORICAL AVERAGES (expected nomination counts per category per award)
# Used to detect if scraping is working correctly
# =============================================================================
HISTORICAL_AVERAGES = {
    # Oscar: 10 films, 5 directors, 5 leading + 5 supporting actors/actresses
    'oscar': {'best-film': 10, 'best-director': 5, 'best-actor': 10, 'best-actress': 10},
    # GG: Drama + Comedy films, Drama + Comedy + Supporting actors = ~18 each
    'gg': {'best-film': 12, 'best-director': 6, 'best-actor': 18, 'best-actress': 18},
    # BAFTA: 6 films, 6 directors, 6 leading + 6 supporting = 12 actors
    'bafta': {'best-film': 6, 'best-director': 6, 'best-actor': 12, 'best-actress': 12},
    # SAG: 5 films (cast), no directors, 5 leading + 5 supporting = 10
    'sag': {'best-film': 5, 'best-director': 0, 'best-actor': 10, 'best-actress': 10},
    # Critics: 10 films, 8 directors, 6 leading + 6 supporting = 12
    'critics': {'best-film': 10, 'best-director': 8, 'best-actor': 12, 'best-actress': 12},
    # AFI: 10 (or 11) films only
    'afi': {'best-film': 11, 'best-director': 0, 'best-actor': 0, 'best-actress': 0},
    # NBR: 10 films, 1 winner each for director/actor/actress
    'nbr': {'best-film': 11, 'best-director': 1, 'best-actor': 1, 'best-actress': 1},
    # Venice: 1 winner each
    'venice': {'best-film': 1, 'best-director': 1, 'best-actor': 1, 'best-actress': 1},
    # DGA: 5 director nominees
    'dga': {'best-film': 0, 'best-director': 5, 'best-actor': 0, 'best-actress': 0},
}

# Tolerance for comparison (e.g., 0.5 means ±50% of expected)
TOLERANCE = 0.5

# Lock for thread-safe printing
print_lock = Lock()


# =============================================================================
# LOGGING AND REPORT CLASSES
# =============================================================================

class AwardLog:
    """Collects log messages for a single award scrape."""
    
    def __init__(self, award_key, year):
        self.award_key = award_key.upper()
        self.year = year
        self.messages = []
        self.start_time = time.time()
        self.end_time = None
        self.success = False
        self.counts = {}  # {category: count}
        self.warnings = []
        self.errors = []
    
    def log(self, msg):
        """Add a log message"""
        self.messages.append(f"  {msg}")
    
    def warn(self, msg):
        """Add a warning"""
        self.warnings.append(msg)
        self.messages.append(f"  ⚠️ {msg}")
    
    def error(self, msg):
        """Add an error"""
        self.errors.append(msg)
        self.messages.append(f"  ❌ {msg}")
    
    def set_counts(self, counts):
        """Set the scraped counts per category"""
        self.counts = counts
    
    def finish(self, success=True):
        """Mark as finished"""
        self.end_time = time.time()
        self.success = success
    
    def duration(self):
        """Get duration in seconds"""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
    
    def print_report(self):
        """Print formatted report for this award"""
        with print_lock:
            # Header
            status = "✓" if self.success else "✗"
            print(f"\n{'─'*60}")
            print(f"  {status} {self.award_key} ({self.year-1}/{self.year}) - {self.duration():.1f}s")
            print(f"{'─'*60}")
            
            # Log messages
            for msg in self.messages:
                print(msg)
            
            # Summary counts
            if self.counts:
                print(f"\n  📊 Results:")
                for cat, count in self.counts.items():
                    expected = HISTORICAL_AVERAGES.get(self.award_key.lower(), {}).get(cat, 0)
                    if expected > 0:
                        diff = count - expected
                        diff_str = f" ({'+' if diff >= 0 else ''}{diff})" if diff != 0 else ""
                        indicator = "✓" if abs(diff) <= expected * TOLERANCE else "⚠️"
                        print(f"     {indicator} {cat}: {count} entries{diff_str}")
                    elif count > 0:
                        print(f"     • {cat}: {count} entries")
            
            # Warnings summary
            if self.warnings:
                print(f"\n  ⚠️ Warnings: {len(self.warnings)}")
            if self.errors:
                print(f"  ❌ Errors: {len(self.errors)}")


class ScrapeReport:
    """Collects all award logs and generates final report."""
    
    def __init__(self, year):
        self.year = year
        self.logs = {}  # award_key -> AwardLog
        self.start_time = datetime.now()
    
    def add_log(self, award_key, log):
        """Add an award log"""
        self.logs[award_key] = log
    
    def print_final_report(self):
        """Print the final summary report"""
        print(f"\n{'='*60}")
        print(f"  📋 FINAL REPORT - Season {self.year-1}/{self.year}")
        print(f"{'='*60}")
        
        # Overall stats
        total = len(self.logs)
        success = sum(1 for log in self.logs.values() if log.success)
        failed = total - success
        
        print(f"\n  ⏱️  Total time: {(datetime.now() - self.start_time).seconds}s")
        print(f"  ✓  Successful: {success}/{total}")
        if failed > 0:
            print(f"  ✗  Failed: {failed}/{total}")
        
        # Category totals
        print(f"\n  📊 TOTALS PER CATEGORY:")
        category_totals = {'best-film': 0, 'best-director': 0, 'best-actor': 0, 'best-actress': 0}
        
        for log in self.logs.values():
            for cat, count in log.counts.items():
                if cat in category_totals:
                    category_totals[cat] += count
        
        for cat, total in category_totals.items():
            print(f"     • {cat}: {total} entries")
        
        # Issues and warnings
        all_warnings = []
        all_errors = []
        missing_data = []
        
        for award_key, log in self.logs.items():
            all_warnings.extend([(award_key, w) for w in log.warnings])
            all_errors.extend([(award_key, e) for e in log.errors])
            
            # Check for missing expected data
            expected = HISTORICAL_AVERAGES.get(award_key.lower(), {})
            for cat, expected_count in expected.items():
                actual = log.counts.get(cat, 0)
                if expected_count > 0 and actual == 0:
                    missing_data.append((award_key, cat, expected_count))
        
        # Print issues
        if missing_data:
            print(f"\n  🔴 MISSING DATA (expected but not found):")
            for award, cat, expected in missing_data:
                print(f"     • {award.upper()}: {cat} (expected ~{expected})")
        
        if all_warnings:
            print(f"\n  ⚠️  WARNINGS ({len(all_warnings)}):")
            for award, warning in all_warnings[:10]:  # Show first 10
                print(f"     • [{award.upper()}] {warning}")
            if len(all_warnings) > 10:
                print(f"     ... and {len(all_warnings) - 10} more")
        
        if all_errors:
            print(f"\n  ❌ ERRORS ({len(all_errors)}):")
            for award, error in all_errors:
                print(f"     • [{award.upper()}] {error}")
        
        # Status per award
        print(f"\n  📡 AWARD STATUS:")
        for award_key in ['oscar', 'gg', 'bafta', 'sag', 'critics', 'afi', 'nbr', 'venice', 'dga']:
            log = self.logs.get(award_key)
            if log:
                total_entries = sum(log.counts.values())
                if total_entries == 0:
                    status = "❌ No data (page not updated?)"
                elif log.errors:
                    status = f"⚠️ {total_entries} entries (with errors)"
                elif log.warnings:
                    status = f"✓ {total_entries} entries (with warnings)"
                else:
                    status = f"✓ {total_entries} entries"
                print(f"     {award_key.upper():8} {status}")
            else:
                print(f"     {award_key.upper():8} ⏭️ Not scraped")
        
        print(f"\n{'='*60}")


# =============================================================================
# ENHANCED SCRAPING FUNCTIONS
# =============================================================================

def scrape_award_with_logging(award_key, year, report):
    """
    Scrape a single award with detailed logging.
    Returns the award data and adds log to report.
    """
    log = AwardLog(award_key, year)
    
    try:
        # ==== START SCRAPING ====
        log.log(f"Starting scrape...")
        
        # Check if year is in ceremony map
        if award_key not in CEREMONY_MAP:
            log.error(f"Award '{award_key}' not in CEREMONY_MAP")
            log.finish(False)
            report.add_log(award_key, log)
            return None
        
        if year not in CEREMONY_MAP[award_key]:
            log.warn(f"Year {year} not in mapping (max: {max(CEREMONY_MAP[award_key].keys())})")
            log.finish(False)
            report.add_log(award_key, log)
            return None
        
        ceremony = CEREMONY_MAP[award_key][year]
        log.log(f"Ceremony/Year mapping: {year} → {ceremony}")
        
        # ==== FETCH PAGE ====
        from master_scraper import URL_TEMPLATES, ordinal, fetch_page
        
        if award_key in URL_TEMPLATES:
            if '{year}' in URL_TEMPLATES[award_key]:
                url = URL_TEMPLATES[award_key].format(year=ceremony)
            else:
                url = URL_TEMPLATES[award_key].format(ord=ordinal(ceremony))
            log.log(f"URL: {url}")
        else:
            log.log(f"Using special scraper function")
        
        # ==== CALL APPROPRIATE SCRAPER ====
        from master_scraper import (scrape_award, scrape_afi, scrape_nbr, 
                                    scrape_venice, scrape_dga)
        
        result = None
        
        if award_key == 'afi':
            result = scrape_afi(ceremony)
            log.log(f"Scraped AFI Top 10 Films list")
        elif award_key == 'nbr':
            result = scrape_nbr(ceremony)
            log.log(f"Scraped NBR Awards page")
        elif award_key == 'venice':
            result = scrape_venice(ceremony)
            log.log(f"Scraped Venice Film Festival page (Italian Wikipedia)")
        elif award_key == 'dga':
            result = scrape_dga(ceremony)
            log.log(f"Loaded DGA data from pre-scraped file")
        else:
            result = scrape_award(award_key, year)
            log.log(f"Scraped Wikipedia awards table")
        
        # ==== ANALYZE RESULTS ====
        if result:
            counts = {}
            for cat, entries in result.items():
                counts[cat] = len(entries)
                
                # Log details for each category
                if entries:
                    winner = next((e for e in entries if e.get('awards', {}).get(award_key) == 'Y'), None)
                    if winner:
                        log.log(f"  {cat}: {len(entries)} entries, Winner: {winner.get('name', 'N/A')}")
                    else:
                        log.log(f"  {cat}: {len(entries)} entries (no winner marked)")
                
                # Check against historical averages
                expected = HISTORICAL_AVERAGES.get(award_key, {}).get(cat, 0)
                if expected > 0 and len(entries) == 0:
                    log.warn(f"{cat}: Expected ~{expected} but found 0")
                elif expected > 0 and abs(len(entries) - expected) > expected * TOLERANCE:
                    log.warn(f"{cat}: Found {len(entries)}, expected ~{expected}")
            
            log.set_counts(counts)
            log.finish(True)
        else:
            log.error("Scraper returned empty result")
            log.finish(False)
        
        report.add_log(award_key, log)
        return result
        
    except Exception as e:
        log.error(f"Exception: {str(e)}")
        log.finish(False)
        report.add_log(award_key, log)
        return None


def scrape_year_enhanced(year, awards=None, parallel=True):
    """
    Enhanced scrape_year with detailed logging and report generation.
    """
    if awards is None:
        awards = ['oscar', 'gg', 'bafta', 'sag', 'critics', 'afi', 'nbr', 'venice', 'dga']
    
    report = ScrapeReport(year)
    all_results = {}
    
    print(f"\n{'='*60}")
    print(f"  🎬 SCRAPING SEASON {year-1}/{year}")
    print(f"{'='*60}")
    print(f"  Awards: {', '.join(a.upper() for a in awards)}")
    print(f"  Mode: {'Parallel' if parallel else 'Sequential'}")
    print(f"  Started: {datetime.now().strftime('%H:%M:%S')}")
    
    if parallel:
        # ==== PARALLEL SCRAPING ====
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(scrape_award_with_logging, award, year, report): award 
                for award in awards
            }
            
            for future in as_completed(futures):
                award_key = futures[future]
                result = future.result()
                if result:
                    all_results[award_key] = result
                
                # Print this award's log now that it's complete
                if award_key in report.logs:
                    report.logs[award_key].print_report()
    else:
        # ==== SEQUENTIAL SCRAPING ====
        for award_key in awards:
            result = scrape_award_with_logging(award_key, year, report)
            if result:
                all_results[award_key] = result
            
            # Print log immediately
            if award_key in report.logs:
                report.logs[award_key].print_report()
    
    # ==== MERGE RESULTS ====
    from master_scraper import merge_results, enrich_with_tmdb
    
    print(f"\n{'─'*60}")
    print(f"  🔄 Merging results from {len(all_results)} awards...")
    
    merged = merge_results(all_results)
    
    # Print merge summary
    for cat, entries in merged.items():
        print(f"     {cat}: {len(entries)} unique entries")
    
    # ==== ENRICH WITH TMDB ====
    print(f"\n  🎞️ Fetching TMDB images...")
    merged = enrich_with_tmdb(merged)
    
    # ==== PRINT FINAL REPORT ====
    report.print_final_report()
    
    return merged


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

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


def upload_with_change_detection(years):
    """Upload only years that have changed"""
    print(f"\n{'='*60}")
    print(f"  📤 UPLOADING WITH CHANGE DETECTION")
    print(f"{'='*60}")
    
    uploaded = 0
    skipped = 0
    
    for year in sorted(years):
        year_key = f"{year-1}_{year}"
        filepath = f'data/data_{year_key}.json'
        
        if not os.path.exists(filepath):
            print(f"  {year_key}: ❌ File not found, skipping")
            continue
        
        # Get hashes
        local_hash = get_file_hash(filepath)
        firebase_hash = get_firebase_hash(year_key)
        
        if local_hash == firebase_hash and firebase_hash is not None:
            print(f"  {year_key}: ⏭️ No changes, skipping")
            skipped += 1
        else:
            data = load_json_file(filepath)
            total = sum(len(entries) for entries in data.values())
            
            if upload_year_data(year_key, data):
                print(f"  {year_key}: ✓ Uploaded ({total} entries)")
                uploaded += 1
            else:
                print(f"  {year_key}: ❌ Upload failed")
    
    print(f"\n  Summary: Uploaded {uploaded}, Skipped {skipped}")
    return uploaded, skipped


def run_full_pipeline(years=None, parallel=True, force_upload=False):
    """
    Run the full scrape and upload pipeline.
    
    Args:
        years: List of years to process (default: just 2026 for current season)
        parallel: Use parallel scraping
        force_upload: Skip change detection and upload all
    """
    if years is None:
        years = [2026]  # Default to current season
    
    print("\n" + "="*60)
    print("   🎬 SCRAPE AND UPLOAD PIPELINE")
    print("="*60)
    print(f"  📅 Seasons: {', '.join(f'{y-1}/{y}' for y in years)}")
    print(f"  ⚡ Parallel: {parallel}")
    print(f"  📤 Force upload: {force_upload}")
    print(f"  🕐 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Step 1: Scrape each year
    for year in years:
        data = scrape_year_enhanced(year, parallel=parallel)
        save_year_data(year, data)
    
    # Step 2: Upload
    print(f"\n{'='*60}")
    print(f"  📤 UPLOAD PHASE")
    print(f"{'='*60}")
    
    if force_upload:
        from firebase_upload import upload_all_years
        upload_all_years()
    else:
        uploaded, skipped = upload_with_change_detection(years)
    
    print("\n" + "="*60)
    print("   ✅ PIPELINE COMPLETE")
    print("="*60)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Scrape and upload awards data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  py scraper/scrape_and_upload.py --years 2026           # Current season
  py scraper/scrape_and_upload.py --years 2026 --no-parallel  # Debug mode
  py scraper/scrape_and_upload.py --upload-only --years 2026  # Just upload
  py scraper/scrape_and_upload.py --years 2024,2025,2026      # Multiple years
        """
    )
    parser.add_argument('--years', type=str, default='2026',
                        help='Year(s) to process: "2026" or "2024-2026" or "2024,2025,2026"')
    parser.add_argument('--no-parallel', action='store_true',
                        help='Disable parallel scraping (useful for debugging)')
    parser.add_argument('--force', action='store_true',
                        help='Force upload even if unchanged')
    parser.add_argument('--upload-only', action='store_true',
                        help='Skip scraping, only upload existing files')
    args = parser.parse_args()
    
    # Parse years
    if '-' in args.years:
        start, end = map(int, args.years.split('-'))
        years = list(range(end, start-1, -1))
    elif ',' in args.years:
        years = [int(y) for y in args.years.split(',')]
    else:
        years = [int(args.years)]
    
    if args.upload_only:
        upload_with_change_detection(years)
    else:
        run_full_pipeline(
            years=years,
            parallel=not args.no_parallel,
            force_upload=args.force
        )
