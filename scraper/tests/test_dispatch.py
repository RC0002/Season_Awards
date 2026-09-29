# -*- coding: utf-8 -*-
"""Every award is routed to a scraper with the right argument (season year or ceremony)."""

import pytest

import master_scraper
from scrapers import CEREMONY_MAP


@pytest.mark.parametrize('award', master_scraper.ALL_AWARDS)
def test_dispatch_passes_expected_argument(award, monkeypatch):
    year = 2025
    calls = []

    def fake(arg):
        calls.append(arg)
        return {'best-film': [{'name': 'X', 'awards': {award: 'Y'}}]}

    for table in (master_scraper._SEASON_YEAR_SCRAPERS, master_scraper._CEREMONY_SCRAPERS):
        for key in table:
            monkeypatch.setitem(table, key, fake)
    monkeypatch.setattr(master_scraper, 'scrape_dga', fake)
    monkeypatch.setattr(master_scraper, 'scrape_dga_wikipedia', fake)
    monkeypatch.setattr(master_scraper, 'scrape_award', lambda key, y: fake(y))

    result = master_scraper.scrape_single_award(award, year)

    assert result
    if award in master_scraper._CEREMONY_SCRAPERS or award == 'dga':
        assert calls == [CEREMONY_MAP[award][year]]
    else:
        assert calls == [year]


def test_unmapped_year_returns_empty():
    assert master_scraper.scrape_single_award('oscar', 1990) == {}


def test_nyfcc_fetches_the_film_year_page(monkeypatch):
    """Season 2025/26 = NYFCC awards for 2025 films (the year was once converted twice)."""
    import scrapers.nyfcc
    urls = []
    monkeypatch.setattr(scrapers.nyfcc, 'fetch_page', lambda url: urls.append(url))

    master_scraper.scrape_single_award('nyfcc', 2026)

    assert urls == ['https://en.wikipedia.org/wiki/2025_New_York_Film_Critics_Circle_Awards']
