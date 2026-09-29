# -*- coding: utf-8 -*-
"""Wikipedia redirects for ceremonies not published yet must not be parsed as real pages."""

import pytest
from bs4 import BeautifulSoup

from scrapers import edition_redirect_target

WIKI = 'https://en.wikipedia.org/wiki/'


def page(canonical, redirected=True):
    note = '<span class="mw-redirectedfrom">(Redirected from x)</span>' if redirected else ''
    return BeautifulSoup(f'<html><head><link rel="canonical" href="{WIKI}{canonical}"></head>'
                         f'<body>{note}</body></html>', 'html.parser')


@pytest.mark.parametrize('requested,canonical', [
    ('54th_Annie_Awards', 'Annie_Award'),
    ('2026_New_York_Film_Critics_Circle_Awards', 'New_York_Film_Critics_Circle'),
    ('Gotham_Independent_Film_Awards_2026', 'Gotham_Independent_Film_Awards'),
    ('33rd_Actor_Awards', '32nd_Actor_Awards'),
])
def test_redirect_to_page_without_edition_is_rejected(requested, canonical):
    assert edition_redirect_target(WIKI + requested, page(canonical)) == canonical.replace('_', ' ')


@pytest.mark.parametrize('requested,canonical', [
    ('31st_Screen_Actors_Guild_Awards', '31st_Actor_Awards'),                 # rename keeps edition
    ('30th_Critics%27_Choice_Awards', '30th_Critics%27_Choice_Awards'),
    ('8th_Astra_Film_Awards', '8th_Astra_Film_Awards_(film)'),
])
def test_redirect_keeping_edition_is_accepted(requested, canonical):
    assert edition_redirect_target(WIKI + requested, page(canonical)) is None


def test_regular_page_is_accepted():
    assert edition_redirect_target(WIKI + '53rd_Annie_Awards', page('53rd_Annie_Awards', redirected=False)) is None
