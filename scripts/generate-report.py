#!/usr/bin/env python3
"""Generate report.html from repositories.json and the local checkouts."""

from __future__ import annotations

import html
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO.parent
MANIFEST = REPO / "repositories.json"
REPORT_OUTPUT = REPO / "report.html"
INDEX_OUTPUT = REPO / "index.html"
GA_ID = "G-4VKP1WY4QJ"
INDEX_TITLE = "Project Portfolio Quality & Readiness Audit"


def git(path: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(path), *args], text=True).strip()


def page_status(path: Path) -> str:
    page = path / "index.html"
    if not page.exists():
        return "Not published"
    source = page.read_text(errors="replace")
    title_match = re.search(r"<title(?:\s[^>]*)?>(.*?)</title\s*>", source, re.I | re.S)
    page_title = re.search(r"page_title\s*:\s*(['\"])(.*?)\1", source)
    if not title_match or not page_title:
        return "Page metadata incomplete"
    title = html.unescape(re.sub(r"<[^>]*>", "", title_match.group(1)).strip())
    if GA_ID not in source or html.unescape(page_title.group(2)) != title:
        return "Page metadata mismatch"
    return "Published"


def main() -> None:
    manifest = json.loads(MANIFEST.read_text())
    expected = {name for name, data in manifest.items() if data.get("checkout", True)}
    actual = {path.name for path in ROOT.iterdir() if (path / ".git").is_dir()}
    if expected != actual:
        raise SystemExit(
            f"checkout inventory mismatch; only local={sorted(actual-expected)}, only manifest={sorted(expected-actual)}"
        )

    projects = []
    for name, metadata in sorted(manifest.items()):
        checkout = metadata.get("checkout", True)
        project = {
            "name": name,
            "category": metadata["category"],
            "description": metadata["description"],
            "homepage": metadata["homepage"],
            "checkout": checkout,
        }
        if checkout:
            path = ROOT / name
            tracked = git(path, "ls-files").splitlines()
            project.update(
                branch=git(path, "branch", "--show-current"),
                tracked=len(tracked),
                readme="README.md" in tracked,
                guidance="CLAUDE.md" in tracked,
                workflows=sum(item.startswith(".github/workflows/") for item in tracked),
                page=page_status(path),
            )
        projects.append(project)

    local_count = len(expected)
    published = sum(project.get("page") == "Published" for project in projects)
    guidance = sum(project.get("guidance", False) for project in projects)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    data = json.dumps(projects, separators=(",", ":")).replace("</", "<\\/")

    document = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark"><title>Get Colors Workspace Audit — {local_count} Checkouts</title>
<style>
:root{{--bg:#09111f;--panel:#111c2f;--text:#e8eef8;--muted:#9cadc2;--line:#2a3b55;--blue:#67c1ff;--green:#4ade80}}*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(circle at 85% 0,#173557 0,transparent 34rem),var(--bg);color:var(--text);font:15px/1.55 system-ui,sans-serif}}.shell{{width:min(1280px,calc(100% - 30px));margin:auto}}header{{padding:58px 0 26px}}h1{{margin:.1em 0;font-size:clamp(2.3rem,6vw,4.7rem);line-height:1;letter-spacing:-.05em}}.eyebrow{{color:#7dd3fc;font-weight:800;letter-spacing:.13em;text-transform:uppercase}}.lead,.muted{{color:var(--muted)}}.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:24px 0}}.kpi,.card{{border:1px solid var(--line);border-radius:14px;background:linear-gradient(145deg,var(--panel),#0e192b)}}.kpi{{padding:18px}}.kpi b{{display:block;font-size:2rem;color:var(--green)}}.toolbar{{position:sticky;top:0;z-index:2;display:grid;grid-template-columns:1fr 210px;gap:10px;padding:11px;margin:24px 0;background:#09111ee8;border:1px solid var(--line);border-radius:13px;backdrop-filter:blur(12px)}}input,select{{height:43px;padding:0 12px;background:#101b2d;color:var(--text);border:1px solid var(--line);border-radius:8px;font:inherit}}.result{{grid-column:1/-1;color:var(--muted);font-size:.85rem}}.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:13px}}.card{{padding:19px}}.head{{display:flex;justify-content:space-between;gap:15px}}h2{{margin:0;font-size:1.3rem}}.pill{{height:max-content;border:1px solid var(--line);border-radius:99px;padding:3px 8px;color:#c5d2e3;font-size:.7rem;font-weight:800;text-transform:uppercase}}.description{{min-height:48px;color:#c5d0df}}.facts{{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-top:14px}}.fact{{padding:8px;border-radius:8px;background:#0b1526;text-align:center;color:var(--muted);font-size:.72rem}}.fact b{{display:block;color:var(--text);font-size:.9rem}}a{{color:var(--blue);overflow-wrap:anywhere}}footer{{padding:40px 0;color:var(--muted);text-align:center}}@media(max-width:850px){{.kpis,.grid{{grid-template-columns:repeat(2,1fr)}}}}@media(max-width:600px){{.kpis,.grid,.toolbar{{grid-template-columns:1fr}}.result{{grid-column:auto}}}}
</style></head><body>
<header class="shell"><div class="eyebrow">Canonical repository inventory</div><h1>Get Colors workspace audit</h1><p class="lead">The local workspace contains {local_count} checkouts. The getcolors organization contains {len(projects)} repositories; <code>airflow-dags</code> is the one organization repository not checked out here.</p><p class="muted">Generated {generated} from tracked files and <code>repositories.json</code>. GitHub descriptions and website fields are synchronized from the same manifest.</p></header>
<main class="shell"><section class="kpis"><div class="kpi"><b>{local_count}</b>local checkouts</div><div class="kpi"><b>{len(projects)}</b>organization repositories</div><div class="kpi"><b>{published}</b>validated landing pages</div><div class="kpi"><b>{guidance}/{local_count}</b>tracked CLAUDE.md files</div></section>
<section class="toolbar"><input id="search" type="search" placeholder="Search names and descriptions…"><select id="category"><option value="all">All layers</option><option>sdk</option><option>package</option><option>deployment</option><option>application</option><option>automation</option><option>portfolio</option></select><div class="result" id="result"></div></section><section class="grid" id="grid"></section></main>
<footer class="shell">Canonical metadata: <code>workspace/repositories.json</code></footer>
<script>const projects={data};const esc=s=>String(s).replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));const grid=document.querySelector('#grid'),search=document.querySelector('#search'),category=document.querySelector('#category'),result=document.querySelector('#result');function card(p){{const home=p.homepage?`<a href="${{esc(p.homepage)}}">${{esc(p.homepage)}}</a>`:'Not published';return `<article class="card"><div class="head"><h2>${{esc(p.name)}}</h2><span class="pill">${{esc(p.category)}}</span></div><p class="description">${{esc(p.description)}}</p><p>${{home}}</p><div class="facts"><div class="fact"><b>${{p.checkout?'Local':'Remote only'}}</b>checkout</div><div class="fact"><b>${{p.page||'N/A'}}</b>landing page</div><div class="fact"><b>${{p.checkout?p.workflows:'N/A'}}</b>workflow files</div></div></article>`}}function render(){{const q=search.value.trim().toLowerCase(),items=projects.filter(p=>(category.value==='all'||p.category===category.value)&&(!q||`${{p.name}} ${{p.description}}`.toLowerCase().includes(q)));grid.innerHTML=items.map(card).join('');result.textContent=`Showing ${{items.length}} of ${{projects.length}} repositories`}}search.addEventListener('input',render);category.addEventListener('change',render);render();</script></body></html>'''
    REPORT_OUTPUT.write_text(document)
    index_document = document.replace(
        f"<title>Get Colors Workspace Audit — {local_count} Checkouts</title>",
        f"<title>{INDEX_TITLE}</title>",
    ).replace(
        "</head>",
        f'''<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag('js',new Date());gtag('config','{GA_ID}',{{page_title:'{INDEX_TITLE}'}});</script></head>''',
        1,
    )
    INDEX_OUTPUT.write_text(index_document)
    print(f"wrote {REPORT_OUTPUT} and {INDEX_OUTPUT} with {len(projects)} repositories ({local_count} local)")


if __name__ == "__main__":
    main()
