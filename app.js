// Season Awards Nomination Tracker
// Firebase Realtime Database + LocalStorage Buffer

// ============ FIREBASE CONFIG ============
// 🔥 REPLACEED THIS with your Firebase project config!
// Get it from: Firebase Console → Project Settings → Web App
const firebaseConfig = {
    apiKey: "AIzaSyBZjeKeLz49GVL4DXlu07H2v_jL-FyQjxg",
    authDomain: "seasonawards-8deae.firebaseapp.com",
    databaseURL: "https://seasonawards-8deae-default-rtdb.europe-west1.firebasedatabase.app",
    projectId: "seasonawards-8deae",
    storageBucket: "seasonawards-8deae.firebasestorage.app",
    messagingSenderId: "834709572288",
    appId: "1:834709572288:web:c85814b579483203397b25",
    measurementId: "G-CHL284WZMJ"
};

// Initialize Firebase
let db = null;
let firebaseReady = false;

try {
    firebase.initializeApp(firebaseConfig);
    db = firebase.database();
    firebaseReady = true;
    console.log('🔥 Firebase initialized');
} catch (err) {
    console.warn('⚠️ Firebase not configured, using LocalStorage only');
}

// ============ CONFIGURATION ============
const CONFIG = {
    TMDB_API_KEY: '4399b8147e098e80be332f172d1fe490',
    TMDB_BASE_URL: 'https://api.themoviedb.org/3',
    TMDB_IMAGE_BASE: 'https://image.tmdb.org/t/p/',

    START_YEAR: 2018,

    AWARD_CLASSES: {
        'Academy': 'academy',
        'GG': 'gg',
        'SAG': 'sag',
        'Critics': 'critics',
        'BAFTA': 'bafta',
        'Venice': 'venice'
    },

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
let currentCategoryIndex = 0;
let data = {};
let editMode = false;
let isDragging = false;
let startX = 0;
let prevTranslate = 0;
let isSynced = true;

// Trackpad throttling
let lastWheelTime = 0;
const WHEEL_COOLDOWN = 600;

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
        <nav class="top-nav">
            <div class="nav-container">
                <div class="nav-logo">Season Awards</div>
                <div class="nav-links" id="nav-links"></div>
                <div class="nav-actions">
                    <select class="nav-year-select" id="year-select"></select>
                    <div class="edit-toggle">
                        <span>Edit</span>
                        <div class="toggle-switch" id="edit-toggle"></div>
                    </div>
                    <div class="sync-status synced" id="sync-status">
                        <span class="sync-dot"></span>
                        <span class="sync-text">Synced</span>
                    </div>
                </div>
            </div>
        </nav>
        
        <main class="main-content">
            <div class="page-header">
                <h1 class="page-title">Season Awards Nominations and Winners <span id="year-display"></span></h1>
                <div class="header-controls">
                    <div class="autocomplete-wrapper" id="header-autocomplete-wrapper">
                        <input type="text" class="header-input" id="header-input" placeholder="Add entry..." disabled>
                        <div class="autocomplete-list" id="header-autocomplete"></div>
                    </div>
                    <button class="header-btn" id="header-add-btn" disabled>+ Add</button>
                </div>
            </div>
            <div class="header-divider"></div>
            
            <div class="swipe-container" id="swipe-container">
                <div class="swipe-track" id="swipe-track"></div>
            </div>
            
            <div class="swipe-indicators" id="swipe-indicators"></div>
        </main>
        
        <div class="loading-overlay" id="loading">
            <div class="loading-text">Loading...</div>
        </div>
    `;

    setupNavigation();
    setupYearSelector();
    setupEditToggle();
    createCategoryCards();
    createSwipeIndicators();
    setupSwipeGestures();
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
            goToCategory(i);
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
        currentCategoryIndex = 0;
        loadData();
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

function createCategoryCards() {
    const track = document.getElementById('swipe-track');

    CONFIG.CATEGORIES.forEach((cat) => {
        const card = document.createElement('div');
        card.className = 'category-card';
        card.id = `card-${cat.id}`;

        card.innerHTML = `
            <div class="category-card-inner">
                <h2 class="category-title">${cat.title}</h2>
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
            </div>
        `;

        track.appendChild(card);
    });

    setupHeaderInput();
}

// Header input for adding entries to current category
function setupHeaderInput() {
    const input = document.getElementById('header-input');
    const btn = document.getElementById('header-add-btn');
    const list = document.getElementById('header-autocomplete');

    btn.addEventListener('click', () => {
        const cat = CONFIG.CATEGORIES[currentCategoryIndex];
        addEntry(cat.id, input);
    });

    // Autocomplete for header input
    input.addEventListener('input', function () {
        clearTimeout(autocompleteTimeout);
        const query = this.value.trim();
        const cat = CONFIG.CATEGORIES[currentCategoryIndex];

        if (query.length < 2) {
            list.classList.remove('active');
            list.innerHTML = '';
            lastSearchResults[cat.id] = [];
            return;
        }

        autocompleteTimeout = setTimeout(() => {
            searchTMDBHeader(query, cat.searchType, list, input, cat.id);
        }, 300);
    });

    // Enter key selects first result
    input.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            const cat = CONFIG.CATEGORIES[currentCategoryIndex];
            const results = lastSearchResults[cat.id];
            if (results && results.length > 0) {
                const firstItem = results[0];
                if (cat.searchType === 'movie') {
                    input.value = firstItem.title;
                    addEntry(cat.id, input, { posterPath: firstItem.poster_path, tmdbId: firstItem.id });
                } else {
                    input.value = firstItem.name;
                    addEntry(cat.id, input, { profilePath: firstItem.profile_path, tmdbId: firstItem.id });
                }
                list.classList.remove('active');
            }
        }
    });

    input.addEventListener('blur', () => setTimeout(() => list.classList.remove('active'), 200));
    input.addEventListener('focus', function () {
        if (list.children.length && this.value.length >= 2) list.classList.add('active');
    });
}

// Update header input placeholder based on current category
function updateHeaderInput() {
    const input = document.getElementById('header-input');
    const btn = document.getElementById('header-add-btn');
    const cat = CONFIG.CATEGORIES[currentCategoryIndex];

    input.placeholder = `Add ${cat.placeholder}...`;
    input.disabled = !editMode;
    btn.disabled = !editMode;
    input.dataset.searchType = cat.searchType;
}

// Create swipe indicator dots
function createSwipeIndicators() {
    const indicators = document.getElementById('swipe-indicators');
    if (!indicators) return;

    CONFIG.CATEGORIES.forEach((cat, i) => {
        const dot = document.createElement('div');
        dot.className = `swipe-dot ${i === 0 ? 'active' : ''}`;
        dot.addEventListener('click', () => goToCategory(i));
        indicators.appendChild(dot);
    });
}

// ============ SWIPE GESTURES ============
function setupSwipeGestures() {
    const container = document.getElementById('swipe-container');

    container.addEventListener('touchstart', touchStart, { passive: true });
    container.addEventListener('touchmove', touchMove, { passive: false });
    container.addEventListener('touchend', touchEnd);

    container.addEventListener('mousedown', touchStart);
    container.addEventListener('mousemove', touchMove);
    container.addEventListener('mouseup', touchEnd);
    container.addEventListener('mouseleave', touchEnd);

    container.addEventListener('wheel', (e) => {
        const now = Date.now();
        if (now - lastWheelTime < WHEEL_COOLDOWN) return;

        if (Math.abs(e.deltaX) > Math.abs(e.deltaY) && Math.abs(e.deltaX) > 20) {
            e.preventDefault();
            lastWheelTime = now;

            if (e.deltaX > 0 && currentCategoryIndex < CONFIG.CATEGORIES.length - 1) {
                goToCategory(currentCategoryIndex + 1);
            } else if (e.deltaX < 0 && currentCategoryIndex > 0) {
                goToCategory(currentCategoryIndex - 1);
            }
        }
    }, { passive: false });
}

function touchStart(e) {
    isDragging = true;
    startX = e.type.includes('mouse') ? e.pageX : e.touches[0].clientX;
    document.getElementById('swipe-track').classList.add('dragging');
}

function touchMove(e) {
    if (!isDragging) return;
    const currentX = e.type.includes('mouse') ? e.pageX : e.touches[0].clientX;
    const diff = currentX - startX;
    setTrackPosition(prevTranslate + diff);
}

function touchEnd(e) {
    if (!isDragging) return;
    isDragging = false;
    document.getElementById('swipe-track').classList.remove('dragging');

    let endX = startX;
    if (e.changedTouches && e.changedTouches.length > 0) {
        endX = e.changedTouches[0].clientX;
    } else if (e.clientX) {
        endX = e.clientX;
    }

    const diff = endX - startX;

    if (diff < -80 && currentCategoryIndex < CONFIG.CATEGORIES.length - 1) {
        goToCategory(currentCategoryIndex + 1);
    } else if (diff > 80 && currentCategoryIndex > 0) {
        goToCategory(currentCategoryIndex - 1);
    } else {
        goToCategory(currentCategoryIndex);
    }
}

function setTrackPosition(position) {
    document.getElementById('swipe-track').style.transform = `translateX(${position}px)`;
}

function setPositionByIndex() {
    const cards = document.querySelectorAll('.category-card');
    if (!cards.length) return;

    // Each card takes 100vw total: 90vw width + 5vw margin left + 5vw margin right
    // So we translate by -index * 100vw (which is just viewport width)
    const cardWidth = cards[0].offsetWidth;
    const cardStyle = window.getComputedStyle(cards[0]);
    const marginLeft = parseFloat(cardStyle.marginLeft);
    const marginRight = parseFloat(cardStyle.marginRight);
    const totalCardWidth = cardWidth + marginLeft + marginRight;

    // Center the card: translate so card[index] starts at left margin position
    prevTranslate = -currentCategoryIndex * totalCardWidth;
    setTrackPosition(prevTranslate);

    cards.forEach((c, i) => {
        c.classList.toggle('active', i === currentCategoryIndex);
    });

    updateYearDisplay();
}

function goToCategory(index) {
    currentCategoryIndex = index;
    setPositionByIndex();
    updateNavigation();
    updateHeaderInput();
}

function updateNavigation() {
    document.querySelectorAll('.nav-link').forEach((link, i) => {
        link.classList.toggle('active', i === currentCategoryIndex);
    });
    document.querySelectorAll('.swipe-dot').forEach((dot, i) => {
        dot.classList.toggle('active', i === currentCategoryIndex);
    });
}

function updateYearDisplay() {
    const yearEl = document.getElementById('year-display');
    if (yearEl) {
        yearEl.textContent = currentYear.replace('_', '/');
    }
}

// ============ DATA MANAGEMENT (FIREBASE + LOCALSTORAGE) ============
async function loadData() {
    showLoading(true);
    updateSyncStatus('syncing');

    const lsKey = `seasonAwards_${currentYear}`;
    const lsData = localStorage.getItem(lsKey);
    let localData = lsData ? JSON.parse(lsData) : null;

    // Try Firebase first
    if (firebaseReady && db) {
        try {
            const snapshot = await db.ref(`awards/${currentYear}`).once('value');
            const firebaseData = snapshot.val();

            if (firebaseData) {
                data = firebaseData;
                localStorage.setItem(lsKey, JSON.stringify(data));
                isSynced = true;
                updateSyncStatus('synced');
                console.log('🔥 Loaded from Firebase');
            } else if (localData) {
                // Firebase empty but LocalStorage has data - push to Firebase
                data = localData;
                await db.ref(`awards/${currentYear}`).set(data);
                isSynced = true;
                updateSyncStatus('synced');
                console.log('📤 Pushed LocalStorage to Firebase');
            } else {
                // Both empty - initialize
                data = {};
                CONFIG.CATEGORIES.forEach(cat => data[cat.id] = []);
                isSynced = true;
                updateSyncStatus('synced');
            }
        } catch (err) {
            console.warn('⚠️ Firebase error, using LocalStorage:', err.message);
            data = localData || {};
            CONFIG.CATEGORIES.forEach(cat => { if (!data[cat.id]) data[cat.id] = []; });
            isSynced = false;
            updateSyncStatus('pending');
        }
    } else {
        // No Firebase - use LocalStorage only
        data = localData || {};
        CONFIG.CATEGORIES.forEach(cat => { if (!data[cat.id]) data[cat.id] = []; });
        isSynced = false;
        updateSyncStatus('pending');
    }

    renderAllTables();
    showLoading(false);
    setTimeout(() => setPositionByIndex(), 100);
}

// Save to LocalStorage immediately, then sync to Firebase
async function saveData() {
    const lsKey = `seasonAwards_${currentYear}`;

    // Instant LocalStorage save
    localStorage.setItem(lsKey, JSON.stringify(data));
    updateSyncStatus('saving');

    // Async Firebase save
    if (firebaseReady && db) {
        try {
            await db.ref(`awards/${currentYear}`).set(data);
            isSynced = true;
            updateSyncStatus('synced');
            console.log('🔥 Saved to Firebase');
        } catch (err) {
            console.warn('⚠️ Firebase save failed:', err.message);
            isSynced = false;
            updateSyncStatus('pending');
        }
    } else {
        isSynced = false;
        updateSyncStatus('pending');
    }
}

function updateSyncStatus(status) {
    const el = document.getElementById('sync-status');
    const textEl = el.querySelector('.sync-text');
    el.className = 'sync-status';

    switch (status) {
        case 'syncing':
            el.classList.add('saving');
            textEl.textContent = 'Loading...';
            break;
        case 'saving':
            el.classList.add('saving');
            textEl.textContent = 'Saving...';
            break;
        case 'synced':
            el.classList.add('synced');
            textEl.textContent = 'Synced';
            break;
        case 'pending':
            el.classList.add('pending');
            textEl.textContent = 'Offline';
            break;
        case 'error':
            el.classList.add('error');
            textEl.textContent = 'Error';
            break;
    }
}

function showLoading(show) {
    document.getElementById('loading').classList.toggle('active', show);
}

// ============ TABLE RENDERING ============
function renderAllTables() {
    CONFIG.CATEGORIES.forEach(cat => renderTable(cat.id));
    // Fetch missing images for entries added via Firebase console
    fetchMissingImages();
}

// Fetch TMDB images for entries that don't have them
async function fetchMissingImages() {
    let needsSave = false;

    for (const cat of CONFIG.CATEGORIES) {
        const entries = data[cat.id] || [];

        for (const entry of entries) {
            const needsImage = cat.isPerson
                ? !entry.profilePath
                : !entry.posterPath;

            if (needsImage && entry.name) {
                const searchType = cat.isPerson ? 'person' : 'movie';
                const endpoint = searchType === 'movie' ? '/search/movie' : '/search/person';
                const url = `${CONFIG.TMDB_BASE_URL}${endpoint}?api_key=${CONFIG.TMDB_API_KEY}&query=${encodeURIComponent(entry.name)}`;

                try {
                    const res = await fetch(url);
                    const json = await res.json();

                    if (json.results?.length > 0) {
                        const match = json.results[0];
                        if (cat.isPerson && match.profile_path) {
                            entry.profilePath = match.profile_path;
                            entry.tmdbId = match.id;
                            needsSave = true;
                        } else if (!cat.isPerson && match.poster_path) {
                            entry.posterPath = match.poster_path;
                            entry.tmdbId = match.id;
                            needsSave = true;
                        }
                    }
                } catch (err) {
                    console.warn('Image fetch failed for:', entry.name);
                }
            }
        }
    }

    if (needsSave) {
        saveData();
        // Re-render to show new images
        CONFIG.CATEGORIES.forEach(cat => renderTable(cat.id));
        console.log('✅ Updated missing images from TMDB');
    }
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

    CONFIG.AWARDS.forEach((award, awardIndex) => {
        const cell = document.createElement('td');
        cell.className = 'clickable' + (editMode ? '' : ' locked');

        const value = entry.awards?.[awardIndex] || '';

        if (value === 'X') {
            cell.classList.add('nominee');
        } else if (value === 'Y') {
            cell.classList.add('winner');
            const awardClass = CONFIG.AWARD_CLASSES[award] || 'default-star';
            cell.classList.add(awardClass);
        }

        cell.addEventListener('click', () => {
            if (editMode) toggleCell(categoryId, index, awardIndex, cell, award);
        });

        row.appendChild(cell);
    });

    return row;
}

function toggleCell(categoryId, entryIndex, awardIndex, cell, award) {
    const entry = data[categoryId][entryIndex];
    if (!entry.awards) entry.awards = [];

    const current = entry.awards[awardIndex] || '';
    const next = current === '' ? 'X' : current === 'X' ? 'Y' : '';

    entry.awards[awardIndex] = next;
    saveData();

    cell.classList.remove('winner', 'nominee', 'academy', 'gg', 'sag', 'critics', 'bafta', 'venice', 'default-star');

    if (next === 'X') {
        cell.classList.add('nominee');
    } else if (next === 'Y') {
        cell.classList.add('winner');
        const awardClass = CONFIG.AWARD_CLASSES[award] || 'default-star';
        cell.classList.add(awardClass);
    }
}

// ============ ENTRY MANAGEMENT ============
function addEntry(categoryId, input, extra = {}) {
    if (!editMode) return;
    const name = input.value.trim();
    if (!name) return input.focus();

    if (!data[categoryId]) data[categoryId] = [];

    // Check for duplicate (case-insensitive)
    const exists = data[categoryId].some(entry =>
        entry.name.toLowerCase() === name.toLowerCase()
    );

    if (exists) {
        console.log('Entry already exists:', name);
        input.value = '';
        input.focus();
        return;
    }

    data[categoryId].push({ name, awards: new Array(CONFIG.AWARDS.length).fill(''), ...extra });

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
let lastSearchResults = {}; // Store last results per category

function setupAutocomplete(input, categoryId) {
    const list = document.getElementById(`${categoryId}-autocomplete`);
    const searchType = input.dataset.searchType;

    input.addEventListener('input', function () {
        clearTimeout(autocompleteTimeout);
        const query = this.value.trim();
        if (query.length < 2) { list.classList.remove('active'); list.innerHTML = ''; lastSearchResults[categoryId] = []; return; }
        autocompleteTimeout = setTimeout(() => searchTMDB(query, searchType, list, input, categoryId), 300);
    });

    // Enter key selects first result
    input.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            const results = lastSearchResults[categoryId];
            if (results && results.length > 0) {
                const firstItem = results[0];
                if (searchType === 'movie') {
                    input.value = firstItem.title;
                    addEntry(categoryId, input, { posterPath: firstItem.poster_path, tmdbId: firstItem.id });
                } else {
                    input.value = firstItem.name;
                    addEntry(categoryId, input, { profilePath: firstItem.profile_path, tmdbId: firstItem.id });
                }
                list.classList.remove('active');
            }
        }
    });

    input.addEventListener('blur', () => setTimeout(() => list.classList.remove('active'), 200));
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

        // Store results for Enter key
        lastSearchResults[categoryId] = json.results || [];

        if (json.results?.length) {
            json.results.slice(0, 5).forEach(item => {
                const div = document.createElement('div');
                div.className = 'autocomplete-item';

                if (searchType === 'movie') {
                    const hasPoster = !!item.poster_path;
                    const posterHTML = hasPoster
                        ? `<img class="autocomplete-poster" src="${CONFIG.TMDB_IMAGE_BASE}w92${item.poster_path}">`
                        : `<div class="autocomplete-poster placeholder">🎬</div>`;
                    div.innerHTML = `${posterHTML}<div class="autocomplete-info"><div class="autocomplete-title">${item.title}</div><div class="autocomplete-subtitle">${item.release_date?.substring(0, 4) || ''}</div></div>`;
                    div.addEventListener('mousedown', e => {
                        e.preventDefault();
                        input.value = item.title;
                        list.classList.remove('active');
                        addEntry(categoryId, input, { posterPath: item.poster_path, tmdbId: item.id });
                    });
                } else {
                    const hasPhoto = !!item.profile_path;
                    const photoHTML = hasPhoto
                        ? `<img class="autocomplete-person-photo" src="${CONFIG.TMDB_IMAGE_BASE}w92${item.profile_path}">`
                        : `<div class="autocomplete-person-photo placeholder">👤</div>`;
                    div.innerHTML = `${photoHTML}<div class="autocomplete-info"><div class="autocomplete-title">${item.name}</div><div class="autocomplete-subtitle">${item.known_for_department || ''}</div></div>`;
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
            lastSearchResults[categoryId] = [];
        }
    } catch (err) { console.error('TMDB error:', err); }
}

window.addEventListener('resize', () => { setPositionByIndex(); });

// Alias for header autocomplete
const searchTMDBHeader = searchTMDB;
