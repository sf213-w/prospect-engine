// ─────────────────────────────────────────────────────────────────────────────
// PROSPECTOR — script.js
// Single source of truth. No logic in index.html.
// ─────────────────────────────────────────────────────────────────────────────

// ── STATE ────────────────────────────────────────────────────────────────────
const S = {
    articles:         [],
    contacts:         [],
    filteredArticles: [],
    filteredContacts: [],
    mode:             'articles',
    sortCol:          '',
    sortDir:          1,
    reportMeta:       {},
};

// ── CLOCK ────────────────────────────────────────────────────────────────────
function tickClock() {
    const el = document.getElementById('clock');
    if (el) el.textContent = new Date().toUTCString().replace('GMT', 'UTC');
}
setInterval(tickClock, 1000);
tickClock();

// ── FILE INPUT LISTENERS ─────────────────────────────────────────────────────
document.getElementById('file-json').addEventListener('change', function() {
    if (this.files[0]) readJSON(this.files[0]);
    this.value = '';
});
document.getElementById('file-csv').addEventListener('change', function() {
    if (this.files[0]) readCSV(this.files[0]);
    this.value = '';
});

// ── DRAG AND DROP ────────────────────────────────────────────────────────────
const dropZone = document.getElementById('drop-zone');
dropZone.addEventListener('dragover', function(e) {
    e.preventDefault();
    this.classList.add('drag-over');
});
dropZone.addEventListener('dragleave', function() {
    this.classList.remove('drag-over');
});
dropZone.addEventListener('drop', function(e) {
    e.preventDefault();
    this.classList.remove('drag-over');
    Array.from(e.dataTransfer.files).forEach(function(f) {
        if (f.name.endsWith('.json')) readJSON(f);
        else if (f.name.endsWith('.csv')) readCSV(f);
    });
});

// ── FILE READERS ─────────────────────────────────────────────────────────────
function readJSON(file) {
    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const data = JSON.parse(e.target.result);
            S.articles   = data.articles || [];
            S.reportMeta = {
                generated:     data.generated || '',
                lookback_days: data.lookback_days || 7,
            };
            showBadge(file.name, 'json');
            onDataLoaded();
        } catch (err) {
            alert('Error parsing JSON file: ' + err.message);
        }
    };
    reader.readAsText(file);
}

function readCSV(file) {
    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            S.contacts = parseCSV(e.target.result);
            showBadge(file.name, 'csv');
            onDataLoaded();
        } catch (err) {
            alert('Error parsing CSV file: ' + err.message);
        }
    };
    reader.readAsText(file);
}

// ── CSV PARSER (RFC-4180) ─────────────────────────────────────────────────────
function parseCSV(raw) {
    const text = raw.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    const allRows = [];
    let row = [], cur = '', inQ = false, i = 0;
    while (i < text.length) {
        const ch = text[i];
        if (inQ) {
            if (ch === '"' && text[i+1] === '"') { cur += '"'; i += 2; }
            else if (ch === '"')                 { inQ = false; i++; }
            else                                 { cur += ch; i++; }
        } else {
            if      (ch === '"') { inQ = true; i++; }
            else if (ch === ',') { row.push(cur); cur = ''; i++; }
            else if (ch === '\n'){ row.push(cur); cur = ''; allRows.push(row); row = []; i++; }
            else                 { cur += ch; i++; }
        }
    }
    row.push(cur);
    if (row.some(function(v) { return v !== ''; })) allRows.push(row);

    if (allRows.length < 2) return [];
    const headers = allRows[0];
    const result  = [];
    for (let r = 1; r < allRows.length; r++) {
        const vals = allRows[r];
        if (vals.length === 1 && vals[0] === '') continue;
        const obj = {};
        headers.forEach(function(h, idx) { obj[h] = vals[idx] !== undefined ? vals[idx] : ''; });
        result.push(obj);
    }
    return result;
}

// ── BADGE ────────────────────────────────────────────────────────────────────
function showBadge(name, type) {
    const container = document.getElementById('loaded-files');
    const old = container.querySelector('[data-type="' + type + '"]');
    if (old) old.remove();
    const el = document.createElement('div');
    el.dataset.type = type;
    el.textContent  = '✓ ' + name;
    el.style.cssText = 'font-size:11px;letter-spacing:0.05em;padding:3px 12px;border-radius:4px;border:1px solid #166534;color:#4ade80;background:rgba(6,78,59,0.2)';
    container.appendChild(el);
}

// ── ON DATA LOADED ────────────────────────────────────────────────────────────
function onDataLoaded() {
    updateStats();
    populateSources();
    applyFilters();
    showPanels();
    setLive();
}

function setLive() {
    const dot  = document.getElementById('status-dot');
    const text = document.getElementById('status-text');
    dot.style.background  = '#34d399';
    dot.style.boxShadow   = '0 0 8px #34d399';
    dot.classList.add('pulse');
    text.textContent      = 'LIVE';
    text.style.color      = '#34d399';
}

function showPanels() {
    ['stats-bar', 'filter-panel', 'results-panel'].forEach(function(id) {
        const el = document.getElementById(id);
        el.style.removeProperty('display');
        el.style.display = 'block';
    });
    if (S.contacts.length > 0) {
        document.getElementById('ollama-panel').style.display = 'block';
    }
}

// ── STATS ────────────────────────────────────────────────────────────────────
function updateStats() {
    const sources    = new Set(S.articles.map(function(a) { return a.source; }).filter(Boolean));
    const emailCount = S.contacts.filter(function(c) { return c.emails_general && c.emails_general.trim(); }).length;

    countUp('stat-articles', S.articles.length);
    countUp('stat-sources',  sources.size);
    countUp('stat-contacts', S.contacts.length);
    countUp('stat-emails',   emailCount);

    const el = document.querySelector('#stat-period .stat-val');
    if (el) {
        if (S.reportMeta.generated) {
            const d = new Date(S.reportMeta.generated);
            el.textContent = d.toLocaleDateString('en-US', { month:'short', day:'numeric', year:'numeric' });
        } else {
            el.textContent = '—';
        }
    }
}

function countUp(id, target) {
    const el = document.querySelector('#' + id + ' .stat-val');
    if (!el) return;
    let n = 0;
    const step  = Math.max(1, Math.ceil(target / 20));
    const timer = setInterval(function() {
        n = Math.min(n + step, target);
        el.textContent = n;
        if (n >= target) clearInterval(timer);
    }, 30);
}

// ── SOURCE DROPDOWN ───────────────────────────────────────────────────────────
function populateSources() {
    const sel = document.getElementById('filter-source');
    while (sel.options.length > 1) sel.remove(1);
    const sources = Array.from(new Set(S.articles.map(function(a) { return a.source; }).filter(Boolean))).sort();
    sources.forEach(function(s) {
        const opt = document.createElement('option');
        opt.value = s; opt.textContent = s;
        sel.appendChild(opt);
    });
}

// ── FILTERS ───────────────────────────────────────────────────────────────────
function applyFilters() {
    const q      = (document.getElementById('filter-search').value || '').toLowerCase().trim();
    const source = document.getElementById('filter-source').value;

    S.filteredArticles = S.articles.filter(function(a) {
        const txt = (a.title + ' ' + a.source + ' ' + a.summary + ' ' + a.url).toLowerCase();
        return (!q || matchWords(txt, q)) && (!source || a.source === source);
    });

    S.filteredContacts = S.contacts.filter(function(c) {
        const txt = (c.company_name + ' ' + c.website + ' ' + c.emails_general + ' ' + c.emails_security + ' ' + c.phones + ' ' + c.addresses + ' ' + c.article_title).toLowerCase();
        return !q || matchWords(txt, q);
    });

    renderView();
}

function matchWords(text, query) {
    return query.trim().split(/\s+/).every(function(w) {
        if (!w) return true;
        return new RegExp('\\b' + w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i').test(text);
    });
}

function resetFilters() {
    document.getElementById('filter-search').value = '';
    document.getElementById('filter-source').value = '';
    applyFilters();
}

// ── MODE SWITCHING ────────────────────────────────────────────────────────────
function setMode(mode) {
    S.mode = mode;
    document.getElementById('tab-articles').className = (mode === 'articles' ? 'tab-on' : 'tab-off') + ' text-xs tracking-wider px-3 py-2 border rounded transition-all';
    document.getElementById('tab-contacts').className = (mode === 'contacts' ? 'tab-on' : 'tab-off') + ' text-xs tracking-wider px-3 py-2 border rounded transition-all';
    document.getElementById('articles-view').style.display = mode === 'articles' ? '' : 'none';
    document.getElementById('contacts-view').style.display = mode === 'contacts' ? '' : 'none';
    renderView();
}

function renderView() {
    if (S.mode === 'articles') renderArticles();
    else renderContacts();
}

// ── RENDER ARTICLES ───────────────────────────────────────────────────────────
function renderArticles() {
    const tbody = document.getElementById('articles-tbody');
    const data  = S.filteredArticles;
    document.getElementById('result-count').textContent = data.length + ' RECORDS';

    if (!data.length) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:48px;color:#475569;font-size:11px;letter-spacing:0.1em">NO ARTICLES MATCH CURRENT FILTERS</td></tr>';
        return;
    }

    tbody.innerHTML = data.map(function(a, i) {
        return '<tr style="border-bottom:1px solid #1e293b">'
            + '<td style="padding:10px 16px;font-size:11px;color:#64748b;white-space:nowrap;vertical-align:top">' + esc(fmtDate(a.published)) + '</td>'
            + '<td style="padding:10px 16px;vertical-align:top;max-width:320px">'
            +   '<span style="color:#e2e8f0;font-size:13px;cursor:pointer;transition:color 0.15s" '
            +   'onmouseover="this.style.color=\'#fbbf24\'" onmouseout="this.style.color=\'#e2e8f0\'" '
            +   'onclick="openArticleModal(' + i + ')">' + esc(a.title) + '</span>'
            + '</td>'
            + '<td style="padding:10px 16px;vertical-align:top">'
            +   '<span style="font-size:10px;color:#64748b;border:1px solid #1e293b;padding:2px 8px;border-radius:4px">' + esc(a.source || '—') + '</span>'
            + '</td>'
            + '<td style="padding:10px 16px;font-size:11px;color:#64748b;vertical-align:top;max-width:340px;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical">' + esc(a.summary || '—') + '</td>'
            + '<td style="padding:10px 16px;vertical-align:top">'
            + (a.url
                ? '<a href="' + esc(a.url) + '" target="_blank" rel="noopener" '
                +   'style="font-size:10px;color:#f59e0b;border:1px solid rgba(245,158,11,0.3);padding:3px 8px;border-radius:4px;text-decoration:none;white-space:nowrap" '
                +   'onmouseover="this.style.background=\'rgba(245,158,11,0.1)\'" onmouseout="this.style.background=\'transparent\'">OPEN ↗</a>'
                : '<span style="color:#1e293b">—</span>')
            + '</td>'
            + '</tr>';
    }).join('');
}

// ── RENDER CONTACTS ───────────────────────────────────────────────────────────
function renderContacts() {
    const tbody = document.getElementById('contacts-tbody');
    const data  = S.filteredContacts;
    document.getElementById('result-count').textContent = data.length + ' RECORDS';

    if (!data.length) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:48px;color:#475569;font-size:11px;letter-spacing:0.1em">NO CONTACTS — LOAD A breach_contacts_*.csv FILE</td></tr>';
        return;
    }

    tbody.innerHTML = data.map(function(c, i) {
        return '<tr id="crow-' + i + '" style="border-bottom:1px solid #1e293b">'
            + '<td style="padding:10px 16px;vertical-align:top;white-space:nowrap">'
            +   '<span style="color:#f1f5f9;font-size:13px;font-weight:600;cursor:pointer" '
            +   'onmouseover="this.style.color=\'#fbbf24\'" onmouseout="this.style.color=\'#f1f5f9\'" '
            +   'onclick="openContactModal(' + i + ')">' + esc(c.company_name || '—') + '</span>'
            + '</td>'
            + '<td style="padding:10px 16px;vertical-align:top">'
            + (c.website
                ? '<a href="' + esc(c.website) + '" target="_blank" rel="noopener" style="font-size:11px;color:#34d399;text-decoration:none" onmouseover="this.style.textDecoration=\'underline\'" onmouseout="this.style.textDecoration=\'none\'">' + esc(stripProto(c.website)) + '</a>'
                : '<span style="color:#1e293b">—</span>')
            + '</td>'
            + '<td id="ce-' + i + '" style="padding:10px 16px;vertical-align:top;font-size:11px">' + fmtEmails(c.emails_general) + '</td>'
            + '<td id="cs-' + i + '" style="padding:10px 16px;vertical-align:top;font-size:11px">' + fmtEmails(c.emails_security) + '</td>'
            + '<td id="cp-' + i + '" style="padding:10px 16px;vertical-align:top;font-size:11px;color:#94a3b8;white-space:nowrap">' + (esc(c.phones || '') || '<span style="color:#1e293b">—</span>') + '</td>'
            + '<td id="ca-' + i + '" style="padding:10px 16px;vertical-align:top;font-size:11px;color:#64748b;max-width:180px">' + (esc(c.addresses || '') || '<span style="color:#1e293b">—</span>') + '</td>'
            + '<td style="padding:10px 16px;vertical-align:top;max-width:200px">'
            + (c.article_url
                ? '<a href="' + esc(c.article_url) + '" target="_blank" rel="noopener" style="font-size:10px;color:rgba(245,158,11,0.6);text-decoration:none" onmouseover="this.style.color=\'#f59e0b\'" onmouseout="this.style.color=\'rgba(245,158,11,0.6)\'">' + esc((c.article_title || '').slice(0, 55)) + ((c.article_title || '').length > 55 ? '…' : '') + '</a>'
                : '<span style="color:#1e293b">—</span>')
            + '</td>'
            + '<td style="padding:10px 16px;vertical-align:top">'
            +   '<button id="eb-' + i + '" onclick="enrichOne(' + i + ')" class="enrich-row-btn" '
            +   'style="font-size:10px;color:#64748b;border:1px solid #334155;padding:3px 10px;border-radius:4px;background:transparent;cursor:pointer;font-family:inherit;letter-spacing:0.05em;transition:all 0.15s">ENRICH</button>'
            + '</td>'
            + '</tr>';
    }).join('');
}

// ── SORTING ───────────────────────────────────────────────────────────────────
function sortBy(type, col) {
    if (S.sortCol === col) S.sortDir *= -1;
    else { S.sortCol = col; S.sortDir = 1; }
    const arr = type === 'articles' ? S.filteredArticles : S.filteredContacts;
    arr.sort(function(a, b) {
        const va = (a[col] || '').toLowerCase();
        const vb = (b[col] || '').toLowerCase();
        return va < vb ? -S.sortDir : va > vb ? S.sortDir : 0;
    });
    renderView();
}

// ── MODALS ────────────────────────────────────────────────────────────────────
function openArticleModal(idx) {
    const a = S.filteredArticles[idx];
    if (!a) return;
    document.getElementById('modal-title').textContent = 'BREACH ARTICLE // DETAIL';
    document.getElementById('modal-body').innerHTML =
        mField('TITLE',     '<span style="color:#f1f5f9;font-size:15px;font-weight:600">' + esc(a.title) + '</span>')
      + mField('SOURCE',    '<span style="font-size:10px;color:#64748b;border:1px solid #1e293b;padding:2px 8px;border-radius:4px">' + esc(a.source || '—') + '</span>')
      + mField('PUBLISHED', '<span style="color:#64748b">' + esc(a.published || '—') + '</span>')
      + mField('SUMMARY',   esc(a.summary || '—'))
      + mField('URL',       a.url ? '<a href="' + esc(a.url) + '" target="_blank" style="color:#f59e0b;word-break:break-all">' + esc(a.url) + '</a>' : '—');
    showModal();
}

function openContactModal(idx) {
    const c = S.filteredContacts[idx];
    if (!c) return;
    document.getElementById('modal-title').textContent = 'COMPANY CONTACT // DETAIL';
    document.getElementById('modal-body').innerHTML =
        mField('COMPANY',        '<span style="color:#f1f5f9;font-size:18px;font-weight:700;font-family:Syne,sans-serif">' + esc(c.company_name || '—') + '</span>')
      + mField('WEBSITE',        c.website ? '<a href="' + esc(c.website) + '" target="_blank" style="color:#34d399">' + esc(c.website) + '</a>' : '—')
      + mField('GENERAL EMAIL',  fmtEmailsFull(c.emails_general))
      + mField('SECURITY EMAIL', fmtEmailsFull(c.emails_security))
      + mField('PHONE',          esc(c.phones || '—'))
      + mField('ADDRESS',        esc(c.addresses || '—'))
      + mField('BREACH ARTICLE', c.article_url ? '<a href="' + esc(c.article_url) + '" target="_blank" style="color:#f59e0b">' + esc(c.article_title || c.article_url) + '</a>' : esc(c.article_title || '—'))
      + mField('BREACH SUMMARY', esc(c.summary || '—'))
      + mField('REPORTED',       esc(c.published || '—'));
    showModal();
}

function mField(label, valueHtml) {
    return '<div style="padding:12px 0;border-bottom:1px solid #1e293b">'
        + '<div style="font-size:10px;color:#475569;letter-spacing:0.12em;margin-bottom:5px">' + label + '</div>'
        + '<div style="font-size:13px;color:#cbd5e1;line-height:1.6">' + valueHtml + '</div>'
        + '</div>';
}

function showModal() {
    const o = document.getElementById('modal-overlay');
    o.style.display = 'flex';
}

function closeModal() {
    document.getElementById('modal-overlay').style.display = 'none';
}

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') closeModal();
});

// ── EXPORT ────────────────────────────────────────────────────────────────────
function exportFiltered() {
    if (S.mode === 'articles') {
        const cols = ['published','title','source','summary','url'];
        if (!S.filteredArticles.length) return alert('No articles to export.');
        dlCSV(cols, S.filteredArticles.map(function(r) { return cols.map(function(c) { return r[c]||''; }); }), 'filtered_articles');
    } else {
        const cols = ['company_name','website','emails_general','emails_security','phones','addresses','article_title','published','article_url'];
        if (!S.filteredContacts.length) return alert('No contacts to export.');
        dlCSV(cols, S.filteredContacts.map(function(r) { return cols.map(function(c) { return r[c]||''; }); }), 'filtered_contacts');
    }
}

function dlCSV(headers, rows, name) {
    const content = [headers].concat(rows).map(function(row) {
        return row.map(function(v) { return '"' + String(v).replace(/"/g, '""') + '"'; }).join(',');
    }).join('\n');
    const a   = document.createElement('a');
    a.href    = URL.createObjectURL(new Blob([content], { type:'text/csv;charset=utf-8;' }));
    a.download = name + '_' + new Date().toISOString().slice(0,10) + '.csv';
    a.click();
    URL.revokeObjectURL(a.href);
}

// ── HELPERS ───────────────────────────────────────────────────────────────────
function esc(str) {
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function fmtDate(str) {
    if (!str) return '—';
    return str.replace(' UTC','').replace('T',' ').slice(0,16);
}

function stripProto(url) {
    return url.replace(/^https?:\/\/(www\.)?/,'').replace(/\/$/,'');
}

function fmtEmails(str) {
    if (!str || !str.trim()) return '<span style="color:#1e293b">—</span>';
    return str.split(',').map(function(e) { return e.trim(); }).filter(Boolean).map(function(e) {
        return '<a href="mailto:' + esc(e) + '" style="color:#f59e0b;text-decoration:none" onmouseover="this.style.textDecoration=\'underline\'" onmouseout="this.style.textDecoration=\'none\'">' + esc(e) + '</a>';
    }).join('<br>');
}

function fmtEmailsFull(str) {
    if (!str || !str.trim()) return '<span style="color:#475569">—</span>';
    return str.split(',').map(function(e) { return e.trim(); }).filter(Boolean).map(function(e) {
        return '<a href="mailto:' + esc(e) + '" style="color:#f59e0b;text-decoration:none" onmouseover="this.style.textDecoration=\'underline\'" onmouseout="this.style.textDecoration=\'none\'">' + esc(e) + '</a>';
    }).join('<br>');
}

// ── OLLAMA ────────────────────────────────────────────────────────────────────
function ollamaBase()  { return (document.getElementById('ollama-url').value   || 'http://localhost:11434').replace(/\/$/, ''); }
function ollamaModel() { return  document.getElementById('ollama-model').value || 'llama3.2'; }

function ollamaLog(msg, color) {
    const log  = document.getElementById('ollama-log');
    const line = document.createElement('div');
    line.style.color = color || '#64748b';
    line.textContent = '[' + new Date().toLocaleTimeString() + '] ' + msg;
    log.appendChild(line);
    log.scrollTop = log.scrollHeight;
}

async function testOllama() {
    ollamaLog('Testing connection…', '#94a3b8');
    try {
        const r = await fetch(ollamaBase() + '/api/tags');
        if (!r.ok) throw new Error('HTTP ' + r.status);
        const d = await r.json();
        const models = (d.models || []).map(function(m) { return m.name; }).join(', ');
        ollamaLog('✓ Connected. Models: ' + (models || 'none'), '#34d399');
    } catch(e) {
        ollamaLog('✗ Failed: ' + e.message, '#f87171');
        ollamaLog('Start Ollama with: $env:OLLAMA_ORIGINS="*"; ollama serve', '#f87171');
    }
}

async function fetchPageText(url) {
    try {
        const r    = await fetch(url, { signal: AbortSignal.timeout(10000) });
        const html = await r.text();
        return html
            .replace(/<script[\s\S]*?<\/script>/gi, '')
            .replace(/<style[\s\S]*?<\/style>/gi, '')
            .replace(/<[^>]+>/g, ' ')
            .replace(/&amp;/g,'&').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&nbsp;/g,' ')
            .replace(/\s{2,}/g, ' ').trim().slice(0, 6000);
    } catch(e) { return null; }
}

async function askOllama(prompt) {
    const r = await fetch(ollamaBase() + '/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: ollamaModel(), prompt: prompt, stream: false, options: { temperature: 0.1, num_predict: 400 } })
    });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return (await r.json()).response || '';
}

function buildPrompt(company, text) {
    return 'You are a contact information extractor. Extract contact details for "' + company + '" from the webpage text below.\n\n'
        + 'Return ONLY a JSON object with these exact fields (empty string if not found):\n'
        + '{"emails_general":"comma-separated general emails","emails_security":"comma-separated security/abuse emails","phones":"comma-separated US phones","addresses":"comma-separated physical addresses"}\n\n'
        + 'No explanation, no markdown, just the JSON object.\n\nWEBPAGE TEXT:\n' + text;
}

function parseOllamaResp(raw) {
    try {
        const m = raw.match(/\{[\s\S]*\}/);
        return m ? JSON.parse(m[0]) : null;
    } catch(e) { return null; }
}

function updateContactRow(idx, enriched) {
    const c = S.filteredContacts[idx];
    if (!c) return;
    if (enriched.emails_general  && !c.emails_general)  c.emails_general  = enriched.emails_general;
    if (enriched.emails_security && !c.emails_security) c.emails_security = enriched.emails_security;
    if (enriched.phones          && !c.phones)          c.phones          = enriched.phones;
    if (enriched.addresses       && !c.addresses)       c.addresses       = enriched.addresses;

    const main = S.contacts.findIndex(function(x) { return x.company_name === c.company_name; });
    if (main !== -1) Object.assign(S.contacts[main], c);

    const ce = document.getElementById('ce-' + idx);
    const cs = document.getElementById('cs-' + idx);
    const cp = document.getElementById('cp-' + idx);
    const ca = document.getElementById('ca-' + idx);
    if (ce) ce.innerHTML = fmtEmails(c.emails_general);
    if (cs) cs.innerHTML = fmtEmails(c.emails_security);
    if (cp) cp.innerHTML = esc(c.phones || '') || '<span style="color:#1e293b">—</span>';
    if (ca) ca.innerHTML = esc(c.addresses || '') || '<span style="color:#1e293b">—</span>';

    const row = document.getElementById('crow-' + idx);
    if (row) {
        row.classList.add('row-flash');
        setTimeout(function() { row.classList.remove('row-flash'); }, 2000);
    }
}

async function enrichOne(idx) {
    const c   = S.filteredContacts[idx];
    if (!c) return;
    const btn = document.getElementById('eb-' + idx);
    if (btn) { btn.textContent = '⟳'; btn.disabled = true; }
    document.getElementById('ollama-panel').style.display = 'block';
    ollamaLog('Enriching: ' + c.company_name, '#94a3b8');

    if (!c.website) {
        ollamaLog('✗ ' + c.company_name + ': no website in CSV', '#f87171');
        if (btn) { btn.textContent = 'NO URL'; btn.disabled = false; }
        return;
    }

    const base   = c.website.replace(/\/$/, '');
    const pages  = [base, base + '/contact', base + '/contact-us'];
    let pageText = null;
    for (const url of pages) {
        ollamaLog('  Fetching ' + url + '…');
        pageText = await fetchPageText(url);
        if (pageText && pageText.length > 200) break;
    }

    if (!pageText) {
        ollamaLog('✗ ' + c.company_name + ': fetch failed (CORS or unreachable)', '#f87171');
        if (btn) { btn.textContent = 'ERR'; btn.disabled = false; }
        return;
    }

    ollamaLog('  Asking ' + ollamaModel() + '…');
    try {
        const parsed = parseOllamaResp(await askOllama(buildPrompt(c.company_name, pageText)));
        if (!parsed) {
            ollamaLog('✗ ' + c.company_name + ': unparseable response', '#f87171');
            if (btn) { btn.textContent = 'ERR'; btn.disabled = false; }
            return;
        }
        updateContactRow(idx, parsed);
        const found = [
            parsed.emails_general  ? 'email: '   + parsed.emails_general.slice(0,40)  : '',
            parsed.emails_security ? 'sec: '     + parsed.emails_security.slice(0,30) : '',
            parsed.phones          ? 'phone: '   + parsed.phones.slice(0,20)           : '',
            parsed.addresses       ? 'addr: '    + parsed.addresses.slice(0,40)        : '',
        ].filter(Boolean).join(' | ');
        ollamaLog('✓ ' + c.company_name + ': ' + (found || 'no new info found'), found ? '#34d399' : '#64748b');
        if (btn) { btn.textContent = '✓ DONE'; btn.disabled = false; }
    } catch(e) {
        ollamaLog('✗ ' + c.company_name + ': ' + e.message, '#f87171');
        if (btn) { btn.textContent = 'ERR'; btn.disabled = false; }
    }
}

async function enrichAll() {
    const data = S.filteredContacts;
    if (!data.length) return ollamaLog('No contacts loaded.', '#f87171');
    const btn = document.getElementById('enrich-all-btn');
    if (btn) btn.disabled = true;
    document.getElementById('ollama-progress').style.display = 'block';
    ollamaLog('━━ Starting enrichment of ' + data.length + ' companies ━━', '#f59e0b');

    for (let i = 0; i < data.length; i++) {
        const pct = Math.round((i / data.length) * 100);
        document.getElementById('progress-label').textContent = 'PROCESSING ' + (i+1) + ' / ' + data.length;
        document.getElementById('progress-pct').textContent   = pct + '%';
        document.getElementById('progress-bar').style.width   = pct + '%';
        await enrichOne(i);
        await new Promise(function(r) { setTimeout(r, 400); });
    }

    document.getElementById('progress-label').textContent = 'COMPLETE — ' + data.length + ' / ' + data.length;
    document.getElementById('progress-pct').textContent   = '100%';
    document.getElementById('progress-bar').style.width   = '100%';
    if (btn) btn.disabled = false;
    ollamaLog('━━ Enrichment complete ━━', '#34d399');
}
