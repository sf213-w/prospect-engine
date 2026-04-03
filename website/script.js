// ── STATE ──────────────────────────────────────────
let state = {
    articles: [],
    contacts: [],
    filteredArticles: [],
    filteredContacts: [],
    mode: 'articles',
    sortCol: '',
    sortDir: 1,
    reportMeta: {},
};

// ── CLOCK ──────────────────────────────────────────
function updateClock() {
    const now = new Date();
    document.getElementById('clock').textContent =
        now.toUTCString().replace('GMT', 'UTC');
}
setInterval(updateClock, 1000);
updateClock();

// ── FILE LOADING ───────────────────────────────────
document.getElementById('file-json').addEventListener('change', e => {
    const file = e.target.files[0];
    if (file) loadJSON(file);
});

document.getElementById('file-csv').addEventListener('change', e => {
    const file = e.target.files[0];
    if (file) loadCSV(file);
});

// Drag and drop
const uploadArea = document.getElementById('upload-area');
uploadArea.addEventListener('dragover', e => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
});
uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('dragover'));
uploadArea.addEventListener('drop', e => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    const files = Array.from(e.dataTransfer.files);
    files.forEach(f => {
        if (f.name.endsWith('.json')) loadJSON(f);
        else if (f.name.endsWith('.csv')) loadCSV(f);
    });
});

function loadJSON(file) {
    const reader = new FileReader();
    reader.onload = e => {
        try {
            const data = JSON.parse(e.target.result);
            state.articles = data.articles || [];
            state.reportMeta = {
                generated: data.generated || '',
                lookback_days: data.lookback_days || 7,
                article_count: data.article_count || state.articles.length,
            };
            addFileBadge(file.name, 'json');
            onDataLoaded();
        } catch(err) {
            alert('Error parsing JSON: ' + err.message);
        }
    };
    reader.readAsText(file);
}

function loadCSV(file) {
    const reader = new FileReader();
    reader.onload = e => {
        try {
            state.contacts = parseCSV(e.target.result);
            addFileBadge(file.name, 'csv');
            onDataLoaded();
        } catch(err) {
            alert('Error parsing CSV: ' + err.message);
        }
    };
    reader.readAsText(file);
}

function parseCSV(text) {
    // Normalize line endings
    const normalized = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    const rows = parseCSVAll(normalized);
    if (rows.length < 2) return [];
    const headers = rows[0];
    const result = [];
    for (let i = 1; i < rows.length; i++) {
        const vals = rows[i];
        // Skip completely empty rows
        if (vals.length === 1 && vals[0] === '') continue;
        const obj = {};
        headers.forEach((h, idx) => { obj[h] = vals[idx] !== undefined ? vals[idx] : ''; });
        result.push(obj);
    }
    return result;
}

// Full RFC-4180 compliant CSV parser — handles quoted fields with commas and newlines
function parseCSVAll(text) {
    const rows = [];
    let row = [];
    let cur = '';
    let inQuote = false;
    let i = 0;

    while (i < text.length) {
        const ch = text[i];

        if (inQuote) {
            if (ch === '"') {
                // Peek ahead for escaped quote ""
                if (i + 1 < text.length && text[i + 1] === '"') {
                    cur += '"';
                    i += 2;
                } else {
                    // End of quoted field
                    inQuote = false;
                    i++;
                }
            } else {
                // Everything inside quotes, including commas and newlines, is literal
                cur += ch;
                i++;
            }
        } else {
            if (ch === '"') {
                inQuote = true;
                i++;
            } else if (ch === ',') {
                row.push(cur);
                cur = '';
                i++;
            } else if (ch === '\n') {
                row.push(cur);
                cur = '';
                rows.push(row);
                row = [];
                i++;
            } else {
                cur += ch;
                i++;
            }
        }
    }

    // Push the last field and row
    row.push(cur);
    if (row.some(v => v !== '')) rows.push(row);

    return rows;
}

function addFileBadge(name, type) {
    const existing = document.querySelector(`.file-badge[data-type="${type}"]`);
    if (existing) existing.remove();
    const badge = document.createElement('div');
    badge.className = 'file-badge';
    badge.dataset.type = type;
    badge.textContent = '✓ ' + name;
    document.getElementById('loaded-files').appendChild(badge);
}

// ── ON DATA LOADED ─────────────────────────────────
function onDataLoaded() {
    updateStats();
    populateSourceFilter();
    applyFilters();
    showPanels();
    setStatus('LIVE', true);
}

function showPanels() {
    ['stats-bar','filter-panel','results-panel'].forEach(id => {
        document.getElementById(id).style.display = '';
    });
}

function setStatus(text, active) {
    document.getElementById('status-text').textContent = text;
    const pulse = document.querySelector('.pulse');
    if (active) pulse.classList.add('active');
    else pulse.classList.remove('active');
}

// ── STATS ──────────────────────────────────────────
function updateStats() {
    const sources = new Set(state.articles.map(a => a.source).filter(Boolean));
    const emailCount = state.contacts.filter(c => c.emails_general && c.emails_general.trim()).length;

    animateNum('stat-articles', state.articles.length);
    animateNum('stat-sources', sources.size);
    animateNum('stat-contacts', state.contacts.length);
    animateNum('stat-emails', emailCount);

    const el = document.querySelector('#stat-period .stat-value');
    if (state.reportMeta.generated) {
        const d = new Date(state.reportMeta.generated);
        el.textContent = d.toLocaleDateString('en-US', { month:'short', day:'numeric', year:'numeric' });
    } else {
        el.textContent = '—';
    }
}

function animateNum(id, target) {
    const el = document.querySelector(`#${id} .stat-value`);
    let current = 0;
    const step = Math.max(1, Math.ceil(target / 20));
    const timer = setInterval(() => {
        current = Math.min(current + step, target);
        el.textContent = current;
        if (current >= target) clearInterval(timer);
    }, 30);
}

// ── SOURCE FILTER ──────────────────────────────────
function populateSourceFilter() {
    const sel = document.getElementById('filter-source');
    // Clear existing except first option
    while (sel.options.length > 1) sel.remove(1);

    const sources = [...new Set(state.articles.map(a => a.source).filter(Boolean))].sort();
    sources.forEach(s => {
        const opt = document.createElement('option');
        opt.value = s;
        opt.textContent = s;
        sel.appendChild(opt);
    });
}

// ── FILTER & SEARCH ────────────────────────────────
function applyFilters() {
    const search = document.getElementById('filter-search').value.toLowerCase().trim();
    const source = document.getElementById('filter-source').value;

    // Filter articles
    state.filteredArticles = state.articles.filter(a => {
        const text = `${a.title} ${a.source} ${a.summary} ${a.url}`.toLowerCase();
        const matchSearch = !search || fuzzy(text, search);
        const matchSource = !source || a.source === source;
        return matchSearch && matchSource;
    });

    // Filter contacts
    state.filteredContacts = state.contacts.filter(c => {
        const text = `${c.company_name} ${c.website} ${c.emails_general} ${c.emails_security} ${c.phones} ${c.addresses} ${c.article_title}`.toLowerCase();
        return !search || fuzzy(text, search);
    });

    renderCurrentView();
}

function fuzzy(text, search) {
    const words = search.trim().split(/\s+/).filter(w => w.length > 0);
    return words.every(word => {
        const escaped = word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp('\\b' + escaped, 'i');
        return regex.test(text);
    });
}

function resetFilters() {
    document.getElementById('filter-search').value = '';
    document.getElementById('filter-source').value = '';
    applyFilters();
}

// ── MODE SWITCHING ─────────────────────────────────
function setMode(mode) {
    state.mode = mode;
    document.getElementById('tab-articles').classList.toggle('active', mode === 'articles');
    document.getElementById('tab-contacts').classList.toggle('active', mode === 'contacts');
    document.getElementById('articles-view').style.display = mode === 'articles' ? '' : 'none';
    document.getElementById('contacts-view').style.display = mode === 'contacts' ? '' : 'none';
    renderCurrentView();
}

function renderCurrentView() {
    if (state.mode === 'articles') renderArticles();
    else renderContacts();
}

// ── RENDER ARTICLES ────────────────────────────────
function renderArticles() {
    const tbody = document.getElementById('articles-tbody');
    const data  = state.filteredArticles;
    document.getElementById('result-count').textContent = data.length + ' RECORDS';

    if (data.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5"><div class="empty-state">NO ARTICLES MATCH CURRENT FILTERS</div></td></tr>`;
        return;
    }

    tbody.innerHTML = data.map((a, i) => `
        <tr>
            <td class="td-date">${formatDate(a.published)}</td>
            <td class="td-title" onclick="openArticleModal(${i})">${escHtml(a.title)}</td>
            <td class="td-source"><span class="source-tag">${escHtml(a.source || '—')}</span></td>
            <td class="td-summary">${escHtml(a.summary || '—')}</td>
            <td class="td-link">${a.url ? `<a href="${escHtml(a.url)}" target="_blank" rel="noopener">OPEN ↗</a>` : '<span class="td-empty">—</span>'}</td>
        </tr>
    `).join('');
}

// ── RENDER CONTACTS ────────────────────────────────
function renderContacts() {
    const tbody = document.getElementById('contacts-tbody');
    const data  = state.filteredContacts;
    document.getElementById('result-count').textContent = data.length + ' RECORDS';

    if (data.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7"><div class="empty-state">NO CONTACTS FOUND — LOAD A breach_contacts_*.csv FILE</div></td></tr>`;
        return;
    }

    tbody.innerHTML = data.map((c, i) => `
        <tr>
            <td class="td-company" onclick="openContactModal(${i})">${escHtml(c.company_name || '—')}</td>
            <td class="td-website">${c.website ? `<a href="${escHtml(c.website)}" target="_blank" rel="noopener">${escHtml(stripProtocol(c.website))}</a>` : '<span class="td-empty">—</span>'}</td>
            <td class="td-email">${formatEmails(c.emails_general)}</td>
            <td class="td-email">${formatEmails(c.emails_security)}</td>
            <td class="td-phone">${escHtml(c.phones || '') || '<span class="td-empty">—</span>'}</td>
            <td style="font-size:11px;color:var(--text-dim);max-width:200px">${escHtml(c.addresses || '') || '<span class="td-empty">—</span>'}</td>
            <td style="font-size:11px;max-width:220px">${c.article_url
                ? `<a href="${escHtml(c.article_url)}" target="_blank" rel="noopener" style="color:var(--accent);text-decoration:none;font-family:var(--mono);font-size:10px">${escHtml((c.article_title||'').slice(0,60))}${(c.article_title||'').length > 60 ? '…' : ''}</a>`
                : '<span class="td-empty">—</span>'
            }</td>
        </tr>
    `).join('');
}

// ── SORTING ────────────────────────────────────────
function sortTable(type, col) {
    if (state.sortCol === col) state.sortDir *= -1;
    else { state.sortCol = col; state.sortDir = 1; }

    const arr = type === 'articles' ? state.filteredArticles : state.filteredContacts;
    arr.sort((a, b) => {
        const va = (a[col] || '').toLowerCase();
        const vb = (b[col] || '').toLowerCase();
        if (va < vb) return -state.sortDir;
        if (va > vb) return  state.sortDir;
        return 0;
    });

    renderCurrentView();
}

// ── MODALS ─────────────────────────────────────────
function openArticleModal(idx) {
    const a = state.filteredArticles[idx];
    if (!a) return;
    document.getElementById('modal-title').textContent = 'BREACH ARTICLE // DETAIL';
    document.getElementById('modal-body').innerHTML = `
        <div class="modal-field">
            <div class="modal-field-label">TITLE</div>
            <div class="modal-field-value" style="font-size:17px;font-weight:700;color:var(--text)">${escHtml(a.title)}</div>
        </div>
        <div class="modal-field">
            <div class="modal-field-label">SOURCE</div>
            <div class="modal-field-value"><span class="source-tag">${escHtml(a.source || '—')}</span></div>
        </div>
        <div class="modal-field">
            <div class="modal-field-label">PUBLISHED</div>
            <div class="modal-field-value" style="font-family:var(--mono)">${escHtml(a.published || '—')}</div>
        </div>
        <div class="modal-field">
            <div class="modal-field-label">SUMMARY</div>
            <div class="modal-field-value">${escHtml(a.summary || '—')}</div>
        </div>
        <div class="modal-field">
            <div class="modal-field-label">URL</div>
            <div class="modal-field-value">${a.url ? `<a href="${escHtml(a.url)}" target="_blank" rel="noopener">${escHtml(a.url)}</a>` : '—'}</div>
        </div>
    `;
    document.getElementById('modal-overlay').classList.add('open');
}

function openContactModal(idx) {
    const c = state.filteredContacts[idx];
    if (!c) return;
    document.getElementById('modal-title').textContent = 'COMPANY CONTACT // DETAIL';
    document.getElementById('modal-body').innerHTML = `
        <div class="modal-field">
            <div class="modal-field-label">COMPANY</div>
            <div class="modal-field-value" style="font-size:20px;font-weight:700;color:var(--text)">${escHtml(c.company_name || '—')}</div>
        </div>
        <div class="modal-field">
            <div class="modal-field-label">WEBSITE</div>
            <div class="modal-field-value">${c.website ? `<a href="${escHtml(c.website)}" target="_blank" rel="noopener">${escHtml(c.website)}</a>` : '—'}</div>
        </div>
        <div class="modal-field">
            <div class="modal-field-label">GENERAL EMAIL</div>
            <div class="modal-field-value" style="font-family:var(--mono)">${formatEmailsFull(c.emails_general)}</div>
        </div>
        <div class="modal-field">
            <div class="modal-field-label">SECURITY / ABUSE EMAIL</div>
            <div class="modal-field-value" style="font-family:var(--mono)">${formatEmailsFull(c.emails_security)}</div>
        </div>
        <div class="modal-field">
            <div class="modal-field-label">PHONE</div>
            <div class="modal-field-value" style="font-family:var(--mono)">${escHtml(c.phones || '—')}</div>
        </div>
        <div class="modal-field">
            <div class="modal-field-label">ADDRESS</div>
            <div class="modal-field-value">${escHtml(c.addresses || '—')}</div>
        </div>
        <div class="modal-field">
            <div class="modal-field-label">RELATED BREACH ARTICLE</div>
            <div class="modal-field-value">${c.article_url
                ? `<a href="${escHtml(c.article_url)}" target="_blank" rel="noopener">${escHtml(c.article_title || c.article_url)}</a>`
                : escHtml(c.article_title || '—')
            }</div>
        </div>
        <div class="modal-field">
            <div class="modal-field-label">BREACH SUMMARY</div>
            <div class="modal-field-value">${escHtml(c.summary || '—')}</div>
        </div>
        <div class="modal-field">
            <div class="modal-field-label">REPORTED</div>
            <div class="modal-field-value" style="font-family:var(--mono)">${escHtml(c.published || '—')}</div>
        </div>
    `;
    document.getElementById('modal-overlay').classList.add('open');
}

function closeModal() {
    document.getElementById('modal-overlay').classList.remove('open');
}

document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeModal();
});

// ── EXPORT ─────────────────────────────────────────
function exportFiltered() {
    if (state.mode === 'articles') {
        const rows = state.filteredArticles;
        if (!rows.length) return alert('No articles to export.');
        const headers = ['published','title','source','summary','url'];
        downloadCSV(headers, rows.map(r => headers.map(h => r[h]||'')), 'filtered_articles');
    } else {
        const rows = state.filteredContacts;
        if (!rows.length) return alert('No contacts to export.');
        const headers = ['company_name','website','emails_general','emails_security','phones','addresses','article_title','published','article_url'];
        downloadCSV(headers, rows.map(r => headers.map(h => r[h]||'')), 'filtered_contacts');
    }
}

function downloadCSV(headers, rows, name) {
    const csvContent = [headers, ...rows]
        .map(row => row.map(v => `"${String(v).replace(/"/g,'""')}"`).join(','))
        .join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${name}_${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
}

// ── HELPERS ────────────────────────────────────────
function escHtml(str) {
    return String(str)
        .replace(/&/g,'&amp;')
        .replace(/</g,'&lt;')
        .replace(/>/g,'&gt;')
        .replace(/"/g,'&quot;');
}

function formatDate(str) {
    if (!str) return '—';
    return str.replace(' UTC','').replace('T',' ').slice(0,16);
}

function stripProtocol(url) {
    return url.replace(/^https?:\/\/(www\.)?/,'').replace(/\/$/,'');
}

function formatEmails(emailStr) {
    if (!emailStr || !emailStr.trim()) return '<span class="td-empty">—</span>';
    return emailStr.split(',').map(e => e.trim()).filter(Boolean).map(e =>
        `<a href="mailto:${escHtml(e)}">${escHtml(e)}</a>`
    ).join('<br>');
}

function formatEmailsFull(emailStr) {
    if (!emailStr || !emailStr.trim()) return '—';
    return emailStr.split(',').map(e => e.trim()).filter(Boolean).map(e =>
        `<a href="mailto:${escHtml(e)}">${escHtml(e)}</a>`
    ).join('<br>');
}
