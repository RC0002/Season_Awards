# -*- coding: utf-8 -*-
"""
Downloads the Wikipedia pages used by the regression tests and keeps only their
wikitables (the part the parsers read), so fixtures stay small.

Run manually when adding a fixture:  py scraper/tests/make_fixtures.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers import CEREMONY_MAP, URL_TEMPLATES, fetch_page, ordinal  # noqa: E402

FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')

# (award, season year) pairs parsed by master_scraper.scrape_award
FIXTURES = [
    ('oscar', 2025),
    ('gg', 2025),
    ('bafta', 2025),
    ('critics', 2025),
]


def fixture_path(award, year):
    return os.path.join(FIXTURES_DIR, f'{award}_{year}.html')


def main():
    os.makedirs(FIXTURES_DIR, exist_ok=True)
    for award, year in FIXTURES:
        url = URL_TEMPLATES[award].format(ord=ordinal(CEREMONY_MAP[award][year]))
        soup = fetch_page(url)
        if not soup:
            print(f'  FAILED {award} {year}: {url}')
            continue
        tables = soup.find_all('table', class_='wikitable')
        html = '<html><body>\n' + '\n'.join(str(t) for t in tables) + '\n</body></html>\n'
        with open(fixture_path(award, year), 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'  {award} {year}: {len(tables)} tables, {len(html) // 1024} KB <- {url}')


if __name__ == '__main__':
    main()
