# CLAUDE.md — Season Awards Nomination Tracker

## Project Overview
Web app that tracks, predicts, and analyzes major film awards candidates throughout the season.
- **Scrapes** data from Wikipedia for 20+ award ceremonies (Oscar, Golden Globe, BAFTA, SAG, etc.)
- **Enriches** with TMDB metadata (posters, genres)
- **Visualizes** in a premium dark/gold themed SPA
- **Uploads** to Firebase Realtime Database for live updates

## Tech Stack
- **Frontend:** Vanilla JS SPA (`app.js` ~105K), HTML, CSS (dark/gold theme). No framework.
- **Scraper:** Python 3 (`scraper/`), uses `requests` + `beautifulsoup4` for Wikipedia parsing, `tmdbv3api` for enrichment.
- **Data:** JSON files in `data/` (one per season: `data_YYYY_YYYY.json`, plus `analysis.json`).
- **Backend:** Firebase Realtime Database. Config in `firebase-config.js` (gitignored keys).
- **Desktop Launcher:** C# WPF app (`ScraperWPF.cs`) that wraps the Python scraper with a GUI progress bar.

## Project Structure
```
├── index.html              # SPA entry point (home page)
├── control.html            # Control panel for data validation
├── app.js                  # CORE: routing, UI rendering, stats, predictions
├── home.js                 # Home page logic (marquees, trending, animations)
├── control.js              # Control panel logic (validates data integrity)
├── styles.css / mobile.css # Styling (dark/gold premium theme)
├── firebase-config.js      # Firebase API keys (NOT in repo)
├── modules/                # Category-specific JS modules
│   ├── film.js / director.js / actor.js / actress.js
├── data/                   # JSON data store
│   ├── data_YYYY_YYYY.json # Per-season awards data (2000-2026)
│   └── analysis.json       # Aggregated stats for control panel
├── scraper/                # Python scraping engine
│   ├── scrape_and_upload.py    # MAIN orchestrator (scrape → TMDB → upload)
│   ├── master_scraper.py       # Core scraping logic & parsing rules
│   ├── firebase_upload.py      # Firebase upload handler
│   ├── manual_adg_data.py      # Fallback data for hard-to-scrape awards
│   ├── regenerate_analysis.py  # Regenerates analysis.json from local data
│   ├── scrapers/               # Per-award scraper modules (21 awards)
│   │   ├── oscar.py, gg.py, bafta.py, sag.py, critics.py, ...
├── ScraperWPF.cs / .exe    # C# WPF desktop launcher
```

## Key Conventions

### Data Format
- Season files: `data_YYYY_YYYY.json` (e.g., `data_2025_2026.json`)
- Categories: Best Film, Director, Actor, Actress (+ special ones like Cast, Screenplay, Animation)
- A **Win** counts as both a win AND a nomination (2 points total in stats)

### Scraping Rules
- **ONLY** run the scraper for the **current ongoing season** — NEVER re-scrape historical years
- Season auto-detection: Oct-Dec → next ceremony year; Jan-Sep → current ceremony year
- Historical data in `data/` is verified and should not be modified unless fixing a known bug
- Run with: `python scraper/scrape_and_upload.py`

### Frontend
- Pure vanilla JS — no frameworks, no build tools
- SPA routing handled in `app.js`
- Premium "Netflix-style" UI with poster marquees
- Predictions use weighted points based on historical precursor accuracy

### Code Style
- JavaScript: no semicolons convention not enforced, mixed styles — match surrounding code
- Python: standard PEP 8, uses `requests`, `beautifulsoup4`, `tmdbv3api`
- Commit messages: English, imperative or descriptive, prefixed with type (Fix:, Docs:, etc.)

## Important Warnings
- `firebase-config.js` contains API keys — NEVER commit or expose
- Do NOT run `scrape_and_upload.py` casually — it makes real HTTP requests to Wikipedia/TMDB and uploads to Firebase
- The `data/` JSON files are large — avoid reading them fully unless necessary
- `app.js` is ~105K lines — use targeted search/edit, don't read the whole file
