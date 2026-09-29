# CLAUDE.md — Season Awards Nomination Tracker

## Project Overview
Web app that tracks, predicts, and analyzes major film awards candidates throughout the season.
- **Scrapes** data from Wikipedia for 20+ award ceremonies (Oscar, Golden Globe, BAFTA, SAG, etc.)
- **Enriches** with TMDB metadata (posters, genres)
- **Visualizes** in a premium dark/gold themed SPA
- **Uploads** to Firebase Realtime Database for live updates

## Tech Stack
- **Frontend:** Vanilla JS SPA (`app.js` ~2.8K lines / ~110 KB), HTML, CSS (dark/gold theme). No framework.
- **Scraper:** Python 3 (`scraper/`), uses `requests` + `beautifulsoup4` for Wikipedia parsing, `tmdbv3api` for enrichment.
- **Data:** JSON files in `data/` (one per season: `data_YYYY_YYYY.json`, plus `analysis.json`).
- **Backend:** Firebase Realtime Database (public read, anonymous writes denied). Web config in `firebase-config.js` (gitignored, generated from the `FIREBASE_CONFIG` secret on deploy).
- **Desktop Launcher:** C# WPF app (`ScraperWPF.cs`) that wraps the Python scraper with a GUI progress bar.

## Project Structure
```
├── index.html              # SPA entry point (home page)
├── control.html            # Control panel for data validation
├── app.js                  # CORE: routing, UI rendering, stats, predictions
├── home.js                 # Home page logic (marquees, trending, animations)
├── control.js              # Control panel logic (validates data integrity)
├── styles.css / mobile.css # Styling (dark/gold premium theme)
├── firebase-config.js      # Firebase web config (gitignored)
├── modules/                # UNUSED legacy category modules (not loaded by any page)
├── data/                   # JSON data store
│   ├── data_YYYY_YYYY.json # Per-season awards data (2000-2026)
│   └── analysis.json       # Aggregated stats for control panel
├── scraper/                # Python scraping engine
│   ├── scrape_and_upload.py    # MAIN orchestrator (scrape → TMDB → upload)
│   ├── master_scraper.py       # Generic Wikipedia table parser + dispatch (scrape_single_award)
│   ├── firebase_upload.py      # Firebase upload handler
│   ├── manual_adg_data.py      # Fallback data for hard-to-scrape awards
│   ├── regenerate_analysis.py  # Regenerates analysis.json from local data
│   ├── scrapers/               # Per-award scraper modules; __init__.py = CEREMONY_MAP, URL_TEMPLATES, season logic
│   ├── tests/                  # pytest suite (offline, fixtures in tests/fixtures)
├── ScraperWPF.cs           # C# WPF desktop launcher (build with build_wpf.bat; .exe is gitignored)
```

## Key Conventions

### Data Format
- Season files: `data_YYYY_YYYY.json` (e.g., `data_2025_2026.json`)
- Categories: Best Film, Director, Actor, Actress (+ special ones like Cast, Screenplay, Animation)
- A **Win** counts as both a win AND a nomination (2 points total in stats)

### Scraping Rules
- **ONLY** run the scraper for the **current ongoing season** — NEVER re-scrape historical years
- Season auto-detection: Sep-Dec → next ceremony year; Jan-Aug → current ceremony year. Same rule in `scrapers.current_season_year`, `SEASON_START_MONTH` in app.js/control.js, and ScraperWPF.cs — keep them in sync
- `CEREMONY_MAP` is generated from per-award offsets; never hand-edit year tables
- `scraper/data_quality.py` is the safety net: `consolidate()` (called by `merge_results`) cleans titles and merges rows split by title variants / missing film (never two different films, never conflicting outcomes); `find_issues()` runs before upload and blocks seasons with problems
- Parsers: read list items with `own_text(li)` (winner `<li>` often nests the other nominees) and split "Name – Film" only on en/em dash or a spaced hyphen (bare hyphens are part of names/titles: "Lee Byung-hun", "Spider-Man")
- `--force` re-uploads only the requested seasons (it no longer uploads the whole history)
- Each award's scraper lives only in `scraper/scrapers/<award>.py` (no duplicates in master_scraper.py)
- Run tests with `py -m pytest` (no network). Add a fixture via `scraper/tests/make_fixtures.py` when changing a parser
- Past seasons in `data/` are NEVER re-scraped. They may be corrected only for verified errors, carefully: check every change against the original (no award lost or added), review ambiguous cases with the user, keep a backup. A person on two rows for two DIFFERENT films is legitimate — never merge those
- Run with: `python scraper/scrape_and_upload.py`

### Frontend
- Pure vanilla JS — no frameworks, no build tools
- SPA routing handled in `app.js`
- Premium "Netflix-style" UI with poster marquees
- Predictions: score = Σ historical P(Oscar win | precursor win / nomination) per category, excluding the predicted season
- Escape Firebase/TMDB text with `escapeHtml()` before interpolating into innerHTML

### Code Style
- JavaScript: no semicolons convention not enforced, mixed styles — match surrounding code
- Python: standard PEP 8, uses `requests`, `beautifulsoup4`, `tmdbv3api`
- Commit messages: English, imperative or descriptive, prefixed with type (Fix:, Docs:, etc.)

## Important Warnings
- `firebase-config.js` is gitignored — do not re-add it to the repo
- Do NOT run `scrape_and_upload.py` casually — it makes real HTTP requests to Wikipedia/TMDB and uploads to Firebase
- The `data/` JSON files are large — avoid reading them fully unless necessary
- `app.js` is ~2.8K lines — prefer targeted search/edit over reading it whole
- `generate_analysis_json()` also uploads analysis to Firebase — don't call it just to refresh local files
- Historical Leading/Supporting `role` labels are unreliable in older seasons (often both winners marked Leading)
