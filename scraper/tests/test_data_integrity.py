# -*- coding: utf-8 -*-
"""Integrity checks on the season files in data/."""

import glob
import json
import os
from collections import Counter

import pytest

from conftest import DATA_DIR

CATEGORIES = ['best-film', 'best-director', 'best-actor', 'best-actress']
SEASON_FILES = sorted(glob.glob(os.path.join(DATA_DIR, 'data_*_*.json')))
# Oscar winners per category (actor/actress include the supporting race)
OSCAR_WINNERS = {'best-film': 1, 'best-director': 1, 'best-actor': 2, 'best-actress': 2}


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def season_id(path):
    return os.path.basename(path)[5:-5]


@pytest.fixture(params=SEASON_FILES, ids=season_id)
def season(request):
    return load(request.param)


def test_award_values_are_win_or_nomination(season):
    bad = [(cat, e['name'], k, v)
           for cat in CATEGORIES for e in season.get(cat, [])
           for k, v in e.get('awards', {}).items() if v not in ('Y', 'X')]
    assert not bad


def test_no_duplicate_entries(season):
    keys = Counter((cat, e['name'], e.get('film', '')) for cat in CATEGORIES for e in season.get(cat, []))
    assert [k for k, n in keys.items() if n > 1] == []


def test_no_person_split_by_missing_film(season):
    """A person listed once with a film and once without is one nomination split in two."""
    split = []
    for cat in CATEGORIES[1:]:
        by_name = {}
        for e in season.get(cat, []):
            by_name.setdefault(e['name'], []).append(e)
        for name, entries in by_name.items():
            films = {e.get('film') for e in entries}
            if len(entries) > 1 and None in films and len(films - {None}) == 1:
                split.append((cat, name))
    assert split == []


def test_oscar_winner_counts(season):
    winners = {cat: sum(1 for e in season.get(cat, []) if e.get('awards', {}).get('oscar') == 'Y')
               for cat in CATEGORIES}
    if not any(winners.values()):
        pytest.skip('Oscars not held yet for this season')
    assert winners == OSCAR_WINNERS
