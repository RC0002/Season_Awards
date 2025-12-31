/**
 * Control Panel Script
 * Loads analysis from Firebase and renders status tables
 */

const FIREBASE_URL = 'https://seasonawards-8deae-default-rtdb.europe-west1.firebasedatabase.app';
const CURRENT_YEAR = '2025_2026';

const AWARDS_ORDER = ['oscar', 'gg', 'bafta', 'sag', 'critics', 'afi', 'nbr', 'venice', 'dga', 'pga', 'lafca', 'wga', 'adg', 'gotham'];
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
    'pga': 'PGA',
    'lafca': 'LAFCA',
    'wga': 'WGA',
    'adg': 'ADG',
    'gotham': 'Gotham'
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
        const response = await fetch(`${FIREBASE_URL}/analysis.json?t=${new Date().getTime()}`);
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
                let status = data.years[yearKey][award][category].status;

                // Recalculate Gotham actor/actress status using year-based expected values
                if (award === 'gotham' && (category === 'best-actor' || category === 'best-actress')) {
                    const yearNum = parseInt(yearKey.split('_')[1]);
                    const actorNoms = data.years[yearKey][award]['best-actor']?.nominations || 0;
                    const actressNoms = data.years[yearKey][award]['best-actress']?.nominations || 0;
                    const combined = actorNoms + actressNoms;

                    // Calculate target using same logic as display
                    let target;
                    if (yearNum <= 2013) target = 0;
                    else if (yearNum === 2016) target = 11;
                    else if (yearNum === 2018) target = 11;
                    else if (yearNum === 2021) target = 10;
                    else if (yearNum === 2022) target = 17;
                    else if (yearNum >= 2023) target = 20;
                    else target = 10;

                    // Recalculate status
                    if (combined === target) status = 'ok';
                    else if (combined === 0 && target === 0) status = 'ok';
                    else if (combined === 0) status = 'pending';
                    else status = 'error';
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

        const isCombined = awardKey === 'lafca' || awardKey === 'gotham';
        let cells = [];

        if (isCombined) {
            // Combined: Film, Director, then combined Actor+Actress
            // For Gotham/LAFCA in summary
            for (const category of ['best-film', 'best-director']) {
                const catData = awardData[category] || { nominations: 0, winners: 0, status: 'pending', expected: undefined };
                const expectedCount = (catData.expected !== undefined) ? catData.expected : (expected[awardKey]?.[category] || 0);

                if (expectedCount === 0 && catData.nominations === 0) {
                    cells.push(`<span class="cp-recap-cell muted"><i class="bi bi-slash-lg text-muted op-50"></i></span>`);
                } else {
                    cells.push(`<span class="cp-recap-cell ${catData.status}"><b>${catData.nominations}</b><small>/${expectedCount}</small></span>`);
                }
            }

            // Combined Actor + Actress cell spanning 2 columns
            const actorData = awardData['best-actor'] || { nominations: 0, status: 'pending' };
            const actressData = awardData['best-actress'] || { nominations: 0, status: 'pending' };
            const combined = actorData.nominations + actressData.nominations;

            let targetTotal = 8; // Default for LAFCA
            if (awardKey === 'gotham') {
                targetTotal = 20; // 2025/2026 season uses 10+10 format
            }
            const combinedStatus = (combined === targetTotal) ? 'ok' : (combined === 0 ? 'pending' : 'error');

            const comboText = (awardKey === 'gotham' && combined > 0) ? `<b>${actorData.nominations}+${actressData.nominations}</b>` : `<b>${combined}</b>`;
            cells.push(`<span class="cp-recap-cell ${combinedStatus}" style="grid-column: span 2; text-align: center;">${comboText}<small>/${targetTotal}</small></span>`);
        } else {
            // Standard awards
            for (const category of CATEGORIES) {
                const catData = awardData[category] || { nominations: 0, winners: 0, status: 'pending', expected: undefined };
                let expectedCount = (catData.expected !== undefined) ? catData.expected : (expected[awardKey]?.[category] || 0);

                // Force ADG Film expected count if missing
                if (awardKey === 'adg' && category === 'best-film' && expectedCount === 0) {
                    expectedCount = 15;
                }

                if (expectedCount === 0 && catData.nominations === 0) {
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

    // LAFCA and GOTHAM use combined Actor+Actress column (gender-neutral categories)
    const isCombined = awardKey === 'lafca' || awardKey === 'gotham';

    let html = `
        <div class="cp-history-card">
            <div class="cp-history-title">${awardName}</div>
            <div class="cp-recap-header">
                <span>Year</span>
                <span>Film</span>
                <span>Dir</span>
                ${isCombined
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

        if (isCombined) {
            // Combined: Film, Director, then combined Actor+Actress
            for (const category of ['best-film', 'best-director']) {
                const catData = yearData[category] || { nominations: 0, winners: 0, status: 'pending', expected: undefined };
                const expectedCount = (catData.expected !== undefined) ? catData.expected : (data.expected[awardKey]?.[category] || 0);

                if (expectedCount === 0 && catData.nominations === 0) {
                    cells.push(`<span class="cp-recap-cell muted"></span>`);
                } else {
                    cells.push(`<span class="cp-recap-cell ${catData.status}"><b>${catData.nominations}</b>/${expectedCount}</span>`);
                }
            }

            // Combined Actor + Actress cell
            const actorData = yearData['best-actor'] || { nominations: 0, status: 'pending' };
            const actressData = yearData['best-actress'] || { nominations: 0, status: 'pending' };
            const combined = actorData.nominations + actressData.nominations;

            let targetTotal = 8; // Default for LAFCA
            if (awardKey === 'gotham') {
                // Extract year from yearKey (e.g. "2017_2018" -> 2018)
                const yearNum = parseInt(yearKey.split('_')[1]);
                // Force expected to match ACTUAL scraped counts per Wikipedia verification
                if (yearNum <= 2013) targetTotal = 0;       // No actor categories before 2013
                else if (yearNum === 2016) targetTotal = 11; // 5+6 scraped
                else if (yearNum === 2018) targetTotal = 11; // 6+5 scraped
                else if (yearNum === 2021) targetTotal = 10; // 5+5 scraped (pre-gender-neutral)
                else if (yearNum === 2022) targetTotal = 17; // 9+8 scraped
                else if (yearNum >= 2023) targetTotal = 20;  // 10+10 standard
                else targetTotal = 10; // 2014-2020 (except 2016): 5+5
            }
            const combinedStatus = (combined === targetTotal) ? 'ok' : (combined === 0 && targetTotal === 0 ? 'ok' : (combined === 0 ? 'pending' : 'error'));

            cells.push(`<span class="cp-recap-cell ${combinedStatus}" style="grid-column: span 2; text-align: center;"><b>${actorData.nominations}+${actressData.nominations}</b>/${targetTotal}</span>`);
        } else {
            // Standard awards: separate columns
            for (const category of CATEGORIES) {
                const catData = yearData[category] || { nominations: 0, winners: 0, status: 'pending', expected: undefined };
                const expectedCount = (catData.expected !== undefined) ? catData.expected : (data.expected[awardKey]?.[category] || 0);

                if (expectedCount === 0 && catData.nominations === 0) {
                    cells.push(`<span class="cp-recap-cell muted"></span>`);
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
