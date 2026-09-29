# -*- coding: utf-8 -*-
"""Safety net that merges rows split by title variants, and the pre-upload quality check."""

import copy
import glob
import json
import os

import pytest
from bs4 import BeautifulSoup

from conftest import DATA_DIR
from data_quality import clean_title, consolidate, find_issues, same_title
from scrapers import own_text


@pytest.mark.parametrize('raw,clean', [
    ('Anora \n Ali Abbasi', 'Anora'),
    ('The Queen [ 1 ]', 'The Queen'),
    ('[3]', ''),
    ('Dune (TIE)', 'Dune'),
    ('Past Lives (A24)', 'Past Lives'),
    ('American Fiction (Orion Pictures / Amazon MGM Studios)', 'American Fiction'),
    ("Pan's Labyrinth (El laberinto del fauno)", "Pan's Labyrinth (El laberinto del fauno)"),
    ('Birdman or (The Unexpected Virtue of Ignorance)', 'Birdman or (The Unexpected Virtue of Ignorance)'),
])
def test_clean_title(raw, clean):
    assert clean_title(raw) == clean


@pytest.mark.parametrize('a,b', [
    ('Adaptation', 'Adaptation.'),
    ('Brokeback Mountain', 'BROKEBACK MOUNTAIN'),
    ('The Curious Case of Benjamin Button', 'Curious Case Of Benjamin Button, The'),
    ('Birdman', 'Birdman or (The Unexpected Virtue of Ignorance)'),
    ('Precious', "Precious: Based on the Novel 'Push' by Sapphire"),
    ('Les Misérables', 'Les Miserables'),
    ("Ma Rainey's Black Bottom", 'Ma Rainey’s Black Bottom'),
])
def test_same_title(a, b):
    assert same_title(a, b)


@pytest.mark.parametrize('a,b', [
    ('Frozen', 'Frozen II'),
    ('Toy Story', 'Toy Story 4'),
    ('Dune', 'Dune: Part Two'),
    ('The Reader', 'Revolutionary Road'),
    ('Erin Brockovich', 'Traffic'),
])
def test_different_films_are_not_the_same_title(a, b):
    assert not same_title(a, b)


def season(**cats):
    base = {c: [] for c in ['best-film', 'best-director', 'best-actor', 'best-actress']}
    base.update(cats)
    return base


def test_merges_title_variants_and_uses_best_film_spelling():
    data = season(**{
        'best-film': [{'name': 'Birdman or (The Unexpected Virtue of Ignorance)', 'awards': {'oscar': 'Y'}},
                      {'name': 'Birdman', 'awards': {'sag': 'Y', 'gg': 'X'}}],
        'best-actor': [{'name': 'Michael Keaton', 'film': 'Birdman', 'awards': {'gg': 'Y'}},
                       {'name': 'Michael Keaton', 'film': 'Birdman or (The Unexpected Virtue of Ignorance)',
                        'awards': {'oscar': 'X'}}],
    })
    data, _ = consolidate(data)
    assert len(data['best-film']) == 1
    assert data['best-film'][0]['awards'] == {'oscar': 'Y', 'sag': 'Y', 'gg': 'X'}
    assert len(data['best-actor']) == 1
    assert data['best-actor'][0]['film'] == data['best-film'][0]['name']
    assert data['best-actor'][0]['awards'] == {'gg': 'Y', 'oscar': 'X'}


def test_row_without_film_joins_the_only_film():
    data = season(**{'best-actress': [
        {'name': 'Julia Roberts', 'film': 'Erin Brockovich', 'awards': {'oscar': 'Y'}},
        {'name': 'Julia Roberts', 'awards': {'gg': 'Y'}},
    ]})
    data, _ = consolidate(data)
    assert data['best-actress'] == [{'name': 'Julia Roberts', 'film': 'Erin Brockovich',
                                     'awards': {'oscar': 'Y', 'gg': 'Y'}}]


def test_two_different_films_stay_separate():
    rows = [{'name': 'Kate Winslet', 'film': 'The Reader', 'awards': {'oscar': 'Y'}},
            {'name': 'Kate Winslet', 'film': 'Revolutionary Road', 'awards': {'gg': 'Y'}},
            {'name': 'Kate Winslet', 'awards': {'critics': 'X'}}]  # ambiguous: which film?
    data, _ = consolidate(season(**{'best-actress': copy.deepcopy(rows)}))
    assert len(data['best-actress']) == 3


def test_conflicting_outcomes_are_not_merged():
    rows = [{'name': 'A Person', 'film': 'Some Film', 'awards': {'gg': 'Y'}},
            {'name': 'A Person', 'film': 'SOME FILM', 'awards': {'gg': 'X'}}]
    data, notes = consolidate(season(**{'best-actor': copy.deepcopy(rows)}))
    assert len(data['best-actor']) == 2
    assert any('NOT merged' in n for n in notes)


def test_accent_variants_of_a_name_are_merged():
    data = season(**{'best-actress': [
        {'name': 'Penélope Cruz', 'film': 'Vicky Cristina Barcelona', 'awards': {'oscar': 'Y'}},
        {'name': 'Penelope Cruz', 'film': 'Vicky Cristina Barcelona', 'awards': {'critics': 'X'}},
    ]})
    data, _ = consolidate(data)
    assert [e['name'] for e in data['best-actress']] == ['Penélope Cruz']


SEASON_FILES = sorted(glob.glob(os.path.join(DATA_DIR, 'data_*_*.json')))


@pytest.mark.parametrize('path', SEASON_FILES, ids=lambda p: os.path.basename(p)[5:-5])
def test_consolidate_leaves_verified_seasons_unchanged(path):
    """The verified history is clean: the safety net must not merge anything in it."""
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    before = copy.deepcopy(data)
    after, notes = consolidate(data)
    assert notes == []
    for cat in before:
        assert sorted(json.dumps(e, sort_keys=True) for e in after[cat]) == \
               sorted(json.dumps(e, sort_keys=True) for e in before[cat]), cat


@pytest.mark.parametrize('path', SEASON_FILES, ids=lambda p: os.path.basename(p)[5:-5])
def test_verified_seasons_pass_the_upload_check(path):
    with open(path, encoding='utf-8') as f:
        assert find_issues(json.load(f)) == []


def test_find_issues_flags_problems():
    data = season(**{
        'best-film': [{'name': 'X', 'awards': {'gg': {'winner': True}}}],
        'best-director': [{'name': 'Clint Bentley', 'film': 'Train Dreams \n Mary Bronstein', 'awards': {'spirit': 'Y'}}],
        'best-actor': [{'name': 'Tom Hanks', 'film': 'Cast Away', 'awards': {'oscar': 'X'}},
                       {'name': 'Tom Hanks', 'awards': {'gg': 'Y'}}],
    })
    issues = ' | '.join(find_issues(data))
    assert 'invalid award values' in issues
    assert 'parser debris' in issues
    assert 'split in two rows' in issues


def test_own_text_ignores_nested_nominee_list():
    li = BeautifulSoup('<ul><li><b>Clint Bentley – <i>Train Dreams</i></b>'
                       '<ul><li>Mary Bronstein – <i>If I Had Legs</i></li></ul></li></ul>',
                       'html.parser').li
    assert own_text(li) == 'Clint Bentley – Train Dreams'
