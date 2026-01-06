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
        { key: 'astra', label: 'Astra' },
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
    ],

    // Which categories each award covers (for N/A strikethrough)
    // 'all' = covers all categories, otherwise list specific category IDs
    AWARD_CATEGORIES: {
        'oscar': 'all',
        'gg': 'all',
        'bafta': 'all',
        'sag': ['best-film', 'best-actor', 'best-actress'], // No director
        'critics': 'all',
        'lafca': 'all',
        'afi': ['best-film'], // Film only
        'nbr': 'all',
        'dga': ['best-director'], // Director only
        'pga': ['best-film'], // Film only
        'wga': ['best-film'], // Film only (screenplay)
        'adg': ['best-film'],
        'gotham': 'all',
        'astra': 'all',
        'spirit': 'all',
        'bifa': 'all',
        'annie': 'all',
        'nyfcc': 'all',
        'cannes': 'all',
        'venice': 'all'
    }
};

// ============ STATE ============
let currentYear = null;
let currentCategoryIndex = 0;
let data = {};
let editMode = false;
let isDragging = false;
let startX = 0;
let startY = 0;
let isHorizontalSwipe = null; // null = undetermined, true/false once determined
let prevTranslate = 0;
let isSynced = true;
let isHomePage = true; // Home is default page

// Trackpad throttling
let lastWheelTime = 0;
const WHEEL_COOLDOWN = 600;

// ============ CACHE MANAGER ============
const CacheManager = {
    TTL: 1000 * 60 * 60 * 24, // 24 hours
    PREFIX: 'sa_cache_v3_',

    // Generate a simple key from the URL
    getKey(url) {
        // Create a simple hash-like string from the URL to use as a key
        let hash = 0;
        for (let i = 0; i < url.length; i++) {
            const char = url.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32bit integer
        }
        return this.PREFIX + hash;
    },

    async fetch(url) {
        const key = this.getKey(url);
        const cached = localStorage.getItem(key);

        if (cached) {
            try {
                const record = JSON.parse(cached);
                if (Date.now() - record.timestamp < this.TTL) {
                    // console.log('Serving from cache:', url);
                    return record.data;
                } else {
                    localStorage.removeItem(key); // Expired
                }
            } catch (e) {
                localStorage.removeItem(key); // Corrupt
            }
        }

        // Fetch fresh
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        const data = await res.json();

        // Save to cache
        try {
            // Check for storage quotas
            try {
                localStorage.setItem(key, JSON.stringify({
                    timestamp: Date.now(),
                    data: data
                }));
            } catch (e) {
                // If quota exceeded, clear old cache and try again
                this.cleanup(true);
                try {
                    localStorage.setItem(key, JSON.stringify({
                        timestamp: Date.now(),
                        data: data
                    }));
                } catch (retryErr) {
                    console.warn('Cache storage full, skipping cache for this item');
                }
            }
        } catch (e) {
            console.warn('Cache write error', e);
        }

        return data;
    },

    // Clear expired cache items (or all if force is true)
    cleanup(force = false) {
        const now = Date.now();
        let removedCount = 0;

        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith(this.PREFIX)) {
                if (force) {
                    localStorage.removeItem(key);
                    removedCount++;
                    continue;
                }

                try {
                    const record = JSON.parse(localStorage.getItem(key));
                    if (now - record.timestamp > this.TTL) {
                        localStorage.removeItem(key);
                        removedCount++;
                    }
                } catch (e) {
                    localStorage.removeItem(key);
                    removedCount++;
                }
            }
        }
        if (removedCount > 0) console.log(`Cleaned up ${removedCount} cache items`);
    }
};

// Clean cache on startup
setTimeout(() => CacheManager.cleanup(), 5000); // Run cleanup 5s after load

// ============ INITIALIZATION ============
document.addEventListener('DOMContentLoaded', () => {
    calculateCurrentYear();
    buildPage();
    loadData();
    setupFilmOverlay();
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
        /* GSAP removed
        if (hasGSAP) {
            // ... removed ...
        }
        */
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
    isHorizontalSwipe = null; // Reset direction detection
    const pos = e.type.includes('mouse') ? e : e.touches[0];
    startX = pos.clientX;
    startY = pos.clientY;
    document.getElementById('swipe-track').classList.add('dragging');
}

function touchMove(e) {
    if (!isDragging) return;

    const pos = e.type.includes('mouse') ? e : e.touches[0];
    const currentX = pos.clientX;
    const currentY = pos.clientY;
    const diffX = currentX - startX;
    const diffY = currentY - startY;

    // Determine direction on first significant movement (threshold: 10px)
    if (isHorizontalSwipe === null && (Math.abs(diffX) > 10 || Math.abs(diffY) > 10)) {
        // Require 2:1 horizontal ratio to be considered a horizontal swipe
        isHorizontalSwipe = Math.abs(diffX) > Math.abs(diffY) * 2;
    }

    // If determined to be vertical scroll, don't move track
    if (isHorizontalSwipe === false) {
        return;
    }

    // If horizontal swipe, prevent vertical scroll
    if (isHorizontalSwipe === true) {
        e.preventDefault();
    }

    // Show home overlay when swiping right from first card
    if (currentCategoryIndex === 0 && diffX > 0 && !isHomePage) {
        const overlay = document.getElementById('home-overlay');
        const opacity = Math.min(diffX / 400, 1);
        overlay.style.opacity = opacity;
    } else if (!isHomePage) {
        document.getElementById('home-overlay').style.opacity = 0;
    }

    setTrackPosition(prevTranslate + diffX);
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
        const response = await fetch(`${filename}?t=${new Date().getTime()}`);

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
            if (!firebaseReady) {
                el.classList.add('synced'); // Green for local mode
                textEl.textContent = 'Local';
            } else {
                el.classList.add('pending'); // Yellow for actual pending sync
                textEl.textContent = 'Offline';
            }
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
                    const json = await CacheManager.fetch(url);

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

    // Add click listener for film details
    if (categoryId === 'best-film') {
        nameCell.style.cursor = 'pointer';
        nameCell.addEventListener('click', (e) => {
            // Prevent triggering if clicking on other interactive elements
            if (e.target.closest('.winner, .nominee')) return;
            showFilmDetails(entry);
        });
    }

    // Add click listener for person details (actors, actresses, directors)
    if (isPerson) {
        nameCell.style.cursor = 'pointer';
        nameCell.addEventListener('click', (e) => {
            if (e.target.closest('.winner, .nominee')) return;
            showPersonDetails(entry);
        });
    }

    row.appendChild(nameCell);

    CONFIG.AWARDS.forEach((award) => {
        const cell = document.createElement('td');

        // Check if this award covers this category
        const coverage = CONFIG.AWARD_CATEGORIES[award.key];
        const coversCategory = coverage === 'all' || (Array.isArray(coverage) && coverage.includes(categoryId));

        if (!coversCategory) {
            // Award doesn't cover this category - show N/A strikethrough
            cell.className = 'na-cell';
        } else {
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
        }

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


// ============ FILM DETAIL OVERLAY LOGIC ============
function setupFilmOverlay() {
    const overlay = document.getElementById('film-detail-overlay');
    const closeBtn = document.getElementById('film-detail-close');
    const backdrop = document.getElementById('film-detail-backdrop');

    if (closeBtn) closeBtn.addEventListener('click', closeOverlay);
    if (backdrop) backdrop.addEventListener('click', closeOverlay);

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && overlay.classList.contains('active')) {
            closeOverlay();
        }
    });
}

function closeOverlay() {
    const overlay = document.getElementById('film-detail-overlay');
    overlay.classList.remove('active');
    setTimeout(() => {
        document.getElementById('film-detail-content').innerHTML = '';
    }, 300);
}

async function showFilmDetails(entry) {
    const overlay = document.getElementById('film-detail-overlay');
    const content = document.getElementById('film-detail-content');

    overlay.classList.add('active');

    // Show loading state
    content.innerHTML = `
        <div class="fd-loading">
            <div class="fd-spinner"></div>
            <span>Loading details for "${entry.name}"...</span>
        </div>
    `;

    try {
        let tmdbId = entry.tmdbId;

        // If no ID, try to search for it first
        if (!tmdbId) {
            const searchUrl = `${CONFIG.TMDB_BASE_URL}/search/movie?api_key=${CONFIG.TMDB_API_KEY}&query=${encodeURIComponent(entry.name)}`;
            const searchJson = await CacheManager.fetch(searchUrl);
            if (searchJson.results && searchJson.results.length > 0) {
                tmdbId = searchJson.results[0].id;
                // Save it for future use
                entry.tmdbId = tmdbId;
                saveData();
            }
        }

        if (!tmdbId) {
            throw new Error('Movie not found on TMDB');
        }

        // Fetch details with credits
        const detailsUrl = `${CONFIG.TMDB_BASE_URL}/movie/${tmdbId}?api_key=${CONFIG.TMDB_API_KEY}&append_to_response=credits,keywords,release_dates`;
        const movie = await CacheManager.fetch(detailsUrl);

        renderFilmDetails(movie, entry);

    } catch (err) {
        console.error('Error fetching film details:', err);
        content.innerHTML = `
            <div class="fd-loading">
                <span style="color: #ff6b6b;">Failed to load details.</span>
                <span style="font-size: 12px;">${err.message}</span>
                <button onclick="closeOverlay()" class="header-btn" style="margin-top:20px;">Close</button>
            </div>
        `;
    }
}

function renderFilmDetails(movie, entry) {
    const content = document.getElementById('film-detail-content');

    const year = movie.release_date ? movie.release_date.substring(0, 4) : 'N/A';
    const releaseDate = movie.release_date ? new Date(movie.release_date).toLocaleDateString('it-IT', { day: 'numeric', month: 'long', year: 'numeric' }) : 'N/A';
    const runtime = movie.runtime ? `${Math.floor(movie.runtime / 60)}h ${movie.runtime % 60}m` : 'N/A';
    const genres = movie.genres ? movie.genres.map(g => g.name).join(', ') : 'N/A';
    const tagline = movie.tagline ? `<div class="fd-tagline">"${movie.tagline}"</div>` : '';

    // Format currency
    const formatMoney = (num) => {
        if (!num || num === 0) return 'N/A';
        return '$' + num.toLocaleString('en-US');
    };

    const budget = formatMoney(movie.budget);
    const revenue = formatMoney(movie.revenue);

    // Countries and languages
    const countries = movie.production_countries?.map(c => c.name).join(', ') || 'N/A';
    const languages = movie.spoken_languages?.map(l => l.english_name).join(', ') || 'N/A';
    const originalLanguage = movie.original_language?.toUpperCase() || 'N/A';
    const originalTitle = movie.original_title !== movie.title ? movie.original_title : null;

    // Production companies
    const productionCompanies = movie.production_companies?.slice(0, 3).map(c => c.name).join(', ') || 'N/A';

    // Rating
    const rating = movie.vote_average ? movie.vote_average.toFixed(1) : 'N/A';
    const voteCount = movie.vote_count ? movie.vote_count.toLocaleString() : '0';

    // Director(s)
    const directors = movie.credits?.crew?.filter(p => p.job === 'Director').map(d => d.name) || [];
    const directorText = directors.length > 0 ? directors.join(', ') : 'Unknown';

    // Writers
    const writers = movie.credits?.crew?.filter(p => p.job === 'Writer' || p.job === 'Screenplay').slice(0, 3).map(w => w.name) || [];
    const writerText = writers.length > 0 ? writers.join(', ') : null;

    // Cast (top 6)
    const cast = movie.credits?.cast?.slice(0, 6).map(c => `
        <div class="fd-cast-item">
            ${c.profile_path ? `<img src="${CONFIG.TMDB_IMAGE_BASE}w92${c.profile_path}" class="fd-cast-photo" alt="">` : '<div class="fd-cast-photo-placeholder"></div>'}
            <div class="fd-cast-info">
                <span class="fd-cast-name">${c.name}</span>
                <span class="fd-cast-role">${c.character}</span>
            </div>
        </div>
    `).join('') || '';

    // Backdrop
    const backdropUrl = movie.backdrop_path
        ? `${CONFIG.TMDB_IMAGE_BASE}original${movie.backdrop_path}`
        : '';

    const posterUrl = movie.poster_path
        ? `${CONFIG.TMDB_IMAGE_BASE}w500${movie.poster_path}`
        : '';

    const html = `
        <div class="fd-header">
            ${backdropUrl ? `<img src="${backdropUrl}" class="fd-backdrop-img" alt="">` : ''}
        </div>
        
        <div class="fd-layout">
            <div class="fd-poster-side">
                <img src="${posterUrl}" class="fd-poster-full" alt="${movie.title}">
                
                <div class="fd-crew-section">
                    <div class="fd-crew-item">
                        <span class="fd-crew-label">Regia</span>
                        <span class="fd-crew-value">${directorText}</span>
                    </div>
                    ${writerText ? `
                    <div class="fd-crew-item">
                        <span class="fd-crew-label">Sceneggiatura</span>
                        <span class="fd-crew-value">${writerText}</span>
                    </div>` : ''}
                    <div class="fd-crew-item">
                        <span class="fd-crew-label">Produzione</span>
                        <span class="fd-crew-value">${productionCompanies}</span>
                    </div>
                </div>
            </div>
            
            <div class="fd-info-side">
                <h1 class="fd-title">${movie.title}</h1>
                ${originalTitle ? `<div class="fd-original-title">${originalTitle}</div>` : ''}
                
                ${tagline}
                
                <div class="fd-meta-grid">
                    <div class="fd-meta-row"><span class="fd-meta-label">Anno</span><span class="fd-meta-value">${year}</span></div>
                    <div class="fd-meta-row"><span class="fd-meta-label">Durata</span><span class="fd-meta-value">${runtime}</span></div>
                    <div class="fd-meta-row"><span class="fd-meta-label">Genere</span><span class="fd-meta-value">${genres}</span></div>
                    <div class="fd-meta-row"><span class="fd-meta-label">Uscita</span><span class="fd-meta-value">${releaseDate}</span></div>
                    <div class="fd-meta-row"><span class="fd-meta-label">Lingua</span><span class="fd-meta-value">${originalLanguage}</span></div>
                    <div class="fd-meta-row"><span class="fd-meta-label">Paese</span><span class="fd-meta-value">${countries}</span></div>
                    <div class="fd-meta-row"><span class="fd-meta-label">Budget</span><span class="fd-meta-value">${budget}</span></div>
                    <div class="fd-meta-row"><span class="fd-meta-label">Incasso</span><span class="fd-meta-value">${revenue}</span></div>
                </div>
                
                <div class="fd-section">
                    <h3>Trama</h3>
                    <p class="fd-overview">${movie.overview || 'Nessuna trama disponibile.'}</p>
                </div>
                
                ${cast ? `
                <div class="fd-section">
                    <h3>Cast Principale</h3>
                    <div class="fd-cast-grid">
                        ${cast}
                    </div>
                </div>` : ''}
                
                ${renderAwardsSection(entry)}
            </div>
        </div>
    `;

    content.innerHTML = html;
}

// Generate awards HTML section for overlay
function renderAwardsSection(entry) {
    if (!entry || !entry.awards || Object.keys(entry.awards).length === 0) {
        return '';
    }

    const awardItems = CONFIG.AWARDS
        .filter(award => entry.awards[award.key])
        .map(award => {
            const status = entry.awards[award.key];
            const isWinner = status === 'Y';
            const isNominee = status === 'X';

            if (!isWinner && !isNominee) return '';

            return `
                <div class="fd-award-item ${isWinner ? 'winner' : 'nominee'}">
                    <span class="fd-award-name">${award.label}</span>
                    <span class="fd-award-status">${isWinner ? 'VINTO' : 'NOM'}</span>
                </div>
            `;
        })
        .filter(html => html)
        .join('');

    if (!awardItems) return '';

    const yearNum = parseInt(currentYear) || 0;
    const yearDisplay = yearNum ? `${yearNum}/${yearNum + 1}` : '';

    return `
        <div class="fd-awards-section">
            <h3>Premi e Nomination ${yearDisplay}</h3>
            <div class="fd-awards-grid">
                ${awardItems}
            </div>
        </div>
    `;
}

// ============ PERSON DETAIL OVERLAY ============
async function showPersonDetails(entry) {
    const overlay = document.getElementById('film-detail-overlay');
    const content = document.getElementById('film-detail-content');

    overlay.classList.add('active');

    // Show loading state
    content.innerHTML = `
        <div class="fd-loading">
            <div class="loading-text">Caricamento...</div>
        </div>
    `;

    try {
        let personId = entry.tmdbId;

        // If no TMDB ID, search for the person
        if (!personId) {
            const searchUrl = `${CONFIG.TMDB_BASE_URL}/search/person?api_key=${CONFIG.TMDB_API_KEY}&query=${encodeURIComponent(entry.name)}`;
            const searchResPromise = CacheManager.fetch(searchUrl);
            const searchData = await searchResPromise;

            if (searchData.results && searchData.results.length > 0) {
                personId = searchData.results[0].id;
                entry.tmdbId = personId; // Cache for future use
            } else {
                throw new Error('Person not found on TMDB');
            }
        }

        // Fetch person details with combined credits
        const detailsUrl = `${CONFIG.TMDB_BASE_URL}/person/${personId}?api_key=${CONFIG.TMDB_API_KEY}&append_to_response=combined_credits`;
        const data = await CacheManager.fetch(detailsUrl);

        renderPersonDetails(data, entry);

    } catch (err) {
        console.error('Error fetching person details:', err);
        content.innerHTML = `
            <div class="fd-loading">
                <span style="color: #ff6b6b;">Failed to load details.</span>
                <span style="font-size: 12px;">${err.message}</span>
                <button onclick="closeOverlay()" class="header-btn" style="margin-top:20px;">Close</button>
            </div>
        `;
    }
}

function renderPersonDetails(person, entry) {
    const content = document.getElementById('film-detail-content');

    const birthday = person.birthday ? new Date(person.birthday).toLocaleDateString('it-IT', { day: 'numeric', month: 'long', year: 'numeric' }) : 'N/A';
    const birthplace = person.place_of_birth || 'N/A';
    const age = person.birthday ? Math.floor((new Date() - new Date(person.birthday)) / (365.25 * 24 * 60 * 60 * 1000)) : null;
    const ageText = age ? `${age} anni` : '';

    const photoUrl = person.profile_path
        ? `${CONFIG.TMDB_IMAGE_BASE}w500${person.profile_path}`
        : '';

    // Talk shows and similar to exclude
    const excludeTitles = ['saturday night live', 'the tonight show', 'the late show', 'the daily show',
        'late night with', 'the talk', 'the view', 'ellen', 'jimmy kimmel',
        'the graham norton', 'conan', 'good morning', 'today show', 'live with', 'kelly clarkson'];

    // Get notable credits (sorted by popularity, filter out talk shows, max 6)
    const notableCredits = person.combined_credits?.cast
        ?.filter(c => {
            const title = (c.title || c.name || '').toLowerCase();
            // Only movies and TV series (not mini-series episodes or talk shows)
            const isMovie = c.media_type === 'movie' || c.title;
            const isTvSeries = c.media_type === 'tv' && c.episode_count !== 1;
            // Exclude talk shows
            const isTalkShow = excludeTitles.some(t => title.includes(t));
            return (isMovie || isTvSeries) && !isTalkShow && c.poster_path;
        })
        .sort((a, b) => (b.popularity || 0) - (a.popularity || 0))
        .slice(0, 6)
        .map(c => {
            const year = (c.release_date || c.first_air_date)?.substring(0, 4) || '';
            const title = c.title || c.name;
            const posterUrl = `${CONFIG.TMDB_IMAGE_BASE}w185${c.poster_path}`;
            return `
                <div class="fd-credit-card">
                    <img src="${posterUrl}" class="fd-credit-poster" alt="${title}">
                    <div class="fd-credit-overlay">
                        <span class="fd-credit-title">${title}</span>
                        <span class="fd-credit-year">${year}</span>
                    </div>
                </div>`;
        })
        .join('') || '';

    const html = `
        <div class="fd-layout">
            <div class="fd-poster-side">
                ${photoUrl ? `<img src="${photoUrl}" class="fd-poster-full" alt="${person.name}">` : '<div class="fd-photo-placeholder"></div>'}
                
                <div class="fd-crew-section">
                    <div class="fd-crew-item">
                        <span class="fd-crew-label">Nato/a</span>
                        <span class="fd-crew-value">${birthday} ${ageText}</span>
                    </div>
                    <div class="fd-crew-item">
                        <span class="fd-crew-label">Luogo</span>
                        <span class="fd-crew-value">${birthplace}</span>
                    </div>
                    ${person.known_for_department ? `
                    <div class="fd-crew-item">
                        <span class="fd-crew-label">Ruolo</span>
                        <span class="fd-crew-value">${person.known_for_department}</span>
                    </div>` : ''}
                </div>
            </div>
            
            <div class="fd-info-side">
                <h1 class="fd-title">${person.name}</h1>
                
                ${renderAwardsSection(entry)}

                ${notableCredits ? `
                <div class="fd-section">
                    <h3>Filmografia Notevole</h3>
                    <div class="fd-credits-list">
                        ${notableCredits}
                    </div>
                </div>` : ''}
            </div>
        </div>
    `;

    content.innerHTML = html;
}


