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
