// Season Awards Nomination Tracker
// Firebase Realtime Database + LocalStorage Buffer

// ============ FIREBASE CONFIG ============
// Firebase config is loaded from firebase-config.js (excluded from git)
// Create firebase-config.js with your Firebase project config:
// const firebaseConfig = { apiKey: "...", authDomain: "...", ... };

// Initialize Firebase
let db = null;
let firebaseReady = false;
let isStatsPageActive = false;
let isPredictionsPageActive = false;

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

    START_YEAR: 2000,

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
                <button class="mobile-menu-toggle" id="mobile-menu-toggle" aria-label="Toggle navigation">
                    <span class="hamburger-icon"></span>
                </button>
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

        <div class="mobile-menu-overlay" id="mobile-menu-overlay"></div>
        
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
    setupMobileMenu();
    setupYearSelector();
    setupThemeToggle(); // Add theme toggle setup
    createCategoryCards();
    createSwipeIndicators();
    setupSwipeGestures();

    // Show home page on load
    showHomeOnLoad();
}

// ============ MOBILE MENU SETUP ============
function setupMobileMenu() {
    const toggleBtn = document.getElementById('mobile-menu-toggle');
    const navLinks = document.getElementById('nav-links');
    const overlay = document.getElementById('mobile-menu-overlay');
    const topNav = document.querySelector('.top-nav');

    if (!toggleBtn || !navLinks) return;

    function toggleMenu() {
        const isExpanded = toggleBtn.getAttribute('aria-expanded') === 'true';
        toggleBtn.setAttribute('aria-expanded', !isExpanded);
        topNav.classList.toggle('mobile-menu-open');
        document.body.style.overflow = !isExpanded ? 'hidden' : '';
    }

    toggleBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleMenu();
    });

    if (overlay) {
        overlay.addEventListener('click', toggleMenu);
    }

    // Close menu when a link is clicked
    navLinks.addEventListener('click', (e) => {
        if (e.target.classList.contains('nav-link')) {
            if (topNav.classList.contains('mobile-menu-open')) {
                toggleMenu();
            }
        }
    });
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
            // Hide stats page if open
            if (isStatsPageActive) {
                hideStatisticsPage();
            }
            if (isPredictionsPageActive) {
                hidePredictionsPage();
            }
            goToCategory(i);
        });

        navLinks.appendChild(link);
    });

    // Add vertical separator
    const separator = document.createElement('span');
    separator.className = 'nav-separator';
    navLinks.appendChild(separator);

    // Add Stats link (not swipeable)
    const statsLink = document.createElement('a');
    statsLink.href = '#';
    statsLink.className = 'nav-link nav-link-special';
    statsLink.textContent = 'Statistics';
    statsLink.addEventListener('click', (e) => {
        e.preventDefault();
        // Force hide main content if it was active
        if (isPredictionsPageActive) hidePredictionsPage();
        // Hide main content (important if we came from home without standard navigation)
        document.querySelector('.main-content').style.display = 'none';
        showStatisticsPage();
    });
    navLinks.appendChild(statsLink);

    // Add Predictions link
    const predictionsLink = document.createElement('a');
    predictionsLink.href = '#';
    predictionsLink.className = 'nav-link nav-link-predictions';
    predictionsLink.textContent = 'Predictions';
    predictionsLink.addEventListener('click', (e) => {
        e.preventDefault();
        if (isStatsPageActive) hideStatisticsPage();
        document.querySelector('.main-content').style.display = 'none';
        showPredictionsPage();
    });
    navLinks.appendChild(predictionsLink);
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

    select.addEventListener('change', async function () {
        currentYear = this.value;
        currentCategoryIndex = 0;
        // Update year display in title
        const yearDisplay = document.getElementById('year-display');
        if (yearDisplay) yearDisplay.textContent = currentYear.replace('_', '/');

        // ALWAYS load data for the new year first
        await loadData();

        // Auto-refresh active page
        if (isPredictionsPageActive) {
            showPredictionsPage();
        } else if (isStatsPageActive) {
            showStatisticsPage();
        }
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
                const seasonYear = parseInt(currentYear.split('_')[0]);

                // For movies, try year, year+1, then no filter (fallback for films like Nomadland)
                const yearsToTry = searchType === 'movie' ? [seasonYear, seasonYear + 1, null] : [null];

                for (const tryYear of yearsToTry) {
                    try {
                        let url = `${CONFIG.TMDB_BASE_URL}${endpoint}?api_key=${CONFIG.TMDB_API_KEY}&query=${encodeURIComponent(entry.name)}`;
                        if (tryYear) {
                            url += `&primary_release_year=${tryYear}`;
                        }

                        const json = await CacheManager.fetch(url);

                        if (json.results?.length > 0) {
                            const match = json.results[0];
                            if (cat.isPerson && match.profile_path) {
                                entry.profilePath = match.profile_path;
                                entry.tmdbId = match.id;
                                needsSave = true;
                                break;
                            } else if (!cat.isPerson && match.poster_path) {
                                entry.posterPath = match.poster_path;
                                entry.tmdbId = match.id;
                                needsSave = true;
                                break;
                            }
                        }
                    } catch (err) {
                        console.warn('Image fetch failed for:', entry.name);
                    }
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

// Reset movie posters for current year to force re-fetch with correct year
async function resetMoviePosters() {
    console.log('🔄 Resetting movie posters for', currentYear);

    const filmEntries = data['best-film'] || [];
    for (const entry of filmEntries) {
        // Clear existing tmdbId and posterPath to force re-fetch
        delete entry.tmdbId;
        delete entry.posterPath;
    }

    await saveData();
    console.log('✅ Cleared', filmEntries.length, 'movie IDs. Re-fetching...');

    // Re-fetch with year filter
    await fetchMissingImages();
    renderAllTables();
    console.log('✅ Done! Refresh to see changes.');
}

// Reset movie posters for ALL years
async function resetAllMoviePosters() {
    if (!firebaseReady || !db) {
        console.error('❌ Firebase not ready');
        return;
    }

    console.log('🔄 Resetting movie posters for ALL years...');

    const snapshot = await db.ref('awards').once('value');
    const allData = snapshot.val();

    if (!allData) {
        console.log('No data found');
        return;
    }

    let totalCleared = 0;

    for (const yearKey in allData) {
        const yearData = allData[yearKey];
        if (yearData['best-film']) {
            for (const entry of yearData['best-film']) {
                if (entry.tmdbId || entry.posterPath) {
                    delete entry.tmdbId;
                    delete entry.posterPath;
                    totalCleared++;
                }
            }

            // Save back to Firebase
            await db.ref(`awards/${yearKey}/best-film`).set(yearData['best-film']);
            console.log(`  ✓ ${yearKey}: cleared ${yearData['best-film'].length} films`);
        }
    }

    console.log(`✅ Cleared ${totalCleared} movie IDs across all years.`);
    console.log('🔄 Reloading current year data...');

    // Reload current year
    await loadData();
    console.log('✅ Done! Posters will be re-fetched with correct year filter.');
}

// Make available globally
window.resetMoviePosters = resetMoviePosters;
window.resetAllMoviePosters = resetAllMoviePosters;

// Fetch missing images for ALL years and save to Firebase
async function fetchAllYearsImages() {
    if (!firebaseReady || !db) {
        console.error('❌ Firebase not ready');
        return;
    }

    console.log('🔄 Fetching missing images for ALL years...');

    const snapshot = await db.ref('awards').once('value');
    const allData = snapshot.val();

    if (!allData) {
        console.log('No data found');
        return;
    }

    let totalUpdated = 0;

    for (const yearKey in allData) {
        const yearData = allData[yearKey];
        const seasonYear = parseInt(yearKey.split('_')[0]);
        let yearUpdated = 0;

        // Process all categories
        for (const catId of ['best-film', 'best-actor', 'best-actress', 'best-director']) {
            if (!yearData[catId]) continue;

            const isPerson = catId !== 'best-film';
            const entries = yearData[catId];

            for (const entry of entries) {
                const needsImage = isPerson ? !entry.profilePath : !entry.posterPath;

                if (needsImage && entry.name) {
                    const searchType = isPerson ? 'person' : 'movie';
                    const endpoint = searchType === 'movie' ? '/search/movie' : '/search/person';

                    let url = `${CONFIG.TMDB_BASE_URL}${endpoint}?api_key=${CONFIG.TMDB_API_KEY}&query=${encodeURIComponent(entry.name)}`;
                    if (searchType === 'movie') {
                        url += `&primary_release_year=${seasonYear}`;
                    }

                    try {
                        const response = await fetch(url);
                        const json = await response.json();

                        if (json.results?.length > 0) {
                            const match = json.results[0];
                            if (isPerson && match.profile_path) {
                                entry.profilePath = match.profile_path;
                                entry.tmdbId = match.id;
                                yearUpdated++;
                            } else if (!isPerson && match.poster_path) {
                                entry.posterPath = match.poster_path;
                                entry.tmdbId = match.id;
                                yearUpdated++;
                            }
                        }

                        // Small delay to avoid rate limiting
                        await new Promise(r => setTimeout(r, 100));
                    } catch (err) {
                        console.warn(`  Failed: ${entry.name}`);
                    }
                }
            }

            // Save category back to Firebase
            if (yearUpdated > 0) {
                await db.ref(`awards/${yearKey}/${catId}`).set(entries);
            }
        }

        if (yearUpdated > 0) {
            console.log(`  ✓ ${yearKey}: updated ${yearUpdated} images`);
            totalUpdated += yearUpdated;
        }
    }

    console.log(`✅ Done! Updated ${totalUpdated} images total.`);
    await loadData();
}

window.fetchAllYearsImages = fetchAllYearsImages;

function renderTable(categoryId) {
    const tbody = document.getElementById(`${categoryId}-tbody`);
    if (!tbody) return;
    tbody.innerHTML = '';

    const cat = CONFIG.CATEGORIES.find(c => c.id === categoryId);
    let entries = data[categoryId] || [];

    // Sort entries:
    // 1. Wins (DESC)
    // 2. Nominations (DESC) (Tie-breaker)
    entries.sort((a, b) => {
        const getStats = (entry) => {
            let wins = 0;
            let noms = 0;
            if (entry.awards) {
                Object.values(entry.awards).forEach(val => {
                    if (val === 'Y') wins++;
                    if (val === 'X') noms++;
                });
            }
            return { wins, noms };
        };

        const statsA = getStats(a);
        const statsB = getStats(b);

        if (statsB.wins !== statsA.wins) {
            return statsB.wins - statsA.wins;
        }
        return statsB.noms - statsA.noms;
    });

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

    // Build film subtitle for persons (actors, directors) with role after film
    let filmSubtitle = '';
    if (isPerson && entry.film) {
        const roleText = entry.role ? ` <span class="entry-meta">${entry.role}</span>` : '';
        filmSubtitle = `<span class="entry-film-line">${entry.film}${roleText}</span>`;
    }

    // Generate mobile badges (winners AND nominees)
    let mobileBadges = '';
    const relevantAwards = CONFIG.AWARDS.filter(award => {
        const val = entry.awards?.[award.key];
        return val === 'Y' || val === 'X';
    });

    if (relevantAwards.length > 0) {
        const badgesHtml = relevantAwards.map(a => {
            const val = entry.awards[a.key];
            const typeClass = val === 'Y' ? 'winner' : 'nominee';
            return `<span class="mobile-badge ${typeClass}">${a.label}</span>`;
        }).join('');
        mobileBadges = `<div class="mobile-badges">${badgesHtml}</div>`;
    }

    // Mobile Poster Injection
    const mobilePosterUrl = isPerson && entry.profilePath
        ? `${CONFIG.TMDB_IMAGE_BASE}w185${entry.profilePath}`
        : (!isPerson && entry.posterPath ? `${CONFIG.TMDB_IMAGE_BASE}w185${entry.posterPath}` : '');

    const mobilePosterHtml = mobilePosterUrl
        ? `<div class="mobile-poster-wrapper"><img src="${mobilePosterUrl}" class="mobile-poster-img" loading="lazy"></div>`
        : `<div class="mobile-poster-wrapper" style="background:#222;"></div>`;

    nameCell.innerHTML = `
        <div class="name-cell-content">
            ${mobilePosterHtml} 
            <div class="name-text-wrapper">
                <span class="entry-name">${entry.name}</span>
                ${filmSubtitle}
                ${mobileBadges}
            </div>
            ${imageHTML}
        </div>
    `;

    // Removed delete button listener logic since editing is removed

    // Add click listener for film details
    if (categoryId === 'best-film') {
        nameCell.style.cursor = 'pointer';
        nameCell.addEventListener('click', (e) => {
            // Prevent triggering if clicking on other interactive elements or if scrolling
            if (e.target.closest('.winner, .nominee') || !isClickAllowed()) return;
            showFilmDetails(entry);
        });
    }

    // Add click listener for person details (actors, actresses, directors)
    if (isPerson) {
        nameCell.style.cursor = 'pointer';
        nameCell.addEventListener('click', (e) => {
            if (e.target.closest('.winner, .nominee') || !isClickAllowed()) return;
            showPersonDetails(entry);
        });
    }

    row.appendChild(nameCell);

    CONFIG.AWARDS.forEach((award) => {
        const cell = document.createElement('td');

        // Check if this award covers this category
        let coverage = CONFIG.AWARD_CATEGORIES[award.key];
        let coversCategory = coverage === 'all' || (Array.isArray(coverage) && coverage.includes(categoryId));

        // Astra didn't exist before 2017 (Season 2017/2018)
        if (award.key === 'astra' && parseInt(currentYear) < 2017) {
            coversCategory = false;
        }

        // Gotham: No Best Actor/Actress/Director before 2013 (Season 2013/2014)
        // User requested "bars" (N/A) for these years
        if (award.key === 'gotham' && parseInt(currentYear) < 2013 && ['best-actor', 'best-actress', 'best-director'].includes(categoryId)) {
            coversCategory = false;
        }

        // Gotham: No Best Feature before 2004 (Season 2004/2005) - specifically 2004 ceremony
        // System year 2004 (2003/04) no film. System year 2005 (2004/05) yes film.
        // So start year < 2004.
        if (award.key === 'gotham' && parseInt(currentYear) < 2004 && categoryId === 'best-film') {
            coversCategory = false;
        }

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
            // Add year filter to get correct movie version
            const seasonYear = parseInt(currentYear.split('_')[0]);
            const searchUrl = `${CONFIG.TMDB_BASE_URL}/search/movie?api_key=${CONFIG.TMDB_API_KEY}&query=${encodeURIComponent(entry.name)}&primary_release_year=${seasonYear}`;
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
                        <span class="fd-crew-label">Director</span>
                        <span class="fd-crew-value">${directorText}</span>
                    </div>
                    ${writerText ? `
                    <div class="fd-crew-item">
                        <span class="fd-crew-label">Screenplay</span>
                        <span class="fd-crew-value">${writerText}</span>
                    </div>` : ''}
                    <div class="fd-crew-item">
                        <span class="fd-crew-label">Production</span>
                        <span class="fd-crew-value">${productionCompanies}</span>
                    </div>
                </div>
            </div>
            
            <div class="fd-info-side">
                <h1 class="fd-title">${movie.title}</h1>
                ${originalTitle ? `<div class="fd-original-title">${originalTitle}</div>` : ''}
                
                ${tagline}
                
                <div class="fd-meta-grid">
                    <div class="fd-meta-row"><span class="fd-meta-label">Year</span><span class="fd-meta-value">${year}</span></div>
                    <div class="fd-meta-row"><span class="fd-meta-label">Runtime</span><span class="fd-meta-value">${runtime}</span></div>
                    <div class="fd-meta-row"><span class="fd-meta-label">Genre</span><span class="fd-meta-value">${genres}</span></div>
                    <div class="fd-meta-row"><span class="fd-meta-label">Release</span><span class="fd-meta-value">${releaseDate}</span></div>
                    <div class="fd-meta-row"><span class="fd-meta-label">Language</span><span class="fd-meta-value">${originalLanguage}</span></div>
                    <div class="fd-meta-row"><span class="fd-meta-label">Country</span><span class="fd-meta-value">${countries}</span></div>
                    <div class="fd-meta-row"><span class="fd-meta-label">Budget</span><span class="fd-meta-value">${budget}</span></div>
                    <div class="fd-meta-row"><span class="fd-meta-label">Revenue</span><span class="fd-meta-value">${revenue}</span></div>
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
                <div class="fd-award-item ${isWinner ? 'winner' : 'nominee'}" title="${isWinner ? 'Winner' : 'Nominee'}">
                    <span class="fd-award-name">${award.label}</span>
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
            <h3>Awards & Nominations ${yearDisplay}</h3>
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
            <div class="loading-text">Loading...</div>
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

    // Get notable credits - ONLY MOVIES, sorted by year (newest first), max 8
    const notableCredits = person.combined_credits?.cast
        ?.filter(c => {
            // ONLY movies (no TV shows like MasterChef, The Voice, Drag Race, etc.)
            const isMovie = c.media_type === 'movie' || (c.title && !c.name);
            return isMovie && c.poster_path;
        })
        .sort((a, b) => {
            // Sort by year descending (newest first)
            const yearA = parseInt((a.release_date || '0000').substring(0, 4));
            const yearB = parseInt((b.release_date || '0000').substring(0, 4));
            return yearB - yearA;
        })
        .slice(0, 8)
        .map(c => {
            const year = c.release_date?.substring(0, 4) || '';
            const title = c.title || c.name;
            const posterUrl = `${CONFIG.TMDB_IMAGE_BASE}w154${c.poster_path}`;
            return `
                <div class="fd-credit-card">
                    <img src="${posterUrl}" class="fd-credit-poster" alt="${title}">
                    <div class="fd-credit-overlay">
                        <span class="fd-credit-title">${title}${year ? ` (${year})` : ''}</span>
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
                        <span class="fd-crew-label">Born</span>
                        <span class="fd-crew-value">${birthday} ${ageText}</span>
                    </div>
                    <div class="fd-crew-item">
                        <span class="fd-crew-label">Place</span>
                        <span class="fd-crew-value">${birthplace}</span>
                    </div>
                    ${person.known_for_department ? `
                    <div class="fd-crew-item">
                        <span class="fd-crew-label">Role</span>
                        <span class="fd-crew-value">${person.known_for_department}</span>
                    </div>` : ''}
                </div>
            </div>
            
            <div class="fd-info-side">
                <h1 class="fd-title">${person.name}</h1>
                
                ${renderAwardsSection(entry)}

                ${notableCredits ? `
                <div class="fd-section">
                    <h3>Notable Filmography</h3>
                    <div class="fd-credits-list">
                        ${notableCredits}
                    </div>
                </div>` : ''}
            </div>
        </div>
    `;

    content.innerHTML = html;
}

// ============ STATISTICS PAGE ============

async function showStatisticsPage() {
    isStatsPageActive = true;

    // Hide main content, show stats container
    const mainContent = document.querySelector('.main-content');
    const swipeIndicators = document.getElementById('swipe-indicators');

    // Create stats container if it doesn't exist
    let statsContainer = document.getElementById('stats-container');
    if (!statsContainer) {
        statsContainer = document.createElement('div');
        statsContainer.id = 'stats-container';
        statsContainer.className = 'stats-container';
        mainContent.parentNode.insertBefore(statsContainer, mainContent.nextSibling);
    }

    // Hide other content
    mainContent.style.display = 'none';
    swipeIndicators.style.display = 'none';
    statsContainer.style.display = 'block';

    // Show loading
    statsContainer.innerHTML = `
        <div class="spinner-overlay">
            <div class="spinner"></div>
        </div>
    `;

    // Deselect nav links, highlight stats
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    document.querySelector('.nav-link-special')?.classList.add('active');

    try {
        const allYearsData = await loadAllYearsData();
        const stats = aggregateStatistics(allYearsData);
        renderStatisticsPage(stats, statsContainer);
    } catch (err) {
        console.error('Error loading statistics:', err);
        statsContainer.innerHTML = `
            <div class="stats-loading">
                <span style="color: #ff6b6b;">Errore nel caricamento delle statistiche.</span>
                <button onclick="hideStatisticsPage()" class="stats-back-btn">Torna Indietro</button>
            </div>
        `;
    }
}

function hideStatisticsPage() {
    isStatsPageActive = false;

    const mainContent = document.querySelector('.main-content');
    const swipeIndicators = document.getElementById('swipe-indicators');
    const statsContainer = document.getElementById('stats-container');

    if (statsContainer) {
        statsContainer.style.display = 'none';
    }
    mainContent.style.display = 'flex';
    swipeIndicators.style.display = 'flex';

    // Restore nav state
    updateNavigation();

    // Deselect stats link
    document.querySelector('.nav-link-special')?.classList.remove('active');
}

async function loadAllYearsData() {
    const allData = {};
    const now = new Date();
    const endYear = now.getMonth() < 8 ? now.getFullYear() : now.getFullYear() + 1;

    if (firebaseReady && db) {
        // Load all years from Firebase
        const snapshot = await db.ref('awards').once('value');
        const firebaseData = snapshot.val();

        if (firebaseData) {
            for (const yearKey in firebaseData) {
                allData[yearKey] = firebaseData[yearKey];
            }
        }
    } else {
        // Fallback: load from localStorage
        for (let year = CONFIG.START_YEAR; year < endYear; year++) {
            const lsKey = `seasonAwards_${year}_${year + 1}`;
            const lsData = localStorage.getItem(lsKey);
            if (lsData) {
                allData[`${year}_${year + 1}`] = JSON.parse(lsData);
            }
        }
    }

    return allData;
}

function aggregateStatistics(allYearsData) {
    const filmStats = {};      // { filmName: { nominations: 0, wins: 0, years: [] } }
    const actorStats = {};     // { personName: { nominations: 0, wins: 0, years: [] } }
    const actressStats = {};
    const directorStats = {};

    for (const yearKey in allYearsData) {
        const yearData = allYearsData[yearKey];
        const displayYear = yearKey.replace('_', '/');

        // Process best-film
        if (yearData['best-film']) {
            for (const entry of yearData['best-film']) {
                if (!filmStats[entry.name]) {
                    filmStats[entry.name] = {
                        nominations: 0,
                        wins: 0,
                        years: [],
                        posterPath: entry.posterPath,
                        genre: entry.genre
                    };
                }
                // Update posterPath if missing and current has it
                if (!filmStats[entry.name].posterPath && entry.posterPath) {
                    filmStats[entry.name].posterPath = entry.posterPath;
                }
                // Update genre if missing
                if (!filmStats[entry.name].genre && entry.genre) {
                    filmStats[entry.name].genre = entry.genre;
                }
                const awards = entry.awards || {};
                for (const awardKey in awards) {
                    if (awards[awardKey] === 'X') {
                        filmStats[entry.name].nominations++;
                    } else if (awards[awardKey] === 'Y') {
                        filmStats[entry.name].wins++;
                        filmStats[entry.name].nominations++;
                    }
                }
                if (!filmStats[entry.name].years.includes(displayYear)) {
                    filmStats[entry.name].years.push(displayYear);
                }
            }
        }

        // Process best-actor
        if (yearData['best-actor']) {
            for (const entry of yearData['best-actor']) {
                if (!actorStats[entry.name]) {
                    actorStats[entry.name] = {
                        nominations: 0,
                        wins: 0,
                        years: [],
                        profilePath: entry.profilePath,
                        role: entry.role
                    };
                }
                // Update profilePath if missing
                if (!actorStats[entry.name].profilePath && entry.profilePath) {
                    actorStats[entry.name].profilePath = entry.profilePath;
                }
                // Update role if missing
                if (!actorStats[entry.name].role && entry.role) {
                    actorStats[entry.name].role = entry.role;
                }
                const awards = entry.awards || {};
                for (const awardKey in awards) {
                    if (awards[awardKey] === 'X') {
                        actorStats[entry.name].nominations++;
                    } else if (awards[awardKey] === 'Y') {
                        actorStats[entry.name].wins++;
                        actorStats[entry.name].nominations++;
                    }
                }
                if (!actorStats[entry.name].years.includes(displayYear)) {
                    actorStats[entry.name].years.push(displayYear);
                }
            }
        }

        // Process best-actress
        if (yearData['best-actress']) {
            for (const entry of yearData['best-actress']) {
                if (!actressStats[entry.name]) {
                    actressStats[entry.name] = { nominations: 0, wins: 0, years: [], profilePath: entry.profilePath };
                }
                if (!actressStats[entry.name].profilePath && entry.profilePath) {
                    actressStats[entry.name].profilePath = entry.profilePath;
                }
                const awards = entry.awards || {};
                for (const awardKey in awards) {
                    if (awards[awardKey] === 'X') {
                        actressStats[entry.name].nominations++;
                    } else if (awards[awardKey] === 'Y') {
                        actressStats[entry.name].wins++;
                        actressStats[entry.name].nominations++;
                    }
                }
                if (!actressStats[entry.name].years.includes(displayYear)) {
                    actressStats[entry.name].years.push(displayYear);
                }
            }
        }

        // Process best-director
        if (yearData['best-director']) {
            for (const entry of yearData['best-director']) {
                if (!directorStats[entry.name]) {
                    directorStats[entry.name] = { nominations: 0, wins: 0, years: [], profilePath: entry.profilePath };
                }
                if (!directorStats[entry.name].profilePath && entry.profilePath) {
                    directorStats[entry.name].profilePath = entry.profilePath;
                }
                const awards = entry.awards || {};
                for (const awardKey in awards) {
                    if (awards[awardKey] === 'X') {
                        directorStats[entry.name].nominations++;
                    } else if (awards[awardKey] === 'Y') {
                        directorStats[entry.name].wins++;
                        directorStats[entry.name].nominations++;
                    }
                }
                if (!directorStats[entry.name].years.includes(displayYear)) {
                    directorStats[entry.name].years.push(displayYear);
                }
            }
        }
    }

    // Sort by nominations (descending)
    const sortByNominations = (a, b) => b[1].nominations - a[1].nominations;
    const sortByWins = (a, b) => b[1].wins - a[1].wins;

    return {
        topFilmsByNominations: Object.entries(filmStats).sort(sortByNominations).slice(0, 10),
        topFilmsByWins: Object.entries(filmStats).sort(sortByWins).slice(0, 10),
        topActorsByNominations: Object.entries(actorStats).sort(sortByNominations).slice(0, 10),
        topActorsByWins: Object.entries(actorStats).sort(sortByWins).slice(0, 10),
        topActressesByNominations: Object.entries(actressStats).sort(sortByNominations).slice(0, 10),
        topActressesByWins: Object.entries(actressStats).sort(sortByWins).slice(0, 10),
        topDirectorsByNominations: Object.entries(directorStats).sort(sortByNominations).slice(0, 10),
        topDirectorsByWins: Object.entries(directorStats).sort(sortByWins).slice(0, 10),
    };
}

function renderStatisticsPage(stats, container) {
    const renderStatsSection = (title, items, isPerson = false, showWins = false, layoutIndex = 0) => {
        // Top 8 for visual grid (2 rows of 4)
        const topVisuals = items.slice(0, 8);
        // Top 10 for list
        const topList = items.slice(0, 10);

        const countLabel = showWins ? 'wins' : 'nominations';
        const isReversed = layoutIndex % 2 !== 0;

        const renderVisualItem = (name, data, index) => {
            const imageUrl = isPerson && data.profilePath
                ? `${CONFIG.TMDB_IMAGE_BASE}w342${data.profilePath}`
                : (!isPerson && data.posterPath ? `${CONFIG.TMDB_IMAGE_BASE}w342${data.posterPath}` : '');

            // If no image, show a placeholder instead of nothing
            const imageHtml = imageUrl
                ? `<img src="${imageUrl}" class="stats-visual-img" loading="lazy">`
                : `<div class="stats-visual-img stats-visual-placeholder"></div>`;

            return `
                <div class="stats-visual-item full-poster">
                    ${imageHtml}
                    <div class="stats-visual-overlay">
                        <span class="stats-visual-rank">#${index + 1}</span>
                        <div class="stats-visual-info">
                            <span class="stats-visual-name">${name}</span>
                            <span class="stats-visual-count">${showWins ? data.wins : data.nominations}</span>
                        </div>
                    </div>
                </div>
            `;
        };

        const renderListItem = (name, data, index) => {
            const count = showWins ? data.wins : data.nominations;
            const isFirst = index === 0 ? 'is-first' : '';
            // For list items, we might want a simpler look now
            return `
                <div class="stats-list-row ${isFirst}">
                    <span class="stats-list-rank">${index + 1}</span>
                    <div style="flex: 1; margin: 0 12px;">
                        <span class="stats-list-name" style="padding: 0;">${name}</span>
                        ${data.role ? `<span class="stats-meta">${data.role}</span>` : ''}
                        ${data.genre ? `<span class="stats-meta">${data.genre}</span>` : ''}
                    </div>
                    <span class="stats-list-count">${count}</span>
                </div>
             `;
        };

        return `
            <div class="stats-section-wide">
                <h2 class="stats-section-title">${title}</h2>
                <div class="stats-split-layout ${isReversed ? 'layout-reverse' : ''}">
                    <div class="stats-list-side">
                        ${topList.map(([name, data], idx) => renderListItem(name, data, idx)).join('')}
                    </div>
                    <div class="stats-visual-side">
                        <div class="stats-visual-grid">
                            ${topVisuals.map(([name, data], idx) => renderVisualItem(name, data, idx)).join('')}
                        </div>
                    </div>
                </div>
            </div>
        `;
    };

    const html = `
        <div class="stats-header">
            <h1 class="stats-title">All-Time Statistics</h1>
            <p class="stats-subtitle">Aggregated nominations and wins from all seasons</p>
        </div>
        
        <div class="stats-content-wrapper">
            ${renderStatsSection('Films with Most Nominations', stats.topFilmsByNominations, false, false, 0)}
            ${renderStatsSection('Films with Most Wins', stats.topFilmsByWins, false, true, 1)}
            
            ${renderStatsSection('Actors with Most Nominations', stats.topActorsByNominations, true, false, 2)}
            ${renderStatsSection('Actors with Most Wins', stats.topActorsByWins, true, true, 3)}
            
            ${renderStatsSection('Actresses with Most Nominations', stats.topActressesByNominations, true, false, 4)}
            ${renderStatsSection('Actresses with Most Wins', stats.topActressesByWins, true, true, 5)}
            
            ${renderStatsSection('Directors with Most Nominations', stats.topDirectorsByNominations, true, false, 6)}
            ${renderStatsSection('Directors with Most Wins', stats.topDirectorsByWins, true, true, 7)}
        </div>
        
        </div>
    `;

    container.innerHTML = html;
}

// ============ PREDICTIONS PAGE ============

// Award weights for Oscar prediction (higher = more predictive)
const PREDICTION_WEIGHTS = {
    sag: 20,       // SAG actors vote at Oscars
    bafta: 18,     // Overlapping international voters
    dga: 18,       // Directors category
    pga: 16,       // Producers overlap
    critics: 15,   // Critical acclaim indicator
    gg: 12,        // Visibility but less predictive
    lafca: 10,     // LA Film Critics
    nyfcc: 10,     // NY Film Critics
    nbr: 8,        // Early indicator
    gotham: 6,     // Indie focus
    spirit: 6,     // Indie focus
    astra: 5,      // Industry buzz
    afi: 3,        // Honorific
    venice: 3,     // Festival
    cannes: 3,     // Festival
    bifa: 2,       // UK indie
    annie: 2,      // Animation only
    adg: 2         // Art Directors Guild
};

async function showPredictionsPage() {
    isPredictionsPageActive = true;

    const mainContent = document.querySelector('.main-content');
    const swipeIndicators = document.getElementById('swipe-indicators');

    // Create predictions container if it doesn't exist
    let predictionsContainer = document.getElementById('predictions-container');
    if (!predictionsContainer) {
        predictionsContainer = document.createElement('div');
        predictionsContainer.id = 'predictions-container';
        predictionsContainer.className = 'predictions-container';
        mainContent.parentNode.insertBefore(predictionsContainer, mainContent.nextSibling);
    }

    // Hide other content
    mainContent.style.display = 'none';
    swipeIndicators.style.display = 'none';
    predictionsContainer.style.display = 'block';

    // Show loading
    predictionsContainer.innerHTML = `
        <div class="spinner-overlay">
            <div class="spinner"></div>
        </div>
    `;

    // Deselect nav links, highlight predictions
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    document.querySelector('.nav-link-predictions')?.classList.add('active');

    try {
        // Load historical data first for dynamic weighting
        const allYearsData = await loadAllYearsData();
        const historyAnalysis = analyzeHistoricalPrecursors(allYearsData);

        // Calculate predictions using dynamic weights
        const predictions = calculateOscarPredictions(data, historyAnalysis);

        // Render page
        renderPredictionsPage(predictions, predictionsContainer);

        // Pass analysis data to the chart renderer so it doesn't need to reload
        // (We'll modify renderPredictionsPage slightly or just use the global function if tailored)
        setTimeout(() => {
            renderPrecursorAnalysis(historyAnalysis, document.getElementById('precursor-analysis-container'));
        }, 100);

    } catch (err) {
        console.error('Error calculating predictions:', err);
        predictionsContainer.innerHTML = `
            <div class="stats-loading">
                <span style="color: #ff6b6b;">Error calculating predictions.</span>
            </div>
        `;
    }
}

function hidePredictionsPage() {
    isPredictionsPageActive = false;

    const mainContent = document.querySelector('.main-content');
    const swipeIndicators = document.getElementById('swipe-indicators');
    const predictionsContainer = document.getElementById('predictions-container');

    if (predictionsContainer) {
        predictionsContainer.style.display = 'none';
    }
    mainContent.style.display = 'flex';
    swipeIndicators.style.display = 'flex';

    // Restore nav state
    updateNavigation();

    // Deselect predictions link
    document.querySelector('.nav-link-predictions')?.classList.remove('active');
}

function calculateOscarPredictions(yearData, historyAnalysis) {
    const categories = ['best-film', 'best-director', 'best-actor', 'best-actress'];
    const predictions = {};

    // Build dynamic weights from history if available
    const dynamicWeights = { ...PREDICTION_WEIGHTS };
    if (historyAnalysis && historyAnalysis.overall) {
        historyAnalysis.overall.forEach(item => {
            // Use historical win percentage as weight (e.g. 80% -> weight 80)
            // Only update if we have meaningful data (at least 5 years of history to be reliable?)
            // For now, trusting the percentage directly.
            if (item.percentage > 0) {
                dynamicWeights[item.key] = item.percentage;
            }
        });
    }

    categories.forEach(categoryId => {
        const entries = yearData[categoryId] || [];
        const scored = entries.map(entry => {
            let score = 0;
            const precursorWins = [];
            const precursorNoms = [];

            if (entry.awards) {
                for (const [awardKey, status] of Object.entries(entry.awards)) {
                    if (status === 'Y') { // Only wins count
                        const weight = dynamicWeights[awardKey] || 2;
                        score += weight;
                        precursorWins.push(awardKey);
                    } else {
                        // Any other status ('X') implies nomination
                        precursorNoms.push(awardKey);
                    }
                }
            }

            return {
                ...entry,
                score,
                precursorWins,
                precursorNoms
            };
        });

        // Sort by score descending, then by number of nominations (Tie-breaker)
        scored.sort((a, b) => {
            if (b.score !== a.score) {
                return b.score - a.score;
            }
            // Tie-breaker: Number of nominations (precursorNoms)
            // More nominations = better currency even if they didn't win high weight awards
            const nomsA = a.precursorNoms ? a.precursorNoms.length : 0;
            const nomsB = b.precursorNoms ? b.precursorNoms.length : 0;
            return nomsB - nomsA;
        });

        // Calculate total score for normalization (Sum = 100%)
        const totalScore = scored.reduce((sum, entry) => sum + entry.score, 0);

        // Add probability percentage
        scored.forEach(entry => {
            entry.probability = totalScore > 0 ? Math.round((entry.score / totalScore) * 100) : 0;
        });

        // Show all entries to fill the list, even if 0%
        predictions[categoryId] = scored;
    });

    return predictions;
}

function renderPredictionsPage(predictions, container) {
    const categoryLabels = {
        'best-film': 'Best Picture',
        'best-director': 'Best Director',
        'best-actor': 'Best Actor',
        'best-actress': 'Best Actress'
    };

    const awardLabels = {
        sag: 'SAG', bafta: 'BAFTA', dga: 'DGA', pga: 'PGA', critics: 'Critics',
        gg: 'GG', lafca: 'LAFCA', nyfcc: 'NYFCC', nbr: 'NBR', gotham: 'Gotham',
        spirit: 'Spirit', astra: 'Astra', afi: 'AFI', venice: 'Venice',
        cannes: 'Cannes', bifa: 'BIFA', annie: 'Annie', adg: 'ADG'
    };

    const yearDisplay = currentYear ? currentYear.replace('_', '/') : '';

    let htmlSections = '';
    let isReversed = false;

    Object.keys(categoryLabels).forEach(categoryId => {
        const allEntries = predictions[categoryId] || [];
        const isPerson = categoryId !== 'best-film';
        const isActorCategory = categoryId === 'best-actor' || categoryId === 'best-actress';

        let groups = [];

        // Split logic for Actor/Actress
        if (isActorCategory) {
            const leading = allEntries.filter(e => e.role === 'Leading');
            const supporting = allEntries.filter(e => e.role === 'Supporting');

            if (leading.length > 0 || supporting.length > 0) {
                if (leading.length > 0) groups.push({ title: `${categoryLabels[categoryId].toUpperCase()} - LEADING`, entries: leading });
                if (supporting.length > 0) groups.push({ title: `${categoryLabels[categoryId].toUpperCase()} - SUPPORTING`, entries: supporting });
            } else {
                groups.push({ title: categoryLabels[categoryId].toUpperCase(), entries: allEntries });
            }
        } else {
            groups.push({ title: categoryLabels[categoryId].toUpperCase(), entries: allEntries });
        }

        groups.forEach(group => {
            const entries = group.entries;

            if (entries.length === 0) {
                htmlSections += `
                    <div class="stats-section-wide pred-section-wide">
                        <h2 class="category-title-large">${group.title}</h2>
                        <div class="pred-empty">No data available</div>
                    </div>
                 `;
            } else {
                const topEntries = [...entries].slice(0, 8);
                const winner = topEntries[0];

                const renderWinnerCard = (entry) => {
                    const imageUrl = isPerson && entry.profilePath
                        ? `${CONFIG.TMDB_IMAGE_BASE}w500${entry.profilePath}`
                        : (!isPerson && entry.posterPath ? `${CONFIG.TMDB_IMAGE_BASE}w500${entry.posterPath}` : '');

                    const metaText = isPerson ? (entry.role || '') : (entry.genre || '');

                    return `
                        <div class="pred-winner-card">
                            <div class="pred-winner-poster-wrapper">
                                ${imageUrl ? `<img src="${imageUrl}" class="pred-winner-poster" loading="lazy">` : '<div class="pred-winner-placeholder"></div>'}
                                <div class="pred-winner-overlay">
                                     <div class="pred-winner-badge">PREDICTED WINNER</div>
                                     <div class="pred-winner-name">${entry.name}</div>
                                     ${metaText ? `<div class="pred-winner-meta">${metaText}</div>` : ''}
                                     <div class="pred-winner-percent">${entry.probability}%</div>
                                </div>
                            </div>
                        </div>
                    `;
                };

                const getBadges = (entry) => {
                    const badges = [];
                    // Wins (Gold)
                    if (entry.precursorWins) {
                        entry.precursorWins.forEach(award => {
                            badges.push(`<span class="nominee-badge badge-win">${awardLabels[award] || award.toUpperCase()}</span>`);
                        });
                    }
                    // Nominations (Silver)
                    if (entry.precursorNoms) {
                        entry.precursorNoms.forEach(award => {
                            badges.push(`<span class="nominee-badge badge-nom">${awardLabels[award] || award.toUpperCase()}</span>`);
                        });
                    }

                    // Fallback for awards not processed in precursor arrays (safety check)
                    const allAwards = entry.awards || {};
                    Object.keys(allAwards).forEach(award => {
                        const isWin = allAwards[award] === 'Y';
                        const inWins = entry.precursorWins && entry.precursorWins.includes(award);
                        const inNoms = entry.precursorNoms && entry.precursorNoms.includes(award);

                        if (isWin && !inWins) {
                            badges.push(`<span class="nominee-badge badge-win">${awardLabels[award] || award.toUpperCase()}</span>`);
                        } else if (!isWin && !inNoms && !inWins) {
                            badges.push(`<span class="nominee-badge badge-nom">${awardLabels[award] || award.toUpperCase()}</span>`);
                        }
                    });

                    return badges.join('');
                };

                const renderListItem = (entry, idx) => {
                    const mobileBadgesHtml = getBadges(entry);
                    const mobileBadges = mobileBadgesHtml ? `<div class="mobile-badges">${mobileBadgesHtml}</div>` : '';
                    const metaText = isPerson ? (entry.role || '') : (entry.genre || '');

                    const imageUrl = isPerson && entry.profilePath
                        ? `${CONFIG.TMDB_IMAGE_BASE}w185${entry.profilePath}`
                        : (!isPerson && entry.posterPath ? `${CONFIG.TMDB_IMAGE_BASE}w185${entry.posterPath}` : '');

                    const posterHtml = imageUrl
                        ? `<img src="${imageUrl}" class="pred-list-poster-img" loading="lazy">`
                        : `<div class="pred-list-poster-img" style="background:var(--line);"></div>`;

                    return `
                        <div class="stats-list-row pred-list-row ${idx === 0 ? 'is-winner-row' : ''}">
                            <div class="pred-list-poster-mobile">
                                ${posterHtml}
                            </div>
                            <!-- Rank hidden on mobile via CSS if desired, but kept in DOM -->
                            <span class="stats-list-rank">${idx + 1}</span>
                            
                            <div class="pred-list-info">
                                 <div class="pred-list-header">
                                    <span class="stats-list-name" style="padding: 0;">${entry.name}</span>
                                    <span class="pred-list-percent">${entry.probability}%</span>
                                 </div>
                                 ${metaText ? `<span class="pred-meta">${metaText}</span>` : ''}
                                 ${mobileBadges}
                                 <div class="pred-badges-desktop">${mobileBadgesHtml}</div>
                            </div>
                        </div>
                     `;
                };

                htmlSections += `
                    <div class="stats-section-wide pred-section-wide">
                        <h2 class="category-title-large">${group.title}</h2>
                        <div class="stats-split-layout ${isReversed ? 'layout-reverse' : ''}">
                            <div class="stats-visual-side pred-visual-side">
                                ${renderWinnerCard(winner)}
                            </div>
                            <div class="stats-list-side pred-list-side">
                                ${topEntries.map((e, idx) => renderListItem(e, idx)).join('')}
                            </div>
                        </div>
                    </div>
                `;
            }
            isReversed = !isReversed;
        });
    });

    const html = `
        <div class="stats-header">
            <h1 class="stats-title">Oscar Predictions ${yearDisplay}</h1>
            <p class="stats-subtitle">Probabilities based on precursor award wins</p>
        </div>
        
        <div class="stats-content-wrapper">
             ${htmlSections}
        </div>
        
        <div class="pred-analysis-section">
            <h2>Historical Analysis</h2>
            <div id="precursor-analysis-container">
                <div class="loading-analysis">Loading historical data...</div>
            </div>
        </div>

        </div>
    `;

    container.innerHTML = html;
}


function renderPredictionCharts(predictions, categoryLabels) {
    if (typeof Chart === 'undefined') {
        console.warn('Chart.js not loaded');
        return;
    }

    const chartColors = {
        gold: 'rgba(212, 168, 75, 0.8)',
        silver: 'rgba(192, 192, 192, 0.8)',
        bronze: 'rgba(205, 127, 50, 0.8)',
        default: 'rgba(255, 255, 255, 0.3)'
    };

    Object.keys(categoryLabels).forEach(catId => {
        const canvas = document.getElementById(`chart-${catId}`);
        if (!canvas) return;

        const entries = (predictions[catId] || []).slice(0, 5);
        const labels = entries.map(e => e.name.length > 20 ? e.name.substring(0, 18) + '...' : e.name);
        const data = entries.map(e => e.score);
        const colors = entries.map((_, i) =>
            i === 0 ? chartColors.gold :
                i === 1 ? chartColors.silver :
                    i === 2 ? chartColors.bronze : chartColors.default
        );

        new Chart(canvas, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Score',
                    data: data,
                    backgroundColor: colors,
                    borderColor: colors.map(c => c.replace('0.8', '1')),
                    borderWidth: 1
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: {
                        display: true,
                        text: categoryLabels[catId],
                        color: '#d4a84b',
                        font: { size: 14, weight: 'bold' }
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255,255,255,0.1)' },
                        ticks: { color: '#888' }
                    },
                    y: {
                        grid: { display: false },
                        ticks: { color: '#ccc', font: { size: 11 } }
                    }
                }
            }
        });
    });
}

// ============ HISTORICAL PRECURSOR ANALYSIS ============
async function loadHistoricalAnalysis() {
    const container = document.getElementById('precursor-analysis-container');
    if (!container) return;

    try {
        // Use existing loadAllYearsData function (works with Firebase/localStorage)
        const allData = await loadAllYearsData();

        if (Object.keys(allData).length === 0) {
            container.innerHTML = `<div class="analysis-error">No historical data available. Please ensure past season data is loaded.</div>`;
            return;
        }

        // Analyze precursor success rates
        const analysis = analyzeHistoricalPrecursors(allData);
        renderPrecursorAnalysis(analysis, container);
    } catch (error) {
        container.innerHTML = `<div class="analysis-error">Error loading data: ${error.message}</div>`;
    }
}

function analyzeHistoricalPrecursors(allData) {
    const precursors = ['sag', 'bafta', 'dga', 'pga', 'critics', 'gg', 'lafca', 'nyfcc', 'nbr', 'gotham', 'spirit'];
    const categories = ['best-film', 'best-director', 'best-actor', 'best-actress'];

    // Track: for each precursor, how many times did the Oscar winner ALSO win/nominate that precursor?
    const stats = {};
    precursors.forEach(p => {
        stats[p] = { wins: 0, noms: 0, total: 0, label: p.toUpperCase() };
    });

    const labelMap = {
        sag: 'SAG', bafta: 'BAFTA', dga: 'DGA', pga: 'PGA', critics: 'Critics Choice',
        gg: 'Golden Globes', lafca: 'LAFCA', nyfcc: 'NYFCC', nbr: 'NBR', gotham: 'Gotham', spirit: 'Spirit'
    };
    precursors.forEach(p => stats[p].label = labelMap[p] || p.toUpperCase());

    // Category-specific results
    const categoryStats = {};
    categories.forEach(cat => {
        categoryStats[cat] = {};
        precursors.forEach(p => {
            categoryStats[cat][p] = { wins: 0, noms: 0, total: 0 };
        });
    });

    // Process each year
    Object.keys(allData).forEach(yearKey => {
        const yearData = allData[yearKey];

        categories.forEach(catId => {
            const entries = yearData[catId] || [];

            // Find Oscar winner (has 'oscar' in awards with 'Y')
            const oscarWinner = entries.find(e => e.awards && e.awards.oscar === 'Y');
            if (!oscarWinner) return;

            // Check which precursors the Oscar winner also won/nominated
            precursors.forEach(precursor => {
                stats[precursor].total++;
                categoryStats[catId][precursor].total++;

                // If key exists, it's a nomination (or win)
                if (oscarWinner.awards[precursor]) {
                    stats[precursor].noms++;
                    categoryStats[catId][precursor].noms++;
                }

                if (oscarWinner.awards[precursor] === 'Y') {
                    stats[precursor].wins++;
                    categoryStats[catId][precursor].wins++;
                }
            });
        });
    });

    // Calculate percentages and sort
    const results = precursors.map(p => ({
        key: p,
        label: stats[p].label,
        wins: stats[p].wins,
        noms: stats[p].noms,
        total: stats[p].total,
        percentage: stats[p].total > 0 ? Math.round((stats[p].wins / stats[p].total) * 100) : 0,
        nomPercentage: stats[p].total > 0 ? Math.round((stats[p].noms / stats[p].total) * 100) : 0
    })).sort((a, b) => b.percentage - a.percentage);

    // Category breakdowns
    const categoryBreakdown = {};
    categories.forEach(cat => {
        categoryBreakdown[cat] = precursors.map(p => ({
            key: p,
            label: stats[p].label,
            wins: categoryStats[cat][p].wins,
            total: categoryStats[cat][p].total,
            percentage: categoryStats[cat][p].total > 0 ?
                Math.round((categoryStats[cat][p].wins / categoryStats[cat][p].total) * 100) : 0,
            nomPercentage: categoryStats[cat][p].total > 0 ?
                Math.round((categoryStats[cat][p].noms / categoryStats[cat][p].total) * 100) : 0
        })).sort((a, b) => b.percentage - a.percentage);
    });

    return { overall: results, byCategory: categoryBreakdown };
}

function renderPrecursorAnalysis(analysis, container) {
    const categoryLabels = {
        'best-film': 'Best Picture',
        'best-director': 'Best Director',
        'best-actor': 'Best Actor',
        'best-actress': 'Best Actress'
    };

    // Overall chart
    let html = `
        <div class="analysis-overall">
            <h3>Overall Correlation of Awards vs Oscars</h3>
            <p class="analysis-note">% of times the Oscar winner also won the following award (2000-2026)</p>
            <div class="analysis-bars">
                ${analysis.overall.map((item, idx) => {
        // Use standard colors for all items as requested
        const barColor = 'var(--gold)';
        const nomBarColor = 'var(--bar-bg-nom)';
        const isTop = idx < 3;
        return `
                        <div class="analysis-bar-row ${isTop ? 'top-predictor' : ''}">
                            <span class="analysis-label">${item.label}</span>
                            <div class="analysis-bar-container">
                                <div class="analysis-bar-nom" style="width: ${item.nomPercentage}%; background: ${nomBarColor}"></div>
                                <div class="analysis-bar" style="width: ${item.percentage}%; background: ${barColor}"></div>
                            </div>
                            <div class="analysis-percent-group">
                                <span class="analysis-percent">${item.percentage}%</span>
                                <span class="analysis-percent-nom">${item.nomPercentage}%</span>
                            </div>
                            <span class="analysis-detail">(${item.wins}/${item.total})</span>
                        </div>
                    `;
    }).join('')}
            </div>
        </div>

        <div class="analysis-categories">
            <h3>Analysis by Category</h3>
            <div class="analysis-category-grid">
                ${Object.keys(categoryLabels).map(catId => {
        const catData = analysis.byCategory[catId] || [];
        const top3 = catData.slice(0, 3);
        return `
                        <div class="analysis-category-card">
                            <h4>${categoryLabels[catId]}</h4>
                            <div class="analysis-category-top">
                                ${top3.map((item, idx) => `
                                    <div class="top-predictor-row">
                                        <span class="top-rank">${idx + 1}.</span>
                                        <span class="top-name">${item.label}</span>
                                        <div class="top-percentages">
                                            <span class="top-percent">${item.percentage}%</span>
                                            <span class="top-percent-nom" style="color: rgba(255,255,255,0.7); font-size: 0.85em; margin-left: 6px;">${item.nomPercentage}%</span>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    `;
    }).join('')}
            </div>
        </div>
    `;

    container.innerHTML = html;
}

// ============ GLOBAL SCROLL TRACKING ============
let isScrolling = false;
let scrollTimeout;

// Use CAPTURE phase to detect scrolling on ANY element (like overflow divs)
window.addEventListener('scroll', () => {
    isScrolling = true;
    clearTimeout(scrollTimeout);
    scrollTimeout = setTimeout(() => {
        isScrolling = false;
    }, 150);
}, true); // true = capture phase

// Helper to check if we should allow a click
function isClickAllowed() {
    return !isScrolling;
}
