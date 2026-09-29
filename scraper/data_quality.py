# -*- coding: utf-8 -*-
"""
Data quality safety net for scraped seasons.

Parsers occasionally emit the same film with a different spelling ("Adaptation." / "Adaptation",
"BROKEBACK MOUNTAIN", "Oppenheimer (Universal Pictures)", "Dune (TIE)") or a person without
their film. merge_results() matches on exact strings, so every variant used to become a separate
row. This module normalizes titles and consolidates rows, and reports anything still suspicious
before a season is uploaded.

A person with rows for two DIFFERENT films (e.g. Kate Winslet 2008: The Reader / Revolutionary
Road) is legitimate and is never merged.
"""

import re
import unicodedata
from collections import Counter, defaultdict

CATEGORIES = ['best-film', 'best-director', 'best-actor', 'best-actress']
PERSON_CATEGORIES = CATEGORIES[1:]
VALID_OUTCOMES = ('Y', 'X')
_EXTRA_FIELDS = ['posterPath', 'profilePath', 'tmdbId', 'genre', 'role']

# Trailing "(Distributor)" added by some award pages, e.g. "Past Lives (A24)"
_DISTRIBUTOR = re.compile(
    r'\s*\((?:[^()]*\b(?:Pictures|Films?|Studios?|Features|Entertainment|Releasing|Netflix|A24|Neon|'
    r'Searchlight|Focus|Apple|Amazon|MGM|Universal|Warner|Paramount|Sony|Lionsgate|Mubi|IFC|'
    r'Magnolia|Janus|Sideshow|Roadside|Orion|Disney|Pixar|DreamWorks|HBO|Bleecker|Annapurna)\b[^()]*)\)\s*$',
    re.IGNORECASE)


_SEQUEL_WORDS = {'ii', 'iii', 'iv', 'v', 'vi', 'part', 'chapter', 'vol', 'volume', 'episode', 'returns', 'reloaded'}


def clean_title(title):
    """Remove parser debris from a film title (keeps the real title untouched otherwise)."""
    if not title:
        return title
    t = title.split('\n')[0]                        # "Anora \n Ali Abbasi" -> "Anora"
    t = re.sub(r'\s*\[[^\]]*\]', '', t)             # footnotes "[1]", "[a]"
    t = re.sub(r'\s*\(tie\)', '', t, flags=re.I)    # "Dune (TIE)"
    t = _DISTRIBUTOR.sub('', t)
    t = re.sub(r'^[\s\-–—|:,]+', '', t)            # leading "- " left by a split
    return ' '.join(t.split())


def _strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


def norm_title(title):
    t = _strip_accents(clean_title(title) or '').lower()
    m = re.match(r'^(.*), (the|a|an)$', t)            # "Curious Case Of Benjamin Button, The"
    if m:
        t = f'{m.group(2)} {m.group(1)}'
    t = re.sub(r'[^a-z0-9 ]', ' ', t)
    return ' '.join(t.split())


def same_title(a, b):
    """Same film: equal after normalization, or one is a word-prefix of the other
    ("Birdman" / "Birdman or (The Unexpected Virtue of Ignorance)")."""
    na, nb = norm_title(a), norm_title(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    short, long_ = sorted([na, nb], key=len)
    if len(short) < 5 or not long_.startswith(short + ' '):
        return False
    # A sequel is a different film: "Frozen" / "Frozen II", "Dune" / "Dune Part Two".
    # "X and Y" is a combined citation or a longer title: "Fantastic Mr. Fox and Up in the Air",
    # "Harry Potter" (series) / "Harry Potter and the Deathly Hallows".
    first_extra = long_[len(short):].split()[0]
    return not (first_extra.isdigit() or first_extra in _SEQUEL_WORDS or first_extra == 'and'
                or re.search(r'\s&\s', clean_title(a if len(norm_title(a)) > len(norm_title(b)) else b)))


def norm_name(name):
    return ' '.join(_strip_accents(name).lower().split())


def _title_badness(title):
    return title.isupper() + ('(' in title) + ('[' in title) + ('\n' in title)


def _merge_awards(rows):
    """Merge award dicts; None if the same award has conflicting outcomes."""
    merged = {}
    for r in rows:
        for k, v in r.get('awards', {}).items():
            if k in merged and merged[k] != v:
                return None
            merged[k] = v
    return merged


def _combine(rows, **overrides):
    awards = _merge_awards(rows)
    if awards is None:
        return None
    # Keep the row with the most awards as the base (it usually has the cleanest metadata)
    base = dict(max(rows, key=lambda r: len(r.get('awards', {}))))
    base['awards'] = awards
    for r in rows:
        for k in _EXTRA_FIELDS:
            if k not in base and k in r:
                base[k] = r[k]
    base.update(overrides)
    return base


def _cluster(items, key, same):
    clusters = []
    for it in items:
        for c in clusters:
            if same(key(it), key(c[0])):
                c.append(it)
                break
        else:
            clusters.append([it])
    return clusters


def consolidate(data):
    """
    Clean titles and merge rows that describe the same film / person+film.
    Returns (data, notes) where notes describe every merge performed.
    """
    notes = []

    # 1) Best film: clean names, merge spelling variants
    films = []
    for e in data.get('best-film', []):
        e = dict(e)
        e['name'] = clean_title(e['name']) or e['name']
        films.append(e)
    merged_films = []
    for c in _cluster(films, lambda e: e['name'], same_title):
        if len(c) == 1:
            merged_films.append(c[0])
            continue
        best = min((e['name'] for e in c), key=lambda t: (_title_badness(t), -len(norm_title(t)), len(t)))
        combined = _combine(c, name=best)
        if combined is None:
            merged_films.extend(c)
            notes.append(f'best-film: NOT merged (conflicting outcomes): {[e["name"] for e in c]}')
        else:
            merged_films.append(combined)
            notes.append(f'best-film: merged {[e["name"] for e in c]} -> {best!r}')
    data['best-film'] = merged_films
    film_names = [e['name'] for e in merged_films]

    def canonical_film(title):
        for f in film_names:
            if same_title(title, f):
                return f
        return title

    # 2) People: clean film titles, align them to the Best Film spelling, merge variants
    for cat in PERSON_CATEGORIES:
        by_person = defaultdict(list)
        order = []
        for e in data.get(cat, []):
            e = dict(e)
            if e.get('film'):
                film = clean_title(e['film'])
                if film:
                    e['film'] = canonical_film(film)
                else:
                    del e['film']  # the "film" was only debris, e.g. "[a]"
            key = norm_name(e['name'])
            if key not in by_person:
                order.append(key)
            by_person[key].append(e)

        out = []
        for key in order:
            rows = by_person[key]
            # Prefer the accented/longest spelling of the name ("Penélope" over "Penelope")
            name = max((r['name'] for r in rows), key=lambda n: (n != _strip_accents(n), len(n)))
            with_film = [r for r in rows if r.get('film')]
            without_film = [r for r in rows if not r.get('film')]

            groups = _cluster(with_film, lambda r: r['film'], same_title)
            # A row without film belongs to the person's only film, if there is exactly one
            if without_film and len(groups) == 1:
                groups[0].extend(without_film)
                without_film = []
            elif len(without_film) > 1:
                groups.append(without_film)
                without_film = []

            for g in groups:
                if len(g) == 1:
                    g[0]['name'] = name
                    out.append(g[0])
                    continue
                titles = [r['film'] for r in g if r.get('film')]
                film = min(titles, key=lambda t: (t not in film_names, _title_badness(t), -len(norm_title(t))))\
                    if titles else None
                overrides = {'name': name}
                if film:
                    overrides['film'] = film
                combined = _combine(g, **overrides)
                if combined is None:
                    out.extend(g)
                    notes.append(f'{cat}: NOT merged (conflicting outcomes): {name} {[r.get("film") for r in g]}')
                else:
                    out.append(combined)
                    notes.append(f'{cat}: merged {name} {[r.get("film") for r in g]} -> {film!r}')
            for r in without_film:
                r['name'] = name
                out.append(r)
        data[cat] = out

    return data, notes


def find_issues(data):
    """Problems that should block an automatic upload. Returns a list of strings (empty = OK)."""
    issues = []
    for cat in CATEGORIES:
        keys = Counter()
        for e in data.get(cat, []):
            name = e.get('name') or ''
            film = e.get('film') or ''
            keys[(norm_name(name), norm_title(film))] += 1
            bad = {k: v for k, v in e.get('awards', {}).items() if v not in VALID_OUTCOMES}
            if bad:
                issues.append(f'{cat}: {name!r} has invalid award values {bad}')
            if not e.get('awards'):
                issues.append(f'{cat}: {name!r} has no awards')
            if '\n' in name + film or re.search(r'\[[^\]]*\]', name + film):
                issues.append(f'{cat}: {name!r} / {film!r} contains parser debris')
        for (name, film), n in keys.items():
            if n > 1:
                issues.append(f'{cat}: duplicate row {name!r} / {film!r} (x{n})')
        if cat in PERSON_CATEGORIES:
            by = defaultdict(set)
            for e in data.get(cat, []):
                by[norm_name(e['name'])].add(norm_title(e.get('film') or ''))
            for name, films in by.items():
                if '' in films and len(films - {''}) == 1:
                    issues.append(f'{cat}: {name!r} split in two rows (one without film)')
    return issues
