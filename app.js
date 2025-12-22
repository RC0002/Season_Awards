// Season Awards Nomination Tracker
// Features: Local JSON file storage with LocalStorage backup

// ============ CONFIGURATION ============
const CONFIG = {
    // TMDB for search
    TMDB_API_KEY: '4399b8147e098e80be332f172d1fe490',
    TMDB_BASE_URL: 'https://api.themoviedb.org/3',
    TMDB_IMAGE_BASE: 'https://image.tmdb.org/t/p/',

    // Data file path
    DATA_FILE: 'data/awards_data.json',

    START_YEAR: 2018,

    AWARDS: [
        'Academy', 'GG', 'BAFTA', 'SAG', 'LAFCA', 'AFI', 'NBR',
        'DGA', 'PGA', 'WGA', 'ADG', 'Critics', 'Gotham',
        'HCA', 'Spirit', 'BIFA', 'Annie', 'NYFCC', 'Cannes', 'Venice'
    ],

    CATEGORIES: [
        { id: 'best-film', title: 'Best Film', placeholder: 'Film', searchType: 'movie', isPerson: false },
        { id: 'best-actress', title: 'Best Actress', placeholder: 'Actress', searchType: 'person', isPerson: true },
        { id: 'best-actor', title: 'Best Actor', placeholder: 'Actor', searchType: 'person', isPerson: true },
        { id: 'best-director', title: 'Best Director', placeholder: 'Director', searchType: 'person', isPerson: true }
    ]
};

// ============ STATE ============
let currentYear = null;
let currentCategory = 'best-film';
let allData = {}; // All years data from JSON
let data = {};    // Current year data
let editMode = true;

// ============ INITIALIZATION ============
document.addEventListener('DOMContentLoaded', () => {
    calculateCurrentYear();
    buildPage();
    loadData();
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
    container.className = '';

    container.innerHTML = `
        <!-- Top Navigation -->
        <nav class="top-nav">
            <div class="nav-container">
                <div class="nav-logo">Season Awards</div>
                <div class="nav-links" id="nav-links"></div>
                <div class="nav-actions">
                    <select class="nav-year-select" id="year-select"></select>
                    <div class="edit-toggle">
                        <span>Edit</span>
                        <div class="toggle-switch active" id="edit-toggle"></div>
                    </div>
                    <div class="sync-status" id="sync-status">
                        <span class="sync-dot"></span>
                        <span>Saved</span>
                    </div>
                </div>
            </div>
        </nav>
        
        <!-- Main Content -->
        <main class="main-content">
            <div class="page-header">
                <h1 class="page-title"><span id="year-display"></span> Nominations</h1>
            </div>
            <div id="category-container"></div>
            <footer><p>Season Awards Nomination Tracker</p></footer>
        </main>
        
        <div class="loading-overlay" id="loading">
            <div class="loading-text">Loading...</div>
        </div>
    `;

    setupNavigation();
    setupYearSelector();
    setupEditToggle();
    createCategoryPages();
    updateYearDisplay();
}

function setupNavigation() {
    const navLinks = document.getElementById('nav-links');

    CONFIG.CATEGORIES.forEach((cat, i) => {
        const link = document.createElement('a');
        link.href = '#';
        link.className = `nav-link ${i === 0 ? 'active' : ''}`;
        link.textContent = cat.title;

        link.addEventListener('click', (e) => {
            e.preventDefault();
            document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
            link.classList.add('active');
            currentCategory = cat.id;
            showCategory(cat.id);
        });

        navLinks.appendChild(link);
    });
}

function setupYearSelector() {
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
        switchYear();
    });
}

function setupEditToggle() {
    const toggle = document.getElementById('edit-toggle');

    toggle.addEventListener('click', () => {
        editMode = !editMode;
        toggle.classList.toggle('active', editMode);
        updateEditState();
    });
}

function updateEditState() {
    document.querySelectorAll('.input-field, .btn').forEach(el => {
        el.disabled = !editMode;
    });
    document.querySelectorAll('td.clickable').forEach(cell => {
        cell.classList.toggle('locked', !editMode);
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
                           data-search-type="${cat.searchType}">
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
}

function updateYearDisplay() {
    document.getElementById('year-display').textContent = currentYear.replace('_', '/');
}

// ============ DATA MANAGEMENT ============
// Load data: First try JSON file, then LocalStorage as backup
async function loadData() {
    showLoading(true);

    try {
        // Try to load from JSON file first
        const response = await fetch(CONFIG.DATA_FILE);
        if (response.ok) {
            allData = await response.json();
            console.log('Loaded data from JSON file');
        } else {
            throw new Error('JSON file not found');
        }
    } catch (err) {
        console.log('JSON file not available, using LocalStorage');
        // Fall back to LocalStorage
        const stored = localStorage.getItem('seasonAwards_allData');
        if (stored) {
            allData = JSON.parse(stored);
        } else {
            allData = {};
        }
    }

    // Initialize current year if not exists
    if (!allData[currentYear]) {
        allData[currentYear] = {};
        CONFIG.CATEGORIES.forEach(cat => {
            allData[currentYear][cat.id] = [];
        });
    }

    data = allData[currentYear];
    renderAllTables();
    showLoading(false);
}

function switchYear() {
    // Initialize year if not exists
    if (!allData[currentYear]) {
        allData[currentYear] = {};
        CONFIG.CATEGORIES.forEach(cat => {
            allData[currentYear][cat.id] = [];
        });
    }

    data = allData[currentYear];
    renderAllTables();
    updateYearDisplay();
}

// Save to LocalStorage (primary storage for browser session)
function saveData() {
    // Update allData with current year data
    allData[currentYear] = data;

    // Save to LocalStorage
    localStorage.setItem('seasonAwards_allData', JSON.stringify(allData));

    // Update sync status
    updateSyncStatus('saving');

    clearTimeout(window.saveTimeout);
    window.saveTimeout = setTimeout(() => {
        updateSyncStatus('saved');
    }, 300);
}

function downloadJSON() {
    const blob = new Blob([JSON.stringify(allData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'awards_data.json';
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function updateSyncStatus(status) {
    const el = document.getElementById('sync-status');
    el.className = 'sync-status';

    if (status === 'saving') {
        el.classList.add('saving');
        el.querySelector('span:last-child').textContent = 'Saving...';
    } else {
        el.querySelector('span:last-child').textContent = 'Saved';
    }
}

function showLoading(show) {
    document.getElementById('loading').classList.toggle('active', show);
}

// ============ TABLE RENDERING ============
function renderAllTables() {
    CONFIG.CATEGORIES.forEach(cat => renderTable(cat.id));
}

function renderTable(categoryId) {
    const tbody = document.getElementById(`${categoryId}-tbody`);
    if (!tbody) return;
    tbody.innerHTML = '';

    const cat = CONFIG.CATEGORIES.find(c => c.id === categoryId);
    const entries = data[categoryId] || [];

    entries.forEach((entry, index) => {
        tbody.appendChild(createTableRow(entry, categoryId, index, cat.isPerson));
    });
}

function createTableRow(entry, categoryId, index, isPerson) {
    const row = document.createElement('tr');

    // Name cell
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
        if (editMode) deleteEntry(categoryId, index);
    });

    row.appendChild(nameCell);

    // Award cells
    CONFIG.AWARDS.forEach((award, awardIndex) => {
        const cell = document.createElement('td');
        cell.className = 'clickable' + (editMode ? '' : ' locked');

        const value = entry.awards?.[awardIndex] || '';

        if (value === 'X') {
            cell.classList.add('nominee');
        } else if (value === 'Y') {
            cell.classList.add('winner');
        }

        cell.addEventListener('click', () => {
            if (editMode) toggleCell(categoryId, index, awardIndex, cell);
        });

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

    // Update cell
    cell.classList.remove('winner', 'nominee');
    if (next === 'X') {
        cell.classList.add('nominee');
    } else if (next === 'Y') {
        cell.classList.add('winner');
    }
}

// ============ ENTRY MANAGEMENT ============
function addEntry(categoryId, input, extra = {}) {
    if (!editMode) return;

    const name = input.value.trim();
    if (!name) return input.focus();

    if (!data[categoryId]) data[categoryId] = [];

    data[categoryId].push({
        name,
        awards: new Array(CONFIG.AWARDS.length).fill(''),
        ...extra
    });

    saveData();
    renderTable(categoryId);
    input.value = '';
    input.focus();
}

function deleteEntry(categoryId, index) {
    if (!editMode) return;

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
        clearTimeout(autocompleteTimeout);
        const query = this.value.trim();

        if (query.length < 2) {
            list.classList.remove('active');
            list.innerHTML = '';
            return;
        }

        autocompleteTimeout = setTimeout(() => searchTMDB(query, searchType, list, input, categoryId), 300);
    });

    input.addEventListener('blur', () => setTimeout(() => list.classList.remove('active'), 200));
    input.addEventListener('focus', function () {
        if (list.children.length && this.value.length >= 2) list.classList.add('active');
    });
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
            json.results.slice(0, 5).forEach(item => {
                const div = document.createElement('div');
                div.className = 'autocomplete-item';

                if (searchType === 'movie') {
                    const poster = item.poster_path ? `${CONFIG.TMDB_IMAGE_BASE}w92${item.poster_path}` : '';
                    const year = item.release_date?.substring(0, 4) || '';
                    div.innerHTML = `
                        ${poster ? `<img class="autocomplete-poster" src="${poster}">` : '<div class="autocomplete-poster"></div>'}
                        <div class="autocomplete-info">
                            <div class="autocomplete-title">${item.title}</div>
                            <div class="autocomplete-subtitle">${year}</div>
                        </div>
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
                        <div class="autocomplete-info">
                            <div class="autocomplete-title">${item.name}</div>
                            <div class="autocomplete-subtitle">${item.known_for_department || ''}</div>
                        </div>
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
