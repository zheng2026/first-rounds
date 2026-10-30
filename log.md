# First Rounds — session log

Pickup rule: read this file top to bottom, then the three spec files (idea description, build-with-variants guideline, additions). Nothing is built without Jade's explicit "Go".

## State (as of 2026-10-30 00:30 Valencia)
- **DEADLINE TODAY:** submit by 16:00 Valencia (hard 18:00). Brief with checkpoints + emergency spec: `first-rounds-build-brief-emrgency-authority-and-checkpoints.md`. Every STOP in it = show Jade, wait.
- Step 1 of the variants guideline (notes → timeline) is in progress.
- **Test set drafted:** `tests/notes.json` — 18 invented notes (n01–n18) + Jade's 3 real notes (r01–r03), each with a drafted expected output. n16–n18 added 2026-10-30 for the brief's emergency must-pass cases (resolved arm weakness, dizziness+vision, negative control).
- **Checks:** `python3 -I tools/check_notes.py tests/notes.json` — 21 hand-listed date-arithmetic assertions, format, coverage. Passing (0 fails) as of 2026-10-30 00:30. Codex second-opinion review (invented / missed / advice) → `tests/review_codex.md`.
- **r03 DECIDED (2026-10-30):** stays flagged. Jade's source: NHS stroke symptoms (https://www.nhs.uk/conditions/stroke/symptoms/) lists dizziness. → add 'sudden dizziness' to the warning-sign list in the system prompt (the brief's list only has it 'together with any of the above').
- **Key setup:** `zsh tools/set_key.sh` — hidden paste → .env (600) → verifies with /v1/models and prints the Nemotron IDs visible to the key. Suggested key name on Token Factory: `first-rounds-dev`.
- **Jade edits `tests/notes.md`**, not the JSON. Current notes.md = post-Codex version (re-exported 2026-10-30 00:21). Tool: `tools/notes_md.py` (export / import / coverage). After her edits run `python3 -I tools/notes_md.py import tests/notes.md tests/notes.json` then `python3 -I tools/notes_md.py coverage tests/notes.json tests/coverage.md`. Round-trip verified lossless on 2026-10-29 (0 diffs across 18 notes).
- **Waiting on Jade:** her edit pass on the notes and expected outputs. The runner is NOT built yet and must not be scored against unedited expectations.
- **Also waiting on Jade:** Nebius Token Factory API key in `.env` (`NEBIUS_API_KEY=...`), never in chat.
- No git repo yet. `.gitignore` already excludes `tests/notes.json` (real brand/drug names) and `.env`.

## Decisions taken (Jade's go, 2026-10-29)
1. r03 (real sudden-dizziness note from 2026-05-15) is an **emergency_warning = true** case. It anchors the threshold. If she later judges it over-fires, flip the flag in notes.json and re-tune prompts.
2. Test set = 15 invented + 3 real, kept as separate groups. Real names stay in the private set; a sanitized copy will be produced for anything public.
3. Test-set drafting done by Fable directly (voice + clinical judgment). Runner + results page: one Sonnet implementer, medium effort, once edited notes exist.

## Expected-output schema (see `meta.conventions` in notes.json)
timeline[] {date, date_precision exact|approx|rough|unknown, what, department, test, test_where, result, medicine_event{name, event started|stopped|skipped|switched|taken_once|resumed, date, dose, stopping_rule, reason}, helps[], worsens[]} + open_questions[], todos[], history_question, ask_the_doctor[], current_medicines[], emergency_warning, nothing_medical, must_not[] (things that count as invented facts / medical advice).

## Scoring rubric (8 dimensions, in notes.json `scoring_rubric`)
dates_correct · no_invented_facts · medicine_events_captured · unclear_to_questions · department_test_result_captured · emergency_flagged (100% recall required: n05, n12, r03) · no_medical_advice · nothing_medical_respected (n08).

## Step 4 deploy / README / submit (started 2026-10-30 13:50)
- README.md + LICENSE (MIT) written (Sonnet implementer), reviewed by Fable. .dockerignore added. `FR_DEMO_ON_START=1` loads the demo story in a background thread on first start (empty DB).
- Docker image builds and runs: `docker build -t first-rounds .`; health answers at once; demo loads ~50 s later. Verified locally 14:10.
- **No deploy host yet:** this Mac has docker only — no vercel/fly/railway/gh CLIs, no logins. A public URL needs Jade: a GitHub repo to push to (and ideally a host linked to it: Render / Railway / HF Spaces Docker / Nebius). Submission needs the public repo at minimum; deploy is optional per the hackathon text.
- Privacy scan (14:05): full git history has 0 hits for real brand names, 0 key-like strings, 0 absolute home paths; the only personal strings are the commit author name/email (Jade's normal git identity). docs/ holds Jade's own idea description (her mother's story in her words) and the build brief ("I'm in Spain") — her call whether those stay public.
- **Public repo:** https://github.com/zheng2026/first-rounds (created by Jade via gh at ~14:20; pushes from this session work).
- **Live:** https://first-rounds-production.up.railway.app (Railway project first-rounds, service first-rounds, volume at /srv/data, vars NEBIUS_API_KEY/NEBIUS_BASE_URL/FR_DEMO_ON_START/FR_DB/PORT=8000). Deploys are Jade's click: `railway redeploy --service first-rounds -y` or `zsh tools/deploy_railway.sh`. The permission layer blocks public-surface creation and deploys for Claude; config changes (variables) are allowed.
- Railway gotcha (cost ~25 min): an empty project needs `railway add --service` first; and the proxy 502s until the service has PORT set and is redeployed (Dockerfile CMD now honours $PORT).
- Tag `hackathon-submission` = the submitted version (pushed). Post-submission work goes on a branch until judging ends 2026-12-15.
- Video: Jade narrated on iPhone (`first rounds.m4a`, 2:44) and screen-recorded the live site clicking along to the cue table in docs/video-script.md; merged with ffmpeg → `first-rounds-demo.mp4` (1080p, 10 MB). Media files are gitignored. Jade uploads to YouTube (Unlisted) and fills Devpost.
- The live demo DB now also holds the emergency note pasted during the recording; clear with `railway redeploy` after deleting the volume, or leave it (it is invented).

## Step 3 doctor card (started 2026-10-30 04:10)
- Contract: app/CONTRACT.md "Step 3 addendum". Card data built in CODE from the DB (history / tests / current medicines / medicine events / helps·worsens / ask). The model only renders Chinese (one Lightning call, `prompts.CARD_ZH_SYSTEM`, same-shape JSON validated, cached by source hash). Stop-rule question inserted by code in the chosen wording — `prompts.STOP_RULE_WORDINGS` A–D — so wording changes need no model call.
- The step-3 variants review = the Doctor card tab itself with toggles (grouped|long, spacious|dense, normal|large, 中文|English, wording A–D) on the demo data. Jade picks; then defaults get locked and toggles hidden.
- Agents: 2 Sonnet implementers (medium): backend app/card.py + routes; frontend card tab in app/static.
- **Built + joined 2026-10-30 05:15.** Live: GET /api/card?problem=teeth renders a fully Chinese card (title, dates, event words formatted in CODE; free text by Lightning; validated + retried if <85% of fields are Chinese); /api/card/text gives the WeChat-paste version; the tab's toggles work on live data.
- Code guards added from live output (app/card.py): stop-rule question only for medicines still being taken (and never for toothpaste etc.); a stopped medicine with a recorded rule becomes a 'stopcheck' question translated by the model; stopped medicines never listed as current; med_events deduped; 'about about' fixed; validator tolerates dropped fields (filled from en). Demo notes now say "brand A toothpaste".
- **LOCKED 2026-10-30 05:20 (Jade): wording A.** Layout grouped, density spacious locked; review toggles hidden (`?review=1` restores). design.md has a Doctor card section. The advice check on model questions: Jade did not ask for a prompt change — leave C3's ask_the_doctor rule as is unless she says so.
- Known model-quality leftovers: the model's own ask_doctor questions sometimes duplicate each other or sound advice-adjacent ("妈妈是否应该停止使用牙膏X以及原因"); one history item is a place, not an event. These are prompt-level; Jade's STOP decides whether to tighten C3's ask_the_doctor rule.

## Step 2 app core (started 2026-10-30 03:20)
- Contract: `app/CONTRACT.md` — stack FastAPI + SQLite + static front end; data model; rules in CODE (stop-check, emergency template, history question → answer note, appointments); HTTP API; frontend screens. Read it before touching app/.
- Schema change (additive, after the eval): OUTPUT_SCHEMA gained `problem` (grouping label) and per-entry `source` (verbatim quote for the source link). The eval ran without them; re-run `tools/run_eval.py --variants C3_dateguard --models lightning --force` if the numbers are ever quoted again.
- Agents: 2 Sonnet implementers (medium) in parallel — backend owns app/*.py, requirements.txt, Dockerfile, app/demo_notes.json; frontend owns app/static/{index.html,app.css,app.js} with a `?mock=1` fixture mode. Fable verifies the join end-to-end.
- Run: `.venv/bin/uvicorn app.main:app --port 8000` → http://127.0.0.1:8000 (venv: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`; system python has no fastapi). Demo data: GET /api/demo/load. Fresh DB: delete data/firstrounds.sqlite.
- **Built + joined 2026-10-30 04:00.** Verified live: demo load (4 notes), chest note → emergency block citing NHS, antibiotic note → "Tell Mom: finish all 7 days" stop-check, nothing-medical note, Timeline/Today/Notes screens in the browser.
- Code-side guards added after seeing live output (all in app/main.py / stopcheck.py): emergency source derived from the sign text (model mislabels chest as stroke); problem labels normalised to a canonical set so one story = one group; duration phrases ("for 7 days", 吃七天) count as a stopping rule when the model leaves it null; meta entries ("note written") dropped; model to-dos that are questions ("Ask Mom…") routed to questions; advice-worded to-dos dropped, and on emergency notes the warning owns the action; reminders ≤4 and questions ≤5 per note.
- Known model-quality limits (prompt, not code): the model sometimes dates a stop event on the note date; odd event types ("continued"); a non-medical demo note yields a few silly questions. Jade's STOPs for step 3 cover wording.
- index.html must reference /static/app.css and /static/app.js (the backend mounts /static).

## Step 0 + look page (2026-10-30 02:45)
- Repo initialised, commit 70c7210 on main. private/ (Jade's real notes = examples.md), docs/ (specs), CLAUDE.md with product rules + emergency spec + model setup. Verified: no private strings in the committed tree.
- `design/look.html` — timeline screen with the tooth story (generic names), 4 independent toggles (mood × type × density × accent = 4×3×2×4). Jade's asks 03:00: all cards very smooth (20–22px) with near-transparent borders in every mood; plus a 4th mood 'glass' (frosted cards over accent-tinted colour blobs, backdrop-filter). Served at http://127.0.0.1:8791/look.html (symlink in tests/). "Copy choice" button gives the lock string. Uncommitted until design.md is written with it.
- **LOCKED 2026-10-30 03:10 (Jade): mood=minimal type=rounded density=spacious accent=indigo** → design/design.md. Glass mood = later, not hackathon. CLAUDE.md has the design rule. Next: app core (step 2), needs Go.

## Step-1 results (2026-10-30 01:25) — tests/results.html, serve with `python3 -m http.server 8791 --directory tests` (file:// blocked in the app browser)
- 168 combos = 4 variants (A_single, B_selfcheck, C_questions_first, A_think) × 2 models × 21 notes. 163 ran; 5 A_think×lightning timed out (>8 min each). A_think×lightning = 219 s/note mean → impractical; shown for information only.
- **Thinking:** both models think by default. OFF via `chat_template_kwargs.enable_thinking=false` (runner default). Lightning ON needs ~10k reasoning tokens/note.
- **Emergency:** every positive caught by every thinking-off combo. B_selfcheck×nano over-fires (4 false alarms: fall, reflux, loose tooth, itch). 
- **Medicine events** are the weak spot everywhere (0.33–0.47 of expected start/stop/skip events found) — models merge or drop events. Real finding, not a matcher artefact (matcher loosened and re-checked).
- Dates 0.67–0.84 (C_questions_first best); rough-stays-rough 0.71–0.90 (A_single lightning best).
- Rescore from cache without API calls: `python3 -I tools/run_eval.py --score-only` then `python3 -I tools/build_page.py`.
- **DECIDED 2026-10-30 01:40 (Jade): model = nvidia/Nemotron-3_5-Lightning, prompt = C_questions_first**, reasoning OFF. Next: prompt fix for medicine events as variant C2_meds (C untouched so page judgments stay valid), Lightning only.

## Step-1 prompt iterations on Lightning (2026-10-30 01:40–02:10), all on the page
- C2_meds = C + "one timeline entry per medicine change" rule. Medicine events 0.44→0.72. Side effect: more dates derived from durations/months.
- C3_dateguard = C2 + date guard (durations/months never become days). Rough-stays-rough 0.90, unexpected dates 0.84, advice-lexicon 0.95; medicine events 0.64.
- C4_calendar = C2 + computed calendar anchors injected in the user prompt. WORSE on dates (0.63). Dropped. Lesson: Lightning gets confused by a calendar block; weekday errors need another approach (e.g. post-hoc date check in code).
- Scorer fixes along the way: medicine-name matching by CJK bigram (的 ignored); ISO dates embedded in rough expected text are allowed; 'stroke' after NHS/BEFAST not an advice hit.
- **DECIDED 2026-10-30 02:15 (Jade): shipping prompt = C3_dateguard** on Lightning, thinking off. `prompts.SHIPPING_*` marks it. Step 1 closed.

## Step-1 runner (built 2026-10-30 ~00:50)
- `tools/prompts.py` — 3 variants, one dimension each: A_single (baseline), B_selfcheck (extract → checker pass deletes anything not in the note), C_questions_first (unclear list + emergency check before extraction). Shared RULES block = no-advice, nothing-invented, unclear→question, date rules, medicine/stop-check, emergency spec (brief's list + 'sudden dizziness' alone per NHS, Jade 10-30) with the brief's template message. MODELS = lightning, nano.
- `tools/score.py` — mechanical proxies only: dates_correct, rough_stays_rough, no_unexpected_dates, med_events, stopping_rules, dept_test_result, questions (token overlap), emergency, nothing_medical, no_advice_lexicon, no_foreign_drugs. Judgment (invented facts, advice wording) is Jade's, on the page.
- `tools/run_eval.py` + `tools/build_page.py` — by 1 Sonnet implementer (medium). Cache tests/runs/<variant>__<model>/<id>.json; tests/results.json; tests/results.html self-contained (file://), with per-column manual judgment controls saved in localStorage + export.
- Run: `python3 -I tools/run_eval.py` (126 calls, cached) then `python3 -I tools/build_page.py` → open tests/results.html.
- Model IDs verified against /v1/models with Jade's key (2026-10-30 00:40). Region not exposed by the API.

## Next (after Jade's edit pass)
1. Verify model IDs + EU hosting on Token Factory with one API call (`nvidia/Nemotron-3_5-Lightning`, `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` per guideline; hackathon text says Nemotron 3 Ultra/Super/Nano — reconcile).
2. Write 3 prompt variants (dimensions to name first — proposal: (a) strict-schema JSON extraction, (b) two-pass: extract then self-check against note, (c) question-first: list unclear things before extracting).
3. Runner: 18 notes × 6 combos, cache raw outputs, auto-score the mechanical dimensions, leave judgment dimensions for Jade on the results page.
4. One results page: score table + per-note side-by-side.

## Open flags for Jade
- Brief's Step 1 asks for 3 real + ~5 variations; we have 21. Results page must still be readable — group by case, not by note, if needed.
- n01 and n13 test the "last Tuesday" ambiguity (zh 上周二 = previous week; en "last tuesday" could be either). Expected answers accept approx + a question.
- n11 "before new year" is deliberately ambiguous (元旦 vs 春节); expected = ask, never pick.
- Guideline says ~5 notes in one place and 10 in another; we're at 18. Trim if the results page gets unreadable.

## Log
- 2026-10-29 — Session 1 (Fable). Read all spec files. Drafted tests/notes.json + tests/coverage.md. Created log.md, .gitignore. No agents spawned.
- 2026-10-29 — Session 1 cont. Built tools/notes_md.py and exported tests/notes.md for Jade's edit pass. Round-trip verified.
- 2026-10-30 17:35 — Demo video merged and handed over. Jade on Devpost. Session's work complete.
- 2026-10-30 14:45 — Repo public, Railway live, tag hackathon-submission pushed. Submission material ready for Devpost.
- 2026-10-30 14:15 — Step 4: README/LICENSE written, Docker verified, privacy scan done, committed. Waiting on Jade: privacy approval + GitHub repo/host.
- 2026-10-30 05:20 — Jade locked wording A. Toggles hidden, design.md updated, committed. Step 3 closed. Next: step 4 (deploy, README, video) — awaiting Go.
- 2026-10-30 05:15 — Doctor card built (2 Sonnet implementers), joined, 7 code fixes from live output, verified in browser, committed. Waiting on Jade's two STOPs.
- 2026-10-30 04:15 — Go doctor card. Card prompt + contract written, 2 Sonnet implementers spawned.
- 2026-10-30 04:00 — App core built (2 Sonnet implementers), joined, patched, verified live. Committed. Next: step 3 (doctor card, Chinese wording STOP, medical-advice STOP). Awaiting Go.
- 2026-10-30 03:20 — Go app core. Contract written, schema +problem/+source, 2 Sonnet implementers spawned (backend / frontend).
- 2026-10-30 03:10 — Look locked (minimal/rounded/spacious/indigo). design.md written, committed with look.html. Awaiting Go for app core.
- 2026-10-30 02:45 — Step 0 committed (Sonnet implementer). Look page built + verified in browser. Waiting on Jade's look choice.
- 2026-10-30 02:15 — Jade: C3 ships. Step 1 closed. Next: brief step 0 (repo, private/, CLAUDE.md rules) + step 2 (app core, look-of-the-app page). Awaiting Go.
- 2026-10-30 02:10 — Jade picked Lightning + C. Iterated C2/C3/C4 on Lightning (63 calls). Page rebuilt (results.html, 10 columns). Waiting on Jade: C2 vs C3.
- 2026-10-30 01:25 — Full run done (163/168), page built, Lightning thinking issue found and solved (enable_thinking=false). Waiting on Jade's review.
- 2026-10-30 00:50 — Go on runner. Wrote prompts.py + score.py; spawned 1 Sonnet implementer (medium) for run_eval.py + build_page.py.
- 2026-10-30 00:35 — Jade: r03 stays flagged (NHS stroke page). Wrote tools/set_key.sh. Waiting on key paste.
- 2026-10-30 00:21 — Codex review back: 44 findings (27 invented, 13 missed, 4 advice). All applied except the 4 advice hits, which are the emergency to-dos the brief authorises — rewritten to the brief's template. check_notes.py passes (18 date assertions after removing 3 that assumed undated first doses). notes.md re-exported with n16–n18 and all fixes.
- 2026-10-30 00:16 — Jade: notes read as human. Read the build brief (deadline today 16:00; emergency spec). Built tools/check_notes.py (pass). Added n16–n18. Spawned 1 Codex agent (codex-rescue, read-only) for invented/missed/advice review.
