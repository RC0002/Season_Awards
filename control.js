/**
 * Control Panel Script
 * Loads analysis from Firebase and renders status tables
 */

const FIREBASE_URL = 'https://seasonawards-8deae-default-rtdb.europe-west1.firebasedatabase.app';
const CURRENT_YEAR = '2025_2026';

const AWARDS_ORDER = ['oscar', 'gg', 'bafta', 'sag', 'critics', 'afi', 'nbr', 'venice', 'cannes', 'annie', 'dga', 'pga', 'lafca', 'nyfcc', 'wga', 'adg', 'gotham', 'astra', 'spirit', 'bifa'];
const AWARDS_NAMES = {
    'oscar': 'Oscar',
    'gg': 'Golden Globes',
    'bafta': 'BAFTA',
    'sag': 'SAG',
    'critics': 'Critics\' Choice',
    'afi': 'AFI',
    'nbr': 'NBR',
    'venice': 'Venice',
    'cannes': 'Cannes',
    'annie': 'Annie',
    'dga': 'DGA',
    'pga': 'PGA',
    'lafca': 'LAFCA',
    'nyfcc': 'NYFCC',
    'wga': 'WGA',
    'adg': 'ADG',
    'gotham': 'Gotham',
    'astra': 'Astra',
    'spirit': 'Spirit',
    'bifa': 'BIFA'
};

const CATEGORIES = ['best-film', 'best-director', 'best-actor', 'best-actress'];
const CATEGORY_SHORT = {
    'best-film': 'Film',
    'best-director': 'Director',
    'best-actor': 'Actor',
    'best-actress': 'Actress'
};

async function loadAnalysis() {
    // Try local file first, then Firebase fallback
    const sources = [
        'data/analysis.json',  // Local file
        `${FIREBASE_URL}/analysis.json`  // Firebase fallback
    ];

    for (const source of sources) {
        try {
            const response = await fetch(`${source}?t=${new Date().getTime()}`);
            if (response.ok) {
                const data = await response.json();
                console.log(`Loaded analysis from: ${source}`);
                return data;
            }
        } catch (error) {
            console.warn(`Failed to load from ${source}:`, error);
        }
    }

    console.error('Error loading analysis from all sources');
    return null;
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

/**
 * Helper to calculate status for combined categories (Gotham, Spirit, BIFA, LAFCA)
 * centralizing the logic used by both summary and table rendering.
 */
function getCombinedStatus(award, yearKey, data) {
    const yearNum = parseInt(yearKey.split('_')[1]);
    const actorData = data.years[yearKey][award]['best-actor'] || { nominations: 0, status: 'pending' };
    const actressData = data.years[yearKey][award]['best-actress'] || { nominations: 0, status: 'pending' };
    const combined = actorData.nominations + actressData.nominations;

    let target;
    // 1. Check for explicit expected overrides in JSON (Spirit/BIFA manual fixes)
    if (actorData.expected !== undefined && actressData.expected !== undefined) {
        target = actorData.expected + actressData.expected;
    }
    // 2. Fallback to hardcoded historical rules
    else if (award === 'gotham') {
        if (yearNum <= 2013) target = 0;
        else if (yearNum === 2016) target = 11;
        else if (yearNum === 2018) target = 11;
        else if (yearNum === 2021) target = 10;
        else if (yearNum === 2022) target = 17;
        else if (yearNum >= 2023) target = 20;
        else target = 10;
    } else if (award === 'bifa') {
        if (yearNum >= 2025) target = 12;
        else if (yearNum === 2024) target = 16;
        else if (yearNum === 2023) target = 17;
        else target = 20;
    } else if (award === 'spirit') {
        if (yearNum === 2013 || yearNum === 2014) target = 21;
        else if (yearNum >= 2018 && yearNum <= 2021) target = 21;
        else target = 20;
    } else if (award === 'lafca') {
        target = 8;
    }

    if (combined === target) return 'ok';
    if (combined === 0 && target === 0) return 'ok';
    if (combined === 0) return 'pending';
    return 'error';
}

function countStatuses(data) {
    let ok = 0, error = 0, pending = 0;
    const expected = data.expected;

    for (const yearKey in data.years) {
        const yearNum = parseInt(yearKey.split('_')[1]);
        const alwaysCombined = (aw) => ['lafca', 'gotham', 'bifa'].includes(aw);

        for (const award in data.years[yearKey]) {
            const isCombinedAward = alwaysCombined(award) || (award === 'spirit' && yearNum >= 2023);

            for (const category in data.years[yearKey][award]) {
                const catData = data.years[yearKey][award][category];
                let status = catData.status;

                // Cancellation logic (Cannes 2020/21, etc)
                const expectedCount = (catData.expected !== undefined) ? catData.expected : (expected[award]?.[category] || 0);
                const isCancelled = (expectedCount === 0 && catData.nominations === 0) ||
                    (award === 'cannes' && yearNum === 2021 && catData.nominations === 0);

                if (isCancelled) continue; // Don't count N/A in OK/Error/Pending

                // Combined awards: count pair as 1 unit
                if (isCombinedAward && (category === 'best-actor' || category === 'best-actress')) {
                    if (category === 'best-actress') continue; // count once per pair
                    status = getCombinedStatus(award, yearKey, data);
                }

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

        const isCombined = awardKey === 'lafca' || awardKey === 'gotham' || awardKey === 'bifa' || awardKey === 'spirit';
        let cells = [];

        if (isCombined) {
            // Combined: Film, Director, then combined Actor+Actress
            // For Gotham/LAFCA in summary
            for (const category of ['best-film', 'best-director']) {
                const catData = awardData[category] || { nominations: 0, winners: 0, status: 'pending', expected: undefined };
                const expectedCount = (catData.expected !== undefined) ? catData.expected : (expected[awardKey]?.[category] || 0);

                if (expectedCount === 0 && catData.nominations === 0) {
                    cells.push(`<span class="cp-recap-cell muted"><i class="bi bi-dash-lg text-muted op-50"></i></span>`);
                } else {
                    cells.push(`<span class="cp-recap-cell ${catData.status}"><b>${catData.nominations}</b><small>/${expectedCount}</small></span>`);
                }
            }

            // Combined Actor + Actress cell spanning 2 columns
            const actorData = awardData['best-actor'] || { nominations: 0, status: 'pending' };
            const actressData = awardData['best-actress'] || { nominations: 0, status: 'pending' };
            const combined = actorData.nominations + actressData.nominations;
            const combinedStatus = getCombinedStatus(awardKey, CURRENT_YEAR, data);

            const comboText = ((awardKey === 'gotham' || awardKey === 'bifa' || awardKey === 'spirit') && combined > 0) ? `<b>${actorData.nominations}+${actressData.nominations}</b>` : `<b>${combined}</b>`;
            cells.push(`<span class="cp-recap-cell ${combinedStatus}" style="grid-column: span 2; text-align: center;">${comboText}</span>`);
        } else {
            // Standard awards
            for (const category of CATEGORIES) {
                const catData = awardData[category] || { nominations: 0, winners: 0, status: 'pending', expected: undefined };
                let expectedCount = (catData.expected !== undefined) ? catData.expected : (expected[awardKey]?.[category] || 0);

                // Force ADG Film expected count if missing
                if (awardKey === 'adg' && category === 'best-film' && expectedCount === 0) {
                    expectedCount = 15;
                }

                // Special case: Cannes 2020 was cancelled (COVID-19)
                const isCancelled = (expectedCount === 0 && catData.nominations === 0) ||
                    (awardKey === 'cannes' && catData.status === 'pending' && catData.nominations === 0);

                if (isCancelled) {
                    cells.push(`<span class="cp-recap-cell muted"><i class="bi bi-slash-lg text-muted op-50"></i></span>`);
                } else {
                    cells.push(`<span class="cp-recap-cell ${catData.status}"><b>${catData.nominations}</b><small>/${expectedCount}</small></span>`);
                }
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

    // LAFCA, GOTHAM, BIFA use combined Actor+Actress column always
    // SPIRIT uses combined only from 2023+ (gender-neutral since 38th)
    const alwaysCombined = awardKey === 'lafca' || awardKey === 'gotham' || awardKey === 'bifa';

    let html = `
        <div class="cp-history-card">
            <div class="cp-history-title">${awardName}</div>
            <div class="cp-recap-header">
                <span>Year</span>
                <span>Film</span>
                <span>Dir</span>
                ${alwaysCombined
            ? '<span style="grid-column: span 2; text-align: center;">Actor + Actress</span>'
            : '<span>Actor</span><span>Actress</span>'}
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

        // Determine if this specific year should use combined display
        const yearNum = parseInt(yearKey.split('_')[1]);
        const isCombined = alwaysCombined || (awardKey === 'spirit' && yearNum >= 2023);

        if (isCombined) {
            // Combined: Film, Director, then combined Actor+Actress
            for (const category of ['best-film', 'best-director']) {
                const catData = yearData[category] || { nominations: 0, winners: 0, status: 'pending', expected: undefined };
                const expectedCount = (catData.expected !== undefined) ? catData.expected : (data.expected[awardKey]?.[category] || 0);

                if (expectedCount === 0 && catData.nominations === 0) {
                    cells.push(`<span class="cp-recap-cell muted"><i class="bi bi-dash-lg text-muted op-50"></i></span>`);
                } else {
                    cells.push(`<span class="cp-recap-cell ${catData.status}"><b>${catData.nominations}</b>/${expectedCount}</span>`);
                }
            }

            // Combined Actor + Actress cell
            const actorData = yearData['best-actor'] || { nominations: 0, status: 'pending' };
            const actressData = yearData['best-actress'] || { nominations: 0, status: 'pending' };
            const combined = actorData.nominations + actressData.nominations;
            const combinedStatus = getCombinedStatus(awardKey, yearKey, data);

            if (actorData.nominations === 0 && actressData.nominations === 0 && combinedStatus === 'ok') {
                cells.push(`<span class="cp-recap-cell muted" style="grid-column: span 2; text-align: center;"><i class="bi bi-dash-lg text-muted op-50"></i></span>`);
            } else {
                cells.push(`<span class="cp-recap-cell ${combinedStatus}" style="grid-column: span 2; text-align: center;"><b>${actorData.nominations}+${actressData.nominations}</b></span>`);
            }
        } else {
            // Standard awards: separate columns
            for (const category of CATEGORIES) {
                const catData = yearData[category] || { nominations: 0, winners: 0, status: 'pending', expected: undefined };
                const expectedCount = (catData.expected !== undefined) ? catData.expected : (data.expected[awardKey]?.[category] || 0);

                // Special case: Cannes 2020 was cancelled (COVID-19) - year 2021 in season format
                const isCancelled = (expectedCount === 0 && catData.nominations === 0) ||
                    (awardKey === 'cannes' && yearNum === 2021 && catData.nominations === 0);

                if (isCancelled) {
                    cells.push(`<span class="cp-recap-cell muted"><i class="bi bi-dash-lg"></i></span>`);
                } else {
                    cells.push(`<span class="cp-recap-cell ${catData.status}"><b>${catData.nominations}</b>/${expectedCount}</span>`);
                }
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
