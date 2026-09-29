# -*- coding: utf-8 -*-
"""Shared pytest setup: make scraper/ importable and block real network access."""

import os
import sys

import pytest

SCRAPER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_DIR = os.path.dirname(SCRAPER_DIR)
DATA_DIR = os.path.join(PROJECT_DIR, 'data')
FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')

sys.path.insert(0, SCRAPER_DIR)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Tests must never hit Wikipedia/TMDB/Firebase."""
    import requests

    def blocked(*args, **kwargs):
        raise RuntimeError('Network access is disabled in tests')

    monkeypatch.setattr(requests, 'get', blocked)
    monkeypatch.setattr(requests, 'post', blocked)
    monkeypatch.setattr(requests, 'put', blocked)
