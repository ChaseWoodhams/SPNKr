// Global variables
let isSearching = false;
let activePlaylistKey = null;

// DOM elements
const gamertagInput = document.getElementById('gamertagInput');
const searchBtn = document.getElementById('searchBtn');
const btnText = document.getElementById('btnText');
const spinner = document.getElementById('spinner');
const errorMessage = document.getElementById('errorMessage');
const results = document.getElementById('results');
const csrSection = document.getElementById('csrSection'); // kept for back-compat
const csrCards = document.getElementById('csrCards');      // kept for back-compat

// New layout elements
const playlistTabs = document.getElementById('playlistTabs');
const csrMetrics = document.getElementById('csrMetrics');

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    gamertagInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            searchPlayer();
        }
    });

    gamertagInput.addEventListener('input', function() {
        hideError();
    });
});

// Main search function
async function searchPlayer() {
    const gamertag = gamertagInput.value.trim();

    if (!gamertag) {
        showError('Please enter a gamertag');
        return;
    }

    if (isSearching) return;

    setLoadingState(true);
    hideError();
    hideResults();

    try {
        const response = await fetch('/api/service-record', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ gamertag })
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);

        displayResults(data);

    } catch (error) {
        console.error('Error fetching service record:', error);
        showError(`Error: ${error.message}`);
    } finally {
        setLoadingState(false);
    }
}

function setLoadingState(loading) {
    isSearching = loading;
    searchBtn.disabled = loading;
    if (loading) { btnText.classList.add('hidden'); spinner.classList.remove('hidden'); }
    else { btnText.classList.remove('hidden'); spinner.classList.add('hidden'); }
}

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.classList.remove('hidden');
}
function hideError() { errorMessage.classList.add('hidden'); }

function hideResults() {
    results.classList.add('hidden');
    if (csrMetrics) csrMetrics.classList.add('hidden');
}

function displayResults(data) {
    // Player header
    document.getElementById('playerName').textContent = data.player.gamertag;
    document.getElementById('playerXuid').textContent = `XUID: ${data.player.xuid}`;

    // Match record
    document.getElementById('totalMatches').textContent = formatNumber(data.service_record.matches_completed);
    document.getElementById('wins').textContent = formatNumber(data.service_record.wins);
    document.getElementById('losses').textContent = formatNumber(data.service_record.losses);
    document.getElementById('ties').textContent = formatNumber(data.service_record.ties);
    const winRate = data.service_record.matches_completed > 0 ? (data.service_record.wins / data.service_record.matches_completed * 100).toFixed(1) : '0.0';
    document.getElementById('winRate').textContent = `${winRate}%`;
    document.getElementById('timePlayed').textContent = formatTimePlayed(data.service_record.time_played);

    // Combat
    const coreStats = data.service_record.core_stats;
    document.getElementById('kills').textContent = formatNumber(coreStats.kills);
    document.getElementById('deaths').textContent = formatNumber(coreStats.deaths);
    document.getElementById('assists').textContent = formatNumber(coreStats.assists);
    const kdRatio = coreStats.deaths > 0 ? (coreStats.kills / coreStats.deaths).toFixed(2) : coreStats.kills.toFixed(2);
    document.getElementById('kdRatio').textContent = kdRatio;
    const accuracy = coreStats.shots_fired > 0 ? (coreStats.shots_hit / coreStats.shots_fired * 100).toFixed(1) : '0.0';
    document.getElementById('accuracy').textContent = `${accuracy}%`;
    document.getElementById('damageDealt').textContent = formatNumber(coreStats.damage_dealt);
    document.getElementById('roundsWon').textContent = formatNumber(coreStats.rounds_won);
    document.getElementById('roundsLost').textContent = formatNumber(coreStats.rounds_lost);
    document.getElementById('roundsTied').textContent = formatNumber(coreStats.rounds_tied);

    // CSR data
    renderCSR(data.csr_data);

    // Show
    results.classList.remove('hidden');
    results.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderCSR(csrData) {
    if (!csrData || Object.keys(csrData).length === 0) {
        if (csrMetrics) {
            csrMetrics.classList.remove('hidden');
            document.getElementById('metricCurrent').textContent = '—';
            document.getElementById('metricSeason').textContent = '—';
            document.getElementById('metricAllTime').textContent = '—';
            document.getElementById('metricAverage').textContent = '—';
            document.getElementById('metricCurrentTier').textContent = 'Unranked';
            document.getElementById('metricSeasonTier').textContent = '—';
            document.getElementById('metricAllTimeTier').textContent = '—';
            document.getElementById('metricAverageTier').textContent = '—';
        }
        return;
    }

    // Build tabs
    playlistTabs.innerHTML = '';
    const entries = Object.entries(csrData);
    entries.forEach(([key]) => {
        const tab = document.createElement('div');
        tab.className = 'tab';
        tab.textContent = displayNameForPlaylist(key);
        tab.onclick = () => activatePlaylist(key, csrData[key]);
        playlistTabs.appendChild(tab);
    });
    playlistTabs.classList.remove('hidden');

    // Activate first
    const [firstKey, firstVal] = entries[0];
    activatePlaylist(firstKey, firstVal);
}

function activatePlaylist(key, data) {
    activePlaylistKey = key;
    // set active tab
    [...playlistTabs.children].forEach(el => {
        el.classList.toggle('active', el.textContent === displayNameForPlaylist(key));
    });

    // Fill metrics
    const current = data.current;
    const season = data.season_max;
    const allTime = data.all_time_max;

    setMetric('metricCurrent', current?.value, current?.formatted_rank);
    setMetric('metricSeason', season?.value, season?.formatted_rank);
    setMetric('metricAllTime', allTime?.value, allTime?.formatted_rank);

    // Average (simple mean of available values)
    const values = [current?.value, season?.value, allTime?.value].filter(v => typeof v === 'number');
    const avg = values.length ? Math.round(values.reduce((a,b)=>a+b,0)/values.length) : null;
    document.getElementById('metricAverage').textContent = avg ?? '—';
    document.getElementById('metricAverageTier').textContent = avg ? tierLabel(avg) : '—';

    csrMetrics.classList.remove('hidden');
}

function setMetric(baseId, value, label) {
    const valueEl = document.getElementById(baseId);
    const subEl = document.getElementById(baseId.replace('metric', 'metric') + 'Tier');
    valueEl.textContent = value ?? '—';
    subEl.textContent = label ?? 'Unranked';
}

function displayNameForPlaylist(key) {
    const map = {
        ranked_arena: 'Ranked Arena',
        ranked_slayer: 'Ranked Slayer',
        ranked_crossplay: 'Ranked Crossplay'
    };
    return map[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function tierLabel(csr) {
    const tiers = ['Bronze','Silver','Gold','Platinum','Diamond','Onyx'];
    const idx = Math.min(Math.floor(csr/300), 5);
    return `${tiers[idx]}`;
}

// Utilities
function formatNumber(num) { if (num === null || num === undefined) return 'N/A'; return num.toLocaleString(); }
function formatTimePlayed(timeStr) {
    if (!timeStr) return 'N/A';
    const m = timeStr.match(/(\d+)\s+days?,\s+(\d+):(\d+):(\d+)/);
    if (m) {
        const d = parseInt(m[1]); const h=parseInt(m[2]); const mi=parseInt(m[3]);
        let out=''; if (d>0) out+=`${d}d `; if (h>0) out+=`${h}h `; if (mi>0) out+=`${mi}m`; return out||'< 1m';
    }
    return timeStr;
}

// Visual feedback ripple
function addVisualFeedback() {
    searchBtn.addEventListener('click', function(e) {
        if (this.disabled) return;
        const ripple = document.createElement('span');
        const rect = this.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = e.clientX - rect.left - size/2;
        const y = e.clientY - rect.top - size/2;
        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = x + 'px';
        ripple.style.top = y + 'px';
        ripple.classList.add('ripple');
        this.appendChild(ripple);
        setTimeout(()=>ripple.remove(), 600);
    });
}

document.addEventListener('DOMContentLoaded', addVisualFeedback);
