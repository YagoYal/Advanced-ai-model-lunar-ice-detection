# Changelog

Record of significant project changes, by date. Loosely follows
[Keep a Changelog](https://keepachangelog.com/) — every entry is backed by
real evidence (a command run, a passing test, a commit), not an estimate.

---

## 2026-11-19 — Site security headers, bounded service-worker cache, cleanup

### Security

- The site now sends (configured in the root `vercel.json`; the first attempt
  used `frontend/vercel.json`, which Vercel turned out not to read, so it was
  deleted) `X-Content-Type-Options: nosniff`,
  `X-Frame-Options: DENY`, `Content-Security-Policy: frame-ancestors 'none'`,
  `Referrer-Policy`, `Permissions-Policy` (camera, microphone, geolocation,
  payment, usb off; clipboard, used by Share, untouched) and
  `Cross-Origin-Opener-Policy`. Before, only HSTS was sent. A full CSP is
  left for later, in report-only mode first.

### Fixed

- Service worker (`public/sw.js`, cache `lunar-ice-v2`): v1 cached every GET
  cache-first, including every NASA tile visited, under a fixed cache name,
  so the cache grew without limit in visitors' browsers. v2 only caches the
  site's own `/assets/` (hashed) files, capped at 40 entries; cross-origin
  requests (API, tiles) are no longer intercepted. The new cache name deletes
  the old cache on activation.

### Removed

- `railway.json` and `Procfile` (Railway was cancelled in June 2026; the
  backend runs on Fly.io). README no longer claims API-key auth on every
  endpoint and has the current test count.

---

## 2026-11-19 — Dead frontend code removed; picomatch exception dropped

### Removed

- `frontend/src/App.jsx` (old entry point, replaced by `LandingPage.jsx`),
  `components/Heatmap.jsx` and `components/LunarMap.jsx`: 237 lines nothing
  imported. The production bundle is byte-identical after the removal (same
  `index-hjV6jWTp.js` hash as the live site), so nothing user-facing changes.
- `leaflet.heat`: only `Heatmap.jsx` used it. Closes Dependabot #37 as
  unnecessary. (The live polar heatmap uses react-leaflet `CircleMarker`.)

### CI

- GitHub withdrew GHSA-fc5q-39xc-vjpf (picomatch) on 2026-11-18, and
  `npm audit` reports 0 vulnerabilities again. Its exception is removed;
  `audit-allowlist.json` is now empty and the gate stays in place.

---

## 2026-11-18 — gunicorn 27 in production; CI audit gate with reviewed exceptions

### Dependencies

- gunicorn 22.0.0 → 27.0.1 (#34), deployed (Fly v13). The backend runs
  `uvicorn.workers.UvicornWorker`, so HTTP/WebSocket parsing stays in uvicorn;
  the stricter gunicorn HTTP parser and the eventlet removal do not apply.

### CI

- `main` went red again on GHSA-fc5q-39xc-vjpf (picomatch <= 4.0.7, ReDoS),
  which has **no patched version**. It is dev/build-only (vite, vitest,
  tinyglobby), the globs come from our own config, and
  `npm audit --omit=dev` is clean.
- The npm audit step now runs `frontend/scripts/audit-gate.mjs`: any
  high/critical advisory blocks the build unless it is listed in
  `frontend/audit-allowlist.json` with a reason and a `review_by` date. When
  that date passes, the gate fails again so the exception is re-checked.
  No new dependency.

---

## 2026-11-16 — Audit follow-up: CI unblocked, hardening

### Fixed

- CI was red: `npm audit` found 5 new advisories (3 high) in build/test-only
  packages (`vite`, `undici`, `source-map-js`, `@vitest/mocker`). Fixed with
  `npm audit fix`. Because the audit step failed first, the tests, the
  scientific benchmark and the smoke test had not run in CI.
- The CI never ran the frontend tests; it now runs `vitest` after the audit.
  Note: the patched `undici` (via `jsdom`) needs Node >= 22.19.

### Security

- In production with real data (`ENV=production`, `DATA_MODE=real`), missing
  data files now abort startup. Before, the API silently served random-noise
  maps with HTTP 200. Dev, CI and mock mode keep the fallback.
- `/ws/simular` no longer sends exception text to the client (generic
  message; full trace stays in the log).

### Dependencies

- Dependabot groups minor/patch updates into one PR per ecosystem per week;
  majors stay separate.
- Applied pending Dependabot bumps: pydantic 2.13.4, slowapi 0.1.10,
  pytest 9.1.1, matplotlib>=3.11.1, @vitejs/plugin-react 6.1.1,
  @testing-library/react 16.3.3, framer-motion 13.1.1 (vite/vitest already
  newer via the audit fix). gunicorn 22→26 (major) left for separate review.

---

## 2026-11-16 — Public site was returning 403 on every analysis

### Fixed

- `lunar-ice.vercel.app` returned **403 "Invalid or missing API key."** on
  `/analisar`, `/analisar_com_mapa` and `/simular`. The production `API_KEY`
  was rotated on 2026-08-20, but the Vercel bundle still embedded the old
  `VITE_API_KEY`. The polar heatmap swallowed the error, so the map showed
  nothing and no message.

### Security

- A key inside a public JS bundle is not a secret (it was extracted from the
  live site with one `curl`). The browser-facing endpoints are now public by
  design. `X-API-Key` is required only on `/predict` (arbitrary input,
  programmatic use, never called by the site).
- The rate limit now keys on the real client IP (`Fly-Client-IP` in
  production). Before, every user behind the Fly proxy shared a single bucket.
- `/ws/simular` had no rate limit at all; it now allows 10 sessions/min per IP.
- The frontend no longer sends any API key. `.env.example` files warn that
  `VITE_*` values are public.
- Tests: 5 new production-mode tests in `backend/test_api.py` (public
  endpoints, `/predict` key enforcement, per-IP buckets for HTTP and WS).

---

## 2026-08-12 — Real deploy, academic publication, and dependency triage

After the previous day's security audit fixed the code on `main` without ever
reaching production, this session closed that gap and organized the project's
academic presence.

### CI — real fix, not the previous day's palliative one

- The first attempt to fix the fixed-PSR-coordinate tests (Shackleton,
  equator) against `docker-ci.yml` (commit `bdcdb0c`) assumed a 64×64 mock
  grid was causing a bounds error — a diagnosis based on an untracked local
  file that **does not exist** on a clean CI checkout.
- Reproduced the real CI environment (clean `git clone` + `docker build`,
  exactly what `actions/checkout` does): without
  `data/processed/lro/mock/`, `backend/main.py` falls back to a
  **random-noise 180×360 grid** — a 200 response, but prob=0.00006
  (Shackleton) / 0.90 (equator), the opposite of expected, because the
  scientific assertion has no valid signal against pure noise.
- Real fix: `pytest.mark.real_data` marker on the 2 tests (registered in
  `pytest.ini`), excluded from the fast mock step (`-m "not real_data"`) and
  run in the step that already generates real data — testing the committed
  production model, not a weakened CI-only retrain. Verified end-to-end by
  simulating both CI steps exactly. Commit `d8783b3`.

### Production

- **First real deploy since June 1st** (`flyctl deploy`, version 6) — shipped
  the CVE fixes, P3/P7, and the real CI fix from the previous session, which
  had been sitting ready in `main` but never deployed.
- Verified with real requests, not assumption: `GET /health` → `200`,
  `GET /v1/openapi.json` → `200`, `POST /analisar` without `X-API-Key` → `403`
  (auth working correctly).
- `frontend/.gitignore` added (ignores local `.vercel/`).

### Scientific publication

- `paper.pdf` recompiled from scratch via Docker (`texlive/texlive:latest`)
  and byte-compared against the previous version — confirms the content was
  already correct, only the local timestamp was misleading.
- **Published as a separate preprint on Zenodo**: DOI
  `10.5281/zenodo.21897740` (CC-BY 4.0), linked to the software DOI
  (`10.5281/zenodo.20014594`) via "Is supplemented by"/"Is supplement to"
  metadata on both records.
- Synced on ORCID: 2 public *works* (software + paper), the paper with an
  extra "Part of" identifier pointing to the software DOI.
- `CITATION.cff`, `21897740.bib`, and the `README.md` badges/BibTeX updated
  with both DOIs.

### Regra zero audit — real findings in `roadmap.md`

- `roadmap.md` claimed the production model uses `FocalLoss(α=0.75, γ=2.0)`.
  False — `model/train.py` has used weighted BCE ever since Focal Loss was
  removed for causing degenerate training collapse. Fixed.
- A dead unchecked line contradicted the checked item right below it.
  Removed.
- "`fly deploy` pending" was already stale by the time it was read — fixed to
  reflect the real deploy done this session.

### Dependency triage (15 accumulated Dependabot PRs, 0 reviewed)

Each one assessed by actual risk (usage in code, tests, runtime), not just
"it's a dependency, merge it":

**Merged** (12, each tested before/after):

- 5× GitHub Actions (`cache`, `checkout`, `setup-node`, `setup-python`,
  `docker/setup-buildx-action`) — CI workflow only, no app impact.
- `requests` 2.33.1→2.34.2, `setuptools` ≥70→≥84.0.0 — straight patches.
- `@vitejs/plugin-react` 6.0.1→6.0.5 — patch, build + 13 vitest confirmed.
- `astropy` 6.1.3→8.0.1 — only used for `astropy.io.fits` in a manual
  ingestion script (`parse_lamp.py`), not `coordinates`/`units` as the
  initial risk categorization assumed.
- `uvicorn` 0.32.0→0.52.1 — validated with a real running server (not just
  `TestClient`): real HTTP + a real WebSocket session against `/ws/simular`.
- `Pillow` ≥11.0.0→≥12.3.0 — transitive dependency, no direct import
  anywhere in the project code.
- `recharts` 2.12.0→3.10.1 — no peer-dependency conflict with React 18
  (different from what was expected); build and 13/13 vitest passing.
  **Not** visually verified: headless Edge was unreliable in this Windows
  sandbox and was abandoned after reasonable effort — a manual look at the
  Dados/Rover chart sections is recommended after the next frontend deploy.

**Deliberately blocked, with a verified reason** (not "major = scary"):

- `react` 18.3.1→19.2.8 — `npm install --dry-run` confirms `ERESOLVE`:
  `react-leaflet@4.2.1` and `framer-motion@11` require `react ^18.0.0`.
  Needs a coordinated upgrade (react-leaflet v5 + framer-motion v13
  together), its own session with visual testing of the map/rover.
- `jsdom` 29→30 and `@testing-library/jest-dom` 6→7 — `jsdom@30` requires
  Node `≥22.22.2`; CI (`docker-ci.yml`) runs Node 20. Blocked until a
  decision is made to bump the CI's Node version.

---

## 2026-08-11 — Full security audit (70 days without a commit on `main`)

The project went without a commit on `main` from 2026-06-02 to 2026-08-11.
Audit run with real evidence (`npm audit`, `pip-audit`), not estimation.

### Security

- Frontend: 4 HIGH vulnerabilities (`nanoid`, `postcss`, `undici`, `vite`)
  fixed via `npm audit fix` — 0 vulnerabilities afterward.
- Backend: 12 known CVEs — the most severe, `starlette==0.38.6` (9 CVEs),
  fixed via `fastapi` 0.115.0→0.141.1 (resolves `starlette` 1.6.0).
  `requests` and `pytest` also updated.
- **Zero security automation before this session** — added
  `.github/dependabot.yml` (pip+npm+github-actions, weekly) and 2 new steps
  in `docker-ci.yml` (`pip-audit --local`, `npm audit --audit-level=high`)
  that fail the build on HIGH+ vulnerabilities.
- 3 worktrees + orphaned branches from abandoned agent sessions, removed.

### Science

- **P3** — `backend/test_integration_production.py`: real HTTP/WebSocket
  tests against production (not mock). 7/7 public endpoints passing.
- **P7** — `model/cross_validate.py`: cross-validation by polar quadrant.
  Real finding, honestly documented in the paper: the model **does not
  generalize** to a polar quadrant never seen in training (hold_sul F1=0.000
  across 30/30 epochs). Doesn't invalidate production (random split sees all
  latitudes) — it's a documented out-of-distribution extrapolation
  limitation, not a bug.
- Real bug found and fixed in `model/run_interpret.py`: it never fetched real
  insolation/temperature per coordinate, inflating false positives in the
  P6 report's negative controls.
- `paper.tex` synced: benchmark 12/14→14/14 (was stale since before the
  haversine fix), new interpretability (P6) and OOD limitation (P7) sections,
  3 new bibliography entries.

### CI — bug identified, but with an incorrect initial diagnosis

A real CI bug was identified on this date: fixed-PSR-coordinate tests were
failing against `docker-ci.yml`. This date's diagnosis and fix (a 64×64 mock
grid causing a bounds error) was **wrong** — based on an untracked local
file that doesn't exist on a real CI checkout. Reviewed and properly fixed
in the following session — see the **2026-08-12** entry above.
