// Season Awards Nomination Tracker
// Firebase Realtime Database + LocalStorage Buffer

// ============ FIREBASE CONFIG ============
// Firebase config is loaded from firebase-config.js (excluded from git)
// Create firebase-config.js with your Firebase project config:
// const firebaseConfig = { apiKey: "...", authDomain: "...", ... };

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

    START_YEAR: 2012,

    // Map award keys to CSS classes for styling
    AWARD_CLASSES: {
        'oscar': 'academy',
        'gg': 'gg',
        'sag': 'sag',
        'critics': 'critics',
        'bafta': 'bafta',
        'venice': 'venice'
    },

    // Awards with key (for data) and label (for display)
    AWARDS: [
        { key: 'oscar', label: 'Academy' },
        { key: 'gg', label: 'GG' },
        { key: 'bafta', label: 'BAFTA' },
        { key: 'sag', label: 'SAG' },
        { key: 'critics', label: 'Critics' },
        { key: 'lafca', label: 'LAFCA' },
        { key: 'afi', label: 'AFI' },
        { key: 'nbr', label: 'NBR' },
        { key: 'dga', label: 'DGA' },
        { key: 'pga', label: 'PGA' },
        { key: 'wga', label: 'WGA' },
        { key: 'adg', label: 'ADG' },
        { key: 'gotham', label: 'Gotham' },
        { key: 'hca', label: 'HCA' },
        { key: 'spirit', label: 'Spirit' },
        { key: 'bifa', label: 'BIFA' },
        { key: 'annie', label: 'Annie' },
        { key: 'nyfcc', label: 'NYFCC' },
        { key: 'cannes', label: 'Cannes' },
        { key: 'venice', label: 'Venice' }
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
let isHomePage = true; // Home is default page

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
                    <button class="theme-toggle" id="theme-toggle" title="Toggle Light/Dark Mode">
                        <span class="theme-toggle-text">Light</span>
                    </button>
                    <div class="sync-status synced" id="sync-status">
                        <span class="sync-dot"></span>
                        <span class="sync-text">Synced</span>
                    </div>
                </div>
            </div>
        </nav>
        
        <main class="main-content">
            <div class="category-title-section" id="category-title-section">
                <div class="title-row">
                    <h2 class="category-title" id="current-category-title">Best Film</h2>
                    <h1 class="page-title">Season Awards Nominations and Winners <span id="year-display"></span></h1>
                </div>
                <div class="category-divider"></div>
            </div>
            
            <div class="swipe-container" id="swipe-container">
                <div class="home-overlay" id="home-overlay">
                    <div class="home-content">
                        <h1 class="home-title">Season Awards</h1>
                        <div class="poster-marquee poster-marquee-awards" id="poster-marquee-awards"></div>
                        <div class="poster-marquee poster-marquee-trending" id="poster-marquee-trending"></div>
                    </div>
                </div>
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
    setupThemeToggle(); // Add theme toggle setup
    createCategoryCards();
    createSwipeIndicators();
    setupSwipeGestures();

    // Show home page on load
    showHomeOnLoad();
}

function showHomeOnLoad() {
    const overlay = document.getElementById('home-overlay');
    const titleSection = document.getElementById('category-title-section');
    if (overlay) {
        overlay.style.opacity = 1;
        overlay.classList.add('active');
    }
    if (titleSection) {
        titleSection.style.opacity = 0;
    }
    updateHomeIndicator();
    updateNavigation(); // Deselect nav links on home
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

// Check if GSAP is loaded
const hasGSAP = typeof gsap !== 'undefined';

function setupThemeToggle() {
    const toggleBtn = document.getElementById('theme-toggle');
    const textSpan = toggleBtn.querySelector('.theme-toggle-text');

    // Check local storage
    const savedTheme = localStorage.getItem('theme') || 'dark';
    if (savedTheme === 'light') {
        document.body.classList.add('light-mode');
        textSpan.textContent = 'Dark';
    }

    toggleBtn.addEventListener('click', () => {
        const isLight = document.body.classList.toggle('light-mode');
        const newTheme = isLight ? 'light' : 'dark';

        // Update storage
        localStorage.setItem('theme', newTheme);

        // Update UI
        textSpan.textContent = isLight ? 'Dark' : 'Light';

        // GSAP transition if available
        if (hasGSAP) {
            const duration = 0.5;

            if (isLight) {
                // To Light Mode (White & Gold)
                gsap.to('body', {
                    backgroundColor: '#ffffff',
                    color: '#000000',
                    duration: duration
                });
                gsap.to('.top-nav', {
                    backgroundColor: '#ffffff',
                    duration: duration
                });
                gsap.to('.category-card-inner', {
                    backgroundColor: '#f8f9fa',
                    borderColor: '#d4af37',
                    boxShadow: '0 8px 32px rgba(212, 175, 55, 0.1)',
                    duration: duration
                });
            } else {
                // To Dark Mode (Original Black)
                gsap.to('body', {
                    backgroundColor: '#000000',
                    color: '#f5f5f5',
                    duration: duration
                });
                gsap.to('.top-nav', {
                    backgroundColor: '#000000',
                    duration: duration
                });
                gsap.to('.category-card-inner', {
                    backgroundColor: '#000000',
                    borderColor: 'rgba(255, 255, 255, 0.15)',
                    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)',
                    duration: duration
                });
            }
        }
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
                <div class="table-wrap">
                    <div class="table-scroll">
                        <table>
                            <thead>
                                <tr>
                                    <th>${cat.placeholder}</th>
                                    ${CONFIG.AWARDS.map(a => `<th>${a.label}</th>`).join('')}
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

}

// Header input for adding entries to current category
// Header input functions removed



// Create swipe indicator dots
function createSwipeIndicators() {
    const indicators = document.getElementById('swipe-indicators');
    if (!indicators) return;

    // Add home icon first
    const homeIcon = document.createElement('div');
    homeIcon.className = 'swipe-dot home-icon';
    homeIcon.innerHTML = '';
    homeIcon.addEventListener('click', () => {
        if (!isHomePage) {
            isHomePage = true;
            document.getElementById('home-overlay').style.opacity = 1;
            document.getElementById('home-overlay').classList.add('active');
            updateHomeIndicator();
            updateCategoryTitle();
        }
    });
    indicators.appendChild(homeIcon);

    CONFIG.CATEGORIES.forEach((cat, i) => {
        const dot = document.createElement('div');
        dot.className = `swipe-dot ${i === 0 ? 'active' : ''}`;
        dot.addEventListener('click', () => {
            if (isHomePage) {
                isHomePage = false;
                document.getElementById('home-overlay').style.opacity = 0;
                document.getElementById('home-overlay').classList.remove('active');
                updateCategoryTitle();
            }
            goToCategory(i);
        });
        indicators.appendChild(dot);
    });
}

function updateHomeIndicator() {
    const homeIcon = document.querySelector('.swipe-dot.home-icon');
    if (homeIcon) {
        homeIcon.classList.toggle('active', isHomePage);
    }
    document.querySelectorAll('.swipe-dot:not(.home-icon)').forEach((dot, i) => {
        dot.classList.toggle('active', !isHomePage && i === currentCategoryIndex);
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

    // Show home overlay when swiping right from first card
    if (currentCategoryIndex === 0 && diff > 0 && !isHomePage) {
        const overlay = document.getElementById('home-overlay');
        const opacity = Math.min(diff / 400, 1);
        overlay.style.opacity = opacity;
    } else if (!isHomePage) {
        document.getElementById('home-overlay').style.opacity = 0;
    }

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
    const overlay = document.getElementById('home-overlay');

    // Handle home page transition
    if (currentCategoryIndex === 0 && diff > 250 && !isHomePage) {
        // Swipe right from first card - go to home
        isHomePage = true;
        overlay.style.opacity = 1;
        overlay.classList.add('active');
        updateHomeIndicator();
        updateCategoryTitle();
        updateNavigation(); // Deselect nav links
        return;
    } else if (isHomePage && diff < -80) {
        // Swipe left from home - scatter posters and go to first card
        isHomePage = false;

        // Scatter the posters for visual effect
        scatterPosters();

        // After scatter animation, transition to cards
        setTimeout(() => {
            overlay.style.opacity = 0;
            overlay.classList.remove('active');
            updateHomeIndicator();
            updateCategoryTitle();

            // Position track to the right first, then animate to center
            const track = document.getElementById('swipe-track');
            track.classList.add('dragging');
            setTrackPosition(window.innerWidth);
            requestAnimationFrame(() => {
                track.classList.remove('dragging');
                goToCategory(0);
            });

            // Reset posters after transition
            setTimeout(() => resetPosters(), 500);
        }, 300);
        return;
    } else if (isHomePage) {
        // Stay on home page
        overlay.style.opacity = 1;
        return;
    }

    // Reset overlay if swipe wasn't enough
    overlay.style.opacity = 0;

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
    updateCategoryTitle();
}

function updateNavigation() {
    document.querySelectorAll('.nav-link').forEach((link, i) => {
        // Don't select any link when on home page
        link.classList.toggle('active', !isHomePage && i === currentCategoryIndex);
    });
    // Use updateHomeIndicator for swipe dots (handles home icon separately)
    updateHomeIndicator();
}

function updateCategoryTitle() {
    const titleEl = document.getElementById('current-category-title');
    const titleSection = document.querySelector('.category-title-section');
    if (titleEl && !isHomePage) {
        titleEl.textContent = CONFIG.CATEGORIES[currentCategoryIndex].title;
        titleSection.style.opacity = 1;
    } else if (titleSection && isHomePage) {
        titleSection.style.opacity = 0;
    }
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
    // Initialize home page (from home.js)
    initHomePage();
}

// Load pre-scraped awards data from JSON file for current year
async function loadScrapedData(year = null) {
    const targetYear = year || currentYear;
    const filename = `data/data_${targetYear - 1}_${targetYear}.json`;

    try {
        showLoading(true);
        const response = await fetch(filename);

        if (!response.ok) {
            console.warn(`⚠️ No scraped data for ${targetYear}`);
            showLoading(false);
            return false;
        }

        const scrapedData = await response.json();

        // Merge scraped data into current data
        for (const catId in scrapedData) {
            if (!data[catId]) data[catId] = [];

            // Add entries that don't already exist
            const existingNames = new Set(data[catId].map(e => e.name));
            for (const entry of scrapedData[catId]) {
                if (!existingNames.has(entry.name)) {
                    data[catId].push(entry);
                } else {
                    // Update existing entry with scraped awards
                    const existing = data[catId].find(e => e.name === entry.name);
                    if (existing && entry.awards) {
                        if (!existing.awards) existing.awards = {};
                        Object.assign(existing.awards, entry.awards);
                    }
                }
            }
        }

        await saveData();
        renderAllTables();
        showLoading(false);
        console.log(`📥 Loaded scraped data for ${targetYear - 1}/${targetYear}`);
        return true;
    } catch (err) {
        console.error('❌ Failed to load scraped data:', err);
        showLoading(false);
        return false;
    }
}

// Make loadScrapedData available globally for console use
window.loadScrapedData = loadScrapedData;

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

    // Build film subtitle for persons (actors, directors)
    let filmSubtitle = '';
    if (isPerson && entry.film) {
        filmSubtitle = `<span class="entry-film">${entry.film}</span>`;
    }

    nameCell.innerHTML = `
        <div class="name-cell-content">
            <div class="name-text-wrapper">
                <span class="entry-name">${entry.name}</span>
                ${filmSubtitle}
            </div>
            ${imageHTML}
        </div>
    `;

    // Removed delete button listener logic since editing is removed

    row.appendChild(nameCell);

    CONFIG.AWARDS.forEach((award) => {
        const cell = document.createElement('td');
        cell.className = 'clickable' + (editMode ? '' : ' locked');

        // Use award.key for sparse object access
        const value = entry.awards?.[award.key] || '';

        if (value === 'X') {
            cell.classList.add('nominee');
        } else if (value === 'Y') {
            cell.classList.add('winner');
            const awardClass = CONFIG.AWARD_CLASSES[award.key] || 'default-star';
            cell.classList.add(awardClass);
        }

        cell.addEventListener('click', () => {
            if (editMode) toggleCell(categoryId, index, award.key, cell, award);
        });

        row.appendChild(cell);
    });

    return row;
}

function toggleCell(categoryId, entryIndex, awardKey, cell, award) {
    const entry = data[categoryId][entryIndex];
    if (!entry.awards) entry.awards = {};

    const current = entry.awards[awardKey] || '';
    const next = current === '' ? 'X' : current === 'X' ? 'Y' : '';

    if (next === '') {
        delete entry.awards[awardKey];  // Remove empty keys to keep sparse
    } else {
        entry.awards[awardKey] = next;
    }
    saveData();

    cell.classList.remove('winner', 'nominee', 'academy', 'gg', 'sag', 'critics', 'bafta', 'venice', 'default-star');

    if (next === 'X') {
        cell.classList.add('nominee');
    } else if (next === 'Y') {
        cell.classList.add('winner');
        const awardClass = CONFIG.AWARD_CLASSES[awardKey] || 'default-star';
        cell.classList.add(awardClass);
    }
}

// Edit and Autocomplete functions removed

window.addEventListener('resize', () => { setPositionByIndex(); });

