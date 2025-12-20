// Season Awards Nomination Tracker - Full Interactive System
// Features: Multi-year, LocalStorage, TMDB Autocomplete

// ============ CONFIGURATION ============
const CONFIG = {
    // TMDB API Key - Replace with your own from https://www.themoviedb.org/settings/api
    TMDB_API_KEY: 'YOUR_TMDB_API_KEY_HERE',
    TMDB_BASE_URL: 'https://api.themoviedb.org/3',

    // Year range
    START_YEAR: 2018,

    // Award columns (from provided image)
    AWARDS: [
        'Academy Awards',
        'Golden Globe',
        'BAFTA',
        'SAG',
        'LAFCA',
        'AFI',
        'NBR',
        'DGA',
        'PGA',
        'WGA',
        'Art Directors',
        "Critic's Choice",
        'Gotham',
        'HCA',
        'Spirit',
        'BIFA',
        'Annie',
        'NYFCC',
        'Cannes',
        'Venezia'
    ],

    // Categories
    CATEGORIES: [
        { id: 'best-film', title: 'BEST FILM', placeholder: 'Film', searchType: 'movie' },
        { id: 'best-actress', title: 'BEST ACTRESS', placeholder: 'Actress / Film', searchType: 'person' },
        { id: 'best-actor', title: 'BEST ACTOR', placeholder: 'Actor / Film', searchType: 'person' },
        { id: 'best-director', title: 'BEST DIRECTOR', placeholder: 'Director / Film', searchType: 'person' }
    ]
};

// ============ STATE ============
let currentYear = null;
let data = {};

// ============ INITIALIZATION ============
document.addEventListener('DOMContentLoaded', function () {
    // Calculate current award season year
    const now = new Date();
    const currentMonth = now.getMonth();
    const currentFullYear = now.getFullYear();

    // Award season runs from fall to spring of next year
    // If we're before September, we're in the previous year's season
    if (currentMonth < 8) { // Before September
        currentYear = (currentFullYear - 1) + '_' + currentFullYear;
    } else {
        currentYear = currentFullYear + '_' + (currentFullYear + 1);
    }

    // Build the page
    buildPage();
    loadData();
    renderAllTables();
});

// ============ PAGE BUILDING ============
function buildPage() {
    const container = document.querySelector('.container');

    // Clear existing content
    container.innerHTML = '';

    // Header with year selector
    container.innerHTML = `
        <header>
            <h1>SEASON AWARDS</h1>
            <div class="year-selector">
                <label for="year-select">Season:</label>
                <select id="year-select"></select>
            </div>
        </header>
    `;

    // Populate year selector
    const yearSelect = document.getElementById('year-select');
    const years = getAvailableYears();
    years.forEach(year => {
        const option = document.createElement('option');
        option.value = year.value;
        option.textContent = year.label;
        if (year.value === currentYear) {
            option.selected = true;
        }
        yearSelect.appendChild(option);
    });

    yearSelect.addEventListener('change', function () {
        currentYear = this.value;
        loadData();
        renderAllTables();
    });

    // Create category sections
    CONFIG.CATEGORIES.forEach(category => {
        const section = document.createElement('div');
        section.className = 'section';
        section.id = category.id;
        section.innerHTML = `
            <h2>${category.title}</h2>
            <div class="section-controls">
                <div class="autocomplete-wrapper">
                    <input type="text" id="${category.id}-input" placeholder="Enter ${category.placeholder}..." data-search-type="${category.searchType}">
                    <div class="autocomplete-list" id="${category.id}-autocomplete"></div>
                </div>
                <button class="btn" id="${category.id}-add">+ Add</button>
            </div>
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>${category.placeholder}</th>
                            ${CONFIG.AWARDS.map(award => `<th>${award}</th>`).join('')}
                        </tr>
                    </thead>
                    <tbody id="${category.id}-tbody"></tbody>
                </table>
            </div>
        `;
        container.appendChild(section);

        // Add event listeners
        const input = document.getElementById(`${category.id}-input`);
        const addBtn = document.getElementById(`${category.id}-add`);

        addBtn.addEventListener('click', () => addEntry(category.id, input));
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') addEntry(category.id, input);
        });

        // TMDB Autocomplete
        setupAutocomplete(input, category.id);
    });

    // Footer
    const footer = document.createElement('footer');
    footer.innerHTML = '<p>Season Awards Nomination Tracker</p>';
    container.appendChild(footer);
}

function getAvailableYears() {
    const years = [];
    const now = new Date();
    const currentFullYear = now.getFullYear();
    const currentMonth = now.getMonth();

    // End year is current or next based on month
    let endYear = currentMonth < 8 ? currentFullYear : currentFullYear + 1;

    for (let year = CONFIG.START_YEAR; year < endYear; year++) {
        years.push({
            value: year + '_' + (year + 1),
            label: year + '/' + (year + 1)
        });
    }

    return years;
}

// ============ DATA MANAGEMENT ============
function getStorageKey() {
    return `seasonAwards_${currentYear}`;
}

function loadData() {
    const stored = localStorage.getItem(getStorageKey());
    if (stored) {
        data = JSON.parse(stored);
    } else {
        // Initialize empty data structure
        data = {};
        CONFIG.CATEGORIES.forEach(cat => {
            data[cat.id] = [];
        });
    }
}

function saveData() {
    localStorage.setItem(getStorageKey(), JSON.stringify(data));
}

// ============ TABLE RENDERING ============
function renderAllTables() {
    CONFIG.CATEGORIES.forEach(category => {
        renderTable(category.id);
    });
}

function renderTable(categoryId) {
    const tbody = document.getElementById(`${categoryId}-tbody`);
    if (!tbody) return;

    tbody.innerHTML = '';

    const entries = data[categoryId] || [];
    entries.forEach((entry, index) => {
        const row = createTableRow(entry, categoryId, index);
        tbody.appendChild(row);
    });
}

function createTableRow(entry, categoryId, index) {
    const row = document.createElement('tr');

    // Name cell with delete button
    const nameCell = document.createElement('td');
    nameCell.className = 'name-cell';
    nameCell.innerHTML = `
        <span class="entry-name">${entry.name}</span>
        <button class="btn-delete" title="Delete">✕</button>
    `;

    // Delete functionality
    const deleteBtn = nameCell.querySelector('.btn-delete');
    deleteBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        deleteEntry(categoryId, index);
    });

    row.appendChild(nameCell);

    // Award cells
    CONFIG.AWARDS.forEach((award, awardIndex) => {
        const cell = document.createElement('td');
        cell.className = 'clickable';

        const value = entry.awards[awardIndex] || '';
        cell.textContent = value;

        if (value === 'Y') {
            cell.classList.add('winner');
        } else if (value === 'X') {
            cell.classList.add('nominee');
        }

        // Click to toggle
        cell.addEventListener('click', () => {
            toggleCell(categoryId, index, awardIndex, cell);
        });

        row.appendChild(cell);
    });

    return row;
}

function toggleCell(categoryId, entryIndex, awardIndex, cell) {
    const entry = data[categoryId][entryIndex];
    if (!entry.awards) entry.awards = [];

    const current = entry.awards[awardIndex] || '';
    let next = '';

    if (current === '') {
        next = 'X';
    } else if (current === 'X') {
        next = 'Y';
    } else {
        next = '';
    }

    entry.awards[awardIndex] = next;
    saveData();

    // Update cell visually (instant, no reload)
    cell.textContent = next;
    cell.classList.remove('winner', 'nominee');
    if (next === 'Y') {
        cell.classList.add('winner');
    } else if (next === 'X') {
        cell.classList.add('nominee');
    }
}

// ============ ENTRY MANAGEMENT ============
function addEntry(categoryId, input) {
    const name = input.value.trim();
    if (!name) {
        input.focus();
        return;
    }

    if (!data[categoryId]) {
        data[categoryId] = [];
    }

    data[categoryId].push({
        name: name,
        awards: new Array(CONFIG.AWARDS.length).fill('')
    });

    saveData();
    renderTable(categoryId);

    input.value = '';
    input.focus();

    // Scroll to the new row
    const tbody = document.getElementById(`${categoryId}-tbody`);
    const lastRow = tbody.lastElementChild;
    if (lastRow) {
        lastRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

function deleteEntry(categoryId, index) {
    // Remove from data (no confirmation for smoother UX)
    data[categoryId].splice(index, 1);
    saveData();
    renderTable(categoryId); // Instant re-render, no reload needed
}

// ============ TMDB AUTOCOMPLETE ============
let autocompleteTimeout = null;

function setupAutocomplete(input, categoryId) {
    const autocompleteList = document.getElementById(`${categoryId}-autocomplete`);
    const searchType = input.dataset.searchType;

    input.addEventListener('input', function () {
        const query = this.value.trim();

        // Clear previous timeout
        if (autocompleteTimeout) {
            clearTimeout(autocompleteTimeout);
        }

        if (query.length < 2) {
            autocompleteList.classList.remove('active');
            return;
        }

        // Debounce API calls
        autocompleteTimeout = setTimeout(() => {
            searchTMDB(query, searchType, autocompleteList, input);
        }, 300);
    });

    // Hide on blur
    input.addEventListener('blur', function () {
        setTimeout(() => {
            autocompleteList.classList.remove('active');
        }, 200);
    });

    // Show on focus if has results
    input.addEventListener('focus', function () {
        if (autocompleteList.children.length > 0) {
            autocompleteList.classList.add('active');
        }
    });
}

async function searchTMDB(query, searchType, autocompleteList, input) {
    // Check if API key is set
    if (CONFIG.TMDB_API_KEY === 'YOUR_TMDB_API_KEY_HERE') {
        // API key not set - don't show autocomplete
        return;
    }

    const endpoint = searchType === 'movie' ? '/search/movie' : '/search/person';
    const url = `${CONFIG.TMDB_BASE_URL}${endpoint}?api_key=${CONFIG.TMDB_API_KEY}&query=${encodeURIComponent(query)}`;

    try {
        const response = await fetch(url);
        const data = await response.json();

        autocompleteList.innerHTML = '';

        if (data.results && data.results.length > 0) {
            const results = data.results.slice(0, 5); // Limit to 5 results

            results.forEach(item => {
                const div = document.createElement('div');
                div.className = 'autocomplete-item';

                if (searchType === 'movie') {
                    const year = item.release_date ? ` (${item.release_date.substring(0, 4)})` : '';
                    div.innerHTML = `<strong>${item.title}</strong>${year}`;
                    div.addEventListener('click', () => {
                        input.value = item.title;
                        autocompleteList.classList.remove('active');
                    });
                } else {
                    div.innerHTML = `<strong>${item.name}</strong><small>${item.known_for_department || ''}</small>`;
                    div.addEventListener('click', () => {
                        input.value = item.name;
                        autocompleteList.classList.remove('active');
                    });
                }

                autocompleteList.appendChild(div);
            });

            autocompleteList.classList.add('active');
        } else {
            autocompleteList.classList.remove('active');
        }
    } catch (error) {
        console.error('TMDB API error:', error);
        autocompleteList.classList.remove('active');
    }
}

// ============ DATA MIGRATION ============
// This function can import existing HTML data if needed
function importFromHTML() {
    // This could be used to migrate existing data from the HTML
    // For now, starting fresh with each year
    console.log('Data migration available if needed');
}
