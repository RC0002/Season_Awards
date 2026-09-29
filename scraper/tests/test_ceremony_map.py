# -*- coding: utf-8 -*-
"""Ceremony mapping: known editions, and coverage of the current/next season."""

import pytest

from scrapers import CEREMONY_MAP, current_season_year, ordinal

# Verified editions for the 2024/25 season (season year 2025)
KNOWN_2025 = {
    'oscar': 97, 'gg': 82, 'bafta': 78, 'sag': 31, 'critics': 30,
    'afi': 2024, 'nbr': 2024, 'venice': 81, 'dga': 2024, 'pga': 36,
    'lafca': 2024, 'wga': 77, 'adg': 2024, 'gotham': 2024, 'annie': 52,
    'astra': 8, 'spirit': 40, 'bifa': 2024, 'cannes': 2024, 'nyfcc': 2024,
}


@pytest.mark.parametrize('award,expected', sorted(KNOWN_2025.items()))
def test_known_editions_2025(award, expected):
    assert CEREMONY_MAP[award][2025] == expected


def test_dga_switches_to_wikipedia_editions_in_2026():
    assert CEREMONY_MAP['dga'][2026] == 78
    assert CEREMONY_MAP['dga'][2027] == 79
    assert CEREMONY_MAP['dga'][2001] == 2000


def test_astra_starts_in_2018():
    assert CEREMONY_MAP['astra'][2018] == 1
    assert 2017 not in CEREMONY_MAP['astra']


@pytest.mark.parametrize('award', sorted(CEREMONY_MAP))
def test_current_and_next_season_are_mapped(award):
    season = current_season_year()
    assert season in CEREMONY_MAP[award]
    assert season + 1 in CEREMONY_MAP[award]


def test_ordinal():
    assert [ordinal(n) for n in (1, 2, 3, 4, 11, 12, 13, 21, 22, 97, 101, 111)] == [
        '1st', '2nd', '3rd', '4th', '11th', '12th', '13th', '21st', '22nd', '97th', '101st', '111th']
