# -*- coding: utf-8 -*-
"""
Critics' Choice Awards Scraper
Uses generic scrape_award from master
"""

from . import CEREMONY_MAP, URL_TEMPLATES, ordinal


def scrape_critics(year):
    """Scrape Critics' Choice Awards for a given year"""
    # Import here to avoid circular dependency
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from master_scraper import scrape_award
    
    return scrape_award('critics', year)
