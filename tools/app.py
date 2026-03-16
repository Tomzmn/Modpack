import os
import re
import base64
import tomllib
import asyncio
import hashlib
import shutil
import subprocess
import zipfile
import io
from typing import Optional
import httpx
from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
import uvicorn

GITHUB_PAT = os.environ.get("GITHUB_PAT", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "")
PORT = int(os.environ.get("PORT", "8080"))

CRAFTY_URL = os.environ.get("CRAFTY_URL", "")
CRAFTY_TOKEN = os.environ.get("CRAFTY_TOKEN", "")
CRAFTY_SERVER_ID = os.environ.get("CRAFTY_SERVER_ID", "")
PORTAINER_URL = os.environ.get("PORTAINER_URL", "https://portainer:9443")
PORTAINER_TOKEN = os.environ.get("PORTAINER_TOKEN", "")
PORTAINER_STACK_ID = os.environ.get("PORTAINER_STACK_ID", "")
PORTAINER_ENDPOINT_ID = os.environ.get("PORTAINER_ENDPOINT_ID", "2")

GITHUB_API = "https://api.github.com"
MODRINTH_API = "https://api.modrinth.com/v2"
GAME_VERSION = "1.20.1"
LOADER = "forge"

SERVER_MODS_DIR = "/server-mods"
PACKWIZ_BINARY = "/tmp/packwiz_bin"
PACKWIZ_REPO = "/tmp/modpack_repo"
packwiz_lock = asyncio.Lock()

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
  input[type="file"] {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.4rem 0.75rem;
    color: var(--text);
    font-size: 0.85rem;
    cursor: pointer;
  }
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
  button.warning-btn { background: #e0922e; }
  button.warning-btn:hover { background: #f0a030; }
  .mod-list { display: flex; flex-direction: column; gap: 0.6rem; }
  .mod-item {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
    transition: border-color 0.2s;
  }
  .mod-item:hover { border-color: var(--accent); }
  .mod-item.disabled-mod { opacity: 0.55; }
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
  .disabled-badge {
    background: rgba(224, 82, 82, 0.15);
    border: 1px solid var(--danger);
    color: var(--danger);
    border-radius: 999px;
    padding: 0.15rem 0.55rem;
    font-size: 0.72rem;
    font-weight: 700;
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
  .notinpack-badge {
    background: rgba(255,152,0,0.12);
    border: 1px solid rgba(255,152,0,0.5);
    color: #ffb74d;
    border-radius: 999px;
    padding: 0.15rem 0.55rem;
    font-size: 0.72rem;
    font-weight: 700;
  }
  .mod-version {
    font-size: 0.78rem;
    color: var(--text-muted);
    font-weight: 400;
    margin-left: 0.3rem;
  }
  .update-badge {
    background: rgba(224,146,46,0.18);
    border: 1px solid #e0922e;
    color: #f0b050;
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
  .edit-label { font-size: 0.85rem; color: var(--text-muted); font-weight: 600; min-width: 80px; }
  .edit-actions { display: flex; gap: 0.5rem; margin-top: 0.25rem; flex-wrap: wrap; }
  .edit-section-title {
    font-size: 0.78rem;
    font-weight: 700;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    border-bottom: 1px solid var(--border);
    padding-bottom: 0.4rem;
    margin-bottom: 0.25rem;
  }

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

  /* Updates tab */
  .updates-panel {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
  }
  .updates-toolbar {
    padding: 1rem 1.25rem;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }
  .updates-toolbar h2 { font-size: 1rem; font-weight: 600; }
  .update-arrow { color: var(--text-muted); font-size: 0.8rem; }
  .update-version-new { color: var(--success); font-size: 0.8rem; font-weight: 600; }
  .update-version-old { color: var(--text-muted); font-size: 0.8rem; }

  /* Upload section */
  .upload-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  /* Server tab */
  .server-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 1.5rem; }
  @media (max-width: 900px) { .server-grid { grid-template-columns: 1fr; } }
  .status-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.25rem;
  }
  .status-card h3 { font-size: 0.85rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 1rem; }
  .status-row { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.6rem; }
  .status-dot {
    width: 12px; height: 12px;
    border-radius: 50%;
    flex-shrink: 0;
    background: var(--border);
  }
  .status-dot.running { background: var(--success); box-shadow: 0 0 6px rgba(76,175,130,0.6); }
  .status-dot.stopped { background: var(--danger); }
  .status-label { font-size: 1rem; font-weight: 700; }
  .stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; margin-top: 0.75rem; }
  .stat-item { background: var(--surface2); border: 1px solid var(--border); border-radius: 6px; padding: 0.5rem 0.75rem; }
  .stat-name { font-size: 0.72rem; color: var(--text-muted); font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; }
  .stat-value { font-size: 1rem; font-weight: 700; margin-top: 0.15rem; }
  .action-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.25rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }
  .action-card h3 { font-size: 0.85rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em; }
  .action-btns { display: flex; gap: 0.75rem; flex-wrap: wrap; }
  .cmd-row { display: flex; gap: 0.5rem; }
  .log-panel {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
  }
  .log-toolbar {
    padding: 0.75rem 1.25rem;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }
  .log-toolbar h3 { font-size: 0.9rem; font-weight: 600; }
  .log-status { font-size: 0.78rem; color: var(--text-muted); margin-left: auto; }
  .log-box {
    background: #0a0c10;
    font-family: 'Consolas', 'Fira Code', 'Courier New', monospace;
    font-size: 0.82rem;
    color: #c8d0e0;
    height: 400px;
    overflow-y: scroll;
    padding: 1rem;
    line-height: 1.5;
    white-space: pre-wrap;
    word-break: break-all;
  }

  /* Docs tab */
  .docs-panel { max-width: 860px; margin: 0 auto; display: flex; flex-direction: column; gap: 2rem; }
  .docs-section {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.5rem 2rem;
  }
  .docs-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 0.75rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--border);
  }
  .docs-subtitle {
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--text);
    margin-top: 1.25rem;
    margin-bottom: 0.6rem;
  }
  .docs-p { color: var(--text-muted); font-size: 0.9rem; line-height: 1.65; margin-bottom: 0.75rem; }
  .docs-p:last-child { margin-bottom: 0; }
  .docs-p code, .docs-info code, .docs-warn code { background: var(--surface2); border: 1px solid var(--border); border-radius: 4px; padding: 0.1rem 0.4rem; font-size: 0.82rem; color: #a39fff; font-family: 'Consolas', monospace; }
  .docs-table-wrap { overflow-x: auto; margin: 0.75rem 0; }
  .docs-table { width: 100%; border-collapse: collapse; font-size: 0.87rem; }
  .docs-table thead tr { background: var(--surface2); }
  .docs-table th { text-align: left; padding: 0.55rem 0.9rem; color: var(--text-muted); font-weight: 600; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.04em; border-bottom: 1px solid var(--border); }
  .docs-table td { padding: 0.65rem 0.9rem; color: var(--text-muted); border-bottom: 1px solid var(--border); vertical-align: top; line-height: 1.5; }
  .docs-table td:first-child { white-space: nowrap; }
  .docs-table tr:last-child td { border-bottom: none; }
  .docs-badge { border-radius: 999px; padding: 0.2rem 0.65rem; font-size: 0.75rem; font-weight: 700; display: inline-block; }
  .docs-badge-purple { background: rgba(108,99,255,0.18); border: 1px solid #6c63ff; color: #a39fff; }
  .docs-badge-green { background: rgba(76,175,130,0.18); border: 1px solid #4caf82; color: #6dd6a6; }
  .docs-badge-red { background: rgba(224,82,82,0.18); border: 1px solid #e05252; color: #f09090; }
  .docs-badge-gray { background: var(--surface2); border: 1px solid var(--border); color: var(--text-muted); }
  .docs-info { background: rgba(108,99,255,0.08); border: 1px solid rgba(108,99,255,0.3); border-radius: 8px; padding: 0.7rem 1rem; font-size: 0.85rem; color: #a39fff; margin-top: 0.75rem; line-height: 1.5; }
  .docs-warn { background: rgba(255,152,0,0.08); border: 1px solid rgba(255,152,0,0.3); border-radius: 8px; padding: 0.7rem 1rem; font-size: 0.85rem; color: #ffb74d; margin-top: 0.75rem; line-height: 1.5; }
  .docs-ol { padding-left: 1.4rem; color: var(--text-muted); font-size: 0.9rem; line-height: 2; margin-bottom: 0.75rem; }
  .docs-ol li { padding-left: 0.25rem; }
  .docs-flow { display: flex; flex-direction: column; gap: 0; margin-top: 0.75rem; }
  .docs-flow-step { display: flex; align-items: center; gap: 0.75rem; background: var(--surface2); border: 1px solid var(--border); border-radius: 8px; padding: 0.75rem 1rem; font-size: 0.88rem; color: var(--text-muted); }
  .docs-flow-num { background: var(--accent); color: #fff; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; font-size: 0.78rem; font-weight: 700; flex-shrink: 0; }
  .docs-flow-arrow { text-align: center; color: var(--border); font-size: 1.1rem; line-height: 1.2; }

  /* Pack tab */
  .pack-layout { display: flex; flex-direction: column; gap: 1.5rem; }
  .pack-panel { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; }
  .packwiz-presets { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.75rem; }
  .packwiz-output {
    background: #0a0c10;
    font-family: 'Consolas', 'Fira Code', monospace;
    font-size: 0.82rem;
    color: #c8d0e0;
    border-radius: 8px;
    padding: 0.85rem 1rem;
    margin-top: 0.75rem;
    min-height: 80px;
    max-height: 340px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-all;
    display: none;
  }
  .packwiz-output.visible { display: block; }
  .pack-info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
  .pack-info-item { background: var(--surface2); border: 1px solid var(--border); border-radius: 8px; padding: 0.6rem 0.9rem; }
  .pack-info-label { font-size: 0.72rem; color: var(--text-muted); font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; }
  .pack-info-value { font-size: 0.95rem; font-weight: 700; margin-top: 0.15rem; word-break: break-all; }
  /* TOML editor */
  .toml-section { display: none; margin-top: 0.5rem; }
  .toml-section.open { display: block; }
  .toml-editor {
    width: 100%;
    background: #0a0c10;
    border: 1px solid var(--border);
    border-radius: 8px;
    color: #c8d0e0;
    font-family: 'Consolas', 'Fira Code', monospace;
    font-size: 0.82rem;
    padding: 0.75rem;
    min-height: 200px;
    resize: vertical;
    outline: none;
    line-height: 1.5;
  }
  .toml-editor:focus { border-color: var(--accent); }
  .toml-toggle { cursor: pointer; user-select: none; }
  .toml-toggle:hover { color: var(--accent); }

  /* Mods tab layout */
  .mods-layout { display: grid; grid-template-columns: 1fr 360px; gap: 1.5rem; align-items: start; }
  @media (max-width: 1100px) { .mods-layout { grid-template-columns: 1fr; } }
  .mods-main { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; }
  .mods-side { position: sticky; top: 1rem; }
  .mods-toolbar { padding: 1rem 1.25rem; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; }
  .mods-toolbar input { max-width: 200px; flex: none; }
  .mods-main .mod-list { padding: 1rem 1.25rem; }
  .filter-chips { display: flex; gap: 0.35rem; flex-wrap: wrap; }
  .chip { background: transparent; border: 1px solid var(--border); border-radius: 999px; color: var(--text-muted); padding: 0.25rem 0.75rem; font-size: 0.78rem; font-weight: 600; cursor: pointer; transition: border-color 0.15s, color 0.15s, background 0.15s; }
  .chip:hover { border-color: var(--accent); color: var(--accent); background: transparent; }
  .chip.active { background: var(--accent); border-color: var(--accent); color: #fff; }
</style>
</head>
<body>
<header>
  <div>
    <h1>Packwiz Mod Manager</h1>
    <div class="subtitle">Mod management for 1.20.1 / Forge</div>
  </div>
  <div class="repo-tag" id="repoTag">Loading...</div>
  <button class="ghost sm" id="syncBtn" onclick="triggerSync()" style="margin-left:1rem">Sync to GitHub</button>
</header>
<div class="container">
  <div class="tabs">
    <button class="tab-btn active" id="tabbtn-mods">Mods</button>
    <button class="tab-btn" id="tabbtn-add">Add Mod</button>
    <button class="tab-btn" id="tabbtn-updates">Updates</button>
    <button class="tab-btn" id="tabbtn-pack">Pack</button>
    <button class="tab-btn" id="tabbtn-server">Server</button>
    <button class="tab-btn" id="tabbtn-docs">Docs</button>
  </div>

  <!-- MODS TAB -->
  <div class="tab-panel active" id="tab-mods">
    <div class="mods-main">
      <div class="mods-toolbar">
        <input type="text" id="allModsFilter" placeholder="Filter by name..."/>
        <div class="filter-chips" id="filterChips">
          <button class="chip active" data-filter="all">All</button>
          <button class="chip" data-filter="client">Client</button>
          <button class="chip" data-filter="server">Server</button>
          <button class="chip" data-filter="both">Both</button>
          <button class="chip" data-filter="notinpack">Not in pack</button>
          <button class="chip" data-filter="disabled">Disabled</button>
        </div>
        <span class="filter-count" id="allModsCount"></span>
        <button class="ghost sm" id="refreshAllBtn">Refresh</button>
      </div>
      <div id="allModsList" class="mod-list">
        <div class="loading"><div class="spinner"></div> Loading...</div>
      </div>
    </div>
  </div>

  <!-- ADD MOD TAB -->
  <div class="tab-panel" id="tab-add">
    <div class="panel">
      <div class="panel-header"><h2>Add Mod via Modrinth</h2></div>
      <div class="panel-body">
        <div class="search-bar">
          <input type="text" id="searchInput" placeholder="Search Modrinth..."/>
          <button id="searchBtn">Search</button>
        </div>
        <div id="searchResults" class="mod-list">
          <div class="empty">Search for mods to add.</div>
        </div>
      </div>
    </div>
  </div>

  <!-- PACK TAB -->
  <div class="tab-panel" id="tab-pack">
    <div class="pack-layout">

      <div class="pack-panel">
        <div class="panel-header">
          <h2>Pack Info</h2>
          <button class="ghost sm" id="packInfoRefreshBtn" style="margin-left:auto">Refresh</button>
        </div>
        <div class="panel-body" id="packInfoBody">
          <div class="loading"><div class="spinner"></div> Loading...</div>
        </div>
      </div>

      <div class="pack-panel">
        <div class="panel-header"><h2>Packwiz</h2></div>
        <div class="panel-body">
          <div class="packwiz-presets">
            <button class="ghost sm pw-preset" data-cmd="refresh">Refresh index</button>
            <button class="ghost sm pw-preset" data-cmd="update --all">Update all</button>
          </div>
          <div class="search-bar">
            <input type="text" id="pwCmdInput" placeholder="e.g. modrinth add sodium -y"/>
            <button id="pwRunBtn">Run</button>
          </div>
          <div class="packwiz-output" id="pwOutput"></div>
        </div>
      </div>

    </div>
  </div>

  <!-- UPDATES TAB -->
  <div class="tab-panel" id="tab-updates">
    <div class="updates-panel">
      <div class="updates-toolbar">
        <h2>Mod Updates</h2>
        <button id="checkUpdatesBtn">Check for Updates</button>
        <button class="success-btn" id="updateAllBtn" style="display:none">Update All</button>
        <span class="filter-count" id="updatesCount"></span>
      </div>
      <div class="panel-body">
        <div id="updatesList" class="mod-list">
          <div class="empty">Click "Check for Updates" to scan all mods.</div>
        </div>
      </div>
    </div>
  </div>

  <!-- SERVER TAB -->
  <div class="tab-panel" id="tab-server">
    <div class="server-grid">
      <div class="status-card">
        <h3>Server Status</h3>
        <div class="status-row">
          <div class="status-dot" id="srvDot"></div>
          <span class="status-label" id="srvStatusLabel">Loading...</span>
        </div>
        <div class="stat-grid">
          <div class="stat-item">
            <div class="stat-name">Players</div>
            <div class="stat-value" id="srvPlayers">-</div>
          </div>
          <div class="stat-item">
            <div class="stat-name">MSPT</div>
            <div class="stat-value" id="srvMspt">-</div>
          </div>
          <div class="stat-item">
            <div class="stat-name">CPU</div>
            <div class="stat-value" id="srvCpu">-</div>
          </div>
          <div class="stat-item">
            <div class="stat-name">RAM</div>
            <div class="stat-value" id="srvRam">-</div>
          </div>
        </div>
      </div>
      <div class="action-card">
        <h3>Actions</h3>
        <div class="action-btns">
          <button class="success-btn" id="srvStartBtn">Start</button>
          <button class="danger" id="srvStopBtn">Stop</button>
          <button class="warning-btn" id="srvRestartBtn">Restart</button>
        </div>
        <div>
          <h3 style="margin-bottom:0.5rem">Send Command</h3>
          <div class="cmd-row">
            <input type="text" id="srvCmdInput" placeholder="e.g. say Hello"/>
            <button id="srvSendBtn">Send</button>
          </div>
        </div>
      </div>
    </div>
    <div class="log-panel">
      <div class="log-toolbar">
        <h3>Server Logs</h3>
        <button class="ghost sm" id="srvClearLogBtn">Clear</button>
        <span class="log-status" id="srvLogStatus">Disconnected</span>
      </div>
      <div class="log-box" id="srvLogBox"></div>
    </div>
  </div>

  <!-- DOCS TAB -->
  <div class="tab-panel" id="tab-docs">
    <div class="docs-panel">

      <div class="docs-section">
        <h2 class="docs-title">Vue d&apos;ensemble</h2>
        <p class="docs-p">Cette interface permet de g&eacute;rer le modpack Minecraft 1.20.1 / Forge distribu&eacute; via <strong>packwiz</strong> et <strong>Prism Launcher</strong>. Les mods sont stock&eacute;s dans le repo GitHub <code>Tomzmn/Modpack</code>. Chaque modification faite ici est committ&eacute;e automatiquement sur GitHub et sync&eacute;e aux joueurs au prochain lancement de leur jeu.</p>
      </div>

      <div class="docs-section">
        <h2 class="docs-title">Onglet &laquo; Client Mods &raquo;</h2>
        <p class="docs-p">Affiche uniquement les mods marqu&eacute;s <code>side = "client"</code> dans le pack &mdash; ceux install&eacute;s exclusivement c&ocirc;t&eacute; joueur, absents du serveur.</p>
        <div class="docs-table-wrap">
          <table class="docs-table">
            <thead><tr><th>Action</th><th>Description</th></tr></thead>
            <tbody>
              <tr><td><span class="docs-badge docs-badge-purple">Recherche Modrinth</span></td><td>Tape un nom, s&eacute;lectionne le mod, choisis le side (client / both / server) puis clique <strong>Add</strong>. Le .pw.toml est cr&eacute;&eacute; sur GitHub.</td></tr>
              <tr><td><span class="docs-badge docs-badge-red">Remove</span></td><td>Supprime le .pw.toml du mod sur GitHub. Prism retirera le mod au prochain lancement.</td></tr>
              <tr><td><span class="docs-badge docs-badge-gray">Refresh</span></td><td>Recharge la liste depuis GitHub.</td></tr>
            </tbody>
          </table>
        </div>
        <div class="docs-info">Les mods ajout&eacute;s avec side <code>both</code> ou <code>server</code> apparaissent dans l&apos;onglet <strong>All Mods</strong> uniquement.</div>
      </div>

      <div class="docs-section">
        <h2 class="docs-title">Onglet &laquo; All Mods &raquo;</h2>
        <p class="docs-p">Affiche <strong>tous</strong> les mods du pack (client, server, both) avec leurs param&egrave;tres complets. Utilise le filtre en haut pour rechercher par nom.</p>
        <div class="docs-table-wrap">
          <table class="docs-table">
            <thead><tr><th>Action</th><th>Description</th></tr></thead>
            <tbody>
              <tr><td><span class="docs-badge docs-badge-gray">Edit</span></td><td>Ouvre le panneau d&apos;&eacute;dition inline du mod.</td></tr>
              <tr><td><strong>Side</strong></td><td><code>client</code> = install&eacute; uniquement c&ocirc;t&eacute; joueur &bull; <code>server</code> = uniquement sur le serveur (invisible pour Prism) &bull; <code>both</code> = install&eacute; partout.</td></tr>
              <tr><td><strong>Optional</strong></td><td>Si activ&eacute;, Prism propose le mod comme optionnel. Le joueur peut le d&eacute;cocher &agrave; l&apos;installation.</td></tr>
              <tr><td><strong>Default</strong></td><td>Si Optional est activ&eacute;, contr&ocirc;le si le mod est coch&eacute; par d&eacute;faut dans Prism.</td></tr>
              <tr><td><strong>Toggle Activ&eacute;</strong></td><td>D&eacute;sactive le mod : renomme le .pw.toml en .pw.toml.disabled sur GitHub <em>et</em> renomme le .jar en .jar.disabled dans le dossier mods du serveur. Le serveur doit &ecirc;tre red&eacute;marr&eacute; pour que l&apos;effet prenne effet.</td></tr>
              <tr><td><span class="docs-badge docs-badge-green">Update</span></td><td>Pour les mods Modrinth : met &agrave; jour vers la derni&egrave;re version compatible 1.20.1/Forge.</td></tr>
              <tr><td><strong>Upload JAR</strong></td><td>Remplace le mod par un fichier .jar upload&eacute; manuellement (override &mdash; pas de m&eacute;tadonn&eacute;es Modrinth). Utile pour des mods non disponibles sur Modrinth.</td></tr>
              <tr><td><span class="docs-badge docs-badge-gray">Save</span></td><td>Enregistre les modifications de side / optional / default sur GitHub.</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="docs-section">
        <h2 class="docs-title">Onglet &laquo; Updates &raquo;</h2>
        <p class="docs-p">V&eacute;rifie les mises &agrave; jour disponibles sur Modrinth pour tous les mods du pack ayant un <code>mod-id</code> Modrinth.</p>
        <div class="docs-table-wrap">
          <table class="docs-table">
            <thead><tr><th>Action</th><th>Description</th></tr></thead>
            <tbody>
              <tr><td><span class="docs-badge docs-badge-purple">Check for Updates</span></td><td>Interroge l&apos;API Modrinth pour chaque mod. Affiche la liste des mods avec une version plus r&eacute;cente disponible.</td></tr>
              <tr><td><span class="docs-badge docs-badge-green">Update</span></td><td>Met &agrave; jour un mod individuel vers la derni&egrave;re version compatible.</td></tr>
              <tr><td><span class="docs-badge docs-badge-green">Update All</span></td><td>Met &agrave; jour tous les mods en attente s&eacute;quentiellement.</td></tr>
            </tbody>
          </table>
        </div>
        <div class="docs-warn">Les mods en override (jar upload&eacute; manuellement) n&apos;ont pas de <code>mod-id</code> Modrinth et ne sont pas v&eacute;rifi&eacute;s.</div>
      </div>

      <div class="docs-section">
        <h2 class="docs-title">Onglet &laquo; Server &raquo;</h2>
        <p class="docs-p">Contr&ocirc;le le serveur Minecraft via l&apos;API Crafty Controller. Affiche l&apos;&eacute;tat en temps r&eacute;el et les logs live.</p>
        <div class="docs-table-wrap">
          <table class="docs-table">
            <thead><tr><th>&Eacute;l&eacute;ment</th><th>Description</th></tr></thead>
            <tbody>
              <tr><td><strong>Statut</strong></td><td>Rafra&icirc;chi automatiquement toutes les 5 secondes. Indique Running / Stopped, joueurs connect&eacute;s, MSPT, CPU et RAM.</td></tr>
              <tr><td><span class="docs-badge docs-badge-green">Start</span></td><td>D&eacute;marre le serveur via Crafty.</td></tr>
              <tr><td><span class="docs-badge docs-badge-red">Stop</span></td><td>Arr&ecirc;te le serveur (envoie la commande stop).</td></tr>
              <tr><td><span class="docs-badge docs-badge-gray">Restart</span></td><td>Red&eacute;marre le serveur.</td></tr>
              <tr><td><strong>Send Command</strong></td><td>Envoie une commande directement dans la console du serveur (ex&nbsp;: <code>say Bonjour</code>, <code>op Tomzmn</code>). Appuie sur Entr&eacute;e ou clique Send.</td></tr>
              <tr><td><strong>Logs</strong></td><td>Flux de logs en temps r&eacute;el via SSE. Se connecte automatiquement quand l&apos;onglet Server est ouvert. Le bouton Clear vide l&apos;affichage.</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="docs-section">
        <h2 class="docs-title">Bouton &laquo; Sync to GitHub &raquo;</h2>
        <p class="docs-p">D&eacute;clenche imm&eacute;diatement la stack Docker <strong>modpack-sync</strong> via l&apos;API Portainer. Cette stack compare les mods du serveur avec le repo GitHub et committe les diff&eacute;rences. Utile apr&egrave;s avoir ajout&eacute; ou supprim&eacute; un mod manuellement dans le dossier du serveur.</p>
        <div class="docs-info">La sync est aussi d&eacute;clench&eacute;e automatiquement &agrave; chaque d&eacute;marrage du serveur via la commande Java dans Crafty.</div>
      </div>

      <div class="docs-section">
        <h2 class="docs-title">Comment les joueurs re&ccedil;oivent les mods</h2>
        <p class="docs-p">Les joueurs utilisent <strong>Prism Launcher</strong> avec le profil pr&eacute;configur&eacute;. Un hook pre-launch appelle automatiquement <code>packwiz-installer</code> qui&nbsp;:</p>
        <ol class="docs-ol">
          <li>T&eacute;l&eacute;charge le <code>pack.toml</code> depuis GitHub</li>
          <li>Compare avec les mods install&eacute;s localement</li>
          <li>T&eacute;l&eacute;charge les nouveaux mods / supprime les anciens</li>
          <li>Lance le jeu</li>
        </ol>
        <div class="docs-info">Le joueur n&apos;a rien &agrave; faire &mdash; la sync est transparente &agrave; chaque lancement.</div>

        <h3 class="docs-subtitle">Flux complet d&apos;un changement de mod</h3>
        <div class="docs-flow">
          <div class="docs-flow-step"><span class="docs-flow-num">1</span><span>Tu ajoutes/retires un mod sur le serveur</span></div>
          <div class="docs-flow-arrow">&#8595;</div>
          <div class="docs-flow-step"><span class="docs-flow-num">2</span><span>Le serveur red&eacute;marre (ou tu cliques <em>Sync to GitHub</em>)</span></div>
          <div class="docs-flow-arrow">&#8595;</div>
          <div class="docs-flow-step"><span class="docs-flow-num">3</span><span>modpack-sync d&eacute;tecte le changement et push sur GitHub</span></div>
          <div class="docs-flow-arrow">&#8595;</div>
          <div class="docs-flow-step"><span class="docs-flow-num">4</span><span>Le joueur lance Prism &rarr; sync automatique &rarr; jeu &agrave; jour</span></div>
        </div>
      </div>

      <div class="docs-section">
        <h2 class="docs-title">Ajouter un mod client uniquement</h2>
        <ol class="docs-ol">
          <li>Va dans l&apos;onglet <strong>Client Mods</strong></li>
          <li>Recherche le mod dans le champ Modrinth</li>
          <li>S&eacute;lectionne le side <code>client</code></li>
          <li>Clique <strong>Add</strong></li>
        </ol>
        <div class="docs-info">Le mod sera install&eacute; uniquement c&ocirc;t&eacute; joueur. Il ne sera jamais supprim&eacute; par la sync serveur.</div>
      </div>

      <div class="docs-section">
        <h2 class="docs-title">D&eacute;sactiver un mod temporairement</h2>
        <ol class="docs-ol">
          <li>Va dans l&apos;onglet <strong>All Mods</strong></li>
          <li>Clique <strong>Edit</strong> sur le mod concern&eacute;</li>
          <li>Bascule le toggle <strong>Activ&eacute;</strong></li>
        </ol>
        <p class="docs-p">Le .pw.toml est renomm&eacute; en .pw.toml.disabled sur GitHub et le .jar en .jar.disabled sur le serveur. Red&eacute;marre le serveur pour appliquer. Les joueurs n&apos;auront plus le mod au prochain lancement de Prism.</p>
      </div>

      <div class="docs-section">
        <h2 class="docs-title">Mods sans Modrinth (jars manuels)</h2>
        <p class="docs-p">Certains mods ne sont pas sur Modrinth (mods priv&eacute;s, patches custom&hellip;). Pour les g&eacute;rer&nbsp;:</p>
        <ol class="docs-ol">
          <li>Copie le .jar dans le dossier mods du serveur</li>
          <li>Clique <strong>Sync to GitHub</strong> &mdash; le mod est d&eacute;tect&eacute; comme override et ajout&eacute; au repo</li>
        </ol>
        <p class="docs-p">Ou depuis All Mods &rarr; Edit &rarr; <strong>Upload JAR</strong> pour le mettre directement sur GitHub sans passer par le serveur.</p>
        <div class="docs-warn">Les mods en override ne sont pas v&eacute;rifi&eacute;s pour les mises &agrave; jour automatiques.</div>
      </div>

    </div>
  </div>

</div>
<div class="toast-container" id="toasts"></div>
<script>
var installedSlugs = new Set();
var installedMods = [];
var allMods = [];
var updatesData = [];
var activeTab = 'mods';
var allModsLoaded = false;
var serverStatusInterval = null;
var logEventSource = null;
var serverRunning = false;

(function() {
  document.getElementById('tabbtn-mods').addEventListener('click', function() { switchTab('mods'); });
  document.getElementById('tabbtn-add').addEventListener('click', function() { switchTab('add'); });
  document.getElementById('tabbtn-updates').addEventListener('click', function() { switchTab('updates'); });
  document.getElementById('tabbtn-pack').addEventListener('click', function() { switchTab('pack'); });
  document.getElementById('tabbtn-server').addEventListener('click', function() { switchTab('server'); });
  document.getElementById('tabbtn-docs').addEventListener('click', function() { switchTab('docs'); });
  document.getElementById('refreshAllBtn').addEventListener('click', function() { allModsLoaded = false; loadAllMods(); });
  document.getElementById('searchBtn').addEventListener('click', function() { doSearch(); });
  document.getElementById('searchInput').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') doSearch();
  });
  document.getElementById('allModsFilter').addEventListener('input', function() { filterAllMods(); });
  document.querySelectorAll('#filterChips .chip').forEach(function(chip) {
    chip.addEventListener('click', function() {
      document.querySelectorAll('#filterChips .chip').forEach(function(c) { c.classList.remove('active'); });
      chip.classList.add('active');
      filterAllMods();
    });
  });
  document.getElementById('checkUpdatesBtn').addEventListener('click', function() { checkUpdates(); });
  document.getElementById('updateAllBtn').addEventListener('click', function() { updateAll(); });
  document.getElementById('srvStartBtn').addEventListener('click', function() { serverAction('start_server'); });
  document.getElementById('srvStopBtn').addEventListener('click', function() { serverAction('stop_server'); });
  document.getElementById('srvRestartBtn').addEventListener('click', function() { serverAction('restart_server'); });
  document.getElementById('srvSendBtn').addEventListener('click', function() { sendServerCommand(); });
  document.getElementById('srvCmdInput').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') sendServerCommand();
  });
  document.getElementById('srvClearLogBtn').addEventListener('click', function() {
    document.getElementById('srvLogBox').textContent = '';
  });
  loadAllMods();
})();

function switchTab(tab) {
  activeTab = tab;
  var tabs = ['mods', 'add', 'updates', 'pack', 'server', 'docs'];
  var btnIds = ['tabbtn-mods', 'tabbtn-add', 'tabbtn-updates', 'tabbtn-pack', 'tabbtn-server', 'tabbtn-docs'];
  tabs.forEach(function(t, i) {
    document.getElementById(btnIds[i]).classList.toggle('active', t === tab);
    document.getElementById('tab-' + t).classList.toggle('active', t === tab);
  });
  if (tab === 'mods' && !allModsLoaded) {
    loadAllMods();
  }
  if (tab === 'pack') {
    loadPackInfo();
  }
  if (tab === 'server') {
    startServerTab();
  } else {
    stopServerTab();
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
          '<button class="sm danger rm-btn" data-slug="' + escHtml(m.slug) + '" data-name="' + escHtml(m.name) + '" id="rm-' + escHtml(m.slug) + '">Remove</button>' +
        '</div>' +
      '</div>' +
    '</div>';
  }).join('');
  el.querySelectorAll('.rm-btn').forEach(function(btn) {
    btn.addEventListener('click', function() { removeMod(btn.dataset.slug, btn.dataset.name, btn); });
  });
}

async function removeMod(slug, name, btn) {
  if (btn) { btn.disabled = true; btn.textContent = '...'; }
  try {
    var res = await fetch('/api/mods/' + encodeURIComponent(slug), { method: 'DELETE' });
    var data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Remove failed');
    toast('Removed: ' + name);
    allModsLoaded = false;
    await loadAllMods();
  } catch(e) {
    toast('Error: ' + e.message, 'error');
    if (btn) { btn.disabled = false; btn.textContent = 'Remove'; }
  }
}

function removeModConfirm(slug, name, btn) {
  if (btn.dataset.confirming === '1') {
    clearTimeout(btn._confirmTimer);
    btn.dataset.confirming = '0';
    btn.textContent = 'Removing...';
    btn.disabled = true;
    fetch('/api/mods/' + encodeURIComponent(slug), { method: 'DELETE' })
      .then(function(res) { return res.json().then(function(d) { return {ok: res.ok, d: d}; }); })
      .then(function(r) {
        if (!r.ok) throw new Error(r.d.detail || 'Remove failed');
        toast('Removed: ' + name);
        var item = document.getElementById('allmod-' + slug);
        if (item) item.remove();
        allMods = allMods.filter(function(m) { return m.slug !== slug; });
        installedSlugs.delete(slug);
        document.getElementById('allModsCount').textContent = allMods.length + ' mod' + (allMods.length !== 1 ? 's' : '');
      })
      .catch(function(e) {
        toast('Error: ' + e.message, 'error');
        btn.disabled = false;
        btn.textContent = 'Remove';
        btn.classList.remove('danger');
      });
  } else {
    btn.dataset.confirming = '1';
    btn.textContent = 'Confirm?';
    btn.classList.add('danger');
    btn._confirmTimer = setTimeout(function() {
      btn.dataset.confirming = '0';
      btn.textContent = 'Remove';
      btn.classList.remove('danger');
    }, 3000);
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
            : '<div class="seg-group search-side-seg" id="sseg-' + escHtml(r.slug) + '">' +
                '<button class="seg-btn active" data-side="client">client</button>' +
                '<button class="seg-btn" data-side="both">both</button>' +
                '<button class="seg-btn" data-side="server">server</button>' +
              '</div>' +
              '<button class="sm add-btn" data-pid="' + escHtml(r.project_id) + '" data-slug="' + escHtml(r.slug) + '" data-name="' + escHtml(r.name) + '" id="add-' + escHtml(r.slug) + '">Add</button>'
          ) +
        '</div>' +
      '</div>' +
    '</div>';
  }).join('');
  el.querySelectorAll('.search-side-seg').forEach(function(seg) {
    seg.querySelectorAll('.seg-btn').forEach(function(b) {
      b.addEventListener('click', function() {
        seg.querySelectorAll('.seg-btn').forEach(function(x) { x.classList.remove('active'); });
        b.classList.add('active');
      });
    });
  });
  el.querySelectorAll('.add-btn').forEach(function(b) {
    b.addEventListener('click', function() {
      var seg = document.getElementById('sseg-' + b.dataset.slug);
      var side = 'client';
      if (seg) {
        var active = seg.querySelector('.seg-btn.active');
        if (active) side = active.dataset.side;
      }
      addMod(b.dataset.pid, b.dataset.slug, b.dataset.name, side);
    });
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

async function addMod(projectId, slug, name, side) {
  side = side || 'client';
  var btn = document.getElementById('add-' + slug);
  if (btn) { btn.disabled = true; btn.textContent = 'Adding...'; }
  try {
    var res = await fetch('/api/mods', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id: projectId, side: side })
    });
    var data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Add failed');
    toast('Added: ' + name);
    allModsLoaded = false;
    await loadAllMods();
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
    installedMods = data.filter(function(m) { return m.in_pack !== false; });
    installedSlugs = new Set(installedMods.map(function(m) { return m.slug; }));
    var inPackCount = installedMods.length;
    document.getElementById('repoTag').textContent = inPackCount + ' mods in pack / ' + data.length + ' total';
    renderAllMods(allMods);
  } catch(e) {
    document.getElementById('allModsList').innerHTML = '<div class="empty">Error: ' + escHtml(e.message) + '</div>';
    toast('Failed to load all mods: ' + e.message, 'error');
  }
}

function filterAllMods() {
  var q = document.getElementById('allModsFilter').value.trim().toLowerCase();
  var activeChip = document.querySelector('#filterChips .chip.active');
  var chipFilter = activeChip ? activeChip.dataset.filter : 'all';
  var filtered = allMods.filter(function(m) {
    if (q && !m.name.toLowerCase().includes(q) && !(m.slug||'').toLowerCase().includes(q)) return false;
    if (chipFilter === 'all') return true;
    if (chipFilter === 'client') return m.side === 'client' && m.in_pack !== false;
    if (chipFilter === 'server') return m.side === 'server' && m.in_pack !== false;
    if (chipFilter === 'both') return m.side === 'both' && m.in_pack !== false;
    if (chipFilter === 'notinpack') return m.in_pack === false;
    if (chipFilter === 'disabled') return !!(m.disabled || m.server_disabled);
    return true;
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
    var isDisabled = !!m.disabled || !!m.server_disabled;
    var inPack = m.in_pack !== false;
    var slug = m.slug;
    var hasMod = !!m.mod_id;
    var ver = m.version ? escHtml(m.version) : '';
    return '<div class="mod-item' + (isDisabled ? ' disabled-mod' : '') + '" id="allmod-' + escHtml(slug) + '" data-name="' + escHtml(m.name.toLowerCase()) + '">' +
      '<div class="mod-item-row">' +
        (m.icon ? '<img class="mod-icon" src="' + escHtml(m.icon) + '" onerror="this.remove()" loading="lazy"/>' : '<div class="mod-icon-placeholder">&#x1F9E9;</div>') +
        '<div class="mod-info">' +
          '<div class="mod-name">' + escHtml(m.name) + (ver ? ' <span class="mod-version">' + ver + '</span>' : '') + '</div>' +
          '<div class="mod-meta">' +
            '<span class="side-badge ' + sideBadgeClass(sid) + '">' + escHtml(sid) + '</span>' +
            (isDisabled ? '<span class="disabled-badge">disabled</span>' : '') +
            (!inPack ? '<span class="notinpack-badge">not in pack</span>' : '') +
            (isOpt ? '<span class="optional-badge">optional</span>' : '') +
            (isOpt && isDef ? '<span class="default-badge">default on</span>' : '') +
            (hasMod ? ' <a href="https://modrinth.com/mod/' + escHtml(m.mod_id) + '" target="_blank" rel="noopener" style="font-size:0.78rem">Modrinth</a>' : '') +
          '</div>' +
        '</div>' +
        '<div class="mod-actions">' +
          '<label class="toggle" title="' + (isDisabled ? 'Enable mod' : 'Disable mod') + '">' +
            '<input type="checkbox" class="dis-toggle" data-slug="' + escHtml(slug) + '" data-name="' + escHtml(m.name) + '" ' + (!isDisabled ? 'checked' : '') + '/>' +
            '<span class="toggle-slider"></span>' +
          '</label>' +
          (hasMod ? '<button class="ghost sm update-mod-btn" data-slug="' + escHtml(slug) + '" data-name="' + escHtml(m.name) + '">Update</button>' : '') +
          '<button class="ghost sm edit-btn" data-slug="' + escHtml(slug) + '">Edit</button>' +
          (inPack ? '<button class="ghost sm danger rm-all-btn" data-slug="' + escHtml(slug) + '" data-name="' + escHtml(m.name) + '">Remove</button>' : '') +
        '</div>' +
      '</div>' +
      '<div class="edit-panel" id="edit-' + escHtml(slug) + '">' +
        '<div class="edit-section-title">Settings</div>' +
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
        '<div class="edit-section-title" style="margin-top:0.5rem">Upload JAR Override</div>' +
        '<div class="edit-panel-row upload-row">' +
          '<input type="file" accept=".jar" class="jar-input" id="jar-' + escHtml(slug) + '"/>' +
          '<button class="sm warning-btn upload-jar-btn" data-slug="' + escHtml(slug) + '" data-name="' + escHtml(m.name) + '">Upload JAR</button>' +
        '</div>' +
        (inPack ?
          '<div class="edit-section-title toml-toggle" data-slug="' + escHtml(slug) + '" style="margin-top:0.5rem">&#9658; Edit Raw .pw.toml</div>' +
          '<div class="toml-section" id="toml-sec-' + escHtml(slug) + '">' +
            '<textarea class="toml-editor" id="toml-txt-' + escHtml(slug) + '" spellcheck="false">Loading...</textarea>' +
            '<div class="edit-actions" style="margin-top:0.5rem">' +
              '<button class="sm success-btn toml-save-btn" data-slug="' + escHtml(slug) + '">Save TOML</button>' +
              '<button class="sm ghost toml-cancel-btn" data-slug="' + escHtml(slug) + '">Cancel</button>' +
            '</div>' +
          '</div>'
        : '') +
      '</div>' +
    '</div>';
  }).join('');

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
  el.querySelectorAll('.upload-jar-btn').forEach(function(b) {
    b.addEventListener('click', function() { uploadJar(b.dataset.slug, b.dataset.name, b); });
  });
  el.querySelectorAll('.update-mod-btn').forEach(function(b) {
    b.addEventListener('click', function() { updateSingleMod(b.dataset.slug, b.dataset.name, b); });
  });
  el.querySelectorAll('.rm-all-btn').forEach(function(b) {
    b.addEventListener('click', function() { removeModConfirm(b.dataset.slug, b.dataset.name, b); });
  });
  el.querySelectorAll('.toml-toggle').forEach(function(h) {
    h.addEventListener('click', function() { toggleTomlSection(h.dataset.slug, h); });
  });
  el.querySelectorAll('.toml-save-btn').forEach(function(b) {
    b.addEventListener('click', function() { saveModToml(b.dataset.slug, b); });
  });
  el.querySelectorAll('.toml-cancel-btn').forEach(function(b) {
    b.addEventListener('click', function() {
      var sec = document.getElementById('toml-sec-' + b.dataset.slug);
      if (sec) sec.classList.remove('open');
    });
  });
  el.querySelectorAll('.dis-toggle').forEach(function(chk) {
    chk.addEventListener('change', function() { toggleDisableMod(chk.dataset.slug, chk.dataset.name, chk); });
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

async function toggleDisableMod(slug, name, chk) {
  chk.disabled = true;
  try {
    var res = await fetch('/api/mods/' + encodeURIComponent(slug) + '/toggle-disable', { method: 'POST' });
    var data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Toggle failed');
    var nowDisabled = data.disabled;
    toast((nowDisabled ? 'Disabled: ' : 'Enabled: ') + name);
    var modItem = document.getElementById('allmod-' + slug);
    if (modItem) {
      modItem.classList.toggle('disabled-mod', nowDisabled);
      // Update toggle title
      var lbl = chk.closest('label');
      if (lbl) lbl.title = nowDisabled ? 'Enable mod' : 'Disable mod';
      // Update disabled badge in meta
      var meta = modItem.querySelector('.mod-meta');
      if (meta) {
        var badge = meta.querySelector('.disabled-badge');
        if (nowDisabled && !badge) {
          var nb = document.createElement('span');
          nb.className = 'disabled-badge';
          nb.textContent = 'disabled';
          meta.insertBefore(nb, meta.children[1] || null);
        } else if (!nowDisabled && badge) {
          badge.remove();
        }
      }
      var entry = allMods.find(function(m) { return m.slug === slug; });
      if (entry) { entry.disabled = nowDisabled; entry.server_disabled = nowDisabled; }
    }
  } catch(e) {
    toast('Error: ' + e.message, 'error');
    chk.checked = !chk.checked;
  } finally {
    chk.disabled = false;
  }
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
    b.classList.toggle('active', b.dataset.side === side);
  });
}

function getSelectedSide(slug) {
  var grp = document.getElementById('seg-' + slug);
  if (!grp) return 'both';
  var active = grp.querySelector('.seg-btn.active');
  return active ? active.dataset.side : 'both';
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
    var entry = allMods.find(function(m) { return m.slug === slug; });
    if (entry) {
      entry.side = side;
      entry.optional = optional;
      entry.default = defaultOn;
    }
    var panel = document.getElementById('edit-' + slug);
    if (panel) panel.classList.remove('open');
    var modItem = document.getElementById('allmod-' + slug);
    if (modItem) {
      var metaEl = modItem.querySelector('.mod-meta');
      if (metaEl) {
        var modrinthLink = metaEl.querySelector('a') ? metaEl.querySelector('a').outerHTML : '';
        var isDisabled = !!(entry && entry.disabled);
        metaEl.innerHTML =
          '<span class="side-badge ' + sideBadgeClass(side) + '">' + escHtml(side) + '</span>' +
          (isDisabled ? '<span class="disabled-badge">disabled</span>' : '') +
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

async function uploadJar(slug, name, btn) {
  var fileInput = document.getElementById('jar-' + slug);
  if (!fileInput || !fileInput.files.length) {
    toast('Select a .jar file first', 'error');
    return;
  }
  var file = fileInput.files[0];
  if (btn) { btn.disabled = true; btn.textContent = 'Uploading...'; }
  try {
    var formData = new FormData();
    formData.append('file', file);
    var res = await fetch('/api/mods/' + encodeURIComponent(slug) + '/upload', {
      method: 'POST',
      body: formData
    });
    var data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Upload failed');
    toast('Uploaded JAR for: ' + name);
    fileInput.value = '';
  } catch(e) {
    toast('Upload error: ' + e.message, 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = 'Upload JAR'; }
  }
}

async function updateSingleMod(slug, name, btn) {
  if (btn) { btn.disabled = true; btn.textContent = 'Updating...'; }
  try {
    var res = await fetch('/api/mods/' + encodeURIComponent(slug) + '/update', { method: 'POST' });
    var data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Update failed');
    if (data.updated) {
      toast('Updated ' + name + ' to ' + data.new_version_id);
    } else {
      toast(name + ' is already up to date');
    }
  } catch(e) {
    toast('Update error: ' + e.message, 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = 'Update'; }
  }
}

/* ===== PACK TAB ===== */
var packInfoLoaded = false;

document.getElementById('packInfoRefreshBtn').addEventListener('click', function() { packInfoLoaded = false; loadPackInfo(); });
document.querySelectorAll('.pw-preset').forEach(function(b) {
  b.addEventListener('click', function() { runPackwiz(b.dataset.cmd.split(' ')); });
});
document.getElementById('pwRunBtn').addEventListener('click', function() {
  var cmd = document.getElementById('pwCmdInput').value.trim();
  if (!cmd) return;
  runPackwiz(cmd.split(/\s+/));
});
document.getElementById('pwCmdInput').addEventListener('keydown', function(e) {
  if (e.key === 'Enter') {
    var cmd = document.getElementById('pwCmdInput').value.trim();
    if (cmd) runPackwiz(cmd.split(/\s+/));
  }
});

async function loadPackInfo() {
  if (packInfoLoaded) return;
  var body = document.getElementById('packInfoBody');
  body.innerHTML = '<div class="loading"><div class="spinner"></div> Loading...</div>';
  try {
    var res = await fetch('/api/pack/info');
    var d = await res.json();
    if (!res.ok) throw new Error(d.detail || 'Failed');
    packInfoLoaded = true;
    body.innerHTML =
      '<div class="pack-info-grid">' +
        '<div class="pack-info-item"><div class="pack-info-label">Repo</div><div class="pack-info-value">' + escHtml(d.repo) + '</div></div>' +
        '<div class="pack-info-item"><div class="pack-info-label">Branch</div><div class="pack-info-value">' + escHtml(d.branch) + '</div></div>' +
        '<div class="pack-info-item"><div class="pack-info-label">.pw.toml</div><div class="pack-info-value">' + d.pw_count + '</div></div>' +
        '<div class="pack-info-item"><div class="pack-info-label">Raw jars</div><div class="pack-info-value">' + d.jar_count + '</div></div>' +
        '<div class="pack-info-item" style="grid-column:span 2"><div class="pack-info-label">Last commit (' + escHtml(d.last_commit_sha) + ') by ' + escHtml(d.last_commit_author) + '</div><div class="pack-info-value" style="font-size:0.82rem;font-weight:400">' + escHtml(d.last_commit_msg) + '</div></div>' +
      '</div>';
  } catch(e) {
    body.innerHTML = '<div class="empty">Error: ' + escHtml(e.message) + '</div>';
  }
}

async function runPackwiz(args) {
  var btn = document.getElementById('pwRunBtn');
  var out = document.getElementById('pwOutput');
  btn.disabled = true;
  btn.textContent = 'Running...';
  out.textContent = '$ packwiz ' + args.join(' ') + '\\n';
  out.classList.add('visible');
  try {
    var res = await fetch('/api/packwiz/exec', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ args: args })
    });
    var d = await res.json();
    if (!res.ok) throw new Error(d.detail || 'Failed');
    out.textContent += d.output || '(no output)';
    if (d.committed) { out.textContent += '\\nCommitted and pushed.'; packInfoLoaded = false; }
    if (!d.ok) out.textContent += '\\n[non-zero exit]';
    out.scrollTop = out.scrollHeight;
    if (d.ok) toast('packwiz ' + args[0] + ' done');
    else toast('packwiz exited with error', 'error');
  } catch(e) {
    out.textContent += 'Error: ' + e.message;
    toast('Error: ' + e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Run';
  }
}

/* ===== TOML EDITOR ===== */
var tomlCache = {};

async function toggleTomlSection(slug, header) {
  var sec = document.getElementById('toml-sec-' + slug);
  if (!sec) return;
  var isOpen = sec.classList.contains('open');
  if (isOpen) {
    sec.classList.remove('open');
    header.innerHTML = '&#9658; Edit Raw .pw.toml';
    return;
  }
  sec.classList.add('open');
  header.innerHTML = '&#9660; Edit Raw .pw.toml';
  var ta = document.getElementById('toml-txt-' + slug);
  if (tomlCache[slug]) { ta.value = tomlCache[slug].content; return; }
  ta.value = 'Loading...';
  try {
    var res = await fetch('/api/mods/' + encodeURIComponent(slug) + '/toml');
    var d = await res.json();
    if (!res.ok) throw new Error(d.detail || 'Failed');
    tomlCache[slug] = d;
    ta.value = d.content;
  } catch(e) {
    ta.value = 'Error: ' + e.message;
  }
}

async function saveModToml(slug, btn) {
  var ta = document.getElementById('toml-txt-' + slug);
  if (!ta) return;
  var cached = tomlCache[slug];
  if (!cached) { toast('Load the TOML first', 'error'); return; }
  btn.disabled = true;
  btn.textContent = 'Saving...';
  try {
    var res = await fetch('/api/mods/' + encodeURIComponent(slug) + '/toml', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: ta.value, sha: cached.sha, path: cached.path })
    });
    var d = await res.json();
    if (!res.ok) throw new Error(d.detail || 'Failed');
    tomlCache[slug] = null;
    toast('Saved TOML for ' + slug);
  } catch(e) {
    toast('Save error: ' + e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Save TOML';
  }
}

/* ===== UPDATES TAB ===== */
async function checkUpdates() {
  var btn = document.getElementById('checkUpdatesBtn');
  btn.disabled = true;
  btn.textContent = 'Checking...';
  document.getElementById('updatesList').innerHTML = '<div class="loading"><div class="spinner"></div> Checking for updates...</div>';
  document.getElementById('updateAllBtn').style.display = 'none';
  document.getElementById('updatesCount').textContent = '';
  try {
    var res = await fetch('/api/mods/updates');
    var data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Check failed');
    updatesData = data;
    renderUpdates(data);
  } catch(e) {
    document.getElementById('updatesList').innerHTML = '<div class="empty">Error: ' + escHtml(e.message) + '</div>';
    toast('Update check failed: ' + e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Check for Updates';
  }
}

function renderUpdates(mods) {
  var el = document.getElementById('updatesList');
  var withUpdates = mods.filter(function(m) { return m.has_update; });
  document.getElementById('updatesCount').textContent = withUpdates.length + ' update' + (withUpdates.length !== 1 ? 's' : '') + ' available';
  if (withUpdates.length > 0) {
    document.getElementById('updateAllBtn').style.display = '';
  }
  if (!withUpdates.length) {
    el.innerHTML = '<div class="empty">All mods are up to date!</div>';
    return;
  }
  el.innerHTML = withUpdates.map(function(m) {
    return '<div class="mod-item" id="upd-' + escHtml(m.slug) + '">' +
      '<div class="mod-item-row">' +
        (m.icon ? '<img class="mod-icon" src="' + escHtml(m.icon) + '" onerror="this.remove()" loading="lazy"/>' : '<div class="mod-icon-placeholder">&#x1F9E9;</div>') +
        '<div class="mod-info">' +
          '<div class="mod-name">' + escHtml(m.name) + '</div>' +
          '<div class="mod-meta">' +
            '<span class="update-version-old">' + escHtml(m.current_version || 'unknown') + '</span>' +
            '<span class="update-arrow"> &#8594; </span>' +
            '<span class="update-version-new">' + escHtml(m.latest_version_id) + '</span>' +
          '</div>' +
        '</div>' +
        '<div class="mod-actions">' +
          '<span class="update-badge">Update available</span>' +
          '<button class="sm success-btn upd-btn" data-slug="' + escHtml(m.slug) + '" data-name="' + escHtml(m.name) + '" data-vid="' + escHtml(m.latest_version_id) + '">Update</button>' +
        '</div>' +
      '</div>' +
    '</div>';
  }).join('');
  el.querySelectorAll('.upd-btn').forEach(function(b) {
    b.addEventListener('click', function() { doUpdateMod(b.dataset.slug, b.dataset.name, b.dataset.vid, b); });
  });
}

async function doUpdateMod(slug, name, versionId, btn) {
  if (btn) { btn.disabled = true; btn.textContent = 'Updating...'; }
  try {
    var body = {};
    if (versionId) body.version_id = versionId;
    var res = await fetch('/api/mods/' + encodeURIComponent(slug) + '/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    var data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Update failed');
    toast('Updated: ' + name);
    var item = document.getElementById('upd-' + slug);
    if (item) item.remove();
    updatesData = updatesData.filter(function(m) { return m.slug !== slug; });
    var remaining = updatesData.filter(function(m) { return m.has_update; });
    document.getElementById('updatesCount').textContent = remaining.length + ' update' + (remaining.length !== 1 ? 's' : '') + ' available';
    if (!remaining.length) {
      document.getElementById('updatesList').innerHTML = '<div class="empty">All mods are up to date!</div>';
      document.getElementById('updateAllBtn').style.display = 'none';
    }
  } catch(e) {
    toast('Error: ' + e.message, 'error');
    if (btn) { btn.disabled = false; btn.textContent = 'Update'; }
  }
}

async function updateAll() {
  var btn = document.getElementById('updateAllBtn');
  btn.disabled = true;
  btn.textContent = 'Updating all...';
  var toUpdate = updatesData.filter(function(m) { return m.has_update; });
  var success = 0;
  var fail = 0;
  for (var i = 0; i < toUpdate.length; i++) {
    var m = toUpdate[i];
    try {
      var body = {};
      if (m.latest_version_id) body.version_id = m.latest_version_id;
      var res = await fetch('/api/mods/' + encodeURIComponent(m.slug) + '/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      var data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'failed');
      success++;
      var item = document.getElementById('upd-' + m.slug);
      if (item) item.remove();
    } catch(e) {
      fail++;
    }
  }
  updatesData = updatesData.filter(function(m) { return !m.has_update; });
  if (success) toast('Updated ' + success + ' mod' + (success !== 1 ? 's' : ''));
  if (fail) toast(fail + ' update(s) failed', 'error');
  document.getElementById('updatesCount').textContent = '0 updates available';
  document.getElementById('updatesList').innerHTML = '<div class="empty">All mods are up to date!</div>';
  btn.disabled = false;
  btn.textContent = 'Update All';
  btn.style.display = 'none';
}

/* ===== SERVER TAB ===== */
function startServerTab() {
  fetchServerStatus();
  if (!serverStatusInterval) {
    serverStatusInterval = setInterval(fetchServerStatus, 5000);
  }
  connectServerLogs();
}

function stopServerTab() {
  if (serverStatusInterval) {
    clearInterval(serverStatusInterval);
    serverStatusInterval = null;
  }
  if (logEventSource) {
    logEventSource.close();
    logEventSource = null;
    document.getElementById('srvLogStatus').textContent = 'Disconnected';
  }
}

async function fetchServerStatus() {
  try {
    var res = await fetch('/api/server/status');
    var data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Status error');
    updateServerStatus(data);
  } catch(e) {
    document.getElementById('srvDot').className = 'status-dot stopped';
    document.getElementById('srvStatusLabel').textContent = 'Error';
  }
}

function updateServerStatus(data) {
  var running = !!data.running;
  serverRunning = running;
  var dot = document.getElementById('srvDot');
  dot.className = 'status-dot ' + (running ? 'running' : 'stopped');
  document.getElementById('srvStatusLabel').textContent = running ? 'Running' : 'Stopped';
  document.getElementById('srvPlayers').textContent = data.players !== undefined ? String(data.players) : '-';
  document.getElementById('srvMspt').textContent = data.mspt !== undefined ? String(data.mspt) : '-';
  document.getElementById('srvCpu').textContent = data.cpu !== undefined ? data.cpu + '%' : '-';
  document.getElementById('srvRam').textContent = data.mem_mb !== undefined ? data.mem_mb + ' MB' : '-';
  document.getElementById('srvStartBtn').disabled = running;
  document.getElementById('srvStopBtn').disabled = !running;
  document.getElementById('srvRestartBtn').disabled = !running;
}

async function serverAction(action) {
  var btnId = action === 'start_server' ? 'srvStartBtn' : action === 'stop_server' ? 'srvStopBtn' : 'srvRestartBtn';
  var btn = document.getElementById(btnId);
  if (btn) btn.disabled = true;
  try {
    var res = await fetch('/api/server/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: action })
    });
    var data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Action failed');
    toast('Action sent: ' + action.replace('_server', ''));
    setTimeout(fetchServerStatus, 1500);
  } catch(e) {
    toast('Error: ' + e.message, 'error');
    if (btn) btn.disabled = false;
  }
}

async function sendServerCommand() {
  var inp = document.getElementById('srvCmdInput');
  var cmd = inp.value.trim();
  if (!cmd) return;
  inp.value = '';
  try {
    var res = await fetch('/api/server/command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command: cmd })
    });
    var data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Command failed');
    appendLog('> ' + cmd);
  } catch(e) {
    toast('Command error: ' + e.message, 'error');
  }
}

function appendLog(line) {
  var box = document.getElementById('srvLogBox');
  var atBottom = box.scrollHeight - box.clientHeight <= box.scrollTop + 10;
  box.textContent += line + '\\n';
  if (atBottom) box.scrollTop = box.scrollHeight;
}

function connectServerLogs() {
  if (logEventSource) {
    logEventSource.close();
    logEventSource = null;
  }
  var statusEl = document.getElementById('srvLogStatus');
  statusEl.textContent = 'Connecting...';
  try {
    logEventSource = new EventSource('/api/server/logs');
    logEventSource.onopen = function() {
      statusEl.textContent = 'Connected';
    };
    logEventSource.onmessage = function(e) {
      if (e.data && e.data !== 'ping') {
        appendLog(e.data);
      }
    };
    logEventSource.onerror = function() {
      statusEl.textContent = 'Reconnecting...';
    };
  } catch(e) {
    statusEl.textContent = 'Error';
  }
}

async function triggerSync() {
  var btn = document.getElementById('syncBtn');
  btn.disabled = true;
  btn.textContent = 'Syncing...';
  try {
    var res = await fetch('/api/sync', { method: 'POST' });
    var data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Sync failed');
    toast('Sync triggered — modpack-sync is running', 'success');
  } catch(e) {
    toast('Sync error: ' + e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Sync to GitHub';
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


def crafty_headers() -> dict:
    return {
        "Authorization": f"Bearer {CRAFTY_TOKEN}",
    }


def parse_toml_simple(content: str) -> dict:
    try:
        return tomllib.loads(content)
    except Exception:
        return {}


def build_pw_toml(name: str, filename: str, project_id: str, version_id: str, url: str, hash512: str, side: str = "client") -> str:
    return (
        f'name = "{name}"\n'
        f'filename = "{filename}"\n'
        f'side = "{side}"\n'
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


def build_pw_toml_override(name: str, filename: str, hash512: str, side: str = "both") -> str:
    """Build a .pw.toml for a local JAR override (no Modrinth update section)."""
    return (
        f'name = "{name}"\n'
        f'filename = "{filename}"\n'
        f'side = "{side}"\n'
        f'\n'
        f'[download]\n'
        f'hash-format = "sha512"\n'
        f'hash = "{hash512}"\n'
    )


def patch_toml_content(raw: str, side: str, optional: bool, default_on: bool) -> str:
    """Patch a .pw.toml string with new side/optional/default values."""

    # 1. Replace side field
    raw = re.sub(r'^side\s*=\s*"[^"]*"', f'side = "{side}"', raw, flags=re.MULTILINE)

    # 2. Handle [option] section
    option_block = f'[option]\noptional = true\ndefault = {"true" if default_on else "false"}\n'

    option_section_precise = re.compile(
        r'^\[option\].*?(?=^\[|\Z)',
        re.MULTILINE | re.DOTALL
    )

    if optional:
        if option_section_precise.search(raw):
            raw = option_section_precise.sub(option_block, raw, count=1)
        else:
            if not raw.endswith('\n'):
                raw += '\n'
            raw += '\n' + option_block
    else:
        if option_section_precise.search(raw):
            raw = option_section_precise.sub('', raw, count=1)
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


async def github_put_file_bytes(client: httpx.AsyncClient, path: str, content_bytes: bytes, message: str, sha: Optional[str] = None):
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{path}"
    encoded = base64.b64encode(content_bytes).decode()
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
    """Fetch a .pw.toml or .pw.toml.disabled entry from GitHub and return parsed mod info."""
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

        fname = entry["name"]
        disabled = fname.endswith(".pw.toml.disabled")
        slug = fname.replace(".pw.toml.disabled", "").replace(".pw.toml", "")

        if client_only and side != "client":
            return None
        mod_id = data.get("update", {}).get("modrinth", {}).get("mod-id", "")
        version_id = data.get("update", {}).get("modrinth", {}).get("version", "")
        option = data.get("option", {})
        jar_filename = data.get("filename", "")
        return {
            "slug": slug,
            "name": data.get("name", slug),
            "filename": jar_filename,
            "version": version_id,
            "mod_id": mod_id,
            "sha": entry.get("sha", ""),
            "side": side,
            "optional": option.get("optional", False),
            "default": option.get("default", False),
            "disabled": disabled,
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
    """Return all .pw.toml and .pw.toml.disabled entries from the mods directory."""
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/mods"
    r = await client.get(url, headers=gh_headers())
    if r.status_code == 404:
        return []
    if r.status_code == 401:
        raise HTTPException(401, "GitHub authentication failed — check GITHUB_PAT")
    r.raise_for_status()
    entries = r.json()
    return [
        e for e in entries
        if isinstance(e, dict) and (
            e.get("name", "").endswith(".pw.toml") or
            e.get("name", "").endswith(".pw.toml.disabled")
        )
    ]


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


def extract_version_from_filename(filename: str) -> str:
    """Extract version string from a jar filename like mod-name-1.2.3.jar"""
    name = re.sub(r'\.(jar|disabled)$', '', filename, flags=re.IGNORECASE)
    name = re.sub(r'\.(jar\.disabled)$', '', name, flags=re.IGNORECASE)
    # Match version-like patterns: digits with dots, optionally prefixed with - or _
    m = re.search(r'[-_]([vV]?\d+[\d.\-+_a-zA-Z]*)$', name)
    if m:
        return m.group(1)
    # Try matching anywhere in the name
    m = re.search(r'[-_]([vV]?\d+[.\d]+)', name)
    if m:
        return m.group(1)
    return ""


def get_server_mods() -> list:
    """List all jar files in /server-mods with version and disabled state."""
    server_mods_dir = "/server-mods"
    if not os.path.isdir(server_mods_dir):
        return []
    result = []
    for fname in sorted(os.listdir(server_mods_dir)):
        if fname.endswith(".jar"):
            result.append({"filename": fname, "disabled": False, "version": extract_version_from_filename(fname)})
        elif fname.endswith(".jar.disabled"):
            result.append({"filename": fname, "disabled": True, "version": extract_version_from_filename(fname)})
    return result


@app.get("/api/all-mods")
async def list_all_mods():
    if not GITHUB_PAT or not GITHUB_REPO:
        raise HTTPException(500, "GITHUB_PAT and GITHUB_REPO environment variables are required")

    # Get server jars (source of truth for what's actually installed)
    server_jars = get_server_mods()
    # Map filename → server info
    server_map: dict = {}
    for s in server_jars:
        base = s["filename"].replace(".disabled", "")
        server_map[base] = s

    async with httpx.AsyncClient(timeout=60) as client:
        pw_files = await list_all_pw_files(client)
        tasks = [fetch_and_parse_entry(client, e, client_only=False) for e in pw_files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        pack_mods = [r for r in results if isinstance(r, dict)]

        # Build map: filename → pack mod
        pack_by_filename: dict = {}
        for m in pack_mods:
            if m.get("filename"):
                pack_by_filename[m["filename"]] = m
            # Also index by slug for overrides
            pack_by_filename[m["slug"]] = m

        # Enrich pack mods with server info
        enriched = []
        seen_filenames = set()

        for pm in pack_mods:
            fname = pm.get("filename", "")
            sinfo = server_map.get(fname, {})
            pm["in_pack"] = True
            pm["in_server"] = bool(sinfo) or pm.get("side") == "client"
            pm["server_disabled"] = sinfo.get("disabled", pm.get("disabled", False))
            # Use server version if no modrinth version_id, else keep version_id
            if not pm.get("version") and sinfo.get("version"):
                pm["version"] = sinfo["version"]
            if fname:
                seen_filenames.add(fname)
            enriched.append(pm)

        # Add server jars NOT in pack
        for sinfo in server_jars:
            base = sinfo["filename"].replace(".disabled", "")
            if base not in seen_filenames:
                enriched.append({
                    "slug": re.sub(r'[^a-z0-9-]', '-', base.replace(".jar", "").lower())[:40],
                    "name": base.replace(".jar", ""),
                    "filename": base,
                    "version": sinfo["version"],
                    "mod_id": "",
                    "sha": "",
                    "side": "both",
                    "optional": False,
                    "default": False,
                    "disabled": sinfo["disabled"],
                    "server_disabled": sinfo["disabled"],
                    "in_pack": False,
                    "in_server": True,
                    "icon": None,
                })

        # Mark all pack mods as in_pack
        for m in enriched:
            if "in_pack" not in m:
                m["in_pack"] = True

        # Enrich icons in parallel (only for Modrinth mods)
        enriched = list(await asyncio.gather(*[enrich_icon(client, m) for m in enriched], return_exceptions=False))
        enriched = [m for m in enriched if isinstance(m, dict)]
        enriched = sorted(enriched, key=lambda m: m["name"].lower())

    return enriched


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


@app.get("/api/mods/updates")
async def check_mod_updates():
    if not GITHUB_PAT or not GITHUB_REPO:
        raise HTTPException(500, "GITHUB_PAT and GITHUB_REPO environment variables are required")

    async with httpx.AsyncClient(timeout=60) as client:
        pw_files = await list_all_pw_files(client)

        tasks = [fetch_and_parse_entry(client, e, client_only=False) for e in pw_files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        mods = [r for r in results if isinstance(r, dict) and r.get("mod_id")]

        async def check_one(mod: dict) -> dict:
            slug = mod["slug"]
            name = mod["name"]
            mod_id = mod["mod_id"]
            current_version = mod.get("version", "")
            icon = mod.get("icon")
            try:
                versions = await get_modrinth_versions(client, mod_id)
                if not versions:
                    return {
                        "slug": slug, "name": name, "icon": icon,
                        "current_version": current_version,
                        "latest_version": None, "latest_version_id": None,
                        "has_update": False,
                    }
                latest = versions[0]
                latest_id = latest.get("id", "")
                latest_name = latest.get("name", latest_id)
                has_update = bool(latest_id and latest_id != current_version)
                return {
                    "slug": slug, "name": name, "icon": icon,
                    "current_version": current_version,
                    "latest_version": latest_name,
                    "latest_version_id": latest_id,
                    "has_update": has_update,
                }
            except Exception:
                return {
                    "slug": slug, "name": name, "icon": icon,
                    "current_version": current_version,
                    "latest_version": None, "latest_version_id": None,
                    "has_update": False,
                }

        # Enrich icons first
        mods = list(await asyncio.gather(*[enrich_icon(client, m) for m in mods], return_exceptions=False))
        mods = [m for m in mods if isinstance(m, dict)]

        update_results = await asyncio.gather(*[check_one(m) for m in mods], return_exceptions=True)
        update_results = [r for r in update_results if isinstance(r, dict)]
        update_results = sorted(update_results, key=lambda m: m["name"].lower())

    return update_results


class AddModRequest(BaseModel):
    project_id: str
    version_id: Optional[str] = None
    side: Optional[str] = "client"


class PatchModRequest(BaseModel):
    side: str
    optional: bool
    default: bool


class UpdateModRequest(BaseModel):
    version_id: Optional[str] = None


class ServerActionRequest(BaseModel):
    action: str


class ServerCommandRequest(BaseModel):
    command: str


@app.post("/api/mods")
async def add_mod(req: AddModRequest):
    if not GITHUB_PAT or not GITHUB_REPO:
        raise HTTPException(500, "GITHUB_PAT and GITHUB_REPO environment variables are required")

    side = req.side or "client"
    valid_sides = {"client", "server", "both"}
    if side not in valid_sides:
        side = "client"

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

        toml_content = build_pw_toml(name, filename, req.project_id, version_id, file_url, sha512, side=side)

        path = f"mods/{slug}.pw.toml"
        existing = await github_get_file(client, path)
        sha = existing["sha"] if existing else None

        commit_msg = f"Add {side} mod: {name}"
        try:
            await github_put_file(client, path, toml_content, commit_msg, sha)
        except httpx.HTTPStatusError as e:
            raise HTTPException(500, f"GitHub commit failed: {e.response.text[:200]}")

    return {"ok": True, "slug": slug, "name": name, "version_id": version_id}


@app.post("/api/mods/{slug}/toggle-disable")
async def toggle_disable_mod(slug: str):
    if not GITHUB_PAT or not GITHUB_REPO:
        raise HTTPException(500, "GITHUB_PAT and GITHUB_REPO environment variables are required")

    async with httpx.AsyncClient(timeout=30) as client:
        enabled_path = f"mods/{slug}.pw.toml"
        disabled_path = f"mods/{slug}.pw.toml.disabled"

        enabled_file = await github_get_file(client, enabled_path)
        disabled_file = await github_get_file(client, disabled_path)

        if enabled_file:
            # Currently enabled → disable it
            sha = enabled_file["sha"]
            raw_b64 = enabled_file.get("content", "")
            try:
                content = base64.b64decode(raw_b64.replace("\n", "")).decode("utf-8", errors="replace")
            except Exception:
                raise HTTPException(500, "Failed to decode file content")

            data = parse_toml_simple(content)
            name = data.get("name", slug)

            # Delete old .pw.toml, create .pw.toml.disabled
            try:
                await github_delete_file(client, enabled_path, f"Disable mod: {name}", sha)
            except httpx.HTTPStatusError as e:
                raise HTTPException(500, f"GitHub delete failed: {e.response.text[:200]}")

            dis_sha = disabled_file["sha"] if disabled_file else None
            try:
                await github_put_file(client, disabled_path, content, f"Disable mod: {name}", dis_sha)
            except httpx.HTTPStatusError as e:
                raise HTTPException(500, f"GitHub create disabled failed: {e.response.text[:200]}")

            # Rename jar on server filesystem
            jar_filename = data.get("filename", f"{slug}.jar")
            jar_path = os.path.join(SERVER_MODS_DIR, jar_filename)
            jar_disabled_path = jar_path + ".disabled"
            try:
                if os.path.exists(jar_path):
                    os.rename(jar_path, jar_disabled_path)
            except Exception:
                pass  # Don't fail if jar not found

            return {"ok": True, "slug": slug, "name": name, "disabled": True}

        elif disabled_file:
            # Currently disabled → enable it
            sha = disabled_file["sha"]
            raw_b64 = disabled_file.get("content", "")
            try:
                content = base64.b64decode(raw_b64.replace("\n", "")).decode("utf-8", errors="replace")
            except Exception:
                raise HTTPException(500, "Failed to decode file content")

            data = parse_toml_simple(content)
            name = data.get("name", slug)

            # Delete .pw.toml.disabled, create .pw.toml
            try:
                await github_delete_file(client, disabled_path, f"Enable mod: {name}", sha)
            except httpx.HTTPStatusError as e:
                raise HTTPException(500, f"GitHub delete failed: {e.response.text[:200]}")

            en_sha = enabled_file["sha"] if enabled_file else None
            try:
                await github_put_file(client, enabled_path, content, f"Enable mod: {name}", en_sha)
            except httpx.HTTPStatusError as e:
                raise HTTPException(500, f"GitHub create enabled failed: {e.response.text[:200]}")

            # Rename jar on server filesystem
            jar_filename = data.get("filename", f"{slug}.jar")
            jar_disabled_path = os.path.join(SERVER_MODS_DIR, jar_filename + ".disabled")
            jar_path = os.path.join(SERVER_MODS_DIR, jar_filename)
            try:
                if os.path.exists(jar_disabled_path):
                    os.rename(jar_disabled_path, jar_path)
            except Exception:
                pass  # Don't fail if jar not found

            return {"ok": True, "slug": slug, "name": name, "disabled": False}

        else:
            raise HTTPException(404, f"Mod file not found: {slug}")


@app.post("/api/mods/{slug}/update")
async def update_mod(slug: str, req: UpdateModRequest = UpdateModRequest()):
    if not GITHUB_PAT or not GITHUB_REPO:
        raise HTTPException(500, "GITHUB_PAT and GITHUB_REPO environment variables are required")

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

        data = parse_toml_simple(raw_content)
        name = data.get("name", slug)
        mod_id = data.get("update", {}).get("modrinth", {}).get("mod-id", "")
        current_version_id = data.get("update", {}).get("modrinth", {}).get("version", "")
        side = data.get("side", "client")

        if not mod_id:
            raise HTTPException(400, f"Mod '{slug}' has no Modrinth mod-id — cannot auto-update")

        if req.version_id:
            try:
                vr = await client.get(f"{MODRINTH_API}/version/{req.version_id}")
                vr.raise_for_status()
                version = vr.json()
            except httpx.HTTPStatusError:
                raise HTTPException(400, f"Version not found: {req.version_id}")
        else:
            try:
                versions = await get_modrinth_versions(client, mod_id)
            except httpx.HTTPStatusError as e:
                raise HTTPException(400, f"Failed to fetch versions: {e.response.status_code}")
            if not versions:
                raise HTTPException(400, f"No compatible versions found for '{name}'")
            version = versions[0]

        new_version_id = version.get("id", "")
        if new_version_id == current_version_id and not req.version_id:
            return {"ok": True, "slug": slug, "name": name, "updated": False, "new_version_id": new_version_id}

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

        toml_content = build_pw_toml(name, filename, mod_id, new_version_id, file_url, sha512, side=side)

        # Re-apply option section if present
        option = data.get("option", {})
        if option.get("optional"):
            toml_content = patch_toml_content(toml_content, side, True, bool(option.get("default", False)))

        commit_msg = f"Update mod: {name} -> {new_version_id}"
        try:
            await github_put_file(client, path, toml_content, commit_msg, sha)
        except httpx.HTTPStatusError as e:
            raise HTTPException(500, f"GitHub commit failed: {e.response.text[:200]}")

    return {"ok": True, "slug": slug, "name": name, "updated": True, "new_version_id": new_version_id}


@app.post("/api/mods/{slug}/upload")
async def upload_mod_jar(slug: str, file: UploadFile = File(...)):
    if not GITHUB_PAT or not GITHUB_REPO:
        raise HTTPException(500, "GITHUB_PAT and GITHUB_REPO environment variables are required")

    content = await file.read()
    if not content:
        raise HTTPException(400, "Uploaded file is empty")

    sha512 = hashlib.sha512(content).hexdigest()
    filename = file.filename or f"{slug}.jar"

    if not filename.endswith(".jar"):
        raise HTTPException(400, "Uploaded file must be a .jar")

    async with httpx.AsyncClient(timeout=60) as client:
        # Upload the jar to mods/<filename> on GitHub
        jar_path = f"mods/{filename}"
        existing_jar = await github_get_file(client, jar_path)
        jar_sha = existing_jar["sha"] if existing_jar else None

        commit_msg = f"Upload JAR override: {filename}"
        try:
            await github_put_file_bytes(client, jar_path, content, commit_msg, jar_sha)
        except httpx.HTTPStatusError as e:
            raise HTTPException(500, f"GitHub jar upload failed: {e.response.text[:200]}")

        # Create/update .pw.toml for this slug
        toml_path = f"mods/{slug}.pw.toml"
        existing_toml = await github_get_file(client, toml_path)
        toml_sha = existing_toml["sha"] if existing_toml else None

        # Get name from existing toml if available, else use slug
        name = slug
        if existing_toml:
            try:
                raw_b64 = existing_toml.get("content", "")
                raw_content = base64.b64decode(raw_b64.replace("\n", "")).decode("utf-8", errors="replace")
                parsed = parse_toml_simple(raw_content)
                name = parsed.get("name", slug)
            except Exception:
                pass

        toml_content = build_pw_toml_override(name, filename, sha512, side="both")
        toml_commit_msg = f"Update mod toml for JAR override: {name}"
        try:
            await github_put_file(client, toml_path, toml_content, toml_commit_msg, toml_sha)
        except httpx.HTTPStatusError as e:
            raise HTTPException(500, f"GitHub toml update failed: {e.response.text[:200]}")

    return {"ok": True, "slug": slug, "name": name, "filename": filename, "sha512": sha512}


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

        data = parse_toml_simple(raw_content)
        name = data.get("name", slug)

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

        commit_msg = f"Remove mod: {name}"
        try:
            await github_delete_file(client, path, commit_msg, sha)
        except httpx.HTTPStatusError as e:
            raise HTTPException(500, f"GitHub delete failed: {e.response.text[:200]}")

    return {"ok": True, "slug": slug, "name": name}


# ===== SERVER (CRAFTY) ENDPOINTS =====

@app.get("/api/server/status")
async def server_status():
    if not CRAFTY_URL or not CRAFTY_TOKEN or not CRAFTY_SERVER_ID:
        raise HTTPException(500, "CRAFTY_URL, CRAFTY_TOKEN, and CRAFTY_SERVER_ID are required")

    url = f"{CRAFTY_URL}/api/v2/servers/{CRAFTY_SERVER_ID}/stats"
    async with httpx.AsyncClient(timeout=10, verify=False) as client:
        try:
            r = await client.get(url, headers=crafty_headers())
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(502, f"Crafty API error: {e.response.status_code}")
        except Exception as e:
            raise HTTPException(502, f"Crafty connection error: {str(e)}")

    data = r.json()
    # Crafty v2 wraps in {"status": "ok", "data": {...}}
    info = data.get("data", data)
    running = info.get("running", False)
    return {
        "running": running,
        "players": info.get("online", info.get("players", 0)),
        "mspt": info.get("mspt", info.get("avg_tick_ms", None)),
        "cpu": info.get("cpu", None),
        "mem_percent": info.get("mem_percent", None),
        "mem_mb": info.get("mem", info.get("mem_mb", None)),
    }


@app.post("/api/server/action")
async def server_action(req: ServerActionRequest):
    if not CRAFTY_URL or not CRAFTY_TOKEN or not CRAFTY_SERVER_ID:
        raise HTTPException(500, "CRAFTY_URL, CRAFTY_TOKEN, and CRAFTY_SERVER_ID are required")

    valid_actions = {"start_server", "stop_server", "restart_server"}
    if req.action not in valid_actions:
        raise HTTPException(400, f"Invalid action. Must be one of: {', '.join(valid_actions)}")

    url = f"{CRAFTY_URL}/api/v2/servers/{CRAFTY_SERVER_ID}/action/{req.action}"
    async with httpx.AsyncClient(timeout=15, verify=False) as client:
        try:
            r = await client.post(url, headers=crafty_headers())
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(502, f"Crafty API error: {e.response.status_code} {e.response.text[:200]}")
        except Exception as e:
            raise HTTPException(502, f"Crafty connection error: {str(e)}")

    return {"ok": True, "action": req.action}


@app.post("/api/server/command")
async def server_command(req: ServerCommandRequest):
    if not CRAFTY_URL or not CRAFTY_TOKEN or not CRAFTY_SERVER_ID:
        raise HTTPException(500, "CRAFTY_URL, CRAFTY_TOKEN, and CRAFTY_SERVER_ID are required")

    if not req.command.strip():
        raise HTTPException(400, "Command cannot be empty")

    url = f"{CRAFTY_URL}/api/v2/servers/{CRAFTY_SERVER_ID}/stdin"
    async with httpx.AsyncClient(timeout=10, verify=False) as client:
        try:
            r = await client.post(url, headers=crafty_headers(), json={"data": req.command})
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(502, f"Crafty API error: {e.response.status_code}")
        except Exception as e:
            raise HTTPException(502, f"Crafty connection error: {str(e)}")

    return {"ok": True, "command": req.command}


@app.get("/api/server/logs")
async def server_logs():
    if not CRAFTY_URL or not CRAFTY_TOKEN or not CRAFTY_SERVER_ID:
        raise HTTPException(500, "CRAFTY_URL, CRAFTY_TOKEN, and CRAFTY_SERVER_ID are required")

    async def log_stream():
        seen_lines: set = set()
        url = f"{CRAFTY_URL}/api/v2/servers/{CRAFTY_SERVER_ID}/logs"
        async with httpx.AsyncClient(timeout=10, verify=False) as client:
            while True:
                try:
                    r = await client.get(url, headers=crafty_headers())
                    if r.status_code == 200:
                        data = r.json()
                        log_lines = data.get("data", data) if isinstance(data, dict) else data
                        if isinstance(log_lines, list):
                            for line in log_lines:
                                line_str = str(line).rstrip()
                                if line_str not in seen_lines:
                                    seen_lines.add(line_str)
                                    yield f"data: {line_str}\n\n"
                        elif isinstance(log_lines, str):
                            for line in log_lines.splitlines():
                                line = line.rstrip()
                                if line and line not in seen_lines:
                                    seen_lines.add(line)
                                    yield f"data: {line}\n\n"
                except Exception:
                    pass
                yield "data: ping\n\n"
                await asyncio.sleep(2)

    return StreamingResponse(
        log_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/sync")
async def trigger_sync():
    if not PORTAINER_TOKEN or not PORTAINER_STACK_ID:
        raise HTTPException(500, "PORTAINER_TOKEN and PORTAINER_STACK_ID are required")
    headers = {"X-API-Key": PORTAINER_TOKEN}
    endpoint_id = PORTAINER_ENDPOINT_ID
    stack_id = PORTAINER_STACK_ID
    async with httpx.AsyncClient(verify=False, timeout=15) as client:
        # Stop first (ignore error if already stopped)
        await client.post(
            f"{PORTAINER_URL}/api/stacks/{stack_id}/stop",
            params={"endpointId": endpoint_id},
            headers=headers,
        )
        # Start
        r = await client.post(
            f"{PORTAINER_URL}/api/stacks/{stack_id}/start",
            params={"endpointId": endpoint_id},
            headers=headers,
        )
        if r.status_code not in (200, 400):  # 400 = already active (race), acceptable
            raise HTTPException(502, f"Portainer error: {r.status_code} {r.text[:100]}")
    return {"ok": True}


# ===== PACK / PACKWIZ ENDPOINTS =====

@app.get("/api/pack/info")
async def pack_info():
    if not GITHUB_PAT or not GITHUB_REPO:
        raise HTTPException(500, "GITHUB_PAT and GITHUB_REPO required")
    gh_headers = {"Authorization": f"Bearer {GITHUB_PAT}", "Accept": "application/vnd.github+json"}
    async with httpx.AsyncClient(timeout=15) as client:
        r_commit = await client.get(
            f"{GITHUB_API}/repos/{GITHUB_REPO}/commits/main", headers=gh_headers
        )
        r_files = await client.get(
            f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/mods", headers=gh_headers
        )
    commit = r_commit.json() if r_commit.status_code == 200 else {}
    files = r_files.json() if r_files.status_code == 200 else []
    pw_count = sum(1 for f in files if isinstance(f, dict) and f.get("name", "").endswith(".pw.toml"))
    jar_count = sum(1 for f in files if isinstance(f, dict) and f.get("name", "").endswith(".jar"))
    c = commit.get("commit", {})
    return {
        "repo": GITHUB_REPO,
        "branch": "main",
        "pw_count": pw_count,
        "jar_count": jar_count,
        "last_commit_sha": commit.get("sha", "")[:7],
        "last_commit_msg": c.get("message", "")[:120],
        "last_commit_author": c.get("author", {}).get("name", ""),
    }


@app.get("/api/mods/{slug}/toml")
async def get_mod_toml(slug: str):
    async with httpx.AsyncClient(timeout=15) as client:
        for path in [f"mods/{slug}.pw.toml", f"mods/{slug}.pw.toml.disabled"]:
            data = await github_get_file(client, path)
            if data:
                content = base64.b64decode(data["content"].replace("\n", "")).decode("utf-8", errors="replace")
                return {"content": content, "sha": data["sha"], "path": path}
    raise HTTPException(404, f"TOML not found for: {slug}")


class TomlBody(BaseModel):
    content: str
    sha: str
    path: str


@app.put("/api/mods/{slug}/toml")
async def put_mod_toml(slug: str, body: TomlBody):
    if not GITHUB_PAT or not GITHUB_REPO:
        raise HTTPException(500, "GITHUB_PAT and GITHUB_REPO required")
    gh_headers = {"Authorization": f"Bearer {GITHUB_PAT}", "Accept": "application/vnd.github+json", "Content-Type": "application/json"}
    payload = {
        "message": f"Edit {body.path}",
        "content": base64.b64encode(body.content.encode()).decode(),
        "sha": body.sha,
    }
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.put(
            f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{body.path}",
            headers=gh_headers, json=payload
        )
    if r.status_code not in (200, 201):
        raise HTTPException(502, f"GitHub error: {r.text[:200]}")
    return {"ok": True}


async def _ensure_packwiz():
    if not os.path.exists(PACKWIZ_BINARY):
        async with httpx.AsyncClient(follow_redirects=True, timeout=60) as client:
            r = await client.get(
                "https://github.com/packwiz/packwiz/releases/download/v0.5.1/packwiz_linux_amd64.zip"
            )
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            with z.open("packwiz") as src, open(PACKWIZ_BINARY, "wb") as dst:
                dst.write(src.read())
        os.chmod(PACKWIZ_BINARY, 0o755)


async def _ensure_repo():
    if not shutil.which("git"):
        subprocess.run(["apk", "add", "--no-cache", "git"], capture_output=True)
    env = {**os.environ, "HOME": "/tmp"}
    git_url = f"https://oauth2:{GITHUB_PAT}@github.com/{GITHUB_REPO}.git"
    if not os.path.exists(os.path.join(PACKWIZ_REPO, ".git")):
        subprocess.run(["git", "clone", "--depth=1", git_url, PACKWIZ_REPO], env=env, capture_output=True)
    else:
        subprocess.run(["git", "fetch", "--depth=1", git_url, "main:main"], env=env, capture_output=True, cwd=PACKWIZ_REPO)
        subprocess.run(["git", "reset", "--hard", "main"], env=env, capture_output=True, cwd=PACKWIZ_REPO)
    subprocess.run(["git", "config", "user.email", "packwiz-manager@auto"], cwd=PACKWIZ_REPO, capture_output=True)
    subprocess.run(["git", "config", "user.name", "packwiz-manager"], cwd=PACKWIZ_REPO, capture_output=True)


class PackwizExecBody(BaseModel):
    args: list


@app.post("/api/packwiz/exec")
async def packwiz_exec(body: PackwizExecBody):
    if not GITHUB_PAT or not GITHUB_REPO:
        raise HTTPException(500, "GITHUB_PAT and GITHUB_REPO required")
    if not body.args:
        raise HTTPException(400, "args required")
    async with packwiz_lock:
        try:
            await _ensure_packwiz()
            await _ensure_repo()
        except Exception as e:
            raise HTTPException(500, f"Setup error: {e}")

        env = {**os.environ, "HOME": "/tmp"}
        proc = subprocess.run(
            [PACKWIZ_BINARY] + [str(a) for a in body.args],
            capture_output=True, text=True, cwd=PACKWIZ_REPO, env=env, timeout=120
        )
        output = (proc.stdout + proc.stderr).strip()

        # Commit and push if anything changed
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=PACKWIZ_REPO)
        committed = False
        if status.stdout.strip():
            subprocess.run(["git", "add", "-A"], cwd=PACKWIZ_REPO)
            msg = "packwiz " + " ".join(str(a) for a in body.args[:3])
            subprocess.run(["git", "commit", "-m", msg], cwd=PACKWIZ_REPO, env=env, capture_output=True)
            push_url = f"https://oauth2:{GITHUB_PAT}@github.com/{GITHUB_REPO}.git"
            push = subprocess.run(
                ["git", "push", push_url, "main"],
                capture_output=True, text=True, cwd=PACKWIZ_REPO, env=env
            )
            output += "\n" + (push.stdout + push.stderr).strip()
            committed = True

        return {"ok": proc.returncode == 0, "output": output, "committed": committed}


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=PORT, reload=False)
