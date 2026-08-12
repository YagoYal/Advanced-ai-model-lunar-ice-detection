# Changelog

Record of significant project changes, by date. Loosely follows
[Keep a Changelog](https://keepachangelog.com/) — every entry is backed by
real evidence (a command run, a passing test, a commit), not an estimate.

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
