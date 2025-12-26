/**
 * Control Panel Script
 * Loads analysis from Firebase and renders status tables
 */

const FIREBASE_URL = 'https://seasonawards-8deae-default-rtdb.europe-west1.firebasedatabase.app';
const CURRENT_YEAR = '2025_2026';

const AWARDS_ORDER = ['oscar', 'gg', 'bafta', 'sag', 'critics', 'afi', 'nbr', 'venice', 'dga', 'pga'];
const AWARDS_NAMES = {
    'oscar': 'Oscar',
    'gg': 'Golden Globes',
    'bafta': 'BAFTA',
    'sag': 'SAG',
    'critics': 'Critics\' Choice',
    'afi': 'AFI',
    'nbr': 'NBR',
    'venice': 'Venice',
    'dga': 'DGA',
    'pga': 'PGA'
};

const CATEGORIES = ['best-film', 'best-director', 'best-actor', 'best-actress'];
const CATEGORY_SHORT = {
    'best-film': 'Film',
    'best-director': 'Director',
    'best-actor': 'Actor',
    'best-actress': 'Actress'
};

async function loadAnalysis() {
    try {
        const response = await fetch(`${FIREBASE_URL}/analysis.json`);
        if (!response.ok) throw new Error('Failed to load analysis from Firebase');
        return await response.json();
    } catch (error) {
        console.error('Error loading analysis:', error);
        return null;
    }
}

function formatDate(isoString) {
    const date = new Date(isoString);
    return date.toLocaleString('it-IT', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function countStatuses(data) {
    let ok = 0, error = 0, pending = 0;
    for (const yearKey in data.years) {
        for (const award in data.years[yearKey]) {
            for (const category in data.years[yearKey][award]) {
                const status = data.years[yearKey][award][category].status;
                if (status === 'ok') ok++;
                else if (status === 'error') error++;
                else if (status === 'pending') pending++;
            }
        }
    }
    return { ok, error, pending, total: ok + error + pending };
}

function renderSummary(stats) {
    const container = document.getElementById('summary-stats');
    container.innerHTML = `
        <div class="cp-stat ok">
            <div class="cp-stat-value">${stats.ok}</div>
            <div class="cp-stat-label">OK</div>
        </div>
        <div class="cp-stat error">
            <div class="cp-stat-value">${stats.error}</div>
            <div class="cp-stat-label">Errors</div>
        </div>
        <div class="cp-stat pending">
            <div class="cp-stat-value">${stats.pending}</div>
            <div class="cp-stat-label">Pending</div>
        </div>
        <div class="cp-stat">
            <div class="cp-stat-value">${Math.round(stats.ok / stats.total * 100)}%</div>
            <div class="cp-stat-label">Health</div>
        </div>
    `;
}

// ============ CURRENT YEAR RECAP ============
function renderCurrentYear(data) {
    const container = document.getElementById('current-year-container');
    const yearData = data.years[CURRENT_YEAR];
    const expected = data.expected;

    if (!yearData) {
        container.innerHTML = `<div class="cp-recap-wrapper"><div class="cp-recap-title">Season 2025/2026</div><p style="text-align:center;color:#999;">No data yet</p></div>`;
        return;
    }

    let html = `
        <div class="cp-recap-wrapper">
            <div class="cp-recap-title">Season 2025/2026</div>
            <div class="cp-recap-header">
                <span></span>
                <span>Film</span>
                <span>Dir</span>
                <span>Actor</span>
                <span>Actress</span>
            </div>
            <div class="cp-recap-grid">
    `;

    for (const awardKey of AWARDS_ORDER) {
        const awardData = yearData[awardKey];
        if (!awardData) continue;

        let cells = [];
        for (const category of CATEGORIES) {
            const catData = awardData[category] || { nominations: 0, winners: 0, status: 'pending' };
            const expectedCount = expected[awardKey]?.[category] || 0;

            if (expectedCount === 0 && catData.nominations === 0) {
                cells.push(`<span class="cp-recap-cell muted">—</span>`);
            } else {
                cells.push(`<span class="cp-recap-cell ${catData.status}"><b>${catData.nominations}</b><small>/${expectedCount}</small></span>`);
            }
        }

        html += `<div class="cp-recap-row"><span class="cp-recap-award">${AWARDS_NAMES[awardKey]}</span>${cells.join('')}</div>`;
    }

    html += `</div></div>`;
    container.innerHTML = html;
}

// ============ HISTORICAL RECAP ============
function renderAwardCard(awardKey, data) {
    const years = Object.keys(data.years).filter(y => y !== CURRENT_YEAR).sort().reverse();
    const awardName = AWARDS_NAMES[awardKey] || awardKey.toUpperCase();

    let html = `
        <div class="cp-history-card">
            <div class="cp-history-title">${awardName}</div>
            <div class="cp-recap-header">
                <span>Year</span>
                <span>Film</span>
                <span>Dir</span>
                <span>Actor</span>
                <span>Actress</span>
            </div>
            <div class="cp-recap-grid">
    `;

    for (const yearKey of years) {
        const yearData = data.years[yearKey][awardKey];
        if (!yearData) continue;

        // Show season as "24/25" format
        const years_parts = yearKey.split('_');
        const yearLabel = `${years_parts[0].slice(-2)}/${years_parts[1].slice(-2)}`;

        let cells = [];
        for (const category of CATEGORIES) {
            const catData = yearData[category] || { nominations: 0, winners: 0, status: 'pending', expected: 0 };
            // Use year-specific expected value from the data
            const expectedCount = catData.expected || data.expected[awardKey]?.[category] || 0;

            if (expectedCount === 0 && catData.nominations === 0) {
                cells.push(`<span class="cp-recap-cell muted">-</span>`);
            } else {
                cells.push(`<span class="cp-recap-cell ${catData.status}"><b>${catData.nominations}</b>/${expectedCount}</span>`);
            }
        }

        html += `<div class="cp-recap-row"><span class="cp-recap-award">${yearLabel}</span>${cells.join('')}</div>`;
    }

    html += `</div></div>`;
    return html;
}

async function init() {
    const data = await loadAnalysis();

    if (!data) {
        document.getElementById('current-year-container').innerHTML = `
            <div style="text-align: center; padding: 48px; color: #ef4444;">
                <h2>Error Loading Data</h2>
                <p>Could not load analysis from Firebase. Please run the scraper first.</p>
            </div>
        `;
        return;
    }

    // Update generated time
    document.getElementById('generated-time').textContent = `Last update: ${formatDate(data.generated)}`;

    // Render summary stats
    const stats = countStatuses(data);
    renderSummary(stats);

    // Render current year table
    renderCurrentYear(data);

    // Render historical award cards
    const container = document.getElementById('awards-container');
    let html = '';
    for (const awardKey of AWARDS_ORDER) {
        html += renderAwardCard(awardKey, data);
    }
    container.innerHTML = html;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', init);
