"""Web dashboard and REST API for zhcorpus MCP server.

Follows the model-radar/srclight pattern:
- _dashboard_html() returns single-page HTML+CSS+JS
- REST endpoints at /api/* wrap MCP tool functions
- add_web_routes(mcp) registers routes on the FastMCP instance
"""

import json
import time

from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response

from .server import (
    _get_corpus_conn,
    _get_dict_conn,
    _query_definitions,
    _query_dialect_forms,
    _server_start_time,
    _VERSION,
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
    --bg: #0d1117; --surface: #161b22; --border: #30363d;
    --text: #e6edf3; --text-muted: #8b949e; --accent: #58a6ff;
    --accent-dim: #1f6feb; --green: #3fb950; --red: #f85149;
    --font: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    --mono: 'SF Mono', SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: var(--bg); color: var(--text); font-family: var(--font); line-height: 1.5; }
  .container { max-width: 960px; margin: 0 auto; padding: 24px 16px; }

  header { display: flex; align-items: center; gap: 12px; margin-bottom: 24px; border-bottom: 1px solid var(--border); padding-bottom: 16px; }
  header h1 { font-size: 20px; font-weight: 600; }
  header .badge { background: var(--accent-dim); color: #fff; padding: 2px 8px; border-radius: 12px; font-size: 12px; }

  .stats-bar { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 24px; }
  .stat-card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 12px 16px; }
  .stat-card .label { font-size: 12px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
  .stat-card .value { font-size: 24px; font-weight: 600; color: var(--accent); }

  .search-box { margin-bottom: 24px; }
  .search-box input {
    width: 100%; padding: 10px 16px; background: var(--surface); border: 1px solid var(--border);
    border-radius: 8px; color: var(--text); font-size: 16px; font-family: var(--font);
  }
  .search-box input:focus { outline: none; border-color: var(--accent); }
  .search-box input::placeholder { color: var(--text-muted); }

  .tabs { display: flex; gap: 0; margin-bottom: 16px; border-bottom: 1px solid var(--border); }
  .tab { padding: 8px 16px; cursor: pointer; color: var(--text-muted); border-bottom: 2px solid transparent; font-size: 14px; }
  .tab:hover { color: var(--text); }
  .tab.active { color: var(--accent); border-bottom-color: var(--accent); }

  .panel { display: none; }
  .panel.active { display: block; }

  .results { margin-top: 16px; }
  .result-item { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 16px; margin-bottom: 12px; }
  .result-item .meta { font-size: 12px; color: var(--text-muted); margin-bottom: 4px; }
  .result-item .meta .source { color: var(--accent); font-weight: 600; }
  .result-item .text { font-size: 15px; line-height: 1.7; }
  .result-item .text .cjk { font-family: 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif; }

  .report-section { margin-bottom: 20px; }
  .report-section h3 { font-size: 14px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }

  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 8px 12px; border-bottom: 1px solid var(--border); font-size: 14px; }
  th { color: var(--text-muted); font-weight: 500; }

  .def-list { list-style: none; }
  .def-list li { padding: 6px 0; border-bottom: 1px solid var(--border); font-size: 14px; }
  .def-list .lang-tag { display: inline-block; background: var(--accent-dim); color: #fff; padding: 1px 6px; border-radius: 4px; font-size: 11px; margin-right: 6px; }
  .def-list .source-tag { color: var(--text-muted); font-size: 12px; }

  .dialect-card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 12px 16px; margin-bottom: 8px; }
  .dialect-card .dialect-name { font-weight: 600; color: var(--green); }
  .dialect-card .pronunciation { font-family: var(--mono); font-size: 15px; }

  .loading { color: var(--text-muted); font-style: italic; }
  .error { color: var(--red); }

  .footer { margin-top: 40px; padding-top: 16px; border-top: 1px solid var(--border); font-size: 12px; color: var(--text-muted); text-align: center; }
  .footer a { color: var(--accent); text-decoration: none; }
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>zhcorpus</h1>
    <span class="badge">MCP Server</span>
    <span class="badge" id="uptime-badge" style="background: var(--green);">loading...</span>
  </header>

  <div class="stats-bar" id="stats-bar">
    <div class="stat-card"><div class="label">Articles</div><div class="value" id="stat-articles">—</div></div>
    <div class="stat-card"><div class="label">Chunks</div><div class="value" id="stat-chunks">—</div></div>
    <div class="stat-card"><div class="label">Headwords</div><div class="value" id="stat-headwords">—</div></div>
    <div class="stat-card"><div class="label">Definitions</div><div class="value" id="stat-definitions">—</div></div>
    <div class="stat-card"><div class="label">Dialect Forms</div><div class="value" id="stat-dialects">—</div></div>
  </div>

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

  <div class="footer">
    zhcorpus v""" + _VERSION + """ — Chinese corpus MCP search engine
    · <a href="/sse">SSE endpoint</a>
    · <a href="/mcp">Streamable HTTP</a>
  </div>
</div>

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

function activeTab() {
  return $('.tab.active').dataset.tab;
}

function fmt(n) {
  if (n === null || n === undefined) return '—';
  return Number(n).toLocaleString();
}

function escHtml(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

// Load stats on page load
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
    $('#uptime-badge').textContent = data.uptime || 'connected';
  } catch(e) {
    $('#uptime-badge').textContent = 'disconnected';
    $('#uptime-badge').style.background = 'var(--red)';
  }
}

// Search
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
    el.innerHTML = data.results.map((r, i) =>
      `<div class="result-item">
        <div class="meta"><span class="source">${escHtml(r.source)}</span> · ${escHtml(r.title)} · rank: ${r.rank.toFixed(2)}</div>
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

    // Definitions
    if (data.definitions && data.definitions.length > 0) {
      html += '<div class="report-section"><h3>Dictionary Definitions</h3><ul class="def-list">';
      data.definitions.forEach(d => {
        html += `<li><span class="lang-tag">${escHtml(d.lang)}</span>${escHtml(d.definition)} <span class="source-tag">(${escHtml(d.source)})</span></li>`;
      });
      html += '</ul></div>';
    }

    // Dialect forms
    if (data.dialects && data.dialects.length > 0) {
      html += '<div class="report-section"><h3>Dialect Forms</h3>';
      data.dialects.forEach(d => {
        const name = d.dialect === 'yue' ? 'Cantonese' : 'Hokkien';
        const chars = d.native_chars ? ` (${escHtml(d.native_chars)})` : '';
        const gloss = d.gloss ? ` — ${escHtml(d.gloss)}` : '';
        html += `<div class="dialect-card"><span class="dialect-name">${name}</span>: <span class="pronunciation">${escHtml(d.pronunciation)}</span>${chars}${gloss} <span class="source-tag">(${escHtml(d.source)})</span></div>`;
      });
      html += '</div>';
    }

    // Corpus evidence
    html += `<div class="report-section"><h3>Corpus Evidence (${fmt(data.total_hits)} hits)</h3>`;
    if (data.sources && data.sources.length > 0) {
      html += '<table><tr><th>Source</th><th>Hits</th></tr>';
      data.sources.forEach(s => { html += `<tr><td>${escHtml(s.name)}</td><td>${fmt(s.hit_count)}</td></tr>`; });
      html += '</table>';
    }
    html += '</div>';

    // Best examples
    if (data.examples && data.examples.length > 0) {
      html += '<div class="report-section"><h3>Best Examples</h3>';
      data.examples.forEach((ex, i) => {
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
      const pos = hw.pos ? ` [${escHtml(hw.pos)}]` : '';
      html += `<h3>${escHtml(hw.traditional)} / ${escHtml(hw.simplified)} (${escHtml(hw.pinyin)})${pos}</h3>`;
      if (hw.definitions && hw.definitions.length > 0) {
        html += '<ul class="def-list">';
        hw.definitions.forEach(d => {
          const conf = d.confidence ? ` [${escHtml(d.confidence)}]` : '';
          html += `<li><span class="lang-tag">${escHtml(d.lang)}</span>${escHtml(d.definition)} <span class="source-tag">(${escHtml(d.source)})${conf}</span></li>`;
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
      const chars = f.native_chars ? ` — characters: ${escHtml(f.native_chars)}` : '';
      const gloss = f.gloss ? ` — ${escHtml(f.gloss)}` : '';
      html += `<div class="dialect-card"><span class="dialect-name">${name}</span>: <span class="pronunciation">${escHtml(f.pronunciation)}</span>${chars}${gloss} <span class="source-tag">(${escHtml(f.source)})</span></div>`;
    });
    el.innerHTML = html;
  } catch(e) { el.innerHTML = `<div class="error">Error: ${e.message}</div>`; }
}

// Init
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
    """Register dashboard and REST API routes on the FastMCP instance.

    Call before run(transport='sse').
    """
    mcp_instance.custom_route("/", ["GET"], name="dashboard")(_dashboard)
    mcp_instance.custom_route("/api/search", ["GET"])(_api_search)
    mcp_instance.custom_route("/api/word_report", ["GET"])(_api_word_report)
    mcp_instance.custom_route("/api/lookup", ["GET"])(_api_lookup)
    mcp_instance.custom_route("/api/dialect", ["GET"])(_api_dialect)
    mcp_instance.custom_route("/api/stats", ["GET"])(_api_stats)
    mcp_instance.custom_route("/api/server_stats", ["GET"])(_api_server_stats)
