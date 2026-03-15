import os
import re
import base64
import tomllib
import asyncio
from typing import Optional
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

GITHUB_PAT = os.environ.get("GITHUB_PAT", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "")
PORT = int(os.environ.get("PORT", "8080"))

GITHUB_API = "https://api.github.com"
MODRINTH_API = "https://api.modrinth.com/v2"
GAME_VERSION = "1.20.1"
LOADER = "forge"

app = FastAPI()

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Packwiz Mod Manager</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #0f1117;
    --surface: #1a1d27;
    --surface2: #22263a;
    --border: #2e3250;
    --accent: #6c63ff;
    --accent-hover: #8078ff;
    --danger: #e05252;
    --danger-hover: #f06060;
    --success: #4caf82;
    --text: #e2e4f0;
    --text-muted: #7b82a6;
    --radius: 10px;
  }
  body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif; min-height: 100vh; }
  header {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 1rem 2rem;
    display: flex;
    align-items: center;
    gap: 1rem;
  }
  header h1 { font-size: 1.3rem; font-weight: 700; color: var(--text); }
  header .subtitle { color: var(--text-muted); font-size: 0.85rem; }
  .repo-tag {
    margin-left: auto;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 0.3rem 0.75rem;
    font-size: 0.8rem;
    color: var(--text-muted);
  }
  .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }

  /* Tabs */
  .tabs {
    display: flex;
    gap: 0.25rem;
    margin-bottom: 1.5rem;
    border-bottom: 1px solid var(--border);
  }
  .tab-btn {
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0;
    color: var(--text-muted);
    padding: 0.6rem 1.25rem;
    font-size: 0.95rem;
    font-weight: 600;
    cursor: pointer;
    transition: color 0.2s, border-color 0.2s;
    margin-bottom: -1px;
  }
  .tab-btn:hover { color: var(--text); background: transparent; }
  .tab-btn.active { color: var(--accent); border-bottom-color: var(--accent); background: transparent; }
  .tab-panel { display: none; }
  .tab-panel.active { display: block; }

  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; }
  @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
  .panel {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
  }
  .panel-header {
    padding: 1rem 1.25rem;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .panel-header h2 { font-size: 1rem; font-weight: 600; }
  .badge {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 0.15rem 0.6rem;
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-left: auto;
  }
  .panel-body { padding: 1.25rem; }
  .search-bar {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;
  }
  input[type="text"] {
    flex: 1;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.6rem 1rem;
    color: var(--text);
    font-size: 0.9rem;
    outline: none;
    transition: border-color 0.2s;
  }
  input[type="text"]:focus { border-color: var(--accent); }
  button {
    background: var(--accent);
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 0.6rem 1.2rem;
    font-size: 0.9rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s, opacity 0.2s;
    white-space: nowrap;
  }
  button:hover { background: var(--accent-hover); }
  button:disabled { opacity: 0.5; cursor: not-allowed; }
  button.danger { background: var(--danger); }
  button.danger:hover { background: var(--danger-hover); }
  button.sm { padding: 0.35rem 0.8rem; font-size: 0.8rem; }
  button.ghost {
    background: transparent;
    border: 1px solid var(--border);
    color: var(--text-muted);
  }
  button.ghost:hover { border-color: var(--accent); color: var(--accent); background: transparent; }
  button.success-btn { background: var(--success); }
  button.success-btn:hover { background: #3d9e6d; }
  .mod-list { display: flex; flex-direction: column; gap: 0.6rem; }
  .mod-item {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
    transition: border-color 0.2s;
  }
  .mod-item:hover { border-color: var(--accent); }
  .mod-item-row {
    padding: 0.75rem 1rem;
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }
  .mod-icon {
    width: 40px;
    height: 40px;
    border-radius: 6px;
    object-fit: cover;
    background: var(--border);
    flex-shrink: 0;
  }
  .mod-icon-placeholder {
    width: 40px;
    height: 40px;
    border-radius: 6px;
    background: var(--border);
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.2rem;
  }
  .mod-info { flex: 1; min-width: 0; }
  .mod-name { font-weight: 600; font-size: 0.95rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .mod-meta { color: var(--text-muted); font-size: 0.8rem; margin-top: 0.2rem; display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap; }
  .mod-desc { color: var(--text-muted); font-size: 0.8rem; margin-top: 0.15rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .mod-actions { display: flex; gap: 0.5rem; align-items: center; flex-shrink: 0; }
  .already-badge {
    background: rgba(76, 175, 130, 0.15);
    border: 1px solid var(--success);
    color: var(--success);
    border-radius: 999px;
    padding: 0.2rem 0.6rem;
    font-size: 0.75rem;
    font-weight: 600;
  }
  .dl-count { color: var(--text-muted); font-size: 0.75rem; }
  .loading {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem;
    color: var(--text-muted);
    gap: 0.5rem;
  }
  .spinner {
    width: 20px; height: 20px;
    border: 2px solid var(--border);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .empty { text-align: center; color: var(--text-muted); padding: 2rem; font-size: 0.9rem; }
  .toast-container {
    position: fixed;
    bottom: 1.5rem;
    right: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    z-index: 9999;
    pointer-events: none;
  }
  .toast {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.75rem 1.25rem;
    font-size: 0.875rem;
    box-shadow: 0 4px 24px rgba(0,0,0,0.4);
    animation: slideIn 0.25s ease;
    pointer-events: auto;
    max-width: 340px;
  }
  .toast.success { border-left: 3px solid var(--success); }
  .toast.error { border-left: 3px solid var(--danger); }
  @keyframes slideIn { from { transform: translateX(120%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
  @keyframes slideOut { from { transform: translateX(0); opacity: 1; } to { transform: translateX(120%); opacity: 0; } }
  a { color: var(--accent); text-decoration: none; }
  a:hover { text-decoration: underline; }
  .refresh-btn { margin-left: auto; }

  /* Side badges */
  .side-badge {
    border-radius: 999px;
    padding: 0.15rem 0.55rem;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.03em;
    display: inline-block;
  }
  .side-client { background: rgba(108,99,255,0.18); border: 1px solid #6c63ff; color: #a39fff; }
  .side-server { background: rgba(76,175,130,0.18); border: 1px solid #4caf82; color: #6dd6a6; }
  .side-both { background: rgba(120,120,140,0.18); border: 1px solid #5a5a7a; color: #a0a0c0; }
  .optional-badge {
    background: rgba(255,193,7,0.15);
    border: 1px solid #ffc107;
    color: #ffd54f;
    border-radius: 999px;
    padding: 0.15rem 0.55rem;
    font-size: 0.72rem;
    font-weight: 700;
  }
  .default-badge {
    background: rgba(255,152,0,0.15);
    border: 1px solid #ff9800;
    color: #ffb74d;
    border-radius: 999px;
    padding: 0.15rem 0.55rem;
    font-size: 0.72rem;
    font-weight: 700;
  }

  /* Inline edit panel */
  .edit-panel {
    display: none;
    border-top: 1px solid var(--border);
    background: #1e2235;
    padding: 1rem 1.25rem;
    gap: 1.25rem;
    flex-direction: column;
  }
  .edit-panel.open { display: flex; }
  .edit-panel-row { display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; }
  .edit-label { font-size: 0.85rem; color: var(--text-muted); font-weight: 600; min-width: 70px; }
  .edit-actions { display: flex; gap: 0.5rem; margin-top: 0.25rem; }

  /* Segmented button */
  .seg-group { display: flex; border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
  .seg-btn {
    background: transparent;
    border: none;
    border-radius: 0;
    color: var(--text-muted);
    padding: 0.4rem 0.85rem;
    font-size: 0.82rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
    border-right: 1px solid var(--border);
  }
  .seg-btn:last-child { border-right: none; }
  .seg-btn:hover { background: var(--surface2); color: var(--text); }
  .seg-btn.active { background: var(--accent); color: #fff; }

  /* Toggle switch */
  .toggle-wrap { display: flex; align-items: center; gap: 0.6rem; }
  .toggle {
    position: relative;
    width: 40px;
    height: 22px;
    flex-shrink: 0;
  }
  .toggle input { opacity: 0; width: 0; height: 0; }
  .toggle-slider {
    position: absolute;
    inset: 0;
    background: var(--border);
    border-radius: 22px;
    cursor: pointer;
    transition: background 0.2s;
  }
  .toggle-slider:before {
    content: '';
    position: absolute;
    width: 16px; height: 16px;
    left: 3px; top: 3px;
    background: var(--text-muted);
    border-radius: 50%;
    transition: transform 0.2s, background 0.2s;
  }
  .toggle input:checked + .toggle-slider { background: var(--accent); }
  .toggle input:checked + .toggle-slider:before { transform: translateX(18px); background: #fff; }
  .toggle-label { font-size: 0.85rem; color: var(--text-muted); }

  /* All mods full-width panel */
  .all-mods-panel {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
  }
  .filter-bar {
    padding: 1rem 1.25rem;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }
  .filter-bar input { max-width: 320px; flex: none; }
  .filter-count { color: var(--text-muted); font-size: 0.85rem; margin-left: auto; }
</style>
</head>
<body>
<header>
  <div>
    <h1>Packwiz Mod Manager</h1>
    <div class="subtitle">Mod management for 1.20.1 / Forge</div>
  </div>
  <div class="repo-tag" id="repoTag">Loading...</div>
</header>
<div class="container">
  <div class="tabs">
    <button class="tab-btn active" onclick="switchTab('client')">Client Mods</button>
    <button class="tab-btn" onclick="switchTab('all')">All Mods</button>
  </div>

  <!-- CLIENT MODS TAB -->
  <div class="tab-panel active" id="tab-client">
    <div class="grid">
      <div class="panel">
        <div class="panel-header">
          <h2>Installed Client Mods</h2>
          <span class="badge" id="modCount">0</span>
          <button class="ghost sm refresh-btn" onclick="loadMods()" title="Refresh">Refresh</button>
        </div>
        <div class="panel-body">
          <div id="modList" class="mod-list">
            <div class="loading"><div class="spinner"></div> Loading mods...</div>
          </div>
        </div>
      </div>
      <div class="panel">
        <div class="panel-header">
          <h2>Search Modrinth</h2>
        </div>
        <div class="panel-body">
          <div class="search-bar">
            <input type="text" id="searchInput" placeholder="Search for mods (1.20.1 / Forge)..." onkeydown="if(event.key==='Enter') doSearch()"/>
            <button onclick="doSearch()" id="searchBtn">Search</button>
          </div>
          <div id="searchResults" class="mod-list">
            <div class="empty">Search for mods to add to your pack.</div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ALL MODS TAB -->
  <div class="tab-panel" id="tab-all">
    <div class="all-mods-panel">
      <div class="filter-bar">
        <input type="text" id="allModsFilter" placeholder="Filter mods by name..." oninput="filterAllMods()"/>
        <button class="ghost sm" onclick="loadAllMods()">Refresh</button>
        <span class="filter-count" id="allModsCount"></span>
      </div>
      <div class="panel-body">
        <div id="allModsList" class="mod-list">
          <div class="loading"><div class="spinner"></div> Loading all mods...</div>
        </div>
      </div>
    </div>
  </div>
</div>
<div class="toast-container" id="toasts"></div>
<script>
var installedSlugs = new Set();
var installedMods = [];
var allMods = [];
var activeTab = 'client';
var allModsLoaded = false;

function switchTab(tab) {
  activeTab = tab;
  document.querySelectorAll('.tab-btn').forEach(function(b, i) {
    b.classList.toggle('active', (i === 0 && tab === 'client') || (i === 1 && tab === 'all'));
  });
  document.getElementById('tab-client').classList.toggle('active', tab === 'client');
  document.getElementById('tab-all').classList.toggle('active', tab === 'all');
  if (tab === 'all' && !allModsLoaded) {
    loadAllMods();
  }
}

function toast(msg, type) {
  type = type || 'success';
  var c = document.getElementById('toasts');
  var el = document.createElement('div');
  el.className = 'toast ' + type;
  el.textContent = msg;
  c.appendChild(el);
  setTimeout(function() {
    el.style.animation = 'slideOut 0.25s ease forwards';
    setTimeout(function() { el.remove(); }, 260);
  }, 3500);
}

function fmtDownloads(n) {
  if (n >= 1000000) return (n/1000000).toFixed(1) + 'M';
  if (n >= 1000) return (n/1000).toFixed(1) + 'K';
  return n;
}

function escHtml(s) {
  return String(s)
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;')
    .replace(/'/g,'&#39;');
}

/* ===== CLIENT MODS ===== */
async function loadMods() {
  document.getElementById('modList').innerHTML = '<div class="loading"><div class="spinner"></div> Loading...</div>';
  try {
    var res = await fetch('/api/mods');
    var data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to load mods');
    installedMods = data;
    installedSlugs = new Set(data.map(function(m) { return m.slug; }));
    document.getElementById('modCount').textContent = data.length;
    document.getElementById('repoTag').textContent = data.length + ' client mods in pack';
    renderMods(data);
    refreshSearchBadges();
  } catch(e) {
    document.getElementById('modList').innerHTML = '<div class="empty">Error: ' + escHtml(e.message) + '</div>';
    toast('Failed to load mods: ' + e.message, 'error');
  }
}

function renderMods(mods) {
  var el = document.getElementById('modList');
  if (!mods.length) { el.innerHTML = '<div class="empty">No client mods installed yet.</div>'; return; }
  el.innerHTML = mods.map(function(m) {
    return '<div class="mod-item" id="mod-' + escHtml(m.slug) + '" data-name="' + escHtml(m.name) + '">' +
      '<div class="mod-item-row">' +
        (m.icon ? '<img class="mod-icon" src="' + escHtml(m.icon) + '" onerror="this.remove()" loading="lazy"/>' : '<div class="mod-icon-placeholder">&#x1F9E9;</div>') +
        '<div class="mod-info">' +
          '<div class="mod-name">' + escHtml(m.name) + '</div>' +
          '<div class="mod-meta">' +
            (m.version ? escHtml(m.version) : '') +
            (m.mod_id ? ' &middot; <a href="https://modrinth.com/mod/' + escHtml(m.mod_id) + '" target="_blank" rel="noopener">Modrinth</a>' : '') +
          '</div>' +
        '</div>' +
        '<div class="mod-actions">' +
          '<button class="sm danger" onclick="removeMod(this)" id="rm-' + escHtml(m.slug) + '">Remove</button>' +
        '</div>' +
      '</div>' +
    '</div>';
  }).join('');
}

async function removeMod(btn) {
  var slug = btn.id.replace('rm-', '');
  var name = btn.closest('.mod-item').dataset.name || slug;
  btn.disabled = true;
  btn.textContent = '...';
  try {
    var res = await fetch('/api/mods/' + encodeURIComponent(slug), { method: 'DELETE' });
    var data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Remove failed');
    toast('Removed: ' + name);
    await loadMods();
  } catch(e) {
    toast('Error: ' + e.message, 'error');
    if (btn) { btn.disabled = false; btn.textContent = 'Remove'; }
  }
}

async function doSearch() {
  var q = document.getElementById('searchInput').value.trim();
  if (!q) return;
  var btn = document.getElementById('searchBtn');
  btn.disabled = true;
  document.getElementById('searchResults').innerHTML = '<div class="loading"><div class="spinner"></div> Searching...</div>';
  try {
    var res = await fetch('/api/search?q=' + encodeURIComponent(q));
    var data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Search failed');
    renderSearch(data);
  } catch(e) {
    document.getElementById('searchResults').innerHTML = '<div class="empty">Error: ' + escHtml(e.message) + '</div>';
    toast('Search error: ' + e.message, 'error');
  } finally {
    btn.disabled = false;
  }
}

function renderSearch(results) {
  var el = document.getElementById('searchResults');
  if (!results.length) { el.innerHTML = '<div class="empty">No results found.</div>'; return; }
  el.innerHTML = results.map(function(r) {
    var already = installedSlugs.has(r.slug);
    return '<div class="mod-item" id="sr-' + escHtml(r.slug) + '">' +
      '<div class="mod-item-row">' +
        (r.icon ? '<img class="mod-icon" src="' + escHtml(r.icon) + '" onerror="this.remove()" loading="lazy"/>' : '<div class="mod-icon-placeholder">&#x1F9E9;</div>') +
        '<div class="mod-info">' +
          '<div class="mod-name">' + escHtml(r.name) + '</div>' +
          '<div class="mod-desc">' + escHtml(r.description || '') + '</div>' +
          '<div class="mod-meta"><span class="dl-count">' + fmtDownloads(r.downloads) + ' downloads</span></div>' +
        '</div>' +
        '<div class="mod-actions">' +
          (already
            ? '<span class="already-badge">Added</span>'
            : '<button class="sm add-btn" data-pid="' + escHtml(r.project_id) + '" data-slug="' + escHtml(r.slug) + '" data-name="' + escHtml(r.name) + '" id="add-' + escHtml(r.slug) + '">Add</button>'
          ) +
        '</div>' +
      '</div>' +
    '</div>';
  }).join('');
  el.querySelectorAll('.add-btn').forEach(function(b) {
    b.addEventListener('click', function() { addMod(b.dataset.pid, b.dataset.slug, b.dataset.name); });
  });
}

function refreshSearchBadges() {
  document.querySelectorAll('[id^="add-"]').forEach(function(btn) {
    var slug = btn.id.replace('add-', '');
    if (installedSlugs.has(slug)) {
      var actions = btn.closest('.mod-actions');
      if (actions) actions.innerHTML = '<span class="already-badge">Added</span>';
    }
  });
}

async function addMod(projectId, slug, name) {
  var btn = document.getElementById('add-' + slug);
  if (btn) { btn.disabled = true; btn.textContent = 'Adding...'; }
  try {
    var res = await fetch('/api/mods', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id: projectId })
    });
    var data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Add failed');
    toast('Added: ' + name);
    await loadMods();
    var actions = btn ? btn.closest('.mod-actions') : null;
    if (actions) actions.innerHTML = '<span class="already-badge">Added</span>';
  } catch(e) {
    toast('Error: ' + e.message, 'error');
    if (btn) { btn.disabled = false; btn.textContent = 'Add'; }
  }
}

/* ===== ALL MODS ===== */
async function loadAllMods() {
  document.getElementById('allModsList').innerHTML = '<div class="loading"><div class="spinner"></div> Loading all mods...</div>';
  document.getElementById('allModsCount').textContent = '';
  allModsLoaded = false;
  try {
    var res = await fetch('/api/all-mods');
    var data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to load mods');
    allMods = data;
    allModsLoaded = true;
    renderAllMods(allMods);
  } catch(e) {
    document.getElementById('allModsList').innerHTML = '<div class="empty">Error: ' + escHtml(e.message) + '</div>';
    toast('Failed to load all mods: ' + e.message, 'error');
  }
}

function filterAllMods() {
  var q = document.getElementById('allModsFilter').value.trim().toLowerCase();
  if (!q) { renderAllMods(allMods); return; }
  var filtered = allMods.filter(function(m) {
    return m.name.toLowerCase().includes(q) || m.slug.toLowerCase().includes(q);
  });
  renderAllMods(filtered);
}

function sideBadgeClass(side) {
  if (side === 'client') return 'side-client';
  if (side === 'server') return 'side-server';
  return 'side-both';
}

function renderAllMods(mods) {
  var el = document.getElementById('allModsList');
  document.getElementById('allModsCount').textContent = mods.length + ' mod' + (mods.length !== 1 ? 's' : '');
  if (!mods.length) { el.innerHTML = '<div class="empty">No mods found.</div>'; return; }
  el.innerHTML = mods.map(function(m) {
    var sid = m.side || 'both';
    var isOpt = !!m.optional;
    var isDef = !!m.default;
    var slug = m.slug;
    return '<div class="mod-item" id="allmod-' + escHtml(slug) + '" data-name="' + escHtml(m.name.toLowerCase()) + '">' +
      '<div class="mod-item-row">' +
        (m.icon ? '<img class="mod-icon" src="' + escHtml(m.icon) + '" onerror="this.remove()" loading="lazy"/>' : '<div class="mod-icon-placeholder">&#x1F9E9;</div>') +
        '<div class="mod-info">' +
          '<div class="mod-name">' + escHtml(m.name) + '</div>' +
          '<div class="mod-meta">' +
            '<span class="side-badge ' + sideBadgeClass(sid) + '">' + escHtml(sid) + '</span>' +
            (isOpt ? '<span class="optional-badge">optional</span>' : '') +
            (isOpt && isDef ? '<span class="default-badge">default on</span>' : '') +
            (m.mod_id ? ' <a href="https://modrinth.com/mod/' + escHtml(m.mod_id) + '" target="_blank" rel="noopener" style="font-size:0.78rem">Modrinth</a>' : '') +
          '</div>' +
        '</div>' +
        '<div class="mod-actions">' +
          '<button class="ghost sm edit-btn" data-slug="' + escHtml(slug) + '">Edit</button>' +
        '</div>' +
      '</div>' +
      '<div class="edit-panel" id="edit-' + escHtml(slug) + '">' +
        '<div class="edit-panel-row">' +
          '<span class="edit-label">Side</span>' +
          '<div class="seg-group" id="seg-' + escHtml(slug) + '">' +
            '<button class="seg-btn' + (sid==='client'?' active':'') + ' side-btn" data-slug="' + escHtml(slug) + '" data-side="client">client</button>' +
            '<button class="seg-btn' + (sid==='server'?' active':'') + ' side-btn" data-slug="' + escHtml(slug) + '" data-side="server">server</button>' +
            '<button class="seg-btn' + (sid==='both'?' active':'') + ' side-btn" data-slug="' + escHtml(slug) + '" data-side="both">both</button>' +
          '</div>' +
        '</div>' +
        '<div class="edit-panel-row">' +
          '<span class="edit-label">Optional</span>' +
          '<label class="toggle"><input type="checkbox" class="opt-chk" data-slug="' + escHtml(slug) + '" id="opt-' + escHtml(slug) + '" ' + (isOpt?'checked':'') + '/><span class="toggle-slider"></span></label>' +
          '<span class="toggle-label" id="opt-label-' + escHtml(slug) + '">' + (isOpt?'Yes':'No') + '</span>' +
        '</div>' +
        '<div class="edit-panel-row" id="default-row-' + escHtml(slug) + '" style="' + (!isOpt?'display:none':'') + '">' +
          '<span class="edit-label">Default</span>' +
          '<label class="toggle"><input type="checkbox" id="def-' + escHtml(slug) + '" ' + (isDef?'checked':'') + '/><span class="toggle-slider"></span></label>' +
          '<span class="toggle-label" id="def-label-' + escHtml(slug) + '">' + (isDef?'Yes':'No') + '</span>' +
        '</div>' +
        '<div class="edit-actions">' +
          '<button class="sm success-btn save-btn" data-slug="' + escHtml(slug) + '" data-name="' + escHtml(m.name) + '" id="save-' + escHtml(slug) + '">Save</button>' +
          '<button class="sm ghost cancel-btn" data-slug="' + escHtml(slug) + '">Cancel</button>' +
        '</div>' +
      '</div>' +
    '</div>';
  }).join('');

  // wire up event listeners (avoid inline onclick with quotes)
  el.querySelectorAll('.edit-btn').forEach(function(b) {
    b.addEventListener('click', function() { toggleEditPanel(b.dataset.slug); });
  });
  el.querySelectorAll('.side-btn').forEach(function(b) {
    b.addEventListener('click', function() { setSide(b.dataset.slug, b.dataset.side); });
  });
  el.querySelectorAll('.opt-chk').forEach(function(chk) {
    chk.addEventListener('change', function() { onOptionalChange(chk.dataset.slug); });
  });
  el.querySelectorAll('.save-btn').forEach(function(b) {
    b.addEventListener('click', function() { saveMod(b.dataset.slug, b.dataset.name); });
  });
  el.querySelectorAll('.cancel-btn').forEach(function(b) {
    b.addEventListener('click', function() { toggleEditPanel(b.dataset.slug); });
  });
  mods.forEach(function(m) {
    var defInput = document.getElementById('def-' + m.slug);
    if (defInput) {
      defInput.addEventListener('change', function() {
        var lbl = document.getElementById('def-label-' + m.slug);
        if (lbl) lbl.textContent = defInput.checked ? 'Yes' : 'No';
      });
    }
  });
}

function toggleEditPanel(slug) {
  var panel = document.getElementById('edit-' + slug);
  if (!panel) return;
  panel.classList.toggle('open');
}

function setSide(slug, side) {
  var grp = document.getElementById('seg-' + slug);
  if (!grp) return;
  grp.querySelectorAll('.seg-btn').forEach(function(b) {
    b.classList.toggle('active', b.textContent.trim() === side);
  });
}

function getSelectedSide(slug) {
  var grp = document.getElementById('seg-' + slug);
  if (!grp) return 'both';
  var active = grp.querySelector('.seg-btn.active');
  return active ? active.textContent.trim() : 'both';
}

function onOptionalChange(slug) {
  var chk = document.getElementById('opt-' + slug);
  var lbl = document.getElementById('opt-label-' + slug);
  var defRow = document.getElementById('default-row-' + slug);
  if (lbl) lbl.textContent = chk.checked ? 'Yes' : 'No';
  if (defRow) defRow.style.display = chk.checked ? '' : 'none';
}

async function saveMod(slug, name) {
  var btn = document.getElementById('save-' + slug);
  if (btn) { btn.disabled = true; btn.textContent = 'Saving...'; }
  try {
    var side = getSelectedSide(slug);
    var optChk = document.getElementById('opt-' + slug);
    var defChk = document.getElementById('def-' + slug);
    var optional = optChk ? optChk.checked : false;
    var defaultOn = defChk ? defChk.checked : false;

    var res = await fetch('/api/mods/' + encodeURIComponent(slug) + '/settings', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ side: side, optional: optional, default: defaultOn })
    });
    var data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Save failed');
    toast('Saved: ' + name);
    // update local allMods entry
    var entry = allMods.find(function(m) { return m.slug === slug; });
    if (entry) {
      entry.side = side;
      entry.optional = optional;
      entry.default = defaultOn;
    }
    // close panel
    var panel = document.getElementById('edit-' + slug);
    if (panel) panel.classList.remove('open');
    // re-render just the badges in the row
    var modItem = document.getElementById('allmod-' + slug);
    if (modItem) {
      var metaEl = modItem.querySelector('.mod-meta');
      if (metaEl) {
        var modrinthLink = metaEl.querySelector('a') ? metaEl.querySelector('a').outerHTML : '';
        metaEl.innerHTML =
          '<span class="side-badge ' + sideBadgeClass(side) + '">' + escHtml(side) + '</span>' +
          (optional ? '<span class="optional-badge">optional</span>' : '') +
          (optional && defaultOn ? '<span class="default-badge">default on</span>' : '') +
          (modrinthLink ? ' ' + modrinthLink : '');
      }
    }
  } catch(e) {
    toast('Error: ' + e.message, 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = 'Save'; }
  }
}

// Initial load
loadMods();
</script>
</body>
</html>
"""


def gh_headers() -> dict:
    return {
        "Authorization": f"Bearer {GITHUB_PAT}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def parse_toml_simple(content: str) -> dict:
    try:
        return tomllib.loads(content)
    except Exception:
        return {}


def build_pw_toml(name: str, filename: str, project_id: str, version_id: str, url: str, hash512: str) -> str:
    return (
        f'name = "{name}"\n'
        f'filename = "{filename}"\n'
        f'side = "client"\n'
        f'\n'
        f'[download]\n'
        f'url = "{url}"\n'
        f'hash-format = "sha512"\n'
        f'hash = "{hash512}"\n'
        f'\n'
        f'[update]\n'
        f'[update.modrinth]\n'
        f'mod-id = "{project_id}"\n'
        f'version = "{version_id}"\n'
    )


def patch_toml_content(raw: str, side: str, optional: bool, default_on: bool) -> str:
    """Patch a .pw.toml string with new side/optional/default values."""

    # 1. Replace side field
    raw = re.sub(r'^side\s*=\s*"[^"]*"', f'side = "{side}"', raw, flags=re.MULTILINE)

    # 2. Handle [option] section
    option_block = f'[option]\noptional = true\ndefault = {"true" if default_on else "false"}\n'

    # Check if [option] section already exists
    option_section_re = re.compile(
        r'^\[option\][^\[]*',
        re.MULTILINE | re.DOTALL
    )
    # More precise: match [option] up to next section header or end of file
    option_section_precise = re.compile(
        r'^\[option\].*?(?=^\[|\Z)',
        re.MULTILINE | re.DOTALL
    )

    if optional:
        if option_section_precise.search(raw):
            # Replace existing [option] section
            raw = option_section_precise.sub(option_block, raw, count=1)
        else:
            # Append at end
            if not raw.endswith('\n'):
                raw += '\n'
            raw += '\n' + option_block
    else:
        # Remove [option] section entirely if it exists
        if option_section_precise.search(raw):
            raw = option_section_precise.sub('', raw, count=1)
        # Clean up any double blank lines left behind
        raw = re.sub(r'\n{3,}', '\n\n', raw)

    return raw


async def github_get_file(client: httpx.AsyncClient, path: str) -> Optional[dict]:
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{path}"
    r = await client.get(url, headers=gh_headers())
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


async def github_put_file(client: httpx.AsyncClient, path: str, content: str, message: str, sha: Optional[str] = None):
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{path}"
    encoded = base64.b64encode(content.encode()).decode()
    body: dict = {"message": message, "content": encoded}
    if sha:
        body["sha"] = sha
    r = await client.put(url, headers=gh_headers(), json=body)
    r.raise_for_status()
    return r.json()


async def github_delete_file(client: httpx.AsyncClient, path: str, message: str, sha: str):
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{path}"
    body = {"message": message, "sha": sha}
    r = await client.delete(url, headers=gh_headers(), json=body)
    r.raise_for_status()
    return r.json()


async def get_modrinth_project(client: httpx.AsyncClient, project_id: str) -> dict:
    r = await client.get(f"{MODRINTH_API}/project/{project_id}")
    r.raise_for_status()
    return r.json()


async def get_modrinth_versions(client: httpx.AsyncClient, project_id: str) -> list:
    r = await client.get(
        f"{MODRINTH_API}/project/{project_id}/version",
        params={
            "game_versions": f'["{GAME_VERSION}"]',
            "loaders": f'["{LOADER}"]',
        },
    )
    r.raise_for_status()
    return r.json()


async def fetch_and_parse_entry(client: httpx.AsyncClient, entry: dict, client_only: bool = False) -> Optional[dict]:
    """Fetch a .pw.toml entry from GitHub and return parsed mod info."""
    try:
        download_url = entry.get("download_url")
        if not download_url:
            return None
        fr = await client.get(download_url)
        if fr.status_code != 200:
            return None
        raw = fr.text
        data = parse_toml_simple(raw)
        side = data.get("side", "both")
        if client_only and side != "client":
            return None
        slug = entry["name"].replace(".pw.toml", "")
        mod_id = data.get("update", {}).get("modrinth", {}).get("mod-id", "")
        version_id = data.get("update", {}).get("modrinth", {}).get("version", "")
        option = data.get("option", {})
        return {
            "slug": slug,
            "name": data.get("name", slug),
            "version": version_id,
            "mod_id": mod_id,
            "sha": entry.get("sha", ""),
            "side": side,
            "optional": option.get("optional", False),
            "default": option.get("default", False),
            "icon": None,
        }
    except Exception:
        return None


async def enrich_icon(client: httpx.AsyncClient, mod: dict) -> dict:
    if not mod.get("mod_id"):
        return mod
    try:
        proj = await get_modrinth_project(client, mod["mod_id"])
        mod["icon"] = proj.get("icon_url", "")
    except Exception:
        pass
    return mod


async def list_all_pw_files(client: httpx.AsyncClient) -> list:
    """Return all .pw.toml entries from the mods directory."""
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/mods"
    r = await client.get(url, headers=gh_headers())
    if r.status_code == 404:
        return []
    if r.status_code == 401:
        raise HTTPException(401, "GitHub authentication failed — check GITHUB_PAT")
    r.raise_for_status()
    entries = r.json()
    return [e for e in entries if isinstance(e, dict) and e.get("name", "").endswith(".pw.toml")]


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML


@app.get("/api/mods")
async def list_mods():
    if not GITHUB_PAT or not GITHUB_REPO:
        raise HTTPException(500, "GITHUB_PAT and GITHUB_REPO environment variables are required")

    async with httpx.AsyncClient(timeout=30) as client:
        pw_files = await list_all_pw_files(client)

        tasks = [fetch_and_parse_entry(client, e, client_only=True) for e in pw_files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        mods = [r for r in results if isinstance(r, dict)]

        mods = list(await asyncio.gather(*[enrich_icon(client, m) for m in mods], return_exceptions=False))
        mods = [m for m in mods if isinstance(m, dict)]
        mods = sorted(mods, key=lambda m: m["name"].lower())

    return mods


@app.get("/api/all-mods")
async def list_all_mods():
    if not GITHUB_PAT or not GITHUB_REPO:
        raise HTTPException(500, "GITHUB_PAT and GITHUB_REPO environment variables are required")

    async with httpx.AsyncClient(timeout=60) as client:
        pw_files = await list_all_pw_files(client)

        tasks = [fetch_and_parse_entry(client, e, client_only=False) for e in pw_files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        mods = [r for r in results if isinstance(r, dict)]

        mods = list(await asyncio.gather(*[enrich_icon(client, m) for m in mods], return_exceptions=False))
        mods = [m for m in mods if isinstance(m, dict)]
        mods = sorted(mods, key=lambda m: m["name"].lower())

    return mods


@app.get("/api/search")
async def search_mods(q: str = ""):
    if not q.strip():
        return []
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            r = await client.get(
                f"{MODRINTH_API}/search",
                params={
                    "query": q,
                    "facets": f'[["project_type:mod"],["categories:{LOADER}"],["versions:{GAME_VERSION}"]]',
                    "limit": 20,
                },
            )
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(502, f"Modrinth API error: {e.response.status_code}")
        data = r.json()
        hits = data.get("hits", [])
        return [
            {
                "project_id": h.get("project_id"),
                "slug": h.get("slug"),
                "name": h.get("title"),
                "description": h.get("description"),
                "icon": h.get("icon_url"),
                "downloads": h.get("downloads", 0),
            }
            for h in hits
        ]


class AddModRequest(BaseModel):
    project_id: str
    version_id: Optional[str] = None


class PatchModRequest(BaseModel):
    side: str
    optional: bool
    default: bool


@app.post("/api/mods")
async def add_mod(req: AddModRequest):
    if not GITHUB_PAT or not GITHUB_REPO:
        raise HTTPException(500, "GITHUB_PAT and GITHUB_REPO environment variables are required")

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            project = await get_modrinth_project(client, req.project_id)
        except httpx.HTTPStatusError:
            raise HTTPException(400, f"Modrinth project not found: {req.project_id}")

        slug = project.get("slug", req.project_id)
        name = project.get("title", slug)

        if req.version_id:
            try:
                vr = await client.get(f"{MODRINTH_API}/version/{req.version_id}")
                vr.raise_for_status()
                version = vr.json()
            except httpx.HTTPStatusError:
                raise HTTPException(400, f"Version not found: {req.version_id}")
        else:
            try:
                versions = await get_modrinth_versions(client, req.project_id)
            except httpx.HTTPStatusError as e:
                raise HTTPException(400, f"Failed to fetch versions: {e.response.status_code}")
            if not versions:
                raise HTTPException(
                    400,
                    f"No versions found for '{name}' compatible with {GAME_VERSION} + {LOADER}",
                )
            version = versions[0]

        version_id = version.get("id", "")
        files = version.get("files", [])
        if not files:
            raise HTTPException(400, "No files found in this version")

        primary = next((f for f in files if f.get("primary")), files[0])
        file_url = primary.get("url", "")
        filename = primary.get("filename", f"{slug}.jar")
        hashes = primary.get("hashes", {})
        sha512 = hashes.get("sha512", "")

        if not sha512:
            raise HTTPException(400, "No sha512 hash found for this version file")

        toml_content = build_pw_toml(name, filename, req.project_id, version_id, file_url, sha512)

        path = f"mods/{slug}.pw.toml"
        existing = await github_get_file(client, path)
        sha = existing["sha"] if existing else None

        commit_msg = f"Add client mod: {name}"
        try:
            await github_put_file(client, path, toml_content, commit_msg, sha)
        except httpx.HTTPStatusError as e:
            raise HTTPException(500, f"GitHub commit failed: {e.response.text[:200]}")

    return {"ok": True, "slug": slug, "name": name, "version_id": version_id}


@app.patch("/api/mods/{slug}/settings")
async def patch_mod_settings(slug: str, req: PatchModRequest):
    if not GITHUB_PAT or not GITHUB_REPO:
        raise HTTPException(500, "GITHUB_PAT and GITHUB_REPO environment variables are required")

    valid_sides = {"client", "server", "both"}
    if req.side not in valid_sides:
        raise HTTPException(400, f"Invalid side value: {req.side}. Must be one of: {', '.join(valid_sides)}")

    async with httpx.AsyncClient(timeout=30) as client:
        path = f"mods/{slug}.pw.toml"
        existing = await github_get_file(client, path)
        if not existing:
            raise HTTPException(404, f"Mod file not found: {path}")

        sha = existing["sha"]
        raw_b64 = existing.get("content", "")
        try:
            raw_content = base64.b64decode(raw_b64.replace("\n", "")).decode("utf-8", errors="replace")
        except Exception:
            raise HTTPException(500, "Failed to decode existing file content")

        # Parse to get name for commit message
        data = parse_toml_simple(raw_content)
        name = data.get("name", slug)

        # Patch the raw TOML content
        patched = patch_toml_content(raw_content, req.side, req.optional, req.default)

        commit_msg = f"Update mod settings: {name}"
        try:
            await github_put_file(client, path, patched, commit_msg, sha)
        except httpx.HTTPStatusError as e:
            raise HTTPException(500, f"GitHub commit failed: {e.response.text[:200]}")

    return {"ok": True, "slug": slug, "name": name}


@app.delete("/api/mods/{slug}")
async def remove_mod(slug: str):
    if not GITHUB_PAT or not GITHUB_REPO:
        raise HTTPException(500, "GITHUB_PAT and GITHUB_REPO environment variables are required")

    async with httpx.AsyncClient(timeout=20) as client:
        path = f"mods/{slug}.pw.toml"
        existing = await github_get_file(client, path)
        if not existing:
            raise HTTPException(404, f"Mod file not found: {path}")

        sha = existing["sha"]
        raw_b64 = existing.get("content", "")
        try:
            raw_content = base64.b64decode(raw_b64.replace("\n", "")).decode("utf-8", errors="replace")
            data = parse_toml_simple(raw_content)
            name = data.get("name", slug)
        except Exception:
            name = slug

        commit_msg = f"Remove client mod: {name}"
        try:
            await github_delete_file(client, path, commit_msg, sha)
        except httpx.HTTPStatusError as e:
            raise HTTPException(500, f"GitHub delete failed: {e.response.text[:200]}")

    return {"ok": True, "slug": slug, "name": name}


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=PORT, reload=False)
