# Repository metadata and Pages plan

1. Keep `repositories.json` as the canonical inventory for every repository in the Get Colors organization, including repositories that are not local checkouts.
2. Synchronize each GitHub description and website field with `./scripts/github-metadata.py --apply`; use the command without `--apply` as the audit.
3. Preserve substantive manuals and application pages, correcting content only when it has drifted from the repository.
4. Publish GitHub Pages from `main` at `/` when a repository intentionally tracks a root `index.html`; do not add a page merely to satisfy a convention.
5. A published repository page uses GA4 measurement ID `G-4VKP1WY4QJ`, with an explicit `page_title` equal to its stable decoded HTML title.
6. Use the GitHub Pages URL as the repository website when the root page is the intended destination. Keep `https://www.getcolors.ai` for `colors-website` and `once-colors`.
7. Leave the website field empty when a repository has no intentional public page or product site; never advertise a URL that returns an error.
8. Validate HTML structure, local links, file tracking, GitHub metadata, and live website responses without reading generated or secret files.
9. Regenerate `index.html` and `report.html` with `./scripts/generate-report.py` after changing the inventory.
10. Commit and push each affected repository independently, then verify every published page.
