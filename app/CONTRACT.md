# First Rounds app — contract between backend and frontend

Stack (decided, do not vary): Python 3.11+ **FastAPI + uvicorn**, **SQLite** (stdlib `sqlite3`), static front end in `app/static/` (plain HTML/CSS/JS, no build step, no framework). Backend serves `/` → `app/static/index.html` and `/static/*`. All UI follows `design/design.md`.

Run: `uvicorn app.main:app --reload --port 8000` from the repo root. Env from `.env` (`NEBIUS_API_KEY`, `NEBIUS_BASE_URL`), optional `PRIVATE_NAMES="名字,Name"` (replaced by "Mom" before any text reaches the model), optional `NTFY_TOPIC` (push each new todo to https://ntfy.sh/<topic>), optional `FR_DB=path.sqlite` (default `data/firstrounds.sqlite`, gitignored).

## Extraction
`app/extract.py`: `extract(note_text: str, note_date: str) -> dict` — builds the steps from `tools/prompts.py` → `VARIANTS[SHIPPING_VARIANT]` for `MODELS[SHIPPING_MODEL]`, `temperature 0`, `max_tokens 4000`, `response_format json_object`, `chat_template_kwargs {"enable_thinking": SHIPPING_THINKING}`, user templates formatted with `note=, note_date=, prev=, date_context=prompts.date_context(note_date)`. Parses the last step's JSON (strip fences, first `{` to last `}`). Applies PRIVATE_NAMES replacement BEFORE formatting. Raises `ExtractError(message, raw_text)` on failure. Never logs the key. Import tools via `sys.path` insert of the repo's `tools/` dir.

Output JSON shape = `prompts.OUTPUT_SCHEMA` (read it): `problem`, `emergency{warning,sign,source}`, `nothing_medical`, `timeline[]{date,date_precision,what,source,department,test,test_where,result,medicine_event{name,event,date,dose,stopping_rule,reason}|null,helps[],worsens[]}`, `open_questions[]`, `todos[]`, `ask_the_doctor[]`, `current_medicines[]`, `history_question`.

## Data model (SQLite, created on startup)
- `notes(id INTEGER PK, note_date TEXT, text TEXT, kind TEXT 'call'|'answer', answers_question_id INT NULL, created_at TEXT)`
- `extractions(id PK, note_id, model TEXT, variant TEXT, output_json TEXT, raw_text TEXT, error TEXT NULL, created_at)`
- `entries(id PK, note_id, problem TEXT, date TEXT NULL, date_precision TEXT, sort_key TEXT, what TEXT, source TEXT, department, test, test_where, result, med_name, med_event, med_date, med_dose, med_rule, med_reason, helps_json, worsens_json)`
  - `sort_key`: ISO date if `date` is ISO; `YYYY-MM-15` for `YYYY-MM`; `YYYY-07-01` for "about YYYY" / "before YYYY-..." (take the first 4-digit year); else the note_date. Used for ordering only; display uses `date` + `date_precision`.
- `questions(id PK, note_id, text, answered_at NULL, answer_note_id NULL)`
- `todos(id PK, note_id, kind TEXT 'reminder'|'stopcheck'|'emergency'|'history'|'appointment', text TEXT, detail TEXT NULL, done_at NULL, created_at)`
- `current_medicines(id PK, note_id, text)` (latest note's list wins for display, but keep all)
- `ask_doctor(id PK, note_id, problem, text)`

## Rules implemented in code (not trusted to the model)
**Stop-check** (`app/stopcheck.py`): for every entry with `med_event == 'stopped'`: look for an earlier entry (any note, any problem) with the same medicine (name match: shared CJK bigram after removing 的, or shared latin word ≥4 chars, case-insensitive) and a non-empty `med_rule`, or a `med_rule` on the stop entry itself.
- rule found → todo kind `stopcheck`: text `Tell Mom: the doctor said "<rule>" (<medicine>)`, detail = `<medicine> stopped <date or 'date unknown'>; reason: <reason>`.
- no rule → todo kind `stopcheck`: text `Mom stopped <medicine> <date or '(date unknown)'>; no stopping instruction recorded. Ask a doctor or pharmacist.`, detail = drafted question: `我妈<start date or 不记得什么时候>开始吃<medicine>，<reason if any>就停了。当时医生有没有说要吃多久？现在停可以吗？` + English line `Mom started <medicine> on <date/unknown>, stopped <date> because <reason>. Did the doctor say how long to take it? Is stopping now OK?`
- Drop model todos whose text starts with "Mom stopped" / "Tell Mom" (code owns these). Keep the model's other todos as kind `reminder`.

**Emergency** (`app/main.py`): if `emergency.warning` true → todo kind `emergency` with text = the brief's English template filled with sign + source, detail = the Chinese template:
EN: `This note describes a possible warning sign: {sign}. {source} advises calling emergency services (120 in China) immediately, even if symptoms have passed. Call Mom now. If signs are present, she or someone near her should call 120.`
ZH: `这条记录提到了可能的预警信号：{sign}。{source}建议：即使症状已经消失，也应立即拨打120。请现在给妈妈打电话；如果症状仍在，请她或身边的人拨打120。`
Sources map: `NHS` → "NHS guidance on when to call an ambulance" / "英国NHS急救指南"; anything with 中风/BEFAST → "中风120 / BEFAST (Chinese Stroke Association)" / "中风120 / BEFAST（中国卒中学会）". Also drop any model todo starting with "EMERGENCY:" (code owns it).

**History question**: if `history_question` non-null → `questions` row AND todo kind `history` with the same text. Answering (POST /api/questions/{id}/answer) creates a note of kind `answer` with text `Answer to "<question>": <answer>` and note_date today, runs extraction on it (so "crowns in 2024" becomes a rough entry), marks the question answered, marks the history todo done.

**Appointments**: entries whose `what` matches /appointment|复查|复诊|visit/i and whose date is after the note date (or precision rough with "next week") → todo kind `appointment`: `<what> — has the date been confirmed?` (one per note).

**Nothing medical**: store the note + extraction; create no entries/todos/questions; response `nothing_medical: true`.

## HTTP API (all JSON; errors `{error: "..."}` with 4xx/5xx)
- `GET /api/health` → `{ok:true, model:"nvidia/Nemotron-3_5-Lightning", variant:"C3_dateguard", db:"..."}`
- `POST /api/notes` body `{text, note_date?: "YYYY-MM-DD"}` → `201 {note:{id,note_date,text,kind}, problem, nothing_medical, emergency:{warning,sign,source,text_en,text_zh}|null, entries:[entry], questions:[question], todos:[todo], ask_doctor:[str], current_medicines:[str], history_question: str|null, extraction_error: str|null}`. On ExtractError: still save the note, return `201` with `extraction_error` set and empty lists (the UI shows "could not extract, note saved").
- `GET /api/notes` → `[{id,note_date,text,kind,created_at,problem,entry_count,emergency:bool}]` newest first.
- `GET /api/notes/{id}` → the same shape as POST's response.
- `GET /api/timeline` → `{problems:[{problem, since: entry.date of earliest, note_count, entries:[entry]}]}` entries sorted by sort_key asc; problems sorted by latest entry desc. `entry` = DB row as JSON + `note_date` + `stopcheck: todo|null` (attached to 'stopped' entries) + `chips: [{kind:'med'|'med-stop'|'question'|'worse'|'help'|'rule'|'test', text}]` built server-side: med start/stop chip, rule chip ("rule: …") when med_rule, worsens → `worse: …`, helps → `helps: …`, test → `<test> · <result>`.
- `GET /api/today` → `{emergencies:[todo], todos:[todo not done, non-emergency], questions:[unanswered question + note_date], appointments:[entry future-dated]}`
- `POST /api/todos/{id}/done` → `{ok:true}`; `POST /api/todos/{id}/undone` → `{ok:true}`
- `POST /api/questions/{id}/answer` body `{text}` → same shape as POST /api/notes (the answer note's extraction)
- `DELETE /api/notes/{id}` → deletes note + everything derived → `{ok:true}`
- `GET /api/demo/load` → loads `app/demo_notes.json` (invented tooth story, generic names; written by backend) through the normal POST path, returns `{loaded:n}`. Idempotent: skip if a note with identical text exists.

`todo` = `{id, note_id, kind, text, detail, done_at, created_at, note_date}`; `question` = `{id, note_id, text, answered_at, note_date}`.

## Frontend (app/static: index.html, app.css, app.js — nothing else)
Single page, 4 tabs: **Timeline · Today · Doctor card · Notes**, plus the pill FAB "+ After the call" visible on every tab. Phone-first per design.md (content width min(420px,100%), centered). Fetch the API with relative URLs. `?mock=1` in the URL uses `app/static/mock.js`-free inline fixtures (put a `MOCK` object at the top of app.js: the tooth story from design/look.html, same shapes as the API) so the UI can be verified with no backend; `?mock=1` must never be the default.
- **After the call**: bottom sheet / full-screen form: textarea (placeholder "What did Mom tell you? Chinese or English, messy is fine."), date field defaulting to today, button "Turn into timeline". While waiting: the button shows "Reading the note…" (disabled). Result view: emergency block FIRST if any (design.md "Emergency block", EN then ZH text, sources line), then "Added to timeline" entries, "Questions for you" (each with an inline answer box + "Save answer"), "To do", and a "Done" button back to Timeline. If `extraction_error`: an error block "Couldn't read this note. It's saved; try again from Notes." If `nothing_medical`: "Nothing medical in this note. Saved under Notes."
- **Timeline**: grouped by problem, problem heading + "since <date> · <n> notes", entries exactly like design/look.html (rail, dots by precision, card, date line, what, chips, source link that toggles the `source` quote + "from note <note_date>"). Stop-check card inline on stopped entries with the "Tell Mom" / "Ask doctor" pill (clicking marks the todo done). Empty state: "No notes yet. Tap + After the call."
- **Today**: emergency blocks first; then "To do" list with checkboxes (POST done/undone), each with its note date; "Questions for you" with inline answer boxes; "Coming up" appointments. Empty: "Nothing for today."
- **Doctor card**: placeholder card: "Doctor card comes in the next step." (step 3)
- **Notes**: list newest first: date, first 80 chars, chips "emergency" red / "nothing medical" grey / "<n> entries"; tap → expands full text + its entries/questions/todos; "Delete" with confirm.
- Copy: sentence case, plain verbs; the person is "Mom"; the user is "you". No medical advice anywhere in UI copy.

---
# Step 3 addendum — Doctor card (2026-10-30 04:10)

## Card data (code builds it from the DB; the model only renders Chinese)
`GET /api/card?problem=<label>|all&wording=A|B|C|D` → 
```
{ problem, generated_at, source_hash,
  en: CARD, zh: CARD | null, zh_error: str|null }
CARD = {
  title: "Doctor card · teeth · 2026-11-10"            (zh: "妈妈的就诊卡 · 牙齿 · 2026年11月10日"),
  history:   [{date_text, text}],                      # non-test, non-medicine entries for the problem, chronological, rough dates as text
  tests:     [{date_text, test, where, result}],       # entries with a test; result "normal"/"not done"/... kept; where "" if unknown
  medicines: [{name, detail}],                         # current: latest note's current_medicines rows + started-not-stopped events; detail = dose/since/rule if known
  med_events:[{date_text, name, event, rule, reason}], # started/stopped/switched/skipped with stopping rule text if any
  helps: [str], worsens: [str],
  ask:       [{text, kind}]                            # kind: 'note' (ask_doctor rows, deduped), 'stop_rule' (one per started medicine, wording from STOP_RULE_WORDINGS[wording]; en = STOP_RULE_EN + " (<name>)"), 'stopcheck' (one per stopped medicine without a rule: "She stopped <name> on <date> because <reason>. Was it OK to stop? Should she restart?")
}
```
- `problem=all` merges every problem; history/tests/med_events get the problem label prefixed in `text`.
- `date_text`: ISO → "2026-11-03"; approx → "about 2026-10-22"; rough → the stored text; unknown → "date unknown".
- **Chinese**: one Lightning call (same `call()` as extraction, thinking off, max_tokens 4000, response_format json_object) with `prompts.CARD_ZH_SYSTEM` as system and the `en` CARD JSON as the user message. Validate: same keys, same array lengths; on mismatch or ExtractError set `zh=null`, `zh_error`. The stop-rule question text is NOT sent to the model: code inserts `STOP_RULE_WORDINGS[wording]` + "（<name>）" into zh.ask after rendering (so the wording toggle needs no new model call). Cache in table `cards(problem, source_hash, wording_independent_zh_json, en_json, created_at)` keyed by `source_hash` = sha1 of the en CARD without the stop_rule items; a cache hit returns instantly.
- `GET /api/card/text?problem=&wording=&lang=zh|en` → `text/plain; charset=utf-8` one-page rendering (title, then sections with headings 病史 / 已做的检查 / 现在在吃的药 / 想问医生的问题 — en: History / Tests already done / Current medicines / Ask the doctor), for copy/paste into WeChat.

## Doctor card tab (frontend, replaces the placeholder)
- Top: problem select (options from `/api/timeline` problems + "All"), "Make card" button (GET /api/card). While waiting: "Writing the card in Chinese…".
- Toggle row (this IS the step-3 variants review; keep it visible for now): layout `grouped | long` (grouped = the sections above; long = one chronological list merging history + tests + med_events, with the ask section after), density `spacious | dense`, text `normal | large` (large = 19px body / 24px headings, for older eyes), language `中文 | English`, wording `A | B | C | D` (re-fetches the card; cache makes it instant). Persist toggles in localStorage `fr_card_prefs`.
- Buttons: "Copy text" (fetches /api/card/text for the current lang+wording and copies to clipboard; shows "Copied"), "Print" (window.print with a print stylesheet: white, no chrome, card only).
- Card rendering per design.md: the card is a single `.card` surface; section headings 13.5px/600 accent-ink; items in body size; dates in `--ink-2`; questions as a numbered list (order carries meaning here: the doctor reads them in order). Chinese renders with the system CJK fallback; never below body size.
- If `zh` is null: show the English card with a notice "Chinese version failed; showing English. Try again."
