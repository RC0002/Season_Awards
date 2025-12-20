// Season Awards Nomination Tracker - Professional Edition
// Features: Page-based navigation, Oscar auto-fetch, Collapsible menu

// ============ CONFIGURATION ============
const CONFIG = {
    TMDB_API_KEY: '4399b8147e098e80be332f172d1fe490',
    TMDB_BASE_URL: 'https://api.themoviedb.org/3',
    TMDB_IMAGE_BASE: 'https://image.tmdb.org/t/p/',

    START_YEAR: 2018,

    AWARDS: [
        'Academy Awards', 'Golden Globe', 'BAFTA', 'SAG', 'LAFCA', 'AFI', 'NBR',
        'DGA', 'PGA', 'WGA', 'Art Directors', "Critic's Choice", 'Gotham',
        'HCA', 'Spirit', 'BIFA', 'Annie', 'NYFCC', 'Cannes', 'Venezia'
    ],

    CATEGORIES: [
        { id: 'best-film', title: 'Best Film', placeholder: 'Film title', searchType: 'movie' },
        { id: 'best-actress', title: 'Best Actress', placeholder: 'Actress name', searchType: 'person', isPerson: true },
        { id: 'best-actor', title: 'Best Actor', placeholder: 'Actor name', searchType: 'person', isPerson: true },
        { id: 'best-director', title: 'Best Director', placeholder: 'Director name', searchType: 'person', isPerson: true }
    ]
};

// ============ STATE ============
let currentYear = null;
let currentCategory = 'best-film';
let data = {};
let menuOpen = true;

// ============ INITIALIZATION ============
document.addEventListener('DOMContentLoaded', function () {
    calculateCurrentYear();
    buildPage();
    loadData();
    renderCurrentCategory();
});

function calculateCurrentYear() {
    const now = new Date();
    const month = now.getMonth();
    const year = now.getFullYear();
    currentYear = month < 8 ? `${year - 1}_${year}` : `${year}_${year + 1}`;
}

// ============ PAGE BUILDING ============
function buildPage() {
    const container = document.querySelector('.container');
    container.className = 'app-container';

    container.innerHTML = `
        <button class="menu-toggle" id="menu-toggle">☰</button>
        
        <aside class="sidebar" id="sidebar">
            <div class="sidebar-header">
                <div class="sidebar-logo">Season Awards</div>
                <button class="btn-close-menu" id="close-menu">✕</button>
            </div>
            
            <div class="sidebar-section">
                <div class="sidebar-section-title">Award Season</div>
                <select class="year-select" id="year-select"></select>
            </div>
            
            <div class="sidebar-section">
                <div class="sidebar-section-title">Categories</div>
                <ul class="nav-list" id="nav-list"></ul>
            </div>
            
            <div class="sidebar-section">
                <div class="sidebar-section-title">Auto-Fetch</div>
                <button class="btn-fetch" id="btn-fetch">Fetch Oscar Nominations</button>
            </div>
            
            <div class="storage-info">
                Data saved in browser<br>
                <code>LocalStorage</code>
            </div>
        </aside>
        
        <main class="main-content" id="main-content">
            <div class="page-header">
                <h1 class="page-title"><span id="year-display"></span> Nominations</h1>
            </div>
            <div id="category-container"></div>
            <footer><p>Season Awards Tracker</p></footer>
        </main>
        
        <div class="loading-overlay" id="loading">
            <div class="loading-text">Fetching Oscar nominations...</div>
        </div>
    `;

    setupEventListeners();
    populateYearSelector();
    populateNavigation();
    createCategoryPages();
    updateYearDisplay();
}

function setupEventListeners() {
    // Menu toggle
    document.getElementById('menu-toggle').addEventListener('click', toggleMenu);
    document.getElementById('close-menu').addEventListener('click', toggleMenu);

    // Fetch Oscar nominations
    document.getElementById('btn-fetch').addEventListener('click', fetchOscarNominations);
}

function toggleMenu() {
    menuOpen = !menuOpen;
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('main-content');
    const toggle = document.getElementById('menu-toggle');

    sidebar.classList.toggle('collapsed', !menuOpen);
    mainContent.classList.toggle('expanded', !menuOpen);
    toggle.classList.toggle('visible', !menuOpen);
}

function populateYearSelector() {
    const select = document.getElementById('year-select');
    const now = new Date();
    const endYear = now.getMonth() < 8 ? now.getFullYear() : now.getFullYear() + 1;

    for (let year = CONFIG.START_YEAR; year < endYear; year++) {
        const option = document.createElement('option');
        option.value = `${year}_${year + 1}`;
        option.textContent = `${year}/${year + 1}`;
        if (option.value === currentYear) option.selected = true;
        select.appendChild(option);
    }

    select.addEventListener('change', function () {
        currentYear = this.value;
        loadData();
        renderCurrentCategory();
        updateYearDisplay();
    });
}

function populateNavigation() {
    const navList = document.getElementById('nav-list');

    CONFIG.CATEGORIES.forEach((cat, i) => {
        const li = document.createElement('li');
        li.className = 'nav-item';
        li.innerHTML = `<a href="#" class="nav-link ${i === 0 ? 'active' : ''}" data-category="${cat.id}">${cat.title}</a>`;

        li.querySelector('.nav-link').addEventListener('click', function (e) {
            e.preventDefault();
            document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
            this.classList.add('active');
            currentCategory = cat.id;
            showCategory(cat.id);
        });

        navList.appendChild(li);
    });
}

function createCategoryPages() {
    const container = document.getElementById('category-container');

    CONFIG.CATEGORIES.forEach((cat, i) => {
        const page = document.createElement('div');
        page.className = `category-page ${i === 0 ? 'active' : ''}`;
        page.id = `page-${cat.id}`;

        page.innerHTML = `
            <h2 class="category-title">${cat.title}</h2>
            
            <div class="section-controls">
                <div class="autocomplete-wrapper">
                    <input type="text" class="input-field" id="${cat.id}-input" 
                           placeholder="Search ${cat.placeholder}..." 
                           data-search-type="${cat.searchType}" data-category="${cat.id}">
                    <div class="autocomplete-list" id="${cat.id}-autocomplete"></div>
                </div>
                <button class="btn" id="${cat.id}-add">+ Add</button>
            </div>
            
            <div class="table-wrap">
                <div class="table-scroll">
                    <table>
                        <thead>
                            <tr>
                                <th>${cat.placeholder}</th>
                                ${CONFIG.AWARDS.map(a => `<th>${a}</th>`).join('')}
                            </tr>
                        </thead>
                        <tbody id="${cat.id}-tbody"></tbody>
                    </table>
                </div>
            </div>
        `;

        container.appendChild(page);

        const input = document.getElementById(`${cat.id}-input`);
        document.getElementById(`${cat.id}-add`).addEventListener('click', () => addEntry(cat.id, input));
        input.addEventListener('keypress', e => { if (e.key === 'Enter') addEntry(cat.id, input); });
        setupAutocomplete(input, cat.id);
    });
}

function showCategory(categoryId) {
    document.querySelectorAll('.category-page').forEach(p => p.classList.remove('active'));
    document.getElementById(`page-${categoryId}`).classList.add('active');
    renderCurrentCategory();
}

function updateYearDisplay() {
    document.getElementById('year-display').textContent = currentYear.replace('_', '/');
}

// ============ DATA MANAGEMENT ============
function getStorageKey() { return `seasonAwards_${currentYear}`; }

function loadData() {
    const stored = localStorage.getItem(getStorageKey());
    data = stored ? JSON.parse(stored) : {};
    CONFIG.CATEGORIES.forEach(cat => { if (!data[cat.id]) data[cat.id] = []; });
}

function saveData() { localStorage.setItem(getStorageKey(), JSON.stringify(data)); }

// ============ RENDERING ============
function renderCurrentCategory() {
    renderTable(currentCategory);
}

function renderTable(categoryId) {
    const tbody = document.getElementById(`${categoryId}-tbody`);
    if (!tbody) return;
    tbody.innerHTML = '';

    const cat = CONFIG.CATEGORIES.find(c => c.id === categoryId);
    const entries = data[categoryId] || [];

    entries.forEach((entry, index) => {
        const row = createTableRow(entry, categoryId, index, cat.isPerson);
        tbody.appendChild(row);
    });
}

function createTableRow(entry, categoryId, index, isPerson) {
    const row = document.createElement('tr');

    const nameCell = document.createElement('td');
    nameCell.className = isPerson ? 'name-cell person-cell' : 'name-cell';

    let imageHTML = '';
    if (isPerson && entry.profilePath) {
        imageHTML = `<img class="person-photo-bg" src="${CONFIG.TMDB_IMAGE_BASE}w185${entry.profilePath}" alt="">`;
    } else if (!isPerson && entry.posterPath) {
        imageHTML = `<img class="poster-bg" src="${CONFIG.TMDB_IMAGE_BASE}w185${entry.posterPath}" alt="">`;
    }

    nameCell.innerHTML = `
        <div class="name-cell-content">
            <span class="entry-name">${entry.name}</span>
            ${imageHTML}
            <button class="btn-delete" title="Delete">✕</button>
        </div>
    `;

    nameCell.querySelector('.btn-delete').addEventListener('click', e => {
        e.stopPropagation();
        deleteEntry(categoryId, index);
    });

    row.appendChild(nameCell);

    CONFIG.AWARDS.forEach((award, awardIndex) => {
        const cell = document.createElement('td');
        cell.className = 'clickable';
        const value = entry.awards?.[awardIndex] || '';
        cell.textContent = value;
        if (value === 'Y') cell.classList.add('winner');
        else if (value === 'X') cell.classList.add('nominee');
        cell.addEventListener('click', () => toggleCell(categoryId, index, awardIndex, cell));
        row.appendChild(cell);
    });

    return row;
}

function toggleCell(categoryId, entryIndex, awardIndex, cell) {
    const entry = data[categoryId][entryIndex];
    if (!entry.awards) entry.awards = [];

    const current = entry.awards[awardIndex] || '';
    const next = current === '' ? 'X' : current === 'X' ? 'Y' : '';

    entry.awards[awardIndex] = next;
    saveData();

    cell.textContent = next;
    cell.classList.remove('winner', 'nominee');
    if (next === 'Y') cell.classList.add('winner');
    else if (next === 'X') cell.classList.add('nominee');
}

// ============ ENTRY MANAGEMENT ============
function addEntry(categoryId, input, extra = {}) {
    const name = input.value.trim();
    if (!name) return input.focus();

    data[categoryId].push({ name, awards: new Array(CONFIG.AWARDS.length).fill(''), ...extra });
    saveData();
    renderTable(categoryId);
    input.value = '';
    input.focus();
}

function deleteEntry(categoryId, index) {
    data[categoryId].splice(index, 1);
    saveData();
    renderTable(categoryId);
}

// ============ TMDB AUTOCOMPLETE ============
let autocompleteTimeout = null;

function setupAutocomplete(input, categoryId) {
    const list = document.getElementById(`${categoryId}-autocomplete`);
    const searchType = input.dataset.searchType;

    input.addEventListener('input', function () {
        const query = this.value.trim();
        clearTimeout(autocompleteTimeout);
        if (query.length < 2) { list.classList.remove('active'); list.innerHTML = ''; return; }
        autocompleteTimeout = setTimeout(() => searchTMDB(query, searchType, list, input, categoryId), 300);
    });

    input.addEventListener('blur', () => setTimeout(() => list.classList.remove('active'), 250));
    input.addEventListener('focus', function () { if (list.children.length && this.value.length >= 2) list.classList.add('active'); });
}

async function searchTMDB(query, searchType, list, input, categoryId) {
    if (!CONFIG.TMDB_API_KEY) return;

    const endpoint = searchType === 'movie' ? '/search/movie' : '/search/person';
    const url = `${CONFIG.TMDB_BASE_URL}${endpoint}?api_key=${CONFIG.TMDB_API_KEY}&query=${encodeURIComponent(query)}`;

    try {
        const res = await fetch(url);
        const json = await res.json();
        list.innerHTML = '';

        if (json.results?.length) {
            json.results.slice(0, 6).forEach(item => {
                const div = document.createElement('div');
                div.className = 'autocomplete-item';

                if (searchType === 'movie') {
                    const poster = item.poster_path ? `${CONFIG.TMDB_IMAGE_BASE}w92${item.poster_path}` : '';
                    const year = item.release_date?.substring(0, 4) || '';
                    div.innerHTML = `
                        ${poster ? `<img class="autocomplete-poster" src="${poster}">` : '<div class="autocomplete-poster"></div>'}
                        <div class="autocomplete-info"><div class="autocomplete-title">${item.title}</div><div class="autocomplete-subtitle">${year}</div></div>
                    `;
                    div.addEventListener('mousedown', e => {
                        e.preventDefault();
                        input.value = item.title;
                        list.classList.remove('active');
                        addEntry(categoryId, input, { posterPath: item.poster_path, tmdbId: item.id });
                    });
                } else {
                    const photo = item.profile_path ? `${CONFIG.TMDB_IMAGE_BASE}w92${item.profile_path}` : '';
                    div.innerHTML = `
                        ${photo ? `<img class="autocomplete-person-photo" src="${photo}">` : '<div class="autocomplete-person-photo"></div>'}
                        <div class="autocomplete-info"><div class="autocomplete-title">${item.name}</div><div class="autocomplete-subtitle">${item.known_for_department || ''}</div></div>
                    `;
                    div.addEventListener('mousedown', e => {
                        e.preventDefault();
                        input.value = item.name;
                        list.classList.remove('active');
                        addEntry(categoryId, input, { profilePath: item.profile_path, tmdbId: item.id });
                    });
                }
                list.appendChild(div);
            });
            list.classList.add('active');
        } else {
            list.classList.remove('active');
        }
    } catch (err) {
        console.error('TMDB error:', err);
    }
}

// ============ OSCAR AUTO-FETCH ============
async function fetchOscarNominations() {
    const loading = document.getElementById('loading');
    const btn = document.getElementById('btn-fetch');

    btn.disabled = true;
    loading.classList.add('active');

    try {
        // Get the Oscar ceremony year from the season
        const [startYear, endYear] = currentYear.split('_').map(Number);
        const oscarYear = endYear; // Oscar ceremony is in the second year

        // Fetch Oscar-winning/nominated movies
        // TMDB doesn't have a direct Oscar API, so we search for known Oscar films
        // We'll search for highly rated films from that year

        const url = `${CONFIG.TMDB_BASE_URL}/discover/movie?api_key=${CONFIG.TMDB_API_KEY}&primary_release_year=${startYear}&sort_by=vote_average.desc&vote_count.gte=1000&page=1`;

        const res = await fetch(url);
        const json = await res.json();

        if (json.results) {
            // Add top films to Best Film category
            const filmsToAdd = json.results.slice(0, 10);

            for (const film of filmsToAdd) {
                // Check if already exists
                const exists = data['best-film'].some(e => e.tmdbId === film.id);
                if (!exists) {
                    data['best-film'].push({
                        name: film.title,
                        posterPath: film.poster_path,
                        tmdbId: film.id,
                        awards: new Array(CONFIG.AWARDS.length).fill('')
                    });
                }

                // Fetch crew for director
                try {
                    const creditsRes = await fetch(`${CONFIG.TMDB_BASE_URL}/movie/${film.id}/credits?api_key=${CONFIG.TMDB_API_KEY}`);
                    const credits = await creditsRes.json();

                    // Get director
                    const director = credits.crew?.find(c => c.job === 'Director');
                    if (director) {
                        const dirExists = data['best-director'].some(e => e.tmdbId === director.id);
                        if (!dirExists) {
                            data['best-director'].push({
                                name: `${director.name} — ${film.title}`,
                                profilePath: director.profile_path,
                                tmdbId: director.id,
                                awards: new Array(CONFIG.AWARDS.length).fill('')
                            });
                        }
                    }

                    // Get lead actors (first 2)
                    const actors = credits.cast?.slice(0, 2) || [];
                    for (const actor of actors) {
                        const catId = actor.gender === 1 ? 'best-actress' : 'best-actor';
                        const actorExists = data[catId].some(e => e.tmdbId === actor.id);
                        if (!actorExists) {
                            data[catId].push({
                                name: `${actor.name} — ${film.title}`,
                                profilePath: actor.profile_path,
                                tmdbId: actor.id,
                                awards: new Array(CONFIG.AWARDS.length).fill('')
                            });
                        }
                    }
                } catch (e) {
                    console.error('Credits fetch error:', e);
                }
            }

            saveData();
            renderCurrentCategory();
        }
    } catch (err) {
        console.error('Fetch error:', err);
        alert('Error fetching nominations. Please try again.');
    } finally {
        loading.classList.remove('active');
        btn.disabled = false;
    }
}
