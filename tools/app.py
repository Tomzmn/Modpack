import os
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
<title>Packwiz Client Mod Manager</title>
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
  .mod-list { display: flex; flex-direction: column; gap: 0.6rem; }
  .mod-item {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.75rem 1rem;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    transition: border-color 0.2s;
  }
  .mod-item:hover { border-color: var(--accent); }
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
  .mod-meta { color: var(--text-muted); font-size: 0.8rem; margin-top: 0.2rem; }
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
</style>
</head>
<body>
<header>
  <div>
    <h1>Packwiz Mod Manager</h1>
    <div class="subtitle">Client-side mod management for 1.20.1 / Forge</div>
  </div>
  <div class="repo-tag" id="repoTag">Loading...</div>
</header>
<div class="container">
  <div class="grid">
    <!-- Left: installed mods -->
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
    <!-- Right: search -->
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
<div class="toast-container" id="toasts"></div>
<script>
let installedSlugs = new Set();
let installedMods = [];

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

async function loadMods() {
  document.getElementById('modList').innerHTML = '<div class="loading"><div class="spinner"></div> Loading...</div>';
  try {
    var res = await fetch('/api/mods');
    var data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to load mods');
    installedMods = data;
    installedSlugs = new Set(data.map(function(m) { return m.slug; }));
    document.getElementById('modCount').textContent = data.length;
    document.getElementById('repoTag').textContent = data.length + ' mods in pack';
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
    return '<div class="mod-item" id="mod-' + escHtml(m.slug) + '">' +
      (m.icon ? '<img class="mod-icon" src="' + escHtml(m.icon) + '" onerror="this.style.display=\'none\'" loading="lazy"/>' : '<div class="mod-icon-placeholder">M</div>') +
      '<div class="mod-info">' +
        '<div class="mod-name">' + escHtml(m.name) + '</div>' +
        '<div class="mod-meta">' +
          (m.version ? escHtml(m.version) : '') +
          (m.mod_id ? ' &middot; <a href="https://modrinth.com/mod/' + escHtml(m.mod_id) + '" target="_blank" rel="noopener">Modrinth</a>' : '') +
        '</div>' +
      '</div>' +
      '<div class="mod-actions">' +
        '<button class="sm danger" onclick="removeMod(\'' + escHtml(m.slug) + '\', \'' + escHtml(m.name.replace(/'/g,'')) + '\')" id="rm-' + escHtml(m.slug) + '">Remove</button>' +
      '</div>' +
    '</div>';
  }).join('');
}

async function removeMod(slug, name) {
  var btn = document.getElementById('rm-' + slug);
  if (!btn) return;
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
      (r.icon ? '<img class="mod-icon" src="' + escHtml(r.icon) + '" onerror="this.style.display=\'none\'" loading="lazy"/>' : '<div class="mod-icon-placeholder">M</div>') +
      '<div class="mod-info">' +
        '<div class="mod-name">' + escHtml(r.name) + '</div>' +
        '<div class="mod-desc">' + escHtml(r.description || '') + '</div>' +
        '<div class="mod-meta"><span class="dl-count">' + fmtDownloads(r.downloads) + ' downloads</span></div>' +
      '</div>' +
      '<div class="mod-actions">' +
        (already
          ? '<span class="already-badge">Added</span>'
          : '<button class="sm" onclick="addMod(\'' + escHtml(r.project_id) + '\', \'' + escHtml(r.slug) + '\', \'' + escHtml(r.name.replace(/'/g,'')) + '\')" id="add-' + escHtml(r.slug) + '">Add</button>'
        ) +
      '</div>' +
    '</div>';
  }).join('');
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


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML


@app.get("/api/mods")
async def list_mods():
    if not GITHUB_PAT or not GITHUB_REPO:
        raise HTTPException(500, "GITHUB_PAT and GITHUB_REPO environment variables are required")

    async with httpx.AsyncClient(timeout=30) as client:
        url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/mods"
        r = await client.get(url, headers=gh_headers())
        if r.status_code == 404:
            return []
        if r.status_code == 401:
            raise HTTPException(401, "GitHub authentication failed — check GITHUB_PAT")
        r.raise_for_status()
        entries = r.json()

        pw_files = [e for e in entries if isinstance(e, dict) and e.get("name", "").endswith(".pw.toml")]

        async def fetch_and_parse(entry: dict):
            try:
                download_url = entry.get("download_url")
                if not download_url:
                    return None
                fr = await client.get(download_url)
                if fr.status_code != 200:
                    return None
                raw = fr.text
                data = parse_toml_simple(raw)
                if data.get("side") != "client":
                    return None
                slug = entry["name"].replace(".pw.toml", "")
                mod_id = data.get("update", {}).get("modrinth", {}).get("mod-id", "")
                version_id = data.get("update", {}).get("modrinth", {}).get("version", "")
                return {
                    "slug": slug,
                    "name": data.get("name", slug),
                    "version": version_id,
                    "mod_id": mod_id,
                    "sha": entry.get("sha", ""),
                    "icon": None,
                }
            except Exception:
                return None

        tasks = [fetch_and_parse(e) for e in pw_files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        mods = [r for r in results if isinstance(r, dict)]

        async def enrich_icon(mod: dict):
            if not mod.get("mod_id"):
                return mod
            try:
                proj = await get_modrinth_project(client, mod["mod_id"])
                mod["icon"] = proj.get("icon_url", "")
            except Exception:
                pass
            return mod

        mods = list(await asyncio.gather(*[enrich_icon(m) for m in mods], return_exceptions=False))
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


@app.post("/api/mods")
async def add_mod(req: AddModRequest):
    if not GITHUB_PAT or not GITHUB_REPO:
        raise HTTPException(500, "GITHUB_PAT and GITHUB_REPO environment variables are required")

    async with httpx.AsyncClient(timeout=30) as client:
        # Get project info
        try:
            project = await get_modrinth_project(client, req.project_id)
        except httpx.HTTPStatusError:
            raise HTTPException(400, f"Modrinth project not found: {req.project_id}")

        slug = project.get("slug", req.project_id)
        name = project.get("title", slug)

        # Pick version
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
