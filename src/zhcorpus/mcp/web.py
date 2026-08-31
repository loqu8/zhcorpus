"""Web dashboard and REST API for zhcorpus MCP server.

Follows the model-radar/srclight pattern:
- _dashboard_html() returns single-page HTML+CSS+JS
- REST endpoints at /api/* wrap MCP tool functions
- add_web_routes(mcp) registers routes on the MCPServer instance
"""

import json
import time

from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response

from zhcorpus import __version__ as _VERSION

from .server import (
    _get_corpus_conn,
    _get_dict_conn,
    _query_definitions,
    _query_dialect_forms,
    _server_start_time,
)


def _dashboard_html() -> str:
    """Single-page dashboard HTML with embedded CSS and JS."""
    return """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>zhcorpus — Chinese Corpus Search</title>
<style>
  :root {
    --crimson: #A50A17;
    --crimson-dim: rgba(165, 10, 23, 0.12);
    --steel-blue: #396A92;
    --surface: #FAFAFA;
    --dark: #1A1A1A;
    --dark-2: #2a2a2a;
    --grey: #666;
    --grey-light: #999;
    --border: #e5e5e5;
    --white: #ffffff;
    --radius: 8px;
    --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    --mono: "SF Mono", SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
    --cjk: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: var(--surface); color: var(--dark); font-family: var(--font); line-height: 1.6; }

  /* Header */
  header {
    background: var(--dark);
    color: white;
    padding: 1rem 2rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  header .left { display: flex; align-items: center; gap: 12px; }
  header h1 { font-size: 1.5rem; font-weight: 600; letter-spacing: -0.02em; }
  header .badge {
    font-size: 0.7rem; font-weight: 600; padding: 0.2rem 0.6rem;
    border-radius: 4px; text-transform: uppercase; letter-spacing: 0.05em;
  }
  header .badge-mcp { background: var(--crimson); color: white; }
  header .badge-uptime { background: rgba(255,255,255,0.15); color: rgba(255,255,255,0.6); }
  header .badge-uptime.ok { background: rgba(59,130,246,0.2); color: #93c5fd; }
  header nav a {
    color: rgba(255,255,255,0.7); text-decoration: none;
    margin-left: 1.5rem; font-size: 0.9rem;
  }
  header nav a:hover { color: white; }

  /* Hero stats bar */
  .hero-stats {
    background: linear-gradient(135deg, var(--dark) 0%, var(--dark-2) 100%);
    padding: 3rem 2rem 2.5rem;
    text-align: center;
  }
  .hero-stats h2 {
    color: white; font-size: 1.75rem; font-weight: 700;
    letter-spacing: -0.03em; margin-bottom: 0.5rem;
  }
  .hero-stats h2 .chinese { color: var(--crimson); font-weight: 400; }
  .hero-stats .subtitle {
    color: rgba(255,255,255,0.5); font-size: 0.95rem; margin-bottom: 2rem;
  }
  .stats-grid {
    display: flex; gap: 2rem; justify-content: center; flex-wrap: wrap;
    max-width: 900px; margin: 0 auto;
  }
  .stat {
    text-align: center; min-width: 120px;
  }
  .stat .number {
    font-size: 2rem; font-weight: 700; color: white;
    letter-spacing: -0.02em; line-height: 1.2;
  }
  .stat .label {
    font-size: 0.75rem; color: rgba(255,255,255,0.45);
    text-transform: uppercase; letter-spacing: 0.05em; margin-top: 0.25rem;
  }

  /* Main content */
  .container { max-width: 900px; margin: 0 auto; padding: 2rem 2rem 3rem; }

  /* Search */
  .search-box { margin-bottom: 1.5rem; position: relative; }
  .search-box input {
    width: 100%; padding: 14px 20px; background: var(--white);
    border: 1px solid var(--border); border-radius: var(--radius);
    color: var(--dark); font-size: 1.1rem; font-family: var(--font);
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    transition: border-color 0.15s, box-shadow 0.15s;
  }
  .search-box input:focus {
    outline: none; border-color: var(--crimson);
    box-shadow: 0 0 0 3px var(--crimson-dim);
  }
  .search-box input::placeholder { color: var(--grey-light); }

  /* Tabs */
  .tabs {
    display: flex; gap: 0; margin-bottom: 1.5rem;
    border-bottom: 1px solid var(--border);
  }
  .tab {
    padding: 10px 20px; cursor: pointer; color: var(--grey);
    border-bottom: 2px solid transparent; font-size: 0.95rem;
    font-weight: 500; transition: color 0.15s;
  }
  .tab:hover { color: var(--dark); }
  .tab.active { color: var(--crimson); border-bottom-color: var(--crimson); }

  .panel { display: none; }
  .panel.active { display: block; }

  /* Results */
  .results { margin-top: 8px; }
  .result-item {
    background: var(--white); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 16px 20px; margin-bottom: 12px;
    transition: box-shadow 0.15s;
  }
  .result-item:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
  .result-item .meta {
    font-size: 0.8rem; color: var(--grey-light); margin-bottom: 6px;
  }
  .result-item .meta .source {
    color: var(--crimson); font-weight: 600; text-transform: uppercase;
    font-size: 0.7rem; letter-spacing: 0.03em;
  }
  .result-item .text {
    font-size: 1rem; line-height: 1.8; color: var(--dark);
    font-family: var(--cjk);
  }

  /* Report sections */
  .report-section { margin-bottom: 24px; }
  .report-section h3 {
    font-size: 0.8rem; color: var(--grey); text-transform: uppercase;
    letter-spacing: 0.05em; margin-bottom: 10px; font-weight: 600;
  }

  table { width: 100%; border-collapse: collapse; }
  th, td {
    text-align: left; padding: 10px 14px;
    border-bottom: 1px solid var(--border); font-size: 0.95rem;
  }
  th { color: var(--grey); font-weight: 500; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.03em; }
  td { color: var(--dark); }

  .def-list { list-style: none; }
  .def-list li {
    padding: 8px 0; border-bottom: 1px solid var(--border);
    font-size: 0.95rem; color: var(--dark);
  }
  .def-list li:last-child { border-bottom: none; }
  .def-list .lang-tag {
    display: inline-block; background: var(--crimson); color: #fff;
    padding: 1px 7px; border-radius: 4px; font-size: 0.7rem;
    margin-right: 8px; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.03em;
  }
  .def-list .source-tag { color: var(--grey-light); font-size: 0.8rem; }

  .dict-heading {
    font-size: 1.25rem; font-weight: 600; margin: 20px 0 8px;
    color: var(--dark); letter-spacing: -0.01em;
  }
  .dict-heading:first-child { margin-top: 0; }
  .dict-heading .pinyin { color: var(--steel-blue); font-weight: 400; }
  .dict-heading .pos { color: var(--grey-light); font-weight: 400; font-size: 0.9rem; }

  /* Dialect cards */
  .dialect-card {
    background: var(--white); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 14px 18px; margin-bottom: 10px;
    display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap;
  }
  .dialect-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
  .dialect-name {
    font-weight: 600; color: var(--crimson);
    font-size: 0.8rem; text-transform: uppercase;
    letter-spacing: 0.03em; min-width: 80px;
  }
  .pronunciation {
    font-family: var(--mono); font-size: 1.05rem; color: var(--dark);
    font-weight: 500;
  }
  .dialect-chars { color: var(--steel-blue); font-family: var(--cjk); }
  .dialect-gloss { color: var(--grey); font-size: 0.9rem; }

  .loading { color: var(--grey-light); font-style: italic; padding: 20px 0; }
  .error { color: var(--crimson); padding: 20px 0; }

  /* Footer */
  footer {
    text-align: center; padding: 1.5rem 2rem; font-size: 0.85rem;
    color: var(--grey); border-top: 1px solid var(--border);
    margin-top: 2rem;
  }
  footer a { color: var(--steel-blue); text-decoration: none; }
  footer a:hover { text-decoration: underline; }

  @media (max-width: 640px) {
    .hero-stats h2 { font-size: 1.3rem; }
    .stats-grid { gap: 1rem; }
    .stat .number { font-size: 1.5rem; }
    .tab { padding: 8px 12px; font-size: 0.85rem; }
  }
</style>
</head>
<body>

<header>
  <div class="left">
    <h1>zhcorpus</h1>
    <span class="badge badge-mcp">MCP Server</span>
    <span class="badge badge-uptime" id="uptime-badge">connecting...</span>
  </div>
  <nav>
    <a href="/sse">SSE</a>
    <a href="/mcp">HTTP</a>
  </nav>
</header>

<div class="hero-stats">
  <h2>Chinese Corpus <span class="chinese">中文语料库</span></h2>
  <div class="subtitle">Multi-source evidence engine for Chinese lexicography</div>
  <div class="stats-grid">
    <div class="stat"><div class="number" id="stat-articles">—</div><div class="label">Articles</div></div>
    <div class="stat"><div class="number" id="stat-chunks">—</div><div class="label">Chunks</div></div>
    <div class="stat"><div class="number" id="stat-headwords">—</div><div class="label">Headwords</div></div>
    <div class="stat"><div class="number" id="stat-definitions">—</div><div class="label">Definitions</div></div>
    <div class="stat"><div class="number" id="stat-dialects">—</div><div class="label">Dialect Forms</div></div>
  </div>
</div>

<div class="container">
  <div class="search-box">
    <input type="text" id="search-input" placeholder="Search Chinese corpus... (e.g. 银行, 营商环境, 画蛇添足)" autofocus>
  </div>

  <div class="tabs">
    <div class="tab active" data-tab="corpus">Corpus Search</div>
    <div class="tab" data-tab="report">Word Report</div>
    <div class="tab" data-tab="dictionary">Dictionary</div>
    <div class="tab" data-tab="dialects">Dialects</div>
  </div>

  <div id="panel-corpus" class="panel active">
    <div class="results" id="corpus-results"></div>
  </div>
  <div id="panel-report" class="panel">
    <div id="report-results"></div>
  </div>
  <div id="panel-dictionary" class="panel">
    <div id="dict-results"></div>
  </div>
  <div id="panel-dialects" class="panel">
    <div id="dialect-results"></div>
  </div>
</div>

<footer>
  zhcorpus v""" + _VERSION + """ · Chinese corpus MCP search engine
  · <a href="https://loqu8.com">Loqu8</a>
</footer>

<script>
const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);

// Tab switching
$$('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    $$('.tab').forEach(t => t.classList.remove('active'));
    $$('.panel').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    $(`#panel-${tab.dataset.tab}`).classList.add('active');
    doSearch();
  });
});

function activeTab() { return $('.tab.active').dataset.tab; }

function fmt(n) {
  if (n === null || n === undefined) return '—';
  return Number(n).toLocaleString();
}

function escHtml(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

async function loadStats() {
  try {
    const res = await fetch('/api/stats');
    const data = await res.json();
    if (data.corpus) {
      $('#stat-articles').textContent = fmt(data.corpus.total_articles);
      $('#stat-chunks').textContent = fmt(data.corpus.total_chunks);
    }
    if (data.dictionary) {
      $('#stat-headwords').textContent = fmt(data.dictionary.headwords);
      $('#stat-definitions').textContent = fmt(data.dictionary.definitions);
      $('#stat-dialects').textContent = fmt(data.dictionary.dialect_forms);
    }
  } catch(e) { console.error('stats load failed', e); }
}

async function loadServerStats() {
  try {
    const res = await fetch('/api/server_stats');
    const data = await res.json();
    const badge = $('#uptime-badge');
    badge.textContent = 'up ' + (data.uptime || '?');
    badge.classList.add('ok');
  } catch(e) {
    const badge = $('#uptime-badge');
    badge.textContent = 'offline';
    badge.style.background = 'rgba(165,10,23,0.3)';
    badge.style.color = '#fca5a5';
  }
}

let searchTimeout;
$('#search-input').addEventListener('input', () => {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(doSearch, 300);
});
$('#search-input').addEventListener('keydown', e => {
  if (e.key === 'Enter') { clearTimeout(searchTimeout); doSearch(); }
});

async function doSearch() {
  const q = $('#search-input').value.trim();
  if (!q) return;
  const tab = activeTab();
  if (tab === 'corpus') await searchCorpus(q);
  else if (tab === 'report') await wordReport(q);
  else if (tab === 'dictionary') await lookupWord(q);
  else if (tab === 'dialects') await dialectForms(q);
}

async function searchCorpus(q) {
  const el = $('#corpus-results');
  el.innerHTML = '<div class="loading">Searching...</div>';
  try {
    const res = await fetch(`/api/search?q=${encodeURIComponent(q)}&limit=20`);
    const data = await res.json();
    if (!data.results || data.results.length === 0) {
      el.innerHTML = '<div class="loading">No results found.</div>';
      return;
    }
    el.innerHTML = data.results.map(r =>
      `<div class="result-item">
        <div class="meta"><span class="source">${escHtml(r.source)}</span> · ${escHtml(r.title)}</div>
        <div class="text">${escHtml(r.snippet)}</div>
      </div>`
    ).join('');
  } catch(e) { el.innerHTML = `<div class="error">Error: ${e.message}</div>`; }
}

async function wordReport(q) {
  const el = $('#report-results');
  el.innerHTML = '<div class="loading">Building report...</div>';
  try {
    const res = await fetch(`/api/word_report?term=${encodeURIComponent(q)}`);
    const data = await res.json();
    let html = '';

    if (data.definitions && data.definitions.length > 0) {
      html += '<div class="report-section"><h3>Dictionary Definitions</h3><ul class="def-list">';
      data.definitions.forEach(d => {
        html += `<li><span class="lang-tag">${escHtml(d.lang)}</span>${escHtml(d.definition)} <span class="source-tag">${escHtml(d.source)}</span></li>`;
      });
      html += '</ul></div>';
    }

    if (data.dialects && data.dialects.length > 0) {
      html += '<div class="report-section"><h3>Dialect Forms</h3>';
      data.dialects.forEach(d => {
        const name = d.dialect === 'yue' ? 'Cantonese' : 'Hokkien';
        const chars = d.native_chars ? `<span class="dialect-chars">${escHtml(d.native_chars)}</span>` : '';
        const gloss = d.gloss ? `<span class="dialect-gloss"> — ${escHtml(d.gloss)}</span>` : '';
        html += `<div class="dialect-card"><span class="dialect-name">${name}</span><span class="pronunciation">${escHtml(d.pronunciation)}</span>${chars}${gloss}</div>`;
      });
      html += '</div>';
    }

    html += `<div class="report-section"><h3>Corpus Evidence — ${fmt(data.total_hits)} hits</h3>`;
    if (data.sources && data.sources.length > 0) {
      html += '<table><tr><th>Source</th><th>Hits</th></tr>';
      data.sources.forEach(s => { html += `<tr><td>${escHtml(s.name)}</td><td>${fmt(s.hit_count)}</td></tr>`; });
      html += '</table>';
    }
    html += '</div>';

    if (data.examples && data.examples.length > 0) {
      html += '<div class="report-section"><h3>Best Examples</h3>';
      data.examples.forEach(ex => {
        html += `<div class="result-item"><div class="meta"><span class="source">${escHtml(ex.source)}</span> · ${escHtml(ex.title)}</div><div class="text">${escHtml(ex.text)}</div></div>`;
      });
      html += '</div>';
    }

    el.innerHTML = html || '<div class="loading">No data found.</div>';
  } catch(e) { el.innerHTML = `<div class="error">Error: ${e.message}</div>`; }
}

async function lookupWord(q) {
  const el = $('#dict-results');
  el.innerHTML = '<div class="loading">Looking up...</div>';
  try {
    const res = await fetch(`/api/lookup?headword=${encodeURIComponent(q)}`);
    const data = await res.json();
    if (!data.headwords || data.headwords.length === 0) {
      el.innerHTML = '<div class="loading">No dictionary entries found.</div>';
      return;
    }
    let html = '';
    data.headwords.forEach(hw => {
      const pos = hw.pos ? `<span class="pos"> ${escHtml(hw.pos)}</span>` : '';
      html += `<div class="dict-heading">${escHtml(hw.traditional)} / ${escHtml(hw.simplified)} <span class="pinyin">${escHtml(hw.pinyin)}</span>${pos}</div>`;
      if (hw.definitions && hw.definitions.length > 0) {
        html += '<ul class="def-list">';
        hw.definitions.forEach(d => {
          html += `<li><span class="lang-tag">${escHtml(d.lang)}</span>${escHtml(d.definition)} <span class="source-tag">${escHtml(d.source)}</span></li>`;
        });
        html += '</ul>';
      }
    });
    el.innerHTML = html;
  } catch(e) { el.innerHTML = `<div class="error">Error: ${e.message}</div>`; }
}

async function dialectForms(q) {
  const el = $('#dialect-results');
  el.innerHTML = '<div class="loading">Looking up dialects...</div>';
  try {
    const res = await fetch(`/api/dialect?headword=${encodeURIComponent(q)}`);
    const data = await res.json();
    if (!data.forms || data.forms.length === 0) {
      el.innerHTML = '<div class="loading">No dialect forms found.</div>';
      return;
    }
    let html = '';
    data.forms.forEach(f => {
      const name = f.dialect === 'yue' ? 'Cantonese' : 'Hokkien';
      const chars = f.native_chars ? `<span class="dialect-chars">${escHtml(f.native_chars)}</span>` : '';
      const gloss = f.gloss ? `<span class="dialect-gloss"> — ${escHtml(f.gloss)}</span>` : '';
      html += `<div class="dialect-card"><span class="dialect-name">${name}</span><span class="pronunciation">${escHtml(f.pronunciation)}</span>${chars}${gloss}</div>`;
    });
    el.innerHTML = html;
  } catch(e) { el.innerHTML = `<div class="error">Error: ${e.message}</div>`; }
}

loadStats();
loadServerStats();
setInterval(loadServerStats, 60000);
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# REST API endpoints
# ---------------------------------------------------------------------------

async def _api_search(request: Request) -> Response:
    """Search the corpus and return JSON results."""
    q = request.query_params.get("q", "")
    limit = int(request.query_params.get("limit", "20"))
    if not q:
        return JSONResponse({"error": "Missing 'q' parameter"}, status_code=400)

    from zhcorpus.search.fts import search_fts
    conn = _get_corpus_conn()
    limit = max(1, min(100, limit))
    results = search_fts(conn, q, limit=limit)

    return JSONResponse({
        "query": q,
        "count": len(results),
        "results": [
            {
                "chunk_id": r.chunk_id,
                "text": r.text,
                "source": r.source,
                "title": r.title,
                "rank": r.rank,
                "snippet": r.snippet,
            }
            for r in results
        ],
    })


async def _api_word_report(request: Request) -> Response:
    """Build a word report and return JSON."""
    term = request.query_params.get("term", "")
    if not term:
        return JSONResponse({"error": "Missing 'term' parameter"}, status_code=400)

    from zhcorpus.report import build_word_report
    conn = _get_corpus_conn()
    report = build_word_report(conn, term)

    # Dictionary definitions
    definitions = []
    dialects = []
    try:
        dict_conn = _get_dict_conn()
        definitions = _query_definitions(dict_conn, term)
        dialects = _query_dialect_forms(dict_conn, term)
    except Exception:
        pass

    return JSONResponse({
        "term": term,
        "total_hits": report.total_hits,
        "sources": [
            {"name": s.name, "hit_count": s.hit_count, "best_snippets": s.best_snippets}
            for s in report.sources
        ],
        "cedict_entries": [
            {"traditional": e.traditional, "simplified": e.simplified, "pinyin": e.pinyin, "definition": e.definition}
            for e in report.cedict_entries
        ],
        "examples": report.best_snippets,
        "definitions": definitions,
        "dialects": dialects,
    })


async def _api_lookup(request: Request) -> Response:
    """Look up a word in the dictionary and return JSON."""
    headword = request.query_params.get("headword", "")
    if not headword:
        return JSONResponse({"error": "Missing 'headword' parameter"}, status_code=400)

    dict_conn = _get_dict_conn()
    rows = dict_conn.execute(
        "SELECT id, traditional, simplified, pinyin, pos "
        "FROM headwords WHERE simplified = ? OR traditional = ?",
        (headword, headword),
    ).fetchall()

    headwords = []
    for hw in rows:
        defs = dict_conn.execute(
            "SELECT lang, definition, source, confidence "
            "FROM definitions WHERE headword_id = ? ORDER BY lang, source",
            (hw["id"],),
        ).fetchall()
        headwords.append({
            "traditional": hw["traditional"],
            "simplified": hw["simplified"],
            "pinyin": hw["pinyin"],
            "pos": hw["pos"],
            "definitions": [dict(d) for d in defs],
        })

    return JSONResponse({"headword": headword, "headwords": headwords})


async def _api_dialect(request: Request) -> Response:
    """Look up dialect forms and return JSON."""
    headword = request.query_params.get("headword", "")
    if not headword:
        return JSONResponse({"error": "Missing 'headword' parameter"}, status_code=400)

    dict_conn = _get_dict_conn()
    forms = _query_dialect_forms(dict_conn, headword)
    return JSONResponse({"headword": headword, "forms": forms})


async def _api_stats(request: Request) -> Response:
    """Combined corpus + dictionary stats."""
    result = {}

    try:
        conn = _get_corpus_conn()
        sources = conn.execute(
            "SELECT name, article_count, chunk_count FROM sources ORDER BY chunk_count DESC"
        ).fetchall()
        total_articles = sum(s["article_count"] or 0 for s in sources)
        total_chunks = sum(s["chunk_count"] or 0 for s in sources)
        result["corpus"] = {
            "total_articles": total_articles,
            "total_chunks": total_chunks,
            "sources": [
                {"name": s["name"], "articles": s["article_count"] or 0, "chunks": s["chunk_count"] or 0}
                for s in sources
            ],
        }
    except Exception:
        result["corpus"] = None

    try:
        dict_conn = _get_dict_conn()
        headwords = dict_conn.execute("SELECT COUNT(*) FROM headwords").fetchone()[0]
        definitions = dict_conn.execute("SELECT COUNT(*) FROM definitions").fetchone()[0]
        dialect_count = dict_conn.execute("SELECT COUNT(*) FROM dialect_forms").fetchone()[0]
        result["dictionary"] = {
            "headwords": headwords,
            "definitions": definitions,
            "dialect_forms": dialect_count,
        }
    except Exception:
        result["dictionary"] = None

    return JSONResponse(result)


async def _api_server_stats(request: Request) -> Response:
    """Server uptime and version."""
    from .server import _server_start_time
    start = _server_start_time or time.time()
    uptime_s = time.time() - start
    if uptime_s < 3600:
        uptime = f"{uptime_s / 60:.1f}m"
    elif uptime_s < 86400:
        uptime = f"{uptime_s / 3600:.1f}h"
    else:
        uptime = f"{uptime_s / 86400:.1f}d"

    return JSONResponse({"version": _VERSION, "uptime": uptime, "uptime_seconds": uptime_s})


async def _dashboard(request: Request) -> Response:
    """Serve the dashboard HTML."""
    return HTMLResponse(_dashboard_html())


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------

def add_web_routes(mcp_instance) -> None:
    """Register dashboard and REST API routes on the MCPServer instance.

    Call before run(transport='sse').
    """
    mcp_instance.custom_route("/", ["GET"], name="dashboard")(_dashboard)
    mcp_instance.custom_route("/api/search", ["GET"])(_api_search)
    mcp_instance.custom_route("/api/word_report", ["GET"])(_api_word_report)
    mcp_instance.custom_route("/api/lookup", ["GET"])(_api_lookup)
    mcp_instance.custom_route("/api/dialect", ["GET"])(_api_dialect)
    mcp_instance.custom_route("/api/stats", ["GET"])(_api_stats)
    mcp_instance.custom_route("/api/server_stats", ["GET"])(_api_server_stats)
